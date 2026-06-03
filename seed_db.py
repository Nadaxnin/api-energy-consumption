from sqlmodel import Session, select

from app.database import engine, create_dbtables
from app.models import Task


def seed_database():
    create_dbtables()

    with Session(engine) as session:
        existing_tasks = session.exec(select(Task)).all()

        if existing_tasks:
            print("Database already has data.")
            return

        tasks = []

        for i in range(1, 101):
            task = Task(
                title=f"Task {i}",
                completed=False,
            )
            tasks.append(task)

        session.add_all(tasks)
        session.commit()

        print("Added 100 tasks.")


if __name__ == "__main__":
    seed_database()
