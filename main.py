from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI(title="Task API", version="2.0")

"""
Task API — SQLite-backed CRUD service for managing a to-do list.
Same endpoints as Assignment 1; only the storage layer changed (memory -> tasks.db).
Endpoints: GET /, GET /health, GET/POST /tasks, GET/PUT/DELETE /tasks/{id}, GET /stats, POST /reset.
"""

DB_FILE = "tasks.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()

    # Seed only if the table is empty
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        seed = [
            ("Buy milk", 0),
            ("Write README", 0),
            ("Push to GitHub", 1),
        ]
        conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", seed)
        conn.commit()
    conn.close()


init_db()


def row_to_task(row):
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


# ---- Schemas ----
class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


# ---- Root & health ----
@app.get("/")
def root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- Read ----
@app.get("/tasks")
def list_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    conn = get_conn()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)
    if search is not None:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


# ---- Create ----
@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    conn = get_conn()
    cur = conn.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (task.title, 0))
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return row_to_task(row)


# ---- Update & Delete ----
@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = row["title"]
    new_done = row["done"]

    if update.title is not None:
        if not update.title.strip():
            conn.close()
            raise HTTPException(status_code=400, detail="title cannot be empty")
        new_title = update.title
    if update.done is not None:
        new_done = 1 if update.done else 0

    conn.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (new_title, new_done, task_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row_to_task(updated)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return


# ---- Extras ----
@app.get("/stats")
def stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    conn.close()
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset")
def reset():
    conn = get_conn()
    conn.execute("DELETE FROM tasks")
    conn.commit()
    seed = [
        ("Buy milk", 0),
        ("Write README", 0),
        ("Push to GitHub", 1),
    ]
    conn.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", seed)
    conn.commit()
    conn.close()
    return {"status": "reset"}