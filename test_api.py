
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

    data = response.json()
    assert isinstance(data, dict)
    assert "resting_orders" in data
    assert "trades" in data
    assert "volume" in data
    assert "last_trade_price" in data
    assert "orders_processed" in data
    assert "recent_orders" in data
    assert "engine_uptime_seconds" in data
    assert data["orders_processed"] >= 0
    assert data["engine_uptime_seconds"] >= 0


def test_orderbook_endpoint():
    response = client.get("/api/orderbook")
    assert response.status_code == 200

    data = response.json()
    assert "orders" in data
    assert "stats" in data
    assert "orders_processed" in data["stats"]


def test_recent_orders_endpoint():
    response = client.get("/api/orders/recent")
    assert response.status_code == 200

    data = response.json()
    assert "count" in data
    assert "orders" in data
    assert isinstance(data["orders"], list)


def test_invalid_order_rejected():
    response = client.post(
        "/api/orders",
        json={
            "side": "BUY",
            "price": -100,
            "quantity": 5,
        },
    )
    assert response.status_code == 422


def test_valid_order_updates_telemetry():
    before = client.get("/api/stats").json()

    response = client.post(
        "/api/orders",
        json={
            "side": "BUY",
            "price": 987654321,
            "quantity": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["order"]["status"] == "RESTING"
    assert data["order"]["remaining_quantity"] == 1
    assert data["stats"]["orders_processed"] == (
        before["orders_processed"] + 1
    )

    recent = client.get("/api/orders/recent").json()
    assert recent["count"] >= 1
    assert recent["orders"][0]["side"] == "BUY"
    assert recent["orders"][0]["price"] == 987654321
    assert recent["orders"][0]["quantity"] == 1
