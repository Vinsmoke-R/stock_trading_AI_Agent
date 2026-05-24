from indicators import add_indicators
import yfinance as yf
import streamlit as st

ticker = st.text_input(
    "Enter stock ticker (e.g. AAPL, MSFT, TSLA)",
    value="AAPL"  # default value is AAPL
).upper().strip()

if ticker:
    data = yf.download(
        ticker,
        period="1y",
        interval="1d",
        progress=False
    )

    if data.empty:
        st.error(" Invalid ticker or no data available.")
    else:
        data = add_indicators(data)
        st.dataframe(data)