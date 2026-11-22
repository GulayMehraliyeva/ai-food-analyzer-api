from tests.conftest import A


def fields(response):
    return {d["field"] for d in response.json()["error"]["details"]}


def test_empty_body(client):
    r = client.post("/api/v1/meals", headers={**A, "Content-Type": "application/json"}, content=b"")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_json(client):
    r = client.post("/api/v1/meals", headers={**A, "Content-Type": "application/json"}, content=b'{"title": "x",}')
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_JSON"
    assert "details" not in r.json()["error"]


def test_required_fields(client):
    r = client.post("/api/v1/meals", headers=A, json={})
    assert r.status_code == 400
    assert fields(r) == {"title", "mealType", "eatenAt", "imagePath", "ingredients"}


def test_types_lengths_and_enums(client, new_meal):
    bad = {**new_meal, "title": "ab", "mealType": "brunch", "eatenAt": 12, "imagePath": "photo.gif"}
    r = client.post("/api/v1/meals", headers=A, json=bad)
    assert r.status_code == 400
    assert fields(r) == {"title", "mealType", "eatenAt", "imagePath"}


def test_future_and_naive_dates(client, new_meal):
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "eatenAt": "2999-01-01T10:00:00Z"})
    assert r.json()["error"]["details"][0]["message"] == "eatenAt cannot be in the future."
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "eatenAt": "2026-11-18T10:00:00"})
    assert "time zone" in r.json()["error"]["details"][0]["message"]


def test_unknown_and_read_only_fields(client, new_meal):
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "calories": 500, "id": "meal_1"})
    assert r.status_code == 400
    assert fields(r) == {"calories", "id"}


def test_ingredient_rules(client, new_meal):
    bad = {
        **new_meal,
        "ingredients": [
            {"name": "pizza", "grams": 100, "confidence": 0.9},
            {"name": "egg", "grams": -5, "confidence": 1.5},
            {"name": "egg", "grams": "50", "confidence": 0.4, "color": "yellow"},
        ],
    }
    r = client.post("/api/v1/meals", headers=A, json=bad)
    assert r.status_code == 400
    assert fields(r) == {
        "ingredients[0].name",
        "ingredients[1].grams",
        "ingredients[1].confidence",
        "ingredients[2].name",
        "ingredients[2].grams",
        "ingredients[2].color",
    }


def test_too_many_ingredients(client, new_meal):
    names = ["apple", "banana", "egg", "oats", "milk", "bread", "tomato", "cucumber", "lettuce", "potato", "pasta"]
    items = [{"name": n, "grams": 10, "confidence": 0.5} for n in names]
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "ingredients": items})
    assert fields(r) == {"ingredients"}


def test_body_must_be_object(client):
    r = client.post("/api/v1/meals", headers=A, json=[1, 2])
    assert r.status_code == 400


def test_put_cannot_change_owner(client, new_meal):
    r = client.put("/api/v1/meals/meal_101", headers=A, json={**new_meal, "ownerId": "user-b"})
    assert r.status_code == 400
    assert fields(r) == {"ownerId"}


def test_invalid_query_params(client):
    r = client.get("/api/v1/meals?page=0&perPage=abc&mealType=brunch&sort=title", headers=A)
    assert r.status_code == 400
    assert fields(r) == {"page", "perPage", "mealType", "sort"}
