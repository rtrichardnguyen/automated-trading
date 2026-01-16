from dotenv import load_dotenv
import os

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest

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