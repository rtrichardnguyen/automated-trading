# #data.py

from abc import ABCMeta, abstractmethod
import datetime 
import os, os.path

import numpy as np
import pandas as pd

from event import MarketEvent

class DataHandler(object):

    """

    DataHandler is an abstract base class providing an interface for
    all subsequent (inherited) data handlers (both live and historic).
    The goal of a (derived) DataHandler object is to output a generated
    set of bars (OHLCVI) for each symbol requested.
    This will replicate how a live strategy would function as current
    market data would be sent "down the pipe". Thus a historic and live
    system will be treated identically by the rest of the backtesting suite.

    """

    __metaclass__ = ABCMeta


    @abstractmethod
    def get_latest_bar(self, symbol):
        
        """
        Returns the last bar updated.
        """

        raise NotImplementedError("Implement get_latest_bar()")


    @abstractmethod
    def get_latest_bars(self, symbol, N=1):

        """
        Returns the last N bars updated.
        """

        raise NotImplementedError("Implement get_latest_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        
        """
        Returns a Python datetime object for the last bar.
        """

        raise NotImplementedError("Implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):

        """
        Returns one of the Open, High, Low, Close, Volume or OI from the last bar.
        """

        raise NotImplementedError("Implement get_latest_bar_value()")

    @abstractmethod
    def get_latest_bar_values(self, symbol, val_type, N=1):

        """
        Returns the last N bar values from the
        latest_symbol list, or N - k if less available.
        """

        raise NotImplementedError("Implement get_latest_bar_values()")

    @abstractmethod
    def update_bars(self):

        """
        Pushes the latest bars to the bars_queue for each symbol
        in a tuple OHLCVI format: (datetime, open, high, low,
        close, volume, open interest).
        """

        raise NotImplementedError("Implement update_bars()")


class HistoricCSVDataHandler(DataHandler):

    def __init__(self, events, csv_dir, symbol_list):

        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self._open_convert_csv_files()


    def _open_convert_csv_files(self):

        comb_index = None
        for symbol in self.symbol_list:

            self.symbol_data[symbol] = pd.read_csv(os.path.join(self.csv_dir, f'{symbol}.csv'), header=0, index_col=0, parse_dates=True, names=['datetime', 'open', 'close', 'adj_close', 'volume'])
            self.symbol_data[symbol].sort_index(inplace=True)

            if comb_index is None:
                comb_index = self.symbol_data[symbol].index
            else:
                comb_index.union(self.symbol_data[symbol].index)

            self.latest_symbol_data[symbol] = []

        for s in self.symbol_list:
            self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad')
            self.symbol_data[s]['returns'] = self.symbol_data[s]['adj_close'].pct_change().dropna()
            self.symbol_data[s] = self.symbol_data[s].iterrows()

    def _get_new_bar(self, symbol):
        for b in self.symbol_data[symbol]:
            yield b


    def get_latest_bar(self, symbol):

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available in data set")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available in data set")
            raise 
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available in data set")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, val_type):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available in data set")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)

    def get_latest_bar_values(self, symbol, val_type, N=1):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol is not available in data set")
            raise
        else:
            return np.array([getattr(b[1], val_type) for b in bars_list[-N:]])

    def update_bars(self):
        for s in self.symbol_list:
            try:
                bar = next(self._get_new_bar(s))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)
        self.events.put(MarketEvent())
