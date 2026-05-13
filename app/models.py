from sqlmodel import Field, SQLModel


# output model API -> server, primary key = id
class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    completed: bool = False
