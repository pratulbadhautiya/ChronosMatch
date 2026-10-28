
import pytest
from ring_buffer import RingBuffer


def test_empty_buffer():
    buffer = RingBuffer(path="test_ring_empty.bin", capacity=2)

    try:
        assert buffer.get() is None
        print("PASS: Empty-buffer behavior")
    finally:
        buffer.close()


def test_full_buffer():
    buffer = RingBuffer(path="test_ring_full.bin", capacity=2)

    try:
        assert buffer.put(1, 100, 5) is True
        assert buffer.put(-1, 101, 3) is True

        # A full buffer must reject another order.
        assert buffer.put(1, 102, 4) is False

        print("PASS: Full-buffer behavior")
    finally:
        buffer.close()


def test_fifo_order():
    buffer = RingBuffer(path="test_ring_fifo.bin", capacity=3)

    try:
        buffer.put(1, 100, 5)
        buffer.put(-1, 101, 3)
        buffer.put(1, 102, 7)

        first = buffer.get()
        second = buffer.get()
        third = buffer.get()

        assert first["price"] == 100
        assert second["price"] == 101
        assert third["price"] == 102

        assert buffer.get() is None

        print("PASS: FIFO ordering")
    finally:
        buffer.close()


def test_sequence_numbers():
    buffer = RingBuffer(path="test_ring_sequence.bin", capacity=2)

    try:
        buffer.put(1, 100, 5)
        first = buffer.get()

        buffer.put(-1, 101, 3)
        second = buffer.get()

        assert first["sequence"] == 1
        assert second["sequence"] == 2

        print("PASS: Sequence numbers")
    finally:
        buffer.close()


def test_slot_reuse():
    buffer = RingBuffer(path="test_ring_reuse.bin", capacity=2)

    try:
        assert buffer.put(1, 100, 5) is True
        assert buffer.put(-1, 101, 3) is True
        assert buffer.put(1, 102, 4) is False

        first = buffer.get()
        assert first["price"] == 100

        # A consumed slot should become available again.
        assert buffer.put(-1, 103, 6) is True

        second = buffer.get()
        third = buffer.get()

        assert second["price"] == 101
        assert third["price"] == 103
        assert third["sequence"] == 3

        print("PASS: Slot reuse")
    finally:
        buffer.close()


def test_invalid_orders():
    buffer = RingBuffer(path="test_ring_invalid.bin", capacity=2)

    try:
        invalid_orders = [
            (0, 100, 5),
            (2, 100, 5),
            (1, 0, 5),
            (1, 100, 0),
            (-1, -100, 5),
        ]

        for side, price, quantity in invalid_orders:
            with pytest.raises(ValueError):
                buffer.put(side, price, quantity)

        print("PASS: Invalid-order validation")
    finally:
        buffer.close()


def test_invalid_order_preserves_buffer_state():
    buffer = RingBuffer(
        path="test_ring_invalid_state.bin",
        capacity=2
    )

    try:
        assert buffer.put(1, 100, 5) is True

        with pytest.raises(ValueError):
            buffer.put(0, 200, 10)

        # The original valid order must remain readable.
        first = buffer.get()

        assert first["sequence"] == 1
        assert first["side"] == 1
        assert first["price"] == 100
        assert first["quantity"] == 5

        # Invalid input must not consume a sequence number.
        assert buffer.put(-1, 101, 3) is True

        second = buffer.get()

        assert second["sequence"] == 2
        assert second["side"] == -1
        assert second["price"] == 101
        assert second["quantity"] == 3

        assert buffer.get() is None

        print("PASS: Invalid order preserves buffer state")
    finally:
        buffer.close()


def test_invalid_capacity_rejected():
    invalid_capacities = [0, -1, 1.5, True, "2"]

    for capacity in invalid_capacities:
        with pytest.raises(ValueError):
            RingBuffer(
                path=f"test_invalid_capacity_{str(capacity)}.bin",
                capacity=capacity
            )

    print("PASS: Invalid capacity validation")


def test_invalid_numeric_values_rejected():
    buffer = RingBuffer(
        path="test_ring_numeric_validation.bin",
        capacity=2
    )

    try:
        invalid_orders = [
            (1, True, 5),
            (1, 100, False),
            (1, 1.5, 5),
            (1, 100, 2.5),
            (1, 2**63, 5),
            (1, 100, 2**63),
        ]

        for side, price, quantity in invalid_orders:
            with pytest.raises(ValueError):
                buffer.put(side, price, quantity)

        # Invalid orders must not consume capacity or sequence numbers.
        assert buffer.put(1, 100, 5) is True

        first = buffer.get()
        assert first["sequence"] == 1
        assert buffer.get() is None

        print("PASS: Invalid numeric values validation")
    finally:
        buffer.close()


if __name__ == "__main__":
    tests = [
        test_empty_buffer,
        test_full_buffer,
        test_fifo_order,
        test_sequence_numbers,
        test_slot_reuse,
        test_invalid_orders,
        test_invalid_order_preserves_buffer_state,
        test_invalid_capacity_rejected,
        test_invalid_numeric_values_rejected,
    ]

    for test in tests:
        test()

    print("\nAll ring buffer tests passed!")
