from datetime import datetime, timedelta, timezone

import pytest

from app.errors import ApiError
from app.validation import validate_list_query, validate_meal_body


def meal_at(timestamp):
    return {
        "title": "Apple snack",
        "mealType": "snack",
        "eatenAt": timestamp,
        "imagePath": "uploads/apple.jpg",
        "ingredients": [{"name": "apple", "grams": 100, "confidence": 0.9}],
    }


def test_accepts_valid_meal_and_converts_time_to_utc():
    body = meal_at("2025-01-15T14:00:00+04:00")
    result = validate_meal_body(body, is_create=True)
    assert result["eatenAt"] == "2025-01-15T10:00:00Z"


def test_rejects_meal_two_minutes_in_the_future():
    future = datetime.now(timezone.utc) + timedelta(minutes=2)
    with pytest.raises(ApiError) as caught:
        validate_meal_body(meal_at(future.isoformat()), is_create=True)

    assert caught.value.status_code == 400
    assert caught.value.details[0]["field"] == "eatenAt"


def test_rejects_page_zero():
    with pytest.raises(ApiError) as caught:
        validate_list_query("0", None, None, None, None, None)

    assert caught.value.status_code == 400
    assert caught.value.details[0]["field"] == "page"