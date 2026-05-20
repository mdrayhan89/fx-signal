import os
import json
import requests
import pandas as pd
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"

def send_telegram_alert(action, entry, sl, tp):
    status_emoji = "🟢" if action == "BUY" else "🔴"
    message = (
        f"{status_emoji} *NEW GOLD PRECISION SIGNAL*\n\n"
        f"📊 *Direction:* `{action}`\n"
        f"⚡ *Entry Price:* ${entry:.2f}\n"
        f"🎯 *Target TP:* ${tp:.2f}\n"
        f"🛑 *Stop Loss:* ${sl:.2f}\n\n"
        f"👤 *Developer:* {OWNER}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Telegram automation error: {e}")

# আপনার মূল ফাইলের লজিক একটুও না পরিবর্তন করে পাইথনে রূপান্তর করা হলো
def run_gold_indicator_logic(df):
    if len(df) < 50:
        return
    
    # আপনার মূল ইনপুট সেটিংস ও লজিক
    df['ema_fast'] = df['close'].ewm(span=20, adjust=False).mean() # ta.ema(close, 20)
    df['ema_slow'] = df['close'].ewm(span=50, adjust=False).mean() # ta.ema(close, 50)
    df['high_signal'] = df['high'].rolling(window=10).max()        # ta.highest(high, 10)
    df['low_signal'] = df['low'].rolling(window=10).min()          # ta.lowest(low, 10)
    
    # ATR 14 ক্যালকুলেশন
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift(1)).abs()
    low_cp = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    # নো-রিপেইন্ট লক করার জন্য লাস্ট ক্লোজড ক্যান্ডেল ইনডেক্স (-2)
    p = -2
    
    # আপনার অরিজিনাল বাই এবং সেল কন্ডিশন
    buy_condition = (df['ema_fast'].iloc[p-1] <= df['ema_slow'].iloc[p-1]) and \
                    (df['ema_fast'].iloc[p] > df['ema_slow'].iloc[p]) and \
                    (df['close'].iloc[p] > df['high_signal'].iloc[p-1])
                    
    sell_condition = (df['ema_fast'].iloc[p-1] >= df['ema_slow'].iloc[p-1]) and \
                     (df['ema_fast'].iloc[p] < df['ema_slow'].iloc[p]) and \
                     (df['close'].iloc[p] < df['low_signal'].iloc[p-1])
                     
    if buy_condition:
        entry = df['close'].iloc[p]
        sl = entry - (df['atr'].iloc[p] * 1.5) # slMultiplier = 1.5
        tp = entry + (df['atr'].iloc[p] * 2.0) # tpMultiplier = 2.0
        send_telegram_alert("BUY", entry, sl, tp)
        
    elif sell_condition:
        entry = df['close'].iloc[p]
        sl = entry + (df['atr'].iloc[p] * 1.5) # slMultiplier = 1.5
        tp = entry - (df['atr'].iloc[p] * 2.0) # tpMultiplier = 2.0
        send_telegram_alert("SELL", entry, sl, tp)

class RenderServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_data = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_data.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def do_POST(self):
        # আপনার লাইভ ডাটা সোর্স (যেমন MT4/MT5 বা API) থেকে ক্যান্ডেল ডেটা রিসিভ করার জায়গা
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            json_data = json.loads(post_data)
            if "candles" in json_data:
                df = pd.DataFrame(json_data["candles"])
                run_gold_indicator_logic(df)
            self.send_response(200)
            self.end_headers()
        except:
            self.send_response(400)
            self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), RenderServerHandler).serve_forever()
