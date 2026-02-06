# tests/test_data.py

import pytest
import os
import numpy as np
import pandas as pd
from datetime import datetime
from data import HistoricCSVDataHandler
from event import MarketEvent


# Known prices used in conftest.py sample_csv_data
KNOWN_PRICES = [100.0, 102.0, 101.0, 104.0, 103.0, 106.0, 105.0, 108.0, 107.0, 110.0]


@pytest.fixture
def csv_test_data(tmp_path, sample_csv_data):
    """Creates test CSV files for data handler testing."""
    csv_dir = tmp_path / "data"
    csv_dir.mkdir()

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
    """Test bar access methods with known data."""

    def test_first_bar_matches_csv_first_row(self, data_handler):
        """After first update, bar adj_close should equal the first known price."""
        data_handler.update_bars()
        price = data_handler.get_latest_bar_value('TEST', 'adj_close')
        assert price == KNOWN_PRICES[0]

    def test_second_bar_matches_csv_second_row(self, data_handler):
        """After two updates, bar adj_close should equal the second known price."""
        data_handler.update_bars()
        data_handler.update_bars()
        price = data_handler.get_latest_bar_value('TEST', 'adj_close')
        assert price == KNOWN_PRICES[1]

    def test_get_latest_bar_datetime_is_timestamp(self, data_handler):
        """Test getting latest bar datetime returns a datetime-like object."""
        data_handler.update_bars()
        dt = data_handler.get_latest_bar_datetime('TEST')
        assert isinstance(dt, (datetime, pd.Timestamp))

    def test_get_latest_bar_structure(self, data_handler):
        """Test bar is a (datetime, row_data) tuple."""
        data_handler.update_bars()
        bar = data_handler.get_latest_bar('TEST')
        assert bar is not None
        assert len(bar) == 2

    def test_get_latest_bars_multiple(self, data_handler):
        """Test getting N latest bars returns exactly N bars."""
        for _ in range(5):
            data_handler.update_bars()

        bars = data_handler.get_latest_bars('TEST', N=3)
        assert len(bars) == 3

    def test_get_latest_bar_values_returns_N_values(self, data_handler):
        """After bug fix: get_latest_bar_values(N=5) returns exactly 5 values."""
        for _ in range(10):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=5)
        assert len(values) == 5

    def test_get_latest_bar_values_match_known_prices(self, data_handler):
        """The last N values should match the last N known prices."""
        for _ in range(10):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=3)
        # After 10 updates, the last 3 prices should be KNOWN_PRICES[7:10]
        expected = KNOWN_PRICES[-3:]
        np.testing.assert_array_almost_equal(values, expected)

    def test_get_latest_bar_values_all(self, data_handler):
        """Requesting N larger than available bars returns all available."""
        for _ in range(5):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=100)
        assert len(values) == 5
        expected = KNOWN_PRICES[:5]
        np.testing.assert_array_almost_equal(values, expected)

    def test_get_latest_bar_invalid_symbol(self, data_handler):
        """Test error handling for invalid symbol."""
        data_handler.update_bars()
        with pytest.raises(KeyError):
            data_handler.get_latest_bar('INVALID')

    def test_bars_chronologically_ordered(self, data_handler):
        """Bars should arrive in chronological order."""
        for _ in range(5):
            data_handler.update_bars()

        bars = data_handler.get_latest_bars('TEST', N=5)
        datetimes = [b[0] for b in bars]
        for i in range(1, len(datetimes)):
            assert datetimes[i] > datetimes[i - 1]


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
        """Test update_bars progresses through data chronologically."""
        data_handler.update_bars()
        first_dt = data_handler.get_latest_bar_datetime('TEST')

        data_handler.update_bars()
        second_dt = data_handler.get_latest_bar_datetime('TEST')

        assert second_dt > first_dt

    def test_continue_backtest_flag(self, data_handler):
        """Test continue_backtest flag becomes False when data exhausted."""
        while data_handler.continue_backtest:
            data_handler.update_bars()

        assert data_handler.continue_backtest == False

    def test_multiple_symbols_synchronized(self, data_handler, event_queue):
        """Test all symbols update together."""
        data_handler.update_bars()

        dt_test = data_handler.get_latest_bar_datetime('TEST')
        dt_aapl = data_handler.get_latest_bar_datetime('AAPL')

        assert dt_test == dt_aapl


class TestHistoricCSVDataHandlerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_latest_symbol_data_before_update(self, data_handler):
        """Test accessing data before any updates raises IndexError."""
        with pytest.raises(IndexError):
            data_handler.get_latest_bar('TEST')

    def test_accessing_more_bars_than_available(self, data_handler):
        """Test requesting more bars than available returns all available."""
        data_handler.update_bars()
        data_handler.update_bars()

        bars = data_handler.get_latest_bars('TEST', N=10)
        assert len(bars) == 2

    def test_bar_values_array_type(self, data_handler):
        """Test get_latest_bar_values returns numpy array."""
        for _ in range(3):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=3)
        assert isinstance(values, np.ndarray)

    def test_all_10_prices_match_known_data(self, data_handler):
        """After all 10 bars, every price must match the known data exactly."""
        while data_handler.continue_backtest:
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'adj_close', N=100)
        # Should have exactly 10 bars
        assert len(values) == 10
        np.testing.assert_array_almost_equal(values, KNOWN_PRICES)

    def test_open_prices_match_known_data(self, data_handler):
        """Verify open prices (close - 1) are also correct."""
        for _ in range(5):
            data_handler.update_bars()

        values = data_handler.get_latest_bar_values('TEST', 'open', N=5)
        expected_opens = [p - 1.0 for p in KNOWN_PRICES[:5]]
        np.testing.assert_array_almost_equal(values, expected_opens)

    def test_market_event_emitted_every_update(self, event_queue, csv_test_data, symbol_list):
        """Each update_bars call puts exactly one MarketEvent on the queue."""
        handler = HistoricCSVDataHandler(event_queue, csv_test_data, symbol_list)

        handler.update_bars()
        assert event_queue.qsize() == 1
        event = event_queue.get()
        assert isinstance(event, MarketEvent)

        handler.update_bars()
        assert event_queue.qsize() == 1
