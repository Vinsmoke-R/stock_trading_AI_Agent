import feedparser

# ticker = "AAPL"

# url = f"https://news.google.com/rss/search?q={ticker}+stock"

# feed = feedparser.parse(url)

# for entry in feed.entries[:10]:
#     print(entry.title)

def news_fetch(ticker):
    url = f"https://news.google.com/rss/search?q={ticker}+stock"

    feed = feedparser.parse(url)

    headlines = []

    for entry in feed.entries[:10]:
        headlines.append(entry.title)   # we use headlines instead of return because return exit the function on 1st loop

    return headlines