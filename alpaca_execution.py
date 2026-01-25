# alpaca_execution.py

import datetime
import time
import uuid

from event import FillEvent, OrderEvent
from execution import ExecutionHandler

from alpaca.trading.client import TradingClient
from alpaca.trading.stream import TradingStream
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce


class AlpacaExecutionHandler(ExecutionHandler):

        def __init__(self, events, public_key, secret_key):

            self.events = events
            self.fill_dict = {}
            self.order_id = uuid.UUID(int=0)

            self.trading_client = TradingClient(public_key, secret_key, paper=True)

            self.trading_stream = TradingStream(public_key, secret_key, paper=True)
            self.trading_stream.subscribe_trade_updates(self._on_trade_update)
            self.trading_stream.run()


        def execute_order(self, event, is_paper):

            if event.type == 'ORDER':

                symbol = event.symbol
                qty = event.quantity

                side = None
            if event.direction == 'LONG':
                side = OrderSide.BUY
            elif event.direction == 'SHORT':
                side = OrderSide.SELL
            else:
                raise Exeception("Order side value invalid.")

               order_type = event.order_type 

            order = self.create_order(symbol, qty, side, order_type)

            submitted_order = self.trading_client.submit_order(order_data=order)
            time.sleep(1)
            self.order_id = submitted_order.id

            self.create_fill_dict_entry(submitted_order)
            self.create_fill(order)


        async def _on_trade_update(self, data):

            if (
                data.event == 'NEW' and  
                data.order.id == self.order_id and
                data.order.id not in self.fill_dict
            ):

                self.create_fill_dict_entry()

            if (
                data.event == 'FILL' and
                self.fill_dict[data.order.id]['filled'] == False:
            ):

                self.create_fill()

        def create_fill_dict_entry(self, trade_update):

            self.fill_dict[trade_update.order.id] = {
                'symbol': trade_update.order.symbol,
                # TODO: Figure out if exchange is necessary
                'direction': 'LONG' if trade_update.order.id == OrderSide.BUY else 'SHORT'
                'filled': False
            }

        def create_fill(self, order):
            pass


        def _error_handler(self, msg):

            print(msg)

        def _reply_handler(self, msg):
            pass

        def create_order(self, symbol, qty, side, order_type):

            order_data = None

            if order_type == 'MKT':

                order_data = MarketOrderRequest(
                                symbol=symbol,
                                qty=qty,
                                side=order_side
                                time_in_force=TimeInForce.DAY
                            )  

            elif order_type == 'LMT':

                order_data = LimitOrderRequest(
                                symbol=symbol,
                                qty=qty,
                                side=order_side
                                time_in_force=TimeInForce.DAY
                                limit_price=0 # TODO: Implement Limit Price
                            )

            else:

                raise Exception("Order type for this order has not been implemented yet. Only market and limit orders available")

            return order_data













