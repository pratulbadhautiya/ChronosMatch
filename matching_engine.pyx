
# matching_engine.pyx
# Cython-based Price-Time Priority Matching Engine
# Hardened capacity checks and memory allocation before matching.

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

        if capacity < 1:
            raise ValueError("Capacity must be positive")

        self.capacity = capacity
        self.count = 0
        self.next_id = 1
        self.last_trade_price = 0
        self.trades = 0
        self.volume = 0

    def __dealloc__(self):
        cdef PriceLevel* level
        cdef PriceLevel* next_level
        cdef OrderNode* order
        cdef OrderNode* next_order

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

    cpdef dict submit(self, int side, int64_t price, int64_t quantity):
        cdef int64_t order_id
        cdef int64_t remaining
        cdef int64_t filled = 0
        cdef int64_t fill_qty

        cdef int64_t simulated_remaining
        cdef int removed_orders = 0

        cdef PriceLevel* level
        cdef PriceLevel* next_level
        cdef PriceLevel* own_level
        cdef PriceLevel* previous
        cdef PriceLevel* new_level = NULL
        cdef PriceLevel** root

        cdef OrderNode* resting
        cdef OrderNode* simulated_order
        cdef OrderNode* new_order = NULL

        if side != 1 and side != -1:
            raise ValueError("side must be 1 (BUY) or -1 (SELL)")

        if price <= 0 or quantity <= 0:
            raise ValueError("price and quantity must be positive")

        order_id = self.next_id

        # ---------------------------------------------------------
        # 1. Preflight the match without changing the order book.
        #    Count how many resting orders would be completely removed.
        # ---------------------------------------------------------
        simulated_remaining = quantity

        if side == 1:
            level = self.asks
        else:
            level = self.bids

        while level != NULL and simulated_remaining > 0:
            if side == 1 and level.price > price:
                break

            if side == -1 and level.price < price:
                break

            simulated_order = level.head

            while simulated_order != NULL and simulated_remaining > 0:
                if simulated_order.quantity <= simulated_remaining:
                    simulated_remaining -= simulated_order.quantity
                    removed_orders += 1
                    simulated_order = simulated_order.next
                else:
                    simulated_remaining = 0

            if simulated_remaining > 0:
                level = level.next

        # Reject before any trade or book mutation if the remainder
        # cannot fit in the available order capacity.
        if (
            simulated_remaining > 0
            and self.count - removed_orders >= self.capacity
        ):
            raise OverflowError(
                "Order book capacity reached; "
                "order was not submitted"
            )

        # ---------------------------------------------------------
        # 2. Allocate memory before matching.
        #    This avoids allocation failures after trades have begun.
        # ---------------------------------------------------------
        new_order = <OrderNode*>malloc(sizeof(OrderNode))

        if new_order == NULL:
            raise MemoryError("Unable to allocate order")

        new_order.order_id = order_id
        new_order.quantity = quantity
        new_order.next = NULL

        # Find the same-price level on the incoming order's own side.
        root = &self.bids if side == 1 else &self.asks

        own_level = root[0]
        previous = NULL

        while own_level != NULL:
            if own_level.price == price:
                break

            if (
                (side == 1 and own_level.price < price)
                or (side == -1 and own_level.price > price)
            ):
                break

            previous = own_level
            own_level = own_level.next

        # A new level is needed only if the incoming order will rest
        # and there is no existing level at its price.
        if simulated_remaining > 0 and (
            own_level == NULL or own_level.price != price
        ):
            new_level = <PriceLevel*>malloc(sizeof(PriceLevel))

            if new_level == NULL:
                free(new_order)
                raise MemoryError("Unable to allocate price level")

            new_level.price = price
            new_level.head = NULL
            new_level.tail = NULL
            new_level.next = NULL

        # ---------------------------------------------------------
        # 3. Execute matching using best-price then FIFO priority.
        # ---------------------------------------------------------
        remaining = quantity

        while remaining > 0:
            if side == 1:
                level = self.asks

                if level == NULL or level.price > price:
                    break
            else:
                level = self.bids

                if level == NULL or level.price < price:
                    break

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

            if resting.quantity == 0:
                level.head = resting.next

                if level.head == NULL:
                    level.tail = NULL

                free(resting)
                self.count -= 1

            if level.head == NULL:
                next_level = level.next

                if side == 1:
                    self.asks = next_level
                else:
                    self.bids = next_level

                free(level)

        # ---------------------------------------------------------
        # 4. Rest any unfilled quantity without further allocation.
        # ---------------------------------------------------------
        if remaining > 0:
            new_order.quantity = remaining

            # Re-find insertion position on the incoming side.
            # The opposite-side matching above cannot alter this side.
            own_level = root[0]
            previous = NULL

            while own_level != NULL:
                if own_level.price == price:
                    break

                if (
                    (side == 1 and own_level.price < price)
                    or (side == -1 and own_level.price > price)
                ):
                    break

                previous = own_level
                own_level = own_level.next

            if own_level != NULL and own_level.price == price:
                # Append to the existing price level to preserve FIFO.
                if own_level.tail == NULL:
                    own_level.head = new_order
                    own_level.tail = new_order
                else:
                    own_level.tail.next = new_order
                    own_level.tail = new_order

                # The spare level was not required after all.
                if new_level != NULL:
                    free(new_level)
                    new_level = NULL

            else:
                # Insert the preallocated price level in sorted order.
                new_level.next = own_level

                if previous == NULL:
                    root[0] = new_level
                else:
                    previous.next = new_level

                new_level.head = new_order
                new_level.tail = new_order
                new_level = NULL

            new_order = NULL
            self.count += 1

        else:
            # Fully matched: no incoming order remains in the book.
            free(new_order)
            new_order = NULL

            if new_level != NULL:
                free(new_level)
                new_level = NULL

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
