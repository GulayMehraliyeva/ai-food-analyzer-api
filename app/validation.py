"""Validation of request bodies and query parameters.

Validation is written by hand (instead of relying on FastAPI's automatic 422
errors) so that every failure returns 400 with our own envelope and a clear,
field-level message.
"""

import json
from datetime import datetime, timezone

from fastapi import Request

from app.auth import USERS
from app.errors import ApiError, ErrorCode, validation_error
from app.nutrition import is_known_ingredient, normalize_name

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")
MEAL_STATUSES = ("analyzed", "unknown")
SORT_OPTIONS = ("eatenAt", "-eatenAt", "calories", "-calories", "createdAt", "-createdAt")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")

EDITABLE_FIELDS = ("title", "mealType", "eatenAt", "imagePath", "ingredients", "notes")
REQUIRED_FIELDS = ("title", "mealType", "eatenAt", "imagePath", "ingredients")
READ_ONLY_FIELDS = ("id", "status", "totals", "createdAt", "updatedAt")
INGREDIENT_FIELDS = ("name", "grams", "confidence")

MAX_INGREDIENTS = 10
MAX_GRAMS = 2000
MAX_PER_PAGE = 50


async def read_json_object(request: Request) -> dict:
    raw = await request.body()
    if not raw.strip():
        raise validation_error(
            [{"field": "body", "message": "Request body is required and must be a JSON object."}],
            message="The request body is missing.",
        )
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, ErrorCode.INVALID_JSON, "The request body is not valid JSON. Check quotes, commas and brackets.")
    if not isinstance(data, dict):
        raise validation_error([{"field": "body", "message": "Request body must be a JSON object, e.g. {\"title\": ...}."}])
    return data


def _is_number(value) -> bool:
    # bool is a subclass of int in Python, but true/false is not a valid number here.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_string(body, field, errors, min_len, max_len, required=True):
    if field not in body or body[field] is None:
        if required:
            errors.append({"field": field, "message": f"{field} is required."})
        return None
    value = body[field]
    if not isinstance(value, str):
        errors.append({"field": field, "message": f"{field} must be a string."})
        return None
    value = value.strip()
    if not (min_len <= len(value) <= max_len):
        errors.append({"field": field, "message": f"{field} must contain between {min_len} and {max_len} characters."})
        return None
    return value


def _check_meal_type(body, errors):
    meal_type = body.get("mealType")
    if meal_type is None:
        errors.append({"field": "mealType", "message": "mealType is required."})
        return None
    if meal_type not in MEAL_TYPES:
        errors.append({"field": "mealType", "message": f"mealType must be one of: {', '.join(MEAL_TYPES)}."})
        return None
    return meal_type


def _check_image_path(body, errors):
    path = _check_string(body, "imagePath", errors, 5, 255)
    if path and not path.lower().endswith(IMAGE_EXTENSIONS):
        errors.append({"field": "imagePath", "message": "imagePath must point to a JPEG or PNG image (.jpg, .jpeg, .png)."})
        return None
    return path


def _check_eaten_at(body, errors):
    if "eatenAt" not in body or body["eatenAt"] is None:
        errors.append({"field": "eatenAt", "message": "eatenAt is required."})
        return None
    value = body["eatenAt"]
    if not isinstance(value, str):
        errors.append({"field": "eatenAt", "message": "eatenAt must be a string in ISO 8601 format, e.g. 2026-11-18T13:05:00Z."})
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append({"field": "eatenAt", "message": "eatenAt must be a valid ISO 8601 date-time, e.g. 2026-11-18T13:05:00Z."})
        return None
    if parsed.tzinfo is None:
        errors.append({"field": "eatenAt", "message": "eatenAt must include a time zone, e.g. 2026-11-18T13:05:00Z or +04:00."})
        return None
    # parsed = parsed.astimezone(timezone.utc).replace(microsecond=0)
    # if parsed > datetime.now(timezone.utc) + timedelta(minutes=5):
    #     errors.append({"field": "eatenAt", "message": "eatenAt cannot be in the future."})
    #     return None
    # return parsed.isoformat().replace("+00:00", "Z")
    try:
        parsed = parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        errors.append({"field": "eatenAt", "message": "eatenAt is outside the supported UTC date range."})
        return None

    if parsed > datetime.now(timezone.utc):
        errors.append({"field": "eatenAt", "message": "eatenAt cannot be in the future."})
        return None

    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check_ingredients(body, errors):
    if "ingredients" not in body or body["ingredients"] is None:
        errors.append({"field": "ingredients", "message": "ingredients is required (use [] if the meal was not recognised)."})
        return None
    items = body["ingredients"]
    if not isinstance(items, list):
        errors.append({"field": "ingredients", "message": "ingredients must be an array."})
        return None
    if len(items) > MAX_INGREDIENTS:
        errors.append({"field": "ingredients", "message": f"A meal can have at most {MAX_INGREDIENTS} ingredients."})
        return None

    clean, seen, start = [], set(), len(errors)
    for i, item in enumerate(items):
        prefix = f"ingredients[{i}]"
        if not isinstance(item, dict):
            errors.append({"field": prefix, "message": "Each ingredient must be an object with name, grams and confidence."})
            continue
        for key in item:
            if key not in INGREDIENT_FIELDS:
                errors.append({"field": f"{prefix}.{key}", "message": "Unknown field. Allowed: name, grams, confidence."})

        name = item.get("name")
        if name is None:
            errors.append({"field": f"{prefix}.name", "message": "name is required."})
        elif not isinstance(name, str):
            errors.append({"field": f"{prefix}.name", "message": "name must be a string."})
        elif not (2 <= len(name.strip()) <= 50):
            errors.append({"field": f"{prefix}.name", "message": "name must contain between 2 and 50 characters."})
        elif not is_known_ingredient(name):
            errors.append({"field": f"{prefix}.name", "message": f"'{name.strip()}' was not found in the nutrition database."})
        elif normalize_name(name) in seen:
            errors.append({"field": f"{prefix}.name", "message": "Duplicate ingredient. Combine the grams into one entry."})
        else:
            seen.add(normalize_name(name))

        grams = item.get("grams")
        if grams is None:
            errors.append({"field": f"{prefix}.grams", "message": "grams is required."})
        elif not _is_number(grams):
            errors.append({"field": f"{prefix}.grams", "message": "grams must be a number."})
        elif not (0 < grams <= MAX_GRAMS):
            errors.append({"field": f"{prefix}.grams", "message": f"grams must be greater than 0 and at most {MAX_GRAMS}."})

        confidence = item.get("confidence")
        if confidence is None:
            errors.append({"field": f"{prefix}.confidence", "message": "confidence is required."})
        elif not _is_number(confidence):
            errors.append({"field": f"{prefix}.confidence", "message": "confidence must be a number."})
        elif not (0 <= confidence <= 1):
            errors.append({"field": f"{prefix}.confidence", "message": "confidence must be between 0 and 1."})

        clean.append({"name": name, "grams": grams, "confidence": confidence})
    return clean if len(errors) == start else None


def validate_meal_body(body: dict, *, is_create: bool) -> dict:
    """Validate a POST or PUT body. Returns cleaned fields or raises 400 with all problems at once."""
    errors = []

    for key in body:
        if key == "ownerId":
            if not is_create:
                errors.append({"field": "ownerId", "message": "ownerId cannot be changed after a meal is created."})
        elif key in READ_ONLY_FIELDS:
            errors.append({"field": key, "message": f"{key} is read-only and is set by the server."})
        elif key not in EDITABLE_FIELDS:
            errors.append({"field": key, "message": f"Unknown field. Allowed fields: {', '.join(EDITABLE_FIELDS)}."})

    fields = {
        "title": _check_string(body, "title", errors, 3, 100),
        "mealType": _check_meal_type(body, errors),
        "eatenAt": _check_eaten_at(body, errors),
        "imagePath": _check_image_path(body, errors),
        "ingredients": _check_ingredients(body, errors),
        "notes": _check_string(body, "notes", errors, 0, 500, required=False),
    }

    owner_id = None
    if is_create and "ownerId" in body:
        owner_id = body["ownerId"]
        if not isinstance(owner_id, str) or owner_id not in USERS:
            errors.append({"field": "ownerId", "message": f"ownerId must be an existing user id: {', '.join(USERS)}."})
            owner_id = None

    if errors:
        raise validation_error(errors)

    if fields["notes"] == "":
        fields["notes"] = None
    fields["ownerId"] = owner_id
    return fields


def _parse_int(params, name, default, minimum, maximum, errors):
    raw = params.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        errors.append({"field": name, "message": f"{name} must be an integer."})
        return default
    if not (minimum <= value <= maximum):
        errors.append({"field": name, "message": f"{name} must be between {minimum} and {maximum}."})
        return default
    return value


def validate_list_query(page, per_page, meal_type, status, owner_id, sort) -> dict:
    errors = []
    params = {"page": page, "perPage": per_page}
    result = {
        "page": _parse_int(params, "page", 1, 1, 10_000, errors),
        "perPage": _parse_int(params, "perPage", 10, 1, MAX_PER_PAGE, errors),
        "mealType": meal_type,
        "status": status,
        "ownerId": owner_id,
        "sort": sort or "-eatenAt",
    }
    if meal_type is not None and meal_type not in MEAL_TYPES:
        errors.append({"field": "mealType", "message": f"mealType must be one of: {', '.join(MEAL_TYPES)}."})
    if status is not None and status not in MEAL_STATUSES:
        errors.append({"field": "status", "message": f"status must be one of: {', '.join(MEAL_STATUSES)}."})
    if owner_id is not None and owner_id not in USERS:
        errors.append({"field": "ownerId", "message": f"ownerId must be an existing user id: {', '.join(USERS)}."})
    if result["sort"] not in SORT_OPTIONS:
        errors.append({"field": "sort", "message": f"sort must be one of: {', '.join(SORT_OPTIONS)}."})
    if errors:
        raise validation_error(errors, message="One or more query parameters are invalid.")
    return result
