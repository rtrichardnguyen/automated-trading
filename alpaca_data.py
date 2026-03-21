import datetime, json
import numpy as np
import pandas as pd
import queue
import threading

from event import MarketEvent
from data import DataHandler

import websockets
import asyncio

class AlpacaDataHandler(DataHandler):

    URI = 'wss://stream.data.alpaca.markets/'

    def __init__(self, events, symbol_list, api_version, exchange, public_key, secret_key):

        self.events = events
        self.symbol_list = symbol_list

        self.latest_symbol_data = {}

        self.public_key = public_key
        self.secret_key = secret_key
        self.api_version = api_version
        self.exchange = exchange

        self.message_queue = queue.Queue()
        self._setup()
        self._start_connection(self.public_key, self.secret_key, self.api_version, self.exchange)

    def _setup(self):
        for s in self.symbol_list:
            self.latest_symbol_data[s] = []

    def _start_connection(self, public_key, secret_key, api_version, exchange):
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target = loop.run_until_complete,
            args=(self._connect(public_key, secret_key, api_version, exchange),),
            daemon=True
        )
        thread.start()

    async def _connect(self, public_key, secret_key, api_version, exchange):

        async with websockets.connect(f'{self.URI}/{api_version}/{exchange}') as ws:

            await ws.send(json.dumps({
                'action': 'auth',
                'key': public_key,
                'secret': secret_key
            }))

            await ws.send(json.dumps({
                'action': 'subscribe',
                'bars' : self.symbol_list
            }))

            while True:
                messages = json.loads(await ws.recv())

                for message in messages:
                    if message['T'] == 'b':
                        self.message_queue.put(message)

    def get_latest_bar(self, symbol):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol not available in data set")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol not available in data set")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol not available in data set")
            raise
        else:
            return bars_list[-1][0]

    def get_latest_bar_value(self, symbol, val_type):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol not available in data set")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)

    def get_latest_bar_values(self, symbol, val_type, N=1):
        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("Symbol not available in data set")
            raise
        else:
            return np.array([getattr(b[1], val_type) for b in bars_list[-N:]])

    def update_bars(self):

        while not self.message_queue.empty():

            message = self.message_queue.get()
            bar = self.latest_symbol_data[message['S']]
            previous_close = getattr(bar[-1][1], 'close') if bar else np.nan
            returns = (message['c'] - previous_close) / previous_close if previous_close and previous_close != 0.0 else np.nan

            new_bar = (
                message['t'],
                pd.Series({
                    'open': message['o'],
                    'high' : message['h'],
                    'low' : message['l'],
                    'close' : message['c'],
                    'volume' : message['v'],
                    'returns' : returns
                })
            )

            self.latest_symbol_data[message['S']].append(new_bar)
            self.events.put(MarketEvent())
