from dotenv import load_dotenv
from datetime import datetime, timedelta
from queue import Queue
import os

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.stream import TradingStream

import yfinance as yf
import pandas as pd

from event import OrderEvent
from alpaca_execution import AlpacaExecutionHandler

load_dotenv()

PUBLIC_KEY = os.getenv('PUBLIC_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
'''
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

'''
event_queue = Queue()
anf_order = OrderEvent('ANF', 'MKT', 1, 'LONG')
execution_handler = AlpacaExecutionHandler(event_queue, PUBLIC_KEY, SECRET_KEY)
execution_handler.open_connection()
execution_handler.execute_order(anf_order)
print(event_queue.queue)
execution_handler.close_connection()
