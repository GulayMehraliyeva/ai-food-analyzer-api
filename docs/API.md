# AI Food Analyzer — API Documentation (v1)

Base URL (local): `http://localhost:8000`
All API paths start with `/api/v1`. Interactive Swagger UI: `http://localhost:8000/docs`.

## Contents

1. [Main resource: Meal](#1-main-resource-meal)
2. [Authentication and authorization](#2-authentication-and-authorization)
3. [Response envelope](#3-response-envelope)
4. [Error codes](#4-error-codes)
5. [Endpoints](#5-endpoints)
   - [GET /api/v1/meals](#51-list-meals) · [GET /api/v1/meals/{id}](#52-get-one-meal) · [POST /api/v1/meals](#53-create-a-meal) · [PUT /api/v1/meals/{id}](#54-replace-a-meal) · [DELETE /api/v1/meals/{id}](#55-delete-a-meal) · [GET /api/v1/greeting](#56-html-greeting-page) · [GET /api/v1/health](#57-health-check)
6. [Validation rules](#6-validation-rules)
7. [Mock data](#7-mock-data)
8. [Design decisions](#8-design-decisions)

---

## 1. Main resource: Meal

A **meal** is one analyzed meal photo: the ingredients the AI recognised (name, grams, confidence) plus the nutrition the server calculated from them. It maps to FR-01, FR-04, FR-05, FR-08, FR-11 and FR-12 of our Assignment 1 proposal.

| Field | Type | Set by | Description |
|---|---|---|---|
| `id` | string | server | `meal_<number>`, e.g. `meal_101` |
| `ownerId` | string | server (admin may choose on create) | `user-a`, `user-b` or `admin` |
| `title` | string | client | Short name of the meal |
| `mealType` | string | client | `breakfast`, `lunch`, `dinner` or `snack` |
| `eatenAt` | string (ISO 8601, UTC) | client | When the meal was eaten |
| `imagePath` | string | client | Path of the uploaded photo (`.jpg`, `.jpeg`, `.png`) |
| `notes` | string \| null | client | Optional note |
| `ingredients[]` | array | client + server | `name`, `grams`, `confidence` from the client; `calories`, `protein`, `carbs`, `fat` added by the server |
| `status` | string | server | `analyzed`, or `unknown` when `ingredients` is empty (FR-05) |
| `totals` | object | server | Sum of `calories`, `protein`, `carbs`, `fat` for the meal (FR-04) |
| `createdAt`, `updatedAt` | string | server | ISO 8601 UTC timestamps |

In the real system the ingredients come from the vision-language model and nutrition from USDA FoodData Central. In this prototype the client sends the ingredients and the server uses a built-in mock nutrition table (`app/nutrition.py`, values per 100 g).

## 2. Authentication and authorization

Send a predefined mock token on every request except `/greeting` and `/health`:

```http
Authorization: Bearer user-a-token
```

| User | `ownerId` | Token | Role | Permissions |
|---|---|---|---|---|
| Demo User A | `user-a` | `user-a-token` | user | Read, create, update and delete **only their own** meals |
| Demo User B | `user-b` | `user-b-token` | user | Read, create, update and delete **only their own** meals |
| Administrator | `admin` | `admin-token` | admin | Read, update and delete **all** meals; can create a meal for any user; can filter the list by `ownerId` |

| Situation | Result |
|---|---|
| No `Authorization` header | `401 UNAUTHORIZED` |
| Header not in the form `Bearer <token>` | `401 INVALID_TOKEN` |
| Unknown token | `401 INVALID_TOKEN` |
| Regular user reads/updates/deletes another user's meal | `404 NOT_FOUND` (see [8.1](#81-404-instead-of-403-for-other-users-meals)) |
| Regular user creates a meal with someone else's `ownerId` | `403 FORBIDDEN` |
| Regular user lists with `?ownerId=` of another user | `403 FORBIDDEN` |

All `401` responses include the header `WWW-Authenticate: Bearer`.

**Check order** for every protected request: 1) authentication (401) → 2) resource exists and is yours (404) → 3) body/query validation (400) → 4) permission for the requested action (403) → 5) conflict (409).

## 3. Response envelope

Every JSON response uses one of two shapes. The HTTP status always matches: `2xx` ⇔ `success: true`, `4xx/5xx` ⇔ `success: false`.

**Success**

```json
{
  "success": true,
  "message": "Meal retrieved successfully.",
  "data": { "id": "meal_101", "...": "..." }
}
```

- `data` is a meal object, an array of meals (list), or `null` (delete).
- List responses also have `meta`: `{ "total": 2, "page": 1, "perPage": 10, "totalPages": 1 }`.

**Error**

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid or missing fields.",
    "details": [
      { "field": "title", "message": "title must contain between 3 and 100 characters." }
    ]
  }
}
```

- `details` appears **only** for `VALIDATION_ERROR`. It lists **every** invalid field at once, not just the first one.
- Error messages never contain stack traces, file paths or other internal details. Unexpected errors are logged on the server and the client gets a generic `500 INTERNAL_ERROR`.

## 4. Error codes

| HTTP | `error.code` | When |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Missing/invalid body fields, unknown or read-only fields, invalid query parameters, empty body |
| 400 | `INVALID_JSON` | Body is not parseable JSON |
| 401 | `UNAUTHORIZED` | `Authorization` header missing |
| 401 | `INVALID_TOKEN` | Header malformed or token unknown |
| 403 | `FORBIDDEN` | Authenticated but not allowed (create for another user, list another user's meals) |
| 404 | `NOT_FOUND` | Meal ID does not exist, or belongs to another user |
| 404 | `ENDPOINT_NOT_FOUND` | URL does not exist (e.g. `/api/v1/getMeals`) |
| 405 | `METHOD_NOT_ALLOWED` | Method not supported on that path (response has an `Allow` header) |
| 409 | `CONFLICT` | Same owner already has a meal with the same `title` and `eatenAt` |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

## 5. Endpoints

### Common headers

| Header | Required on | Value |
|---|---|---|
| `Authorization` | all `/meals` endpoints | `Bearer user-a-token` \| `Bearer user-b-token` \| `Bearer admin-token` |
| `Content-Type` | `POST`, `PUT` | `application/json` |

---

### 5.1 List meals

`GET /api/v1/meals`

**Auth:** any valid token. Users get their own meals; admin gets everyone's.

**Query parameters** (all optional)

| Name | Type | Default | Rules |
|---|---|---|---|
| `page` | integer | `1` | 1 – 10000 |
| `perPage` | integer | `10` | 1 – 50 |
| `mealType` | string | — | `breakfast` \| `lunch` \| `dinner` \| `snack` |
| `status` | string | — | `analyzed` \| `unknown` |
| `ownerId` | string | — | `user-a` \| `user-b` \| `admin`. Regular users may only pass their own id |
| `sort` | string | `-eatenAt` | `eatenAt`, `-eatenAt`, `calories`, `-calories`, `createdAt`, `-createdAt` (`-` = descending) |

**Success:** `200 OK`, `data` = array of meals, plus `meta`. A page past the end returns `data: []`.

**Errors:** `400 VALIDATION_ERROR` (bad query), `401`, `403 FORBIDDEN` (`ownerId` of another user, non-admin).

**Example**

```http
GET /api/v1/meals?perPage=1 HTTP/1.1
Authorization: Bearer user-a-token
```

```json
HTTP/1.1 200 OK
{
  "success": true,
  "message": "1 meal(s) returned.",
  "data": [
    {
      "id": "meal_102",
      "ownerId": "user-a",
      "title": "Oatmeal with banana",
      "mealType": "breakfast",
      "eatenAt": "2026-11-18T07:45:00Z",
      "imagePath": "uploads/user-a/oatmeal-banana.png",
      "notes": null,
      "status": "analyzed",
      "ingredients": [
        { "name": "oats", "grams": 60, "confidence": 0.88, "calories": 233.4, "protein": 10.1, "carbs": 39.8, "fat": 4.1 },
        { "name": "banana", "grams": 100, "confidence": 0.95, "calories": 89.0, "protein": 1.1, "carbs": 22.8, "fat": 0.3 },
        { "name": "milk", "grams": 200, "confidence": 0.7, "calories": 122.0, "protein": 6.4, "carbs": 9.6, "fat": 6.6 }
      ],
      "totals": { "calories": 444.4, "protein": 17.6, "carbs": 72.2, "fat": 11.0 },
      "createdAt": "2026-11-18T18:00:00Z",
      "updatedAt": "2026-11-18T18:00:00Z"
    }
  ],
  "meta": { "total": 2, "page": 1, "perPage": 1, "totalPages": 2 }
}
```

Error example — invalid query:

```http
GET /api/v1/meals?page=0&sort=title
Authorization: Bearer user-a-token
```

```json
HTTP/1.1 400 Bad Request
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more query parameters are invalid.",
    "details": [
      { "field": "page", "message": "page must be between 1 and 10000." },
      { "field": "sort", "message": "sort must be one of: eatenAt, -eatenAt, calories, -calories, createdAt, -createdAt." }
    ]
  }
}
```

Error example — user A asks for user B's meals:

```http
GET /api/v1/meals?ownerId=user-b
Authorization: Bearer user-a-token
```

```json
HTTP/1.1 403 Forbidden
{ "success": false, "error": { "code": "FORBIDDEN", "message": "Only an administrator can list meals of other users." } }
```

---

### 5.2 Get one meal

`GET /api/v1/meals/{id}`

**Auth:** owner of the meal, or admin.
**Path parameter:** `id` — meal id, e.g. `meal_101`.

**Success:** `200 OK`, `data` = meal.
**Errors:** `401`, `404 NOT_FOUND` (does not exist **or** belongs to another user).

**Example**

```http
GET /api/v1/meals/meal_101 HTTP/1.1
Authorization: Bearer user-a-token
```

```json
HTTP/1.1 200 OK
{
  "success": true,
  "message": "Meal retrieved successfully.",
  "data": {
    "id": "meal_101",
    "ownerId": "user-a",
    "title": "Chicken rice bowl",
    "mealType": "lunch",
    "eatenAt": "2026-11-17T12:30:00Z",
    "imagePath": "uploads/user-a/chicken-rice-bowl.jpg",
    "notes": "Post-workout lunch.",
    "status": "analyzed",
    "ingredients": [
      { "name": "chicken breast", "grams": 150, "confidence": 0.94, "calories": 247.5, "protein": 46.5, "carbs": 0.0, "fat": 5.4 },
      { "name": "white rice", "grams": 200, "confidence": 0.9, "calories": 260.0, "protein": 5.4, "carbs": 56.4, "fat": 0.6 },
      { "name": "broccoli", "grams": 80, "confidence": 0.82, "calories": 27.2, "protein": 2.2, "carbs": 5.3, "fat": 0.3 }
    ],
    "totals": { "calories": 534.7, "protein": 54.1, "carbs": 61.7, "fat": 6.3 },
    "createdAt": "2026-11-18T18:00:00Z",
    "updatedAt": "2026-11-18T18:00:00Z"
  }
}
```

Error examples:

```http
GET /api/v1/meals/meal_103
Authorization: Bearer user-a-token        ← meal_103 belongs to user B
```

```json
HTTP/1.1 404 Not Found
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Meal 'meal_103' was not found." } }
```

```http
GET /api/v1/meals/meal_999
Authorization: Bearer admin-token         ← does not exist
```

```json
HTTP/1.1 404 Not Found
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Meal 'meal_999' was not found." } }
```

---

### 5.3 Create a meal

`POST /api/v1/meals`

**Auth:** any valid token. The meal is owned by the caller. Admin may set `ownerId` to create a meal for another user.
**Headers:** `Authorization`, `Content-Type: application/json`.

**Body**

| Field | Required | Type | Rules |
|---|---|---|---|
| `title` | yes | string | 3–100 characters (trimmed) |
| `mealType` | yes | string | `breakfast` \| `lunch` \| `dinner` \| `snack` |
| `eatenAt` | yes | string | ISO 8601 with time zone; not in the future |
| `imagePath` | yes | string | 5–255 characters, ends with `.jpg`, `.jpeg` or `.png` |
| `ingredients` | yes | array | 0–10 items. `[]` = meal not recognised → `status: "unknown"` |
| `ingredients[].name` | yes | string | 2–50 characters, must exist in the nutrition table, no duplicates |
| `ingredients[].grams` | yes | number | > 0 and ≤ 2000 |
| `ingredients[].confidence` | yes | number | 0 – 1 |
| `notes` | no | string \| null | ≤ 500 characters |
| `ownerId` | no | string | Existing user id. Regular users: only their own id (else 403) |

Server-set fields (`id`, `status`, `totals`, `createdAt`, `updatedAt`) are rejected with `400`. Any other unknown field is rejected with `400`.

**Success:** `201 Created`, `Location: /api/v1/meals/{newId}`, `data` = the new meal with nutrition.
**Errors:** `400 VALIDATION_ERROR`, `400 INVALID_JSON`, `401`, `403 FORBIDDEN`, `409 CONFLICT`.

**Example**

```http
POST /api/v1/meals HTTP/1.1
Authorization: Bearer user-a-token
Content-Type: application/json

{
  "title": "Chicken salad",
  "mealType": "lunch",
  "eatenAt": "2026-11-18T13:05:00Z",
  "imagePath": "uploads/user-a/chicken-salad.jpg",
  "notes": "Homemade",
  "ingredients": [
    { "name": "chicken breast", "grams": 120, "confidence": 0.93 },
    { "name": "lettuce", "grams": 60, "confidence": 0.81 },
    { "name": "tomato", "grams": 80, "confidence": 0.77 }
  ]
}
```

```json
HTTP/1.1 201 Created
Location: /api/v1/meals/meal_106
{
  "success": true,
  "message": "Meal created successfully.",
  "data": {
    "id": "meal_106",
    "ownerId": "user-a",
    "title": "Chicken salad",
    "mealType": "lunch",
    "eatenAt": "2026-11-18T13:05:00Z",
    "imagePath": "uploads/user-a/chicken-salad.jpg",
    "notes": "Homemade",
    "status": "analyzed",
    "ingredients": [
      { "name": "chicken breast", "grams": 120, "confidence": 0.93, "calories": 198.0, "protein": 37.2, "carbs": 0.0, "fat": 4.3 },
      { "name": "lettuce", "grams": 60, "confidence": 0.81, "calories": 9.0, "protein": 0.8, "carbs": 1.7, "fat": 0.1 },
      { "name": "tomato", "grams": 80, "confidence": 0.77, "calories": 14.4, "protein": 0.7, "carbs": 3.1, "fat": 0.2 }
    ],
    "totals": { "calories": 221.4, "protein": 38.7, "carbs": 4.8, "fat": 4.6 },
    "createdAt": "2026-11-19T06:16:57Z",
    "updatedAt": "2026-11-19T06:16:57Z"
  }
}
```

Error example — validation (all problems reported together):

```json
POST /api/v1/meals
{ "title": "ab", "mealType": "brunch", "eatenAt": "2026-11-18T13:05:00Z", "imagePath": "photo.gif",
  "calories": 500, "ingredients": [ { "name": "pizza", "grams": -5, "confidence": 0.9 } ] }

HTTP/1.1 400 Bad Request
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid or missing fields.",
    "details": [
      { "field": "calories", "message": "Unknown field. Allowed fields: title, mealType, eatenAt, imagePath, ingredients, notes." },
      { "field": "title", "message": "title must contain between 3 and 100 characters." },
      { "field": "mealType", "message": "mealType must be one of: breakfast, lunch, dinner, snack." },
      { "field": "imagePath", "message": "imagePath must point to a JPEG or PNG image (.jpg, .jpeg, .png)." },
      { "field": "ingredients[0].name", "message": "'pizza' was not found in the nutrition database." },
      { "field": "ingredients[0].grams", "message": "grams must be greater than 0 and at most 2000." }
    ]
  }
}
```

Error example — broken JSON (`{"title": "x",}`):

```json
HTTP/1.1 400 Bad Request
{ "success": false, "error": { "code": "INVALID_JSON", "message": "The request body is not valid JSON. Check quotes, commas and brackets." } }
```

Error example — same request sent twice:

```json
HTTP/1.1 409 Conflict
{ "success": false, "error": { "code": "CONFLICT", "message": "A meal titled 'Chicken salad' at 2026-11-18T13:05:00Z already exists (meal_106). Change the title or time, or update the existing meal." } }
```

Error example — user A sends `"ownerId": "user-b"`:

```json
HTTP/1.1 403 Forbidden
{ "success": false, "error": { "code": "FORBIDDEN", "message": "You can only create meals for your own account." } }
```

---

### 5.4 Replace a meal

`PUT /api/v1/meals/{id}`

Full replacement: send all editable fields (same body and rules as POST). Typical use: the user corrects an ingredient or a portion (FR-12) and the server recalculates the totals. `id`, `ownerId` and `createdAt` never change; `updatedAt` is refreshed. `ownerId` in the body → `400`.

**Auth:** owner of the meal, or admin.
**Path parameter:** `id`.
**Success:** `200 OK`, `data` = updated meal.
**Errors:** `400 VALIDATION_ERROR`, `400 INVALID_JSON`, `401`, `404 NOT_FOUND`, `409 CONFLICT`.

**Example**

```http
PUT /api/v1/meals/meal_106 HTTP/1.1
Authorization: Bearer user-a-token
Content-Type: application/json

{
  "title": "Chicken salad (corrected)",
  "mealType": "lunch",
  "eatenAt": "2026-11-18T13:05:00Z",
  "imagePath": "uploads/user-a/chicken-salad.jpg",
  "ingredients": [
    { "name": "chicken breast", "grams": 150, "confidence": 0.95 },
    { "name": "olive oil", "grams": 10, "confidence": 0.6 }
  ]
}
```

```json
HTTP/1.1 200 OK
{
  "success": true,
  "message": "Meal updated successfully. Nutrition totals were recalculated.",
  "data": {
    "id": "meal_106",
    "ownerId": "user-a",
    "title": "Chicken salad (corrected)",
    "mealType": "lunch",
    "eatenAt": "2026-11-18T13:05:00Z",
    "imagePath": "uploads/user-a/chicken-salad.jpg",
    "notes": null,
    "status": "analyzed",
    "ingredients": [
      { "name": "chicken breast", "grams": 150, "confidence": 0.95, "calories": 247.5, "protein": 46.5, "carbs": 0.0, "fat": 5.4 },
      { "name": "olive oil", "grams": 10, "confidence": 0.6, "calories": 88.4, "protein": 0.0, "carbs": 0.0, "fat": 10.0 }
    ],
    "totals": { "calories": 335.9, "protein": 46.5, "carbs": 0.0, "fat": 15.4 },
    "createdAt": "2026-11-19T06:16:57Z",
    "updatedAt": "2026-11-19T06:16:57Z"
  }
}
```

Error example — user B tries to update user A's meal: `PUT /api/v1/meals/meal_101` with `user-b-token` → `404 NOT_FOUND`, `"Meal 'meal_101' was not found."`

---

### 5.5 Delete a meal

`DELETE /api/v1/meals/{id}`

**Auth:** owner of the meal, or admin.
**Path parameter:** `id`.
**Success:** `200 OK`, `data: null`.
**Errors:** `401`, `404 NOT_FOUND` (also when deleting the same meal twice).

**Example**

```http
DELETE /api/v1/meals/meal_106 HTTP/1.1
Authorization: Bearer user-a-token
```

```json
HTTP/1.1 200 OK
{ "success": true, "message": "Meal 'meal_106' deleted successfully.", "data": null }
```

---

### 5.6 HTML greeting page

`GET /api/v1/greeting` — **public**, returns `Content-Type: text/html; charset=utf-8`.

Shows the project name and description, target users, team members (name, student ID, what they built), every endpoint with method, path and description, and the API status/version. Responsive layout (endpoint table turns into stacked cards under 640 px). `GET /` redirects here.

### 5.7 Health check

`GET /api/v1/health` — **public**. Used by the watchdog script from Assignment 1.

```json
HTTP/1.1 200 OK
{
  "success": true,
  "message": "API is running.",
  "data": { "status": "ok", "version": "v1", "time": "2026-11-19T06:16:57Z", "uptimeSeconds": 20, "mealsInStore": 5, "storage": "in-memory mock data (resets on restart)" }
}
```

### 5.8 Wrong method / wrong URL

```http
PATCH /api/v1/meals/meal_101
```

```json
HTTP/1.1 405 Method Not Allowed
Allow: DELETE, GET, PUT
{ "success": false, "error": { "code": "METHOD_NOT_ALLOWED", "message": "Method PATCH is not allowed for /api/v1/meals/meal_101. Allowed methods: DELETE, GET, PUT." } }
```

```http
GET /api/v1/getMeals
```

```json
HTTP/1.1 404 Not Found
{ "success": false, "error": { "code": "ENDPOINT_NOT_FOUND", "message": "The endpoint /api/v1/getMeals does not exist. See GET /api/v1/greeting for the list of endpoints." } }
```

## 6. Validation rules

Summary of what is checked (`app/validation.py`):

- **Required fields:** `title`, `mealType`, `eatenAt`, `imagePath`, `ingredients` (and inside each ingredient: `name`, `grams`, `confidence`).
- **Types:** strings must be strings, numbers must be numbers (`true`/`false` and `"50"` are rejected), `ingredients` must be an array of objects, the body must be a JSON object.
- **Lengths / ranges:** `title` 3–100, `imagePath` 5–255, `notes` ≤ 500, ingredient `name` 2–50, `grams` 0 < g ≤ 2000, `confidence` 0–1, at most 10 ingredients (FR-06), `perPage` 1–50.
- **Formats:** `eatenAt` ISO 8601 with time zone and not in the future; `imagePath` must be JPEG/PNG (FR-10); `mealType`, `status`, `sort` from fixed lists.
- **Unknown fields:** rejected, with the list of allowed fields. Server-set fields are rejected as read-only.
- **Business rules:** ingredient must exist in the nutrition table; no duplicate ingredient names; no two meals with the same owner + title + `eatenAt` (409).
- **Non-existent IDs:** `404 NOT_FOUND` for GET/PUT/DELETE.

Supported ingredient names: apple, avocado, banana, beef, bread, broccoli, cheddar cheese, chicken breast, cucumber, egg, feta cheese, greek yogurt, lentils, lettuce, milk, oats, olive oil, pasta, potato, salmon, tomato, white rice (case-insensitive).

## 7. Mock data

Loaded from `app/store.py` into memory at start-up. **All changes are lost when the server restarts.**

| ID | Owner | Title | Type | Status | Calories |
|---|---|---|---|---|---:|
| `meal_101` | user-a | Chicken rice bowl | lunch | analyzed | 534.7 |
| `meal_102` | user-a | Oatmeal with banana | breakfast | analyzed | 444.4 |
| `meal_103` | user-b | Salmon with potatoes | dinner | analyzed | 680.3 |
| `meal_104` | user-b | Greek salad | lunch | analyzed | 301.2 |
| `meal_105` | user-b | Blurry snack photo | snack | unknown | 0 |
| `meal_999` | — | *does not exist — use it to demonstrate 404* | | | |

New meals get IDs starting at `meal_106`.

## 8. Design decisions

### 8.1 404 instead of 403 for other users' meals

When a regular user requests, updates or deletes a meal that belongs to someone else, the API answers **`404 Not Found`** — exactly the same response as for an ID that does not exist. Meal history is private health data; answering `403` would confirm that the ID exists and belongs to another person, which lets an attacker enumerate IDs. With `404`, a user can learn nothing about meals they are not allowed to see. The admin token sees all meals, so for the admin a `404` always means the meal really does not exist.

We still use **`403 Forbidden`** where the user is asking for something they are explicitly not allowed to do and no hidden data would be revealed: creating a meal for another user, or filtering the list by another user's `ownerId`.

### 8.2 Other decisions

- **Resource-oriented URLs:** plural noun `/meals`, no verbs in paths; the action comes from the HTTP method.
- **Versioning:** `/api/v1` prefix so future breaking changes can go to `/api/v2`.
- **400 instead of 422:** FastAPI's default validation status is 422; we validate manually so every validation failure returns `400` with our envelope, as required by the assignment.
- **Server-computed nutrition:** clients send only what the AI recognised; totals are always recalculated on the server so they cannot be faked or become inconsistent.
- **PUT is a full replacement**, which keeps the rules identical to POST. `PATCH` is not supported (→ 405).
- **DELETE returns 200 with a message** rather than 204, so that the response still uses the envelope.
