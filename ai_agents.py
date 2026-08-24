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

# -------------------------------------------------------------------------------------------------------------------------------

from test import get_account, get_clock, get_all_positions, get_historical_bars, get_latest_quote, get_orders
from test import submit_buy, submit_sell, start_stream
from test import cancel_order

# -------------------------------------------------------------------------------------------------------------------------------

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
def buy(balance:float, stock_price:float, position:int):
    """Execute a buy trade: decrease balance and increase position."""

    if balance<stock_price:
        return {
            "error":"Not enough balance",
            "balance":balance,
            "position":position
        }
    else:
        balance -= stock_price
        position += 1

        return {
            "balance":balance,
            "position":position
        }

@tool
def sell(balance:float, stock_price:float, position:int):
    """Execute a sell trade: increase balance and decrease position."""

    if position<1:
        return{
            "error":"Not Enough Stocks",
            "balance":balance,
            "position":position
        }
    else:
        balance += stock_price
        position -= 1

        return {
            "balance":balance,
            "position":position
        }

tools = [buy,sell] # dont use "buy" like this  -> use like this - tool
llm_with_tools = llm.bind_tools(tools)

# graph functions 
def get_live_price_node(state: TradingState):
    symbol = state["symbol"]
    result = get_latest_quote(symbol)
    if "error" in result:
        return {"live_price": {symbol : state["market_data"][symbol]["close"][-1]}}  # fallback
    return {"live_price": {symbol : result["price"]}}

def get_data(state:TradingState):
    symbol = state["symbol"]
    data = get_historical_bars(symbol)
    # flatten the nested columns
    data.columns = data.columns.droplevel(1)
    
    return{
        "market_data":{
            symbol:{
                "close" : data[symbol]['close'].tolist(),
                "high" : data[symbol]['high'].tolist(),
                "low" : data[symbol]['low'].tolist(),
                "open" : data[symbol]['open'].tolist(),
                "volume" : data[symbol]['volume'].tolist()
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
    return {"headlines":{symbol:headlines}}   # only return the changed data 


def get_sentiment(state: TradingState):
    symbol = state["symbol"]
    headlines = state["headlines"]

    sentiment_result = sentiment(classifier,headlines[symbol])
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
                return {
                    "balance": tool_result.get("balance", state["balance"]),
                    "position": tool_result.get("position", state["position"]),
                    "messages": [AIMessage(content="Trade done.")],
                    "signal": state.get("signal", "hold"),
                }
            except (json.JSONDecodeError, TypeError):
                pass
    symbol = state["symbol"]
    indicators = state["indicators"][symbol]
    market_data = state["market_data"][symbol]
    position = state.get("position", {}).get(symbol, 0)
    balance = state.get("balance", 10000.0)
    sentiment_data = state.get("sentiment", {}).get(symbol, [])
    risk = state.get("risk", 0.5)
    # Get the most recent values
    latest = {k: v[-1] for k, v in indicators.items() if v}
    live_price = state.get("live_price", {}).get(symbol, market_data["close"][-1])

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

    return {
        "messages": messages + [response],
        "signal": signal,
    }

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
graph.add_node("trading_model",trading_model)
graph.add_node("tools",tool_node) # (name,tool)

# graph edges 
graph.add_edge(START,"get_data")
graph.add_edge(START,"get_news")
graph.add_edge("get_data", "get_live_price")  
graph.add_edge("get_live_price", "get_indicators")  
graph.add_edge("get_news","get_sentiment")
graph.add_edge("get_sentiment","trading_model")
graph.add_edge("get_indicators","trading_model")
graph.add_conditional_edges(
    "trading_model",
    should_continue,
    {"tools": "tools", "end": END}
)
graph.add_edge("tools","trading_model")         # going back to trading model

stock_bot = graph.compile()
# print(stock_bot.get_graph().draw_ascii())



initial_state = {
    "user_name": "trader_john",
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

result = stock_bot.invoke(initial_state)