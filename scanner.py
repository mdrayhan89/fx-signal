import os
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

# টেলিগ্রাম কনফিগারেশন
BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"

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
        print(f"Signal Sent successfully: {action}")
    except Exception as e:
        print(f"Telegram Sending Error: {e}")

# পান্ডাস ছাড়া পিওর পাইথনে ইন্ডিকেটর ম্যাথমেটিক্স (EMA, Highest, Lowest, ATR)
def calculate_ema(data, period):
    ema = []
    k = 2 / (period + 1)
    # প্রথম ভ্যালু সিম্পল অ্যাভারেজ
    current_ema = sum(data[:period]) / period
    ema.append(current_ema)
    for price in data[period:]:
        current_ema = (price * k) + (current_ema * (1 - k))
        ema.append(current_ema)
    # ডেটা লেন্থ ম্যাচ করার জন্য শুরুতে প্যাডিং
    return [0] * (period - 1) + ema

def process_gold_logic(candles):
    if len(candles) < 50:
        return

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]

    # EMA 20 এবং 50 ক্যালকুলেশন
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)

    # ট্রু রেঞ্জ (TR) এবং ATR 14 ক্যালকুলেশন
    tr_list = []
    for i in range(len(candles)):
        if i == 0:
            tr_list.append(highs[i] - lows[i])
        else:
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr_list.append(max(tr1, tr2, tr3))
            
    # ATR rolling window 14
    atr = [0] * len(candles)
    for i in range(13, len(candles)):
        atr[i] = sum(tr_list[i-13:i+1]) / 14

    # নো-রিপেইন্ট লক ইডেক্স (-2 মানে সর্বশেষ ক্লোজড ক্যান্ডেল)
    p = -2
    p_prev = -3

    # হাইয়েস্ট এবং লোয়েস্ট ১০ ক্যান্ডেল উইন্ডো (high_signal[1] এবং low_signal[1] এর জন্য)
    # p-1 ইডেক্স থেকে পেছনের ১০টি ক্যান্ডেল ট্র্যাক করা হচ্ছে
    high_signal_prev = max(highs[p_prev-9:p_prev+1])
    low_signal_prev = min(lows[p_prev-9:p_prev+1])

    # আপনার অরিজিং ইন্ডিকেটরের বাই/সেল শর্তসমূহ
    buy_condition = (ema20[p_prev] <= ema50[p_prev]) and (ema20[p] > ema50[p]) and (closes[p] > high_signal_prev)
    sell_condition = (ema20[p_prev] >= ema50[p_prev]) and (ema20[p] < ema50[p]) and (closes[p] < low_signal_prev)

    if buy_condition:
        entry = high_signal_prev
        sl = entry - (atr[p] * 1.5)
        tp = entry + (atr[p] * 2.0)
        send_telegram_alert("BUY", entry, sl, tp)
        
    elif sell_condition:
        entry = low_signal_prev
        sl = entry + (atr[p] * 1.5)
        tp = entry - (atr[p] * 2.0)
        send_telegram_alert("SELL", entry, sl, tp)

class RenderServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Dashboard Error: {e}".encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            json_data = json.loads(post_data)
            if "candles" in json_data:
                process_gold_logic(json_data["candles"])
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            self.send_response(400)
            self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Lightweight Auto-Scanner Server Live on Port {port}...")
    HTTPServer(('0.0.0.0', port), RenderServerHandler).serve_forever()
