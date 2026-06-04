from concurrent import futures

import grpc
from sqlmodel import Session, select

import tasks_pb2
import tasks_pb2_grpc
from app.database import engine, create_dbtables
from app.models import Task


def task_to_proto(task: Task) -> tasks_pb2.Task:
    if task.id is None:
        raise ValueError("Task id cannot be None after database save")

    return tasks_pb2.Task(
        id=task.id,
        title=task.title,
        completed=task.completed,
    )


class TaskService(tasks_pb2_grpc.TaskServiceServicer):
    def GetTasks(self, request, context):
        with Session(engine) as session:
            statement = select(Task)
            tasks = session.exec(statement).all()

            return tasks_pb2.TaskList(
                tasks=[task_to_proto(task) for task in tasks]
            )

    def GetTask(self, request, context):
        with Session(engine) as session:
            task = session.get(Task, request.id)

            if task is None:
                return tasks_pb2.TaskResponse(
                    error="Task not found"
                )

            return tasks_pb2.TaskResponse(
                task=task_to_proto(task),
                error="",
            )

    def CreateTask(self, request, context):
        with Session(engine) as session:
            new_task = Task(
                title=request.title,
                completed=request.completed,
            )

            session.add(new_task)
            session.commit()
            session.refresh(new_task)

            return tasks_pb2.TaskResponse(
                task=task_to_proto(new_task),
                error="",
            )

    def UpdateTask(self, request, context):
        with Session(engine) as session:
            task = session.get(Task, request.id)

            if task is None:
                return tasks_pb2.TaskResponse(
                    error="Task not found"
                )

            if request.HasField("title"):
                task.title = request.title

            if request.HasField("completed"):
                task.completed = request.completed

            session.add(task)
            session.commit()
            session.refresh(task)

            return tasks_pb2.TaskResponse(
                task=task_to_proto(task),
                error="",
            )

    def DeleteTask(self, request, context):
        with Session(engine) as session:
            task = session.get(Task, request.id)

            if task is None:
                return tasks_pb2.DeleteTaskResponse(
                    success=False,
                    error="Task not found",
                )

            session.delete(task)
            session.commit()

            return tasks_pb2.DeleteTaskResponse(
                success=True,
                error="",
            )


def serve():
    create_dbtables()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tasks_pb2_grpc.add_TaskServiceServicer_to_server(TaskService(), server)

    server.add_insecure_port("[::]:50051")
    server.start()

    print("gRPC server running on port 50051")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()