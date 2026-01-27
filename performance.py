# performance .py

import numpy as np
import pandas as pd

def create_sharpe_ratio(returns, periods=252):

    """

    Create the Sharpe ratio for the strategy, based on a
    benchmark of zero (i.e. no risk-free rate information).

    Parameters:
    returns - A Pandas Series representing period percentage returns.
    periods - Daily (252), Hourly (252*6.5), Minutely(252*6.5*60) etc.

    """

    return np.sqrt(periods) * (np.mean(returns)) / np.std(returns)

def create_drawdowns(pnl):

    """

    Calculate the largest peak-to-trough drawdown of the PnL curve
    as well as the duration of the drawdown. Requires that the
    pnl_returns is a Pandas Series.

    Parameters:
    pnl - A Pandas Series representing period percentage returns.

    Returns:
    drawdown, duration - Highest peak-to-trough drawdown and duration.


    """

    # High water mark
    hwm = [0]

    # Drawdown and duration series
    i = pnl.index
    drawdown = pd.Series(index=i, dtype=float)
    duration = pd.Series(index=i, dtype=float)

    for t in range(1, len(i)):
        hwm.append(max(hwm[t - 1], pnl.iloc[t]))
        drawdown.iloc[t] = (hwm[t] - pnl.iloc[t])
        duration.iloc[t] = (0 if drawdown.iloc[t] == 0 else duration.iloc[t - 1] + 1)

    return drawdown, drawdown.max(), duration.max()
