import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient

# আপনার দেওয়া তথ্যসমূহ
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
AD_SCRIPT = "<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>"
ADMIN_ID = 8796601390  # আপনার নিজের টেলিগ্রাম আইডি এখানে দিন (উইথড্র রিকোয়েস্ট পাওয়ার জন্য)

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# MongoDB কানেকশন
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']

# মেইন মেনু রিপ্লাই মার্কআপ (সহজে ব্যবহারের জন্য)
def main_menu():
    markup = telebot.types.InlineKeyboardMarkup()
    earn_btn = telebot.types.InlineKeyboardButton("💰 অ্যাড দেখে আয়", url=f"https://{BASE_URL}/earn/")
    bal_btn = telebot.types.InlineKeyboardButton("📊 ব্যালেন্স", callback_data="check_bal")
    ref_btn = telebot.types.InlineKeyboardButton("👥 রেফার করুন", callback_data="referral")
    withdraw_btn = telebot.types.InlineKeyboardButton("💳 টাকা তুলুন", callback_data="withdraw")
    markup.row(earn_btn)
    markup.row(bal_btn, ref_btn)
    markup.row(withdraw_btn)
    return markup

# টেলিগ্রাম বটের স্টার্ট কমান্ড
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user = users_col.find_one({"user_id": user_id})
    
    # রেফারেল চেক
    ref_by = None
    if len(message.text.split()) > 1:
        ref_by = message.text.split()[1]
        if ref_by.isdigit():
            ref_by = int(ref_by)

    if not user:
        new_user = {"user_id": user_id, "balance": 0.0, "clicks": 0, "referred_by": ref_by}
        users_col.insert_one(new_user)
        
        # রেফারারকে বোনাস দেওয়া (যেমন: ১ টাকা)
        if ref_by and ref_by != user_id:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": 1.0}})
            try:
                bot.send_message(ref_by, f"🎊 আপনার লিঙ্কে একজন জয়েন করেছে! আপনি ১.০০ টাকা রেফার বোনাস পেয়েছেন।")
            except:
                pass
    
    bot.send_message(user_id, "👋 স্বাগতম! অ্যাড দেখে আয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=main_menu())

# সব কলব্যাক হ্যান্ডলার (বাটন ক্লিক)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user = users_col.find_one({"user_id": user_id})

    if call.data == "check_bal":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, f"👤 আইডি: {user['user_id']}\n💰 ব্যালেন্স: {user['balance']:.2f} টাকা\n✅ মোট ক্লিক: {user['clicks']}")

    elif call.data == "referral":
        bot.answer_callback_query(call.id)
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        msg = f"👥 আপনার রেফারেল লিঙ্ক:\n{ref_link}\n\nপ্রতি রেফারে পাবেন ১.০০ টাকা বোনাস!"
        bot.send_message(user_id, msg)

    elif call.data == "withdraw":
        bot.answer_callback_query(call.id)
        if user['balance'] < 20.0:
            bot.send_message(user_id, "⚠️ আপনার ব্যালেন্স ২০ টাকার কম। টাকা তুলতে অন্তত ২০ টাকা প্রয়োজন।")
        else:
            msg = bot.send_message(user_id, "আপনার বিকাশ/নগদ নাম্বার এবং কত টাকা তুলতে চান লিখে পাঠান।\nউদাহরণ: 01710XXXXXX - 50 TK")
            bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    user_id = message.chat.id
    details = message.text
    user = users_col.find_one({"user_id": user_id})
    
    if user['balance'] >= 20.0:
        # এডমিনকে জানানো
        bot.send_message(ADMIN_ID, f"🔔 **নতুন উইথড্র রিকোয়েস্ট!**\n\nইউজার আইডি: `{user_id}`\nবিস্তারিত: {details}\nব্যালেন্স: {user['balance']} টাকা")
        bot.send_message(user_id, "✅ আপনার রিকোয়েস্ট এডমিনের কাছে পাঠানো হয়েছে। ২৪ ঘন্টার মধ্যে পেমেন্ট পাবেন।")
    else:
        bot.send_message(user_id, "❌ পর্যাপ্ত ব্যালেন্স নেই।")

# আর্নিং পেজ (অ্যাড দেখার জন্য)
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
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background: #f0f2f5; padding-top: 50px; }}
            .box {{ background: white; padding: 30px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 85%; max-width: 400px; }}
            .btn-show {{ background: #007bff; color: white; padding: 15px 25px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; transition: 0.3s; }}
            .btn-claim {{ background: #28a745; color: white; padding: 15px 25px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; display: none; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>💰 অ্যাড দেখে টাকা নিন</h2>
            <p>নিচের বাটনে ক্লিক করে অ্যাড দেখুন। ৫ সেকেন্ড পর ক্লেম বাটন আসবে।</p>
            
            <button id="adBtn" class="btn-show" onclick="startAd()">১. অ্যাড দেখুন</button>

            <form action="/claim" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <button type="submit" id="claimBtn" class="btn-claim">২. টাকা সংগ্রহ করুন</button>
            </form>
        </div>

        <script>
            function startAd() {{
                if (typeof show_10351894 === 'function') {{
                    show_10351894();
                }}
                
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
    return "<h1>✅ ০.৫০ টাকা সফলভাবে যোগ হয়েছে!</h1><p>এখন এই পেজটি কেটে দিয়ে টেলিগ্রাম বটে ফিরে যান।</p>"

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
    return "Bot is Running Successfully!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
