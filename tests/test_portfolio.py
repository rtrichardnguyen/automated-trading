# tests/test_portfolio.py

import pytest
from datetime import datetime
from portfolio import Portfolio
from event import SignalEvent, FillEvent, OrderEvent, MarketEvent


class MockDataHandler:
    """Mock DataHandler for testing Portfolio."""

    def __init__(self, symbol_list):
        self.symbol_list = symbol_list
        self._bar_data = {}
        for symbol in symbol_list:
            self._bar_data[symbol] = [(datetime(2024, 1, 1), type('Bar', (), {
                'adj_close': 100.0,
                'open': 99.0,
                'close': 100.0,
                'volume': 1000000
            })())]

    def get_latest_bar_datetime(self, symbol):
        return self._bar_data[symbol][-1][0]

    def get_latest_bar_value(self, symbol, val_type):
        return getattr(self._bar_data[symbol][-1][1], val_type)


@pytest.fixture
def mock_data_handler(symbol_list):
    """Provides a mock data handler."""
    return MockDataHandler(symbol_list)


@pytest.fixture
def portfolio(mock_data_handler, event_queue, start_date, initial_capital):
    """Provides a portfolio instance for testing."""
    return Portfolio(mock_data_handler, event_queue, start_date, initial_capital)


class TestPortfolioInitialization:
    """Test Portfolio initialization."""

    def test_initialization(self, portfolio, symbol_list, initial_capital):
        """Test portfolio initializes with correct values."""
        assert portfolio.initial_capital == initial_capital
        assert portfolio.symbol_list == symbol_list
        assert portfolio.current_holdings['cash'] == initial_capital
        assert portfolio.current_holdings['total'] == initial_capital

    def test_initial_positions(self, portfolio, symbol_list):
        """Test all positions start at zero."""
        for symbol in symbol_list:
            assert portfolio.current_positions[symbol] == 0

    def test_all_positions_initialized(self, portfolio):
        """Test all_positions list is initialized with start date."""
        assert len(portfolio.all_positions) == 1
        assert 'datetime' in portfolio.all_positions[0]

    def test_all_holdings_initialized(self, portfolio):
        """Test all_holdings list is initialized."""
        assert len(portfolio.all_holdings) == 1
        assert portfolio.all_holdings[0]['cash'] == portfolio.initial_capital


class TestPortfolioSignalHandling:
    """Test Portfolio signal handling and order generation."""

    def test_update_signal_long(self, portfolio, event_queue):
        """Test portfolio generates BUY order from LONG signal."""
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'LONG', 1.0)
        portfolio.update_signal(signal)

        # Should have an order in the queue
        assert not event_queue.empty()
        order = event_queue.get()

        assert order.type == 'ORDER'
        assert order.symbol == 'TEST'
        assert order.direction == 'BUY'
        assert order.quantity == 100  # Default quantity

    def test_update_signal_short(self, portfolio, event_queue):
        """Test portfolio generates SELL order from SHORT signal."""
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'SHORT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'SELL'
        assert order.quantity == 100

    def test_update_signal_exit_long_position(self, portfolio, event_queue):
        """Test portfolio generates SELL order from EXIT signal when holding long."""
        # First, establish a long position
        portfolio.current_positions['TEST'] = 100

        # Now send EXIT signal
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'EXIT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'SELL'
        assert order.quantity == 100

    def test_update_signal_exit_short_position(self, portfolio, event_queue):
        """Test portfolio generates BUY order from EXIT signal when holding short."""
        # Establish a short position
        portfolio.current_positions['TEST'] = -50

        # Send EXIT signal
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'EXIT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'BUY'
        assert order.quantity == 50

    def test_update_signal_no_duplicate_long(self, portfolio, event_queue):
        """Test portfolio doesn't generate duplicate LONG orders."""
        # Establish existing position
        portfolio.current_positions['TEST'] = 100

        # Send another LONG signal
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'LONG', 1.0)
        portfolio.update_signal(signal)

        # Should put None on queue (no order generated)
        order = event_queue.get()
        assert order is None


class TestPortfolioFillHandling:
    """Test Portfolio fill handling."""

    def test_update_fill_buy(self, portfolio, event_queue):
        """Test portfolio updates positions after BUY fill."""
        fill = FillEvent(
            datetime.utcnow(),
            'TEST',
            'NYSE',
            100,
            'BUY',
            100.0,
            commission=1.0
        )

        initial_cash = portfolio.current_holdings['cash']
        portfolio.update_fill(fill)

        # Position should increase
        assert portfolio.current_positions['TEST'] == 100

        # Cash should decrease by cost + commission
        expected_cash = initial_cash - (100 * 100.0 + 1.0)
        assert portfolio.current_holdings['cash'] == expected_cash

    def test_update_fill_sell(self, portfolio, event_queue):
        """Test portfolio updates positions after SELL fill."""
        # Start with a position
        portfolio.current_positions['TEST'] = 100

        fill = FillEvent(
            datetime.utcnow(),
            'TEST',
            'NYSE',
            50,
            'SELL',
            100.0,
            commission=1.0
        )

        initial_cash = portfolio.current_holdings['cash']
        portfolio.update_fill(fill)

        # Position should decrease
        assert portfolio.current_positions['TEST'] == 50

        # Cash should increase by proceeds minus commission
        expected_cash = initial_cash + (50 * 100.0 - 1.0)
        assert portfolio.current_holdings['cash'] == expected_cash

    def test_commission_tracking(self, portfolio):
        """Test commission is tracked in holdings."""
        fill = FillEvent(
            datetime.utcnow(),
            'TEST',
            'NYSE',
            100,
            'BUY',
            100.0,
            commission=5.0
        )

        portfolio.update_fill(fill)
        assert portfolio.current_holdings['commission'] == 5.0


class TestPortfolioTimeIndex:
    """Test Portfolio time index updates."""

    def test_update_timeindex(self, portfolio, mock_data_handler):
        """Test portfolio updates timeindex correctly."""
        market_event = MarketEvent()
        portfolio.update_timeindex(market_event)

        # Should have 2 entries now (initial + 1 update)
        assert len(portfolio.all_positions) == 2
        assert len(portfolio.all_holdings) == 2

    def test_timeindex_preserves_positions(self, portfolio, mock_data_handler):
        """Test timeindex update preserves current positions."""
        portfolio.current_positions['TEST'] = 50

        market_event = MarketEvent()
        portfolio.update_timeindex(market_event)

        # Latest positions entry should reflect current position
        assert portfolio.all_positions[-1]['TEST'] == 50


class TestPortfolioEquityCurve:
    """Test Portfolio equity curve generation."""

    def test_create_equity_curve_dataframe(self, portfolio, mock_data_handler):
        """Test equity curve DataFrame is created correctly."""
        # Add some time points
        for _ in range(5):
            portfolio.update_timeindex(MarketEvent())

        portfolio.create_equity_curve_dataframe()

        assert hasattr(portfolio, 'equity_curve')
        assert 'returns' in portfolio.equity_curve.columns
        assert 'equity_curve' in portfolio.equity_curve.columns
        assert len(portfolio.equity_curve) == 6  # Initial + 5 updates

    def test_output_summary_stats(self, portfolio, mock_data_handler, tmp_path, monkeypatch):
        """Test summary stats are generated."""
        # Change to temp directory for CSV output
        monkeypatch.chdir(tmp_path)

        # Add some time points
        for _ in range(10):
            portfolio.update_timeindex(MarketEvent())

        portfolio.create_equity_curve_dataframe()
        stats = portfolio.output_summary_stats()

        assert isinstance(stats, list)
        assert len(stats) == 4  # Total Return, Sharpe, Max DD, DD Duration
        assert stats[0][0] == 'Total Return'
        assert stats[1][0] == 'Sharpe Ratio'
        assert stats[2][0] == 'Max Drawdown'
        assert stats[3][0] == 'Drawdown Duration'

        # Check that equity.csv was created
        assert (tmp_path / 'equity.csv').exists()
