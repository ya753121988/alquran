import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# ডাটাবেস সেটআপ
client = MongoClient(MONGO_URI)
db = client['alquran_db']
users_col = db['users']

# বট এবং ফ্ল্যাস্ক সেটআপ
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- ওয়েবসাইট ডিজাইন (HTML/JS) ---
# এখানে আপনার দেওয়া Monetag, Adexora এবং Gigapub স্ক্রিপ্টগুলো যুক্ত করা হয়েছে।
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quran App - Earn Rewards</title>
    
    <!-- Monetag SDK -->
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
    
    <!-- Adexora SDK -->
    <script src="https://adexora.com/cdn/ads.js?id=38"></script>

    <!-- Gigapub SDK -->
    <script src="https://ad.gigapub.tech/script?id=1255"></script>

    <style>
        body { font-family: 'Arial', sans-serif; background: #eef2f3; text-align: center; padding: 20px; }
        .container { background: white; max-width: 400px; margin: auto; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; font-size: 22px; }
        .ad-btn { display: block; width: 90%; margin: 15px auto; padding: 15px; border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.3s; }
        .btn-adexora { background: #27ae60; }
        .btn-giga { background: #2980b9; }
        .btn-monetag { background: #8e44ad; }
        .ad-btn:hover { opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Watch Ads & Support Us</h1>
        <p>নিচের বাটনে ক্লিক করে অ্যাড দেখুন</p>

        <button class="btn-adexora ad-btn" onclick="openAdexora()">Watch Adexora Ad</button>
        <button class="btn-giga ad-btn" onclick="openGiga()">Watch Gigapub Ad</button>
        <button class="btn-monetag ad-btn" onclick="alert('Monetag is loading...')">Check Rewards</button>
        
        <p style="font-size: 12px; color: gray;">Admin Pass Required for Dashboard</p>
    </div>

    <script>
        function openAdexora() {
            window.showAdexora().then(() => {
                alert("ধন্যবাদ! আপনি অ্যাডটি দেখেছেন।");
            }).catch(e => alert("Ad error. Try again!"));
        }

        function openGiga() {
            window.showGiga().then(() => {
                alert("সফল! পয়েন্ট যুক্ত করা হয়েছে।");
            }).catch(e => alert("Ad loading failed."));
        }
    </script>
</body>
</html>
"""

# --- ফ্ল্যাস্ক রুটস ---

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

# --- টেলিগ্রাম বট হ্যান্ডলারস ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    # ডাটাবেসে ইউজার সেভ করা
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "points": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    web_link = telebot.types.InlineKeyboardButton("Watch Ads", url=f"https://{BASE_URL}")
    markup.add(web_link)
    
    bot.reply_to(message, "আসসালামু আলাইকুম! কুরআন অ্যাপে আপনাকে স্বাগতম। অ্যাড দেখতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_login(message):
    msg = bot.send_message(message.chat.id, "অ্যাডমিন পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(msg, check_admin_pass)

def check_admin_pass(message):
    if message.text == ADMIN_PASS:
        total_users = users_col.count_documents({})
        bot.send_message(message.chat.id, f"লগইন সফল! মোট ইউজার: {total_users}")
    else:
        bot.send_message(message.chat.id, "ভুল পাসওয়ার্ড!")

# --- Vercel এর জন্য প্রয়োজনীয় ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
