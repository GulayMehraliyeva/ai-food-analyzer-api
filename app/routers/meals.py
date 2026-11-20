"""CRUD endpoints for the main resource: meals (analyzed meal records)."""

from fastapi import APIRouter, Depends, Query, Request

from app.auth import User, can_access, get_current_user
from app.config import API_PREFIX
from app.errors import ApiError, ErrorCode, success_response
from app.store import store
from app.validation import read_json_object, validate_list_query, validate_meal_body

router = APIRouter(prefix=f"{API_PREFIX}/meals", tags=["Meals"])

_MEAL_BODY_EXAMPLE = {
    "title": "Chicken salad",
    "mealType": "lunch",
    "eatenAt": "2026-11-18T13:05:00Z",
    "imagePath": "uploads/user-a/chicken-salad.jpg",
    "notes": "Homemade",
    "ingredients": [
        {"name": "chicken breast", "grams": 120, "confidence": 0.93},
        {"name": "lettuce", "grams": 60, "confidence": 0.81},
        {"name": "tomato", "grams": 80, "confidence": 0.77},
    ],
}
_OPENAPI_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"example": _MEAL_BODY_EXAMPLE}},
    }
}


def _not_found(meal_id: str) -> ApiError:
    return ApiError(404, ErrorCode.NOT_FOUND, f"Meal '{meal_id}' was not found.")


def _get_accessible_meal(meal_id: str, user: User) -> dict:
    """Return the meal, or 404 if it does not exist OR belongs to someone else.

    We deliberately answer 404 (not 403) for other users' meals so that a regular
    user cannot discover which meal IDs exist. See docs/API.md.
    """
    meal = store.get(meal_id)
    if meal is None or not can_access(user, meal):
        raise _not_found(meal_id)
    return meal


def _ensure_not_duplicate(owner_id: str, fields: dict, exclude_id: str | None = None):
    duplicate = store.find_duplicate(owner_id, fields["title"], fields["eatenAt"], exclude_id)
    if duplicate:
        raise ApiError(
            409,
            ErrorCode.CONFLICT,
            f"A meal titled '{fields['title']}' at {fields['eatenAt']} already exists ({duplicate['id']}). "
            "Change the title or time, or update the existing meal.",
        )


_SORT_KEYS = {
    "eatenAt": lambda m: m["eatenAt"],
    "createdAt": lambda m: (m["createdAt"], m["id"]),
    "calories": lambda m: m["totals"]["calories"],
}


@router.get("", summary="List meals")
async def list_meals(
    user: User = Depends(get_current_user),
    page: str | None = Query(default=None, description="Page number, starts at 1 (default 1)."),
    perPage: str | None = Query(default=None, description="Items per page, 1-50 (default 10)."),
    mealType: str | None = Query(default=None, description="breakfast | lunch | dinner | snack"),
    status: str | None = Query(default=None, description="analyzed | unknown"),
    ownerId: str | None = Query(default=None, description="Admin only: filter by owner (user-a, user-b, admin)."),
    sort: str | None = Query(default=None, description="eatenAt | -eatenAt (default) | calories | -calories | createdAt | -createdAt"),
):
    q = validate_list_query(page, perPage, mealType, status, ownerId, sort)

    if q["ownerId"] and not user.is_admin and q["ownerId"] != user.id:
        raise ApiError(403, ErrorCode.FORBIDDEN, "Only an administrator can list meals of other users.")

    meals = [m for m in store.all() if can_access(user, m)]
    if q["ownerId"]:
        meals = [m for m in meals if m["ownerId"] == q["ownerId"]]
    if q["mealType"]:
        meals = [m for m in meals if m["mealType"] == q["mealType"]]
    if q["status"]:
        meals = [m for m in meals if m["status"] == q["status"]]

    key = q["sort"].lstrip("-")
    meals.sort(key=_SORT_KEYS[key], reverse=q["sort"].startswith("-"))

    total = len(meals)
    start = (q["page"] - 1) * q["perPage"]
    page_items = meals[start : start + q["perPage"]]
    meta = {
        "total": total,
        "page": q["page"],
        "perPage": q["perPage"],
        "totalPages": (total + q["perPage"] - 1) // q["perPage"],
    }
    return success_response(f"{len(page_items)} meal(s) returned.", page_items, meta=meta)


@router.get("/{meal_id}", summary="Get one meal")
async def get_meal(meal_id: str, user: User = Depends(get_current_user)):
    meal = _get_accessible_meal(meal_id, user)
    return success_response("Meal retrieved successfully.", meal)


@router.post("", status_code=201, summary="Create a meal analysis", openapi_extra=_OPENAPI_BODY)
async def create_meal(request: Request, user: User = Depends(get_current_user)):
    body = await read_json_object(request)
    fields = validate_meal_body(body, is_create=True)

    owner_id = fields.pop("ownerId") or user.id
    if owner_id != user.id and not user.is_admin:
        raise ApiError(403, ErrorCode.FORBIDDEN, "You can only create meals for your own account.")

    _ensure_not_duplicate(owner_id, fields)
    meal = store.create(owner_id, fields)
    message = "Meal created successfully." if meal["status"] == "analyzed" else (
        "Meal saved, but no ingredients were recognised (status: unknown)."
    )
    return success_response(message, meal, status_code=201, headers={"Location": f"{API_PREFIX}/meals/{meal['id']}"})


@router.put("/{meal_id}", summary="Replace a meal", openapi_extra=_OPENAPI_BODY)
async def update_meal(meal_id: str, request: Request, user: User = Depends(get_current_user)):
    existing = _get_accessible_meal(meal_id, user)
    body = await read_json_object(request)
    fields = validate_meal_body(body, is_create=False)
    fields.pop("ownerId")

    _ensure_not_duplicate(existing["ownerId"], fields, exclude_id=meal_id)
    meal = store.replace(meal_id, fields)
    return success_response("Meal updated successfully. Nutrition totals were recalculated.", meal)


@router.delete("/{meal_id}", summary="Delete a meal")
async def delete_meal(meal_id: str, user: User = Depends(get_current_user)):
    _get_accessible_meal(meal_id, user)
    store.delete(meal_id)
    return success_response(f"Meal '{meal_id}' deleted successfully.", None)
