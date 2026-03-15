import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient

# আপনার দেওয়া তথ্যসমূহ
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
AD_SCRIPT = "<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>"

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']

# টেলিগ্রাম বটের স্টার্ট কমান্ড
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0.0, "clicks": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    earn_btn = telebot.types.InlineKeyboardButton("💰 অ্যাড দেখে আয় করুন", url=f"https://{BASE_URL}/earn/{user_id}")
    bal_btn = telebot.types.InlineKeyboardButton("📊 ব্যালেন্স চেক", callback_data="check_bal")
    markup.add(earn_btn)
    markup.add(bal_btn)
    
    bot.send_message(user_id, "স্বাগতম! অ্যাড দেখে আয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_bal")
def check_balance(call):
    user = users_col.find_one({"user_id": call.from_user.id})
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, f"👤 আইডি: {user['user_id']}\n💰 ব্যালেন্স: {user['balance']:.2f} টাকা\n✅ মোট ক্লিক: {user['clicks']}")

# আর্নিং পেজ (এখানে অ্যাড আসবে)
@app.route('/earn/<int:user_id>')
def earn_page(user_id):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Watch Ad</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {AD_SCRIPT}
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; background: #f4f7f6; padding-top: 50px; }}
            .box {{ background: white; padding: 20px; border-radius: 10px; display: inline-block; box-shadow: 0 0 10px rgba(0,0,0,0.1); width: 90%; max-width: 400px; }}
            .btn-show {{ background: #007bff; color: white; padding: 15px 20px; border: none; border-radius: 5px; font-size: 18px; cursor: pointer; }}
            .btn-claim {{ background: #28a745; color: white; padding: 15px 20px; border: none; border-radius: 5px; font-size: 18px; cursor: pointer; display: none; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>অ্যাড দেখে টাকা নিন</h2>
            <p>১. নিচের বাটনে ক্লিক করে অ্যাড দেখুন।<br>২. ৫ সেকেন্ড পর ক্লেম বাটন আসবে।</p>
            
            <button id="adBtn" class="btn-show" onclick="startAd()">১. অ্যাড লোড করুন</button>

            <form action="/claim" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <button type="submit" id="claimBtn" class="btn-claim">২. টাকা সংগ্রহ করুন</button>
            </form>
        </div>

        <script>
            function startAd() {{
                // অ্যাড শো করার ফাংশন (আপনার SDK অনুযায়ী)
                if (typeof show_10351894 === 'function') {{
                    show_10351894();
                }}
                
                // ৫ সেকেন্ড পর ক্লেম বাটন দেখাবে
                setTimeout(function() {{
                    document.getElementById('adBtn').style.display = 'none';
                    document.getElementById('claimBtn').style.display = 'inline-block';
                }}, 5000);
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/claim', methods=['POST'])
def claim():
    user_id = int(request.form.get('user_id'))
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": 0.50, "clicks": 1}})
    return "<h1>সাফল্য! ০.৫০ টাকা যোগ হয়েছে।</h1><p>এখন এটি কেটে দিয়ে বটে ফিরে যান।</p>"

# Webhook Route
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def main():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "Bot is Running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
