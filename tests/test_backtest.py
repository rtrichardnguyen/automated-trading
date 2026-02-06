# tests/test_backtest.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio
from mac import MovingAverageCrossStrategy


def _create_csv(csv_dir, symbol, prices):
    """Helper to create a deterministic CSV file for backtesting."""
    dates = pd.date_range('2024-01-01', periods=len(prices), freq='D')
    data = pd.DataFrame({
        'open': [p - 0.5 for p in prices],
        'close': prices,
        'adj_close': prices,
        'volume': [1000000] * len(prices)
    }, index=dates)
    csv_path = csv_dir / f"{symbol}.csv"
    data.to_csv(csv_path)


class TestBacktestWithFlatPrices:
    """Flat prices -> no crossover -> no signals, orders, or fills."""

    @pytest.fixture
    def flat_csv(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        # 60 bars, all at price 100. No MA crossover possible.
        _create_csv(csv_dir, 'TEST', [100.0] * 60)
        return str(csv_dir)

    def test_no_trades_on_flat_prices(self, flat_csv, tmp_path, monkeypatch):
        """Flat prices produce zero signals/orders/fills."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=flat_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.signals == 0
        assert bt.orders == 0
        assert bt.fills == 0

    def test_portfolio_unchanged_on_flat_prices(self, flat_csv, tmp_path, monkeypatch):
        """With no trades, portfolio total should remain at initial capital."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=flat_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.portfolio.equity_curve['total'].iloc[-1] == pytest.approx(100000.0)


class TestBacktestSingleLongSignal:
    """
    Prices: 50 bars at 100, then 5 bars at 200.
    MAC with short=20, long=50 (defaults).

    At bar 51 (first bar at 200):
      short_sma = mean([100]*19 + [200]) = (1900+200)/20 = 105
      long_sma  = mean([100]*49 + [200]) = (4900+200)/50 = 102
      short (105) > long (102) -> LONG signal.

    Bars 52-55: short > long but already LONG -> no more signals.

    Result: exactly 1 signal, 1 order, 1 fill.
    Portfolio: bought 100 shares at 200, price stays at 200 -> total = 100000.
    """

    @pytest.fixture
    def single_long_csv(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        prices = [100.0] * 50 + [200.0] * 5
        _create_csv(csv_dir, 'TEST', prices)
        return str(csv_dir)

    def test_exactly_one_trade(self, single_long_csv, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=single_long_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.signals == 1
        assert bt.orders == 1
        assert bt.fills == 1

    def test_signal_order_fill_chain_balanced(self, single_long_csv, tmp_path, monkeypatch):
        """Every signal produces an order which produces a fill: counts must be equal."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=single_long_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.signals == bt.orders == bt.fills

    def test_portfolio_total_after_buy_at_same_price(self, single_long_csv, tmp_path, monkeypatch):
        """Bought at 200, price stays 200 -> total should be initial capital (no gain/loss)."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=single_long_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        # Cash = 100000 - (100 * 200) = 80000
        # Market value = 100 * 200 = 20000
        # Total = 80000 + 20000 = 100000
        assert bt.portfolio.equity_curve['total'].iloc[-1] == pytest.approx(100000.0)


class TestBacktestLongThenExit:
    """
    Prices: 50 bars at 100, 10 bars at 200, 20 bars at 50.

    LONG signal at bar 51:
      short_sma = (19*100 + 200)/20 = 105
      long_sma  = (49*100 + 200)/50 = 102
      -> BUY 100 shares at 200. Cash = 80000.

    EXIT signal at bar 73 (13th bar at price 50):
      short_sma = (7*200 + 13*50)/20 = 102.5
      long_sma  = (27*100 + 10*200 + 13*50)/50 = 107
      short (102.5) < long (107) -> EXIT.
      -> SELL 100 shares at 50. Cash = 80000 + 5000 = 85000.

    Final total = 85000 (lost 15000: bought at 200, sold at 50).
    """

    @pytest.fixture
    def round_trip_csv(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        prices = [100.0] * 50 + [200.0] * 10 + [50.0] * 20
        _create_csv(csv_dir, 'TEST', prices)
        return str(csv_dir)

    def test_two_signals_for_round_trip(self, round_trip_csv, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=round_trip_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.signals == 2
        assert bt.orders == 2
        assert bt.fills == 2

    def test_portfolio_total_after_round_trip_loss(self, round_trip_csv, tmp_path, monkeypatch):
        """Buy 100 at 200, sell 100 at 50 -> loss of 15000 -> total = 85000."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=round_trip_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.portfolio.equity_curve['total'].iloc[-1] == pytest.approx(85000.0)

    def test_position_flat_after_exit(self, round_trip_csv, tmp_path, monkeypatch):
        """After EXIT, position should be back to 0."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=round_trip_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert bt.portfolio.current_positions['TEST'] == 0


class TestBacktestEquityCurve:
    """Verify equity curve structure and output."""

    @pytest.fixture
    def simple_csv(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        _create_csv(csv_dir, 'TEST', [100.0] * 60)
        return str(csv_dir)

    def test_equity_curve_has_required_columns(self, simple_csv, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=simple_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert isinstance(bt.portfolio.equity_curve, pd.DataFrame)
        for col in ['returns', 'equity_curve', 'total', 'cash']:
            assert col in bt.portfolio.equity_curve.columns

    def test_equity_csv_written(self, simple_csv, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=simple_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        assert (tmp_path / 'equity.csv').exists()

    def test_total_return_zero_for_no_trades(self, simple_csv, tmp_path, monkeypatch):
        """With no trades and flat prices, total return should be 0%."""
        monkeypatch.chdir(tmp_path)

        bt = Backtest(
            csv_dir=simple_csv, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        bt.simulate_trading()

        stats = dict(bt.portfolio.output_summary_stats())
        assert stats['Total Return'] == '0.00%'


class TestBacktestInitialization:

    @pytest.fixture
    def csv_dir(self, tmp_path):
        csv_dir = tmp_path / "data"
        csv_dir.mkdir()
        _create_csv(csv_dir, 'TEST', [100.0] * 20)
        return str(csv_dir)

    def test_counters_start_at_zero(self, csv_dir):
        bt = Backtest(
            csv_dir=csv_dir, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        assert bt.signals == 0
        assert bt.orders == 0
        assert bt.fills == 0

    def test_components_created(self, csv_dir):
        bt = Backtest(
            csv_dir=csv_dir, symbol_list=['TEST'],
            initial_capital=100000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        assert hasattr(bt, 'data_handler')
        assert hasattr(bt, 'strategy')
        assert hasattr(bt, 'portfolio')
        assert hasattr(bt, 'execution_handler')

    def test_initial_capital_propagated(self, csv_dir):
        bt = Backtest(
            csv_dir=csv_dir, symbol_list=['TEST'],
            initial_capital=50000.0, heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio, strategy=MovingAverageCrossStrategy
        )
        assert bt.portfolio.initial_capital == 50000.0
        assert bt.portfolio.current_holdings['cash'] == 50000.0
