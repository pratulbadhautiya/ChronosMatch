
# matching_engine.pyx
# Cython-based Price-Time Priority Matching Engine

from libc.stdint cimport int64_t
from libc.stdlib cimport malloc, free


cdef struct OrderNode:
    int64_t order_id
    int64_t quantity
    OrderNode* next


cdef struct PriceLevel:
    int64_t price
    OrderNode* head
    OrderNode* tail
    PriceLevel* next


cdef class MatchingEngine:
    cdef PriceLevel* bids
    cdef PriceLevel* asks

    cdef int capacity
    cdef int count

    cdef int64_t next_id
    cdef int64_t last_trade_price
    cdef int64_t trades
    cdef int64_t volume

    def __cinit__(self, int capacity=10000):
        self.bids = NULL
        self.asks = NULL

        self.capacity = capacity
        self.count = 0
        self.next_id = 1
        self.last_trade_price = 0
        self.trades = 0
        self.volume = 0

        if capacity < 1:
            raise ValueError("Capacity must be positive")

    def __dealloc__(self):
        cdef PriceLevel* level
        cdef PriceLevel* next_level
        cdef OrderNode* order
        cdef OrderNode* next_order

        # Free BUY price levels and their orders.
        level = self.bids
        while level != NULL:
            next_level = level.next
            order = level.head

            while order != NULL:
                next_order = order.next
                free(order)
                order = next_order

            free(level)
            level = next_level

        # Free SELL price levels and their orders.
        level = self.asks
        while level != NULL:
            next_level = level.next
            order = level.head

            while order != NULL:
                next_order = order.next
                free(order)
                order = next_order

            free(level)
            level = next_level

    cdef void _add_resting_order(
        self,
        int side,
        int64_t price,
        int64_t order_id,
        int64_t quantity
    ) except *:
        cdef PriceLevel* level
        cdef PriceLevel* previous
        cdef PriceLevel* new_level
        cdef OrderNode* new_order
        cdef PriceLevel** root

        root = &self.bids if side == 1 else &self.asks

        previous = NULL
        level = root[0]

        # Bids: highest price first.
        # Asks: lowest price first.
        while level != NULL:
            if level.price == price:
                break

            if (
                (side == 1 and level.price < price)
                or
                (side == -1 and level.price > price)
            ):
                break

            previous = level
            level = level.next

        # Create a new price level when needed.
        if level == NULL or level.price != price:
            new_level = <PriceLevel*>malloc(sizeof(PriceLevel))

            if new_level == NULL:
                raise MemoryError("Unable to allocate price level")

            new_level.price = price
            new_level.head = NULL
            new_level.tail = NULL
            new_level.next = level

            if previous == NULL:
                root[0] = new_level
            else:
                previous.next = new_level

            level = new_level

        # Allocate a new order node.
        new_order = <OrderNode*>malloc(sizeof(OrderNode))

        if new_order == NULL:
            # Remove an empty price level created above.
            if level.head == NULL:
                if previous == NULL:
                    root[0] = level.next
                else:
                    previous.next = level.next
                free(level)

            raise MemoryError("Unable to allocate order")

        new_order.order_id = order_id
        new_order.quantity = quantity
        new_order.next = NULL

        # Append to the tail to preserve FIFO priority.
        if level.tail == NULL:
            level.head = new_order
            level.tail = new_order
        else:
            level.tail.next = new_order
            level.tail = new_order

        self.count += 1

    cpdef dict submit(self, int side, int64_t price, int64_t quantity):
        cdef int64_t order_id
        cdef int64_t remaining
        cdef int64_t filled = 0
        cdef int64_t fill_qty

        cdef PriceLevel* level
        cdef PriceLevel* next_level
        cdef OrderNode* resting

        if side != 1 and side != -1:
            raise ValueError("side must be 1 (BUY) or -1 (SELL)")

        if price <= 0 or quantity <= 0:
            raise ValueError("price and quantity must be positive")

        order_id = self.next_id
        remaining = quantity

        # Match incoming order against the best opposite-side price.
        while remaining > 0:
            if side == 1:
                level = self.asks

                if level == NULL or level.price > price:
                    break
            else:
                level = self.bids

                if level == NULL or level.price < price:
                    break

            # FIFO: oldest order at this price is always first.
            resting = level.head

            fill_qty = remaining

            if resting.quantity < fill_qty:
                fill_qty = resting.quantity

            remaining -= fill_qty
            resting.quantity -= fill_qty
            filled += fill_qty

            self.trades += 1
            self.volume += fill_qty
            self.last_trade_price = level.price

            # Remove a fully filled order.
            if resting.quantity == 0:
                level.head = resting.next

                if level.head == NULL:
                    level.tail = NULL

                free(resting)
                self.count -= 1

            # Remove the price level when it becomes empty.
            if level.head == NULL:
                next_level = level.next

                if side == 1:
                    self.asks = next_level
                else:
                    self.bids = next_level

                free(level)

        # Add any unfilled quantity to the appropriate book.
        if remaining > 0:
            if self.count >= self.capacity:
                raise OverflowError(
                    "Order book capacity reached; "
                    "unfilled quantity could not be stored"
                )

            self._add_resting_order(
                side,
                price,
                order_id,
                remaining
            )

        self.next_id += 1

        if remaining == 0:
            status = "FILLED"
        elif filled > 0:
            status = "PARTIAL"
        else:
            status = "RESTING"

        return {
            "order_id": order_id,
            "filled_quantity": filled,
            "remaining_quantity": remaining,
            "status": status,
        }

    cpdef list snapshot(self):
        cdef list result = []
        cdef PriceLevel* level
        cdef OrderNode* order

        # BUY orders: highest price first, FIFO within each level.
        level = self.bids

        while level != NULL:
            order = level.head

            while order != NULL:
                result.append({
                    "order_id": order.order_id,
                    "side": "BUY",
                    "price": level.price,
                    "quantity": order.quantity,
                })

                order = order.next

            level = level.next

        # SELL orders: lowest price first, FIFO within each level.
        level = self.asks

        while level != NULL:
            order = level.head

            while order != NULL:
                result.append({
                    "order_id": order.order_id,
                    "side": "SELL",
                    "price": level.price,
                    "quantity": order.quantity,
                })

                order = order.next

            level = level.next

        return result

    cpdef dict stats(self):
        return {
            "resting_orders": self.count,
            "trades": self.trades,
            "volume": self.volume,
            "last_trade_price": self.last_trade_price,
        }
