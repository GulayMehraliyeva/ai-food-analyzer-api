from tests.conftest import A, ADMIN, B


def test_missing_token_returns_401(client):
    r = client.get("/api/v1/meals")
    assert r.status_code == 401
    assert r.json() == {
        "success": False,
        "error": {"code": "UNAUTHORIZED", "message": "Authentication required. Send the header 'Authorization: Bearer <token>'."},
    }


def test_invalid_token_returns_401(client):
    r = client.get("/api/v1/meals", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


def test_malformed_header_returns_401(client):
    r = client.get("/api/v1/meals", headers={"Authorization": "user-a-token"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


def test_user_a_lists_only_own_meals(client):
    r = client.get("/api/v1/meals", headers=A)
    assert r.status_code == 200
    assert {m["ownerId"] for m in r.json()["data"]} == {"user-a"}
    assert r.json()["meta"]["total"] == 2


def test_admin_lists_all_meals(client):
    r = client.get("/api/v1/meals", headers=ADMIN)
    assert r.json()["meta"]["total"] == 5


def test_user_a_cannot_read_update_or_delete_user_b_meal(client, new_meal):
    assert client.get("/api/v1/meals/meal_103", headers=A).status_code == 404
    assert client.put("/api/v1/meals/meal_103", headers=A, json=new_meal).status_code == 404
    assert client.delete("/api/v1/meals/meal_103", headers=A).status_code == 404
    assert client.get("/api/v1/meals/meal_103", headers=B).status_code == 200


def test_user_b_cannot_read_update_or_delete_user_a_meal(client, new_meal):
    assert client.get("/api/v1/meals/meal_101", headers=B).status_code == 404
    assert client.put("/api/v1/meals/meal_101", headers=B, json=new_meal).status_code == 404
    assert client.delete("/api/v1/meals/meal_101", headers=B).status_code == 404


def test_admin_can_read_update_and_delete_any_meal(client, new_meal):
    assert client.get("/api/v1/meals/meal_101", headers=ADMIN).status_code == 200
    r = client.put("/api/v1/meals/meal_103", headers=ADMIN, json=new_meal)
    assert r.status_code == 200
    assert r.json()["data"]["ownerId"] == "user-b"  # owner is kept
    assert client.delete("/api/v1/meals/meal_104", headers=ADMIN).status_code == 200


def test_regular_user_cannot_create_for_someone_else(client, new_meal):
    r = client.post("/api/v1/meals", headers=A, json={**new_meal, "ownerId": "user-b"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_create_for_user(client, new_meal):
    r = client.post("/api/v1/meals", headers=ADMIN, json={**new_meal, "ownerId": "user-b"})
    assert r.status_code == 201
    assert r.json()["data"]["ownerId"] == "user-b"


def test_regular_user_cannot_filter_by_other_owner(client):
    r = client.get("/api/v1/meals?ownerId=user-b", headers=A)
    assert r.status_code == 403
