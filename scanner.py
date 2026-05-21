import os
import json
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"

# গ্লোবাল লিস্ট সাইটে সিগন্যাল জমা রাখার জন্য
LIVE_SIGNALS_CACHE = []

def send_telegram_alert(action, entry, sl, tp):
    status_emoji = "🟢" if action == "BUY" else "🔴"
    message = (
        f"{status_emoji} *NEW GOLD PRECISION SIGNAL*\n\n"
        f"📊 *Direction:* `{action}`\n"
        f"⚡ *Exact Entry Price:* ${entry:.2f}\n"
        f"🎯 *Target TP:* ${tp:.2f}\n"
        f"🛑 *Stop Loss:* ${sl:.2f}\n\n"
        f"👤 *Developer:* {OWNER}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Telegram Notification Error: {e}")

def calculate_ema(prices, period):
    if len(prices) < period: return [0] * len(prices)
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price * k) + (ema[-1] * (1 - k)))
    return [0] * (period - 1) + ema

def check_indicators(candles):
    global LIVE_SIGNALS_CACHE
    if len(candles) < 20: return
    
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    
    tr = []
    for i in range(len(candles)):
        if i == 0: tr.append(highs[i] - lows[i])
        else: tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = [0] * len(candles)
    for i in range(13, len(candles)): atr[i] = sum(tr[i-13:i+1]) / 14

    p = -2 # নো-রিপেইন্ট ক্যান্ডেল ইডেক্স
    
    high_signal_prev = max(highs[p-10:p])
    low_signal_prev = min(lows[p-10:p])
    
    buy_trigger = (ema20[p-1] <= ema50[p-1]) and (ema20[p] > ema50[p]) and (closes[p] > high_signal_prev)
    sell_trigger = (ema20[p-1] >= ema50[p-1]) and (ema20[p] < ema50[p]) and (closes[p] < low_signal_prev)
    
    if buy_trigger or sell_trigger:
        action = "BUY" if buy_trigger else "SELL"
        entry = closes[p]
        sl = entry - (atr[p] * 1.5) if buy_trigger else entry + (atr[p] * 1.5)
        tp = entry + (atr[p] * 2.0) if buy_trigger else entry - (atr[p] * 2.0)
        
        # টেলিগ্রামে সিগন্যাল পাঠানো
        send_telegram_alert(action, entry, sl, tp)
        
        # সাইটের ড্যাশবোর্ডে পুশ করা
        new_sig = {
            "action": action,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "time": datetime.now().strftime("%I:%M %p")
        }
        LIVE_SIGNALS_CACHE.insert(0, new_sig) # লেটেস্ট সিগন্যাল সবার উপরে থাকবে
        if len(LIVE_SIGNALS_CACHE) > 10: LIVE_SIGNALS_CACHE.pop()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global LIVE_SIGNALS_CACHE
        if self.path == '/get-signals':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(LIVE_SIGNALS_CACHE).encode("utf-8"))
        else:
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            except:
                self.send_response(500)
                self.end_headers()

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(length).decode('utf-8'))
        if "candles" in data: check_indicators(data["candles"])
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
