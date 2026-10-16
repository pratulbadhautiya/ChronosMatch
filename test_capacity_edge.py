
from matching_engine import MatchingEngine


def test_normal_partial_fill():
    engine = MatchingEngine(capacity=1)

    engine.submit(-1, 100, 10)
    result = engine.submit(1, 100, 5)

    assert result["filled_quantity"] == 5
    assert result["remaining_quantity"] == 0
    assert result["status"] == "FILLED"

    book = engine.snapshot()
    assert len(book) == 1
    assert book[0]["side"] == "SELL"
    assert book[0]["quantity"] == 5

    stats = engine.stats()
    assert stats["volume"] == 5
    assert stats["trades"] == 1

    print("PASS: Normal partial fill")


def test_capacity_slot_reused_after_match():
    engine = MatchingEngine(capacity=1)

    engine.submit(-1, 100, 3)
    result = engine.submit(1, 100, 5)

    assert result["filled_quantity"] == 3
    assert result["remaining_quantity"] == 2
    assert result["status"] == "PARTIAL"

    book = engine.snapshot()
    assert len(book) == 1
    assert book[0]["side"] == "BUY"
    assert book[0]["quantity"] == 2

    stats = engine.stats()
    assert stats["resting_orders"] == 1
    assert stats["trades"] == 1
    assert stats["volume"] == 3
    assert stats["last_trade_price"] == 100

    print("PASS: Capacity slot reused after matching")


def test_full_capacity_without_match():
    engine = MatchingEngine(capacity=1)

    engine.submit(-1, 100, 3)

    before_book = engine.snapshot()
    before_stats = engine.stats()

    try:
        engine.submit(1, 90, 5)
    except OverflowError:
        pass
    else:
        raise AssertionError("Expected OverflowError")

    assert engine.snapshot() == before_book
    assert engine.stats() == before_stats

    print("PASS: Capacity error leaves state unchanged")


if __name__ == "__main__":
    test_normal_partial_fill()
    test_capacity_slot_reused_after_match()
    test_full_capacity_without_match()
    print("\nAll capacity tests passed.")
