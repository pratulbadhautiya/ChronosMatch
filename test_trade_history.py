
from matching_engine import MatchingEngine


def test_new_engine_has_empty_trade_history():
    engine = MatchingEngine(capacity=10)

    assert engine.get_trades() == []


def test_trade_history_records_actual_execution():
    engine = MatchingEngine(capacity=10)

    sell = engine.submit(-1, 100, 5)
    buy = engine.submit(1, 100, 5)

    trades = engine.get_trades()

    assert len(trades) == 1

    trade = trades[0]

    assert trade["trade_id"] == 1
    assert trade["buy_order_id"] == buy["order_id"]
    assert trade["sell_order_id"] == sell["order_id"]
    assert trade["price"] == 100
    assert trade["quantity"] == 5

    stats = engine.stats()

    assert stats["trades"] == 1
    assert stats["volume"] == 5


def test_trade_history_retains_latest_1000_executions():
    engine = MatchingEngine(capacity=1)

    total_executions = 1005

    for _ in range(total_executions):
        engine.submit(-1, 100, 1)
        engine.submit(1, 100, 1)

    trades = engine.get_trades()
    stats = engine.stats()

    # Only the latest 1000 executions should remain.
    assert len(trades) == 1000

    # Retained records should be in chronological order.
    trade_ids = [trade["trade_id"] for trade in trades]

    assert trade_ids == list(range(6, 1006))

    # Trade IDs must remain unique.
    assert len(set(trade_ids)) == 1000

    # Cumulative statistics must include all executions.
    assert stats["trades"] == 1005
    assert stats["volume"] == 1005

    # Latest retained execution should have ID 1005.
    assert trades[-1]["trade_id"] == 1005
