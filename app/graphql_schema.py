import strawberry
from sqlmodel import Session, select
from typing import Optional

from app.database import engine
from app.models import Task


@strawberry.type
class TaskType:
    id: int
    title: str
    completed: bool


@strawberry.input
class TaskCreateInput:
    title: str
    completed: bool = False


@strawberry.input
class TaskUpdateInput:
    title: Optional[str] = None
    completed: Optional[bool] = None


def task_to_type(task: Task) -> TaskType:
    if task.id is None:
        raise ValueError("Task id cannot be None after database save")

    return TaskType(
        id=task.id,
        title=task.title,
        completed=task.completed,
    )


@strawberry.type
class Query:
    @strawberry.field
    def tasks(self) -> list[TaskType]:
        with Session(engine) as session:
            statement = select(Task)
            tasks = session.exec(statement).all()
            return [task_to_type(task) for task in tasks]

    @strawberry.field
    def task(self, task_id: int) -> Optional[TaskType]:
        with Session(engine) as session:
            task = session.get(Task, task_id)

            if task is None:
                return None

            return task_to_type(task)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_task(self, task: TaskCreateInput) -> TaskType:
        with Session(engine) as session:
            new_task = Task(
                title=task.title,
                completed=task.completed,
            )

            session.add(new_task)
            session.commit()
            session.refresh(new_task)

            return task_to_type(new_task)

    @strawberry.mutation
    def update_task(self, task_id: int,
                    task: TaskUpdateInput) -> Optional[TaskType]:
        with Session(engine) as session:
            existing_task = session.get(Task, task_id)

            if existing_task is None:
                return None

            if task.title is not None:
                existing_task.title = task.title

            if task.completed is not None:
                existing_task.completed = task.completed

            session.add(existing_task)
            session.commit()
            session.refresh(existing_task)

            return task_to_type(existing_task)

    @strawberry.mutation
    def delete_task(self, task_id: int) -> bool:
        with Session(engine) as session:
            task = session.get(Task, task_id)

            if task is None:
                return False

            session.delete(task)
            session.commit()

            return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
