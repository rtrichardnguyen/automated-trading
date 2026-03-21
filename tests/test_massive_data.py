# tests/test_massive_data.py

import numpy as np
import pandas as pd
import pytest

from datetime import datetime, UTC
from unittest.mock import patch

from event import MarketEvent
from massive_data import MassiveHistoricDataHandler


def _to_epoch_ms(year, month, day):
    return int(datetime(year, month, day, tzinfo=UTC).timestamp() * 1000)


class FakeAgg:
    def __init__(self, timestamp, open_, high, low, close, volume, vwap, transactions, otc):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.vwap = vwap
        self.transactions = transactions
        self.otc = otc


TEST_BARS = {
    'TEST': [
        FakeAgg(_to_epoch_ms(2024, 1, 1), 99.0, 101.0, 98.0, 100.0, 1000, 100.0, 10, False),
        FakeAgg(_to_epoch_ms(2024, 1, 2), 109.0, 111.0, 108.0, 110.0, 1100, 110.0, 11, False),
        FakeAgg(_to_epoch_ms(2024, 1, 3), 120.0, 122.0, 119.0, 121.0, 1200, 121.0, 12, False),
    ],
    'AAPL': [
        FakeAgg(_to_epoch_ms(2024, 1, 1), 199.0, 201.0, 198.0, 200.0, 2000, 200.0, 20, False),
        FakeAgg(_to_epoch_ms(2024, 1, 3), 219.0, 221.0, 218.0, 220.0, 2200, 220.0, 22, False),
    ],
}


@pytest.fixture
def massive_handler(event_queue):
    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def list_aggs(self, ticker, multiplier, timespan, from_, to, sort, limit):
            assert multiplier == 1
            assert timespan == 'day'
            assert sort == 'asc'
            return TEST_BARS[ticker]

    with patch('massive_data.RESTClient', FakeClient):
        return MassiveHistoricDataHandler(
            api_key='test-key',
            events=event_queue,
            symbol_list=['TEST', 'AAPL'],
            timespan='day',
            multiplier=1
        )


class TestMassiveHistoricDataHandlerInitialization:
    def test_initialization(self, massive_handler):
        assert massive_handler.symbol_list == ['TEST', 'AAPL']
        assert massive_handler.continue_backtest is True

    def test_symbol_data_loaded(self, massive_handler):
        assert 'TEST' in massive_handler.symbol_data
        assert 'AAPL' in massive_handler.symbol_data

    def test_latest_symbol_data_initialized(self, massive_handler):
        assert massive_handler.latest_symbol_data == {
            'TEST': [],
            'AAPL': []
        }


class TestMassiveHistoricDataHandlerBarAccess:
    def test_first_bar_matches_first_known_price(self, massive_handler):
        massive_handler.update_bars()

        assert massive_handler.get_latest_bar_value('TEST', 'adj_close') == 100.0
        assert massive_handler.get_latest_bar_value('AAPL', 'adj_close') == 200.0

    def test_forward_fill_keeps_missing_symbol_price_flat(self, massive_handler):
        massive_handler.update_bars()
        massive_handler.update_bars()

        assert massive_handler.get_latest_bar_datetime('TEST') == massive_handler.get_latest_bar_datetime('AAPL')
        assert massive_handler.get_latest_bar_value('AAPL', 'adj_close') == 200.0
        assert massive_handler.get_latest_bar_value('AAPL', 'returns') == 0.0

    def test_pct_change_returns_follow_aligned_series(self, massive_handler):
        while massive_handler.continue_backtest:
            massive_handler.update_bars()

        test_returns = massive_handler.get_latest_bar_values('TEST', 'returns', N=3)
        aapl_returns = massive_handler.get_latest_bar_values('AAPL', 'returns', N=3)
        aapl_prices = massive_handler.get_latest_bar_values('AAPL', 'adj_close', N=3)

        assert np.isnan(test_returns[0])
        np.testing.assert_allclose(test_returns[1:], np.array([0.1, 0.1]))
        assert np.isnan(aapl_returns[0])
        np.testing.assert_allclose(aapl_returns[1:], np.array([0.0, 0.1]))
        np.testing.assert_allclose(aapl_prices, np.array([200.0, 200.0, 220.0]))

    def test_get_latest_bar_values_returns_numpy_array(self, massive_handler):
        for _ in range(3):
            massive_handler.update_bars()

        values = massive_handler.get_latest_bar_values('TEST', 'adj_close', N=3)
        assert isinstance(values, np.ndarray)

    def test_invalid_symbol_raises_key_error(self, massive_handler):
        massive_handler.update_bars()

        with pytest.raises(KeyError):
            massive_handler.get_latest_bar('INVALID')


class TestMassiveHistoricDataHandlerUpdates:
    def test_update_bars_creates_market_event(self, massive_handler, event_queue):
        massive_handler.update_bars()

        assert not event_queue.empty()
        event = event_queue.get()
        assert isinstance(event, MarketEvent)
        assert event.type == 'MARKET'

    def test_multiple_symbols_stay_synchronized(self, massive_handler):
        massive_handler.update_bars()
        massive_handler.update_bars()

        dt_test = massive_handler.get_latest_bar_datetime('TEST')
        dt_aapl = massive_handler.get_latest_bar_datetime('AAPL')
        assert dt_test == dt_aapl
        assert isinstance(dt_test, (datetime, pd.Timestamp))

    def test_continue_backtest_flag_turns_false_when_data_exhausted(self, massive_handler):
        while massive_handler.continue_backtest:
            massive_handler.update_bars()

        assert massive_handler.continue_backtest is False
