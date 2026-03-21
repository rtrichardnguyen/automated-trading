# event.py

VALID_SIGNAL_TYPES = {'LONG', 'SHORT', 'EXIT'}
VALID_ORDER_DIRECTIONS = {'BUY', 'SELL'}
VALID_FILL_DIRECTIONS = {'BUY', 'SELL'}

class Event(object):
    
    """
    Event is base class providing an interface for all subsequent
    (inherited) events, that will trigger further events in the
    trading infrastructure.
    """

    pass


class MarketEvent(Event):
    
    """
    Handles the event of receiving a new market update with
    corresponding bars.
    """

    def __init__(self):
        self.type = 'MARKET'



class SignalEvent(Event):
    
    """
    Initialises the SignalEvent.

    Parameters:

    strategy_id - The unique identifier for the strategy that generated the signal.
    symbol - The ticker symbol, e.g. ’GOOG’.
    datetime - The timestamp at which the signal was generated.
    signal_type - 'LONG', 'SHORT', or 'EXIT'.
    strength - An adjustment factor "suggestion" used to scale quantity at the portfolio level. Useful for pairs strategies.

    """

    def __init__(self, strategy_id, symbol, datetime, signal_type, strength):

        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = self._check_signal_type(signal_type)
        self.strength = strength

    def _check_signal_type(self, signal_type):

        if signal_type not in VALID_SIGNAL_TYPES:
            raise ValueError(
                f"Signal event type must be one of {sorted(VALID_SIGNAL_TYPES)}"
            )

        return signal_type


class OrderEvent(Event):

    """
    Handles the event of sending an Order to an execution system.
    The order contains a symbol (e.g. GOOG), a type (market or limit),
    quantity and a direction. 
    """
        
    def __init__(self, symbol, order_type, quantity, direction):

        """
        Initialises the order type, setting whether it is
        a Market order (’MKT’) or Limit order (’LMT’), has
        a quantity (integral) and its direction (’BUY’ or
        ’SELL’).

        Parameters:
        symbol - The instrument to trade.
        order_type - ’MKT’ or ’LMT’ for Market or Limit.
        quantity - Non-negative integer for quantity.
        direction - ’BUY’ or ’SELL’ for long or short.

        """

        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = self._check_set_quantity_positive(quantity)
        self.direction = self._check_direction(direction)


    def _check_set_quantity_positive(self, quantity):

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Order event quantity is not a positive integer")

        return quantity

    def _check_direction(self, direction):

        if direction not in VALID_ORDER_DIRECTIONS:
            raise ValueError(
                f"Order event direction must be one of {sorted(VALID_ORDER_DIRECTIONS)}"
            )

        return direction

    def print_order(self):

        print(f"Order: Symbol={self.symbol}, Type={self.order_type}, Quantity={self.quantity}, Direction={self.direction}")


class FillEvent(Event):

    """
    Encapsulates the notion of a Filled Order, as returned
    from a brokerage. Stores the quantity of an instrument
    actually filled and at what price. In addition, stores
    the commission of the trade from the brokerage.
    """

    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost, commission=None):

        """

        Initialises the FillEvent object. Sets the symbol, exchange,
        quantity, direction, cost of fill and an optional
        commission.

        If commission is not provided, the Fill object will
        calculate it based on the trade size and Interactive
        Brokers fees.

        Parameters:
        timeindex - The bar-resolution when the order was filled.
        symbol - The instrument which was filled.
        exchange - The exchange where the order was filled.
        quantity - The filled quantity.
        direction - The direction of fill (’BUY’ or ’SELL’)
        fill_cost - The holdings value in dollars.
        commission - An optional commission sent from IB.

        """

        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = self._check_direction(direction)
        self.fill_cost = fill_cost

        if commission is None:
            self.commission = self._calculate_commission()
        else:
            self.commission = commission


    def _calculate_commission(self):
        # Generate Commision from broker
        # TODO
        return 0

    def _check_direction(self, direction):

        if direction not in VALID_FILL_DIRECTIONS:
            raise ValueError(
                f"Fill event direction must be one of {sorted(VALID_FILL_DIRECTIONS)}"
            )

        return direction
