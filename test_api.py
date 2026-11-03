
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


# Day 3: Trade History API Tests

def test_trades_endpoint():
    response = client.get("/api/trades")

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert "trades" in data
    assert isinstance(data["count"], int)
    assert isinstance(data["trades"], list)
    assert data["count"] == len(data["trades"])


def test_trade_history_records_actual_execution():
    before = client.get("/api/trades").json()

    previous_trade_ids = {
        trade["trade_id"] for trade in before["trades"]
    }

    unique_price = 8765432101
    quantity = 5

    buy_response = client.post(
        "/api/orders",
        json={
            "side": "BUY",
            "price": unique_price,
            "quantity": quantity,
        },
    )

    assert buy_response.status_code == 200
    buy_order = buy_response.json()["order"]

    assert buy_order["status"] == "RESTING"

    sell_response = client.post(
        "/api/orders",
        json={
            "side": "SELL",
            "price": unique_price,
            "quantity": quantity,
        },
    )

    assert sell_response.status_code == 200
    sell_order = sell_response.json()["order"]

    assert sell_order["status"] == "FILLED"
    assert sell_order["filled_quantity"] == quantity

    after = client.get("/api/trades")

    assert after.status_code == 200

    trades = after.json()["trades"]

    new_trades = [
        trade
        for trade in trades
        if trade["trade_id"] not in previous_trade_ids
    ]

    assert len(new_trades) == 1

    trade = new_trades[0]

    assert trade["buy_order_id"] == buy_order["order_id"]
    assert trade["sell_order_id"] == sell_order["order_id"]
    assert trade["price"] == unique_price
    assert trade["quantity"] == quantity


def test_trade_history_response_fields():
    response = client.get("/api/trades")

    assert response.status_code == 200

    data = response.json()

    for trade in data["trades"]:
        assert "trade_id" in trade
        assert "buy_order_id" in trade
        assert "sell_order_id" in trade
        assert "price" in trade
        assert "quantity" in trade

        assert isinstance(trade["trade_id"], int)
        assert isinstance(trade["buy_order_id"], int)
        assert isinstance(trade["sell_order_id"], int)
        assert isinstance(trade["price"], int)
        assert isinstance(trade["quantity"], int)
