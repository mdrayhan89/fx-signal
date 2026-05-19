import os
import json
import time
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# ---- কনফিগারেশন ----
BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"
DB_FILE = "database.json"

# ডাটাবেজ ফাইল চেক ও তৈরি
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

def get_gold_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd").json()
        return res['gold']['usd']
    except: return 0

# =================================================================
# রেন্ডার ওয়েব সার্ভার (লিংকে ঢুকলে চার্ট দেখাবে এবং ট্রেডিংভিউ থেকে ডেটা নেবে)
# =================================================================
class WebServerHandler(BaseHTTPRequestHandler):
    
    # আপনি যখন লিংকে ঢুকবেন (GET), তখন এই ফাংশনটি index.html চার্ট পেজটি লোড করবে
    def do_GET(self):
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error loading dashboard: {e}".encode())

    # ট্রেডিংভিউ অ্যালার্ট ব্যাকগ্রাউন্ডে ডেটা পাঠালে (POST) এই ফাংশনটি কাজ করবে
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        with open(DB_FILE, "r") as f:
            db_data = json.load(f)
            
        if db_data["status"] == "RUNNING":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Locked. Trade is currently running.")
            return

        current_price = get_gold_price()
        if current_price == 0:
            self.send_response(500)
            self.end_headers()
            return

        signal_type = "SELL" if "sell" in post_data.lower() else "BUY"
        timeframe = "5m" if "5m" in post_data.lower() else "3m"

        # ২০ পিপস TP, ৩০ পিপস SL অটো ক্যালকুলেশন
        if signal_type == "BUY":
            tp1, tp2, sl = current_price + 2.0, current_price + 4.0, current_price - 3.0
        else:
            tp1, tp2, sl = current_price - 2.0, current_price - 4.0, current_price + 3.0

        # ডাটাবেজে লক করা
        db_data = {"status": "RUNNING", "type": signal_type, "entry_price": current_price, "tp2": tp2, "sl": sl}
        with open(DB_FILE, "w") as f: json.dump(db_data, f)

        # টেলিগ্রামে সিগন্যাল পাঠানো
        msg = f"🔔 *NEW GOLD SMART MONEY SIGNAL*\n\n" \
              f"📊 Strategy: `SMC Approved`\n" \
              f"⏱ Timeframe: `{timeframe}`\n" \
              f"Direction: `{signal_type}`\n\n" \
              f"Entry Price: ${current_price}\n" \
              f"🎯 TP1: ${tp1}\n" \
              f"🎯 TP2: ${tp2}\n" \
              f"🛑 SL: ${sl}\n\n" \
              f"Owner: {OWNER}"
        send_telegram(msg)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Signal Processed Successfully.")

# অনবরত লাইভ মার্কেট ট্র্যাক করার ব্যাকগ্রাউন্ড লুপ
def track_tp_sl():
    while True:
        try:
            with open(DB_FILE, "r") as f:
                db_data = json.load(f)
                
            if db_data["status"] == "RUNNING":
                current_price = get_gold_price()
                if current_price > 0:
                    tp2, sl, side = db_data["tp2"], db_data["sl"], db_data["type"]
                    
                    if side == "BUY":
                        if current_price >= tp2:
                            send_telegram(f"🎉 *Gold BUY TP2 Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)
                        elif current_price <= sl:
                            send_telegram(f"❌ *Gold BUY SL Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)
                    
                    elif side == "SELL":
                        if current_price <= tp2:
                            send_telegram(f"🎉 *Gold SELL TP2 Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)
                        elif current_price >= sl:
                            send_telegram(f"❌ *Gold SELL SL Hit!*\nPrice: ${current_price}\nOwner: {OWNER}")
                            with open(DB_FILE, "w") as f: json.dump({"status": "READY", "type": "", "entry_price": 0, "tp2": 0, "sl": 0}, f)
        except: pass
        time.sleep(10) # প্রতি ১০ সেকেন্ড পর পর প্রাইস চেক করবে

if __name__ == "__main__":
    threading.Thread(target=track_tp_sl, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), WebServerHandler)
    print(f"Server started on port {port}...")
    server.serve_forever()
