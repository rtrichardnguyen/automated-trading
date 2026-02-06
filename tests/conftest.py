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
    """Sample OHLCV data for testing."""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    data = {
        'open': np.random.uniform(95, 105, 100),
        'close': np.random.uniform(95, 105, 100),
        'adj_close': np.random.uniform(95, 105, 100),
        'volume': np.random.randint(1000000, 10000000, 100)
    }
    return pd.DataFrame(data, index=dates)
