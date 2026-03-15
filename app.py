from flask import Flask, request, render_template_string
import telebot
from pymongo import MongoClient
import os

TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
AD_SCRIPT = "<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>"

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# MongoDB Connection with error handling
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['earning_bot_db']
    users_col = db['users']
    client.admin.command('ping') # চেক করার জন্য যে কানেকশন ঠিক আছে কি না
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@app.route('/')
def home():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
        return "Bot is Running! Webhook set successfully."
    except Exception as e:
        return f"Error: {str(e)}"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0.0, "total_clicks": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    earn_btn = telebot.types.InlineKeyboardButton("💰 অ্যাড দেখে আয় করুন", url=f"https://{BASE_URL}/earn/{user_id}")
    bal_btn = telebot.types.InlineKeyboardButton("📊 ব্যালেন্স চেক", callback_data="check_bal")
    markup.add(earn_btn)
    markup.add(bal_btn)
    bot.send_message(user_id, "অ্যাড দেখে আয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_bal")
def check_balance(call):
    user = users_col.find_one({"user_id": call.from_user.id})
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, f"💰 ব্যালেন্স: {user['balance']:.2f} টাকা\n✅ মোট ক্লিক: {user['total_clicks']}")

@app.route('/earn/<int:user_id>')
def earn_page(user_id):
    html = f"""
    <html>
    <head><title>Earn</title>{AD_SCRIPT}</head>
    <body style="text-align:center; padding-top:50px; font-family:sans-serif;">
        <h2>অ্যাডটি দেখুন...</h2>
        <form action="/claim" method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <button type="submit" style="padding:15px; background:green; color:white; border:none; border-radius:5px;">Claim Money</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/claim', methods=['POST'])
def claim():
    user_id = int(request.form.get('user_id'))
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": 1.0, "total_clicks": 1}})
    return "<h1>Success! 1.00 TK added.</h1><p>Close this and back to bot.</p>"

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

if __name__ == "__main__":
    app.run(debug=True)
