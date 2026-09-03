import feedparser

def news_fetch(ticker):
    url = f"https://news.google.com/rss/search?q={ticker}+stock"
    feed = feedparser.parse(url)
    headlines = []
    for entry in feed.entries[:10]:
        headlines.append(entry.title)
    return headlines