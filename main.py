import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from supabase_client import supabase
from supabase_auth.errors import AuthApiError
from auth import get_current_user, get_current_token

load_dotenv()

app = FastAPI(title="Task API", version="3.0")

"""
Task API — Postgres-backed CRUD service for managing a to-do list.
Same endpoints as Assignments 1 and 2; only the storage layer changed again
(memory -> SQLite -> Postgres in Docker). Endpoints: GET /, GET /health,
GET/POST /tasks, GET/PUT/DELETE /tasks/{id}, GET /stats, POST /reset.
"""

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres:dev@localhost:5432/tasks")


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            conn.commit()

            cur.execute("SELECT COUNT(*) AS count FROM tasks")
            count = cur.fetchone()["count"]
            if count == 0:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Buy milk", False),
                        ("Write README", False),
                        ("Push to GitHub", True),
                    ],
                )
                conn.commit()


@app.on_event("startup")
def on_startup():
    init_db()
    # supabase_client.py raises on import if SUPABASE_URL/SUPABASE_KEY are
    # missing, so reaching this line means the client is ready to use.
    print("Server running and connected to Supabase")


def row_to_task(row):
    return {"id": row["id"], "title": row["title"], "done": row["done"]}


# ---- Schemas ----
class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class AuthCredentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


# ---- Root & health ----
@app.get("/")
def root():
    return {"name": "Task API", "version": "3.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "ok", "db": "ok"}
    except Exception:
        return {"status": "ok", "db": "unreachable"}


# ---- Auth ----
@app.post("/auth/signup", status_code=201)
def signup(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="email and password are required")

    try:
        result = supabase.auth.sign_up(
            {"email": credentials.email, "password": credentials.password}
        )
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"user": result.user.model_dump(mode="json") if result.user else None}


@app.post("/auth/login")
def login(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="email and password are required")

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": credentials.email, "password": credentials.password}
        )
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "user": result.user.model_dump(mode="json") if result.user else None,
    }


# ---- Public & protected gates ----
@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@app.get("/protected/dashboard")
def protected_dashboard(user=Depends(get_current_user)):
    # Second protected route reusing the exact same dependency — no new
    # auth code, proving the guard generalizes to any route.
    return {"message": f"Welcome to your dashboard, {user.email}."}


@app.post("/auth/logout", status_code=204)
def logout(token: str = Depends(get_current_token)):
    try:
        supabase.auth.admin.sign_out(token, "global")
    except AuthApiError:
        # Token was already invalid/expired — logout is a no-op either way,
        # the end state (no valid session) is the same.
        pass
    return


# ---- Read ----
@app.get("/tasks")
def list_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if done is not None:
        query += " AND done = %s"
        params.append(done)
    if search is not None:
        query += " AND title ILIKE %s"
        params.append(f"%{search}%")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


# ---- Create ----
@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
                (task.title, False),
            )
            row = cur.fetchone()
            conn.commit()
    return row_to_task(row)


# ---- Update & Delete ----
@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

            new_title = row["title"]
            new_done = row["done"]

            if update.title is not None:
                if not update.title.strip():
                    raise HTTPException(status_code=400, detail="title cannot be empty")
                new_title = update.title
            if update.done is not None:
                new_done = update.done

            cur.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
                (new_title, new_done, task_id),
            )
            updated = cur.fetchone()
            conn.commit()
    return row_to_task(updated)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            conn.commit()
    return


# ---- Extras ----
@app.get("/stats")
def stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM tasks")
            total = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS done FROM tasks WHERE done = TRUE")
            done = cur.fetchone()["done"]
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset")
def reset():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks")
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                [
                    ("Buy milk", False),
                    ("Write README", False),
                    ("Push to GitHub", True),
                ],
            )
            conn.commit()
    return {"status": "reset"}
