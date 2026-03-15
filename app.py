import os
import telebot
from flask import Flask, request, render_template_string, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_ID = 7120801813

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
            try: bot.send_message(ref_by, f"🎊 আপনার লিঙ্কে একজন জয়েন করেছে! আপনি {s['per_ref']} {s['currency']} বোনাস পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"👋 স্বাগতম {user_name}!\nআয় করতে নিচের বাটনে ক্লিক করে ড্যাশবোর্ডে যান।", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.chat.id == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("⚙️ ওয়েব এডমিন প্যানেল", url=f"https://{BASE_URL}/admin/panel"))
        markup.add(telebot.types.InlineKeyboardButton("💸 উইথড্র রিকোয়েস্ট", callback_data="adm_withdraws"))
        bot.send_message(message.chat.id, "🛠 **এডমিন প্যানেল**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_withdraws")
def adm_withdraws(call):
    pending = withdraw_col.find({"status": "pending"})
    if withdraw_col.count_documents({"status": "pending"}) == 0:
        bot.send_message(ADMIN_ID, "❌ কোনো পেন্ডিং রিকোয়েস্ট নেই।")
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
        bot.send_message(req['user_id'], "✅ আপনার পেমেন্ট সফলভাবে পাঠানো হয়েছে।")
        bot.edit_message_text("✅ Paid Success", call.message.chat.id, call.message.message_id)
    else:
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        bot.send_message(req['user_id'], "❌ আপনার পেমেন্ট রিজেক্ট করা হয়েছে।")
        bot.edit_message_text("❌ Rejected", call.message.chat.id, call.message.message_id)

# ================= ওয়েবসাইট ড্যাশবোর্ড (HTML Templates) =================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
        .header { background: #007bff; color: white; padding: 40px 20px; border-bottom-left-radius: 25px; border-bottom-right-radius: 25px; }
        .card { background: white; width: 85%; margin: -30px auto 20px; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }
        .menu-item { background: white; padding: 20px; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .btn-earn { grid-column: span 2; background: #28a745; color: white !important; font-size: 1.2rem; }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{logo}}" width="70" style="border-radius:50%; background:white;">
        <h2>{{bot_name}}</h2>
    </div>
    <div class="card">
        <p style="margin:0; color:#666;">বর্তমান ব্যালেন্স</p>
        <h1 style="margin:10px 0; color:#28a745;">{{balance}} {{currency}}</h1>
        <small>ইউজার আইডি: {{user_id}}</small>
    </div>
    <div class="menu-grid">
        <a href="/earn_page/{{user_id}}" class="menu-item btn-earn"><i class="fas fa-play-circle"></i> 💰 অ্যাড দেখে আয়</a>
        <a href="javascript:alert('ব্যালেন্স: {{balance}} {{currency}}')" class="menu-item"><i class="fas fa-wallet"></i> 📊 ব্যালেন্স</a>
        <a href="/refer_page/{{user_id}}" class="menu-item"><i class="fas fa-users"></i> 👥 রেফার করুন</a>
        <a href="/withdraw_page/{{user_id}}" class="menu-item"><i class="fas fa-money-bill-wave"></i> 💳 টাকা তুলুন</a>
    </div>
</body>
</html>
"""

REFER_HTML = """
<div style="text-align:center; padding:50px; font-family:sans-serif;">
    <h2>👥 রেফার করে আয় করুন</h2>
    <p>আপনার রেফার লিঙ্কটি কপি করে বন্ধুদের পাঠান</p>
    <div style="background:#eee; padding:15px; border-radius:10px; word-break:break-all; border:1px dashed #007bff;" id="refLink">{{ref_link}}</div>
    <br>
    <button onclick="copyRef()" style="padding:15px 30px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer; font-size:16px;">Copy Link</button>
    <br><br><a href="/dashboard/{{user_id}}">ড্যাশবোর্ডে ফিরে যান</a>
    <script>
        function copyRef() {
            var text = document.getElementById("refLink").innerText;
            navigator.clipboard.writeText(text).then(() => { alert("লিঙ্ক কপি হয়েছে!"); });
        }
    </script>
</div>
"""

EARN_HTML = """
<body style="text-align:center; padding-top:100px; font-family:sans-serif; background:#f4f4f4;">
    <script src='//libtl.com/sdk.js' data-zone='{{monetag_id}}' data-sdk='show_{{monetag_id}}'></script>
    <div id="status">
        <h2>বিজ্ঞাপন লোড হচ্ছে...</h2>
        <p>৫ সেকেন্ড অপেক্ষা করুন</p>
    </div>
    <button id="claim" style="display:none; padding:15px 40px; background:#28a745; color:white; border:none; border-radius:10px; font-size:20px; cursor:pointer;" onclick="location.href='/claim/{{user_id}}'">💰 টাকা সংগ্রহ করুন</button>
    <script>
        setTimeout(() => { 
            if(typeof show_{{monetag_id}} === 'function') { show_{{monetag_id}}(); }
            document.getElementById('status').innerHTML = "<h2>বিজ্ঞাপন দেখা শেষ হয়েছে?</h2>";
            document.getElementById('claim').style.display='inline-block'; 
        }, 5000);
    </script>
</body>
"""

ADMIN_HTML = """
<div style="padding:20px; font-family:sans-serif; background:#f8f9fa;">
    <h2>🛠 এডমিন প্যানেল</h2>
    <form method="POST" style="background:white; padding:20px; border-radius:10px; box-shadow: 0 2px 5px #ccc;">
        বোটের নাম: <input type="text" name="bot_name" value="{{bot_name}}" style="width:100%; padding:8px; margin:10px 0;"><br>
        লোগো URL: <input type="text" name="logo" value="{{logo}}" style="width:100%; padding:8px; margin:10px 0;"><br>
        মনিটেগ আইডি: <input type="text" name="monetag_id" value="{{monetag_id}}" style="width:100%; padding:8px; margin:10px 0;"><br>
        ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{{per_click}}" style="width:100%; padding:8px; margin:10px 0;"><br>
        মিনিমাম উইথড্র: <input type="number" name="min_withdraw" value="{{min_withdraw}}" style="width:100%; padding:8px; margin:10px 0;"><br>
        <button type="submit" style="background:blue; color:white; padding:10px; width:100%; border:none; border-radius:5px;">Save Settings</button>
    </form>
    <h3>ইউজার লিস্ট</h3>
    <table border="1" style="width:100%; border-collapse:collapse; background:white;">
        <tr><th>ID</th><th>Name</th><th>Balance</th><th>Action</th></tr>
        {{user_rows|safe}}
    </table>
</div>
"""

# ================= ওয়েব রাউটস (Routes) =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>User not found!</h1>"
    s = get_settings()
    return render_template_string(DASHBOARD_HTML, user_id=user_id, balance=round(user.get('balance', 0), 2), clicks=user.get('clicks', 0), logo=s['logo'], bot_name=s['bot_name'], currency=s['currency'])

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return render_template_string(REFER_HTML, ref_link=ref_link, user_id=user_id)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    return render_template_string(EARN_HTML, monetag_id=s['monetag_id'], user_id=user_id)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"<div style='text-align:center; padding:50px;'><h1>✅ সফল!</h1><p>{s['per_click']} টাকা যোগ হয়েছে।</p><br><a href='/dashboard/{user_id}'>ড্যাশবোর্ডে ফিরে যান</a></div>"

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    return render_template_string(f"""
    <div style="text-align:center; padding:30px; font-family:sans-serif;">
        <h2>💳 টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: {user.get('balance', 0)} {s['currency']}</p>
        <form action="/do_withdraw" method="POST">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="method" placeholder="বিকাশ / নগদ নাম্বার" required style="padding:12px; width:80%; margin-bottom:10px;"><br>
            <input type="number" step="0.01" name="amount" placeholder="টাকার পরিমাণ" required style="padding:12px; width:80%; margin-bottom:10px;"><br>
            <button type="submit" style="padding:12px 25px; background:#007bff; color:white; border:none; border-radius:5px;">উইথড্র রিকোয়েস্ট পাঠান</button>
        </form>
        <br><a href="/dashboard/{user_id}">ফিরে যান</a>
    </div>
    """)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid = int(request.form.get('user_id'))
    amt = float(request.form.get('amount'))
    mtd = request.form.get('method')
    user = users_col.find_one({"user_id": uid})
    s = get_settings()
    if user['balance'] >= amt and amt >= s['min_withdraw']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": mtd, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return f"<div style='text-align:center; padding:50px;'><h1>✅ সফল!</h1><p>রিকোয়েস্ট জমা হয়েছে।</p><a href='/dashboard/{uid}'>ফিরে যান</a></div>"
    return "<h1>ব্যালেন্স কম!</h1>"

@app.route('/admin/panel', methods=['GET', 'POST'])
def admin_web_panel():
    s = get_settings()
    if request.method == 'POST':
        settings_col.update_one({"id": "config"}, {"$set": {
            "bot_name": request.form.get('bot_name'),
            "logo": request.form.get('logo'),
            "monetag_id": request.form.get('monetag_id'),
            "per_click": float(request.form.get('per_click')),
            "min_withdraw": float(request.form.get('min_withdraw'))
        }})
        return redirect('/admin/panel')

    users = users_col.find().limit(20)
    user_rows = "".join([f"<tr><td>{u['user_id']}</td><td>{u['name']}</td><td>{u.get('balance',0):.2f}</td><td><a href='/admin/edit/{u['user_id']}'>Edit</a></td></tr>" for u in users])
    return render_template_string(ADMIN_HTML, bot_name=s['bot_name'], logo=s['logo'], monetag_id=s['monetag_id'], per_click=s['per_click'], min_withdraw=s['min_withdraw'], user_rows=user_rows)

@app.route('/admin/edit/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    user = users_col.find_one({"user_id": uid})
    if request.method == 'POST':
        if request.form.get('action') == "delete":
            users_col.delete_one({"user_id": uid})
        else:
            users_col.update_one({"user_id": uid}, {"$set": {"balance": float(request.form.get('balance'))}})
        return redirect('/admin/panel')
    return f"<h2>Edit User</h2><form method='POST'>Balance: <input type='number' step='0.1' name='balance' value='{user.get('balance',0)}'><button type='submit'>Save</button><button type='submit' name='action' value='delete' style='color:red;'>Delete</button></form>"

# ================= ওয়েব হুক (Webhook) =================

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
    return "<h1>Bot is Running Successfully!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
