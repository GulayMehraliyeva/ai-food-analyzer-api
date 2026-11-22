# AI Food Analyzer — API Prototype (Assignment 2)

**Group 5 · CSCI 3509 Intro to Software Engineering · ADA University · Fall 2026**

First functional prototype of the AI Food Analyzer backend: a FastAPI REST API around the main resource **meals** (analyzed meal photos with ingredients and nutrition). It uses mocked in-memory data instead of PostgreSQL, mock bearer tokens with role-based access, structured validation/error responses, and an HTML greeting page.

| | |
|---|---|
| API documentation | [`docs/API.md`](docs/API.md) |
| Postman collection | [`postman/AI_Food_Analyzer.postman_collection.json`](postman/AI_Food_Analyzer.postman_collection.json) |
| Greeting page | `http://localhost:8000/api/v1/greeting` |
| Swagger UI | `http://localhost:8000/docs` |
| Demo video | `<YouTube link>` |
| Contributors | [`CONTRIBUTORS.md`](CONTRIBUTORS.md) |

## Requirements

- Python 3.10 or newer (we used 3.12)
- Git

## Install and run

```bash
# 1. Clone
git clone https://github.com/GulayMehraliyeva/ai-food-analyzer-api.git
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
- http://localhost:8000/docs — interactive Swagger UI (see [Authentication](#authentication) for how to log in with a mock token)

## Authentication

There is no real login or password storage. The API uses three predefined mock tokens, sent as a Bearer token on every request except `GET /api/v1/greeting` and `GET /api/v1/health`:

```http
Authorization: Bearer user-a-token
```

| Token | User (`ownerId`) | Role | Permissions |
|---|---|---|---|
| `user-a-token` | `user-a` | user | Read, create, update and delete **only their own** meals |
| `user-b-token` | `user-b` | user | Read, create, update and delete **only their own** meals |
| `admin-token` | `admin` | admin | Read, update and delete **all** meals; can create a meal for any user; can filter the list by `ownerId` |

### Using a token in Swagger UI (`/docs`)

Swagger UI uses an HTTP Bearer security scheme, so it adds the `Bearer ` prefix for you:

1. Open http://localhost:8000/docs and click the green **Authorize** button (top right).
2. In the *HTTPBearer* field enter **only the token**, for example `user-a-token` (do **not** type `Bearer `).
3. Click **Authorize**, then **Close**. Every *Try it out* request now sends `Authorization: Bearer user-a-token`.
4. To switch user, click **Authorize** again, choose **Logout**, and authorize with another token.

With curl or Postman you must send the full header yourself: `Authorization: Bearer user-a-token`.

### Authentication and authorization results

| Situation | Status | `error.code` |
|---|---|---|
| No `Authorization` header | `401` | `UNAUTHORIZED` |
| Header is not in the form `Bearer <token>` | `401` | `INVALID_TOKEN` |
| Unknown or invalid token | `401` | `INVALID_TOKEN` |
| Regular user reads, updates or deletes another user's meal | `404` | `NOT_FOUND` |
| Regular user creates a meal with another user's `ownerId` | `403` | `FORBIDDEN` |
| Regular user lists meals with `?ownerId=` of another user | `403` | `FORBIDDEN` |
| Administrator accesses any meal | `200` / `201` | — |

All `401` responses include the header `WWW-Authenticate: Bearer`.

**Why `404` and not `403` for other users' meals:** meal history is private data. A `403` would confirm that the ID exists and belongs to someone else, which lets a user discover other people's meal IDs. A `404` is identical to the answer for an ID that does not exist, so nothing is revealed. We still use `403` where nothing hidden is exposed (creating a meal for another user, filtering the list by another user's `ownerId`). Details: [`docs/API.md`, section 8.1](docs/API.md#81-404-instead-of-403-for-other-users-meals).

## Mock data

Data is stored in memory. **Every create/update/delete is lost when the server restarts**, and the server starts again with the seed data below. Restart the server to reset the demo.

| Meal | Owner | Notes |
|---|---|---|
| `meal_101`, `meal_102` | user A | |
| `meal_103`, `meal_104` | user B | |
| `meal_105` | user B | *unknown* meal (no ingredients recognised) |
| `meal_999` | — | does **not** exist; use it to demonstrate `404 Not Found` |

The administrator can see all five meals.

## Quick test with curl

```bash
# list my meals
curl -H "Authorization: Bearer user-a-token" http://localhost:8000/api/v1/meals

# create a meal
curl -X POST http://localhost:8000/api/v1/meals \
  -H "Authorization: Bearer user-a-token" -H "Content-Type: application/json" \
  -d '{"title":"Chicken salad","mealType":"lunch","eatenAt":"2026-11-18T13:05:00Z","imagePath":"uploads/user-a/chicken-salad.jpg","ingredients":[{"name":"chicken breast","grams":120,"confidence":0.93},{"name":"lettuce","grams":60,"confidence":0.81}]}'

# no token -> 401 UNAUTHORIZED
curl -i http://localhost:8000/api/v1/meals

# invalid token -> 401 INVALID_TOKEN
curl -i -H "Authorization: Bearer wrong-token" http://localhost:8000/api/v1/meals

# user A reads user B's meal -> 404
curl -i -H "Authorization: Bearer user-a-token" http://localhost:8000/api/v1/meals/meal_103

# admin reads user B's meal -> 200
curl -i -H "Authorization: Bearer admin-token" http://localhost:8000/api/v1/meals/meal_103
```

(On Windows PowerShell use `curl.exe` and escape the inner quotes, or just use Postman.)

## Postman

1. Postman → Import → choose `postman/AI_Food_Analyzer.postman_collection.json`.
2. Start the server.
3. Right-click the collection → Run collection → Run. All 39 requests have tests that check the status code and error code. Tokens are collection variables (`userAToken`, `userBToken`, `adminToken`).
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
  config.py          project info, team, endpoint list (shown on the greeting page)
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
| Gulay Mehraliyeva | Project config and `.gitignore`, JSON response envelope and error handlers (`app/errors.py`), FastAPI entry point (`app/main.py`), mock data and nutrition table (`app/nutrition.py`, `app/store.py`), mock users and Bearer token authentication including the Swagger Bearer scheme (`app/auth.py`), README |
| Araz Valishov | Request and query validation (`app/validation.py`), meal CRUD endpoints (`app/routers/meals.py`), HTML greeting page, `405` `Allow` header handling, shared test fixtures (`tests/conftest.py`), validation tests, auth tests, other tests, health endpoint, Postman collection, API documentation (`docs/API.md`) |

## Git contribution summary

Output of `git shortlog -sn --all`:


Workflow: features were developed on their own branches (`feature/...`, `docs/...`) and merged into `main` through pull requests.
