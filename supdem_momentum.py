from datetime import datetime, UTC
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

class SupplyDemandMomentumStrategy(Strategy):

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

    def _same_hhmm_bar_days_back(self, symbol, days_back, tolerance_minutes=1):

        bars = self.bars.latest_symbol_data.get(symbol)
        cur_time = self.bars.get_latest_bar_datetime(symbol)

        for bar in reversed(bars[:-1]):
            prev_bar_time = datetime.strptime(bar[0], "%Y-%m-%d %H:%M:%S")
            cur_bar_time = datetime.strptime(cur_time, "%Y-%m-%d %H:%M:%S")
            if bar[0].hour == cur_time.hour:
                print(f"{bar[0]}, {cur_time}")

    def calculate_signals(self, event):

        if event.type == 'MARKET':

            cur_date = datetime.now(UTC)

            for symbol in self.symbol_list:
                self._same_hhmm_bar_days_back(symbol, 1, 1)

