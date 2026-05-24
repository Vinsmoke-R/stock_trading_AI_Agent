import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Live Stock Dashboard", layout="wide")

st.title("📈 Live Stock Viewer")

# USER INPUT (ANY TICKER)
ticker = st.text_input(
    "Enter stock ticker (e.g. AAPL, TSLA, MSFT)",
    value="AAPL"
).upper().strip()

period = st.selectbox(
    "What period do you want",
    ("1y","5y","max")
)

interval = st.selectbox(
    "What range do you want",
    ("1d")
)

if ticker:
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False
        )

        if data.empty:
            st.error("❌ Invalid ticker or no data available.")
        else:
            # Timezone handling
            if data.index.tz is None:
                data.index = data.index.tz_localize("UTC")
            data.index = data.index.tz_convert("Asia/Kolkata")

            st.subheader(f"📊 {ticker} Price Data")
            st.dataframe(data.tail(20))

            st.subheader("📉 Close Price")
            st.line_chart(data["Close"])

    except Exception as e:
        st.error(f"Error fetching data: {e}")
