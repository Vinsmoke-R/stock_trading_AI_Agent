# AI STOCK TRADING AGENT

A multi-agent stock trading system that autonomously makes 
BUY / SELL / HOLD decisions using LLM reasoning + technical 
indicators + real-time news sentiment.



## Dashboard

<p align="center">
  <img src="Screenshot1.png" alt="Dashboard" width="800"/>
</p>

## Charts

<p align="center">
  <img src="Screenshot2.png" alt="Signals" width="800"/>
</p>


<p align="center">
  <img src="Screenshot3.png" alt="Charts" width="800"/>
</p>


## How it works
- **get_data** — fetches 1 year of OHLCV price data from Yahoo Finance
- **get_indicators** — computes RSI, EMA, VWAP, ATR
- **get_news** — fetches latest financial headlines
- **get_sentiment** — LLM scores news sentiment
- **trading_model** — Llama 3.3 70B reasons over all signals and decides to buy/sell/hold stock

## Tech Stack
- LangGraph — agent orchestration
- LangChain + Groq — LLM inference
- yfinance — market data
- feedparser — news data 
- Streamlit + Plotly — dashboard