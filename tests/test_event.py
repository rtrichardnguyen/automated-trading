# tests/test_event.py

import pytest
from datetime import datetime
from event import Event, MarketEvent, SignalEvent, OrderEvent, FillEvent


class TestMarketEvent:
    """Test MarketEvent class."""

    def test_market_event_creation(self):
        """Test MarketEvent can be created and has correct type."""
        event = MarketEvent()
        assert event.type == 'MARKET'

    def test_market_event_inherits_from_event(self):
        """Test MarketEvent is a subclass of Event."""
        event = MarketEvent()
        assert isinstance(event, Event)


class TestSignalEvent:
    """Test SignalEvent class."""

    def test_signal_event_creation(self):
        """Test SignalEvent creation with valid parameters."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        signal = SignalEvent(
            strategy_id=1,
            symbol='AAPL',
            datetime=dt,
            signal_type='LONG',
            strength=1.0
        )

        assert signal.type == 'SIGNAL'
        assert signal.strategy_id == 1
        assert signal.symbol == 'AAPL'
        assert signal.datetime == dt
        assert signal.signal_type == 'LONG'
        assert signal.strength == 1.0

    def test_signal_event_short(self):
        """Test SignalEvent with SHORT signal."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        signal = SignalEvent(1, 'AAPL', dt, 'SHORT', 1.0)
        assert signal.signal_type == 'SHORT'

    def test_signal_event_exit(self):
        """Test SignalEvent with EXIT signal."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        signal = SignalEvent(1, 'AAPL', dt, 'EXIT', 1.0)
        assert signal.signal_type == 'EXIT'

    def test_signal_event_inherits_from_event(self):
        """Test SignalEvent is a subclass of Event."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        signal = SignalEvent(1, 'AAPL', dt, 'LONG', 1.0)
        assert isinstance(signal, Event)


class TestOrderEvent:
    """Test OrderEvent class."""

    def test_order_event_creation_buy(self):
        """Test OrderEvent creation with BUY direction."""
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        assert order.type == 'ORDER'
        assert order.symbol == 'AAPL'
        assert order.order_type == 'MKT'
        assert order.quantity == 100
        assert order.direction == 'BUY'

    def test_order_event_creation_sell(self):
        """Test OrderEvent creation with SELL direction."""
        order = OrderEvent('AAPL', 'MKT', 50, 'SELL')
        assert order.direction == 'SELL'
        assert order.quantity == 50

    def test_order_event_limit_order(self):
        """Test OrderEvent with limit order type."""
        order = OrderEvent('AAPL', 'LMT', 100, 'BUY')
        assert order.order_type == 'LMT'

    def test_order_event_invalid_quantity_zero(self):
        """Test OrderEvent raises error for zero quantity."""
        with pytest.raises(ValueError):
            OrderEvent('AAPL', 'MKT', 0, 'BUY')

    def test_order_event_invalid_quantity_negative(self):
        """Test OrderEvent raises error for negative quantity."""
        with pytest.raises(ValueError):
            OrderEvent('AAPL', 'MKT', -10, 'BUY')

    def test_order_event_invalid_quantity_float(self):
        """Test OrderEvent raises error for non-integer quantity."""
        with pytest.raises(ValueError):
            OrderEvent('AAPL', 'MKT', 10.5, 'BUY')

    def test_order_event_print_order(self, capsys):
        """Test print_order method outputs correctly."""
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')
        order.print_order()
        captured = capsys.readouterr()
        assert 'AAPL' in captured.out
        assert 'MKT' in captured.out
        assert '100' in captured.out
        assert 'BUY' in captured.out

    def test_order_event_inherits_from_event(self):
        """Test OrderEvent is a subclass of Event."""
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')
        assert isinstance(order, Event)


class TestFillEvent:
    """Test FillEvent class."""

    def test_fill_event_creation_with_commission(self):
        """Test FillEvent creation with specified commission."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(
            timeindex=dt,
            symbol='AAPL',
            exchange='NYSE',
            quantity=100,
            direction='BUY',
            fill_cost=150.0,
            commission=1.0
        )

        assert fill.type == 'FILL'
        assert fill.timeindex == dt
        assert fill.symbol == 'AAPL'
        assert fill.exchange == 'NYSE'
        assert fill.quantity == 100
        assert fill.direction == 'BUY'
        assert fill.fill_cost == 150.0
        assert fill.commission == 1.0

    def test_fill_event_creation_without_commission(self):
        """Test FillEvent creation without commission defaults to 0."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(dt, 'AAPL', 'NYSE', 100, 'BUY', 150.0)
        assert fill.commission == 0

    def test_fill_event_sell_direction(self):
        """Test FillEvent with SELL direction."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(dt, 'AAPL', 'NYSE', 50, 'SELL', 150.0)
        assert fill.direction == 'SELL'
        assert fill.quantity == 50

    def test_fill_event_inherits_from_event(self):
        """Test FillEvent is a subclass of Event."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(dt, 'AAPL', 'NYSE', 100, 'BUY', 150.0)
        assert isinstance(fill, Event)

    def test_fill_event_commission_is_numeric(self):
        """Test commission is numeric type when defaulted."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(dt, 'AAPL', 'NYSE', 100, 'BUY', 150.0)
        assert isinstance(fill.commission, (int, float))

    def test_fill_event_with_none_fill_cost(self):
        """SimulatedExecutionHandler sends fill_cost=None. Must be stored as-is."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        fill = FillEvent(dt, 'AAPL', 'NYSE', 100, 'BUY', None)
        assert fill.fill_cost is None
        assert fill.commission == 0

    def test_order_event_boolean_quantity_accepted(self):
        """bool is a subclass of int in Python, so True (=1) passes the int check."""
        order = OrderEvent('AAPL', 'MKT', True, 'BUY')
        assert order.quantity == True
        assert isinstance(order.quantity, int)

    def test_order_event_string_quantity_rejected(self):
        """String quantity must raise ValueError."""
        with pytest.raises(ValueError):
            OrderEvent('AAPL', 'MKT', '100', 'BUY')
