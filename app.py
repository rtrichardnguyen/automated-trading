from dotenv import load_dotenv
from datetime import datetime, timedelta
import os, pandas, time

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()

PUBLIC_KEY = os.getenv('PUBLIC_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')

trading_client = TradingClient(PUBLIC_KEY, SECRET_KEY)
account = trading_client.get_account()

# Market Data Client
md_client = CryptoHistoricalDataClient()


while(1):

    request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=TimeFrame.Minute, #TODO: Switch Time horizon
    start=datetime.now() - timedelta(days=200),
    end=datetime.now()
    )

    btc_bars = md_client.get_crypto_bars(request_params)
    btc_bars = btc_bars.df
    long_ma = btc_bars["close"].mean()

    request_params = CryptoBarsRequest(
    symbol_or_symbols=["BTC/USD"],
    timeframe=TimeFrame.Minute, #TODO: Switch Time horizon
    start=datetime.now() - timedelta(days=50),
    end=datetime.now()
    )

    btc_bars = md_client.get_crypto_bars(request_params)
    btc_bars = btc_bars.df
    short_ma = btc_bars["close"].mean()

    if short_ma > long_ma:
        print('BUY')
    elif short_ma < long_ma:
        print('SELL')

    print(f'200 DAY MOVING AVERAGE: {long_ma}')
    print(f'50 DAY MOVING AVERAGE: {short_ma}')

    #time.sleep(60)
    print(btc_bars)
    break