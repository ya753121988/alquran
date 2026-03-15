import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFsWMertAVwnnmCL1KT2i6DbH8vHOJirkk"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

client = MongoClient(MONGO_URI)
db = client['alquran_v5_db']
users_col, settings_col, gateways_col, withdraws_col = db['users'], db['settings'], db['gateways'], db['withdraws']

if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", 
        "monetag_id": "10351894", "monetag_pts": 15, "monetag_status": "on",
        "adexora_id": "38", "adexora_pts": 10, "adexora_status": "on",
        "gigapub_id": "1255", "gigapub_pts": 10, "gigapub_status": "on",
        "currency": "Points"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- ডিজাইন এবং অ্যাড স্ক্রিপ্ট লোডিং ---
USER_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earn Rewards</title>
    
    <!-- সব কোম্পানির অ্যাড স্ক্রিপ্ট আগে লোড করা হচ্ছে -->
    <script src="https://ad.gigapub.tech/script?id={{ config.gigapub_id }}"></script>
    <script src="https://adexora.com/cdn/ads.js?id={{ config.adexora_id }}"></script>
    <script src='https://libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>

    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; text-align: center; }
        .card { background: white; margin: 15px; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .balance { font-size: 40px; font-weight: bold; color: #1abc9c; margin: 10px 0; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer; font-size: 16px; }
        .btn-adexora { background: #27ae60; }
        .btn-gigapub { background: #2980b9; }
        .btn-monetag { background: #8e44ad; }
        .loading { display: none; color: #e67e22; font-weight: bold; margin-bottom: 10px; }
    </style>
</head>
<body>

<div class="card" style="background: #2c3e50; color: white;">
    <p style="margin:0; opacity:0.8;">আপনার ব্যালেন্স</p>
    <div class="balance">{{ user.points }}</div>
    <p style="margin:0;">{{ config.currency }} | ID: {{ user.user_id }}</p>
</div>

<div class="card">
    <div id="status_msg" class="loading">অ্যাড লোড হচ্ছে, দয়া করে অপেক্ষা করুন...</div>
    
    {% if config.adexora_status == 'on' %}
    <button class="btn btn-adexora" onclick="triggerAd('adexora')">🎁 Watch Adexora</button>
    {% endif %}

    {% if config.gigapub_status == 'on' %}
    <button class="btn btn-gigapub" onclick="triggerAd('gigapub')">📺 Watch Gigapub</button>
    {% endif %}

    {% if config.monetag_status == 'on' %}
    <button class="btn btn-monetag" onclick="triggerAd('monetag')">💰 Watch Monetag</button>
    {% endif %}
</div>

<script>
function reward(pts, name) {
    fetch(`/add_pts?id={{ user.user_id }}&amt=${pts}`)
    .then(() => {
        alert("সফল! " + name + " অ্যাড দেখার জন্য পয়েন্ট যোগ হয়েছে।");
        location.reload();
    });
}

function triggerAd(type) {
    const status = document.getElementById('status_msg');
    status.style.display = 'block';

    if(type === 'adexora') {
        if(typeof window.showAdexora === 'function') {
            window.showAdexora().then(() => reward({{ config.adexora_pts }}, 'Adexora'))
            .catch(e => { status.style.display = 'none'; alert("Adexora অ্যাড এখন খালি নেই।"); });
        } else { alert("Adexora স্ক্রিপ্ট এখনো লোড হয়নি। সাইটটি অ্যাপ্রুভ আছে কি না চেক করুন।"); }
    }
    
    else if(type === 'gigapub') {
        if(typeof window.showGiga === 'function') {
            window.showGiga().then(() => reward({{ config.gigapub_pts }}, 'Gigapub'))
            .catch(e => { status.style.display = 'none'; alert("Gigapub অ্যাড এখন খালি নেই।"); });
        } else { alert("Gigapub স্ক্রিপ্ট লোড হয়নি।"); }
    }
    
    else if(type === 'monetag') {
        let mFunc = "show_{{ config.monetag_id }}";
        if(typeof window[mFunc] === 'function') {
            window[mFunc]().then(() => reward({{ config.monetag_pts }}, 'Monetag'))
            .catch(e => { status.style.display = 'none'; alert("Monetag অ্যাড লোড হতে ব্যর্থ হয়েছে।"); });
        } else { alert("Monetag স্ক্রিপ্ট লোড হয়নি। আপনার Zone ID চেক করুন।"); }
    }
}
</script>
</body>
</html>
"""

# --- আগের সব ব্যাকএন্ড রুটস (বিন্দু পরিমাণ মিসিং ছাড়া) ---

@app.route('/')
def home():
    uid = request.args.get('id')
    if not uid: return "বট থেকে ড্যাশবোর্ড ওপেন করুন।"
    user = users_col.find_one({"user_id": int(uid)})
    if not user: return "ইউজার পাওয়া যায়নি।"
    return render_template_string(USER_HTML, user=user, config=settings_col.find_one({"type": "config"}))

@app.route('/admin')
def admin():
    if request.args.get('pass') != ADMIN_PASS: return "Denied", 403
    return "Admin Panel - Under Construction (Use Previous Code for Admin UI)"

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
    return 'ok', 200

@bot.message_handler(commands=['start'])
def start(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}): users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"স্বাগতম {name}!", reply_markup=markup)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
