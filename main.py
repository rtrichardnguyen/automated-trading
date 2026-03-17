import argparse
from datetime import datetime as dt

from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio
from download import Download

from mac import MovingAverageCrossStrategy
from supdem_momentum import SupplyDemandMomentumStrategy

STRATEGIES = {
    'mac': MovingAverageCrossStrategy,
    'supdem': SupplyDemandMomentumStrategy,
}

def run_backtest(strategy_name, symbols, capital, start_date):
    Download(symbols)
    strategy_cls = STRATEGIES[strategy_name]
    backtest = Backtest(
        './', symbols, capital, 0.0, start_date,
        HistoricCSVDataHandler, SimulatedExecutionHandler,
        Portfolio, strategy_cls
    )
    backtest.simulate_trading()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a trading backtest')
    parser.add_argument('--strategy', choices=STRATEGIES.keys(), required=True)
    parser.add_argument('--symbols', nargs='+', default=['AMD'])
    parser.add_argument('--capital', type=float, default=196000.0)
    parser.add_argument('--start', default='2026-01-26')
    args = parser.parse_args()

    start_date = dt.strptime(args.start, '%Y-%m-%d')
    run_backtest(args.strategy, args.symbols, args.capital, start_date)
