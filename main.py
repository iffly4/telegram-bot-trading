import time
import asyncio
import requests
import pandas as pd
import ta
from telegram import Bot

# ===== CONFIG =====
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
TELEGRAM_TOKEN = "8325852900:AAGM27V9rOPAjwrqyJCJHTJK12mZtyXIRy4"
CHAT_ID = "6876248388"

LEVERAGE = 25
CAPITAL = 100
INITIAL_SIZE_PCT = 0.04
ADD_SIZE_PCT = 0.15

# ===== INIT =====
bot = Bot(token=TELEGRAM_TOKEN)
position_size = 0
add_used = False

# ===== HELPER =====
async def send_telegram(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print(f"📤 Telegram sent: {msg}")
    except Exception as e:
        print(f"Telegram error: {e}")

def fetch_ohlcv(symbol, interval, limit=100):
    interval_map = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "1h": "1h",
        "1d": "1d"
    }
    url_interval = interval_map.get(interval, "1d")
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={url_interval}&limit={limit}"
    r = requests.get(url)
    data = r.json()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time","quote_asset_volume","number_of_trades",
        "taker_buy_base","taker_buy_quote","ignore"
    ])
    df["close"] = df["close"].astype(float)
    return df

# ===== MAIN LOOP =====
async def main():
    global position_size, add_used
    
    print(f"🤖 Trading Bot Started!")
    print(f"📊 Monitoring {SYMBOL} on {INTERVAL} interval")
    print(f"💰 Capital: ${CAPITAL} | Leverage: {LEVERAGE}x")
    print("-" * 50)
    
    # Kirim pesan startup ke Telegram
    await send_telegram(f"🤖 Bot Trading Aktif!\n📊 Pair: {SYMBOL}\n⏱ Interval: {INTERVAL}\n💰 Capital: ${CAPITAL} | Leverage: {LEVERAGE}x")
    
    while True:
        try:
            print(f"⏰ Checking market at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            df = fetch_ohlcv(SYMBOL, INTERVAL, limit=100)
            print(f"✅ Fetched {len(df)} candles from Binance")

            if len(df) < 50:
                print("Belum cukup data, tunggu 1 menit...")
                await asyncio.sleep(60)
                continue

            close = df["close"]

            print("📈 Calculating indicators...")
            ema13 = ta.trend.EMAIndicator(close, window=13).ema_indicator()
            ema21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
            ma50  = ta.trend.SMAIndicator(close, window=50).sma_indicator()
            print(f"   EMA13: {ema13.iloc[-1]:.2f} | EMA21: {ema21.iloc[-1]:.2f} | MA50: {ma50.iloc[-1]:.2f}")

            last = len(df) - 1
            prev = len(df) - 2

            entryCondition1 = ema13.iloc[prev] < ema21.iloc[prev] and ema13.iloc[last] > ema21.iloc[last]
            entryCondition2 = ema13.iloc[last] > ema21.iloc[last] and ema13.iloc[last] > ma50.iloc[last] and ema21.iloc[last] > ma50.iloc[last]
            exitCondition = ema13.iloc[prev] > ema21.iloc[prev] and ema13.iloc[last] < ema21.iloc[last]

            buying_power = CAPITAL * LEVERAGE
            initial_size = buying_power * INITIAL_SIZE_PCT
            add_size = buying_power * ADD_SIZE_PCT

            if entryCondition1:
                position_size += initial_size
                await send_telegram(f"📈 Open Long Initial: {initial_size:.2f} USD")

            if entryCondition2 and position_size > 0 and not add_used:
                position_size += add_size
                add_used = True
                await send_telegram(f"➕ Open Long Add: {add_size:.2f} USD")

            if exitCondition and position_size > 0:
                await send_telegram(f"❌ Close Long: {position_size:.2f} USD")
                position_size = 0
                add_used = False

            print(f"💼 Current position: ${position_size:.2f}")
            print(f"⏳ Sleeping for 60 seconds...")
            print("-" * 50)
            await asyncio.sleep(60)

        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
