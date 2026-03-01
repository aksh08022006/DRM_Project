import yfinance as yf

ticker = yf.Ticker("JSWSTEEL.NS")

dividends = ticker.dividends

print(dividends["2025-03-04":"2026-03-04"])
