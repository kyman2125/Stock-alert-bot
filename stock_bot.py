import os
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        if r.status_code != 200:
            print("❌ Telegram error:", r.text)
    except Exception as e:
        print("❌ Telegram send failed:", e)

def get_tickers_under_10():
    try:
        urls = [
            "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt",
            "ftp://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
        ]
        dfs = [pd.read_csv(u, sep="|") for u in urls]
        tickers = pd.concat(dfs)["Symbol"].dropna().tolist()
        cheap = []
        for t in tickers[:2000]:
            try:
                price = yf.Ticker(t).info.get("regularMarketPrice", None)
                if price and price < 10:
                    cheap.append(t)
            except Exception:
                pass
        return cheap
    except Exception as e:
        print("❌ Error fetching tickers:", e)
        return []

def scan_ticker(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d")
        if data.empty:
            return None
        last_close = data["Close"].iloc[-1]
        avg_volume = data["Volume"].mean()
        last_volume = data["Volume"].iloc[-1]

        conditions = []
        if last_volume > 2 * avg_volume:
            conditions.append("High Volume")

        delta = data["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        last_rsi = rsi.iloc[-1]

        if last_rsi < 30:
            conditions.append("Oversold (RSI<30)")
        elif last_rsi > 70:
            conditions.append("Overbought (RSI>70)")

        if conditions:
            return f"🚨 {ticker}: {', '.join(conditions)} | Price ${last_close:.2f}"
    except Exception as e:
        print(f"❌ Error scanning {ticker}: {e}")
    return None

def main():
    send_telegram("🤖 Stock Alert Bot started and is running...")
    tickers = get_tickers_under_10()
    print(f"✅ Loaded {len(tickers)} cheap tickers")
    last_refresh = datetime.now()

    while True:
        if datetime.now() - last_refresh > timedelta(hours=24):
            tickers = get_tickers_under_10()
            print(f"🔄 Refreshed ticker list: {len(tickers)}")
            last_refresh = datetime.now()

        for t in tickers[:200]:
            alert = scan_ticker(t)
            if alert:
                send_telegram(alert)

        time.sleep(300)

if __name__ == "__main__":
    main()
