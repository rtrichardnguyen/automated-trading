# Automated Trading System

An event-driven algorithmic trading system built in Python that supports both backtesting with historical data and live trading through the Alpaca API.

## Overview

This project implements a modular, event-driven trading architecture that allows you to develop, backtest, and deploy trading strategies. The system is designed to work seamlessly with both historical CSV data for backtesting and live market data for real-time trading.

## Features

- **Event-Driven Architecture**: Decoupled components communicate through an event queue (Market, Signal, Order, Fill events)
- **Backtesting Engine**: Test strategies against historical data with realistic execution simulation
- **Live Trading Integration**: Execute trades automatically via Alpaca API
- **Portfolio Management**: Track positions, holdings, cash, and performance metrics in real-time
- **Performance Analytics**: Calculate Sharpe ratio, drawdowns, returns, and equity curves
- **Strategy Framework**: Abstract base class for easy strategy development
- **Data Handling**: Support for both historical CSV data and live market feeds
- **Execution Handlers**: Pluggable execution system for simulated and live trading

## Architecture

The system follows an event-driven design pattern with the following components:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌───────────────┐
│   Data      │────▶│   Strategy   │────▶│  Portfolio  │────▶│  Execution    │
│   Handler   │     │              │     │             │     │   Handler     │
└─────────────┘     └──────────────┘     └─────────────┘     └───────────────┘
      │                    │                     │                    │
      └────────────────────┴─────────────────────┴────────────────────┘
                                Event Queue
```

### Core Components

- **Event System** (`event.py`): Defines MarketEvent, SignalEvent, OrderEvent, and FillEvent
- **Data Handler** (`data.py`): Manages market data feed (historical CSV or live)
- **Strategy** (`strategy.py`): Base class for trading strategies
- **Portfolio** (`portfolio.py`): Manages positions, cash, and performance tracking
- **Execution Handler** (`execution.py`, `alpaca_execution.py`): Executes orders (simulated or live)
- **Backtest** (`backtest.py`): Orchestrates the backtesting simulation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd automated-trading
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the project root:
```env
PUBLIC_KEY=your_alpaca_public_key
SECRET_KEY=your_alpaca_secret_key
```

## Requirements

- Python 3.7+
- pandas
- numpy
- yfinance
- alpaca-py
- python-dotenv

## Usage

### Backtesting a Strategy

The project includes a Moving Average Crossover strategy as an example (`mac.py`):

```python
from datetime import UTC, datetime as dt
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio
from mac import MovingAverageCrossStrategy

# Configuration
csv_dir = './'
symbol_list = ['AMD']
initial_capital = 196000.0
heartbeat = 0.0
start_date = dt(2026, 1, 26, 0, 0, 0)

# Run backtest
backtest = Backtest(
    csv_dir,
    symbol_list,
    initial_capital,
    heartbeat,
    start_date,
    HistoricCSVDataHandler,
    SimulatedExecutionHandler,
    Portfolio,
    MovingAverageCrossStrategy
)
backtest.simulate_trading()
```

### Live Trading

Execute live trades using the Alpaca API (`app.py`):

```python
from queue import Queue
from event import OrderEvent
from alpaca_execution import AlpacaExecutionHandler
import threading

# Initialize
event_queue = Queue()
execution_handler = AlpacaExecutionHandler(event_queue, PUBLIC_KEY, SECRET_KEY)

# Start WebSocket connection
ws_thread = threading.Thread(target=execution_handler.open_connection, daemon=True)
ws_thread.start()

# Execute order
order = OrderEvent('MSFT', 'MKT', 1, 'BUY')
execution_handler.execute_order(order)
```

### Creating a Custom Strategy

Inherit from the `Strategy` base class:

```python
from strategy import Strategy
from event import SignalEvent

class MyStrategy(Strategy):
    def __init__(self, bars, events):
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list

    def calculate_signals(self, event):
        if event.type == 'MARKET':
            # Your strategy logic here
            # Generate signals based on market data
            signal = SignalEvent(
                strategy_id=1,
                symbol='AAPL',
                datetime=dt.now(UTC),
                signal_type='LONG',
                strength=1.0
            )
            self.events.put(signal)
```

## Project Structure

```
automated-trading/
├── app.py                   # Live trading entry point
├── backtest.py             # Backtesting engine
├── strategy.py             # Strategy base class
├── mac.py                  # Moving Average Crossover strategy example
├── event.py                # Event definitions
├── data.py                 # Data handler classes
├── alpaca_data.py          # Alpaca data integration
├── portfolio.py            # Portfolio management
├── execution.py            # Simulated execution handler
├── alpaca_execution.py     # Alpaca live execution handler
├── performance.py          # Performance metrics
├── download.py             # Data download utilities
├── time.py                 # Time utilities
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── README.md               # Project documentation
├── CLAUDE.md               # Development guide for Claude Code
└── tests/                  # Unit and integration tests
    ├── conftest.py         # Shared test fixtures
    ├── test_event.py       # Event class tests
    ├── test_portfolio.py   # Portfolio tests
    ├── test_strategy.py    # Strategy tests
    ├── test_execution.py   # Execution handler tests
    ├── test_data.py        # Data handler tests
    ├── test_performance.py # Performance metric tests
    └── test_backtest.py    # Integration tests
```

## Strategy Example: Moving Average Crossover

The included Moving Average Crossover strategy (`mac.py`) demonstrates:
- Short-term (20-period) and long-term (50-period) moving averages
- Buy signal when short MA crosses above long MA
- Sell signal when short MA crosses below long MA
- Position tracking to avoid duplicate signals

## Performance Metrics

The system automatically calculates:
- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted return metric
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Drawdown Duration**: Length of drawdown periods
- **Equity Curve**: Portfolio value over time (exported to `equity.csv`)

## Data Requirements

For backtesting, prepare CSV files with the following format:
```csv
datetime,open,close,adj_close,volume
2024-01-01,100.0,102.0,102.0,1000000
```

You can download data using `yfinance`:
```python
import yfinance as yf
ticker = yf.Ticker("AAPL")
df = ticker.history(period="1y", interval="1d")
df.to_csv("AAPL.csv")
```

## Configuration

### Backtest Parameters
- `csv_dir`: Directory containing historical CSV data
- `symbol_list`: List of ticker symbols to trade
- `initial_capital`: Starting portfolio value
- `heartbeat`: Delay between iterations (0 for historical)
- `start_date`: Backtest start date

### Portfolio Settings
- Default commission: 0 (customize in `event.py:_calculate_commission()`)
- Position sizing: Fixed 100 shares (customize in `portfolio.py:generate_naive_order()`)

## Testing

The project includes a comprehensive test suite using pytest.

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_event.py

# Run specific test class
pytest tests/test_portfolio.py::TestPortfolioInitialization

# Run with verbose output
pytest -v
```

### Test Coverage

Tests are organized by component:
- **test_event.py**: Tests for all event types (Market, Signal, Order, Fill)
- **test_portfolio.py**: Portfolio management, position tracking, and order generation
- **test_strategy.py**: Strategy base class and Moving Average Crossover strategy
- **test_execution.py**: Simulated execution handler tests
- **test_data.py**: CSV data handler and bar access methods
- **test_performance.py**: Sharpe ratio and drawdown calculations
- **test_backtest.py**: End-to-end integration tests

### Writing New Tests

When adding new features, follow the existing test patterns:

```python
# tests/test_your_feature.py
import pytest
from your_module import YourClass

@pytest.fixture
def your_fixture():
    """Provides test data or objects."""
    return YourClass()

class TestYourFeature:
    """Test your feature."""

    def test_basic_functionality(self, your_fixture):
        """Test description."""
        result = your_fixture.do_something()
        assert result == expected_value
```

## Production Readiness

### Current Status (as of 2026-02-07)

- **Overall live-trading readiness**: ~40% (strong research/backtesting base, not yet safe for real-capital production)
- **Backtesting test status**: `162 passed` via `./venv/bin/pytest -q`
- **Coverage status**: `95% total` via `./venv/bin/pytest --cov=. --cov-report=term-missing -q`

### What Is Already Strong

- Event-driven architecture with clear component boundaries
- Deterministic, high-coverage tests across core backtesting flows
- End-to-end backtest execution from data feed to performance output

### Key Gaps Before Production

- `AlpacaDataHandler` is currently a skeleton and not production-capable
- Live execution path still needs hardening around async updates, partial fills, and broker-state reconciliation
- No production risk controls (position limits, daily loss limits, kill switch, exposure caps)
- No persistent state/reconciliation for restarts (orders, fills, positions)
- No structured observability stack (logs, metrics, alerting, audit trail)
- No CI enforcement (tests/lint/type checks on every commit)
- Dependencies are unpinned, reducing reproducibility and deployment safety

### Minimum Go-Live Checklist

- [ ] Fully implement `AlpacaDataHandler` with reconnect, backfill, and market-hours behavior
- [ ] Harden `AlpacaExecutionHandler` for async updates, partial fills, retries, and idempotency
- [ ] Add risk engine: sizing rules, max notional/exposure, daily loss limits, and emergency stop
- [ ] Add persistent storage for orders/fills/positions and startup reconciliation with broker state
- [ ] Add structured logging, metrics, and real-time alerts for trading and infrastructure failures
- [ ] Add CI pipeline with coverage threshold, linting, and type checking
- [ ] Pin dependencies and define a repeatable release environment
- [ ] Create an operations runbook (incident response, manual override, rollback process)
- [ ] Validate in paper trading for 2-4 weeks before limited-capital live rollout

### Suggested Release Gates

- **Gate 1**: Deterministic backtest acceptance criteria (reproducible metrics)
- **Gate 2**: Stable paper trading period with zero unreconciled state drift
- **Gate 3**: Limited-capital live with strict risk caps and alerting
- **Gate 4**: Scale up only after a clean pilot period and post-trade reviews

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Future Enhancements

- [ ] Add more built-in strategies (momentum, mean reversion, pairs trading)
- [ ] Implement risk management module
- [ ] Add support for multiple timeframes
- [ ] Integrate additional data sources (Polygon, IEX)
- [ ] Build web dashboard for monitoring
- [ ] Add machine learning strategy framework
- [ ] Implement paper trading mode
- [ ] Add logging and error handling improvements

## Literature

- Successful Algorithmic Trading - Michael L. Halls-Moore, PhD.
- Algorithmic Trading & DMA - Barry Johnson
- pre-print servers for strategies: arXiv, SSRN, Journal of Investment Strategies (risk.net), Journal of Computational Finance (risk.net)

## Data feeds
- Tiingo
- AlphaVantage
- Polygon

## Disclaimer

This software is for educational purposes only. Trading financial instruments carries risk. Use at your own discretion and always test thoroughly before deploying with real capital.

## License

MIT License - see LICENSE file for details
