
import random
import time
import traceback

from matching_engine import MatchingEngine


TOTAL_ORDERS = 200_000
CAPACITY = TOTAL_ORDERS + 10_000
SEED = 42


def main():
    random.seed(SEED)
    engine = MatchingEngine(capacity=CAPACITY)

    trades_before = engine.stats()["trades"]
    start = time.perf_counter()

    for i in range(TOTAL_ORDERS):
        side = random.choice((1, -1))
        price = random.randint(95, 105)
        quantity = random.randint(1, 10)

        result = engine.submit(side, price, quantity)

        if result["order_id"] <= 0:
            raise AssertionError(
                f"Invalid order ID at submission {i + 1}"
            )

        if result["status"] not in (
            "FILLED", "PARTIAL", "RESTING"
        ):
            raise AssertionError(
                f"Unexpected status: {result['status']}"
            )

    elapsed = time.perf_counter() - start
    stats = engine.stats()
    book = engine.snapshot()

    assert stats["trades"] >= trades_before
    assert stats["volume"] >= 0
    assert stats["resting_orders"] == len(book)
    assert len(book) <= CAPACITY

    for order in book:
        assert order["price"] > 0
        assert order["quantity"] > 0
        assert order["side"] in ("BUY", "SELL")

    print("\n" + "=" * 50)
    print("CHRONOSMATCH STRESS TEST")
    print("=" * 50)
    print(f"Submitted orders : {TOTAL_ORDERS:,}")
    print(f"Elapsed time     : {elapsed:.4f} seconds")
    print(f"Throughput       : {TOTAL_ORDERS / elapsed:,.0f} orders/sec")
    print(f"Trades           : {stats['trades']:,}")
    print(f"Traded volume    : {stats['volume']:,}")
    print(f"Resting orders   : {stats['resting_orders']:,}")
    print(f"Order book rows  : {len(book):,}")
    print("\nAll stress-test assertions passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nSTRESS TEST FAILED")
        traceback.print_exc()
        raise
