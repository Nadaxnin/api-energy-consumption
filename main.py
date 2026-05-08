from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

#basis
tasks = [
    {"id": 1, "title": "first", "completed": False},
    {"id": 2, "title": "second", "completed": False},
    {"id": 3, "title": "third", "completed": False}
]
#output model API -> server
class Task(BaseModel):
    id: int
    title: str
    completed: bool

#input model  server -> API
class TaskCreate(BaseModel):
    title: str
    completed: bool

class TaskUpdate (BaseModel):
    completed: bool

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    if len(tasks) == 0:
        raise HTTPException(status_code=400, detail="no tasks left")
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return {"message" : "Task deleted"}
    raise HTTPException(status_code=404, detail="Task not found")

@app.patch("/tasks/{task_id}")
async def patch_task(task_id: int, upd_task: TaskUpdate): 
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = upd_task.completed
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/tasks")
async def create_task(task: TaskCreate):
    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "completed": task.completed
    }
    if new_task["title"] == tasks[-1]["title"] and new_task["completed"] == tasks[-1]["completed"]:
        raise HTTPException(status_code=409, detail="Task already created")
    tasks.append(new_task)
    return new_task

@app.get("/")
async def root():
    return {"message": "You are at the root"}

@app.get("/tasks")
async def get_tasks():
    return tasks

@app.get("/taskslength")
async def get_tasks_length():
    return len(tasks)

@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

