import os
import telebot
from flask import Flask, request, render_template_string, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_ID = 7120801813  # আপনার আইডি

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
            "currency": "BDT",
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
    if message.chat.id == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("⚙️ ওয়েব এডমিন প্যানেল", url=f"https://{BASE_URL}/admin/panel"))
        markup.add(telebot.types.InlineKeyboardButton("💸 উইথড্র রিকোয়েস্ট", callback_data="adm_withdraws"))
        bot.send_message(message.chat.id, "🛠 **এডমিন কন্ট্রোল প্যানেল**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_withdraws")
def show_withdrawals(call):
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

# ================= ওয়েবসাইট ড্যাশবোর্ড =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>User not found!</h1>"
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard</title>
        <style>
            body {{ font-family: sans-serif; background: #f0f2f5; margin: 0; text-align: center; }}
            .header {{ background: #007bff; color: white; padding: 40px 20px; border-bottom-left-radius: 25px; border-bottom-right-radius: 25px; }}
            .card {{ background: white; width: 85%; margin: -30px auto 20px; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .menu-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }}
            .menu-item {{ background: white; padding: 20px; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .btn-earn {{ grid-column: span 2; background: #28a745; color: white; font-size: 1.2rem; }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{s['logo']}" width="70" style="border-radius:50%; background:white;">
            <h2>{s['bot_name']}</h2>
        </div>
        <div class="card">
            <p style="margin:0; color:#666;">বর্তমান ব্যালেন্স</p>
            <h1 style="margin:10px 0; color:#28a745;">{user['balance']:.2f} {s['currency']}</h1>
            <small>ইউজার আইডি: {user_id}</small>
        </div>
        <div class="menu-grid">
            <a href="/earn_page/{user_id}" class="menu-item btn-earn">💰 অ্যাড দেখে আয়</a>
            <a href="javascript:alert('ব্যালেন্স: {user['balance']} {s['currency']}')" class="menu-item">📊 ব্যালেন্স</a>
            <a href="/refer_page/{user_id}" class="menu-item">👥 রেফার করুন</a>
            <a href="/withdraw_page/{user_id}" class="menu-item">💳 টাকা তুলুন</a>
        </div>
    </body>
    </html>
    """)

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return render_template_string(f"""
    <div style="text-align:center; padding:50px; font-family:sans-serif;">
        <h2>👥 রেফার করুন এবং আয় করুন</h2>
        <p>প্রতিটি রেফারে পাবেন ১.০০ টাকা</p>
        <input type="text" value="{ref_link}" id="refLink" readonly style="padding:10px; width:80%; border:1px solid #ccc; text-align:center;"><br><br>
        <button onclick="copyLink()" style="padding:10px 20px; background:green; color:white; border:none; border-radius:5px; cursor:pointer;">Copy Referral Link</button>
        <br><br><a href="/dashboard/{user_id}">ড্যাশবোর্ডে ফিরে যান</a>
        <script>
            function copyLink() {{
                var copyText = document.getElementById("refLink");
                copyText.select();
                copyText.setSelectionRange(0, 99999);
                navigator.clipboard.writeText(copyText.value);
                alert("লিঙ্কটি কপি হয়েছে!");
            }}
        </script>
    </div>
    """)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    return render_template_string(f"""
    <body style="text-align:center; padding-top:100px; font-family:sans-serif; background:#f4f4f4;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <h2>অ্যাড লোড হচ্ছে...</h2>
        <p id="timer">৫ সেকেন্ড অপেক্ষা করুন</p>
        <button id="claim" style="display:none; padding:15px 30px; background:#28a745; color:white; border:none; border-radius:10px; font-size:20px; cursor:pointer;" onclick="location.href='/claim/{user_id}'">💰 টাকা সংগ্রহ করুন</button>
        <script>
            setTimeout(() => {{ 
                if(typeof show_{s['monetag_id']} === 'function') show_{s['monetag_id']}();
                document.getElementById('timer').style.display='none';
                document.getElementById('claim').style.display='inline-block'; 
            }}, 5000);
        </script>
    </body>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>সফল! {s['per_click']} {s['currency']} যোগ হয়েছে।</h1><a href='/dashboard/{user_id}'>ফিরে যান</a></div>"

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    return render_template_string(f"""
    <div style="text-align:center; padding:30px; font-family:sans-serif;">
        <h2>💳 টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: {user['balance']} {s['currency']}</p>
        <form action="/do_withdraw" method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="method" placeholder="বিকাশ/নগদ নাম্বার" required style="padding:12px; width:80%; border-radius:5px; border:1px solid #ccc;"><br><br>
            <input type="number" step="0.01" name="amount" placeholder="পরিমাণ" required style="padding:12px; width:80%; border-radius:5px; border:1px solid #ccc;"><br><br>
            <button type="submit" style="padding:12px 30px; background:#007bff; color:white; border:none; border-radius:5px;">উইথড্র রিকোয়েস্ট পাঠান</button>
        </form>
        <br><a href="/dashboard/{user_id}">ফিরে যান</a>
    </div>
    """)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid, amt, mtd = int(request.form.get('user_id')), float(request.form.get('amount')), request.form.get('method')
    user, s = users_col.find_one({"user_id": uid}), get_settings()
    if user['balance'] >= amt and amt >= s['min_withdraw']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": mtd, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return f"<div style='text-align:center; padding:50px;'><h1>রিকোয়েস্ট জমা হয়েছে!</h1><a href='/dashboard/{uid}'>ফিরে যান</a></div>"
    return "<h1>ব্যালেন্স কম!</h1>"

# ================= এডমিন প্যানেল (ওয়েব) =================

@app.route('/admin/panel', methods=['GET', 'POST'])
def admin_web_panel():
    s = get_settings()
    if request.method == 'POST':
        # সেটিংস আপডেট
        new_settings = {
            "bot_name": request.form.get('bot_name'),
            "logo": request.form.get('logo'),
            "currency": request.form.get('currency'),
            "min_withdraw": float(request.form.get('min_withdraw')),
            "monetag_id": request.form.get('monetag_id'),
            "per_click": float(request.form.get('per_click')),
            "per_ref": float(request.form.get('per_ref'))
        }
        settings_col.update_one({"id": "config"}, {"$set": new_settings})
        return redirect('/admin/panel')

    users = users_col.find().limit(20)
    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Admin Panel</title><style>
        body{{font-family:sans-serif; padding:20px; background:#f8f9fa;}}
        .box{{background:white; padding:20px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 5px #ccc;}}
        input{{padding:8px; margin:5px; width:200px;}}
        table{{width:100%; border-collapse:collapse; background:white;}}
        th, td{{padding:10px; border:1px solid #ddd; text-align:left;}}
    </style></head>
    <body>
        <h2>🛠 এডমিন ড্যাশবোর্ড</h2>
        <div class="box">
            <h3>⚙️ বোট সেটিংস</h3>
            <form method="POST">
                বোটের নাম: <input type="text" name="bot_name" value="{s['bot_name']}"><br>
                লোগো URL: <input type="text" name="logo" value="{s['logo']}"><br>
                কারেন্সি: <input type="text" name="currency" value="{s['currency']}"><br>
                মনিটেগ আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}"><br>
                ক্লিক বোনাস: <input type="number" step="0.1" name="per_click" value="{s['per_click']}"><br>
                রেফার বোনাস: <input type="number" step="0.1" name="per_ref" value="{s['per_ref']}"><br>
                মিনিমাম উইথড্র: <input type="number" name="min_withdraw" value="{s['min_withdraw']}"><br>
                <button type="submit" style="background:blue; color:white; padding:10px;">Save Settings</button>
            </form>
        </div>

        <div class="box">
            <h3>👥 ইউজার ম্যানেজমেন্ট</h3>
            <form action="/admin/edit_user" method="POST">
                ইউজার আইডি: <input type="number" name="user_id" placeholder="User ID">
                নতুন ব্যালেন্স: <input type="number" step="0.1" name="balance" placeholder="Balance">
                <button name="action" value="update" style="background:green; color:white;">Update</button>
                <button name="action" value="delete" style="background:red; color:white;">Delete User</button>
            </form>
            <br>
            <table>
                <tr><th>ID</th><th>নাম</th><th>ব্যালেন্স</th><th>ক্লিক</th></tr>
                {"".join([f"<tr><td>{u['user_id']}</td><td>{u['name']}</td><td>{u['balance']}</td><td>{u['clicks']}</td></tr>" for u in users])}
            </table>
        </div>
    </body>
    </html>
    """)

@app.route('/admin/edit_user', methods=['POST'])
def edit_user():
    uid = int(request.form.get('user_id'))
    action = request.form.get('action')
    if action == "update":
        new_bal = float(request.form.get('balance'))
        users_col.update_one({"user_id": uid}, {"$set": {"balance": new_bal}})
    elif action == "delete":
        users_col.delete_one({"user_id": uid})
    return redirect('/admin/panel')

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
