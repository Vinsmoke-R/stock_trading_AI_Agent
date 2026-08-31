import os
import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv

# Alpaca Trading
from alpaca.trading.client import TradingClient
from alpaca.data.enums import DataFeed
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderClass,
)

# Alpaca Historical Data
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame

# Alpaca Live Data
from alpaca.data.live import StockDataStream


# ============================================================
# 1. LOAD API KEYS
# ============================================================

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    raise RuntimeError(
        "Missing APCA_API_KEY_ID or APCA_API_SECRET_KEY.\n"
        "Put your Alpaca Paper Trading keys in .env"
    )


# ============================================================
# CLIENTS
# ============================================================

trading_client = TradingClient(
    api_key=API_KEY,
    secret_key=SECRET_KEY,
    paper=True
)

data_client = StockHistoricalDataClient(
    api_key=API_KEY,
    secret_key=SECRET_KEY
)


# ============================================================
# 1. GET ACCOUNT
# ============================================================

def get_account():

    print("\n========== 1. ACCOUNT ==========")

    account = trading_client.get_account()

    print("Account status :", account.status)
    print("Cash           :", account.cash)
    print("Buying power   :", account.buying_power)
    print("Portfolio value:", account.portfolio_value)
    print("Equity         :", account.equity)

    return account


# ============================================================
# 2. GET MARKET CLOCK
# ============================================================

def get_clock():

    print("\n========== 2. MARKET CLOCK ==========")

    clock = trading_client.get_clock()

    print("Market open :", clock.is_open)
    print("Current time:", clock.timestamp)
    print("Next open   :", clock.next_open)
    print("Next close  :", clock.next_close)

    return clock


# ============================================================
# 3. GET ALL POSITIONS
# ============================================================

def get_all_positions():

    print("\n========== 3. POSITIONS ==========")

    positions = trading_client.get_all_positions()

    if not positions:
        print("No open positions.")

    for position in positions:

        print(
            f"{position.symbol} | "
            f"Qty: {position.qty} | "
            f"Avg: {position.avg_entry_price} | "
            f"Current: {position.current_price} | "
            f"P/L: {position.unrealized_pl}"
        )

    return positions


# ============================================================
# 4. GET OPEN ORDERS
# ============================================================

def get_orders():

    print("\n========== 4. OPEN ORDERS ==========")

    orders = trading_client.get_orders()

    if not orders:
        print("No open orders.")

    for order in orders:

        print(
            f"ID: {order.id} | "
            f"{order.symbol} | "
            f"Side: {order.side} | "
            f"Qty: {order.qty} | "
            f"Status: {order.status}"
        )

    return orders


# ============================================================
# 5. HISTORICAL BARS
# ============================================================

def get_historical_bars(symbol:str):

    print("\n========== 5. HISTORICAL BARS ==========")

    symbol = symbol

    end = datetime.now()
    start = end - timedelta(days=30)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        feed=DataFeed.IEX
    )

    bars = data_client.get_stock_bars(request)

    print(f"Historical data for {symbol}:")

    # Convert to dataframe
    df = bars.df

    print(df.tail())

    return df


# ============================================================
# 6. LATEST QUOTE
# ============================================================

def get_latest_quote(symbol:str):

    print("\n========== 6. LATEST QUOTE ==========")

    symbol = symbol

    request = StockLatestQuoteRequest(
        symbol_or_symbols=symbol
    )

    quotes = data_client.get_stock_latest_quote(request)

    quote = quotes[symbol]

    print("Symbol    :", symbol)
    print("Bid price :", quote.bid_price)
    print("Ask price :", quote.ask_price)
    print("Bid size  :", quote.bid_size)
    print("Ask size  :", quote.ask_size)

    return quote


# ============================================================
# 7. SUBMIT BUY
# ============================================================

def submit_buy(symbol : str, qty : int):

    print("\n========== 7. BUY ORDER ==========")

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )

    result = trading_client.submit_order(order)

    print("BUY ORDER SUBMITTED")
    print("Order ID:", result.id)
    print("Symbol  :", result.symbol)
    print("Qty     :", result.qty)
    print("Status  :", result.status)

    return result


# ============================================================
# 8. SUBMIT SELL
# ============================================================

def submit_sell(symbol:str, qty:int):

    print("\n========== 8. SELL ORDER ==========")

    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )

    result = trading_client.submit_order(order)

    print("SELL ORDER SUBMITTED")
    print("Order ID:", result.id)
    print("Symbol  :", result.symbol)
    print("Qty     :", result.qty)
    print("Status  :", result.status)

    return result


# ============================================================
# 9. CANCEL ORDER
# ============================================================

def cancel_order(order_id):

    print("\n========== 9. CANCEL ORDER ==========")

    trading_client.cancel_order_by_id(order_id)

    print("Order cancelled:", order_id)


# ============================================================
# 10. BRACKET ORDER
# ============================================================

def submit_bracket_order():

    print("\n========== 10. BRACKET ORDER ==========")

    symbol = "AAPL"

    order = MarketOrderRequest(

        symbol=symbol,

        qty=1,

        side=OrderSide.BUY,

        time_in_force=TimeInForce.DAY,

        order_class=OrderClass.BRACKET,

        take_profit=TakeProfitRequest(
            limit_price=300
        ),

        stop_loss=StopLossRequest(
            stop_price=200
        )
    )

    result = trading_client.submit_order(order)

    print("BRACKET ORDER SUBMITTED")
    print("Order ID:", result.id)
    print("Take profit: $300")
    print("Stop loss  : $200")

    return result


# ============================================================
# 11. LIVE STREAMING
# ============================================================

async def stream_handler(data):

    print("\n========== LIVE DATA ==========")

    print("Symbol:", data.symbol)
    print("Price :", data.price)
    print("Size  :", data.size)


def start_stream(symbol:str):

    print("\n========== 11. LIVE STREAM ==========")

    stream = StockDataStream(
        API_KEY,
        SECRET_KEY
    )

    stream.subscribe_trades(
        stream_handler,
        symbol
    )

    print("Listening for AAPL trades...")
    print("Press CTRL+C to stop.")

    stream.run()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("\n")
    print("======================================")
    print("       ALPACA API TEST PROGRAM        ")
    print("======================================")

    # --------------------------------------------------------
    # SAFE TESTS
    # These DO NOT place trades.
    # --------------------------------------------------------

    get_account()

    get_clock()

    get_all_positions()

    get_orders()

    get_historical_bars("AAPL")

    get_latest_quote("AAPL")


    # --------------------------------------------------------
    # TRADING TESTS
    #
    # UNCOMMENT ONLY WHEN YOU WANT TO
    # ACTUALLY PLACE PAPER TRADES.
    # --------------------------------------------------------

    # buy_order = submit_buy()

    # sell_order = submit_sell()

    # cancel_order(buy_order.id)

    # bracket_order = submit_bracket_order()


    # --------------------------------------------------------
    # LIVE STREAM
    #
    # UNCOMMENT TO START LIVE DATA.
    # CTRL+C TO STOP.
    # --------------------------------------------------------

    # start_stream()