import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200

def test_add(client):
    r = client.get("/add?a=2&b=3")
    assert r.get_json()["result"] == 5.0

def test_subtract(client):
    r = client.get("/subtract?a=10&b=4")
    assert r.get_json()["result"] == 6.0

def test_multiply(client):
    r = client.get("/multiply?a=3&b=7")
    assert r.get_json()["result"] == 21.0
