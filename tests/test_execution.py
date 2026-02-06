# tests/test_execution.py

import pytest
from datetime import datetime
from execution import SimulatedExecutionHandler
from event import OrderEvent, FillEvent


class TestSimulatedExecutionHandler:
    """Test SimulatedExecutionHandler class."""

    def test_initialization(self, event_queue):
        """Test handler can be initialized."""
        handler = SimulatedExecutionHandler(event_queue)
        assert handler.events == event_queue

    def test_execute_market_order_buy(self, event_queue):
        """Test executing a market BUY order."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        handler.execute_order(order)

        # Check that a fill event was added to the queue
        assert not event_queue.empty()
        fill = event_queue.get()

        assert fill.type == 'FILL'
        assert fill.symbol == 'AAPL'
        assert fill.quantity == 100
        assert fill.direction == 'BUY'
        assert fill.exchange == 'NYSE'

    def test_execute_market_order_sell(self, event_queue):
        """Test executing a market SELL order."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 50, 'SELL')

        handler.execute_order(order)

        fill = event_queue.get()
        assert fill.direction == 'SELL'
        assert fill.quantity == 50

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

        # Create a mock event with non-ORDER type
        class MockEvent:
            type = 'MARKET'

        handler.execute_order(MockEvent())

        # Queue should be empty
        assert event_queue.empty()

    def test_multiple_orders(self, event_queue):
        """Test executing multiple orders in sequence."""
        handler = SimulatedExecutionHandler(event_queue)

        order1 = OrderEvent('AAPL', 'MKT', 100, 'BUY')
        order2 = OrderEvent('GOOGL', 'MKT', 50, 'SELL')
        order3 = OrderEvent('MSFT', 'MKT', 75, 'BUY')

        handler.execute_order(order1)
        handler.execute_order(order2)
        handler.execute_order(order3)

        # Should have 3 fills in the queue
        assert event_queue.qsize() == 3

        fill1 = event_queue.get()
        assert fill1.symbol == 'AAPL'
        assert fill1.quantity == 100

        fill2 = event_queue.get()
        assert fill2.symbol == 'GOOGL'
        assert fill2.quantity == 50

        fill3 = event_queue.get()
        assert fill3.symbol == 'MSFT'
        assert fill3.quantity == 75

    def test_fill_timestamp(self, event_queue):
        """Test that fills have a timestamp."""
        handler = SimulatedExecutionHandler(event_queue)
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        before = datetime.utcnow()
        handler.execute_order(order)
        after = datetime.utcnow()

        fill = event_queue.get()
        assert before <= fill.timeindex <= after
