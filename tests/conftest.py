# tests/conftest.py

import pytest
import queue
from datetime import datetime
import pandas as pd
import numpy as np


@pytest.fixture
def event_queue():
    """Provides a fresh event queue for each test."""
    return queue.Queue()


@pytest.fixture
def symbol_list():
    """Standard symbol list for testing."""
    return ['TEST', 'AAPL']


@pytest.fixture
def start_date():
    """Standard start date for testing."""
    return datetime(2024, 1, 1, 0, 0, 0)


@pytest.fixture
def initial_capital():
    """Standard initial capital for testing."""
    return 100000.0


@pytest.fixture
def sample_csv_data():
    """Deterministic OHLCV data for testing with known prices."""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    # Explicit, hand-chosen prices - no randomness
    prices = [100.0, 102.0, 101.0, 104.0, 103.0, 106.0, 105.0, 108.0, 107.0, 110.0]
    data = {
        'open':      [p - 1.0 for p in prices],
        'close':     prices,
        'adj_close': prices,
        'volume':    [1000000] * 10
    }
    return pd.DataFrame(data, index=dates)
