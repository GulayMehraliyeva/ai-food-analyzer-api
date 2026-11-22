from tests.conftest import A, ADMIN


def test_list_has_envelope_and_meta(client):
    body = client.get("/api/v1/meals?page=1&perPage=1", headers=A).json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["meta"] == {"total": 2, "page": 1, "perPage": 1, "totalPages": 2}


def test_list_filters_and_sort(client):
    body = client.get("/api/v1/meals?mealType=lunch&sort=-calories", headers=ADMIN).json()
    assert [m["id"] for m in body["data"]] == ["meal_101", "meal_104"]
    unknown = client.get("/api/v1/meals?status=unknown", headers=ADMIN).json()
    assert [m["id"] for m in unknown["data"]] == ["meal_105"]


def test_get_one_meal(client):
    r = client.get("/api/v1/meals/meal_101", headers=A)
    assert r.status_code == 200
    meal = r.json()["data"]
    assert meal["id"] == "meal_101"
    assert meal["totals"] == {"calories": 534.7, "protein": 54.1, "carbs": 61.7, "fat": 6.3}


def test_get_missing_meal_returns_404(client):
    r = client.get("/api/v1/meals/meal_999", headers=ADMIN)
    assert r.status_code == 404
    assert r.json()["error"] == {"code": "NOT_FOUND", "message": "Meal 'meal_999' was not found."}


def test_create_meal_calculates_totals(client, new_meal):
    r = client.post("/api/v1/meals", headers=A, json=new_meal)
    assert r.status_code == 201
    assert r.headers["location"] == "/api/v1/meals/meal_106"
    data = r.json()["data"]
    assert data["ownerId"] == "user-a"
    assert data["status"] == "analyzed"
    assert data["totals"]["calories"] == 207.0  # 198 (chicken) + 9 (lettuce)
    assert client.get("/api/v1/meals/meal_106", headers=A).status_code == 200


def test_create_unknown_meal(client, new_meal):
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "ingredients": []})
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "unknown"
    assert r.json()["data"]["totals"]["calories"] == 0


def test_create_duplicate_returns_409(client, new_meal):
    assert client.post("/api/v1/meals", headers=A, json=new_meal).status_code == 201
    r = client.post("/api/v1/meals", headers=A, json=new_meal)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


def test_update_meal_recalculates(client, new_meal):
    r = client.put("/api/v1/meals/meal_101", headers=A, json=new_meal)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == "meal_101"
    assert data["title"] == "Chicken salad"
    assert data["totals"]["calories"] == 207.0
    assert data["createdAt"] == "2026-11-18T18:00:00Z"
    assert data["updatedAt"] != data["createdAt"]


def test_update_missing_meal_returns_404(client, new_meal):
    assert client.put("/api/v1/meals/meal_999", headers=A, json=new_meal).status_code == 404


def test_delete_meal(client):
    r = client.delete("/api/v1/meals/meal_102", headers=A)
    assert r.status_code == 200
    assert r.json() == {"success": True, "message": "Meal 'meal_102' deleted successfully.", "data": None}
    assert client.get("/api/v1/meals/meal_102", headers=A).status_code == 404
    assert client.delete("/api/v1/meals/meal_102", headers=A).status_code == 404


def test_method_not_allowed(client):
    r = client.patch("/api/v1/meals/meal_101", headers=A, json={})
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert r.headers["allow"] == "DELETE, GET, PUT"


def test_unknown_endpoint(client):
    r = client.get("/api/v1/getMeals", headers=A)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "ENDPOINT_NOT_FOUND"
