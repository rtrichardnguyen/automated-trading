# tests/test_alpaca_data.py

from datetime import datetime
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from alpaca_data import AlpacaDataHandler
from event import MarketEvent


API_VERSION = 'v2'
EXCHANGE = 'iex'
PUBLIC_KEY = 'fake_key'
SECRET_KEY = 'fake_secret'


def _make_bar_message(symbol, timestamp, open_, high, low, close, volume):
    return {
        'T': 'b',
        'S': symbol,
        't': timestamp,
        'o': open_,
        'h': high,
        'l': low,
        'c': close,
        'v': volume,
    }


@pytest.fixture
def handler(event_queue, symbol_list):
    with patch.object(AlpacaDataHandler, '_start_connection', autospec=True) as mock_start:
        handler = AlpacaDataHandler(
            event_queue,
            symbol_list,
            API_VERSION,
            EXCHANGE,
            PUBLIC_KEY,
            SECRET_KEY,
        )

    mock_start.assert_called_once_with(
        handler,
        PUBLIC_KEY,
        SECRET_KEY,
        API_VERSION,
        EXCHANGE,
    )
    return handler


class TestAlpacaDataHandlerInitialization:
    def test_initialization(self, event_queue, symbol_list):
        with patch.object(AlpacaDataHandler, '_start_connection', autospec=True) as mock_start:
            handler = AlpacaDataHandler(
                event_queue,
                symbol_list,
                API_VERSION,
                EXCHANGE,
                PUBLIC_KEY,
                SECRET_KEY,
            )

        assert handler.events == event_queue
        assert handler.symbol_list == symbol_list
        assert handler.latest_symbol_data == {symbol: [] for symbol in symbol_list}
        assert handler.api_version == API_VERSION
        assert handler.exchange == EXCHANGE
        assert handler.public_key == PUBLIC_KEY
        assert handler.secret_key == SECRET_KEY
        assert handler.message_queue.empty()
        mock_start.assert_called_once_with(
            handler,
            PUBLIC_KEY,
            SECRET_KEY,
            API_VERSION,
            EXCHANGE,
        )

    def test_initialization_with_single_symbol(self, event_queue):
        with patch.object(AlpacaDataHandler, '_start_connection', autospec=True):
            handler = AlpacaDataHandler(
                event_queue,
                ['AAPL'],
                API_VERSION,
                EXCHANGE,
                PUBLIC_KEY,
                SECRET_KEY,
            )

        assert handler.symbol_list == ['AAPL']
        assert handler.latest_symbol_data == {'AAPL': []}

    def test_initialization_with_multiple_symbols(self, event_queue):
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']

        with patch.object(AlpacaDataHandler, '_start_connection', autospec=True):
            handler = AlpacaDataHandler(
                event_queue,
                symbols,
                API_VERSION,
                EXCHANGE,
                PUBLIC_KEY,
                SECRET_KEY,
            )

        assert handler.symbol_list == symbols
        assert handler.latest_symbol_data == {symbol: [] for symbol in symbols}


class TestAlpacaDataHandlerEmptyState:
    def test_get_latest_bar_raises_index_error_without_data(self, handler):
        with pytest.raises(IndexError):
            handler.get_latest_bar('TEST')

    def test_get_latest_bars_returns_empty_list_without_data(self, handler):
        assert handler.get_latest_bars('TEST', N=5) == []

    def test_get_latest_bar_datetime_raises_index_error_without_data(self, handler):
        with pytest.raises(IndexError):
            handler.get_latest_bar_datetime('TEST')

    def test_get_latest_bar_value_raises_index_error_without_data(self, handler):
        with pytest.raises(IndexError):
            handler.get_latest_bar_value('TEST', 'close')

    def test_get_latest_bar_values_returns_empty_array_without_data(self, handler):
        values = handler.get_latest_bar_values('TEST', 'close', N=10)
        assert isinstance(values, np.ndarray)
        assert values.size == 0

    def test_invalid_symbol_raises_key_error(self, handler):
        with pytest.raises(KeyError):
            handler.get_latest_bar('INVALID')


class TestAlpacaDataHandlerUpdates:
    def test_update_bars_with_empty_queue_is_noop(self, handler, event_queue):
        result = handler.update_bars()

        assert result is None
        assert event_queue.empty()
        assert handler.latest_symbol_data['TEST'] == []

    def test_update_bars_stores_bar_and_emits_market_event(self, handler, event_queue):
        timestamp = datetime(2024, 1, 1, 10, 0, 0)
        handler.message_queue.put(
            _make_bar_message('TEST', timestamp, 100.0, 101.0, 99.0, 100.5, 1000)
        )

        handler.update_bars()

        bar = handler.get_latest_bar('TEST')
        assert bar[0] == timestamp
        assert isinstance(bar[1], pd.Series)
        assert handler.get_latest_bar_datetime('TEST') == timestamp
        assert handler.get_latest_bar_value('TEST', 'close') == 100.5
        assert np.isnan(handler.get_latest_bar_value('TEST', 'returns'))

        assert event_queue.qsize() == 1
        event = event_queue.get()
        assert isinstance(event, MarketEvent)
        assert event.type == 'MARKET'

    def test_update_bars_computes_returns_from_previous_close(self, handler):
        first_timestamp = datetime(2024, 1, 1, 10, 0, 0)
        second_timestamp = datetime(2024, 1, 1, 10, 1, 0)

        handler.message_queue.put(
            _make_bar_message('TEST', first_timestamp, 100.0, 101.0, 99.0, 100.0, 1000)
        )
        handler.message_queue.put(
            _make_bar_message('TEST', second_timestamp, 101.0, 102.0, 100.0, 101.0, 1100)
        )

        handler.update_bars()

        closes = handler.get_latest_bar_values('TEST', 'close', N=2)
        returns = handler.get_latest_bar_values('TEST', 'returns', N=2)

        np.testing.assert_allclose(closes, np.array([100.0, 101.0]))
        assert np.isnan(returns[0])
        np.testing.assert_allclose(returns[1:], np.array([0.01]))

    def test_update_bars_processes_multiple_symbols(self, handler, event_queue):
        test_timestamp = datetime(2024, 1, 1, 10, 0, 0)
        aapl_timestamp = datetime(2024, 1, 1, 10, 0, 1)

        handler.message_queue.put(
            _make_bar_message('TEST', test_timestamp, 100.0, 101.0, 99.0, 100.0, 1000)
        )
        handler.message_queue.put(
            _make_bar_message('AAPL', aapl_timestamp, 200.0, 201.0, 199.0, 200.0, 2000)
        )

        handler.update_bars()

        assert handler.get_latest_bar_value('TEST', 'close') == 100.0
        assert handler.get_latest_bar_value('AAPL', 'close') == 200.0
        assert event_queue.qsize() == 2
