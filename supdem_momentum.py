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

class SupplyDemandMomentumStrategy(Strategy):

    def __init__(self, bars, events):

        self.bars = bars
        self.events = events

        self.symbol_list = symbol_list
        self.bought = self._calculate_initial_bought

    def _calculate_initial_bought(self):

        bought = {}

        for symbol in self.symbol_list:
            bought[symbol] = 'OUT'

        return bought

    def calculate_signals(self, event):

        if event.type == 'MARKET':

            for symbol in self.symbol_list:
                pass

