import time
import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---- কনফিগারেশন ----
BOT_TOKEN = "8772565875:AAHyDH-063rlJoEoO5vvrEVnUtRQoTsHIdA"
CHAT_ID = "-1003833319917"
OWNER = "DARK-X-RAYHAN"
DB_FILE = "database.json"

# ডাটাবেজ ইনিশিয়ালাইজেশন
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0}, f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def get_gold_price():
    try:
        res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd").json()
        return res['gold']['usd']
    except: return 0

# ভার্চুয়াল ব্রাউজার সেটআপ (যা ব্যাকগ্রাউন্ডে HTML চার্ট ওপেন রাখবে)
chrome_options = Options()
chrome_options.add_argument("--headless") # পিসি স্ক্রিনে ব্রাউজার দৃশ্যমান হবে না, ব্যাকগ্রাউন্ডে চলবে
chrome_options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=chrome_options)

# আপনার লোকাল বা সার্ভার HTML ফাইলটি ওপেন করা
# (রেন্ডারে হোস্ট করলে রেন্ডারের ইউআরএল লিঙ্কটি এখানে বসবে)
html_path = "file://" + os.path.abspath("index.html")
driver.get(html_path)

print(f"SMC Chart Scanner Engine by {OWNER} is active...")

# অনবরত প্রতি সেকেন্ডে স্ক্যান করার লুপ
while True:
    try:
        with open(DB_FILE, "r") as f:
            db_data = json.load(f)

        current_price = get_gold_price()
        
        # কন্ডিশন ১: যদি কোনো ট্রেড অলরেডি রানিং থাকে (TP/SL ট্র্যাকিং মুড)
        if db_data["status"] == "RUNNING":
            tp1, tp2, sl, side = db_data["tp1"], db_data["tp2"], db_data["sl"], db_data["type"]
            
            if side == "BUY":
                if current_price >= tp2:
                    send_telegram(f"🎉 *Gold BUY TP2 Hit!*\nTarget achieved.\nPrice: ${current_price}\nEngine: {OWNER}")
                    db_data = {"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0}
                elif current_price <= sl:
                    send_telegram(f"❌ *Gold BUY SL Hit!*\nMarket Invalidated.\nPrice: ${current_price}\nEngine: {OWNER}")
                    db_data = {"status": "READY", "type": "", "entry_price": 0, "tp1", 0, "tp2": 0, "sl": 0}
            
            elif side == "SELL":
                if current_price <= tp2:
                    send_telegram(f"🎉 *Gold SELL TP2 Hit!*\nTarget achieved.\nPrice: ${current_price}\nEngine: {OWNER}")
                    db_data = {"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0}
                elif current_price >= sl:
                    send_telegram(f"❌ *Gold SELL SL Hit!*\nMarket Invalidated.\nPrice: ${current_price}\nEngine: {OWNER}")
                    db_data = {"status": "READY", "type": "", "entry_price": 0, "tp1": 0, "tp2": 0, "sl": 0}
            
            with open(DB_FILE, "w") as f: json.dump(db_data, f)

        # কন্ডিশন ২: সিস্টেম ফ্রি থাকলে চার্ট স্ক্যান করা
        elif db_data["status"] == "READY":
            # ব্রাউজারের সোর্স কোড বা DOM স্ক্যান করা (১ সেকেন্ডও মিস হবে না)
            page_source = driver.page_source
            
            signal_detected = False
            signal_type = ""
            timeframe = ""
            strategy = "SMC Setup"

            # [টেকনিক্যাল রিয়েলিটি চেক]: আপনার ইন্ডিকেটর স্ক্রিনে সিগন্যাল দিলে যদি কোনো নির্দিষ্ট টেক্সট বা আইডি 
            # চার্টের ভেতরের HTML-এ জেনারেট হয়, পাইথন সেটা এখান থেকে সেকেন্ডে ধরে ফেলবে।
            # উদাহরণ:
            if "SMC_BUY_ALERT" in page_source:
                signal_detected = True; signal_type = "BUY"; timeframe = "3m"; strategy = "ICT / FVG"
            elif "SMC_SELL_ALERT" in page_source:
                signal_detected = True; signal_type = "SELL"; timeframe = "3m"; strategy = "Order Block"

            if signal_detected and current_price > 0:
                # ২০ পিপস TP, ৩০ পিপস SL ক্যালকুলেশন
                if signal_type == "BUY":
                    tp1, tp2, sl = current_price + 2.0, current_price + 4.0, current_price - 3.0
                else:
                    tp1, tp2, sl = current_price - 2.0, current_price - 4.0, current_price + 3.0

                db_data = {
                    "status": "RUNNING", "type": signal_type, "entry_price": current_price,
                    "tp1": tp1, "tp2": tp2, "sl": sl
                }
                with open(DB_FILE, "w") as f: json.dump(db_data, f)

                # টেলিগ্রামে ইনস্ট্যান্ট মেসেজ পাঠানো
                msg = f"🔔 *NEW GOLD SMART MONEY SIGNAL*\n\n" \
                      f"📊 Strategy: `{strategy}`\n" \
                      f"⏱ Timeframe: `{timeframe}`\n" \
                      f"Direction: `{signal_type}`\n\n" \
                      f"Entry Price: ${current_price}\n" \
                      f"🎯 TP1: ${tp1}\n" \
                      f"🎯 TP2: ${tp2}\n" \
                      f"🛑 SL: ${sl}\n\n" \
                      f"Powered By: {OWNER}"
                send_telegram(msg)

    except Exception as e:
        print(f"Scanning error: {e}")
    
    time.sleep(1) # প্রতি ১ সেকেন্ড পর পর স্ক্যান করবে (জিরো নোটিফিকেশন ডিলে)