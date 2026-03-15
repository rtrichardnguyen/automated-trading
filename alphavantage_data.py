# alphavantage_data.py

import datetime, os, requests

import numpy as numpy
import pandas as pd

from event import MarkketEvent
from data import DataHandler

class AlphaVantageDataHandler(DataHandler):

    BASE_URL = 'https://www.alphavantage.co/query?'

    def __init__(self, events, symbol_list, api_key):

        self.events = events
        self.symbol_list = symbol_list

        self.symbol_data = {}
        self.latest_symbol_data = {}
        self.continue_backtest = True

        self.api_key = api_key
        self._initialize_connection(self.api_key)

    def _initialize_connection(self, api_key):

        
