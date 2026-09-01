import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    from database import db
    from scraper.gsmarena import load_fallback_dataset

    db.init_db()
    for record in load_fallback_dataset():
        db.upsert_phone(record)
    with TestClient(app) as c:
        yield c


def test_list_phones(client):
    res = client.get("/api/phones")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 10
    assert all("name" in p and "processor" in p for p in data)


def test_get_phone(client):
    res = client.get("/api/phones/Galaxy S23")
    assert res.status_code == 200
    assert "Snapdragon" in res.json()["processor"]


def test_get_phone_404(client):
    res = client.get("/api/phones/nonexistent xyz")
    assert res.status_code == 404


def test_ask_entity_resolution(client):
    res = client.post(
        "/api/ask", json={"query": "What are the camera specs of the Samsung Galaxy S23?"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sources"] == ["Galaxy S23"]
    compact = body["answer"].replace("\u202f", "").replace(" ", "").lower()
    assert "50mp" in compact or "generativemode" in compact


def test_review_unknown_404(client):
    res = client.post("/api/review", json={"phone": "nonexistent xyz"})
    assert res.status_code == 404
