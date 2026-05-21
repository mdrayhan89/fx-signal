import os
import json
import requests
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"

CHART_CANDLES = []
CHART_MARKERS = []
LIVE_SIGNALS_CACHE = []

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
        print(f"Telegram Error: {e}")

def calculate_ema(prices, period):
    if len(prices) < period: return [0] * len(prices)
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price * k) + (ema[-1] * (1 - k)))
    return [0] * (period - 1) + ema

def run_ai_indicator_engine():
    global CHART_CANDLES, CHART_MARKERS, LIVE_SIGNALS_CACHE
    last_processed_time = None
    
    while True:
        try:
            # Binance API থেকে গোল্ড লাইভ ডাটা নেওয়া
            url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=3m&limit=100"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                raw_data = response.json()
                
                candles = []
                for c in raw_data:
                    candles.append({
                        "time": int(c[0] / 1000), # Unix timestamp format
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4])
                    })
                
                CHART_CANDLES = candles
                current_candle_time = candles[-1]["time"]
                
                if last_processed_time != current_candle_time:
                    closes = [c['close'] for c in candles]
                    highs = [c['high'] for c in candles]
                    lows = [c['low'] for c in candles]
                    
                    ema20 = calculate_ema(closes, 20)
                    ema50 = calculate_ema(closes, 50)
                    
                    # ATR লজিক
                    tr = []
                    for i in range(len(candles)):
                        if i == 0: tr.append(highs[i] - lows[i])
                        else: tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
                    atr = [0] * len(candles)
                    for i in range(13, len(candles)): atr[i] = sum(tr[i-13:i+1]) / 14

                    p = -2 # Confirmed Candle
                    
                    high_signal_prev = max(highs[p-10:p])
                    low_signal_prev = min(lows[p-10:p])
                    
                    buy_trigger = (ema20[p-1] <= ema50[p-1]) and (ema20[p] > ema50[p]) and (closes[p] > high_signal_prev)
                    sell_trigger = (ema20[p-1] >= ema50[p-1]) and (ema20[p] < ema50[p]) and (closes[p] < low_signal_prev)
                    
                    if buy_trigger or sell_trigger:
                        action = "BUY" if buy_trigger else "SELL"
                        entry = closes[p]
                        sl = entry - (atr[p] * 1.5) if buy_trigger else entry + (atr[p] * 1.5)
                        tp = entry + (atr[p] * 2.0) if buy_trigger else entry - (atr[p] * 2.0)
                        
                        # টেলিগ্রামে ইনস্ট্যান্ট অ্যালার্ট পাঠানো
                        send_telegram_alert(action, entry, sl, tp)
                        
                        # চার্টের ক্যান্ডেলের নিচে/ওপরে মার্কার তৈরি (হুবহু TradingView স্টাইল)
                        marker = {
                            "time": candles[p]["time"],
                            "position": "aboveBar" if action == "SELL" else "belowBar",
                            "color": "#ef5350" if action == "SELL" else "#26a69a",
                            "shape": "arrowDown" if action == "SELL" else "arrowUp",
                            "text": f"GOLD {action}\\nEntry: ${entry:.2f}\\nSL: ${sl:.2f}\\nTP: ${tp:.2f}"
                        }
                        CHART_MARKERS.append(marker)
                        
                        new_sig = {
                            "action": action, "entry": entry, "sl": sl, "tp": tp,
                            "time": datetime.now().strftime("%I:%M %p")
                        }
                        LIVE_SIGNALS_CACHE.insert(0, new_sig)
                        if len(LIVE_SIGNALS_CACHE) > 10: LIVE_SIGNALS_CACHE.pop()
                    
                    last_processed_time = current_candle_time
        except Exception as e:
            print(f"Data Feed Error: {e}")
        time.sleep(10)

class ServerEngine(BaseHTTPRequestHandler):
    def do_GET(self):
        global CHART_CANDLES, CHART_MARKERS, LIVE_SIGNALS_CACHE
        if self.path == '/get-market-data':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            # CORS পলিসি অন করা যাতে ব্রাউজার ডাটা ব্লক না করে
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            payload = {
                "candles": CHART_CANDLES,
                "markers": CHART_MARKERS,
                "signals": LIVE_SIGNALS_CACHE
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except:
                self.send_response(500)
                self.end_headers()

if __name__ == "__main__":
    threading.Thread(target=run_ai_indicator_engine, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), ServerEngine).serve_forever()
