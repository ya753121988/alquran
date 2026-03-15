import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- কনফিগারেশন ---
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_ID = 7120801813 # আপনার নিজের টেলিগ্রাম আইডি এখানে দিন

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- MongoDB কানেকশন ---
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']

# --- ডিফল্ট সেটিংস চেক ---
def get_settings():
    settings = settings_col.find_one({"id": "config"})
    if not settings:
        default_settings = {
            "id": "config",
            "bot_name": "Earning Bot",
            "logo": "https://via.placeholder.com/150",
            "currency": "BDT",
            "min_withdraw": 20.0,
            "max_withdraw": 500.0,
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0,
            "menu_earn": "💰 অ্যাড দেখে আয়",
            "menu_bal": "📊 ব্যালেন্স",
            "menu_ref": "👥 রেফার করুন",
            "menu_wit": "💳 টাকা তুলুন"
        }
        settings_col.insert_one(default_settings)
        return default_settings
    return settings

# --- কিবোর্ড জেনারেটর ---
def main_menu():
    s = get_settings()
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(s['menu_earn'], s['menu_bal'])
    markup.row(s['menu_ref'], s['menu_wit'])
    if True: # Admin check logic here if needed
        pass 
    return markup

# --- টেলিগ্রাম বট হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name
    s = get_settings()
    
    user = users_col.find_one({"user_id": user_id})
    if not user:
        # রেফারেল চেক
        ref_by = None
        if len(message.text.split()) > 1:
            ref_id = message.text.split()[1]
            if ref_id.isdigit(): ref_by = int(ref_id)
        
        users_col.insert_one({
            "user_id": user_id, "name": user_name, "balance": 0.0, 
            "clicks": 0, "ref_by": ref_by
        })
        
        if ref_by:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": s['per_ref']}})
            bot.send_message(ref_by, f"🎊 নতুন রেফারাল! আপনি {s['per_ref']} {s['currency']} পেয়েছেন।")

    bot.send_photo(user_id, s['logo'], caption=f"স্বাগতম {user_name}!\nআমাদের **{s['bot_name']}** এ আপনি অ্যাড দেখে আয় করতে পারবেন।", reply_markup=main_menu())

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⚙️ সেটিংস পরিবর্তন", callback_data="adm_settings"))
    markup.add(telebot.types.InlineKeyboardButton("👥 ইউজার ম্যানেজ", callback_data="adm_users"))
    markup.add(telebot.types.InlineKeyboardButton("💸 উইথড্র রিকোয়েস্ট", callback_data="adm_withdraws"))
    bot.send_message(message.chat.id, "🛠 এডমিন প্যানেল", reply_markup=markup)

# --- এডমিন সেটিংস হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "adm_settings":
        s = get_settings()
        text = f"🤖 নাম: {s['bot_name']}\n💰 কারেন্সি: {s['currency']}\n🎯 Monetag ID: {s['monetag_id']}\n💳 Min: {s['min_withdraw']} | Max: {s['max_withdraw']}"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("নাম পরিবর্তন", callback_data="edit_bot_name"))
        markup.add(telebot.types.InlineKeyboardButton("Monetag ID পরিবর্তন", callback_data="edit_monetag"))
        markup.add(telebot.types.InlineKeyboardButton("মিনিমাম উইথড্র", callback_data="edit_min"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "adm_withdraws":
        pending = withdraw_col.find({"status": "pending"})
        if withdraw_col.count_documents({"status": "pending"}) == 0:
            bot.answer_callback_query(call.id, "কোন রিকোয়েস্ট নেই।")
            return
        for req in pending:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm_{req['_id']}"),
                telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{req['_id']}")
            )
            bot.send_message(ADMIN_ID, f"💰 **উইথড্র রিকোয়েস্ট**\nইউজার: {req['user_id']}\nপরিমাণ: {req['amount']}\nমেথড: {req['method']}", reply_markup=markup)

# --- পেমেন্ট কনফার্ম/রিজেক্ট ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment(call):
    action = call.data.split("_")[1]
    req_id = ObjectId(call.data.split("_")[2])
    req = withdraw_col.find_one({"_id": req_id})
    
    if action == "confirm":
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "success"}})
        bot.send_message(req['user_id'], "✅ আপনার পেমেন্ট সফলভাবে পাঠানো হয়েছে।")
    else:
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        bot.send_message(req['user_id'], "❌ আপনার পেমেন্ট রিজেক্ট করা হয়েছে এবং ব্যালেন্স ফেরত দেওয়া হয়েছে।")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- ইউজার বাটন হ্যান্ডলার ---
@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    s = get_settings()
    user_id = message.chat.id
    user = users_col.find_one({"user_id": user_id})

    if message.text == s['menu_earn']:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔗 ওপেন আর্নিং পেজ", url=f"https://{BASE_URL}/earn/{user_id}"))
        bot.send_message(user_id, "নিচের লিঙ্কে ক্লিক করে অ্যাড দেখুন:", reply_markup=markup)

    elif message.text == s['menu_bal']:
        bot.send_message(user_id, f"👤 নাম: {user['name']}\n💰 ব্যালেন্স: {user['balance']:.2f} {s['currency']}\n✅ ক্লিক: {user['clicks']}")

    elif message.text == s['menu_ref']:
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={user_id}"
        bot.send_message(user_id, f"👥 প্রতি রেফারে পাবেন {s['per_ref']} {s['currency']}\n\nআপনার লিঙ্ক: {link}")

    elif message.text == s['menu_wit']:
        if user['balance'] < s['min_withdraw']:
            bot.send_message(user_id, f"⚠️ মিনিমাম উইথড্র {s['min_withdraw']} {s['currency']}")
        else:
            msg = bot.send_message(user_id, "আপনার নাম্বার ও পেমেন্ট মেথড লিখুন (যেমন: 017xx... Bikash):")
            bot.register_next_step_handler(msg, process_wit_req, user['balance'])

def process_wit_req(message, amount):
    user_id = message.chat.id
    method = message.text
    withdraw_col.insert_one({
        "user_id": user_id, "amount": amount, "method": method, "status": "pending"
    })
    users_col.update_one({"user_id": user_id}, {"$set": {"balance": 0.0}})
    bot.send_message(user_id, "✅ আপনার উইথড্র রিকোয়েস্ট জমা হয়েছে।")

# --- Flask Routes (Web) ---
@app.route('/earn/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    html = f"""
    <html>
    <head>
        <title>Watch Ad</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <style>
            body {{ font-family: sans-serif; text-align: center; padding-top: 50px; background: #f4f4f4; }}
            .box {{ background: white; padding: 20px; border-radius: 10px; display: inline-block; width: 80%; box-shadow: 0 0 10px #ccc; }}
            .btn {{ background: #28a745; color: white; padding: 15px; border: none; border-radius: 5px; font-size: 18px; cursor: pointer; display:none; }}
            .loader {{ font-size: 18px; color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>Ad Loading...</h2>
            <p id="timer">অ্যাডটি লোড হচ্ছে, ৫ সেকেন্ড অপেক্ষা করুন...</p>
            <button id="claimBtn" class="btn" onclick="document.getElementById('claimForm').submit()">💰 টাকা সংগ্রহ করুন</button>
            <form id="claimForm" action="/claim" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
            </form>
        </div>
        <script>
            setTimeout(function() {{
                if (typeof show_{s['monetag_id']} === 'function') {{ show_{s['monetag_id']}(); }}
                document.getElementById('timer').style.display = 'none';
                document.getElementById('claimBtn').style.display = 'block';
            }}, 5000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/claim', methods=['POST'])
def claim():
    user_id = int(request.form.get('user_id'))
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"<h1>সাফল্য! {s['per_click']} {s['currency']} যোগ হয়েছে।</h1>"

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
