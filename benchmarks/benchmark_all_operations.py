import csv
import math
import statistics
import sys
import time
from pathlib import Path

import grpc
import requests
from codecarbon import EmissionsTracker
from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import tasks_pb2
import tasks_pb2_grpc
from app.database import engine, create_dbtables
from app.models import Task

REST_URL = "http://127.0.0.1:8000/tasks"
GRAPHQL_URL = "http://127.0.0.1:8000/graphql"
GRPC_TARGET = "localhost:50051"

REQUESTS_PER_RUN = 1000
WARMUP_REQUESTS = 20
RUNS_PER_COMBINATION = 3

HTTP_TIMEOUT_SECONDS = 30

RESULTS_DIR = PROJECT_ROOT / "benchmarks"
CODECARBON_DIR = RESULTS_DIR / "codecarbon"

APIS = ["REST", "GraphQL", "gRPC"]

OPERATIONS = [
    "get_all_tasks",
    "get_one_task",
    "create_task",
    "update_task",
    "delete_task",
]

RERUN_ONLY = [
    ("GraphQL", "get_one_task"),
    ("REST", "get_one_task"),
    ("GraphQL", "update_task"),
    ("GraphQL", "delete_task"),
]

GRAPHQL_GET_ALL = """
query {
  tasks {
    id
    title
    completed
  }
}
"""

GRAPHQL_GET_ONE = """
query GetTask($taskId: Int!) {
  task(taskId: $taskId) {
    id
    title
    completed
  }
}
"""

GRAPHQL_CREATE = """
mutation CreateTask($title: String!, $completed: Boolean!) {
  createTask(task: {title: $title, completed: $completed}) {
    id
    title
    completed
  }
}
"""

GRAPHQL_UPDATE = """
mutation UpdateTask($taskId: Int!, $title: String, $completed: Boolean) {
  updateTask(taskId: $taskId, task: {title: $title, completed: $completed}) {
    id
    title
    completed
  }
}
"""

GRAPHQL_DELETE = """
mutation DeleteTask($taskId: Int!) {
  deleteTask(taskId: $taskId)
}
"""


def reset_database(seed_count):
    create_dbtables()

    with Session(engine) as session:
        existing_tasks = session.exec(select(Task)).all()

        for task in existing_tasks:
            session.delete(task)

        session.commit()

        new_tasks = []
        for task_id in range(1, seed_count + 1):
            new_tasks.append(
                Task(
                    id=task_id,
                    title=f"Task {task_id}",
                    completed=False,
                )
            )

        session.add_all(new_tasks)
        session.commit()


def seed_count_for_operation(operation):
    if operation in ["update_task", "delete_task"]:
        return REQUESTS_PER_RUN + WARMUP_REQUESTS + 10

    return 100


def percentile(values, p):
    sorted_values = sorted(values)
    index = math.ceil((p / 100) * len(sorted_values)) - 1
    return sorted_values[index]


def create_result(
    api_name,
    operation,
    run_number,
    successful_requests,
    total_time,
    latencies,
    energy_kwh,
    emissions_kg,
):
    average_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = percentile(latencies, 95)
    throughput = successful_requests / total_time

    if energy_kwh is not None and successful_requests > 0:
        energy_per_request_kwh = energy_kwh / successful_requests
    else:
        energy_per_request_kwh = None

    return {
        "api": api_name,
        "operation": operation,
        "run": run_number,
        "requests": REQUESTS_PER_RUN,
        "successful_requests": successful_requests,
        "total_time_seconds": round(total_time, 6),
        "average_latency_ms": round(average_latency, 6),
        "median_latency_ms": round(median_latency, 6),
        "p95_latency_ms": round(p95_latency, 6),
        "throughput_requests_per_second": round(throughput, 6),
        "energy_kwh": energy_kwh,
        "energy_per_request_kwh": energy_per_request_kwh,
        "emissions_kg": emissions_kg,
    }


def run_with_energy(api_name, operation, run_number, benchmark_function):
    CODECARBON_DIR.mkdir(parents=True, exist_ok=True)

    tracker = EmissionsTracker(
        project_name=f"{api_name}_{operation}_run_{run_number}",
        output_dir=str(CODECARBON_DIR),
        output_file=f"codecarbon_{api_name}_{operation}_run_{run_number}.csv",
        save_to_file=True,
        log_level="error",
    )

    tracker.start()

    try:
        successful_requests, total_time, latencies = benchmark_function()
    finally:
        emissions = tracker.stop()

    data = getattr(tracker, "final_emissions_data", None)

    if data is not None:
        energy_kwh = getattr(data, "energy_consumed", None)
        emissions_kg = getattr(data, "emissions", emissions)
    else:
        energy_kwh = None
        emissions_kg = emissions

    return create_result(
        api_name,
        operation,
        run_number,
        successful_requests,
        total_time,
        latencies,
        energy_kwh,
        emissions_kg,
    )


def rest_request(operation, index):
    try:
        if operation == "get_all_tasks":
            response = requests.get(REST_URL, timeout=HTTP_TIMEOUT_SECONDS)
            return response.status_code == 200

        if operation == "get_one_task":
            response = requests.get(
                f"{REST_URL}/1",
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            return response.status_code == 200

        if operation == "create_task":
            payload = {
                "title": f"Created REST task {index}",
                "completed": False,
            }
            response = requests.post(
                REST_URL,
                json=payload,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            return response.status_code in [200, 201]

        if operation == "update_task":
            task_id = index + 1
            payload = {
                "title": f"Updated REST task {task_id}",
                "completed": True,
            }
            response = requests.patch(
                f"{REST_URL}/{task_id}",
                json=payload,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            return response.status_code == 200

        if operation == "delete_task":
            task_id = index + 1
            response = requests.delete(
                f"{REST_URL}/{task_id}",
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            return response.status_code in [200, 204]

    except requests.exceptions.RequestException:
        return False

    return False


def graphql_request(operation, index):
    if operation == "get_all_tasks":
        payload = {
            "query": GRAPHQL_GET_ALL,
        }

    elif operation == "get_one_task":
        payload = {
            "query": GRAPHQL_GET_ONE,
            "variables": {
                "taskId": 1,
            },
        }

    elif operation == "create_task":
        payload = {
            "query": GRAPHQL_CREATE,
            "variables": {
                "title": f"Created GraphQL task {index}",
                "completed": False,
            },
        }

    elif operation == "update_task":
        task_id = index + 1
        payload = {
            "query": GRAPHQL_UPDATE,
            "variables": {
                "taskId": task_id,
                "title": f"Updated GraphQL task {task_id}",
                "completed": True,
            },
        }

    elif operation == "delete_task":
        task_id = index + 1
        payload = {
            "query": GRAPHQL_DELETE,
            "variables": {
                "taskId": task_id,
            },
        }

    else:
        return False

    try:
        response = requests.post(
            GRAPHQL_URL,
            json=payload,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException:
        return False

    if response.status_code != 200:
        return False

    try:
        body = response.json()
    except ValueError:
        return False

    return "errors" not in body


def grpc_request(operation, index, stub):
    try:
        if operation == "get_all_tasks":
            response = stub.GetTasks(tasks_pb2.Empty())
            return response.tasks is not None

        if operation == "get_one_task":
            response = stub.GetTask(tasks_pb2.TaskIdRequest(id=1))
            return response.error == ""

        if operation == "create_task":
            response = stub.CreateTask(
                tasks_pb2.CreateTaskRequest(
                    title=f"Created gRPC task {index}",
                    completed=False,
                )
            )
            return response.error == ""

        if operation == "update_task":
            task_id = index + 1
            response = stub.UpdateTask(
                tasks_pb2.UpdateTaskRequest(
                    id=task_id,
                    title=f"Updated gRPC task {task_id}",
                    completed=True,
                )
            )
            return response.error == ""

        if operation == "delete_task":
            task_id = index + 1
            response = stub.DeleteTask(
                tasks_pb2.TaskIdRequest(id=task_id)
            )
            return response.success is True

    except grpc.RpcError:
        return False

    return False


def benchmark_rest(operation):
    def benchmark_function():
        latencies = []
        successful_requests = 0

        for index in range(WARMUP_REQUESTS):
            rest_request(operation, index)

        start_time = time.perf_counter()

        for index in range(REQUESTS_PER_RUN):
            request_start = time.perf_counter()
            success = rest_request(operation, index + WARMUP_REQUESTS)
            request_end = time.perf_counter()

            if success:
                successful_requests += 1

            latencies.append((request_end - request_start) * 1000)

        total_time = time.perf_counter() - start_time

        return successful_requests, total_time, latencies

    return benchmark_function


def benchmark_graphql(operation):
    def benchmark_function():
        latencies = []
        successful_requests = 0

        for index in range(WARMUP_REQUESTS):
            graphql_request(operation, index)

        start_time = time.perf_counter()

        for index in range(REQUESTS_PER_RUN):
            request_start = time.perf_counter()
            success = graphql_request(operation, index + WARMUP_REQUESTS)
            request_end = time.perf_counter()

            if success:
                successful_requests += 1

            latencies.append((request_end - request_start) * 1000)

        total_time = time.perf_counter() - start_time

        return successful_requests, total_time, latencies

    return benchmark_function


def benchmark_grpc(operation):
    def benchmark_function():
        latencies = []
        successful_requests = 0

        with grpc.insecure_channel(GRPC_TARGET) as channel:
            stub = tasks_pb2_grpc.TaskServiceStub(channel)

            for index in range(WARMUP_REQUESTS):
                grpc_request(operation, index, stub)

            start_time = time.perf_counter()

            for index in range(REQUESTS_PER_RUN):
                request_start = time.perf_counter()
                success = grpc_request(operation, index + WARMUP_REQUESTS, stub)
                request_end = time.perf_counter()

                if success:
                    successful_requests += 1

                latencies.append((request_end - request_start) * 1000)

            total_time = time.perf_counter() - start_time

        return successful_requests, total_time, latencies

    return benchmark_function


def save_results(results, output_path):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = output_path.exists()

    with open(output_path, "a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())

        if not file_exists:
            writer.writeheader()

        writer.writerows(results)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"rerun_problematic_rows_{timestamp}.csv"

    benchmark_map = {
        "REST": benchmark_rest,
        "GraphQL": benchmark_graphql,
        "gRPC": benchmark_grpc,
    }

    for api_name, operation in RERUN_ONLY:
        for run_number in range(1, RUNS_PER_COMBINATION + 1):
            print(f"Rerunning {api_name} {operation} run {run_number}")

            reset_database(seed_count_for_operation(operation))

            benchmark_function = benchmark_map[api_name](operation)

            result = run_with_energy(
                api_name,
                operation,
                run_number,
                benchmark_function,
            )

            print(result)
            save_results([result], output_path)

    print(f"Saved rerun results to {output_path}")

if __name__ == "__main__":
    main()