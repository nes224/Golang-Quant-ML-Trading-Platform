import yfinance as yf
import json

def debug_news():
    ticker = yf.Ticker("GC=F")
    news = ticker.news
    if news:
        print("Content Keys:", list(news[0]['content'].keys()))
        # print("First Item:", json.dumps(news[0], indent=2))
    else:
        print("No news found")

if __name__ == "__main__":
    debug_news()
