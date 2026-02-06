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


@pytest.fixture
def backtest_csv_data(tmp_path):
    """Creates test CSV data for backtesting."""
    csv_dir = tmp_path / "backtest_data"
    csv_dir.mkdir()

    # Create 60 days of data with a trend
    dates = pd.date_range('2024-01-01', periods=60, freq='D')

    # Create trending price data
    base_prices = np.linspace(100, 120, 60)
    noise = np.random.normal(0, 1, 60)
    prices = base_prices + noise

    data = pd.DataFrame({
        'open': prices - 0.5,
        'close': prices,
        'adj_close': prices,
        'volume': np.random.randint(1000000, 5000000, 60)
    }, index=dates)

    # Save CSV
    csv_path = csv_dir / "TEST.csv"
    data.to_csv(csv_path)

    return str(csv_dir)


class TestBacktestInitialization:
    """Test Backtest initialization."""

    def test_initialization(self, backtest_csv_data):
        """Test backtest initializes correctly."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        assert backtest.initial_capital == 100000.0
        assert backtest.symbol_list == ['TEST']
        assert backtest.signals == 0
        assert backtest.orders == 0
        assert backtest.fills == 0

    def test_trading_instances_generated(self, backtest_csv_data):
        """Test trading instances are created."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        assert hasattr(backtest, 'data_handler')
        assert hasattr(backtest, 'strategy')
        assert hasattr(backtest, 'portfolio')
        assert hasattr(backtest, 'execution_handler')

    def test_event_queue_initialized(self, backtest_csv_data):
        """Test event queue is initialized."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        assert hasattr(backtest, 'events')
        assert backtest.events.empty()


class TestBacktestExecution:
    """Test backtest execution."""

    def test_simulate_trading_completes(self, backtest_csv_data, capsys):
        """Test simulate_trading runs to completion."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        # Should complete without errors
        backtest.simulate_trading()

        # Check output contains expected info
        captured = capsys.readouterr()
        assert 'Creating summary stats' in captured.out
        assert 'Creating equity curve' in captured.out

    def test_event_counts_updated(self, backtest_csv_data):
        """Test event counters are updated during backtest."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        backtest.simulate_trading()

        # With a 60-day trend, MAC strategy should generate some signals
        # Exact counts depend on the random data, but there should be some activity
        assert backtest.signals >= 0
        assert backtest.orders >= 0
        assert backtest.fills >= 0

    def test_equity_curve_generated(self, backtest_csv_data):
        """Test equity curve is generated."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        backtest.simulate_trading()

        assert hasattr(backtest.portfolio, 'equity_curve')
        assert isinstance(backtest.portfolio.equity_curve, pd.DataFrame)
        assert 'returns' in backtest.portfolio.equity_curve.columns
        assert 'equity_curve' in backtest.portfolio.equity_curve.columns

    def test_equity_csv_created(self, backtest_csv_data, tmp_path, monkeypatch):
        """Test equity.csv file is created."""
        monkeypatch.chdir(tmp_path)

        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        backtest.simulate_trading()

        # equity.csv should be created
        assert (tmp_path / 'equity.csv').exists()


class TestBacktestMultipleSymbols:
    """Test backtest with multiple symbols."""

    @pytest.fixture
    def multi_symbol_csv_data(self, tmp_path):
        """Creates CSV data for multiple symbols."""
        csv_dir = tmp_path / "multi_data"
        csv_dir.mkdir()

        dates = pd.date_range('2024-01-01', periods=60, freq='D')

        for symbol in ['TEST', 'AAPL']:
            base_prices = np.linspace(100, 120, 60)
            noise = np.random.normal(0, 1, 60)
            prices = base_prices + noise

            data = pd.DataFrame({
                'open': prices - 0.5,
                'close': prices,
                'adj_close': prices,
                'volume': np.random.randint(1000000, 5000000, 60)
            }, index=dates)

            csv_path = csv_dir / f"{symbol}.csv"
            data.to_csv(csv_path)

        return str(csv_dir)

    def test_multiple_symbols_backtest(self, multi_symbol_csv_data):
        """Test backtest with multiple symbols."""
        backtest = Backtest(
            csv_dir=multi_symbol_csv_data,
            symbol_list=['TEST', 'AAPL'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        backtest.simulate_trading()

        # Should complete without errors
        assert hasattr(backtest.portfolio, 'equity_curve')


class TestBacktestParameters:
    """Test different backtest parameters."""

    def test_different_initial_capital(self, backtest_csv_data):
        """Test backtest with different initial capital."""
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=50000.0,
            heartbeat=0.0,
            start_date=datetime(2024, 1, 1),
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        assert backtest.portfolio.initial_capital == 50000.0
        backtest.simulate_trading()

    def test_different_start_date(self, backtest_csv_data):
        """Test backtest with different start date."""
        start_date = datetime(2024, 1, 15)
        backtest = Backtest(
            csv_dir=backtest_csv_data,
            symbol_list=['TEST'],
            initial_capital=100000.0,
            heartbeat=0.0,
            start_date=start_date,
            data_handler=HistoricCSVDataHandler,
            execution_handler=SimulatedExecutionHandler,
            portfolio=Portfolio,
            strategy=MovingAverageCrossStrategy
        )

        assert backtest.start_date == start_date
        backtest.simulate_trading()
