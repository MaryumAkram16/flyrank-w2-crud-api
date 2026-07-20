from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import List


app = FastAPI(
    title="To-Do List API",
    description="A simple CRUD API for managing tasks using in-memory storage.",
    version="1.0.0"
)


# In-memory storage
tasks = []
next_id = 1


# Request model
class TaskCreate(BaseModel):
    title: str
    done: bool = False

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str):
        if not value.strip():
            raise ValueError("Title cannot be empty")
        return value.strip()


# Response model
class Task(TaskCreate):
    id: int


# GET /tasks
@app.get("/tasks", response_model=List[Task], status_code=status.HTTP_200_OK)
def get_tasks():
    return tasks


# GET /tasks/{id}
@app.get("/tasks/{id}", response_model=Task, status_code=status.HTTP_200_OK)
def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {id} not found"
    )


# POST /tasks
@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate):
    global next_id

    new_task = {
        "id": next_id,
        "title": task_data.title,
        "done": task_data.done
    }

    tasks.append(new_task)
    next_id += 1

    return new_task


# PUT /tasks/{id}
@app.put("/tasks/{id}", response_model=Task, status_code=status.HTTP_200_OK)
def update_task(id: int, task_data: TaskCreate):
    for task in tasks:
        if task["id"] == id:
            task["title"] = task_data.title
            task["done"] = task_data.done
            return task

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {id} not found"
    )


# DELETE /tasks/{id}
@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int):
    for index, task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(index)
            return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {id} not found"
    )
