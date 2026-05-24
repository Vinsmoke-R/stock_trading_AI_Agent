from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from indicators import add_indicators
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
import yfinance as yf
import pandas as pd
from langchain_core.messages import AnyMessage
from sentiment import sentiment
from news_api import news_fetch
from sentiment import classifier

from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # current and reliable
    temperature=0,
    max_tokens = 500,
)

# graph class
class TradingState(TypedDict):
    name : str # share name (TSLA,MSFT,AAPL)
    market_data: dict[str, list[float]] # recent price history (close,high,low,open,vol)
    indicators : dict[str,list[float]]  # ema, rsi, vwap, atr
    position : int # holds no of share
    signal : str # buy / hold / sell
    risk : float # 0.2-> safe , 0.8->risky
    balance : float # hold profit / loss 
    messages: list[AnyMessage]
    headlines : list
    sentiment : list

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
def get_data(state:TradingState):
    data = yf.download(
        tickers = state["name"],
        period="1y",
        interval="1d",
        progress=False
    )

    if data.empty:
        return {}
    
    # flatten the nested columns
    data.columns = data.columns.droplevel(1)
    market_data = data

    return{
        "market_data":{
            "close" : market_data['Close'].tolist(),
            "high" : market_data['High'].tolist(),
            "low" : market_data['Low'].tolist(),
            "open" : market_data['Open'].tolist(),
            "volume" : market_data['Volume'].tolist()
        }
    }

def get_indicators(state:TradingState):
    md = state["market_data"]

    df = pd.DataFrame({
        "Open": md["open"],
        "High": md["high"],
        "Low": md["low"],
        "Close": md["close"],
        "Volume" : md['volume']
    })
    data = add_indicators(df)   # function used of another file

    return {
        "indicators": {
            "ema" : data['EMA_20'].tolist(),
            "rsi" : data['RSI_14'].tolist(),
            "vwap" :data['VWAP'].tolist(),
            "atr" : data['ATR'].tolist()
        }
    }

def get_news(state: TradingState):
    name = state['name']

    headlines = news_fetch(name)
    return {"headlines":headlines}   # only return the changed data 


def get_sentiment(state: TradingState):
    headlines = state["headlines"]

    sentiment_result = sentiment(classifier,headlines)
    return {"sentiment":sentiment_result}     # only return the changed data 

import json

def trading_model(state: TradingState):
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], ToolMessage):
        try:
            tool_result = json.loads(messages[-1].content)
            return {
                "balance": tool_result.get("balance", state["balance"]),
                "position": tool_result.get("position", state["position"])
            }
        except (json.JSONDecodeError, TypeError):
            pass
    indicators = state["indicators"]
    market_data = state["market_data"]
    position = state.get("position", 0)
    balance = state.get("balance", 10000.0)
    sentiment_data = state.get("sentiment",[])
    risk = state.get("risk", 0.5)
    # Get the most recent values
    latest = {k: v[-1] for k, v in indicators.items() if v}
    current_price = market_data["close"][-1]

    prompt = f"""
        You are a stock trading agent. You have ONLY two tools available:
        1. "buy"  - call this to purchase a stock
        2. "sell" - call this to sell a stock

        DO NOT call any other tool. DO NOT call "check_signal" or any other function.
        If the decision is HOLD, do not call any tool at all.

        Current Price: {current_price:.2f}
        Position (shares held): {position}
        Balance: {balance:.2f}
        Sentiment: {sentiment_data}
        Risk Tolerance: {risk}

        Latest Indicators:
        - EMA_20: {latest.get('ema', 'N/A')}
        - RSI_14: {latest.get('rsi', 'N/A')}  (>70 overbought, <30 oversold)
        - VWAP:   {latest.get('vwap', 'N/A')}
        - ATR:    {latest.get('atr', 'N/A')}

        Rules:
        - RSI < 30 and price < VWAP → BUY
        - RSI > 70 and price > VWAP → SELL
        - Otherwise → HOLD, call no tool
        - Only buy if balance >= current price
        - Only sell if position >= 1
        - Only buy if sentiment is positive 
        - Only sell if sentiment is negative 
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


graph = StateGraph(TradingState)
# graph nodes 
graph.add_node("get_data",get_data)
graph.add_node("get_indicators",get_indicators)
graph.add_node("get_news",get_news)
graph.add_node("get_sentiment",get_sentiment)
graph.add_node("trading_model",trading_model)
graph.add_node("tools",tool_node) # (name,tool)

# graph edges 
graph.add_edge(START,"get_data")
graph.add_edge(START,"get_news")
graph.add_edge("get_data","get_indicators")
graph.add_edge("get_news","get_sentiment")
graph.add_edge("get_sentiment","trading_model")
graph.add_edge("get_indicators","trading_model")
graph.add_conditional_edges("trading_model",tools_condition)
graph.add_edge("tools","trading_model")         # going back to trading model

stock_bot = graph.compile()