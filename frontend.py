import streamlit as st
import plotly.graph_objects as go
import time
import yfinance as yf
from ai_agents import stock_bot

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Agent",
    page_icon="📈",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0a0a0f;
    color: #e0e0e0;
}

h1, h2, h3 { font-family: 'Syne', sans-serif; font-weight: 800; }

.stMetric {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 12px;
}

.stButton > button {
    background: #00ff88;
    color: #0a0a0f;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    border: none;
    border-radius: 6px;
    padding: 10px 28px;
}

.stButton > button:hover {
    background: #00cc6a;
    color: #0a0a0f;
}

.ticker-card {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
}

.signal-buy  { color: #00ff88; font-weight: 700; font-family: 'Space Mono', monospace; }
.signal-sell { color: #ff4d6d; font-weight: 700; font-family: 'Space Mono', monospace; }
.signal-hold { color: #888;    font-weight: 700; font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# ── Tickers ───────────────────────────────────────────────────────────────────
TICKERS = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]

# ── Session state init ────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {
        t: {"balance": 10000.0, "position": 0} for t in TICKERS
    }

if "trade_history" not in st.session_state:
    st.session_state.trade_history = {t: [] for t in TICKERS}

if "last_signals" not in st.session_state:
    st.session_state.last_signals = {t: "hold" for t in TICKERS}

if "market_data_cache" not in st.session_state:
    st.session_state.market_data_cache = {t: [] for t in TICKERS}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📈 AI Trading Agent")
st.markdown("---")

# ── Controls ──────────────────────────────────────────────────────────────────
col_btn, col_auto, col_space = st.columns([1, 1, 4])

with col_btn:
    run_now = st.button("▶ Run Agent Now")

with col_auto:
    auto_refresh = st.toggle("Auto Refresh (5 min)", value=False)

# ── Run agent for all tickers ─────────────────────────────────────────────────
def run_all():
    for ticker in TICKERS:
        saved = st.session_state.portfolio[ticker]
        with st.spinner(f"Analyzing {ticker}..."):
            try:
                result = stock_bot.invoke({
                    "name": ticker,
                    "position": saved["position"],
                    "balance": saved["balance"],
                    "risk": 0.5,
                    "messages": [],
                    "market_data": {},
                    "indicators": {},
                    "signal": ""
                })

                signal = result.get("signal", "hold")
                st.session_state.last_signals[ticker] = signal
                st.session_state.portfolio[ticker]["balance"] = result.get("balance", saved["balance"])
                st.session_state.portfolio[ticker]["position"] = result.get("position", saved["position"])

                # cache closes for chart
                closes = result.get("market_data", {}).get("close", [])
                if closes:
                    st.session_state.market_data_cache[ticker] = closes

                # record trade
                if signal in ["buy", "sell"] and closes:
                    st.session_state.trade_history[ticker].append({
                        "index": len(closes) - 1,
                        "price": closes[-1],
                        "signal": signal,
                        "balance": result.get("balance", saved["balance"])
                    })

            except Exception as e:
                st.error(f"{ticker} error: {e}")

if run_now:
    run_all()

# ── Chart builder ─────────────────────────────────────────────────────────────
def build_chart(ticker, closes, trades):
    fig = go.Figure()

    # price line
    fig.add_trace(go.Scatter(
        y=closes,
        mode="lines",
        name="Price",
        line=dict(color="#4a9eff", width=2)
    ))

    # shade profit/loss regions between consecutive trades
    for i in range(1, len(trades)):
        prev = trades[i - 1]
        curr = trades[i]
        profit = curr["price"] > prev["price"]
        color = "rgba(0,255,136,0.12)" if profit else "rgba(255,77,109,0.12)"
        fig.add_vrect(
            x0=prev["index"], x1=curr["index"],
            fillcolor=color, line_width=0
        )

    # buy/sell markers
    for trade in trades:
        if trade["signal"] == "buy":
            fig.add_trace(go.Scatter(
                x=[trade["index"]], y=[trade["price"]],
                mode="markers+text",
                marker=dict(color="#00ff88", size=14, symbol="triangle-up"),
                text=["BUY"], textposition="top center",
                textfont=dict(color="#00ff88", size=10),
                name=f"BUY @ {trade['price']:.2f}",
                showlegend=False
            ))
        elif trade["signal"] == "sell":
            fig.add_trace(go.Scatter(
                x=[trade["index"]], y=[trade["price"]],
                mode="markers+text",
                marker=dict(color="#ff4d6d", size=14, symbol="triangle-down"),
                text=["SELL"], textposition="bottom center",
                textfont=dict(color="#ff4d6d", size=10),
                name=f"SELL @ {trade['price']:.2f}",
                showlegend=False
            ))

    fig.update_layout(
        title=dict(text=ticker, font=dict(size=18, color="#e0e0e0")),
        paper_bgcolor="#0a0a0f",
        plot_bgcolor="#0a0a0f",
        xaxis=dict(showgrid=False, color="#444"),
        yaxis=dict(showgrid=True, gridcolor="#1e1e2e", color="#444"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=280
    )
    return fig

# ── Dashboard ─────────────────────────────────────────────────────────────────
st.markdown("### Portfolio")

col1, col2, col3, col4, col5 = st.columns(5)
cols = [col1, col2, col3, col4, col5]

for i, ticker in enumerate(TICKERS):
    pf = st.session_state.portfolio[ticker]
    signal = st.session_state.last_signals[ticker]
    pnl = pf["balance"] - 10000.0
    pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
    signal_class = f"signal-{signal}"

    with cols[i]:
        st.markdown(f"""
        <div class="ticker-card">
            <b>{ticker}</b><br>
            <span class="{signal_class}">{signal.upper()}</span><br>
            <small>Balance: ${pf['balance']:,.2f}</small><br>
            <small>Position: {pf['position']} shares</small><br>
            <small>P&L: {pnl_str}</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Charts")

# 2 columns for charts
left, right = st.columns(2)
chart_cols = [left, right]

for i, ticker in enumerate(TICKERS):
    closes = st.session_state.market_data_cache[ticker]
    trades = st.session_state.trade_history[ticker]

    with chart_cols[i % 2]:
        if closes:
            fig = build_chart(ticker, closes, trades)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No data yet for {ticker}. Click 'Run Agent Now'.")

# ── Auto refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    st.caption("⏱ Auto-refreshing every 5 minutes...")
    time.sleep(60)
    run_all()
    st.rerun()