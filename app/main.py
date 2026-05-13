from fastapi import FastAPI # HTTPException  # , status
from contextlib import asynccontextmanager
from sqlmodel import select

from app.database import create_dbtables, SessionDep
from app.models import Task
# from app.schemas import TaskCreate, TaskUpdate


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


# @app.get("/taskslength")
# async def get_tasks_length():
#     return len(tasks)


# @app.get("/tasks/{task_id}", response_model=Task)
# async def get_task(task_id: int):

#     for task in tasks:
#         if task.id == task_id:
#             return task
#     raise HTTPException(status_code=404, detail="Task not found")


# @app.post("/tasks", response_model=Task)
# async def create_task(session: SessionDep):
#     statement = select(Task)
#     # was here last!!!!!


#     for ex_task in tasks:
#         if (
#             ex_task["title"] == task.title
#             and ex_task["completed"] == task.completed
#         ):
#             raise HTTPException(status_code=409,
#            detail="Task already created")
#     new_id = max(t["id"] for t in tasks) + 1 if tasks else 1

#     new_task = {
#         "id": new_id,
#         "title": task.title,
#         "completed": task.completed
#     }
#     tasks.append(new_task)
#     return new_task


# @app.patch("/tasks/{task_id}", response_model=Task)
# async def patch_task(task_id: int, upd_task: TaskUpdate):
#     for task in tasks:
#         if task["id"] == task_id:
#             task["completed"] = upd_task.completed
#             return task
#     raise HTTPException(status_code=404, detail="Task not found")


# @app.delete("/tasks/{task_id}")
# async def delete_task(task_id: int):
#     for task in tasks:
#         if task["id"] == task_id:
#             tasks.remove(task)
#             return {"message": "Task deleted"}
#     raise HTTPException(status_code=404, detail="Task not found")
