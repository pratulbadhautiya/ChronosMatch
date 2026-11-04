
import random
from matching_engine import MatchingEngine


def validate_order_book(engine, expected_filled_quantity):
    """Validate matching and order-book invariants."""

    book = engine.snapshot()
    stats = engine.stats()

    assert stats["resting_orders"] == len(book), (
        "Resting-order count does not match snapshot"
    )

    for order in book:
        assert order["price"] > 0
        assert order["quantity"] > 0
        assert order["side"] in ("BUY", "SELL")

    order_ids = [order["order_id"] for order in book]

    assert len(order_ids) == len(set(order_ids)), (
        "Duplicate order IDs detected"
    )

    bids = [order for order in book if order["side"] == "BUY"]
    asks = [order for order in book if order["side"] == "SELL"]

    bid_prices = [order["price"] for order in bids]
    ask_prices = [order["price"] for order in asks]

    assert bid_prices == sorted(bid_prices, reverse=True), (
        "Buy-side price priority failed"
    )

    assert ask_prices == sorted(ask_prices), (
        "Sell-side price priority failed"
    )

    # FIFO: older order IDs must appear first at the same price.
    for side_orders in (bids, asks):
        for i in range(1, len(side_orders)):
            previous = side_orders[i - 1]
            current = side_orders[i]

            if previous["price"] == current["price"]:
                assert previous["order_id"] < current["order_id"], (
                    "FIFO priority failed"
                )

    # No crossed orders should remain in the book.
    if bids and asks:
        assert max(bid_prices) < min(ask_prices), (
            "Crossed order book detected"
        )

    assert stats["volume"] == expected_filled_quantity, (
        f"Trade-volume mismatch: expected {expected_filled_quantity}, "
        f"got {stats['volume']}"
    )

    return book


def check_quantity_conservation(
    submitted_quantity,
    filled_quantity,
    resting_quantity,
    order_number,
):
    """
    Each trade consumes quantity from both a BUY and a SELL order.
    Therefore submitted = 2 * filled + resting.
    """

    expected_resting = submitted_quantity - (2 * filled_quantity)

    if expected_resting != resting_quantity:
        print("\nQUANTITY CONSERVATION FAILURE")
        print(f"After order number : {order_number}")
        print(f"Submitted quantity : {submitted_quantity}")
        print(f"Traded quantity    : {filled_quantity}")
        print(f"Expected resting   : {expected_resting}")
        print(f"Actual resting     : {resting_quantity}")

        raise AssertionError("Order quantity conservation failed")


def test_randomized_matching():
    random.seed(42)

    total_orders = 5000
    engine = MatchingEngine(capacity=total_orders + 10)

    total_submitted_quantity = 0
    total_filled_quantity = 0

    print(f"Submitting {total_orders:,} randomized orders...")

    for i in range(total_orders):
        side = random.choice((1, -1))
        price = random.randint(90, 110)
        quantity = random.randint(1, 20)

        result = engine.submit(side, price, quantity)

        total_submitted_quantity += quantity
        total_filled_quantity += result["filled_quantity"]

        if (i + 1) % 50 == 0:
            book = validate_order_book(
                engine,
                total_filled_quantity,
            )

            resting_quantity = sum(
                order["quantity"] for order in book
            )

            check_quantity_conservation(
                total_submitted_quantity,
                total_filled_quantity,
                resting_quantity,
                i + 1,
            )

            print(f"Validated {i + 1:,} orders")

    # Final validation.
    book = validate_order_book(engine, total_filled_quantity)

    resting_quantity = sum(
        order["quantity"] for order in book
    )

    check_quantity_conservation(
        total_submitted_quantity,
        total_filled_quantity,
        resting_quantity,
        total_orders,
    )

    stats = engine.stats()

    print("\nRandomized testing passed!")
    print(f"Orders submitted : {total_orders:,}")
    print(f"Total quantity   : {total_submitted_quantity:,}")
    print(f"Traded quantity  : {total_filled_quantity:,}")
    print(f"Resting quantity : {resting_quantity:,}")
    print(f"Resting orders   : {len(book):,}")
    print(f"Trade volume     : {stats['volume']:,}")


if __name__ == "__main__":
    test_randomized_matching()
