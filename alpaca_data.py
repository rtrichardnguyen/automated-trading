import datetime
import numpy as np
import pandas as pd

from event import MarketEvent
from data import DataHandler

class AlpacaDataHandler(DataHandler):

    def __init__(self, events, symbol_list):

        self.events = events
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

    def get_latest_bar(self, symbol):
        pass

    def get_latest_bars(self, symbol, N=1):
        pass

    def get_latest_bar_datetime(self, symbol):
        pass

    def get_latest_bar_value(self, symbol, val_type):
        pass

    def get_latest_bar_values(self, symbol, val_type, N=1):
        pass

    def update_bars(self):
        pass
