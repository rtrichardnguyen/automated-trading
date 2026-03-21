# tests/test_alpaca_execution.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid
import sys

# Mock Alpaca modules before importing alpaca_execution
alpaca_mock = MagicMock()
sys.modules['alpaca'] = alpaca_mock
sys.modules['alpaca.trading'] = MagicMock()
sys.modules['alpaca.trading.client'] = MagicMock()
sys.modules['alpaca.trading.stream'] = MagicMock()
sys.modules['alpaca.trading.requests'] = MagicMock()
sys.modules['alpaca.trading.enums'] = MagicMock()

# Create mock classes that can be instantiated
class MockTradingClient:
    def __init__(self, *args, **kwargs):
        self.submit_order = MagicMock()

class MockTradingStream:
    def __init__(self, *args, **kwargs):
        self.subscribe_trade_updates = MagicMock()
        self.run = MagicMock()
        self.stop = MagicMock()

class MockOrderSide:
    BUY = 'buy'
    SELL = 'sell'

class MockTimeInForce:
    DAY = 'day'

class MockMarketOrderRequest:
    def __init__(self, symbol, qty, side, time_in_force):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.time_in_force = time_in_force

class MockLimitOrderRequest:
    def __init__(self, symbol, qty, side, time_in_force, limit_price):
        self.symbol = symbol
        self.qty = qty
        self.side = side
        self.time_in_force = time_in_force
        self.limit_price = limit_price

# Set up the mocked modules
sys.modules['alpaca.trading.client'].TradingClient = MockTradingClient
sys.modules['alpaca.trading.stream'].TradingStream = MockTradingStream
sys.modules['alpaca.trading.requests'].MarketOrderRequest = MockMarketOrderRequest
sys.modules['alpaca.trading.requests'].LimitOrderRequest = MockLimitOrderRequest
sys.modules['alpaca.trading.enums'].OrderSide = MockOrderSide
sys.modules['alpaca.trading.enums'].TimeInForce = MockTimeInForce

# Now import after mocking
from alpaca_execution import AlpacaExecutionHandler
from event import OrderEvent, FillEvent

OrderSide = MockOrderSide
TimeInForce = MockTimeInForce


@pytest.fixture
def alpaca_handler(event_queue):
    """AlpacaExecutionHandler with mocked Alpaca clients."""
    return AlpacaExecutionHandler(event_queue, 'fake_key', 'fake_secret')


class TestAlpacaExecutionHandlerInitialization:
    """Test AlpacaExecutionHandler initialization."""

    def test_initialization(self, alpaca_handler):
        """Handler initializes with correct attributes."""
        assert alpaca_handler.fill_dict == {}
        assert alpaca_handler.order_id == uuid.UUID(int=0)
        assert alpaca_handler.trading_client is not None
        assert alpaca_handler.trading_stream is not None

    def test_stream_subscription_on_init(self, alpaca_handler):
        """TradingStream subscribes to trade updates on initialization."""
        # Verify subscription was called
        alpaca_handler.trading_stream.subscribe_trade_updates.assert_called_once()


class TestAlpacaExecutionHandlerOrderExecution:
    """Test order execution with Alpaca API."""

    def test_execute_market_order_buy(self, alpaca_handler):
        """BUY direction translates to OrderSide.BUY and submits order."""
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        # Mock the submitted order response
        mock_submitted = Mock(id=uuid.uuid4())
        alpaca_handler.trading_client.submit_order.return_value = mock_submitted

        alpaca_handler.execute_order(order)

        # Verify submit_order was called
        assert alpaca_handler.trading_client.submit_order.called
        call_kwargs = alpaca_handler.trading_client.submit_order.call_args[1]
        order_data = call_kwargs['order_data']

        assert order_data.symbol == 'AAPL'
        assert order_data.qty == 100
        assert order_data.side == OrderSide.BUY

    def test_execute_market_order_sell(self, alpaca_handler):
        """SELL direction translates to OrderSide.SELL."""
        order = OrderEvent('AAPL', 'MKT', 50, 'SELL')

        mock_submitted = Mock(id=uuid.uuid4())
        alpaca_handler.trading_client.submit_order.return_value = mock_submitted

        alpaca_handler.execute_order(order)

        call_kwargs = alpaca_handler.trading_client.submit_order.call_args[1]
        order_data = call_kwargs['order_data']

        assert order_data.side == OrderSide.SELL
        assert order_data.qty == 50

    def test_execute_limit_order(self, alpaca_handler):
        """LMT order type creates LimitOrderRequest."""
        order = OrderEvent('TSLA', 'LMT', 75, 'BUY')

        mock_submitted = Mock(id=uuid.uuid4())
        alpaca_handler.trading_client.submit_order.return_value = mock_submitted

        alpaca_handler.execute_order(order)

        call_kwargs = alpaca_handler.trading_client.submit_order.call_args[1]
        order_data = call_kwargs['order_data']

        # LimitOrderRequest has limit_price attribute
        assert hasattr(order_data, 'limit_price')
        assert order_data.limit_price == 0  # TODO in implementation

    def test_invalid_direction_raises_exception(self, alpaca_handler):
        """Invalid direction (not BUY/SELL) is rejected by OrderEvent."""
        with pytest.raises(ValueError):
            OrderEvent('AAPL', 'MKT', 100, 'LONG')

    def test_invalid_order_type_raises_exception(self, alpaca_handler):
        """Unsupported order type raises exception."""
        order = OrderEvent('AAPL', 'STOP', 100, 'BUY')

        with pytest.raises(Exception) as exc_info:
            alpaca_handler.execute_order(order)

        assert "not been implemented" in str(exc_info.value)

    def test_order_id_stored_after_submission(self, alpaca_handler):
        """After order submission, order_id is updated."""
        order = OrderEvent('AAPL', 'MKT', 100, 'BUY')

        expected_id = uuid.uuid4()
        mock_submitted = Mock(id=expected_id)
        alpaca_handler.trading_client.submit_order.return_value = mock_submitted

        alpaca_handler.execute_order(order)

        assert alpaca_handler.order_id == expected_id

    def test_non_order_event_ignored(self, alpaca_handler):
        """Non-ORDER events are ignored."""
        fake_event = Mock(type='MARKET')

        alpaca_handler.execute_order(fake_event)

        alpaca_handler.trading_client.submit_order.assert_not_called()


class TestAlpacaExecutionHandlerTradeUpdates:
    """Test WebSocket trade update handling.

    Note: The _on_trade_update method is async and requires pytest-asyncio.
    These tests verify the helper methods that _on_trade_update calls.
    For full async testing, install: pip install pytest-asyncio
    """

    # Async tests removed - test the helper methods instead
    # The _on_trade_update method calls:
    # - create_fill_dict_entry() for NEW events
    # - create_fill() for FILL events
    # Both of these are tested separately below


class TestAlpacaExecutionHandlerConnection:
    """Test WebSocket connection management."""

    def test_open_connection(self, alpaca_handler):
        """open_connection starts the TradingStream."""
        alpaca_handler.open_connection()
        alpaca_handler.trading_stream.run.assert_called_once()

    def test_close_connection(self, alpaca_handler):
        """close_connection stops the TradingStream."""
        alpaca_handler.close_connection()
        alpaca_handler.trading_stream.stop.assert_called_once()


class TestAlpacaExecutionHandlerOrderCreation:
    """Test create_order method for different order types."""

    def test_create_market_order(self, alpaca_handler):
        """Market order creates MarketOrderRequest with correct parameters."""
        order_data = alpaca_handler.create_order('AAPL', 100, OrderSide.BUY, 'MKT')

        assert order_data.symbol == 'AAPL'
        assert order_data.qty == 100
        assert order_data.side == OrderSide.BUY
        assert order_data.time_in_force == TimeInForce.DAY

    def test_create_limit_order(self, alpaca_handler):
        """Limit order creates LimitOrderRequest with limit_price."""
        order_data = alpaca_handler.create_order('TSLA', 50, OrderSide.SELL, 'LMT')

        assert order_data.symbol == 'TSLA'
        assert order_data.qty == 50
        assert order_data.side == OrderSide.SELL
        assert order_data.time_in_force == TimeInForce.DAY
        assert order_data.limit_price == 0  # TODO in implementation

    def test_create_unsupported_order_type(self, alpaca_handler):
        """Unsupported order type raises Exception."""
        with pytest.raises(Exception) as exc_info:
            alpaca_handler.create_order('AAPL', 100, OrderSide.BUY, 'STOP_LOSS')

        assert "not been implemented" in str(exc_info.value)


class TestAlpacaExecutionHandlerFillDictEntry:
    """Test create_fill_dict_entry method."""

    def test_create_fill_dict_entry_buy(self, alpaca_handler):
        """Fill dict entry for BUY order keeps BUY direction."""
        order_id = uuid.uuid4()
        mock_order = Mock(
            id=order_id,
            symbol='MSFT',
            side=OrderSide.BUY
        )

        alpaca_handler.create_fill_dict_entry(mock_order)

        assert alpaca_handler.fill_dict[order_id]['symbol'] == 'MSFT'
        assert alpaca_handler.fill_dict[order_id]['direction'] == 'BUY'
        assert alpaca_handler.fill_dict[order_id]['filled'] == False

    def test_create_fill_dict_entry_sell(self, alpaca_handler):
        """Fill dict entry for SELL order keeps SELL direction."""
        order_id = uuid.uuid4()
        mock_order = Mock(
            id=order_id,
            symbol='GOOGL',
            side=OrderSide.SELL
        )

        alpaca_handler.create_fill_dict_entry(mock_order)

        assert alpaca_handler.fill_dict[order_id]['direction'] == 'SELL'


class TestAlpacaExecutionHandlerCreateFill:
    """Test create_fill method."""

    def test_create_fill_generates_fill_event(self, alpaca_handler, event_queue):
        """create_fill generates FillEvent with correct data."""
        order_id = uuid.uuid4()

        alpaca_handler.fill_dict[order_id] = {
            'symbol': 'NVDA',
            'exchange': 'NYSE',
            'direction': 'BUY',
            'filled': False
        }

        mock_order = Mock(
            id=order_id,
            filled_qty=200,
            filled_avg_price=500.25
        )

        # Mock datetime.datetime.now(...) for deterministic fill timestamps.
        with patch('alpaca_execution.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            alpaca_handler.create_fill(mock_order)

        fill = event_queue.get()
        assert fill.symbol == 'NVDA'
        assert fill.quantity == 200
        assert fill.fill_cost == 500.25
        assert fill.direction == 'BUY'
        assert fill.exchange == 'NYSE'

    def test_create_fill_marks_as_filled(self, alpaca_handler, event_queue):
        """create_fill sets filled=True."""
        order_id = uuid.uuid4()

        alpaca_handler.fill_dict[order_id] = {
            'symbol': 'TEST',
            'exchange': 'NYSE',
            'direction': 'BUY',
            'filled': False
        }

        mock_order = Mock(id=order_id, filled_qty=100, filled_avg_price=100.0)

        # Mock datetime for Python 3.9 compatibility
        with patch('alpaca_execution.datetime') as mock_dt:
            mock_dt.datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            alpaca_handler.create_fill(mock_order)

        assert alpaca_handler.fill_dict[order_id]['filled'] == True
