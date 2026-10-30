from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_engine_info_endpoint():
    response = client.get("/api/engine-info")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "chronosmatch"
    assert isinstance(data["native_extension_loaded"], bool)
    assert "module_path" in data
    assert "engine_class" in data
    assert "stats" in data


def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_orderbook_endpoint():
    response = client.get("/api/orderbook")
    assert response.status_code == 200

    data = response.json()
    assert "orders" in data
    assert "stats" in data


def test_invalid_order_rejected():
    response = client.post(
        "/api/orders",
        json={
            "side": "BUY",
            "price": -100,
            "quantity": 5
        }
    )
    assert response.status_code == 422
