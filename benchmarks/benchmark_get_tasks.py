import csv
import statistics
import sys
import time
from pathlib import Path

import grpc
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import tasks_pb2
import tasks_pb2_grpc


REST_URL = "http://127.0.0.1:8000/tasks"
GRAPHQL_URL = "http://127.0.0.1:8000/graphql"
GRPC_TARGET = "localhost:50051"

REQUESTS_PER_API = 1000
WARMUP_REQUESTS = 20

GRAPHQL_QUERY = """
query {
  tasks {
    id
    title
    completed
  }
}
"""


def benchmark_rest():
    latencies = []
    successful_requests = 0

    for _ in range(WARMUP_REQUESTS):
        requests.get(REST_URL, timeout=10)

    start_time = time.perf_counter()

    for _ in range(REQUESTS_PER_API):
        request_start = time.perf_counter()
        response = requests.get(REST_URL, timeout=10)
        request_end = time.perf_counter()

        if response.status_code == 200:
            successful_requests += 1

        latencies.append((request_end - request_start) * 1000)

    total_time = time.perf_counter() - start_time

    return create_result("REST", successful_requests, total_time, latencies)


def benchmark_graphql():
    latencies = []
    successful_requests = 0

    payload = {"query": GRAPHQL_QUERY}

    for _ in range(WARMUP_REQUESTS):
        requests.post(GRAPHQL_URL, json=payload, timeout=10)

    start_time = time.perf_counter()

    for _ in range(REQUESTS_PER_API):
        request_start = time.perf_counter()
        response = requests.post(GRAPHQL_URL, json=payload, timeout=10)
        request_end = time.perf_counter()

        if response.status_code == 200 and "errors" not in response.json():
            successful_requests += 1

        latencies.append((request_end - request_start) * 1000)

    total_time = time.perf_counter() - start_time

    return create_result("GraphQL", successful_requests, total_time, latencies)


def benchmark_grpc():
    latencies = []
    successful_requests = 0

    with grpc.insecure_channel(GRPC_TARGET) as channel:
        stub = tasks_pb2_grpc.TaskServiceStub(channel)

        for _ in range(WARMUP_REQUESTS):
            stub.GetTasks(tasks_pb2.Empty())

        start_time = time.perf_counter()

        for _ in range(REQUESTS_PER_API):
            request_start = time.perf_counter()
            response = stub.GetTasks(tasks_pb2.Empty())
            request_end = time.perf_counter()

            if response.tasks is not None:
                successful_requests += 1

            latencies.append((request_end - request_start) * 1000)

        total_time = time.perf_counter() - start_time

    return create_result("gRPC", successful_requests, total_time, latencies)


def create_result(api_name, successful_requests, total_time, latencies):
    average_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18]
    throughput = successful_requests / total_time

    return {
        "api": api_name,
        "requests": REQUESTS_PER_API,
        "successful_requests": successful_requests,
        "total_time_seconds": round(total_time, 4),
        "average_latency_ms": round(average_latency, 4),
        "median_latency_ms": round(median_latency, 4),
        "p95_latency_ms": round(p95_latency, 4),
        "throughput_requests_per_second": round(throughput, 4),
    }


def save_results(results):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = PROJECT_ROOT / "benchmarks" / f"results_get_tasks_{timestamp}.csv"

    with open(output_path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"Saved results to {output_path}")


def main():
    results = [
        benchmark_rest(),
        benchmark_graphql(),
        benchmark_grpc(),
    ]

    for result in results:
        print(result)

    save_results(results)


if __name__ == "__main__":
    main()