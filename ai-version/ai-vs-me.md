## AI vs me (Stage 7 bonus)

### My prompt (written from memory, no copying from the assignment)

> I want you to build a small CRUD API for managing a to-do list using Python and FastAPI. The data should be stored in a simple in-memory list, so there should be no database involved.
> The API should have the main task endpoints: `GET /tasks` to get all tasks, `GET /tasks/{id}` to get one specific task, `POST /tasks` to create a new task, `PUT /tasks/{id}` to update an existing task, and `DELETE /tasks/{id}` to delete a task.
> Please use the appropriate HTTP status codes. Successful reads and updates should return `200`, creating a task should return `201`, and a successful delete should return `204` with no response body. If the request data is invalid, such as when the title is missing or empty, return `400`. If someone tries to access, update, or delete a task that doesn't exist, return `404` with a clear error message.
> For validation, the task title should be required and must not be empty. Each task can have an ID, a title, and a `done` status.
> Since this is a FastAPI project, make sure the API is properly documented and available through Swagger UI at `/docs`. I should be able to test all the endpoints using the interactive Swagger documentation.

### 1. What did the AI do better?

- Used a Pydantic `@field_validator` to strip and validate the title, which is a cleaner pattern than my manual `if not title.strip()` check inside the route function.
- Defined a separate `Task` response model (inheriting from `TaskCreate` and adding `id`), which gives FastAPI proper response typing and better auto-generated docs than my plain dictionaries.
- Used `status.HTTP_200_OK` style constants instead of raw numbers like `200` — more readable, same result.

I understand its version well enough to explain all of it — the validator decorator and the response model are both standard FastAPI patterns I recognized from the framework docs, just not ones I'd used myself yet.

### 2. What did it get wrong or quietly ignore from my prompt?

- **Biggest issue:** my prompt explicitly said "if the title is missing or empty, return `400`." The AI's code returns **`422`** instead, because it validates with a Pydantic `field_validator` that raises inside the schema — FastAPI's default behavior converts any Pydantic validation error to 422, not 400. Confirmed with curl:
  ```
  POST /tasks {"title":""} → 422 (not 400)
  ```
  To the AI's credit, it *told me this directly* in its own explanation and said I'd need a custom exception handler to get 400 — it didn't pretend the spec was fully met.
- It silently dropped the `GET /` and `GET /health` endpoints — I never mentioned them, so this isn't wrong, just an omission on my part it didn't flag.
- No seed data — its `tasks` list starts empty (`tasks = []`), while mine pre-fills 3 example tasks. I never specified seed data either way.

### 3. What did my prompt forget to specify, and what did the AI decide for me?

- I never said whether tasks should start empty or pre-seeded — it silently chose empty.
- I never specified the exact JSON key for error messages — it used `"detail"`, same convention FastAPI defaults to (matches what my own code does too).
- I never asked for extras (filtering, search, stats, reset) — it didn't add any, which is reasonable since I didn't ask.
- I didn't specify how `id` should be generated — it used the same auto-increment approach I did, so no conflict there, but it was left to the AI's judgment.

### Rematch

I sent a follow-up correction: *"Return 400 specifically — do not rely on FastAPI's default Pydantic validation errors (422); validate the title manually in the route (or add a custom exception handler for RequestValidationError) so an empty or missing title returns 400, not 422."*

**Result:** the AI returned code that was byte-for-byte identical to its first attempt — no exception handler, no manual validation change. I tested it directly with curl against the regenerated file and confirmed the empty-title case still returns `422`, not `400`.

This was the most interesting outcome of the whole exercise: even after the AI correctly diagnosed the problem in its own explanation of the first version, a plain-language follow-up instruction wasn't enough to make it actually change the code. It's a reminder that an AI acknowledging an issue in conversation doesn't guarantee the next code output reflects that acknowledgment — the fix has to be verified by running the code, not by trusting the AI's explanation.
