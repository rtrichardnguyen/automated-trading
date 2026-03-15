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

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self.public_key = public_key
        self.secret_key = secret_key

        self.message_queue = queue.Queue()
        self._setup()
        self._start_connection(self.public_key, self.secret_key)

    def _setup(self):
        for s in self.symbol_list:
            self.latest_symbol_data[s] = []

    def _start_connection(self, public_key, secret_key):
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target = loop.run_until_complete,
            args=(self._connect(public_key, secret_key),),
            daemon=True
        )
        thread.start()

    async def _connect(self, public_key, secret_key):

        async with websockets.connect(self.URI) as ws:

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

        if not self.message_queue.empty():

            message = self.message_queue.get()

            new_bar = {
                'datetime' : message['t'],
                'open': message['o'],
                'high' : message['h'],
                'low' : message['l'],
                'close' : message['c'],
                'volume' : message['v']
            }

            self.latest_symbol_data[message['S']].append(new_bar)
            self.events.put(MarketEvent())
