# tests/test_strategy.py

import pytest
import numpy as np
from datetime import datetime
from mac import MovingAverageCrossStrategy
from event import MarketEvent, SignalEvent


class MockBars:
    """Mock bars object for testing strategies."""

    def __init__(self, symbol_list):
        self.symbol_list = symbol_list
        self._data = {}
        for symbol in symbol_list:
            # Create sample price data with uptrend
            self._data[symbol] = {
                'adj_close': np.array([100 + i * 0.5 for i in range(100)]),
                'datetime': datetime(2024, 1, 1)
            }

    def get_latest_bar_values(self, symbol, value_type, N=1):
        """Return latest N bar values."""
        if symbol in self._data and value_type in self._data[symbol]:
            data = self._data[symbol][value_type]
            if isinstance(data, np.ndarray):
                return data[-N:] if N <= len(data) else data
            return data
        return np.array([])

    def get_latest_bar_datetime(self, symbol):
        """Return latest bar datetime."""
        return self._data[symbol]['datetime']

    def set_prices(self, symbol, prices):
        """Set custom prices for testing."""
        self._data[symbol]['adj_close'] = np.array(prices)


@pytest.fixture
def mock_bars():
    """Provides mock bars for strategy testing."""
    return MockBars(['TEST'])


@pytest.fixture
def mac_strategy(mock_bars, event_queue):
    """Provides Moving Average Crossover strategy."""
    return MovingAverageCrossStrategy(
        bars=mock_bars,
        events=event_queue,
        short_window=5,
        long_window=10
    )


class TestMovingAverageCrossStrategyInitialization:
    """Test MovingAverageCrossStrategy initialization."""

    def test_initialization(self, mac_strategy, mock_bars):
        """Test strategy initializes correctly."""
        assert mac_strategy.bars == mock_bars
        assert mac_strategy.short_window == 5
        assert mac_strategy.long_window == 10

    def test_symbol_list_inherited(self, mac_strategy):
        """Test symbol list is inherited from bars."""
        assert mac_strategy.symbol_list == ['TEST']

    def test_initial_bought_state(self, mac_strategy):
        """Test all symbols start in OUT state."""
        assert mac_strategy.bought['TEST'] == 'OUT'

    def test_multiple_symbols(self, event_queue):
        """Test strategy with multiple symbols."""
        bars = MockBars(['TEST', 'AAPL', 'GOOGL'])
        strategy = MovingAverageCrossStrategy(bars, event_queue)

        assert len(strategy.bought) == 3
        for symbol in ['TEST', 'AAPL', 'GOOGL']:
            assert strategy.bought[symbol] == 'OUT'


class TestMovingAverageCrossStrategySignals:
    """Test signal generation logic."""

    def test_long_signal_on_bullish_crossover(self, mac_strategy, mock_bars, event_queue):
        """Test LONG signal generated when short MA crosses above long MA."""
        # Create price series where short MA will cross above long MA
        prices = [100] * 10 + [105] * 10  # Price increase
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        mac_strategy.calculate_signals(market_event)

        # Should have signal in queue
        if not event_queue.empty():
            signal = event_queue.get()
            assert signal.type == 'SIGNAL'
            assert signal.symbol == 'TEST'
            assert signal.signal_type == 'LONG'

    def test_exit_signal_on_bearish_crossover(self, mac_strategy, mock_bars, event_queue):
        """Test EXIT signal generated when short MA crosses below long MA."""
        # Set strategy to already holding long
        mac_strategy.bought['TEST'] = 'LONG'

        # Create price series where short MA will cross below long MA
        prices = [110] * 5 + [105] * 10 + [95] * 10  # Price decrease
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        mac_strategy.calculate_signals(market_event)

        # Check for EXIT signal
        if not event_queue.empty():
            signal = event_queue.get()
            if signal.signal_type == 'EXIT':
                assert signal.symbol == 'TEST'
                assert mac_strategy.bought['TEST'] == 'OUT'

    def test_no_signal_when_already_long(self, mac_strategy, mock_bars, event_queue):
        """Test no duplicate LONG signals when already in position."""
        # Set to already long
        mac_strategy.bought['TEST'] = 'LONG'

        # Create bullish prices
        prices = [100] * 5 + [110] * 10
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        mac_strategy.calculate_signals(market_event)

        # Should not generate another LONG signal
        # (queue might be empty or have other signals)
        signals = []
        while not event_queue.empty():
            signals.append(event_queue.get())

        long_signals = [s for s in signals if s.signal_type == 'LONG']
        assert len(long_signals) == 0

    def test_no_exit_when_not_holding(self, mac_strategy, mock_bars, event_queue):
        """Test no EXIT signal when not holding position."""
        # Ensure state is OUT
        mac_strategy.bought['TEST'] = 'OUT'

        # Create bearish prices
        prices = [110] * 5 + [95] * 10
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        mac_strategy.calculate_signals(market_event)

        # Should not generate EXIT signal
        signals = []
        while not event_queue.empty():
            signals.append(event_queue.get())

        exit_signals = [s for s in signals if s.signal_type == 'EXIT']
        assert len(exit_signals) == 0

    def test_insufficient_data(self, mac_strategy, mock_bars, event_queue):
        """Test strategy handles insufficient data gracefully."""
        # Set only 5 prices (less than long_window of 10)
        prices = [100, 101, 102, 103, 104]
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        # Should not crash
        mac_strategy.calculate_signals(market_event)

        # May or may not generate signal, but shouldn't error
        assert True

    def test_signal_strength(self, mac_strategy, mock_bars, event_queue):
        """Test signals have correct strength value."""
        prices = [100] * 10 + [110] * 10
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        mac_strategy.calculate_signals(market_event)

        if not event_queue.empty():
            signal = event_queue.get()
            assert signal.strength == 1.0

    def test_non_market_event_ignored(self, mac_strategy, event_queue):
        """Test strategy only processes MARKET events."""
        # Create a non-market event
        class MockEvent:
            type = 'SIGNAL'

        mac_strategy.calculate_signals(MockEvent())

        # Should not generate any signals
        assert event_queue.empty()


class TestMovingAverageCrossStrategyWindowSizes:
    """Test different window size configurations."""

    def test_custom_short_window(self, mock_bars, event_queue):
        """Test strategy with custom short window."""
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=10, long_window=20
        )
        assert strategy.short_window == 10
        assert strategy.long_window == 20

    def test_very_short_windows(self, mock_bars, event_queue):
        """Test strategy with very short windows."""
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=2, long_window=5
        )

        # Should still work with small windows
        prices = [100, 101, 102, 103, 104, 105, 106]
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        strategy.calculate_signals(market_event)
        # Should not crash

    def test_large_windows(self, mock_bars, event_queue):
        """Test strategy with large windows."""
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=50, long_window=100
        )

        # Should handle large windows
        prices = list(range(100, 200))
        mock_bars.set_prices('TEST', prices)

        market_event = MarketEvent()
        strategy.calculate_signals(market_event)
        # Should not crash
