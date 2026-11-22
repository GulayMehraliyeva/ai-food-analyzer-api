import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store

A = {"Authorization": "Bearer user-a-token"}
B = {"Authorization": "Bearer user-b-token"}
ADMIN = {"Authorization": "Bearer admin-token"}


@pytest.fixture
def client():
    store.reset()  # every test starts from the same mock data
    with TestClient(app) as c:
        yield c


@pytest.fixture
def new_meal():
    return {
        "title": "Chicken salad",
        "mealType": "lunch",
        "eatenAt": "2026-11-18T13:05:00Z",
        "imagePath": "uploads/user-a/chicken-salad.jpg",
        "ingredients": [
            {"name": "chicken breast", "grams": 120, "confidence": 0.93},
            {"name": "lettuce", "grams": 60, "confidence": 0.81},
        ],
    }
