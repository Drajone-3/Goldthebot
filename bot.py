import telebot
import requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = "8671082907:AAFu6RI44Qgw2eOB4sUKhPZZSOyeVz-ER2E"
GROQ_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
                "max_tokens": 900,
                "temperature": 0.3
            },
            timeout=30
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "AI Error: " + str(e)

def get_gold_data(interval, range_period):
    try:
        base = "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD%3DX"
        url = base + "?interval=" + interval + "&range=" + range_period
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = r.json()["chart"]["result"][0]
        closes = [c for c in data["indicators"]["quote"][0]["close"] if c is not None]
        highs  = [h for h in data["indicators"]["quote"][0]["high"]  if h is not None]
        lows   = [l for l in data["indicators"]["quote"][0]["low"]   if l is not None]
        if closes:
            avg_range = sum([highs[i]-lows[i] for i in range(-10,0)]) / 10
            last_range = highs[-1] - lows[-1]
            volatility = "HIGH" if last_range > avg_range * 1.5 else "NORMAL" if last_range > avg_range * 0.8 else "LOW"
            return {
                "price":      round(closes[-1], 2),
                "high":       round(max(highs[-20:]), 2),
                "low":        round(min(lows[-20:]), 2),
                "change":     round(closes[-1] - closes[-2], 2) if len(closes) > 1 else 0,
                "pct":        round(((closes[-1] - closes[-2]) / closes[-2]) * 100, 3) if len(closes) > 1 else 0,
                "range":      round(last_range, 2),
                "avg_range":  round(avg_range, 2),
                "volatility": volatility,
            }
    except:
        return None

def get_all_mtf():
    return {
        "M1":  get_gold_data("1m",  "1d"),
        "M5":  get_gold_data("5m",  "1d"),
        "M15": get_gold_data("15m", "1d"),
        "H1":  get_gold_data("60m", "5d"),
        "H4":  get_gold_data("1h",  "1mo"),
        "D1":  get_gold_data("1d",  "3mo"),
    }

def get_web_signals():
    signals = []
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc?query=gold+XAU+USD+buy+sell+signal+trading&mode=artlist&maxrecords=6&sort=DateDesc&format=json",
            timeout=10
        )
        for a in r.json().get("articles", [])[:5]:
            signals.append(a.get("title", ""))
    except:
        pass
    return signals

def build_mtf_summary(mtf):
    text = ""
    for tf, d in mtf.items():
        if d:
            arrow = "UP" if d["change"] >= 0 else "DOWN"
            text += tf + ": $" + str(d["price"]) + " " + arrow + " " + str(d["change"]) + " | Vol:" + d["volatility"] + " | Range:" + str(d["range"]) + "\n"
        else:
            text += tf + ": Unavailable\n"
    return text

def get_session():
    hour = datetime.now(timezone.utc).hour
    wat = hour + 1
    if 7 <= hour < 12:
        return "London Open (High Activity) - " + str(wat) + ":00 WAT"
    elif 12 <= hour < 16:
        return "London/NY Overlap (Best Session) - " + str(wat) + ":00 WAT"
    elif 16 <= hour < 21:
        return "NY Session - " + str(wat) + ":00 WAT"
    else:
        return "Asian Session (Low Activity) - " + str(wat) + ":00 WAT"

@bot.message_handler(commands=["start", "help"])
def start(msg):
    bot.reply_to(msg,
        "Jones X Operations Gold Bot\n"
        "Powered by Groq AI + Live Data\n\n"
        "SIGNALS:\n"
        "/signal - Full combined signal\n"
        "/smart - $15 to $20 smart entry\n"
        "/volatile - Volatility analysis\n\n"
        "TIMEFRAMES:\n"
        "/m1  - 1 min signal\n"
        "/m5  - 5 min signal\n"
        "/m15 - 15 min signal\n"
        "/h1  - 1 hour signal\n"
        "/h4  - 4 hour signal\n"
        "/d1  - Daily signal\n\n"
        "INFO:\n"
        "/price   - Live gold price\n"
        "/analyze - Deep MTF analysis\n"
        "/news    - Web trader signals\n"
        "/session - Current market session\n"
        "/help    - This menu"
    )

@bot.message_handler(commands=["session"])
def session(msg):
    bot.reply_to(msg,
        "Current Session: " + get_session() + "\n\n"
        "Best sessions for gold:\n"
        "London Open: 8AM-12PM WAT\n"
        "London/NY Overlap: 2PM-5PM WAT\n\n"
        "Avoid: 30 mins before CPI, NFP, FOMC\n"
        "Next FOMC: May 6-7, Jun 17-18"
    )

@bot.message_handler(commands=["price"])
def price(msg):
    bot.reply_to(msg, "Fetching live gold price...")
    d = get_gold_data("1m", "1d")
    if d:
        arrow = "UP" if d["change"] >= 0 else "DOWN"
        now = datetime.now(timezone.utc)
        wat = now.hour + 1
        bot.reply_to(msg,
            "XAU/USD Live Price\n"
            "$" + str(d["price"]) + " USD/oz\n"
            "" + arrow + " " + str(d["change"]) + " (" + str(d["pct"]) + "%)\n"
            "High: $" + str(d["high"]) + " | Low: $" + str(d["low"]) + "\n"
            "Volatility: " + d["volatility"] + "\n"
            "Session: " + get_session() + "\n"
            "Time: " + str(wat) + ":" + now.strftime("%M") + " WAT"
        )
    else:
        bot.reply_to(msg, "Could not fetch price. Try again.")

@bot.message_handler(commands=["volatile"])
def volatile(msg):
    bot.reply_to(msg, "Checking volatility across all timeframes...")
    mtf = get_all_mtf()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mtf_text = build_mtf_summary(mtf)
    prompt = (
        "You are a professional XAU/USD volatility analyst.\n"
        "Time: " + now + "\n"
        "Session: " + get_session() + "\n\n"
        "Multi-Timeframe Volatility Data:\n" + mtf_text + "\n"
        "Analyze volatility and give:\n\n"
        "VOLATILITY REPORT - XAU/USD\n"
        "OVERALL VOLATILITY: [HIGH / NORMAL / LOW]\n"
        "VOLATILITY ANALYSIS: [2 sentences]\n"
        "IS NOW A GOOD TIME TO TRADE? [YES / NO / WAIT] - reason\n\n"
        "VOLATILITY PLAY SETUP:\n"
        "Signal: [BUY/SELL]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "TP1: $[level]\n"
        "TP2: $[level]\n\n"
        "DANGER ZONES: [levels to avoid]\n"
        "RECOMMENDATION: [One clear sentence]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["smart"])
def smart(msg):
    bot.reply_to(msg, "Running smart entry for $15 to $20 target... Please wait 20 seconds")
    mtf = get_all_mtf()
    web = get_web_signals()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(web[:4]) if web else "None"
    d1 = get_gold_data("1m", "1d")
    current_price = str(d1["price"]) if d1 else "N/A"
    prompt = (
        "You are an elite XAU/USD scalp trader.\n"
        "Time: " + now + "\n"
        "Session: " + get_session() + "\n"
        "Current Price: $" + current_price + "\n\n"
        "All Timeframe Data:\n" + mtf_text + "\n"
        "Web Signals:\n" + signals_text + "\n\n"
        "Trader wants to risk $15 to make $20 using 0.01-0.02 lot size.\n\n"
        "SMART ENTRY - $15 TO $20 TARGET\n"
        "SIGNAL: [STRONG BUY / BUY / SELL / STRONG SELL]\n"
        "Confidence: [%]\n\n"
        "NORMAL ENTRY:\n"
        "Entry Price: $[level]\n"
        "Stop Loss: $[level] (~$15 risk on 0.01 lot)\n"
        "Take Profit: $[level] (~$20 profit on 0.01 lot)\n"
        "Risk/Reward: 1:[ratio]\n\n"
        "BEST ENTRY (High Probability):\n"
        "Wait for: $[level]\n"
        "Confirmation: [what to look for]\n"
        "Stop Loss: $[level]\n"
        "Take Profit: $[level]\n\n"
        "TIMEFRAME CONFLUENCE: [which TFs agree]\n"
        "DO NOT TRADE IF: [conditions]\n"
        "BEST TIME TODAY (WAT): [time]\n"
        "VERDICT: [One sentence]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["signal"])
def signal(msg):
    bot.reply_to(msg, "Analyzing all timeframes + web signals... Please wait 20 seconds")
    mtf = get_all_mtf()
    web = get_web_signals()
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(web[:5]) if web else "None"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        "You are a professional XAU/USD gold trader.\n"
        "Time: " + now + "\n"
        "Session: " + get_session() + "\n\n"
        "Multi-Timeframe Data:\n" + mtf_text + "\n"
        "Web Trader Signals:\n" + signals_text + "\n\n"
        "Give ONE combined signal:\n\n"
        "SIGNAL: [STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL]\n"
        "Current Price: $[price]\n"
        "Entry Zone: $[range]\n"
        "Stop Loss: $[level] (~[pips] pips)\n"
        "Take Profit 1: $[level]\n"
        "Take Profit 2: $[level]\n"
        "Risk/Reward: 1:[ratio]\n\n"
        "REASON: [3 sentences]\n"
        "WEB SENTIMENT: [BULLISH/BEARISH/MIXED]\n"
        "VOLATILITY: [HIGH/NORMAL/LOW]\n"
        "KEY RISK: [One sentence]\n"
        "VALID FOR: [timeframe]\n\n"
        "Note: 0.01 lots, $5-10 profit target, $5 max loss."
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

def single_tf(msg, tf, interval, range_p):
    bot.reply_to(msg, "Analyzing " + tf + " timeframe...")
    d = get_gold_data(interval, range_p)
    if not d:
        bot.reply_to(msg, "Could not fetch " + tf + " data.")
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        "You are a professional XAU/USD analyst.\n"
        "Time: " + now + "\n"
        "Timeframe: " + tf + "\n"
        "Price: $" + str(d["price"]) + "\n"
        "Change: " + str(d["change"]) + " (" + str(d["pct"]) + "%)\n"
        "High: $" + str(d["high"]) + " | Low: $" + str(d["low"]) + "\n"
        "Volatility: " + d["volatility"] + "\n\n"
        "Give a " + tf + " signal:\n\n"
        "TIMEFRAME: " + tf + "\n"
        "SIGNAL: [BUY / SELL / NEUTRAL]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Take Profit: $[level]\n"
        "Risk/Reward: 1:[ratio]\n\n"
        "REASON: [2 sentences]\n"
        "VALID FOR: [time]\n"
        "NOTE: 0.01 lots, $5-10 profit, $5 max loss."
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["m1"])
def m1(msg):
    single_tf(msg, "M1", "1m", "1d")

@bot.message_handler(commands=["m5"])
def m5(msg):
    single_tf(msg, "M5", "5m", "1d")

@bot.message_handler(commands=["m15"])
def m15(msg):
    single_tf(msg, "M15", "15m", "1d")

@bot.message_handler(commands=["h1"])
def h1(msg):
    single_tf(msg, "H1", "60m", "5d")

@bot.message_handler(commands=["h4"])
def h4(msg):
    single_tf(msg, "H4", "1h", "1mo")

@bot.message_handler(commands=["d1"])
def d1(msg):
    single_tf(msg, "D1", "1d", "3mo")

@bot.message_handler(commands=["news"])
def news(msg):
    bot.reply_to(msg, "Fetching web trader signals...")
    signals = get_web_signals()
    if signals:
        text = "Web Trader Signals\n\n"
        for i, s in enumerate(signals, 1):
            text += str(i) + ". " + s + "\n\n"
        bot.reply_to(msg, text)
    else:
        bot.reply_to(msg, "Could not fetch signals. Try again.")

@bot.message_handler(commands=["analyze"])
def analyze(msg):
    bot.reply_to(msg, "Running deep analysis... Please wait 20 seconds")
    mtf = get_all_mtf()
    web = get_web_signals()
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(web[:4]) if web else "None"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = (
        "You are a senior XAU/USD analyst.\n"
        "Time: " + now + "\n"
        "Session: " + get_session() + "\n\n"
        "All Timeframes:\n" + mtf_text + "\n"
        "Web Signals:\n" + signals_text + "\n\n"
        "DEEP ANALYSIS - XAU/USD\n\n"
        "MARKET STRUCTURE: [Overall trend from D1 and H4]\n\n"
        "TIMEFRAME CONFLUENCE:\n"
        "D1: [trend + key level]\n"
        "H4: [trend + structure]\n"
        "H1: [momentum]\n"
        "M15: [short term bias]\n"
        "M5: [entry timing]\n"
        "M1: [micro entry]\n\n"
        "KEY LEVELS:\n"
        "Major Resistance: $[level]\n"
        "Minor Resistance: $[level]\n"
        "Current: $[price]\n"
        "Minor Support: $[level]\n"
        "Major Support: $[level]\n\n"
        "VOLATILITY STATUS: [HIGH/NORMAL/LOW]\n"
        "WEB SENTIMENT: [Bullish/Bearish/Mixed]\n\n"
        "BEST SETUP:\n"
        "Bias: [BULLISH/BEARISH/RANGING]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Target: $[level]\n\n"
        "FINAL VERDICT: [One clear action]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

print("Jones X Operations Gold Bot is running...")
print("M1 M5 M15 H1 H4 D1 + Smart Entry + Volatility")
bot.infinity_polling()
            
          
