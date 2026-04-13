import telebot
import requests
import os
from datetime import datetime, timezone
import pandas as pd

# 🔐 USE ENV VARIABLES (IMPORTANT)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# =========================
# 🤖 GROQ AI FUNCTION
# =========================
def ask_groq(prompt):
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + GROQ_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.3
            },
            timeout=30
        )

        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return "AI Error: No valid response"

    except Exception as e:
        return "AI Error: " + str(e)

# =========================
# 📊 GOLD DATA + INDICATORS
# =========================
def get_gold_data(interval, range_period):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD%3DX?interval={interval}&range={range_period}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)

        data = r.json()["chart"]["result"][0]["indicators"]["quote"][0]

        df = pd.DataFrame({
            "close": data["close"],
            "high": data["high"],
            "low": data["low"]
        }).dropna()

        if len(df) < 50:
            return None

        # EMA
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        # RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        last = df.iloc[-1]

        return {
            "price": round(last["close"], 2),
            "ema20": round(last["ema20"], 2),
            "ema50": round(last["ema50"], 2),
            "rsi": round(last["rsi"], 2),
            "trend": "BULLISH" if last["ema20"] > last["ema50"] else "BEARISH"
        }

    except:
        return None

# =========================
# 📊 MULTI TIMEFRAME
# =========================
def get_all_mtf():
    return {
        "M1": get_gold_data("1m", "1d"),
        "M5": get_gold_data("5m", "1d"),
        "M15": get_gold_data("15m", "1d"),
        "H1": get_gold_data("60m", "5d"),
        "H4": get_gold_data("1h", "1mo"),
        "D1": get_gold_data("1d", "3mo"),
    }

# =========================
# 🧠 TRADE FILTER
# =========================
def is_good_trade(d):
    if not d:
        return False
    if d["rsi"] > 70 or d["rsi"] < 30:
        return False
    return True

def get_entry_signal(d):
    if not d:
        return "NO DATA"

    if d["trend"] == "BULLISH" and d["rsi"] < 60:
        return "BUY"
    elif d["trend"] == "BEARISH" and d["rsi"] > 40:
        return "SELL"
    return "WAIT"

# =========================
# 📈 BUILD TEXT
# =========================
def build_mtf_summary(mtf):
    text = ""
    for tf, d in mtf.items():
        if d:
            text += f"{tf}: ${d['price']} | RSI:{d['rsi']} | {d['trend']}\n"
        else:
            text += f"{tf}: No data\n"
    return text

# =========================
# 🕒 SESSION
# =========================
def get_session():
    hour = datetime.now(timezone.utc).hour
    wat = hour + 1

    if 7 <= hour < 12:
        return f"London Open - {wat}:00 WAT"
    elif 12 <= hour < 16:
        return f"London/NY Overlap - {wat}:00 WAT"
    elif 16 <= hour < 21:
        return f"NY Session - {wat}:00 WAT"
    else:
        return f"Asian Session - {wat}:00 WAT"

# =========================
# 🚀 COMMANDS
# =========================
@bot.message_handler(commands=["start", "help"])
def start(msg):
    bot.reply_to(msg,
        "🔥 Jones X Gold Bot (PRO)\n\n"
        "/signal - AI + Indicator Signal\n"
        "/price - Live price\n"
        "/analyze - Deep analysis\n"
        "/session - Market session"
    )

# =========================
# 💰 PRICE
# =========================
@bot.message_handler(commands=["price"])
def price(msg):
    bot.send_chat_action(msg.chat.id, "typing")

    d = get_gold_data("1m", "1d")

    if not d:
        bot.reply_to(msg, "Error fetching price")
        return

    bot.reply_to(msg,
        f"XAU/USD: ${d['price']}\n"
        f"RSI: {d['rsi']}\n"
        f"Trend: {d['trend']}\n"
        f"Session: {get_session()}"
    )

# =========================
# 📊 SIGNAL
# =========================
@bot.message_handler(commands=["signal"])
def signal(msg):
    bot.send_chat_action(msg.chat.id, "typing")

    mtf = get_all_mtf()
    m1 = mtf["M1"]

    if not is_good_trade(m1):
        bot.reply_to(msg, "❌ Market not safe to trade now")
        return

    mtf_text = build_mtf_summary(mtf)

    prompt = (
        "You are a professional gold trader.\n\n"
        "RULES:\n"
        "- RSI >70 = overbought (sell)\n"
        "- RSI <30 = oversold (buy)\n"
        "- EMA20 > EMA50 = bullish\n\n"
        "DATA:\n" + mtf_text + "\n\n"

        "Give:\n"
        "SIGNAL: BUY or SELL\n"
        "ENTRY: price\n"
        "SL: price\n"
        "TP: price\n"
        "REASON: short explanation"
    )

    result = ask_groq(prompt)
    bot.reply_to(msg, result)

# =========================
# 🧠 ANALYSIS
# =========================
@bot.message_handler(commands=["analyze"])
def analyze(msg):
    bot.send_chat_action(msg.chat.id, "typing")

    mtf = get_all_mtf()
    mtf_text = build_mtf_summary(mtf)

    prompt = (
        "You are a gold analyst.\n\n"
        "Analyze market using RSI + EMA.\n\n"
        + mtf_text +
        "\nGive trend and best trade setup."
    )

    result = ask_groq(prompt)
    bot.reply_to(msg, result)

# =========================
# 🕒 SESSION
# =========================
@bot.message_handler(commands=["session"])
def session(msg):
    bot.reply_to(msg, get_session())

# =========================
# ▶ RUN BOT
# =========================
print("🚀 Gold Bot Running...")
bot.infinity_polling()
          
