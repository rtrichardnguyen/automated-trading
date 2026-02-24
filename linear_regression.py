from datetime import datetime as datetime

import numpy as np
import pandas as pd

from strategy import Strategy
from event import SignalEvent
from backtest import Backtest
from data import HistoricCSVDataHandler
from execution import SimulatedExecutionHandler
from portfolio import Portfolio

from sklearn.linear_model import LinearRegression

class LinearRegressionStrategy(Strategy):

    def __init__(self, bars, events):
        self.bars = bars
        self.events = events

        self.symbol_list = self.bars.symbol_list
