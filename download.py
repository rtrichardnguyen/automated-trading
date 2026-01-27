import yfinance as yf
import pandas as pd

from datetime import timedelta

ticker = yf.Ticker("AMD")
df = ticker.history(interval='1d', start=(pd.Timestamp.now(tz='UTC') - timedelta(weeks=260)), auto_adjust=False)

COLUMN_MAP = {
    'Date': 'datetime',
    'Open': 'open',
    'Close': 'close',
    'Adj Close': 'adj_close',
    'Volume': 'volume'
}

df.drop(columns=['Dividends', 'Stock Splits', 'High', 'Low'], inplace=True)

df.rename(columns=COLUMN_MAP, inplace=True)
df.index.name = 'datetime'

df.to_csv("AMD.csv")

print(df.columns)
print(df.index)
