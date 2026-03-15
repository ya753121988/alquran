import os
import telebot
from flask import Flask, request, render_template_string, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_ID = 6363236087  # আপনার টেলিগ্রাম আইডি

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']

# ডিফল্ট সেটিংস লোড করা
def get_settings():
    settings = settings_col.find_one({"id": "config"})
    if not settings:
        default = {
            "id": "config",
            "bot_name": "সহজ ইনকাম",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "টাকা",
            "min_withdraw": 20.0,
            "max_withdraw": 5000.0,
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
        # রেফারেল চেক
        ref_by = None
        if len(message.text.split()) > 1:
            try:
                ref_by = int(message.text.split()[1])
            except:
                pass
        
        users_col.insert_one({
            "user_id": user_id, "name": user_name, "balance": 0.0, 
            "clicks": 0, "ref_by": ref_by
        })
        
        if ref_by and ref_by != user_id:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": s['per_ref']}})
            try: bot.send_message(ref_by, f"🎊 নতুন রেফারাল! আপনি {s['per_ref']} {s['currency']} বোনাস পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"👋 স্বাগতম {user_name}!\nআমাদের {s['bot_name']} এ অ্যাড দেখে আয় করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⚙️ সেটিংস পরিবর্তন", callback_data="adm_settings"))
    markup.add(telebot.types.InlineKeyboardButton("💸 উইথড্র রিকোয়েস্ট", callback_data="adm_withdraws"))
    markup.add(telebot.types.InlineKeyboardButton("👥 ইউজার ডাটা (ব্রাউজার)", url=f"https://{BASE_URL}/admin/users"))
    bot.send_message(message.chat.id, "🛠 **এডমিন কন্ট্রোল প্যানেল**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "adm_settings":
        s = get_settings()
        text = f"⚙️ **সেটিংস:**\n\nনাম: {s['bot_name']}\nকারেন্সি: {s['currency']}\nমনিটেজ আইডি: {s['monetag_id']}\nক্লিক বোনাস: {s['per_click']}\nরেফার বোনাস: {s['per_ref']}\nমিনিমাম উইথড্র: {s['min_withdraw']}"
        bot.send_message(call.message.chat.id, text + "\n\n*(সেটিংস পরিবর্তন করতে ডাটাবেস বা নতুন কমান্ড ব্যবহার করুন)*")

    elif call.data == "adm_withdraws":
        pending = withdraw_col.find({"status": "pending"})
        count = withdraw_col.count_documents({"status": "pending"})
        if count == 0:
            bot.send_message(ADMIN_ID, "❌ কোন পেন্ডিং রিকোয়েস্ট নেই।")
            return
        
        for req in pending:
            m = telebot.types.InlineKeyboardMarkup()
            m.add(telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm_{req['_id']}"),
                  telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{req['_id']}"))
            bot.send_message(ADMIN_ID, f"💰 **উইথড্র রিকোয়েস্ট**\nইউজার আইডি: `{req['user_id']}`\nপরিমাণ: {req['amount']} {get_settings()['currency']}\nপেমেন্ট মেথড: {req['method']}", reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment(call):
    data = call.data.split("_")
    action = data[1]
    req_id = ObjectId(data[2])
    req = withdraw_col.find_one({"_id": req_id})
    
    if action == "confirm":
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "success"}})
        bot.send_message(req['user_id'], "✅ অভিনন্দন! আপনার উইথড্র রিকোয়েস্ট সফলভাবে পেমেন্ট করা হয়েছে।")
        bot.edit_message_text("✅ Paid Success", call.message.chat.id, call.message.message_id)
    else:
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        bot.send_message(req['user_id'], "❌ দুঃখিত! আপনার উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে। ব্যালেন্স ফেরত দেওয়া হয়েছে।")
        bot.edit_message_text("❌ Rejected", call.message.chat.id, call.message.message_id)

# ================= ওয়েব ড্যাশবোর্ড সেকশন =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>User Not Found!</h1>"
    s = get_settings()
    
    html = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{s['bot_name']} - Dashboard</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #f4f7f6; margin: 0; padding: 0; }}
            .header {{ background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 40px 20px; text-align: center; border-bottom-left-radius: 30px; border-bottom-right-radius: 30px; }}
            .logo {{ width: 80px; height: 80px; border-radius: 50%; background: white; padding: 5px; margin-bottom: 10px; }}
            .balance-card {{ background: white; width: 85%; margin: -40px auto 20px; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }}
            .balance-card h2 {{ color: #28a745; font-size: 32px; margin: 10px 0; }}
            .menu-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }}
            .menu-item {{ background: white; padding: 20px; border-radius: 15px; text-decoration: none; color: #333; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: 0.3s; }}
            .menu-item:active {{ transform: scale(0.95); }}
            .menu-item i {{ font-size: 28px; color: #007bff; margin-bottom: 10px; display: block; }}
            .earn-btn {{ grid-column: span 2; background: #28a745; color: white !important; font-size: 20px; }}
            .earn-btn i {{ color: white !important; }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{s['logo']}" class="logo">
            <h1>{s['bot_name']}</h1>
            <p>আইডি: {user['user_id']}</p>
        </div>
        <div class="balance-card">
            <p style="color: #666; margin: 0;">আপনার বর্তমান ব্যালেন্স</p>
            <h2>{user['balance']:.2f} {s['currency']}</h2>
            <small>মোট ক্লিক: {user['clicks']} টি</small>
        </div>
        <div class="menu-container">
            <a href="/earn_page/{user_id}" class="menu-item earn-btn"><i class="fas fa-play-circle"></i> 💰 অ্যাড দেখে আয়</a>
            <a href="javascript:alert('ব্যালেন্স: {user['balance']} {s['currency']}')" class="menu-item"><i class="fas fa-wallet"></i> 📊 ব্যালেন্স</a>
            <a href="javascript:alert('আপনার রেফারাল লিঙ্ক:\\nhttps://t.me/your_bot?start={user_id}')" class="menu-item"><i class="fas fa-users"></i> 👥 রেফার</a>
            <a href="/withdraw_page/{user_id}" class="menu-item"><i class="fas fa-hand-holding-usd"></i> 💳 টাকা তুলুন</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    html = f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Loading Ad...</title>
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <style>
            body {{ font-family: sans-serif; text-align: center; padding-top: 100px; background: #f4f4f4; }}
            .loader {{ border: 8px solid #f3f3f3; border-top: 8px solid #3498db; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{ background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 10px; font-size: 20px; cursor: pointer; display: none; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div id="content">
            <h2>অ্যাড লোড হচ্ছে...</h2>
            <div class="loader"></div>
            <p>৫ সেকেন্ড অপেক্ষা করুন</p>
        </div>
        <a href="/claim/{user_id}" id="claimBtn" class="btn">💰 টাকা সংগ্রহ করুন</a>
        <script>
            setTimeout(function() {{
                if (typeof show_{s['monetag_id']} === 'function') {{ show_{s['monetag_id']}(); }}
                document.getElementById('content').style.display = 'none';
                document.getElementById('claimBtn').style.display = 'inline-block';
            }}, 5000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"""
    <div style="text-align:center; padding:50px; font-family:sans-serif;">
        <h1 style="color:green;">✅ অভিনন্দন!</h1>
        <p>{s['per_click']} {s['currency']} আপনার ব্যালেন্সে যোগ হয়েছে।</p>
        <a href="/dashboard/{user_id}" style="padding:10px 20px; background:#007bff; color:white; text-decoration:none; border-radius:5px;">ড্যাশবোর্ডে ফিরে যান</a>
    </div>
    """

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    html = f"""
    <div style="text-align:center; padding:30px; font-family:sans-serif;">
        <h2>টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: <b>{user['balance']} {s['currency']}</b></p>
        <p style="color:red;">মিনিমাম উইথড্র: {s['min_withdraw']} {s['currency']}</p>
        <form action="/do_withdraw" method="POST" style="margin-top:20px;">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="method" placeholder="বিকাশ/নগদ নাম্বার" required style="padding:12px; width:80%; border:1px solid #ccc; border-radius:5px;"><br><br>
            <input type="number" step="0.01" name="amount" placeholder="পরিমাণ" required style="padding:12px; width:80%; border:1px solid #ccc; border-radius:5px;"><br><br>
            <button type="submit" style="padding:12px 30px; background:#007bff; color:white; border:none; border-radius:5px; font-size:16px;">রিকোয়েস্ট পাঠান</button>
        </form>
        <br><a href="/dashboard/{user_id}">ফিরে যান</a>
    </div>
    """
    return render_template_string(html)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid = int(request.form.get('user_id'))
    amount = float(request.form.get('amount'))
    method = request.form.get('method')
    s = get_settings()
    user = users_col.find_one({"user_id": uid})
    
    if user['balance'] >= amount and amount >= s['min_withdraw']:
        withdraw_col.insert_one({
            "user_id": uid, "amount": amount, "method": method, "status": "pending"
        })
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amount}})
        return f"<h1>রিকোয়েস্ট জমা হয়েছে!</h1><a href='/dashboard/{uid}'>ফিরে যান</a>"
    else:
        return f"<h1>ভুল পরিমাণ বা ব্যালেন্স কম!</h1><a href='/dashboard/{uid}'>আবার চেষ্টা করুন</a>"

# ================= এডমিন ইউজার ম্যানেজমেন্ট (ওয়েব) =================

@app.route('/admin/users')
def admin_users():
    # এখানে সিম্পল একটি লিস্ট দেখা যাবে
    users = users_col.find()
    html = "<h2>ইউজার লিস্ট</h2><table border='1'><tr><th>ID</th><th>নাম</th><th>ব্যালেন্স</th><th>ক্লিক</th></tr>"
    for u in users:
        html += f"<tr><td>{u['user_id']}</td><td>{u['name']}</td><td>{u['balance']}</td><td>{u['clicks']}</td></tr>"
    html += "</table>"
    return html

# ================= ওয়েব হুক ও স্টার্টআপ =================

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
