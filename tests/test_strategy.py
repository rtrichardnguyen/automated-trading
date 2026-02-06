# tests/test_strategy.py

import pytest
import numpy as np
from datetime import datetime
from mac import MovingAverageCrossStrategy
from event import MarketEvent, SignalEvent


class MockBars:
    """Mock bars with precise control over price data for deterministic testing."""

    def __init__(self, symbol_list, prices_dict=None):
        self.symbol_list = symbol_list
        self._prices = {}
        if prices_dict:
            self._prices = {s: np.array(p, dtype=float) for s, p in prices_dict.items()}
        else:
            for s in symbol_list:
                self._prices[s] = np.array([100.0] * 10)

    def get_latest_bar_values(self, symbol, value_type, N=1):
        if value_type == 'adj_close' and symbol in self._prices:
            data = self._prices[symbol]
            return data[-N:] if N <= len(data) else data
        return np.array([])

    def get_latest_bar_datetime(self, symbol):
        return datetime(2024, 1, 1)

    def set_prices(self, symbol, prices):
        self._prices[symbol] = np.array(prices, dtype=float)


@pytest.fixture
def mock_bars():
    return MockBars(['TEST'])


@pytest.fixture
def mac_strategy(mock_bars, event_queue):
    return MovingAverageCrossStrategy(
        bars=mock_bars, events=event_queue,
        short_window=5, long_window=10
    )


class TestMovingAverageCrossStrategyInitialization:

    def test_initial_bought_state_is_out(self, mac_strategy):
        """All symbols must start in 'OUT' state (no position)."""
        assert mac_strategy.bought['TEST'] == 'OUT'

    def test_symbol_list_from_bars(self, mac_strategy):
        assert mac_strategy.symbol_list == ['TEST']

    def test_window_sizes_stored(self, mac_strategy):
        assert mac_strategy.short_window == 5
        assert mac_strategy.long_window == 10

    def test_multiple_symbols_all_start_out(self, event_queue):
        bars = MockBars(['A', 'B', 'C'])
        strategy = MovingAverageCrossStrategy(bars, event_queue, short_window=5, long_window=10)
        for s in ['A', 'B', 'C']:
            assert strategy.bought[s] == 'OUT'


class TestMovingAverageCrossStrategySignals:
    """Test signal generation with mathematically verified price scenarios.

    With short_window=5, long_window=10, the strategy fetches the last 10
    adj_close values, computes:
        short_sma = mean(last 5 values)
        long_sma  = mean(all 10 values)
    Then:
        short_sma > long_sma AND bought=='OUT'  -> LONG signal
        short_sma < long_sma AND bought=='LONG' -> EXIT signal
    """

    def test_long_signal_when_short_ma_above_long_ma(self, mac_strategy, mock_bars, event_queue):
        """
        prices = [90]*5 + [110]*5
        short_sma = mean([110]*5) = 110
        long_sma  = mean([90]*5 + [110]*5) = (450+550)/10 = 100
        short (110) > long (100) AND bought=='OUT' -> must produce LONG signal.
        """
        mock_bars.set_prices('TEST', [90]*5 + [110]*5)
        mac_strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty(), "Expected a LONG signal but queue is empty"
        signal = event_queue.get()
        assert signal.type == 'SIGNAL'
        assert signal.signal_type == 'LONG'
        assert signal.symbol == 'TEST'
        assert signal.strength == 1.0

    def test_long_signal_updates_bought_state_to_long(self, mac_strategy, mock_bars, event_queue):
        """After LONG signal, bought state must transition from 'OUT' to 'LONG'."""
        mock_bars.set_prices('TEST', [90]*5 + [110]*5)
        mac_strategy.calculate_signals(MarketEvent())
        assert mac_strategy.bought['TEST'] == 'LONG'

    def test_exit_signal_when_short_ma_below_long_ma(self, mac_strategy, mock_bars, event_queue):
        """
        prices = [110]*5 + [90]*5
        short_sma = mean([90]*5) = 90
        long_sma  = mean([110]*5 + [90]*5) = (550+450)/10 = 100
        short (90) < long (100) AND bought=='LONG' -> must produce EXIT signal.
        """
        mac_strategy.bought['TEST'] = 'LONG'
        mock_bars.set_prices('TEST', [110]*5 + [90]*5)
        mac_strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty(), "Expected an EXIT signal but queue is empty"
        signal = event_queue.get()
        assert signal.signal_type == 'EXIT'
        assert signal.symbol == 'TEST'

    def test_exit_signal_updates_bought_state_to_out(self, mac_strategy, mock_bars, event_queue):
        """After EXIT signal, bought state must transition from 'LONG' to 'OUT'."""
        mac_strategy.bought['TEST'] = 'LONG'
        mock_bars.set_prices('TEST', [110]*5 + [90]*5)
        mac_strategy.calculate_signals(MarketEvent())
        assert mac_strategy.bought['TEST'] == 'OUT'

    def test_no_signal_when_smas_equal(self, mac_strategy, mock_bars, event_queue):
        """
        prices = [100]*10
        short_sma = long_sma = 100 -> neither > nor < -> no signal.
        """
        mock_bars.set_prices('TEST', [100]*10)
        mac_strategy.calculate_signals(MarketEvent())
        assert event_queue.empty(), "No signal expected when SMAs are equal"

    def test_no_long_when_already_long(self, mac_strategy, mock_bars, event_queue):
        """short > long but bought=='LONG' -> no duplicate LONG signal."""
        mac_strategy.bought['TEST'] = 'LONG'
        mock_bars.set_prices('TEST', [90]*5 + [110]*5)  # short > long
        mac_strategy.calculate_signals(MarketEvent())
        assert event_queue.empty(), "No signal expected when already LONG with short > long"

    def test_no_exit_when_already_out(self, mac_strategy, mock_bars, event_queue):
        """short < long but bought=='OUT' -> no EXIT signal."""
        mock_bars.set_prices('TEST', [110]*5 + [90]*5)  # short < long
        mac_strategy.calculate_signals(MarketEvent())
        assert event_queue.empty(), "No EXIT signal expected when already OUT"

    def test_non_market_event_ignored(self, mac_strategy, event_queue):
        """Only MARKET events should trigger signal calculation."""
        class FakeEvent:
            type = 'SIGNAL'
        mac_strategy.calculate_signals(FakeEvent())
        assert event_queue.empty()

    def test_empty_bars_no_crash(self, mac_strategy, mock_bars, event_queue):
        """Strategy handles empty price data gracefully (no exception)."""
        mock_bars.set_prices('TEST', [])
        mac_strategy.calculate_signals(MarketEvent())
        assert event_queue.empty()

    def test_sma_crossover_with_trending_prices(self, mock_bars, event_queue):
        """
        Verify crossover with a realistic uptrend:
        prices = [80, 85, 90, 95, 100, 105, 110, 115, 120, 125]
        short_sma (last 5) = mean([105, 110, 115, 120, 125]) = 575/5 = 115
        long_sma  (all 10) = mean([80..125]) = 1025/10 = 102.5
        short (115) > long (102.5) -> LONG signal.
        """
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=5, long_window=10
        )
        mock_bars.set_prices('TEST', [80, 85, 90, 95, 100, 105, 110, 115, 120, 125])
        strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty(), "Expected LONG signal from upward trending prices"
        signal = event_queue.get()
        assert signal.signal_type == 'LONG'

    def test_full_long_exit_cycle(self, mac_strategy, mock_bars, event_queue):
        """
        Complete cycle: OUT -> LONG -> OUT.
        Step 1: short > long -> LONG signal, state becomes LONG.
        Step 2: short < long -> EXIT signal, state becomes OUT.
        """
        # Step 1: trigger LONG
        mock_bars.set_prices('TEST', [90]*5 + [110]*5)
        mac_strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty()
        signal1 = event_queue.get()
        assert signal1.signal_type == 'LONG'
        assert mac_strategy.bought['TEST'] == 'LONG'

        # Step 2: trigger EXIT
        mock_bars.set_prices('TEST', [110]*5 + [90]*5)
        mac_strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty()
        signal2 = event_queue.get()
        assert signal2.signal_type == 'EXIT'
        assert mac_strategy.bought['TEST'] == 'OUT'

    def test_strategy_never_generates_short_signal(self, mac_strategy, mock_bars, event_queue):
        """MAC strategy only generates LONG and EXIT, never SHORT."""
        scenarios = [
            ('OUT', [90]*5 + [110]*5),    # triggers LONG
            ('LONG', [110]*5 + [90]*5),   # triggers EXIT
            ('OUT', [100]*10),            # no signal
        ]
        for state, prices in scenarios:
            mac_strategy.bought['TEST'] = state
            mock_bars.set_prices('TEST', prices)
            mac_strategy.calculate_signals(MarketEvent())

        signals = []
        while not event_queue.empty():
            signals.append(event_queue.get())

        short_signals = [s for s in signals if s.signal_type == 'SHORT']
        assert len(short_signals) == 0, "MAC strategy should never generate SHORT signals"

    def test_multiple_symbols_independent_signals(self, event_queue):
        """Each symbol generates signals independently based on its own prices."""
        bars = MockBars(['A', 'B'], {
            'A': [90]*5 + [110]*5,   # short > long -> LONG
            'B': [100]*10,           # flat -> no signal
        })
        strategy = MovingAverageCrossStrategy(bars, event_queue, short_window=5, long_window=10)
        strategy.calculate_signals(MarketEvent())

        signals = []
        while not event_queue.empty():
            signals.append(event_queue.get())

        assert len(signals) == 1, f"Expected 1 signal (for A only), got {len(signals)}"
        assert signals[0].symbol == 'A'
        assert signals[0].signal_type == 'LONG'

    def test_marginal_crossover(self, mock_bars, event_queue):
        """
        Barely above crossover should still produce LONG signal.
        prices = [99]*5 + [101]*5
        short_sma = 101, long_sma = 100
        Difference is only 1, but short > long -> LONG.
        """
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=5, long_window=10
        )
        mock_bars.set_prices('TEST', [99]*5 + [101]*5)
        strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty(), "Expected LONG signal even for marginal crossover"
        signal = event_queue.get()
        assert signal.signal_type == 'LONG'

    def test_fewer_bars_than_long_window(self, mock_bars, event_queue):
        """
        With only 7 bars and long_window=10, get_latest_bar_values returns all 7.
        Both SMAs are computed on the same data (7 bars).
        prices = [90, 90, 90, 110, 110, 110, 110]
        short_sma (last 5) = mean([90, 110, 110, 110, 110]) = 530/5 = 106
        long_sma (all 7, since 7 < 10) = mean([90*3, 110*4]) = (270+440)/7 = 101.43
        short > long -> LONG signal.
        """
        strategy = MovingAverageCrossStrategy(
            mock_bars, event_queue, short_window=5, long_window=10
        )
        mock_bars.set_prices('TEST', [90, 90, 90, 110, 110, 110, 110])
        strategy.calculate_signals(MarketEvent())

        assert not event_queue.empty(), "Expected LONG signal with fewer bars than long_window"
        signal = event_queue.get()
        assert signal.signal_type == 'LONG'
