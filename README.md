# Task API

A small CRUD API for managing a to-do list, built with FastAPI. Data is stored in memory (no database) — it resets when the server restarts.

## Run it

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install fastapi uvicorn
uvicorn main:app --port 8000 --reload
```

Then open:
- API root: http://localhost:8000/
- Interactive docs (Swagger UI): http://localhost:8000/docs

## Endpoints

| Method | Path              | Description                          | Success | Errors  |
|--------|-------------------|---------------------------------------|---------|---------|
| GET    | `/`               | API description                       | 200     | —       |
| GET    | `/health`         | Health check                          | 200     | —       |
| GET    | `/tasks`          | List all tasks (supports `?done=` and `?search=`) | 200 | — |
| POST   | `/tasks`          | Create a task (`{"title": "..."}`)    | 201     | 400 (missing/empty title) |
| GET    | `/tasks/{id}`     | Get one task                          | 200     | 404 (not found) |
| PUT    | `/tasks/{id}`     | Update a task's title and/or done     | 200     | 400, 404 |
| DELETE | `/tasks/{id}`     | Delete a task                         | 204     | 404 |
| GET    | `/stats`          | Task counts (`total`, `done`, `open`) | 200     | — |
| POST   | `/reset`          | Reset to the 3 seed tasks             | 200     | — |

## Example request

```
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Buy milk\"}"
```

```
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

All endpoints listed and testable via "Try it out":

![Endpoints](screenshots/api-end-poinr.PNG)

Full CRUD cycle tested through Swagger UI, including validation and error handling:

**Create (201)**
![Create success](screenshots/post-task-1.2.PNG)

**Create with missing title (400)**
![Create validation error](screenshots/post-task-2.2.PNG)

**Read unknown id (404)**
![Not found](screenshots/get-task-1.2.PNG)

**Update (200)**
![Update success](screenshots/put-task-1.2.PNG)

**Delete (204)**
![Delete success](screenshots/delete-task-1.2.PNG)

## Notes

- Data is in-memory only — restarting the server resets it back to the 3 seed tasks (or call `POST /reset` any time).
- FastAPI's default validation returns 422 for missing required fields. Since the spec asks for 400 on invalid input, `title` is defined as optional in the schema and validated manually in the route, so a missing/empty title returns 400 instead of FastAPI's default 422.
