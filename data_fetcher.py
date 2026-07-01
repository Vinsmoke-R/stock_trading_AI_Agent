import yfinance as yf

# create function
def data_fetch(company, period, interval):
    data = yf.download(
        company,
        period = period,
        interval = interval,
    )
    data.index = data.index.tz_convert("Asia/Kolkata")
    return data.tail()

# baka = data_fetch("AAPL","1d","5m")
# print(baka)
    