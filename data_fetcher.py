import yfinance as yf
# data = yf.download(
#     "AAPL",
#     period="1d",
#     interval="5m"
# )
# print(data.index)
# data.index = data.index.tz_convert("Asia/Kolkata")

# print(data.tail())

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
    