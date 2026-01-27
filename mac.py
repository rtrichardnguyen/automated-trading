# mac.py

from datetime import datetime as dt

import numpy as np
import pandas as pd

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio

class MovingAverageCrossStrategy(Strategy):

    def __init__(self, bars, events, short_window=100, long_window=400):

        self.bars = bars
        self.events = events
        self.short_window = short_window
        self.long_window = long_window

        self.symbol_list = self.bars.symbol_list

        self.bought = self._calculate_initial_bought()


    def _calculate_initial_bought(self):

        bought = {}

        for s in self.symbol_list:
            bought[s] = 'OUT'

        return bought

    def calculate_signals(self, event):

        if event.type == 'MARKET':

            for s in self.symbol_list:

                bars = self.get_latest_bar_values(s, 'adj_close', N=self.long_window)

                bar_date = get_latest_bar_datetime(s)

                if bars.size > 0:

                    short_sma = np.mean(bars[-self.short_window:])
                    long_sma = np.mean(bars[-self.long_window:])

                    symbol = s
                    cur_date = dt.utcnow()
                    sig_dir = ""

                    if short_sma > long_sma and self.bought[s] == 'OUT':

                        print(f"LONG: {bar_date}")
                        sig_dir = 'LONG'
                        signal = SignalEvent(1, symbol, cur_date, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'LONG'

                    elif short_sma < long_sma and self.bought[s] == "LONG":

                        print(f"SHORT: {bar_date}")
                        sig_dir = 'EXIT'
                        signal = SignalEvent(1, symbol, cur_date, sig_dir, 1.0)
                        self.events.put(signal)
                        self.bought[s] = 'OUT'


if __name__ == '__main__':

    csv_dir = './'
    symbol_list = ['AMD']
    initial_capital = 196000.0
    heartbeat = 0.0
    start_date = dt(2026, 1, 26, 0, 0, 0)

    backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat, start_date, HistoricCSVDataHandler, SimulatedExecutionHandler, Portfolio, MovingAverageCrossStrategy)
    backtest.simulate_trading()











