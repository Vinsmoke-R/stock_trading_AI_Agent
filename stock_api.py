import os 
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.enums import DataFeed
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from alpaca.data.requests import StockLatestTradeRequest
from indicators import add_indicators
from alpaca.common.exceptions import APIError

load_dotenv()
# paper=True enables paper trading
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

stock_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
# trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

# account = trading_client.get_account()
# # print(account)
# print(trading_client.get_all_positions())

def get_live_price(ticker):
    # invalid ticker check
    if not ticker or not ticker.isalpha():
        return {"error": f"Invalid ticker: {ticker}"}
    
    try:
        request = StockLatestTradeRequest(symbol_or_symbols=[ticker])
        latest_trade = stock_client.get_stock_latest_trade(request)
        trade = latest_trade[ticker]
        return {
            "price": trade.price,
            "timestamp": trade.timestamp,
        }
    
    # invalid ticker (Alpaca doesn't recognize it)
    except KeyError:
        return {"error": f"Ticker {ticker} not found"}
    
    # market closed — no recent trade available
    except APIError as e:
        if "forbidden" in str(e).lower() or "not found" in str(e).lower():
            return {"error": "Market may be closed or ticker unavailable"}
        return {"error": f"API error: {str(e)}"}
    
    # catch everything else
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# print(get_live_price("AAPL"))
# print(get_live_price("XXXyayu"))