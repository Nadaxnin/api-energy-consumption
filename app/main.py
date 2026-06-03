from fastapi import FastAPI, HTTPException, status
from contextlib import asynccontextmanager
from sqlmodel import select

from app.database import create_dbtables, SessionDep
from app.models import Task
from app.schemas import TaskCreate, TaskUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("starting...")
    create_dbtables()
    yield
    print("shutting down...")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "You are at the root"}


@app.get("/tasks", response_model=list[Task])
async def get_tasks(session: SessionDep):
    statement = select(Task)
    tasks = session.exec(statement).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, session: SessionDep):
    statement = select(Task).where(Task.title == task.title)
    existing_task = session.exec(statement).first()

    if existing_task is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already exists",
        )

    new_task = Task(
        title=task.title,
        completed=task.completed,
    )

    session.add(new_task)
    session.commit()
    session.refresh(new_task)

    return new_task


@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int,
                      updated_task: TaskUpdate, session: SessionDep):
    task = session.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = updated_task.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(task, key, value)

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, session: SessionDep):
    task = session.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    session.delete(task)
    session.commit()

    return {"message": "Task deleted"}
