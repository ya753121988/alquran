import os
import telebot
import requests
from flask import Flask, request, render_template_string, redirect, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"

# মেইন এডমিন লগইন তথ্য
MAIN_ADMIN_U = "admin"
MAIN_ADMIN_P = "password123"

app = Flask(__name__)
app.secret_key = "PREMIUM_ULTRA_SECURE_KEY_99"
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']
methods_col = db['methods']
clones_col = db['clones']

def get_bot_settings(bid="main"):
    s = settings_col.find_one({"bot_id": str(bid)})
    if not s:
        default = {
            "bot_id": str(bid),
            "bot_name": "Premium Earn 💎",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "BDT ৳",
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0,
            "ad_seconds": 10
        }
        settings_col.insert_one(default)
        return default
    return s

# ================= প্রিমিয়াম সিএসএস (CSS) =================
# ব্র্যাকেট এরর এড়াতে CSS আলাদা করে রাখা হয়েছে
GLOBAL_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --main: #8b5cf6; --sec: #d946ef; --bg: #0f172a; --card: rgba(255, 255, 255, 0.06); }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); color: #f1f5f9; margin: 0; padding: 0; }
    .header { background: linear-gradient(135deg, var(--main), var(--sec)); padding: 50px 20px; text-align: center; border-radius: 0 0 40px 40px; }
    .card { background: var(--card); backdrop-filter: blur(10px); width: 90%; max-width: 450px; margin: -30px auto 20px; border-radius: 25px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); text-align: center; box-sizing: border-box; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 15px; max-width: 500px; margin: auto; }
    .btn { background: var(--card); padding: 20px; border-radius: 18px; text-decoration: none; color: white; font-weight: 600; transition: 0.3s; display: block; border: 1px solid rgba(255,255,255,0.1); }
    .btn:hover { background: var(--main); transform: translateY(-3px); }
    .btn i { display: block; font-size: 28px; margin-bottom: 8px; color: #fbbf24; }
    .earn-btn { grid-column: span 2; background: #10b981; border: none; font-size: 20px; box-shadow: 0 10px 15px rgba(16, 185, 129, 0.2); }
    input, select { width: 100%; padding: 15px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; background: rgba(0,0,0,0.2); color: white; font-size: 16px; box-sizing: border-box; }
    .sub-btn { background: var(--main); color: white; border: none; padding: 16px; width: 100%; border-radius: 12px; cursor: pointer; font-size: 18px; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; }
    .m-logo { width: 40px; height: 40px; border-radius: 8px; vertical-align: middle; margin-right: 10px; border: 1px solid #fff; }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""

# ================= টেলিগ্রাম বোট লজিক =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    s = get_bot_settings("main")
    user = users_col.find_one({"user_id": user_id, "bot_id": "main"})
    
    if not user:
        ref_by = int(message.text.split()[1]) if len(message.text.split()) > 1 and message.text.split()[1].isdigit() else None
        users_col.insert_one({"user_id": user_id, "bot_id": "main", "name": message.from_user.first_name, "balance": 0.0, "clicks": 0, "ref_by": ref_by})
        if ref_by: users_col.update_one({"user_id": ref_by, "bot_id": "main"}, {"$inc": {"balance": s['per_ref']}})

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}/dashboard/{user_id}?bot=main"))
    bot.send_message(user_id, f"💎 **স্বাগতম!**\nকাজ শুরু করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

# ================= ওয়েবসাইট পেজসমূহ =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    if not user: return "ইউজার পাওয়া যায়নি। বোট থেকে পুনরায় স্টার্ট দিন।"
    s = get_bot_settings(bid)
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{GLOBAL_STYLE}</head><body>
    <div class="header">
        <img src="{s['logo']}" width="85" style="border-radius:50%; border:3px solid white;">
        <h2>{s['bot_name']}</h2>
    </div>
    <div class="card">
        <p style="color:#94a3b8; margin:0;">💰 বর্তমান ব্যালেন্স</p>
        <h1 style="color:#10b981; font-size:42px; margin:10px 0;">{user['balance']:.2f} {s['currency']}</h1>
        <p>📊 মোট ক্লিক: {user['clicks']} | 🆔 আইডি: {user_id}</p>
    </div>
    <div class="grid">
        <a href="/earn_page/{user_id}?bot={bid}" class="btn earn-btn"><i class="fas fa-play-circle"></i> আয় করুন</a>
        <a href="/refer_page/{user_id}?bot={bid}" class="btn"><i class="fas fa-users"></i> রেফার</a>
        <a href="/withdraw_page/{user_id}?bot={bid}" class="btn"><i class="fas fa-wallet"></i> উইথড্র</a>
        <a href="/clone_page/{user_id}" class="btn" style="grid-column: span 2; background:var(--main);"><i class="fas fa-robot"></i> নিজের বোট ও এডমিন প্যানেল নিন</a>
    </div>
    </body></html>
    """)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    bid = request.args.get('bot', 'main')
    s = get_bot_settings(bid)
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{GLOBAL_STYLE}</head>
    <body style="text-align:center; padding-top:100px;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <div class="card">
            <h2>🎁 বিজ্ঞাপন লোড হচ্ছে</h2>
            <p>অপেক্ষা করুন: <span id="sec" style="font-weight:bold; color:var(--sec);">{s['ad_seconds']}</span> সেকেন্ড</p>
            <button id="clm" style="display:none;" class="sub-btn" onclick="location.href='/claim/{user_id}?bot={bid}'">💰 টাকা সংগ্রহ করুন</button>
        </div>
        <script>
            let s = {s['ad_seconds']};
            let itv = setInterval(() => {{
                s--; document.getElementById('sec').innerText = s;
                if(s <= 0) {{
                    clearInterval(itv);
                    if(typeof show_{s['monetag_id']} === 'function') {{ show_{s['monetag_id']}(); }}
                    document.getElementById('clm').style.display='block';
                }}
            }}, 1000);
        </script>
    </body></html>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    bid = request.args.get('bot', 'main')
    s = get_bot_settings(bid)
    users_col.update_one({"user_id": user_id, "bot_id": bid}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return redirect(f"/dashboard/{user_id}?bot={bid}")

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bid = request.args.get('bot', 'main')
    bot_info = bot.get_me() if bid == 'main' else telebot.TeleBot(clones_col.find_one({"bot_id": bid})['token']).get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{GLOBAL_STYLE}</head><body style="padding:20px; text-align:center;">
        <h2>👥 রেফারাল প্রোগ্রাম</h2>
        <div class="card">
            <p>আপনার রেফার লিঙ্ক:</p>
            <input type="text" id="rl" value="{ref_link}" readonly>
            <button class="sub-btn" style="margin-top:10px;" onclick="copy()">🔗 কপি করুন</button>
        </div>
        <script>function copy() {{ navigator.clipboard.writeText("{ref_link}"); alert("কপি হয়েছে!"); }}</script>
        <a href="/dashboard/{user_id}?bot={bid}" style="color:#94a3b8;">🔙 ফিরে যান</a>
    </body></html>
    """)

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    meths = list(methods_col.find({"bot_id": bid}))
    s = get_bot_settings(bid)
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{GLOBAL_STYLE}</head><body style="padding:20px;">
        <h2>💳 টাকা উত্তোলন</h2>
        <div class="card" style="text-align:left;">
            <p>ব্যালেন্স: {user['balance']:.2f} {s['currency']}</p>
            <form action="/do_withdraw" method="POST">
                <input type="hidden" name="user_id" value="{user_id}"><input type="hidden" name="bid" value="{bid}">
                <label>মেথড বেছে নিন:</label>
                <select name="method" required>
                    {% for m in meths %}
                    <option value="{{ m.name }}">{{ m.name }} (Min: {{ m.min }}৳)</option>
                    {% endfor %}
                </select>
                <div style="margin-bottom:10px;">
                    {% for m in meths %}<img src="{{m.logo}}" class="m-logo" title="{{m.name}}">{% endfor %}
                </div>
                <input type="text" name="acc" placeholder="অ্যাকাউন্ট নম্বর" required>
                <input type="number" step="0.01" name="amt" placeholder="টাকার পরিমাণ" required>
                <button type="submit" class="sub-btn">✅ সাবমিট করুন</button>
            </form>
        </div>
        <center><a href="/dashboard/{user_id}?bot={bid}" style="color:#94a3b8;">🔙 ফিরে যান</a></center>
    </body></html>
    """, meths=meths)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid, bid, amt = int(request.form.get('user_id')), request.form.get('bid'), float(request.form.get('amt'))
    user = users_col.find_one({"user_id": uid, "bot_id": bid})
    meth = methods_col.find_one({"bot_id": bid, "name": request.form.get('method')})
    if user['balance'] >= amt and meth and amt >= meth['min'] and amt <= meth['max']:
        withdraw_col.insert_one({"user_id": uid, "bot_id": bid, "amount": amt, "method": meth['name'], "acc": request.form.get('acc'), "status": "pending"})
        users_col.update_one({"user_id": uid, "bot_id": bid}, {"$inc": {"balance": -amt}})
        return f"<script>alert('আবেদন সফল!'); location.href='/dashboard/{uid}?bot={bid}';</script>"
    return "<h1>ব্যালেন্স কম বা ভুল তথ্য!</h1>"

# ================= ক্লোন সিস্টেম =================

@app.route('/clone_page/<int:user_id>')
def clone_page(user_id):
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{GLOBAL_STYLE}</head><body style="padding:20px;">
        <h2>🤖 নিজের বোট ও এডমিন প্যানেল নিন</h2>
        <div class="card" style="text-align:left;">
            <form action="/do_clone" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                বোটের নাম: <input type="text" name="s_name" placeholder="যেমন: MyEarn" required>
                বোট টোকেন: <input type="text" name="token" placeholder="BotFather থেকে নিন" required>
                এডমিন ইউজারনেম: <input type="text" name="u" required>
                এডমিন পাসওয়ার্ড: <input type="text" name="p" required>
                <button type="submit" class="sub-btn">🚀 বোট জেনারেট করুন</button>
            </form>
        </div>
    </body></html>
    """)

@app.route('/do_clone', methods=['POST'])
def do_clone():
    bid = str(ObjectId())
    clones_col.insert_one({"bot_id": bid, "token": request.form.get('token'), "admin_u": request.form.get('u'), "admin_p": request.form.get('p')})
    settings_col.insert_one({"bot_id": bid, "bot_name": request.form.get('s_name'), "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png", "currency": "BDT ৳", "monetag_id": "10351894", "per_click": 0.50, "per_ref": 1.0, "ad_seconds": 10})
    requests.get(f"https://api.telegram.org/bot{request.form.get('token')}/setWebhook?url=https://{BASE_URL}/webhook/{bid}")
    return f"""<body style="background:#0f172a; color:white; text-align:center; padding-top:50px; font-family:sans-serif;">
    <h1>🎉 ক্লোন সফল!</h1><p>আপনার এডমিন প্যানেল: <br><b>https://{BASE_URL}/admin/login?bot={bid}</b></p>
    </body>"""

# ================= এডমিন প্যানেল =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    bid = request.args.get('bot', 'main')
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        if (bid == 'main' and u == MAIN_ADMIN_U and p == MAIN_ADMIN_P) or clones_col.find_one({"bot_id": bid, "admin_u": u, "admin_p": p}):
            session['adm'] = bid
            return redirect(f'/admin/panel?bot={bid}')
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{GLOBAL_STYLE}</head><body style="display:flex; justify-content:center; align-items:center; height:100vh;">
    <div class="card" style="width:320px;">
        <h2>🔐 Admin Login</h2>
        <form method="POST"><input type="text" name="u" placeholder="Username" required><input type="password" name="p" placeholder="Password" required><button type="submit" class="sub-btn">Login</button></form>
    </div></body></html>
    """)

@app.route('/admin/panel')
def admin_panel():
    bid = request.args.get('bot')
    if session.get('adm') != bid: return redirect(f'/admin/login?bot={bid}')
    s = get_bot_settings(bid)
    q = request.args.get('q')
    query = {"bot_id": bid}
    if q and q.isdigit(): query["user_id"] = int(q)
    users = users_col.find(query).limit(10)
    withdraws = list(withdraw_col.find({"bot_id": bid, "status": "pending"}))
    meths = list(methods_col.find({"bot_id": bid}))
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{GLOBAL_STYLE}</head><body style="padding:20px;">
        <h2>🛠 এডমিন প্যানেল ({s['bot_name']}) <a href="/admin/logout" style="float:right; color:red; font-size:14px;">Logout</a></h2>
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>⚙️ সেটিংস</h3>
            <form action="/admin/save_config" method="POST">
                <input type="hidden" name="bid" value="{bid}">
                নাম: <input type="text" name="bot_name" value="{s['bot_name']}">
                মনিটেগ আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}">
                টাইমার: <input type="number" name="ad_seconds" value="{s['ad_seconds']}">
                ক্লিক পে: <input type="number" step="0.01" name="per_click" value="{s['per_click']}">
                লোগো: <input type="text" name="logo" value="{s['logo']}">
                <button type="submit" class="sub-btn">Save</button>
            </form>
        </div>
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>💳 মেথড</h3>
            <form action="/admin/add_method" method="POST">
                <input type="hidden" name="bid" value="{bid}">
                নাম: <input type="text" name="name" placeholder="Bikash" required>
                লোগো: <input type="text" name="logo" placeholder="URL" required>
                লিমিট: <input type="number" name="min" placeholder="Min" required> <input type="number" name="max" placeholder="Max" required>
                <button type="submit" class="sub-btn" style="background:#4f46e5;">Add</button>
            </form>
            <table>{% for m in meths %}<tr><td><img src="{{m.logo}}" width="30"> {{m.name}}</td><td><a href="/admin/del_method/{{m._id}}?bot={{bid}}" style="color:red;">Del</a></td></tr>{% endfor %}</table>
        </div>
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>👥 ইউজার ও উইথড্র</h3>
            <form method="GET"><input type="hidden" name="bot" value="{bid}"><input type="number" name="q" placeholder="ID..."><button type="submit">Search</button></form>
            <table>{% for u in users %}<tr><td>{{u.user_id}}</td><td>{{u.balance}}৳</td><td><a href="/admin/edit_user/{{u.user_id}}?bot={{bid}}">Edit</a></td></tr>{% endfor %}</table>
            <h4>পেন্ডিং ({{withdraws|length}})</h4>
            {% for w in withdraws %}<div style="padding:10px; border:1px solid #444; margin-top:5px;">ID: {{w.user_id}} | {{w.amount}}৳ | {{w.method}}<br><a href="/admin/pay/confirm/{{w._id}}?bot={{bid}}" style="color:green;">Pay</a> | <a href="/admin/pay/reject/{{w._id}}?bot={{bid}}" style="color:red;">Reject</a></div>{% endfor %}
        </div>
    </body></html>
    """, users=users, meths=meths, withdraws=withdraws)

# ================= এডমিন অ্যাকশন =================

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    bid = request.form.get('bid')
    if session.get('adm') != bid: return "Error"
    settings_col.update_one({"bot_id": bid}, {"$set": {"bot_name": request.form.get('bot_name'), "monetag_id": request.form.get('monetag_id'), "ad_seconds": int(request.form.get('ad_seconds')), "per_click": float(request.form.get('per_click')), "logo": request.form.get('logo')}})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/add_method', methods=['POST'])
def add_method():
    bid = request.form.get('bid')
    if session.get('adm') != bid: return "Error"
    methods_col.insert_one({"bot_id": bid, "name": request.form.get('name'), "logo": request.form.get('logo'), "min": float(request.form.get('min')), "max": float(request.form.get('max'))})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/del_method/<id>')
def del_method(id):
    bid = request.args.get('bot')
    methods_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/pay/<action>/<id>')
def admin_pay(action, id):
    bid = request.args.get('bot')
    req = withdraw_col.find_one({"_id": ObjectId(id)})
    if action == "confirm": withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "success"}})
    else:
        withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id'], "bot_id": bid}, {"$inc": {"balance": req['amount']}})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    bid = request.args.get('bot')
    user = users_col.find_one({"user_id": uid, "bot_id": bid})
    if request.method == 'POST':
        if request.form.get('a') == 'del': users_col.delete_one({"user_id": uid, "bot_id": bid})
        else: users_col.update_one({"user_id": uid, "bot_id": bid}, {"$set": {"balance": float(request.form.get('b'))}})
        return redirect(f'/admin/panel?bot={bid}')
    return f"<h2>Edit {uid}</h2><form method='POST'>Bal: <input type='number' name='b' value='{user['balance']}'><button type='submit'>Save</button><button type='submit' name='a' value='del'>Delete</button></form>"

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

# ================= ওয়েব হুক হ্যান্ডলার =================

@app.route('/webhook/<id>', methods=['POST'])
def webhook_handler(id):
    clone = clones_col.find_one({"bot_id": id})
    if not clone: return "!", 200
    temp_bot = telebot.TeleBot(clone['token'])
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    if update.message and update.message.text:
        uid, name = update.message.chat.id, update.message.from_user.first_name
        user = users_col.find_one({"user_id": uid, "bot_id": id})
        if not user: users_col.insert_one({"user_id": uid, "bot_id": id, "name": name, "balance": 0.0, "clicks": 0, "ref_by": None})
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}/dashboard/{uid}?bot={id}"))
        temp_bot.send_message(uid, f"👋 স্বাগতম! কাজ শুরু করতে ড্যাশবোর্ডে যান।", reply_markup=markup)
    return "!", 200

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route('/')
def main():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "<h1>Premium Multi-Vendor Engine Online! 🚀</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
