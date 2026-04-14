
import telebot
import requests
from datetime import datetime, timezone

TELEGRAM_TOKEN = "8671082907:AAFu6RI44Qgw2eOB4sUKhPZZSOyeVz-ER2E"
GROQ_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ─── TWITTER/X TRADERS TO TRACK ──────────────────────────────────────────────
TRACKED_TRADERS = [
    "GoldTradingPro",
    "XAUSignals",
    "ForexGoldKing",
    "GoldBullTrader",
    "PeterLBrandt",
]

# ─── GROQ AI ──────────────────────────────────────────────────────────────────
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
                "max_tokens": 1000,
                "temperature": 0.3
            },
            timeout=45
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return "AI Error: " + str(e)

# ─── EXACT GOLD PRICE ─────────────────────────────────────────────────────────
def get_exact_gold_price():
    # Try metals-api first (most accurate spot price)
    try:
        r = requests.get(
            "https://metals-api.com/api/latest?access_key=demo&base=USD&symbols=XAU",
            timeout=6
        )
        data = r.json()
        if data.get("success") and data.get("rates", {}).get("XAU"):
            price = round(1 / data["rates"]["XAU"], 2)
            return {"price": price, "source": "Metals-API"}
    except:
        pass

    # Try Yahoo Finance spot gold
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD%3DX?interval=1m&range=1d",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = r.json()
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        prev  = result["meta"]["previousClose"]
        change = round(price - prev, 2)
        pct = round((change / prev) * 100, 3)
        return {
            "price": round(price, 2),
            "prev":  round(prev, 2),
            "change": change,
            "pct": pct,
            "source": "Yahoo Finance Spot"
        }
    except:
        pass

    # Fallback: GC=F futures (close to spot)
    try:
        r = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1m&range=1d",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = r.json()
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        prev  = result["meta"]["previousClose"]
        change = round(price - prev, 2)
        pct = round((change / prev) * 100, 3)
        return {
            "price": round(price, 2),
            "prev":  round(prev, 2),
            "change": change,
            "pct": pct,
            "source": "Yahoo Finance Futures"
        }
    except:
        return None

def get_gold_data(interval, range_period):
    try:
        base = "https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD%3DX"
        url = base + "?interval=" + interval + "&range=" + range_period
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        data = r.json()["chart"]["result"][0]
        closes = [c for c in data["indicators"]["quote"][0]["close"] if c is not None]
        highs  = [h for h in data["indicators"]["quote"][0]["high"]  if h is not None]
        lows   = [l for l in data["indicators"]["quote"][0]["low"]   if l is not None]
        if closes and len(highs) >= 10:
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

# ─── WEB SIGNALS & NEWS ───────────────────────────────────────────────────────
def get_gold_news():
    news = []
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc?query=gold+XAU+price+analysis+forecast&mode=artlist&maxrecords=8&sort=DateDesc&format=json",
            timeout=10
        )
        for a in r.json().get("articles", [])[:6]:
            news.append({"title": a.get("title",""), "url": a.get("url","")})
    except:
        pass
    return news

def get_trader_signals():
    signals = []
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc?query=gold+XAU+buy+sell+signal+trader+trading+view&mode=artlist&maxrecords=8&sort=DateDesc&format=json",
            timeout=10
        )
        for a in r.json().get("articles", [])[:6]:
            signals.append(a.get("title",""))
    except:
        pass
    try:
        r2 = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc?query=XAU+USD+technical+analysis+bullish+bearish&mode=artlist&maxrecords=5&sort=DateDesc&format=json",
            timeout=10
        )
        for a in r2.json().get("articles", [])[:4]:
            signals.append(a.get("title",""))
    except:
        pass
    return signals[:8]

def get_myfxbook_signals():
    signals = []
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc?query=myfxbook+gold+signal+XAU+forex+trader&mode=artlist&maxrecords=5&sort=DateDesc&format=json",
            timeout=10
        )
        for a in r.json().get("articles", [])[:4]:
            signals.append(a.get("title",""))
    except:
        pass
    return signals

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def build_mtf_summary(mtf):
    text = ""
    for tf, d in mtf.items():
        if d:
            arrow = "UP" if d["change"] >= 0 else "DOWN"
            text += tf + ": $" + str(d["price"]) + " " + arrow + " " + str(d["change"]) + " | Vol:" + d["volatility"] + "\n"
        else:
            text += tf + ": Unavailable\n"
    return text

def get_session():
    hour = datetime.now(timezone.utc).hour
    wat = hour + 1
    if 7 <= hour < 12:
        return "London Open (High Activity) " + str(wat) + ":00 WAT"
    elif 12 <= hour < 16:
        return "London/NY Overlap (Best!) " + str(wat) + ":00 WAT"
    elif 16 <= hour < 21:
        return "NY Session " + str(wat) + ":00 WAT"
    else:
        return "Asian Session (Low Activity) " + str(wat) + ":00 WAT"

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# ─── COMMANDS ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def start(msg):
    bot.reply_to(msg,
        "Jones X Operations Gold Bot\n"
        "Powered by Groq AI + Live Data\n\n"
        "PRICE & SESSION:\n"
        "/price   - Exact live gold price\n"
        "/session - Current market session\n\n"
        "SIGNALS:\n"
        "/signal  - Full AI combined signal\n"
        "/smart   - $15 to $20 smart entry\n"
        "/volatile - Volatility analysis\n\n"
        "TIMEFRAMES:\n"
        "/m1  /m5  /m15  /h1  /h4  /d1\n\n"
        "TRADER TRACKING:\n"
        "/traders - Signals from web traders\n"
        "/copytrade - Best trade to copy now\n"
        "/myfxbook - Myfxbook style signals\n\n"
        "AI ANALYSIS:\n"
        "/news    - AI gold news analysis\n"
        "/analyze - Deep market structure\n"
        "/structure - Full HTF to LTF structure\n\n"
        "AI CHAT:\n"
        "/ask [question] - Ask AI anything about gold\n"
        "Or just type any question directly!\n\n"
        "/help - This menu"
    )

@bot.message_handler(commands=["session"])
def session(msg):
    bot.reply_to(msg,
        "Current Session: " + get_session() + "\n\n"
        "Session Schedule (WAT):\n"
        "Asian:        2AM - 9AM\n"
        "London Open:  8AM - 12PM (High Vol)\n"
        "London/NY:    2PM - 5PM (Best!)\n"
        "NY Session:   3PM - 10PM\n\n"
        "Avoid trading:\n"
        "30 mins before CPI, NFP, FOMC\n\n"
        "Next key events:\n"
        "FOMC: May 6-7, Jun 17-18\n"
        "CPI: ~13th of each month\n"
        "NFP: First Friday of month"
    )

@bot.message_handler(commands=["price"])
def price(msg):
    bot.reply_to(msg, "Fetching exact gold spot price...")
    d = get_exact_gold_price()
    if d:
        now = datetime.now(timezone.utc)
        wat_h = now.hour + 1
        wat_m = now.strftime("%M")
        arrow = "UP" if d.get("change", 0) >= 0 else "DOWN"
        text = (
            "XAU/USD Spot Price\n"
            "Price: $" + str(d["price"]) + " USD/oz\n"
            "" + arrow + " " + str(d.get("change","")) + " (" + str(d.get("pct","")) + "%)\n"
            "Session: " + get_session() + "\n"
            "Time: " + str(wat_h) + ":" + wat_m + " WAT\n"
            "Source: " + d["source"]
        )
        bot.reply_to(msg, text)
    else:
        bot.reply_to(msg, "Could not fetch price. Check connection.")

@bot.message_handler(commands=["news"])
def news(msg):
    bot.reply_to(msg, "Fetching gold news and running AI analysis...")
    articles = get_gold_news()
    if not articles:
        bot.reply_to(msg, "Could not fetch news right now.")
        return
    headlines = "\n".join([str(i+1) + ". " + a["title"] for i, a in enumerate(articles)])
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"

    prompt = (
        "You are a professional gold market news analyst.\n"
        "Current Gold Price: " + price_str + "\n"
        "Time: " + now_str() + "\n\n"
        "Latest Gold Headlines:\n" + headlines + "\n\n"
        "Analyze these headlines and give:\n\n"
        "GOLD NEWS ANALYSIS\n"
        "Overall News Sentiment: [BULLISH / BEARISH / NEUTRAL]\n\n"
        "KEY THEMES:\n"
        "[3 bullet points on what the news means for gold]\n\n"
        "PRICE IMPACT:\n"
        "Short term (today): [UP/DOWN/SIDEWAYS] - reason\n"
        "Medium term (week): [UP/DOWN/SIDEWAYS] - reason\n\n"
        "TRADING IMPLICATION:\n"
        "[Should traders buy, sell or wait based on news? One clear sentence]\n\n"
        "RISK FACTORS FROM NEWS:\n"
        "[2 key risks to watch]"
    )
    result = ask_groq(prompt)
    headlines_text = "Latest Headlines:\n" + "\n".join([str(i+1)+". "+a["title"] for i,a in enumerate(articles[:4])]) + "\n\n"
    bot.reply_to(msg, headlines_text + result)

@bot.message_handler(commands=["traders"])
def traders(msg):
    bot.reply_to(msg, "Fetching signals from web traders and analysts...")
    signals = get_trader_signals()
    if not signals:
        bot.reply_to(msg, "No trader signals found right now.")
        return
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"
    signals_text = "\n".join([str(i+1)+". "+s for i,s in enumerate(signals)])

    prompt = (
        "You are analyzing signals from multiple gold traders and analysts.\n"
        "Current Gold Price: " + price_str + "\n"
        "Time: " + now_str() + "\n\n"
        "Trader Signals & Headlines from Web:\n" + signals_text + "\n\n"
        "Analyze and summarize:\n\n"
        "WEB TRADER CONSENSUS REPORT\n\n"
        "OVERALL BIAS: [BULLISH / BEARISH / MIXED]\n"
        "Bullish traders: [%] | Bearish traders: [%]\n\n"
        "WHAT TRADERS ARE SAYING:\n"
        "[3 bullet points summarizing the consensus]\n\n"
        "MOST COMMON SIGNAL: [BUY/SELL/WAIT]\n"
        "Most mentioned level: $[level]\n\n"
        "SHOULD YOU FOLLOW? [YES/NO/PARTIALLY] - reason\n\n"
        "BEST TRADE FROM CONSENSUS:\n"
        "Signal: [BUY/SELL]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Target: $[level]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["copytrade"])
def copytrade(msg):
    bot.reply_to(msg, "Analyzing best trade to copy from web traders... Please wait")
    signals = get_trader_signals()
    mtf = get_all_mtf()
    mtf_text = build_mtf_summary(mtf)
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"
    signals_text = "\n".join([str(i+1)+". "+s for i,s in enumerate(signals[:6])])

    prompt = (
        "You are an expert gold copy trading advisor.\n"
        "Current Gold Price: " + price_str + "\n"
        "Time: " + now_str() + "\n"
        "Session: " + get_session() + "\n\n"
        "Market Data (All Timeframes):\n" + mtf_text + "\n"
        "Web Trader Signals:\n" + signals_text + "\n\n"
        "X/Twitter traders being tracked: " + ", ".join(TRACKED_TRADERS) + "\n\n"
        "Based on all data, identify the BEST trade to copy:\n\n"
        "COPY TRADE RECOMMENDATION\n\n"
        "TRADE RATING: [1-10] / 10\n"
        "SIGNAL: [BUY / SELL]\n"
        "Confidence: [%]\n\n"
        "TRADE DETAILS:\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Take Profit 1: $[level]\n"
        "Take Profit 2: $[level]\n"
        "Risk/Reward: 1:[ratio]\n\n"
        "WHY THIS TRADE:\n"
        "[3 reasons based on trader consensus + market data]\n\n"
        "TIMEFRAME AGREEMENT:\n"
        "[Which timeframes confirm this trade]\n\n"
        "RISK WARNING:\n"
        "[One sentence on when to exit if wrong]\n\n"
        "For 0.01 lot: Risk ~$[amount] | Reward ~$[amount]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["myfxbook"])
def myfxbook(msg):
    bot.reply_to(msg, "Fetching Myfxbook style community signals...")
    signals = get_myfxbook_signals()
    trader_signals = get_trader_signals()
    all_signals = signals + trader_signals
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"
    signals_text = "\n".join([str(i+1)+". "+s for i,s in enumerate(all_signals[:6])])

    prompt = (
        "You are a Myfxbook-style community signal aggregator for XAU/USD.\n"
        "Current Gold Price: " + price_str + "\n"
        "Time: " + now_str() + "\n\n"
        "Community Signals Data:\n" + signals_text + "\n\n"
        "Give a Myfxbook-style report:\n\n"
        "COMMUNITY SIGNALS - XAU/USD\n\n"
        "Long: [%] | Short: [%]\n"
        "Community Bias: [LONG/SHORT/NEUTRAL]\n\n"
        "TOP SIGNALS:\n"
        "1. Entry: $[level] | SL: $[level] | TP: $[level] | [BUY/SELL]\n"
        "2. Entry: $[level] | SL: $[level] | TP: $[level] | [BUY/SELL]\n"
        "3. Entry: $[level] | SL: $[level] | TP: $[level] | [BUY/SELL]\n\n"
        "BEST COMMUNITY TRADE:\n"
        "Signal: [BUY/SELL]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Take Profit: $[level]\n"
        "Success Probability: [%]\n\n"
        "VERDICT: [One sentence recommendation]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["structure"])
def structure(msg):
    bot.reply_to(msg, "Analyzing full market structure HTF to LTF... Please wait 20 seconds")
    mtf = get_all_mtf()
    mtf_text = build_mtf_summary(mtf)
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"

    prompt = (
        "You are an elite XAU/USD market structure analyst.\n"
        "Current Price: " + price_str + "\n"
        "Time: " + now_str() + "\n\n"
        "All Timeframe Data:\n" + mtf_text + "\n\n"
        "Perform a complete market structure analysis:\n\n"
        "FULL MARKET STRUCTURE ANALYSIS - XAU/USD\n\n"
        "MACRO STRUCTURE (D1):\n"
        "Trend: [UPTREND/DOWNTREND/RANGING]\n"
        "Last BOS (Break of Structure): $[level] [direction]\n"
        "Last CHoCH (Change of Character): $[level]\n"
        "Key D1 levels: $[resistance] / $[support]\n\n"
        "INTERMEDIATE STRUCTURE (H4):\n"
        "Trend: [direction]\n"
        "Order Blocks: $[bullish OB] / $[bearish OB]\n"
        "Fair Value Gap: $[FVG zone]\n"
        "Key H4 levels: $[resistance] / $[support]\n\n"
        "SHORT TERM STRUCTURE (H1):\n"
        "Trend: [direction]\n"
        "Current momentum: [strong/weak/neutral]\n"
        "Key H1 levels: $[resistance] / $[support]\n\n"
        "ENTRY STRUCTURE (M15/M5/M1):\n"
        "Micro trend: [direction]\n"
        "Best entry zone: $[level]\n"
        "Confirmation needed: [what to look for]\n\n"
        "OVERALL BIAS: [BULLISH/BEARISH/RANGING]\n\n"
        "SMART MONEY CONCEPT:\n"
        "[What is smart money likely doing? Accumulating/Distributing/Hunting stops]\n\n"
        "IDEAL TRADE SETUP:\n"
        "Direction: [BUY/SELL]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level] (below/above structure)\n"
        "Target: $[level] (next key level)\n\n"
        "FINAL VERDICT: [One clear action sentence]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["analyze"])
def analyze(msg):
    bot.reply_to(msg, "Running deep analysis... Please wait 20 seconds")
    mtf = get_all_mtf()
    news = get_gold_news()
    mtf_text = build_mtf_summary(mtf)
    news_text = "\n".join([a["title"] for a in news[:4]])
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"

    prompt = (
        "You are a senior XAU/USD analyst.\n"
        "Price: " + price_str + "\n"
        "Time: " + now_str() + "\n"
        "Session: " + get_session() + "\n\n"
        "Timeframe Data:\n" + mtf_text + "\n"
        "News:\n" + news_text + "\n\n"
        "DEEP ANALYSIS - XAU/USD\n\n"
        "MARKET STRUCTURE:\n"
        "[Overall trend from D1 and H4]\n\n"
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
        "Current: " + price_str + "\n"
        "Minor Support: $[level]\n"
        "Major Support: $[level]\n\n"
        "NEWS IMPACT: [Bullish/Bearish/Neutral]\n"
        "VOLATILITY: [HIGH/NORMAL/LOW]\n\n"
        "BEST SETUP:\n"
        "Bias: [BULLISH/BEARISH/RANGING]\n"
        "Entry: $[level]\n"
        "Stop Loss: $[level]\n"
        "Target: $[level]\n\n"
        "FINAL VERDICT: [One clear action]"
    )
    result = ask_groq(prompt)
    bot.reply_to(msg, result)

@bot.message_handler(commands=["signal"])
def signal(msg):
    bot.reply_to(msg, "Analyzing all timeframes + web signals... Please wait 20 seconds")
    mtf = get_all_mtf()
    signals = get_trader_signals()
    mtf_text = build_mtf_summary(mtf)
    signals_text = "\n".join(signals[:5]) if signals else "None"
    d = get_exact_gold_price()
    price_str = "$" + str(d["price"]) if d else "N/A"

    prompt = (
        "You are a professional XAU/USD gold trader.\n"
        "Price: " + price_str + "\n"
        "Time: " + now_str() + "\n"
        "Session: " + get_session() + "\n\n"
        "Multi-Timeframe Data:\n" + mtf_text + "\n"
        "Web Tra
