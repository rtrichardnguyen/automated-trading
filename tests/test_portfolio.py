# tests/test_portfolio.py

import pytest
from datetime import datetime
from portfolio import Portfolio
from event import SignalEvent, FillEvent, OrderEvent, MarketEvent


class MockDataHandler:
    """Mock DataHandler for testing Portfolio with known prices."""

    def __init__(self, symbol_list, price=100.0):
        self.symbol_list = symbol_list
        self._prices = {s: price for s in symbol_list}

    def get_latest_bar_datetime(self, symbol):
        return datetime(2024, 1, 1)

    def get_latest_bar_value(self, symbol, val_type):
        if val_type == 'adj_close':
            return self._prices[symbol]
        return 0.0

    def set_price(self, symbol, price):
        self._prices[symbol] = price


@pytest.fixture
def mock_data_handler(symbol_list):
    """Provides a mock data handler with price=100.0."""
    return MockDataHandler(symbol_list, price=100.0)


@pytest.fixture
def portfolio(mock_data_handler, event_queue, start_date, initial_capital):
    """Provides a portfolio instance for testing."""
    return Portfolio(mock_data_handler, event_queue, start_date, initial_capital)


class TestPortfolioInitialization:

    def test_cash_equals_initial_capital(self, portfolio):
        assert portfolio.current_holdings['cash'] == 100000.0
        assert portfolio.current_holdings['total'] == 100000.0

    def test_all_positions_start_at_zero(self, portfolio, symbol_list):
        for symbol in symbol_list:
            assert portfolio.current_positions[symbol] == 0

    def test_commission_starts_at_zero(self, portfolio):
        assert portfolio.current_holdings['commission'] == 0.0

    def test_all_positions_history_has_start_entry(self, portfolio, start_date):
        assert len(portfolio.all_positions) == 1
        assert portfolio.all_positions[0]['datetime'] == start_date

    def test_all_holdings_history_has_start_entry(self, portfolio):
        assert len(portfolio.all_holdings) == 1
        assert portfolio.all_holdings[0]['cash'] == 100000.0
        assert portfolio.all_holdings[0]['total'] == 100000.0


class TestPortfolioSignalHandling:

    def test_long_signal_generates_buy_order_for_100_shares(self, portfolio, event_queue):
        """LONG signal -> BUY order with fixed quantity of 100."""
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'LONG', 1.0)
        portfolio.update_signal(signal)

        assert not event_queue.empty()
        order = event_queue.get()
        assert order.type == 'ORDER'
        assert order.symbol == 'TEST'
        assert order.direction == 'BUY'
        assert order.quantity == 100

    def test_short_signal_generates_sell_order_for_100_shares(self, portfolio, event_queue):
        """SHORT signal -> SELL order with fixed quantity of 100."""
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'SHORT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'SELL'
        assert order.quantity == 100

    def test_exit_long_generates_sell_for_exact_position_size(self, portfolio, event_queue):
        """EXIT signal on 75-share long -> SELL 75 (not fixed 100)."""
        portfolio.current_positions['TEST'] = 75

        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'EXIT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'SELL'
        assert order.quantity == 75

    def test_exit_short_generates_buy_for_exact_position_size(self, portfolio, event_queue):
        """EXIT signal on 50-share short -> BUY 50."""
        portfolio.current_positions['TEST'] = -50

        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'EXIT', 1.0)
        portfolio.update_signal(signal)

        order = event_queue.get()
        assert order.direction == 'BUY'
        assert order.quantity == 50

    def test_no_order_for_long_when_position_exists(self, portfolio, event_queue):
        """LONG signal ignored when already holding (prevents pyramiding)."""
        portfolio.current_positions['TEST'] = 100
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'LONG', 1.0)
        portfolio.update_signal(signal)
        assert event_queue.empty()

    def test_no_order_for_short_when_position_exists(self, portfolio, event_queue):
        """SHORT signal ignored when already holding."""
        portfolio.current_positions['TEST'] = -100
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'SHORT', 1.0)
        portfolio.update_signal(signal)
        assert event_queue.empty()

    def test_exit_signal_on_flat_position_generates_nothing(self, portfolio, event_queue):
        """EXIT signal with 0 position -> no order."""
        signal = SignalEvent(1, 'TEST', datetime.utcnow(), 'EXIT', 1.0)
        portfolio.update_signal(signal)
        assert event_queue.empty()


class TestPortfolioFillHandling:
    """Test fill handling with hand-calculated expected values.

    Key behavior: Portfolio uses the CURRENT BAR PRICE (from bars.get_latest_bar_value),
    NOT the fill_cost from the FillEvent. This is the correct design for backtesting
    where SimulatedExecutionHandler sets fill_cost=None.
    """

    def test_buy_fill_updates_position(self, portfolio):
        """BUY 100 shares -> position goes from 0 to 100."""
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill)
        assert portfolio.current_positions['TEST'] == 100

    def test_sell_fill_updates_position(self, portfolio):
        """SELL 50 from 100-share position -> position becomes 50."""
        portfolio.current_positions['TEST'] = 100
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 50, 'SELL', None, commission=0.0)
        portfolio.update_fill(fill)
        assert portfolio.current_positions['TEST'] == 50

    def test_buy_fill_cash_calculation(self, portfolio):
        """
        BUY 100 shares, bar price = 100, commission = 1.0.
        cost = 100 * 100 * 1 = 10000
        cash = 100000 - (10000 + 1) = 89999
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=1.0)
        portfolio.update_fill(fill)
        assert portfolio.current_holdings['cash'] == 89999.0

    def test_sell_fill_cash_calculation(self, portfolio):
        """
        Start with 100 shares. SELL 50, bar price = 100, commission = 1.0.
        cost = 100 * 50 * (-1) = -5000
        cash = 100000 - (-5000 + 1) = 104999
        """
        portfolio.current_positions['TEST'] = 100
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 50, 'SELL', None, commission=1.0)
        portfolio.update_fill(fill)
        assert portfolio.current_holdings['cash'] == 104999.0

    def test_fill_cost_from_event_is_ignored(self, portfolio):
        """
        Portfolio uses bar price (100), NOT fill_cost.
        Even with fill_cost=999, cash should change by bar_price * qty = 10000.
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', 999.0, commission=0.0)
        portfolio.update_fill(fill)
        assert portfolio.current_holdings['cash'] == 90000.0  # 100000 - 100*100

    def test_fill_cost_none_handled(self, portfolio):
        """
        SimulatedExecutionHandler sends fill_cost=None.
        Portfolio must handle this without error (it ignores fill_cost).
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill)
        assert portfolio.current_positions['TEST'] == 100
        assert portfolio.current_holdings['cash'] == 90000.0

    def test_commission_accumulates(self, portfolio):
        """Two fills with commissions 5.0 and 3.0 -> total commission = 8.0."""
        fill1 = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=5.0)
        fill2 = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 50, 'BUY', None, commission=3.0)
        portfolio.update_fill(fill1)
        portfolio.update_fill(fill2)
        assert portfolio.current_holdings['commission'] == 8.0

    def test_round_trip_flat_price_commission_only_loss(self, portfolio):
        """
        Buy 100 at 100, sell 100 at 100. Commission = 2 each.
        Cash: 100000 - 10002 + 9998 = 99996. Loss = 4 (total commissions).
        """
        buy = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=2.0)
        sell = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'SELL', None, commission=2.0)
        portfolio.update_fill(buy)
        portfolio.update_fill(sell)

        assert portfolio.current_positions['TEST'] == 0
        assert portfolio.current_holdings['cash'] == 99996.0
        assert portfolio.current_holdings['commission'] == 4.0

    def test_profit_from_price_increase(self, portfolio, mock_data_handler):
        """
        Buy 100 at 100, price rises to 150, sell 100 at 150.
        Cash: 100000 - 10000 + 15000 = 105000. Profit = 5000.
        """
        # Buy at price 100
        buy = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(buy)
        assert portfolio.current_holdings['cash'] == 90000.0

        # Price rises to 150
        mock_data_handler.set_price('TEST', 150.0)

        # Sell at price 150
        sell = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'SELL', None, commission=0.0)
        portfolio.update_fill(sell)

        assert portfolio.current_positions['TEST'] == 0
        assert portfolio.current_holdings['cash'] == 105000.0

    def test_loss_from_price_decrease(self, portfolio, mock_data_handler):
        """
        Buy 100 at 100, price drops to 80, sell 100 at 80.
        Cash: 100000 - 10000 + 8000 = 98000. Loss = 2000.
        """
        buy = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(buy)

        mock_data_handler.set_price('TEST', 80.0)

        sell = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'SELL', None, commission=0.0)
        portfolio.update_fill(sell)

        assert portfolio.current_positions['TEST'] == 0
        assert portfolio.current_holdings['cash'] == 98000.0


class TestPortfolioTimeIndex:
    """Test the update_timeindex snapshot mechanism."""

    def test_total_equals_cash_plus_market_value(self, portfolio, mock_data_handler):
        """
        Mathematical invariant: after update_timeindex,
        total == cash + sum(position * price for each symbol).

        Buy 100 TEST at 100: cash = 90000, market = 100*100 = 10000, total = 100000.
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill)
        portfolio.update_timeindex(MarketEvent())

        latest = portfolio.all_holdings[-1]
        expected_total = latest['cash']
        for s in portfolio.symbol_list:
            expected_total += portfolio.current_positions[s] * mock_data_handler.get_latest_bar_value(s, 'adj_close')
        assert latest['total'] == expected_total

    def test_total_reflects_unrealized_gain(self, portfolio, mock_data_handler):
        """
        Buy 100 at 100, price rises to 150.
        update_timeindex should show total = cash + market value = 90000 + 15000 = 105000.
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill)

        mock_data_handler.set_price('TEST', 150.0)
        portfolio.update_timeindex(MarketEvent())

        latest = portfolio.all_holdings[-1]
        assert latest['cash'] == 90000.0
        assert latest['TEST'] == 15000.0  # 100 * 150
        assert latest['total'] == 105000.0

    def test_total_reflects_unrealized_loss(self, portfolio, mock_data_handler):
        """
        Buy 100 at 100, price drops to 80.
        total = 90000 + 100*80 = 98000.
        """
        fill = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill)

        mock_data_handler.set_price('TEST', 80.0)
        portfolio.update_timeindex(MarketEvent())

        latest = portfolio.all_holdings[-1]
        assert latest['total'] == 98000.0

    def test_timeindex_appends_to_history(self, portfolio):
        """Each update_timeindex call adds one entry."""
        for _ in range(5):
            portfolio.update_timeindex(MarketEvent())

        assert len(portfolio.all_positions) == 6   # 1 initial + 5 updates
        assert len(portfolio.all_holdings) == 6

    def test_timeindex_preserves_position_snapshot(self, portfolio):
        """Positions are snapshotted correctly."""
        portfolio.current_positions['TEST'] = 50
        portfolio.update_timeindex(MarketEvent())
        assert portfolio.all_positions[-1]['TEST'] == 50

    def test_total_invariant_multiple_symbols(self, portfolio, mock_data_handler):
        """
        With 2 symbols at different prices and positions, total must be correct.
        TEST: 100 shares at price 100 -> market value 10000
        AAPL: 50 shares at price 200 -> market value 10000
        Cash after buys: 100000 - 10000 - 10000 = 80000
        Total: 80000 + 10000 + 10000 = 100000
        """
        # Buy TEST
        fill_test = FillEvent(datetime.utcnow(), 'TEST', 'NYSE', 100, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill_test)

        # Buy AAPL at different price
        mock_data_handler.set_price('AAPL', 200.0)
        fill_aapl = FillEvent(datetime.utcnow(), 'AAPL', 'NYSE', 50, 'BUY', None, commission=0.0)
        portfolio.update_fill(fill_aapl)

        portfolio.update_timeindex(MarketEvent())

        latest = portfolio.all_holdings[-1]
        assert latest['cash'] == 80000.0
        assert latest['TEST'] == 10000.0   # 100 * 100
        assert latest['AAPL'] == 10000.0   # 50 * 200
        assert latest['total'] == 100000.0


class TestPortfolioEquityCurve:

    def test_equity_curve_structure(self, portfolio):
        for _ in range(5):
            portfolio.update_timeindex(MarketEvent())

        portfolio.create_equity_curve_dataframe()

        assert hasattr(portfolio, 'equity_curve')
        assert 'returns' in portfolio.equity_curve.columns
        assert 'equity_curve' in portfolio.equity_curve.columns
        assert len(portfolio.equity_curve) == 6  # initial + 5 updates

    def test_summary_stats_structure(self, portfolio, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        for _ in range(10):
            portfolio.update_timeindex(MarketEvent())

        portfolio.create_equity_curve_dataframe()
        stats = portfolio.output_summary_stats()

        assert isinstance(stats, list)
        stat_names = [s[0] for s in stats]
        assert 'Total Return' in stat_names
        assert 'Sharpe Ratio' in stat_names
        assert 'Max Drawdown' in stat_names
        assert 'Drawdown Duration' in stat_names
        assert (tmp_path / 'equity.csv').exists()

    def test_zero_return_for_no_trades(self, portfolio, tmp_path, monkeypatch):
        """With no trades and flat prices, total return should be 0%."""
        monkeypatch.chdir(tmp_path)

        for _ in range(10):
            portfolio.update_timeindex(MarketEvent())

        portfolio.create_equity_curve_dataframe()
        stats = dict(portfolio.output_summary_stats())
        assert stats['Total Return'] == '0.00%'
