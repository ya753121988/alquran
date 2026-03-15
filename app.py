from flask import Flask, request, render_template_string, redirect
import telebot
from pymongo import MongoClient

# আপনার দেওয়া তথ্যসমূহ
TOKEN = "8796601390:AAFcVGlEaTvBACE-miekOgLok_VRwQ_HSM4"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"
# আপনার দেওয়া অ্যাড স্ক্রিপ্ট
AD_SCRIPT = "<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>"

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']

# টেলিগ্রাম বটের স্টার্ট কমান্ড
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name
    
    # ইউজার ডাটাবেসে না থাকলে সেভ করা
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0.0, "total_clicks": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    earn_btn = telebot.types.InlineKeyboardButton("💰 অ্যাড দেখে আয় করুন", url=f"https://{BASE_URL}/earn/{user_id}")
    bal_btn = telebot.types.InlineKeyboardButton("📊 ব্যালেন্স চেক", callback_data="check_bal")
    markup.add(earn_btn)
    markup.add(bal_btn)
    
    bot.send_message(user_id, f"আসসালামু আলাইকুম {user_name}!\nনিচের বাটনে ক্লিক করে অ্যাড দেখুন এবং টাকা আয় করুন।", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_bal")
def check_balance(call):
    user = users_col.find_one({"user_id": call.from_user.id})
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, f"👤 ইউজার আইডি: {user['user_id']}\n💰 বর্তমান ব্যালেন্স: {user['balance']:.2f} টাকা\n✅ মোট অ্যাড দেখেছেন: {user['total_clicks']} টি")

# অ্যাড দেখার পেজ
@app.route('/earn/<int:user_id>')
def earn_page(user_id):
    # এই পেজেই আপনার অ্যাড স্ক্রিপ্টটি কাজ করবে
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Watch Ad & Earn</title>
        {AD_SCRIPT}
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; padding-top: 50px; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            .btn {{ background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; border: none; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>অ্যাড লোড হওয়া পর্যন্ত অপেক্ষা করুন</h1>
            <p>সম্পূর্ণ অ্যাডটি দেখা হলে নিচের বাটনে ক্লিক করুন।</p>
            <br><br>
            <form action="/claim" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <button type="submit" class="btn">টাকা সংগ্রহ করুন (Claim Money)</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)

# টাকা যোগ করার রুট
@app.route('/claim', methods=['POST'])
def claim_money():
    user_id = int(request.form.get('user_id'))
    # প্রতি ক্লিকে ১.০০ টাকা করে যোগ হবে (আপনি চাইলে কমাতে বা বাড়াতে পারেন)
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": 1.0, "total_clicks": 1}})
    
    return """
    <div style="text-align:center; padding-top:50px; font-family:Arial;">
        <h1 style="color:green;">অভিনন্দন!</h1>
        <p>আপনার ব্যালেন্সে ১.০০ টাকা যোগ করা হয়েছে।</p>
        <p>এখন এই ট্যাবটি বন্ধ করে টেলিগ্রাম বটে ফিরে যান।</p>
        <a href="tg://resolve?domain=YOUR_BOT_USERNAME" style="text-decoration:none; color:blue;">বটে ফিরে যান</a>
    </div>
    """

# Vercel ও Webhook সেটিংস
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "Bot is Running with Ad Network!", 200

if __name__ == "__main__":
    app.run(debug=True)
