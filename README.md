# AI Food Analyzer — API Prototype (Assignment 2)

**Group 5 · CSCI 3509 Intro to Software Engineering · ADA University · Fall 2026**

First functional prototype of the AI Food Analyzer backend: a FastAPI REST API around the main resource meals (analyzed meal photos with ingredients and nutrition), using mocked in-memory data instead of PostgreSQL, mock bearer tokens with role-based access, structured validation/error responses, and an HTML greeting page.

| | |
|---|---|
| API documentation | [`docs/API.md`](docs/API.md)  |
| Postman collection | [`postman/AI_Food_Analyzer.postman_collection.json`](postman/AI_Food_Analyzer.postman_collection.json) |
| Greeting page | `http://localhost:8000/api/v1/greeting` |
| Demo video | `<YouTube link>` |
| Contributors | [`CONTRIBUTORS.md`](CONTRIBUTORS.md) |

## Requirements

- Python 3.10 or newer (we used 3.12)
- Git

## Install and run

```bash
# 1. Clone
git clone https://github.com/<org-or-user>/ai-food-analyzer-api.git
cd ai-food-analyzer-api

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload
```

The API now runs at **http://localhost:8000**. Open:

- http://localhost:8000/api/v1/greeting — HTML greeting page
- http://localhost:8000/docs — interactive Swagger UI (click an endpoint → *Try it out*; put `Bearer user-a-token` in the `authorization` field)

## Mock data and tokens

Data is stored in memory. Every create/update/delete is lost when the server restarts, and the server starts again with the seed data below. Restart the server to reset the demo.

| Token | User | Can do |
|---|---|---|
| `user-a-token` | `user-a` | only their own meals |
| `user-b-token` | `user-b` | only their own meals |
| `admin-token` | `admin` | all meals |

Seed meals: `meal_101`, `meal_102` (user A); `meal_103`, `meal_104`, `meal_105` (user B, `meal_105` is an *unknown* meal).

## Quick test with curl

```bash
# list my meals
curl -H "Authorization: Bearer user-a-token" http://localhost:8000/api/v1/meals

# create a meal
curl -X POST http://localhost:8000/api/v1/meals \
  -H "Authorization: Bearer user-a-token" -H "Content-Type: application/json" \
  -d '{"title":"Chicken salad","mealType":"lunch","eatenAt":"2026-11-18T13:05:00Z","imagePath":"uploads/user-a/chicken-salad.jpg","ingredients":[{"name":"chicken breast","grams":120,"confidence":0.93},{"name":"lettuce","grams":60,"confidence":0.81}]}'

# no token -> 401
curl -i http://localhost:8000/api/v1/meals

# user A reads user B's meal -> 404
curl -i -H "Authorization: Bearer user-a-token" http://localhost:8000/api/v1/meals/meal_103
```

(On Windows PowerShell use `curl.exe` and escape the inner quotes, or just use Postman.)

## Postman

1. Postman → Import → choose `postman/AI_Food_Analyzer.postman_collection.json`.
2. Start the server.
3. Right-click the collection → Run collection → Run. All requests have tests that check the status code and error code (39 requests).
4. Restart the server before running the collection again (the run changes the mock data).

## Run the automated tests

```bash
pytest -q
```

36 tests cover CRUD, 401/403/404/405/409 cases, validation and the greeting page.

## Project structure

```
app/
  main.py            FastAPI app, routers, exception handlers
  config.py          project info, team, endpoint list (edit student IDs here)
  errors.py          response envelope, error codes, global error handlers
  auth.py            mock users + tokens, Bearer authentication, ownership check
  nutrition.py       mock nutrition table (stands in for USDA FoodData Central)
  store.py           in-memory meal store + seed data
  validation.py      body and query validation
  routers/
    meals.py         GET/POST/PUT/DELETE /api/v1/meals
    greeting.py      GET /api/v1/greeting (HTML)
    health.py        GET /api/v1/health
  templates/greeting.html
docs/API.md          full API documentation
postman/             Postman collection
tests/               pytest suite
```

## Who worked on what

| Member | Parts of the system |
|---|---|
| Gulay Mehraliyeva | Mock data and nutrition calculation, validation rules, meal CRUD endpoints, CRUD/validation tests, API documentation |
| Araz Valishov | Project setup, response envelope and error handling, token authentication and role checks, HTML greeting page, health check, auth tests, Postman collection, README |

## Git contribution summary

Output of `git shortlog -sn --all`:

```
<paste the output here after all work is merged>
```

Workflow: every feature was developed on its own branch (`feature/...`) and merged into `main` through a pull request reviewed by the other member.
