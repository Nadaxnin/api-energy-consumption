import grpc

import tasks_pb2
import tasks_pb2_grpc


def run():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = tasks_pb2_grpc.TaskServiceStub(channel)

        response = stub.GetTasks(tasks_pb2.Empty())

        print("Tasks:")
        for task in response.tasks:
            print(task.id, task.title, task.completed)

        created = stub.CreateTask(
            tasks_pb2.CreateTaskRequest(
                title="Task from gRPC",
                completed=False,
            )
        )

        print("Created:")
        print(created)

        updated = stub.UpdateTask(
            tasks_pb2.UpdateTaskRequest(
                id=created.task.id,
                completed=True,
            )
        )

        print("Updated:")
        print(updated)

        deleted = stub.DeleteTask(
            tasks_pb2.TaskIdRequest(
                id=created.task.id,
            )
        )

        print("Deleted:")
        print(deleted)


if __name__ == "__main__":
    run()