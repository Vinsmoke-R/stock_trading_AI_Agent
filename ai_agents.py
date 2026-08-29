from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from indicators import add_indicators
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
import yfinance as yf
import pandas as pd
from langchain_core.messages import AnyMessage
from sentiment import sentiment
from news_api import news_fetch
from sentiment import classifier
from stock_api import get_live_price
from langgraph.graph.message import add_messages
from typing import Annotated

from dotenv import load_dotenv

# ----------------------------------------------------------------------------

from test import get_account, get_clock, get_all_positions, get_historical_bars, get_latest_quote, get_orders
from test import submit_buy, submit_sell, start_stream
from test import cancel_order

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trading_bot.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("trading_bot")

# ----------------------------------------------------------------------------
load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",  # current and reliable
    temperature=0,
    max_tokens = 500,
)

# graph class
class TradingState(TypedDict):
    user_name : str # name of the stock holder
    symbol : str # name of the Stock
    market_data: dict[str, dict[str, list[float]]] # recent price history (close,high,low,open,vol)
    indicators: dict[str, dict[str, list[float]]]  # ema, rsi, vwap, atr
    position : dict[str,int] # hold total no of stocks 
    signal : str # buy / hold / sell
    risk : float # 0.2-> safe , 0.8->risky
    balance : float # hold profit / loss 
    messages: Annotated[list[AnyMessage], add_messages]
    headlines : dict[str, list[str]]
    sentiment : dict[str, list[float]]
    live_price : dict[str, float]  # from alpaca

@tool 
def buy(state : TradingState):
    """Execute a buy trade: decrease balance and increase position."""

    symbol = state["symbol"]
    balance = state["balance"]
    position = state.get("position", {}).get(symbol, 0)
    live_price = state.get("live_price", {}).get(symbol, 0)

    qty = 1

    total_cost = qty*live_price

    if balance < total_cost:
            logger.warning(f"BUY FAILED for {symbol} - Not enough balance. Have: ${balance:.2f}, Need: ${total_cost:.2f}")
            return {
                "success": False,
                "error": "Not enough balance"
            }

    order = submit_buy(symbol,qty)
    logger.info(f"BUY EXECUTED - {symbol} x{qty} @ ${live_price:.2f} | Order ID: {getattr(order, 'id', 'N/A')}")

    new_balance = balance - total_cost
    new_position = position + 1

    logger.info(f"Updated state - Balance: ${new_balance:.2f}, Position: {new_position}")

    return {
        "balance" : new_balance,
        "position" : {symbol: new_position},
        "signal" : "buy"
    }

@tool
def sell(state : TradingState):
    """Execute a sell trade: increase balance and decrease position."""

    symbol = state["symbol"]
    balance = state["balance"]
    position = state.get("position", {}).get(symbol, 0)
    live_price = state.get("live_price", {}).get(symbol, 0)

    qty = 1
    total_cost = qty*live_price

    if position < qty:
        logger.warning(f"Sell failed for {symbol} - Not enough shares. Have: {position}, Need: {qty}")
        return {
            "success":False,
            "error": "Not enough shares"
        }
    
    order = submit_sell(symbol,qty)
    logger.info(f"SELL EXECUTED - {symbol} x{qty} @ ${live_price:.2f} | Order ID: {getattr(order, 'id', 'N/A')}")

    new_balance = balance + total_cost
    new_position = position - 1

    logger.info(f"Updated state - Balance: ${new_balance:.2f}, Position: {new_position}")

    return{
        "balance" : new_balance,
        "position" : {symbol:new_position},
        "signal" : "sell"
    }


tools = [buy,sell] # dont use "buy" like this  -> use like this - tool
llm_with_tools = llm.bind_tools(tools)

# graph functions 
def get_live_price_node(state: TradingState):
    symbol = state["symbol"]
    result = get_latest_quote(symbol)
    if "error" in result:
        fallback_price = state["market_data"][symbol]["close"][-1]
        logger.warning(f"Live quote error for {symbol}, falling back to last close: ${fallback_price:.2f}")
        return {"live_price": {symbol : fallback_price}}  # fallback
    
    logger.info(f"Live price for {symbol}: ${result.ask_price:.2f}")
    return {"live_price": {symbol : result.ask_price}}

def get_data(state:TradingState):
    symbol = state["symbol"]
    data = get_historical_bars(symbol)
    logger.info(f"Fetched {len(data)} historical bars for {symbol}")
    return{
        "market_data":{
            symbol:{
                "close" : data['close'].tolist(),
                "high" : data['high'].tolist(),
                "low" : data['low'].tolist(),
                "open" : data['open'].tolist(),
                "volume" : data['volume'].tolist()
            }
        }
    }

def get_indicators(state:TradingState):
    symbol = state["symbol"]
    md = state["market_data"]

    df = pd.DataFrame({
        "Open": md[symbol]["open"],
        "High": md[symbol]["high"],
        "Low": md[symbol]["low"],
        "Close": md[symbol]["close"],
        "Volume" : md[symbol]['volume']
    })
    data = add_indicators(df)   # function used of another file

    logger.info(f"Computed indicators for {symbol} - EMA/RSI/VWAP/ATR ready")

    return {
        "indicators":{
            symbol:{
                "ema" : data['EMA_20'].tolist(),
                "rsi" : data['RSI_14'].tolist(),
                "vwap" :data['VWAP'].tolist(),
                "atr" : data['ATR'].tolist()
            }
        }
    }

def get_news(state: TradingState):
    symbol = state['symbol']

    headlines = news_fetch(symbol)
    logger.info(f"Fetched {len(headlines)} headlines for {symbol}")
    return {"headlines":{symbol:headlines}}   # only return the changed data 


def get_sentiment(state: TradingState):
    symbol = state["symbol"]
    headlines = state["headlines"]

    sentiment_result = sentiment(classifier,headlines[symbol])
    logger.info(f"Sentiment for {symbol}: {sentiment_result}")
    return {"sentiment":{symbol:sentiment_result}}     # only return the changed data 

import json

def trading_model(state: TradingState):
    messages = state.get("messages", [])
    
    # check if tool was already executed — stop if so
    if len(messages) >= 3:  # has at least one full tool cycle
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
        if tool_messages:
            last_tool = tool_messages[-1]
            try:
                tool_result = json.loads(last_tool.content)
                logger.info(f"Trade cycle complete - Balance: {tool_result.get('balance', state['balance'])}, Position: {tool_result.get('position', state['position'])}")
                return {
                    "balance": tool_result.get("balance", state["balance"]),
                    "position": tool_result.get("position", state["position"]),
                    "messages": [AIMessage(content="Trade done.")],
                    "signal": state.get("signal", "hold"),
                }
            except (json.JSONDecodeError, TypeError):
                pass
    symbol = state["symbol"]
    # if symbol not in state.get("indicators", {}):
    #     return {"signal": "hold", "messages": []}

    indicators = state["indicators"][symbol]
    market_data = state["market_data"][symbol]
    position = state.get("position", {}).get(symbol, 0)
    balance = state.get("balance", 10000.0)
    sentiment_data = state.get("sentiment", {}).get(symbol, [])
    risk = state.get("risk", 0.5)
    # Get the most recent values
    latest = {k: v[-1] for k, v in indicators.items() if v}
    live_price = state.get("live_price", {}).get(symbol, market_data["close"][-1])

    logger.info(f"Running trading model for {symbol} | Price: ${live_price:.2f} | Balance: ${balance:.2f} | Position: {position}")

    prompt = f"""
        You are a professional stock trading agent. You have ONLY two tools available:
        1. "buy"  - call this to purchase a stock
        2. "sell" - call this to sell a stock

        DO NOT call any other tool. DO NOT call "check_signal" or any other function.
        If the decision is HOLD, do not call any tool at all.

        Symbol : {symbol}
        Live Price: {live_price:.2f}
        Position (shares held): {position}
        Balance: {balance:.2f}
        Sentiment: {sentiment_data}
        Risk Tolerance: {risk}

        Latest Indicators:
        - EMA_20: {latest.get('ema', 'N/A')}
        - RSI_14: {latest.get('rsi', 'N/A')} 
        - VWAP:   {latest.get('vwap', 'N/A')}
        - ATR:    {latest.get('atr', 'N/A')}
        """

    messages = [{"role": "user", "content": prompt}]
    response = llm_with_tools.invoke(messages)

    # Determine signal for state tracking
    signal = "hold"
    if response.tool_calls:
        signal = response.tool_calls[0]["name"]  # "buy" or "sell"

    logger.info(f"DECISION for {symbol}: {signal.upper()}")

    return {
        "messages": messages + [response],
        "signal": signal,
    }

def join_data(state: TradingState):
    """Node that waits for both sentiment and indicators to complete"""
    return {}

tool_node = ToolNode(tools)

def should_continue(state: TradingState):
    messages = state.get("messages", [])
    if not messages:
        return "end"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"

graph = StateGraph(TradingState)
# graph nodes 
graph.add_node("get_data",get_data)
graph.add_node("get_live_price", get_live_price_node)
graph.add_node("get_indicators",get_indicators)
graph.add_node("get_news",get_news)
graph.add_node("get_sentiment",get_sentiment)
graph.add_node("join", join_data)  # NEW JOIN NODE
graph.add_node("trading_model",trading_model)
graph.add_node("tools",tool_node) # (name,tool)

# graph edges 
graph.add_edge(START,"get_data")
graph.add_edge(START,"get_news")
graph.add_edge("get_data", "get_live_price")  
graph.add_edge("get_live_price", "get_indicators")  
graph.add_edge("get_news","get_sentiment")
graph.add_edge("get_sentiment","join")
graph.add_edge("get_indicators","join")
# Join node goes to trading_model (NEW)
graph.add_edge("join", "trading_model")

graph.add_conditional_edges(
    "trading_model",
    should_continue,
    {"tools": "tools", "end": END}
)
graph.add_edge("tools","trading_model")         # going back to trading model

stock_bot = graph.compile()
print(stock_bot.get_graph().draw_ascii())



initial_state = {
    "user_name": "Lucy",
    "symbol": "AAPL",
    "market_data": {},
    "indicators": {},
    "position": {},
    "signal": "hold",
    "risk": 0.5,
    "balance": 10000.0,
    "messages": [],
    "headlines": {},
    "sentiment": {},
    "live_price": {},
}

logger.info("========== TRADING BOT STARTING ==========")
result = stock_bot.invoke(initial_state)
logger.info("========== TRADING BOT FINISHED ==========")