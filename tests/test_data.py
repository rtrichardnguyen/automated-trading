# tests/test_data.py

import pytest
import os
import pandas as pd
from datetime import datetime
from data import HistoricCSVDataHandler
from event import MarketEvent


@pytest.fixture
def csv_test_data(tmp_path, sample_csv_data):
    """Creates test CSV files for data handler testing."""
    csv_dir = tmp_path / "data"
    csv_dir.mkdir()

    # Create CSV files for test symbols
    for symbol in ['TEST', 'AAPL']:
        file_path = csv_dir / f"{symbol}.csv"
        sample_csv_data.to_csv(file_path)

    return str(csv_dir)


@pytest.fixture
def data_handler(event_queue, csv_test_data, symbol_list):
    """Provides a data handler instance for testing."""
    return HistoricCSVDataHandler(event_queue, csv_test_data, symbol_list)


class TestHistoricCSVDataHandlerInitialization:
    """Test HistoricCSVDataHandler initialization."""

    def test_initialization(self, data_handler, symbol_list):
        """Test data handler initializes correctly."""
        assert data_handler.symbol_list == symbol_list
        assert data_handler.continue_backtest == True

    def test_symbol_data_loaded(self, data_handler, symbol_list):
        """Test CSV data is loaded for all symbols."""
        for symbol in symbol_list:
            assert symbol in data_handler.symbol_data

    def test_latest_symbol_data_initialized(self, data_handler, symbol_list):
        """Test latest_symbol_data is initialized as empty lists."""
        for symbol in symbol_list:
            assert symbol in data_handler.latest_symbol_data
            assert isinstance(data_handler.latest_symbol_data[symbol], list)
            assert len(data_handler.latest_symbol_data[symbol]) == 0


class TestHistoricCSVDataHandlerBarAccess:
    """Test bar access methods."""

    def test_get_latest_bar_datetime(self, data_handler):
        """Test getting latest bar datetime."""
        # First update bars to populate data
        data_handler.update_bars()

        dt = data_handler.get_latest_bar_datetime('TEST')
        assert isinstance(dt, (datetime, pd.Timestamp))

    def test_get_latest_bar_value(self, data_handler):
        """Test getting latest bar value."""
        data_handler.update_bars()

        close_price = data_handler.get_latest_bar_value('TEST', 'adj_close')
        assert isinstance(close_price, (int, float))
        assert close_price > 0

    def test_get_latest_bar(self, data_handler):
        """Test getting latest bar."""
        data_handler.update_bars()

        bar = data_handler.get_latest_bar('TEST')
        assert bar is not None
        assert len(bar) == 2  # (datetime, bar_data)

    def test_get_latest_bars_multiple(self, data_handler):
        """Test getting multiple latest bars."""
        # Update bars a few times
        for _ in range(5):
            data_handler.update_bars()

        bars = data_handler.get_latest_bars('TEST', N=3)
        assert len(bars) == 3

    def test_get_latest_bar_values(self, data_handler):
        """Test getting multiple bar values."""
        # Update bars several times
        for _ in range(10):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=5)
        assert len(values) == 10  # Returns all available bars
        assert all(isinstance(v, (int, float)) for v in values)

    def test_get_latest_bar_invalid_symbol(self, data_handler):
        """Test error handling for invalid symbol."""
        data_handler.update_bars()

        with pytest.raises(KeyError):
            data_handler.get_latest_bar('INVALID')


class TestHistoricCSVDataHandlerUpdates:
    """Test bar updates and market events."""

    def test_update_bars_creates_market_event(self, data_handler, event_queue):
        """Test update_bars puts MarketEvent on queue."""
        data_handler.update_bars()

        assert not event_queue.empty()
        event = event_queue.get()
        assert isinstance(event, MarketEvent)
        assert event.type == 'MARKET'

    def test_update_bars_increments_data(self, data_handler):
        """Test update_bars progresses through data."""
        data_handler.update_bars()
        first_dt = data_handler.get_latest_bar_datetime('TEST')

        data_handler.update_bars()
        second_dt = data_handler.get_latest_bar_datetime('TEST')

        assert second_dt > first_dt

    def test_continue_backtest_flag(self, data_handler):
        """Test continue_backtest flag becomes False when data exhausted."""
        # Update until data runs out
        while data_handler.continue_backtest:
            data_handler.update_bars()

        assert data_handler.continue_backtest == False

    def test_multiple_symbols_synchronized(self, data_handler, event_queue):
        """Test all symbols update together."""
        data_handler.update_bars()

        # Both symbols should have data
        dt_test = data_handler.get_latest_bar_datetime('TEST')
        dt_aapl = data_handler.get_latest_bar_datetime('AAPL')

        # Should be same datetime (synchronized)
        assert dt_test == dt_aapl


class TestHistoricCSVDataHandlerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_latest_symbol_data_before_update(self, data_handler):
        """Test accessing data before any updates raises appropriate error."""
        with pytest.raises(IndexError):
            data_handler.get_latest_bar('TEST')

    def test_accessing_more_bars_than_available(self, data_handler):
        """Test requesting more bars than available."""
        # Update only twice
        data_handler.update_bars()
        data_handler.update_bars()

        # Request 10 bars (only 2 available)
        bars = data_handler.get_latest_bars('TEST', N=10)
        assert len(bars) == 2

    def test_bar_values_array_type(self, data_handler):
        """Test get_latest_bar_values returns numpy array."""
        data_handler.update_bars()
        data_handler.update_bars()
        data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=3)
        assert hasattr(values, 'shape')  # numpy array attribute
