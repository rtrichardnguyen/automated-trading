from datetime import UTC, datetime as dt
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
            bought[symbol] = 'OUT'

        return bought

    def calculate_signals(self, event):

        if event.type == 'MARKET':
            spy = self.symbol_list[0]
            nvda = self.symbol_list[1]

            X = self.bars.get_latest_bar_values(spy, 'adj_close', N=40).reshape(-1, 1)
            Y = self.bars.get_latest_bar_values(nvda, 'adj_close', N=40)

            if len(X) < 40:
                return

            model = LinearRegression()
            model.fit(X, Y)

            Y_pred = model.predict(X)
            spread = Y - Y_pred
            z_scores = (spread - spread.mean()) / spread.std()

            if z_scores[-1] < -1 and self.bought[nvda] == 'OUT':
                sig_dir = 'LONG'
            elif z_scores[-1] > 1 and self.bought[nvda] == 'OUT':
                sig_dir = 'SHORT'
            elif z_scores[-1] > 1 and self.bought[nvda] == 'LONG':
                sig_dir = 'EXIT'
            elif z_scores[-1] < -1 and self.bought[nvda] == 'SHORT':
                sig_dir = 'EXIT'
            else:
                sig_dir = None

            if sig_dir:

                bar_datetime = self.bars.get_latest_bar_datetime(nvda)
                cur_datetime = dt.now(UTC)

                print(f"{sig_dir}: {bar_datetime}")
                signal = SignalEvent(1, nvda, bar_datetime, sig_dir, 1.0)

                self.events.put(signal)


                if sig_dir == 'LONG' or sig_dir == 'SHORT':
                    position_type = sig_dir
                else:
                    position_type = 'OUT'

                self.bought[nvda] = position_type

            '''
            plt.figure(figsize=(8, 6))
            plt.scatter(X, Y, color='blue', label='Data Points')
            plt.plot(X, Y_pred, color='red', linewidth='2', label='Linear Regression')
            plt.legend()
            plt.grid(True)
            plt.xlabel('X')
            plt.ylabel('Y')
            # plt.show()
            '''
