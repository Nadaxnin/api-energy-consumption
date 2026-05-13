from fastapi import FastAPI, HTTPException  # , status
from pydantic import BaseModel

app = FastAPI()


# basis
tasks = [
    {"id": 1, "title": "first", "completed": False},
    {"id": 2, "title": "second", "completed": False},
    {"id": 3, "title": "third", "completed": False}
]


# output model API -> server
class Task(BaseModel):
    id: int
    title: str
    completed: bool


# input model  server -> API
class TaskCreate(BaseModel):
    title: str
    completed: bool = False


class TaskUpdate (BaseModel):
    completed: bool


@app.get("/")
async def root():
    return {"message": "You are at the root"}


@app.get("/tasks", response_model=list[Task])
async def get_tasks():
    return tasks


@app.get("/taskslength")
async def get_tasks_length():
    return len(tasks)


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/tasks", response_model=Task)
async def create_task(task: TaskCreate):
    for ex_task in tasks:
        if (
            ex_task["title"] == task.title
            and ex_task["completed"] == task.completed
        ):
            raise HTTPException(status_code=409, detail="Task already created")
    new_id = max(t["id"] for t in tasks) + 1 if tasks else 1

    new_task = {
        "id": new_id,
        "title": task.title,
        "completed": task.completed
    }
    tasks.append(new_task)
    return new_task


@app.patch("/tasks/{task_id}", response_model=Task)
async def patch_task(task_id: int, upd_task: TaskUpdate):
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = upd_task.completed
            return task
    raise HTTPException(status_code=404, detail="Task not found")


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return {"message": "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")
