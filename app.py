import os
import telebot
from flask import Flask, request, render_template_string, jsonify
from pymongo import MongoClient

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"

# ডাটাবেস কানেকশন
client = MongoClient(MONGO_URI)
db = client['alquran_db']
users_col = db['users']

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- ওয়েবসাইট ডিজাইন (HTML/JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quran App Dashboard</title>
    
    <!-- Ad Scripts -->
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
    <script src="https://adexora.com/cdn/ads.js?id=38"></script>
    <script src="https://ad.gigapub.tech/script?id=1255"></script>

    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; margin: 0; padding: 0; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px; }
        .user-info { background: white; margin: -30px 20px 20px 20px; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; }
        .balance-box { font-size: 24px; font-weight: bold; color: #27ae60; margin: 10px 0; }
        .ad-container { padding: 20px; }
        .ad-card { background: white; margin-bottom: 15px; padding: 15px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .ad-card img { width: 50px; height: 50px; border-radius: 8px; }
        .ad-details { flex-grow: 1; margin-left: 15px; text-align: left; }
        .ad-details h3 { margin: 0; font-size: 16px; color: #333; }
        .btn-watch { background: #3498db; color: white; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .btn-watch:disabled { background: #ccc; }
    </style>
</head>
<body>

<div class="header">
    <h2>Al-Quran Rewards</h2>
</div>

<div class="user-info">
    <div style="font-size: 14px; color: #7f8c8d;">স্বাগতম, <span id="user_name">ইউজার</span></div>
    <div style="font-size: 12px; color: #bdc3c7;">ID: <span id="user_id">000000</span></div>
    <div class="balance-box">৳ <span id="balance">0.00</span></div>
</div>

<div class="ad-container">
    <!-- Adexora -->
    <div class="ad-card">
        <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_4C-n6-mSiz4r4Kz4yW9Z-6F6F9D-1GkKpg&s" alt="Adexora">
        <div class="ad-details">
            <h3>Adexora Ads</h3>
            <small>Reward: 10 Points</small>
        </div>
        <button class="btn-watch" onclick="watchAdexora()">Watch</button>
    </div>

    <!-- Gigapub -->
    <div class="ad-card">
        <img src="https://ad.gigapub.tech/favicon.ico" alt="Gigapub">
        <div class="ad-details">
            <h3>Gigapub Ads</h3>
            <small>Reward: 10 Points</small>
        </div>
        <button class="btn-watch" onclick="watchGiga()">Watch</button>
    </div>

    <!-- Monetag -->
    <div class="ad-card">
        <img src="https://monetag.com/wp-content/uploads/2022/11/Group-13.png" alt="Monetag">
        <div class="ad-details">
            <h3>Monetag Ads</h3>
            <small>Direct Rewards</small>
        </div>
        <button class="btn-watch" onclick="alert('Wait for Ad to load...')">Watch</button>
    </div>
</div>

<script>
    // URL থেকে ডাটা নেওয়া
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('id');
    const userName = urlParams.get('name');

    if(userId) {
        document.getElementById('user_id').innerText = userId;
        document.getElementById('user_name').innerText = userName || "User";
        fetchBalance();
    }

    function fetchBalance() {
        fetch(`/get_user_data?id=${userId}`)
            .then(res => res.json())
            .then(data => {
                document.getElementById('balance').innerText = data.points;
            });
    }

    function updatePoints(amount) {
        fetch(`/add_points?id=${userId}&amount=${amount}`)
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    alert("Points Added Successfully!");
                    fetchBalance();
                }
            });
    }

    function watchAdexora() {
        window.showAdexora().then(() => { updatePoints(10); }).catch(e => alert("Ad not ready."));
    }

    function watchGiga() {
        window.showGiga().then(() => { updatePoints(10); }).catch(e => alert("Ad error."));
    }
</script>

</body>
</html>
"""

# --- API রুটস ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_user_data')
def get_user_data():
    uid = request.args.get('id')
    user = users_col.find_one({"user_id": int(uid)})
    return jsonify({"points": user['points'] if user else 0})

@app.route('/add_points')
def add_points():
    uid = request.args.get('id')
    amount = int(request.args.get('amount'))
    users_col.update_one({"user_id": int(uid)}, {"$inc": {"points": amount}})
    return jsonify({"success": True})

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

# --- টেলিগ্রাম বট হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    
    # ডাটাবেসে ইউজার সেভ করা
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    
    # ওয়েব অ্যাপ লিংক (ID এবং Name সহ)
    web_link = f"https://{BASE_URL}?id={uid}&name={name}"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ওপেন অ্যাপ", url=web_link))
    
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}!\nআপনার অ্যাকাউন্টে লগইন করা হয়েছে। অ্যাড দেখে আয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
