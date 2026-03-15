import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient

# --- কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
ADMIN_PASS = "admin123"

# ডাটাবেস সেটআপ
client = MongoClient(MONGO_URI)
db = client['quran_app']
users_col = db['users']

# বট সেটআপ
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- HTML টেমপ্লেট (আপনার দেওয়া অ্যাড স্ক্রিপ্টসহ) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quran App - Watch Ads</title>
    
    <!-- Monetag SDK -->
    <script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
    
    <!-- Adexora SDK -->
    <script src="https://adexora.com/cdn/ads.js?id=38"></script>

    <!-- Gigapub SDK -->
    <script src="https://ad.gigapub.tech/script?id=1255"></script>

    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #f0f2f5; padding: 20px; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }
        h2 { color: #333; }
        .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; transition: 0.3s; color: white; }
        .btn-adexora { background-color: #00b894; }
        .btn-giga { background-color: #0984e3; }
        .btn-monetag { background-color: #6c5ce7; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Watch & Earn</h2>
        <p>অ্যাড দেখুন এবং রিওয়ার্ড সংগ্রহ করুন</p>
        
        <button class="btn btn-adexora" onclick="showAdexoraAd()">Watch Adexora</button>
        <button class="btn btn-giga" onclick="showGigaAd()">Watch Gigapub</button>
        <button class="btn btn-monetag" onclick="showMonetagAd()">Watch Monetag</button>
    </div>

    <script>
        function showAdexoraAd() {
            window.showAdexora().then(() => {
                alert("Success! Points added for Adexora.");
            }).catch(e => alert("Ad failed!"));
        }

        function showGigaAd() {
            window.showGiga().then(() => {
                alert("Success! Points added for Gigapub.");
            }).catch(e => alert("Ad failed!"));
        }

        function showMonetagAd() {
            // Monetag usually auto-shows or triggers via zone
            alert("Showing Monetag Ad...");
        }
    </script>
</body>
</html>
"""

# --- ফ্ল্যাস্ক রুটস (Web Logic) ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# --- টেলিগ্রাম বট কমান্ডস ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    # ডাটাবেসে ইউজার চেক বা সেভ করা
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "points": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    web_app_url = "https://your-vercel-app-name.vercel.app" # এখানে আপনার আসল ইউআরএল দিন
    btn = telebot.types.InlineKeyboardButton("Open Web App", url=web_app_url)
    markup.add(btn)
    
    bot.reply_to(message, "আসসালামু আলাইকুম! কুরআন অ্যাপে স্বাগতম। অ্যাড দেখতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(commands=['balance'])
def balance(message):
    user = users_col.find_one({"user_id": message.from_user.id})
    points = user['points'] if user else 0
    bot.reply_to(message, f"আপনার বর্তমান ব্যালেন্স: {points} পয়েন্ট।")

# --- মেইন ফাংশন ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
