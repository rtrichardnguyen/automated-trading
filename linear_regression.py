from datetime import datetime as dt
from datetime import timedelta

import numpy as np
import pandas as pd

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio
from download import Download

from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

import yfinance as yf
import pandas as pd

class LinearRegressionStrategy(Strategy):

    def __init__(self, bars, events):

        self.bars = bars
        self.events = events

        self.symbol_list = self.bars.symbol_list
        self.bought = self._calculate_initial_bought()

    def _calculate_initial_bought(self):

        bought = {}

        for symbol in self.symbol_list:
            bought['symbol'] = 'OUT'

        return bought

    def calculate_signals(self, event):

        if event.type == 'MARKET':
            spy = self.symbol_list[0]
            nvda = self.symbol_list[1]

            X = self.bars.get_latest_bar_values(spy, 'adj_close', N=40).reshape(-1, 1)
            Y = self.bars.get_latest_bar_values(nvda, 'adj_close', N=40)
            model = LinearRegression()
            model.fit(X, Y)

            Y_pred = model.predict(X)

            plt.figure(figsize=(8, 6))
            plt.scatter(X, Y, color='blue', label='Data Points')
            plt.plot(X, Y_pred, color='red', linewidth='2', label='Linear Regression')
            plt.legend()
            plt.grid(True)
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.show()

if __name__ == '__main__':

    csv_dir = './'
    symbol_list = ['SPY', 'NVDA']
    initial_capital = 1000000
    heartbeat = 0.0
    start_date = dt(2026, 2, 24, 0, 0, 0)

    Download(symbol_list)

    backtest = Backtest(csv_dir, symbol_list, initial_capital, heartbeat, start_date, HistoricCSVDataHandler, SimulatedExecutionHandler, Portfolio, LinearRegressionStrategy)
    backtest.simulate_trading()
