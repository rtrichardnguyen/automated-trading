# tests/test_performance.py

import pytest
import math
import numpy as np
import pandas as pd
from performance import create_sharpe_ratio, create_drawdowns


class TestSharpeRatio:
    """Test Sharpe ratio with independently hand-calculated expected values.

    The implementation uses: sqrt(periods) * mean(returns) / std(returns)
    where std uses population standard deviation (ddof=0).

    Expected values below are derived algebraically, NOT by repeating the formula.
    """

    def test_sharpe_ratio_known_values(self):
        """
        returns = [0.01, 0.02, 0.03], periods = 252.
        mean = 0.02
        population variance = ((0.01-0.02)^2 + 0^2 + (0.03-0.02)^2) / 3
                            = (0.0001 + 0 + 0.0001) / 3 = 2e-4 / 3
        population std = sqrt(2e-4 / 3) = 0.01 * sqrt(2/3)
        sharpe = sqrt(252) * 0.02 / (0.01 * sqrt(2/3))
               = sqrt(252) * 2 * sqrt(3/2)
               = sqrt(252) * sqrt(4) * sqrt(3/2)
               = sqrt(252 * 4 * 3/2)
               = sqrt(252 * 6)
               = sqrt(1512)
        """
        returns = pd.Series([0.01, 0.02, 0.03])
        sharpe = create_sharpe_ratio(returns, periods=252)
        expected = math.sqrt(1512)  # ≈ 38.884
        assert sharpe == pytest.approx(expected, rel=1e-10)

    def test_sharpe_ratio_negative_returns(self):
        """
        returns = [-0.01, -0.02, -0.03], periods = 252.
        By symmetry with the positive case, magnitude is the same but sign is negative.
        sharpe = -sqrt(1512)
        """
        returns = pd.Series([-0.01, -0.02, -0.03])
        sharpe = create_sharpe_ratio(returns, periods=252)
        expected = -math.sqrt(1512)
        assert sharpe == pytest.approx(expected, rel=1e-10)
        assert sharpe < 0

    def test_sharpe_ratio_constant_positive_returns(self):
        """Constant returns have std=0, so sharpe = mean/0 = +inf."""
        returns = pd.Series([0.01, 0.01, 0.01, 0.01, 0.01])
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert np.isinf(sharpe)
        assert sharpe > 0

    def test_sharpe_ratio_zero_returns(self):
        """All-zero returns: mean=0, std=0, so sharpe = 0/0 = NaN."""
        returns = pd.Series([0.0] * 100)
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert np.isnan(sharpe)

    def test_sharpe_ratio_symmetric_returns_is_zero(self):
        """Returns that sum to zero have mean=0, so sharpe=0 regardless of std."""
        returns = pd.Series([0.01, -0.01] * 50)
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert sharpe == pytest.approx(0.0, abs=1e-10)

    def test_sharpe_scales_with_sqrt_of_periods(self):
        """
        Sharpe with periods=P1 vs P2 should differ by factor sqrt(P1/P2).
        sharpe_hourly / sharpe_daily = sqrt(252*6.5) / sqrt(252) = sqrt(6.5)
        """
        returns = pd.Series([0.01, 0.02, 0.015, 0.005, 0.012] * 20)

        sharpe_daily = create_sharpe_ratio(returns, periods=252)
        sharpe_hourly = create_sharpe_ratio(returns, periods=252 * 6.5)

        ratio = sharpe_hourly / sharpe_daily
        assert ratio == pytest.approx(math.sqrt(6.5), rel=1e-10)

    def test_sharpe_ratio_single_return(self):
        """
        Single return [0.05], periods=252.
        mean = 0.05, std = 0 (single element, population std = 0).
        sharpe = sqrt(252) * 0.05 / 0 = +inf.
        """
        returns = pd.Series([0.05])
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert np.isinf(sharpe)
        assert sharpe > 0

    def test_sharpe_ratio_two_returns(self):
        """
        returns = [0.02, 0.04], periods = 1.
        mean = 0.03
        population std = sqrt(((0.02-0.03)^2 + (0.04-0.03)^2) / 2)
                       = sqrt((0.0001 + 0.0001) / 2) = sqrt(0.0001) = 0.01
        sharpe = sqrt(1) * 0.03 / 0.01 = 3.0
        """
        returns = pd.Series([0.02, 0.04])
        sharpe = create_sharpe_ratio(returns, periods=1)
        assert sharpe == pytest.approx(3.0, rel=1e-10)


class TestDrawdowns:
    """Test drawdown calculations with hand-calculated expected values.

    The implementation initializes HWM at [0] and iterates from index 1.
    Index 0's drawdown and duration are never assigned (remain NaN).
    """

    def test_monotonically_increasing_zero_drawdown(self):
        """Always making new highs -> zero drawdown everywhere (except index 0)."""
        pnl = pd.Series([100, 105, 110, 115, 120, 125])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 0.0
        assert dd_duration == 0.0
        assert len(drawdown) == 6

    def test_known_drawdown_values(self):
        """
        pnl = [100, 110, 90, 80, 70, 75, 80]
        HWM:      [0, 110, 110, 110, 110, 110, 110]
        Drawdown: [NaN, 0, 20, 30, 40, 35, 30]
        Duration: [NaN, 0, 1, 2, 3, 4, 5]
        """
        pnl = pd.Series([100, 110, 90, 80, 70, 75, 80])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 40.0
        assert dd_duration == 5.0
        # Verify each index
        assert drawdown.iloc[1] == 0.0    # new high at 110
        assert drawdown.iloc[2] == 20.0   # 110 - 90
        assert drawdown.iloc[3] == 30.0   # 110 - 80
        assert drawdown.iloc[4] == 40.0   # 110 - 70
        assert drawdown.iloc[5] == 35.0   # 110 - 75
        assert drawdown.iloc[6] == 30.0   # 110 - 80

    def test_recovery_to_new_high(self):
        """
        pnl = [100, 110, 90, 95, 100, 115, 120]
        After the dip, recovery to 115 (new high) resets drawdown to 0.
        HWM: [0, 110, 110, 110, 110, 115, 120]
        Drawdown at index 2 = 20 (110-90), index 5 = 0, index 6 = 0.
        """
        pnl = pd.Series([100, 110, 90, 95, 100, 115, 120])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 20.0
        assert drawdown.iloc[2] == 20.0
        assert drawdown.iloc[5] == 0.0  # recovered above previous high
        assert drawdown.iloc[6] == 0.0  # new high

    def test_multiple_peaks_drawdown_and_duration(self):
        """
        pnl = [100, 110, 105, 115, 110, 105, 100, 120]
        HWM:      [0, 110, 110, 115, 115, 115, 115, 120]
        Drawdown: [NaN, 0, 5, 0, 5, 10, 15, 0]
        Duration: [NaN, 0, 1, 0, 1, 2, 3, 0]
        Max drawdown = 15, max duration = 3.
        """
        pnl = pd.Series([100, 110, 105, 115, 110, 105, 100, 120])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 15.0
        assert dd_duration == 3.0
        assert drawdown.iloc[3] == 0.0    # new high at 115
        assert drawdown.iloc[6] == 15.0   # 115 - 100
        assert drawdown.iloc[7] == 0.0    # new high at 120

    def test_flat_pnl_zero_drawdown(self):
        """Constant PnL -> zero drawdown."""
        pnl = pd.Series([100] * 10)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 0.0
        assert dd_duration == 0.0

    def test_drawdown_series_length_matches_input(self):
        """Output series has same length as input."""
        pnl = pd.Series([100, 110, 90, 80, 70, 75, 80])
        drawdown, _, _ = create_drawdowns(pnl)
        assert len(drawdown) == len(pnl)

    def test_index_zero_is_nan(self):
        """
        The HWM loop starts at index 1, so index 0 drawdown is never assigned.
        This is a known behavior: the first element is always NaN.
        """
        pnl = pd.Series([100, 110, 90])
        drawdown, _, _ = create_drawdowns(pnl)
        assert pd.isna(drawdown.iloc[0])

    def test_single_element_pnl(self):
        """
        Single-element PnL: loop range(1, 1) executes zero times.
        Drawdown is all NaN, max returns NaN.
        """
        pnl = pd.Series([100])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert len(drawdown) == 1
        assert pd.isna(drawdown.iloc[0])
        assert pd.isna(max_dd)

    def test_duration_resets_after_new_high(self):
        """
        pnl = [100, 110, 105, 100, 115, 110, 105]
        Duration at index 2 = 1, index 3 = 2, index 4 = 0 (new high),
        index 5 = 1, index 6 = 2.
        Both drawdown periods have their own duration counters.
        """
        pnl = pd.Series([100, 110, 105, 100, 115, 110, 105])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        # Drawdown resets at index 4 (new high 115 > previous 110)
        assert drawdown.iloc[4] == 0.0
        # Max duration should be 2 (both drawdown periods lasted 2 bars)
        assert dd_duration == 2.0
