from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.stream import TradingStream

import yfinance as yf
import pandas as pd

load_dotenv()

PUBLIC_KEY = os.getenv('PUBLIC_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')

trading_client = TradingClient(PUBLIC_KEY, SECRET_KEY)

account = trading_client.get_account()

# Check if our account is restricted from trading.
if account.trading_blocked:
    print('Account is currently restricted from trading.')

# Check how much money we can use to open new positions.
print('${} is available as buying power.'.format(account.buying_power))

ticker = yf.Ticker("SPY")
df = ticker.history(interval='1d', start=(pd.Timestamp.now(tz='UTC') - timedelta(weeks=260)))

df.to_csv("SPY.csv")

stream = TradingStream(PUBLIC_KEY, SECRET_KEY)

async def on_trade_update(data):
    print("EVENT:", data.event)
    print("ORDER ID:", data.order.id)
    print("SYMBOL:", data.order.symbol)
    print("STATUS:", data.order.status)
    print("FILLED_QTY:", data.order.filled_qty)
    print("AVG_PRICE:", data.order.filled_avg_price)

stream.subscribe_trade_updates(on_trade_update)

stream.run()
