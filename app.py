import os
import telebot
from flask import Flask, request, render_template_string
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_ID = 7120801813  # আপনার দেওয়া আইডি এখানে সেট করা হয়েছে

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']

def get_settings():
    settings = settings_col.find_one({"id": "config"})
    if not settings:
        default = {
            "id": "config",
            "bot_name": "সহজ ইনকাম",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "টাকা",
            "min_withdraw": 20.0,
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0
        }
        settings_col.insert_one(default)
        return default
    return settings

# ================= টেলিগ্রাম বট হ্যান্ডলার =================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name
    s = get_settings()
    
    user = users_col.find_one({"user_id": user_id})
    if not user:
        ref_by = None
        if len(message.text.split()) > 1:
            try: ref_by = int(message.text.split()[1])
            except: pass
        
        users_col.insert_one({
            "user_id": user_id, "name": user_name, "balance": 0.0, 
            "clicks": 0, "ref_by": ref_by
        })
        if ref_by and ref_by != user_id:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": s['per_ref']}})
            try: bot.send_message(ref_by, f"🎊 রেফার বোনাস {s['per_ref']} {s['currency']} পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"👋 স্বাগতম {user_name}!\nআয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    # আপনার আইডি চেক করা হচ্ছে
    if message.chat.id == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("⚙️ সেটিংস পরিবর্তন", callback_data="adm_settings"))
        markup.add(telebot.types.InlineKeyboardButton("💸 উইথড্র রিকোয়েস্ট", callback_data="adm_withdraws"))
        markup.add(telebot.types.InlineKeyboardButton("👥 ইউজার লিস্ট", url=f"https://{BASE_URL}/admin/users"))
        bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল**", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ আপনি এই বটের এডমিন নন।")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "adm_settings":
        s = get_settings()
        text = f"⚙️ **বর্তমান সেটিংস:**\nমনিটেজ আইডি: `{s['monetag_id']}`\nক্লিক বোনাস: {s['per_click']}\nরেফার বোনাস: {s['per_ref']}\nমিনিমাম উইথড্র: {s['min_withdraw']}"
        bot.send_message(call.message.chat.id, text)

    elif call.data == "adm_withdraws":
        pending = withdraw_col.find({"status": "pending"})
        if withdraw_col.count_documents({"status": "pending"}) == 0:
            bot.send_message(ADMIN_ID, "❌ পেন্ডিং রিকোয়েস্ট নেই।")
            return
        
        for req in pending:
            m = telebot.types.InlineKeyboardMarkup()
            m.add(telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm_{req['_id']}"),
                  telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{req['_id']}"))
            bot.send_message(ADMIN_ID, f"💰 **রিকোয়েস্ট:**\nID: `{req['user_id']}`\nপরিমাণ: {req['amount']}\nমেথড: {req['method']}", reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment(call):
    data = call.data.split("_")
    action, req_id = data[1], ObjectId(data[2])
    req = withdraw_col.find_one({"_id": req_id})
    if action == "confirm":
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "success"}})
        bot.send_message(req['user_id'], "✅ আপনার পেমেন্ট সফল হয়েছে।")
        bot.edit_message_text("✅ Paid", call.message.chat.id, call.message.message_id)
    else:
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        bot.send_message(req['user_id'], "❌ আপনার পেমেন্ট রিকোয়েস্ট রিজেক্ট করা হয়েছে।")
        bot.edit_message_text("❌ Rejected", call.message.chat.id, call.message.message_id)

# ================= ওয়েব ড্যাশবোর্ড সেকশন =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>ইউজার পাওয়া যায়নি! টেলিগ্রাম থেকে /start দিন।</h1>"
    s = get_settings()
    
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard</title>
        <style>
            body {{ font-family: sans-serif; background: #f4f7f6; margin: 0; text-align: center; }}
            .header {{ background: #007bff; color: white; padding: 30px; border-radius: 0 0 20px 20px; }}
            .balance-card {{ background: white; width: 85%; margin: -30px auto 20px; border-radius: 15px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .menu-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }}
            .menu-item {{ background: white; padding: 20px; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .earn-btn {{ grid-column: span 2; background: #28a745; color: white; }}
        </style>
    </head>
    <body>
        <div class="header"><h1>{s['bot_name']}</h1></div>
        <div class="balance-card">
            <p>আপনার ব্যালেন্স</p>
            <h2 style="color:#28a745;">{user['balance']:.2f} {s['currency']}</h2>
            <small>মোট ক্লিক: {user['clicks']}</small>
        </div>
        <div class="menu-grid">
            <a href="/earn_page/{user_id}" class="menu-item earn-btn">💰 অ্যাড দেখে আয়</a>
            <a href="javascript:alert('ব্যালেন্স: {user['balance']} টাকা')" class="menu-item">📊 ব্যালেন্স</a>
            <a href="javascript:alert('আপনার রেফার লিঙ্ক:\\nhttps://t.me/your_bot_name?start={user_id}')" class="menu-item">👥 রেফার</a>
            <a href="/withdraw_page/{user_id}" class="menu-item">💳 টাকা তুলুন</a>
        </div>
    </body>
    </html>
    """, user=user)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    return render_template_string(f"""
    <body style="text-align:center; padding-top:100px; font-family:sans-serif;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <h2>অ্যাড লোড হচ্ছে...</h2>
        <p>৫ সেকেন্ড পর বাটন আসবে</p>
        <button id="claim" style="display:none; padding:15px 30px; background:green; color:white; border:none; border-radius:5px; font-size:18px;" onclick="location.href='/claim/{user_id}'">💰 টাকা নিন</button>
        <script>
            setTimeout(() => {{ 
                if(typeof show_{s['monetag_id']} === 'function') show_{s['monetag_id']}();
                document.getElementById('claim').style.display='inline-block'; 
            }}, 5000);
        </script>
    </body>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"<h1>সফল! {s['per_click']} টাকা যোগ হয়েছে।</h1><a href='/dashboard/{user_id}'>ফিরে যান</a>"

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    return f"""
    <div style="text-align:center; padding:30px; font-family:sans-serif;">
        <h2>টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: {user['balance']} {s['currency']}</p>
        <form action="/do_withdraw" method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="method" placeholder="বিকাশ/নগদ নাম্বার" required style="padding:10px; width:80%;"><br><br>
            <input type="number" name="amount" placeholder="পরিমাণ" required style="padding:10px; width:80%;"><br><br>
            <button type="submit" style="padding:10px 20px; background:blue; color:white; border:none;">রিকোয়েস্ট পাঠান</button>
        </form>
    </div>
    """

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid, amt, mtd = int(request.form.get('user_id')), float(request.form.get('amount')), request.form.get('method')
    user = users_col.find_one({"user_id": uid})
    s = get_settings()
    if user['balance'] >= amt and amt >= s['min_withdraw']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": mtd, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return "<h1>রিকোয়েস্ট জমা হয়েছে!</h1>"
    return "<h1>ব্যালেন্স কম!</h1>"

# ================= এডমিন ইউজার লিস্ট =================

@app.route('/admin/users')
def admin_users():
    # সরাসরি ব্রাউজারে ইউজার লিস্ট দেখার জন্য
    users = users_col.find()
    html = "<h2>User List</h2><table border='1'><tr><th>ID</th><th>Name</th><th>Balance</th></tr>"
    for u in users:
        html += f"<tr><td>{u['user_id']}</td><td>{u['name']}</td><td>{u['balance']}</td></tr>"
    return html + "</table>"

# ================= ওয়েব হুক =================

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
    return "<h1>Bot is Running!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
