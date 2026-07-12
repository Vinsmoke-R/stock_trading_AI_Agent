import yfinance as yf
from indicators import add_indicators

def backtest(ticker="AAPL", initial_balance=10000):
    data = yf.download(ticker, period="1y", interval="1d", progress=False)
    data.columns = data.columns.droplevel(1)
    df = add_indicators(data)
    df = df.dropna()

    balance = initial_balance
    share = 0

    for date, row in df.iterrows():
        price = row["Close"]
        rsi = row["RSI_14"]
        vwap = row["VWAP"]

        if rsi < 30 and price < vwap and balance >= price:
            balance -= price
            share += 1
        elif rsi > 70 and price > vwap and share >= 1:
            balance += price
            share -= 1

    final_price = df["Close"].iloc[-1]
    portfolio_value = balance + (share * final_price)
    profit = portfolio_value - initial_balance
    strategy_return = (profit / initial_balance) * 100
    buy_and_hold = ((df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]) * 100

    return {
        "ticker": ticker,
        "profit": round(profit, 2),
        "strategy_return": round(strategy_return, 2),
        "buy_and_hold": round(buy_and_hold, 2),
        "final_portfolio": round(portfolio_value, 2),
        "shares_held": share,
    }

if __name__ == "__main__":
    result = backtest("AAPL")
    print(f"Strategy Return:   {result['strategy_return']}%")
    print(f"Buy & Hold Return: {result['buy_and_hold']}%")
    print(f"Final Portfolio:   ${result['final_portfolio']}")
    print(f"Profit:            ${result['profit']}")
    print(f"Shares held:       {result['shares_held']}")