# tests/test_execution.py

import pytest
from datetime import UTC, datetime
from execution import SimulatedExecutionHandler
from event import OrderEvent, FillEvent


class TestSimulatedExecutionHandler:
    """Test SimulatedExecutionHandler class."""

    def test_initialization(self, event_queue):
        """Test handler can be initialized."""
        handler = SimulatedExecutionHandler(event_queue)
        assert handler.events == event_queue

    def test_execute_market_order_buy(self, event_queue):
        """Test executing a market BUY order produces matching fill."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        handler.execute_order(order)

        assert not event_queue.empty()
        fill = event_queue.get()

        assert fill.type == 'FILL'
        assert fill.symbol == 'AAPL'
        assert fill.quantity == 100
        assert fill.direction == 'BUY'
        assert fill.exchange == 'NYSE'
        assert fill.commission == 0

    def test_execute_market_order_sell(self, event_queue):
        """Test executing a market SELL order produces matching fill."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 50, 'SELL')

        handler.execute_order(order)

        fill = event_queue.get()
        assert fill.direction == 'SELL'
        assert fill.quantity == 50
        assert fill.commission == 0

    def test_execute_limit_order(self, event_queue):
        """Test executing a limit order (treated same as market in simulation)."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'LMT', 100, 'BUY')

        handler.execute_order(order)

        fill = event_queue.get()
        assert fill.type == 'FILL'
        assert fill.symbol == 'AAPL'

    def test_execute_non_order_event(self, event_queue):
        """Test that non-ORDER events are ignored."""
        handler = SimulatedExecutionHandler(event_queue)

        class MockEvent:
            type = 'MARKET'

        handler.execute_order(MockEvent())

        assert event_queue.empty()

    def test_multiple_orders_fill_consistency(self, event_queue):
        """Test each order produces a fill with matching symbol, quantity, direction."""
        handler = SimulatedExecutionHandler(event_queue)

        orders = [
            OrderEvent('AAPL', 'MKT', 100, 'BUY'),
            OrderEvent('GOOGL', 'MKT', 50, 'SELL'),
            OrderEvent('MSFT', 'MKT', 75, 'BUY'),
        ]

        for order in orders:
            handler.execute_order(order)

        assert event_queue.qsize() == 3

        for order in orders:
            fill = event_queue.get()
            assert fill.symbol == order.symbol
            assert fill.quantity == order.quantity
            assert fill.direction == order.direction
            assert fill.commission == 0

    def test_fill_timestamp(self, event_queue):
        """Test that fills have a timestamp between before and after execution."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        before = datetime.now(UTC)
        handler.execute_order(order)
        after = datetime.now(UTC)

        fill = event_queue.get()
        assert before <= fill.timeindex <= after

    def test_fill_cost_is_none(self, event_queue):
        """SimulatedExecutionHandler sets fill_cost=None (portfolio uses bar price instead)."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')
        handler.execute_order(order)

        fill = event_queue.get()
        assert fill.fill_cost is None

    def test_queue_has_exactly_one_fill_per_order(self, event_queue):
        """Each order produces exactly one fill event, no more."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')
        handler.execute_order(order)

        assert event_queue.qsize() == 1
        fill = event_queue.get()
        assert fill.type == 'FILL'
        assert event_queue.empty()
