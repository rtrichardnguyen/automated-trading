import yfinance as yf
import pandas as pd

from datetime import timedelta

COLUMN_MAP = {
    'Date': 'datetime',
    'Open': 'open',
    'Close': 'close',
    'Adj Close': 'adj_close',
    'Volume': 'volume'
}


class Download(object):

    def __init__(self, symbol_list):

        self._download(symbol_list)

    def _download(self, symbol_list):
        for s in symbol_list:
            ticker = yf.Ticker(s)
            df = ticker.history(interval='1d', start=(pd.Timestamp.now(tz='UTC') - timedelta(weeks=260)), auto_adjust=False)
            df.drop(columns=['Dividends', 'Stock Splits', 'High', 'Low'], inplace=True)

            df.rename(columns=COLUMN_MAP, inplace=True)
            df.index.name = 'datetime'
            df.to_csv(f"{s}.csv")

