import numpy as np
import pandas as pd

from datetime import datetime, UTC
from dateutil.relativedelta import relativedelta

from event import MarketEvent
from data import DataHandler

from massive import RESTClient


class MassiveHistoricDataHandler(DataHandler):

    def __init__(self, api_key, events, symbol_list, timespan, multiplier):

        self.api_key = api_key
        self.events = events
        self.symbol_list = symbol_list
        self.timespan = timespan
        self.multiplier = multiplier

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self.client = RESTClient(api_key=api_key)
        self._download_historic_data(self.timespan, self.multiplier, self.symbol_list)

    def _download_historic_data(self, timespan, multiplier, symbol_list):

        comb_index = None
        start = datetime.now(UTC) - relativedelta(years=2)
        end = datetime.now(UTC)

        for symbol in symbol_list:
            try:
                historic_data = self.client.list_aggs(
                    ticker=symbol,
                    multiplier=multiplier,
                    timespan=timespan,
                    from_=start,
                    to=end,
                    sort='asc',
                    limit=50000
                )
            except Exception as exc:
                raise RuntimeError(f"Failed to download historical data for {symbol}") from exc

            self.latest_symbol_data[symbol] = []

            bar_list = []
            for bar in historic_data:
                dt = datetime.fromtimestamp(bar.timestamp / 1000, tz=UTC)
                bar_list.append({
                    'datetime': dt,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    # Keep the existing DataHandler interface intact.
                    'adj_close': bar.close,
                    'volume': bar.volume,
                    'vwap': bar.vwap,
                    'transactions': bar.transactions,
                    'otc': bar.otc,
                })

            if not bar_list:
                raise ValueError(f"No historical data returned for symbol '{symbol}'")

            self.symbol_data[symbol] = pd.DataFrame(bar_list).set_index("datetime")
            self.symbol_data[symbol].sort_index(inplace=True)

            if comb_index is None:
                comb_index = self.symbol_data[symbol].index
            else:
                comb_index = comb_index.union(self.symbol_data[symbol].index)

        for symbol in self.symbol_list:
            self.symbol_data[symbol] = self.symbol_data[symbol].reindex(index=comb_index, method='pad')
            self.symbol_data[symbol]['returns'] = self.symbol_data[symbol]['adj_close'].pct_change().dropna()
            self.symbol_data[symbol] = self.symbol_data[symbol].iterrows()

    def _get_new_bar(self, symbol):
        for bar in self.symbol_data[symbol]:
            yield bar

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
            return np.array([getattr(bar[1], val_type) for bar in bars_list[-N:]])

    def update_bars(self):
        for symbol in self.symbol_list:
            try:
                bar = next(self._get_new_bar(symbol))
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[symbol].append(bar)
        self.events.put(MarketEvent())
