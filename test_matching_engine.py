
# test_matching_engine.py
# ChronosMatch - Matching Engine Correctness Tests

import unittest

from matching_engine import MatchingEngine


class TestMatchingEngine(unittest.TestCase):

    def test_empty_order_book(self):
        """A new engine should have no orders or trades."""
        engine = MatchingEngine(capacity=100)

        self.assertEqual(engine.snapshot(), [])
        self.assertEqual(engine.stats()["resting_orders"], 0)
        self.assertEqual(engine.stats()["trades"], 0)
        self.assertEqual(engine.stats()["volume"], 0)

    def test_resting_buy_order(self):
        """A BUY order should rest when no SELL order can match it."""
        engine = MatchingEngine(capacity=100)

        result = engine.submit(1, 100, 5)

        self.assertEqual(result["status"], "RESTING")
        self.assertEqual(result["filled_quantity"], 0)
        self.assertEqual(result["remaining_quantity"], 5)

        book = engine.snapshot()
        self.assertEqual(len(book), 1)
        self.assertEqual(book[0]["side"], "BUY")
        self.assertEqual(book[0]["price"], 100)
        self.assertEqual(book[0]["quantity"], 5)

    def test_best_price_priority(self):
        """A BUY order should match the lowest available SELL prices first."""
        engine = MatchingEngine(capacity=100)

        engine.submit(-1, 101, 5)
        engine.submit(-1, 99, 5)

        result = engine.submit(1, 105, 7)

        self.assertEqual(result["status"], "FILLED")
        self.assertEqual(result["filled_quantity"], 7)
        self.assertEqual(result["remaining_quantity"], 0)

        book = engine.snapshot()

        self.assertEqual(len(book), 1)
        self.assertEqual(book[0]["side"], "SELL")
        self.assertEqual(book[0]["price"], 101)
        self.assertEqual(book[0]["quantity"], 3)

        stats = engine.stats()
        self.assertEqual(stats["trades"], 2)
        self.assertEqual(stats["volume"], 7)
        self.assertEqual(stats["last_trade_price"], 101)

    def test_fifo_priority(self):
        """At the same price, the older resting order should fill first."""
        engine = MatchingEngine(capacity=100)

        first = engine.submit(-1, 100, 3)
        second = engine.submit(-1, 100, 4)

        result = engine.submit(1, 100, 4)

        self.assertEqual(first["order_id"], 1)
        self.assertEqual(second["order_id"], 2)
        self.assertEqual(result["filled_quantity"], 4)

        book = engine.snapshot()

        self.assertEqual(len(book), 1)
        self.assertEqual(book[0]["order_id"], 2)
        self.assertEqual(book[0]["quantity"], 3)
        self.assertEqual(book[0]["price"], 100)

    def test_partial_fill_and_resting_remainder(self):
        """Any unfilled incoming quantity should rest in the book."""
        engine = MatchingEngine(capacity=100)

        engine.submit(-1, 100, 3)
        result = engine.submit(1, 100, 5)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["filled_quantity"], 3)
        self.assertEqual(result["remaining_quantity"], 2)

        book = engine.snapshot()

        self.assertEqual(len(book), 1)
        self.assertEqual(book[0]["side"], "BUY")
        self.assertEqual(book[0]["price"], 100)
        self.assertEqual(book[0]["quantity"], 2)

        stats = engine.stats()
        self.assertEqual(stats["trades"], 1)
        self.assertEqual(stats["volume"], 3)

    def test_non_crossing_orders_do_not_trade(self):
        """Orders should not match when their prices do not cross."""
        engine = MatchingEngine(capacity=100)

        engine.submit(1, 99, 5)
        engine.submit(-1, 101, 4)

        stats = engine.stats()

        self.assertEqual(stats["trades"], 0)
        self.assertEqual(stats["volume"], 0)
        self.assertEqual(stats["resting_orders"], 2)

    def test_invalid_side_is_rejected(self):
        """Only side=1 (BUY) and side=-1 (SELL) are valid."""
        engine = MatchingEngine(capacity=100)

        with self.assertRaises(ValueError):
            engine.submit(0, 100, 1)

        with self.assertRaises(ValueError):
            engine.submit(2, 100, 1)

    def test_invalid_price_is_rejected(self):
        """Prices must be positive."""
        engine = MatchingEngine(capacity=100)

        with self.assertRaises(ValueError):
            engine.submit(1, 0, 1)

        with self.assertRaises(ValueError):
            engine.submit(-1, -100, 1)

    def test_invalid_quantity_is_rejected(self):
        """Quantities must be positive."""
        engine = MatchingEngine(capacity=100)

        with self.assertRaises(ValueError):
            engine.submit(1, 100, 0)

        with self.assertRaises(ValueError):
            engine.submit(-1, 100, -1)

    def test_capacity_limit(self):
        """A non-crossing order must not exceed book capacity."""
        engine = MatchingEngine(capacity=1)

        engine.submit(1, 100, 5)

        with self.assertRaises(OverflowError):
            engine.submit(1, 99, 2)

        # The original resting order should remain present.
        book = engine.snapshot()

        self.assertEqual(len(book), 1)
        self.assertEqual(book[0]["price"], 100)
        self.assertEqual(book[0]["quantity"], 5)
        self.assertEqual(engine.stats()["resting_orders"], 1)

    def test_repeated_matching(self):
        """Repeated matched orders should update trade statistics."""
        engine = MatchingEngine(capacity=100)

        for _ in range(1000):
            engine.submit(-1, 100, 1)
            engine.submit(1, 100, 1)

        stats = engine.stats()

        self.assertEqual(stats["trades"], 1000)
        self.assertEqual(stats["volume"], 1000)
        self.assertEqual(stats["resting_orders"], 0)
        self.assertEqual(engine.snapshot(), [])

    def test_order_ids_increase(self):
        """Successful submissions should receive increasing order IDs."""
        engine = MatchingEngine(capacity=100)

        first = engine.submit(1, 100, 1)
        second = engine.submit(1, 99, 1)
        third = engine.submit(-1, 110, 1)

        self.assertEqual(first["order_id"], 1)
        self.assertEqual(second["order_id"], 2)
        self.assertEqual(third["order_id"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
