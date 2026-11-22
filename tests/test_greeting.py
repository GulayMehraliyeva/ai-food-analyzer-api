def test_greeting_returns_html(client):
    r = client.get("/api/v1/greeting")
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/html; charset=utf-8"
    html = r.text
    assert html.startswith("<!DOCTYPE html>")
    assert "AI Food Analyzer" in html
    assert "Gulay Mehraliyeva" in html and "Araz Valishov" in html
    assert "/api/v1/meals/{id}" in html
    assert "API is running" in html


def test_health_is_public(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"
