from pydantic import BaseModel


# input model  server -> API
class TaskCreate(BaseModel):
    title: str
    completed: bool = False


class TaskUpdate(BaseModel):
    completed: bool
