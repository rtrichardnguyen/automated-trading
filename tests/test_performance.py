# tests/test_performance.py

import pytest
import numpy as np
import pandas as pd
from performance import create_sharpe_ratio, create_drawdowns


class TestSharpeRatio:
    """Test Sharpe ratio calculations."""

    def test_sharpe_ratio_positive_returns(self):
        """Test Sharpe ratio with positive returns."""
        returns = pd.Series([0.01, 0.02, 0.015, 0.01, 0.02] * 50)
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert sharpe > 0
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_negative_returns(self):
        """Test Sharpe ratio with negative returns."""
        returns = pd.Series([-0.01, -0.02, -0.015, -0.01, -0.02] * 50)
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert sharpe < 0

    def test_sharpe_ratio_mixed_returns(self):
        """Test Sharpe ratio with mixed returns."""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015] * 40)
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_zero_returns(self):
        """Test Sharpe ratio with zero returns."""
        returns = pd.Series([0.0] * 100)
        # Zero standard deviation should result in NaN or inf
        sharpe = create_sharpe_ratio(returns, periods=252)
        assert np.isnan(sharpe) or np.isinf(sharpe)

    def test_sharpe_ratio_different_periods(self):
        """Test Sharpe ratio with different period values."""
        returns = pd.Series([0.01, 0.02, 0.015] * 30)

        sharpe_daily = create_sharpe_ratio(returns, periods=252)
        sharpe_hourly = create_sharpe_ratio(returns, periods=252*6.5)

        # Higher periods should result in higher Sharpe (due to sqrt(periods))
        assert sharpe_hourly > sharpe_daily


class TestDrawdowns:
    """Test drawdown calculations."""

    def test_drawdowns_increasing_pnl(self):
        """Test drawdowns with steadily increasing PnL."""
        pnl = pd.Series([100, 105, 110, 115, 120, 125])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert isinstance(drawdown, pd.Series)
        assert max_dd == 0.0
        assert dd_duration == 0.0

    def test_drawdowns_with_decline(self):
        """Test drawdowns with a decline."""
        pnl = pd.Series([100, 110, 105, 100, 95, 105, 115])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd > 0
        assert dd_duration > 0
        assert len(drawdown) == len(pnl)

    def test_drawdowns_severe_decline(self):
        """Test drawdowns with severe decline."""
        pnl = pd.Series([100, 110, 90, 80, 70, 75, 80])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        # Max drawdown should be from 110 to 70 = 40
        assert max_dd == 40.0

    def test_drawdowns_multiple_peaks(self):
        """Test drawdowns with multiple peaks and valleys."""
        pnl = pd.Series([100, 110, 105, 115, 110, 105, 100, 110])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd > 0
        assert dd_duration >= 0

    def test_drawdowns_flat_pnl(self):
        """Test drawdowns with flat PnL."""
        pnl = pd.Series([100] * 10)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        assert max_dd == 0.0
        assert dd_duration == 0.0

    def test_drawdowns_recovery(self):
        """Test drawdowns with recovery to new high."""
        pnl = pd.Series([100, 110, 90, 95, 100, 115, 120])
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)

        # Should have drawdown from 110 to 90 = 20
        assert max_dd == 20.0
        # Drawdown should be 0 at the end (new high)
        assert drawdown.iloc[-1] == 0.0
