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
                "Authorization": f"Bearer {GROQ_API_KEY}",
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
        return f"AI Error: {e}"

def get_gold_data(interval, range_period):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval={interval}&range={range_period}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = r.json()["chart"]["result"][0]
        closes = [c for c in data["indicators"]["quote"][0]["close"] if c is not None]
        highs  = [h for h in data["indicators"]["quote"][0]["high"]  if h is not None]
        lows   = [l for l in data["indicators"]["quote"][0]["low"]   if l is not None]
        volumes= [v for v in data["indicators"]["quote"][0]["volume"] if v is not None]
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
            text += f"{tf}: ${d['price']} {arrow} {d['change']:+.2f} | Vol:{d['volatility']} | Range:{d['range']}\n"
        else:
            text += f"{tf}: Unavailable\n"
    return text

def get_session():
    hour = datetime.now(timezone.utc).hour
    if 7 <= hour < 12:
        return "London Open (High Activity)"
    elif 12 <= hour < 16:
        return "London/NY Overlap (Best Session)"
    elif 16 <= hour < 21:
        return "NY Session"
    else:
        return "Asian Session (Low Activity)"

@bot.message_handler(commands=["start", "help"])
def start(msg):
    bot.reply_to(msg,
        "Jones X Operations Gold Bot\n"
        "Powered by Groq AI + Live Data\n\n"
        "SIGNALS:\n"
        "/signal - Full combined signal\n"
        "/smart - $15 to $20 smart entry\n"
        "/volatile - Volatility alert analysis\n\n"
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
    s = get_session()
    hour = datetime.now(timezone.utc).hour
    bot.reply_to(msg,
        f"Current Session: {s}\n"
        f"UTC Time: {hour}:00\n"
        f"WAT Time: {hour+1}:00\n\n"
        "Best sessions for gold:\n"
        "London Open: 8AM-12PM WAT\n"
        "London/NY: 2PM-5PM WAT\n\n"
        "Avoid: 30 mins before CPI, NFP, FOMC"
    )

@bot.message_handler(commands=["price"])
def price(msg):
    bot.reply_to(msg, "Fetching live gold price...")
    d = get_gold_data("1m", "1d")
    if d:
        arrow = "UP" if d["change"] >= 0 else "DOWN"
        bot.reply_to(msg,
            f"XAU/USD Live Price\n"
            f"${d['price']:,.2f} USD/oz\n"
            f"{arrow} {d['change']:+.2f} ({d['pct']:+.3f}%)\n"
            f"Volatility: {d['volatility']}\n"
            f"Session: {get_session()}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        )
    else:
        bot.reply_to(msg, "Could not fetch price. Try again.")

@bot.message_handler(commands=["volatile"])
def volatile(msg):
    bot.reply_to(msg, "Checking volatility across all timeframes...")
    mtf = get_all_mtf()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mtf_text = build_mtf_summary(mtf)
    prompt = f"""You are a professional XAU/USD volatility analyst.
Time: {now}
Session: {get_session()}

Multi-Timeframe Volatility Data:
{mtf_text}

Analyze volatility and give:

VOLATILITY REPORT - XAU/USD
Time: {now}
Session: {get_session()}

OVERALL VOLATILITY: [HIGH / NORMAL / LOW]

VOLATILITY ANALYSIS:
[2 sentences on current volatility across timeframes]

IS NOW A GOOD TIME TO TRADE?
[YES / NO / WAIT] - [reason]

IF HIGH VOLATILITY - BEST ENTRIES:
Primary Entry: $[level] [direction]
Aggressive Entry: $[level] [direction]
Conservative Entry: $[level] [direction]

VOLATILITY PLAY SETUP:
Signal: [BUY/SELL]
Entry: $[level]
Stop Loss: $[level] (wider for volatility)
TP1: $[level]
TP2: $[level]

DANGER ZONES: [price levels to avoid]

RECOMMENDATION: [One clear action sentence]"""
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["smart"])
def smart(msg):
    bot.reply_to(msg, "Running smart entry analysis for $15 to $20 target... Please wait")
    mtf = get_all_mtf()
    web = get_web_signals()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(web[:4]) if web else "None"
    d1 = get_gold_data("1m", "1d")
    current_price = d1["price"] if d1 else "N/A"

    prompt = f"""You are an elite XAU/USD scalp trader. 
Time: {now}
Session: {get_session()}
Current Price: ${current_price}

All Timeframe Data:
{mtf_text}

Web Signals:
{signals_text}

The trader wants to risk $15 to make $20 profit on gold using 0.01-0.02 lot size.
That means roughly 13-20 pip stop loss and 17-25 pip take profit on 0.01 lot.

Give the SMARTEST highest probability entry:

SMART ENTRY - $15 TO $20 TARGET
Time: {now}
Current Price: ${current_price}
Session: {get_session()}

SIGNAL: [STRONG BUY / BUY / SELL / STRONG SELL]
Confidence: [%]

NORMAL ENTRY:
Entry Price: $[level]
Stop Loss: $[level] (~[pips] pips = ~$15 risk on 0.01 lot)
Take Profit: $[level] (~[pips] pips = ~$20 profit on 0.01 lot)
Risk/Reward: 1:[ratio]

BEST ENTRY (High Probability):
Wait for price to reach: $[level]
Confirmation signal: [what to look for]
Entry after: [condition]
Stop Loss: $[level]
Take Profit: $[level]

VOLATILITY ENTRY (If market is moving fast):
Breakout level: $[level]
Entry on break of: $[level]
Stop Loss: $[level]
Target: $[level]

TIMEFRAME CONFLUENCE: [which TFs agree]
WEB SENTIMENT: [Bullish/Bearish/Mixed]

DO NOT TRADE IF: [conditions to avoid]

BEST TIME TO ENTER TODAY: [specific time in WAT]

VERDICT: [One sentence - enter now or wait and why]"""
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
    prompt = f"""You are a professional XAU/USD gold trader and analyst.
Time: {now}
Session: {get_session()}

Multi-Timeframe Data:
{mtf_text}

Web Trader Signals:
{signals_text}

Give ONE combined signal:

SIGNAL: [STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL]
Current Price: $[price]
Entry Zone: $[range]
Stop Loss: $[level] (~[pips] pips)
Take Profit 1: $[level] (~[pips] pips)
Take Profit 2: $[level] (~[pips] pips)
Risk/Reward: 1:[ratio]

REASON:
[3 sentences covering all timeframes and web sentiment]

WEB SENTIMENT: [BULLISH/BEARISH/MIXED]
VOLATILITY: [HIGH/NORMAL/LOW]
KEY RISK: [One sentence]
VALID FOR: [timeframe]
BEST SESSION: {get_session()}

Note: 0.01 lots, $5-10 profit target, $5 max loss."""
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

def single_tf(msg, tf, interval, range_p):
    bot.reply_to(msg, f"Analyzing {tf} timeframe...")
    d = get_gold_data(interval, range_p)
    if not d:
        bot.reply_to(msg, f"Could not fetch {tf} data.")
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = f"""You are a professional XAU/USD analyst.
Time: {now}
Timeframe: {tf}
Price: ${d['price']}
Change: {d['change']:+.2f} ({d['pct']:+.3f}%)
High: ${d['high']} | Low: ${d['low']}
Volatility: {d['volatility']} | Range: {d['range']} pips

Give a {tf} signal:

TIMEFRAME: {tf}
SIGNAL: [BUY / SELL / NEUTRAL]
Entry: $[level]
Stop Loss: $[level]
Take Profit: $[level]
Risk/Reward: 1:[ratio]
Volatility: {d['volatility']}

REASON: [2 sentences]
VALID FOR: [time]
NOTE: 0.01 lots, $5-10 profit, $5 max loss."""
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
            text += f"{i}. {s}\n\n"
        bot.reply_to(msg, text)
    else:
        bot.reply_to(msg, "Could not fetch signals. Try again.")

@bot.message_handler(commands=["analyze"])
def analyze(msg):
    bot.reply_to(msg, "Running deep analysis across all timeframes... Please wait")
    mtf = get_all_mtf()
    web = get_web_signals()
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(web[:4]) if web else "None"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prompt = f"""You are a senior XAU/USD analyst.
Time: {now}
Session: {get_session()}

All Timeframes:
{mtf_text}

Web Signals:
{signals_text}

DEEP ANALYSIS - XAU/USD
Time: {now}
Session: {get_session()}

MARKET STRUCTURE:
[Overall trend from D1 and H4]

TIMEFRAME CONFLUENCE:
D1: [trend + key level]
H4: [trend + structure]
H1: [momentum]
M15: [short term bias]
M5: [entry timing]
M1: [micro entry]

KEY LEVELS:
Major Resistance: $[level]
Minor Resistance: $[level]
Current: $[price]
Minor Support: $[level]
Major Support: $[level]

VOLATILITY STATUS: [HIGH/NORMAL/LOW]
WEB SENTIMENT: [Bullish/Bearish/Mixed]

BEST SETUP:
Bias: [BULLISH/BEARISH/RANGING]
Entry: $[level]
Stop Loss: $[level]
Target: $[level]
Session: {get_session()}

FINAL VERDICT: [One clear action]"""
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

print("Jones X Operations Gold Bot is running...")
print("M1 M5 M15 H1 H4 D1 + Smart Entry + Volatility")
bot.infinity_polling()
          
