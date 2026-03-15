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

# মেইন এডমিন লগইন
MAIN_ADMIN_U = "admin"
MAIN_ADMIN_P = "password123"

app = Flask(__name__)
app.secret_key = "MULTIVENDOR_SECRET_ULTRA"
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']
methods_col = db['methods']
clones_col = db['clones']

def get_bot_settings(bot_id="main"):
    s = settings_col.find_one({"bot_id": str(bot_id)})
    if not s:
        default = {
            "bot_id": str(bot_id),
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

# ================= স্টাইল শিট (CSS) =================
HTML_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Poppins:wght@300;400;600&display=swap');
    :root { --main: #8b5cf6; --sec: #d946ef; --bg: #0b0e14; --card: rgba(255, 255, 255, 0.05); }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); color: #e2e8f0; margin: 0; padding: 0; }
    .header { background: linear-gradient(135deg, var(--main), var(--sec)); padding: 60px 20px; text-align: center; border-radius: 0 0 50px 50px; box-shadow: 0 10px 30px rgba(139, 92, 246, 0.3); }
    .card { background: var(--card); backdrop-filter: blur(10px); width: 90%; max-width: 450px; margin: -40px auto 20px; border-radius: 30px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); box-sizing: border-box; text-align: center; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 15px; max-width: 500px; margin: auto; }
    .btn { background: var(--card); padding: 20px; border-radius: 20px; text-decoration: none; color: white; font-weight: 600; transition: 0.3s; display: block; border: 1px solid rgba(255,255,255,0.1); }
    .btn:hover { background: var(--main); box-shadow: 0 0 20px var(--main); }
    .btn i { display: block; font-size: 30px; margin-bottom: 10px; color: #fbbf24; }
    .earn-btn { grid-column: span 2; background: #10b981; border: none; font-size: 20px; box-shadow: 0 0 15px #10b981; }
    input, select { width: 100%; padding: 15px; margin: 10px 0; border: 1px solid rgba(255,255,255,0.2); border-radius: 15px; background: rgba(0,0,0,0.3); color: white; font-size: 16px; }
    .submit-btn { background: var(--main); color: white; border: none; padding: 18px; width: 100%; border-radius: 15px; cursor: pointer; font-size: 18px; font-weight: bold; box-shadow: 0 5px 15px var(--main); }
    .method-img { width: 45px; height: 45px; border-radius: 10px; margin: 5px; border: 1px solid white; }
    table { width: 100%; color: white; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; font-size: 14px; }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""

# ================= টেলিগ্রাম বট লজিক =================
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

# ================= ওয়েবসাইট সেকশন =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    if not user: return "ইউজার ডাটা পাওয়া যায়নি।"
    s = get_bot_settings(bid)
    
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body>
    <div class="header">
        <img src="{s['logo']}" width="90" style="border-radius:50%; border:4px solid white;">
        <h1 style="font-family:'Orbitron';">{s['bot_name']}</h1>
    </div>
    <div class="card">
        <p style="color:#94a3b8; margin:0;">💰 ব্যালেন্স</p>
        <h1 style="color:#10b981; font-size:45px; margin:10px 0;">{user['balance']:.2f} {s['currency']}</h1>
        <p>📊 ক্লিক: {user['clicks']} | 🆔 আইডি: {user_id}</p>
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
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head>
    <body style="text-align:center; padding-top:100px;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <div class="card">
            <h2>🎁 বিজ্ঞাপন লোড হচ্ছে</h2>
            <p>অপেক্ষা করুন: <span id="sec" style="font-weight:bold; color:cyan;">{s['ad_seconds']}</span> সেকেন্ড</p>
            <button id="clm" style="display:none;" class="submit-btn" onclick="location.href='/claim/{user_id}?bot={bid}'">💰 টাকা সংগ্রহ করুন</button>
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

@app.route('/clone_page/<int:user_id>')
def clone_page(user_id):
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body style="padding:20px;">
        <h2>🤖 নিজের বোট ও এডমিন প্যানেল সেটআপ</h2>
        <div class="card" style="text-align:left;">
            <p>নিচের তথ্যগুলো দিন, সিস্টেম অটোমেটিক আপনার বোট তৈরি করে দিবে।</p>
            <form action="/do_clone" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                বোটের নাম: <input type="text" name="site_name" placeholder="যেমন: MyPocket" required>
                বোট টোকেন: <input type="text" name="bot_token" placeholder="BotFather থেকে নিন" required>
                এডমিন ইউজারনেম: <input type="text" name="admin_u" placeholder="প্যানেলে লগইন করার জন্য" required>
                এডমিন পাসওয়ার্ড: <input type="text" name="admin_p" placeholder="পাসওয়ার্ড দিন" required>
                <button type="submit" class="submit-btn">🚀 বোট জেনারেট করুন</button>
            </form>
        </div>
    </body></html>
    """)

@app.route('/do_clone', methods=['POST'])
def do_clone():
    token = request.form.get('bot_token')
    # ক্লোন ডাটা সেভ
    clone_id = str(ObjectId())
    clones_col.insert_one({
        "bot_id": clone_id, "token": token,
        "admin_u": request.form.get('admin_u'), "admin_p": request.form.get('admin_p')
    })
    # ডিফল্ট সেটিংস সেটআপ
    settings_col.insert_one({
        "bot_id": clone_id, "bot_name": request.form.get('site_name'),
        "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
        "currency": "BDT ৳", "monetag_id": "10351894", "per_click": 0.50, "per_ref": 1.0, "ad_seconds": 10
    })
    # ওয়েব হুক
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url=https://{BASE_URL}/webhook/{clone_id}")
    return f"""<div style="background:#0b0e14; color:white; padding:50px; text-align:center; font-family:sans-serif; height:100vh;">
        <h1>🎉 অভিনন্দন!</h1><p>আপনার ব্যক্তিগত এডমিন প্যানেল ইউআরএল: <br><b>https://{BASE_URL}/admin/login?bot={clone_id}</b></p>
        <p>বোটটি এখন সচল। লগইন করে আপনার ইচ্ছামতো সব সাজিয়ে নিন।</p>
    </div>"""

# ================= অ্যাডভান্সড এডমিন প্যানেল =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    bid = request.args.get('bot', 'main')
    if request.method == 'POST':
        u = request.form.get('u')
        p = request.form.get('p')
        if bid == 'main' and u == MAIN_ADMIN_U and p == MAIN_ADMIN_P:
            session['adm'] = bid
            return redirect(f'/admin/panel?bot={bid}')
        else:
            clone = clones_col.find_one({"bot_id": bid, "admin_u": u, "admin_p": p})
            if clone:
                session['adm'] = bid
                return redirect(f'/admin/panel?bot={bid}')
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{HTML_STYLE}</head><body style="display:flex; justify-content:center; align-items:center; height:100vh;">
    <div class="card" style="width:320px;">
        <h2>🔐 Admin Login</h2>
        <form method="POST">
            <input type="text" name="u" placeholder="Username" required>
            <input type="password" name="p" placeholder="Password" required>
            <button type="submit" class="submit-btn">Login</button>
        </form>
    </div></body></html>
    """)

@app.route('/admin/panel')
def admin_panel():
    bid = request.args.get('bot')
    if session.get('adm') != bid: return redirect(f'/admin/login?bot={bid}')
    s = get_bot_settings(bid)
    
    # ইউজার সার্চ
    q = request.args.get('q')
    query = {"bot_id": bid}
    if q and q.isdigit(): query["user_id"] = int(q)
    users = users_col.find(query).limit(10)
    
    withdraws = list(withdraw_col.find({"bot_id": bid, "status": "pending"}))
    meths = list(methods_col.find({"bot_id": bid}))
    
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{HTML_STYLE}<title>Admin Panel</title></head><body style="padding:20px;">
        <h2>🛠 {s['bot_name']} এডমিন প্যানেল <a href="/admin/logout" style="float:right; color:red; font-size:15px;">Logout</a></h2>
        
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>⚙️ বোট ও অ্যাড সেটিংস</h3>
            <form action="/admin/save_config" method="POST">
                <input type="hidden" name="bid" value="{bid}">
                নাম: <input type="text" name="bot_name" value="{s['bot_name']}">
                লোগো URL: <input type="text" name="logo" value="{s['logo']}">
                মনিটেগ আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}">
                অ্যাড টাইমার (সেকেন্ড): <input type="number" name="ad_seconds" value="{s['ad_seconds']}">
                ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{s['per_click']}">
                <button type="submit" class="submit-btn">Save Settings</button>
            </form>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>💳 পেমেন্ট মেথড যোগ করুন</h3>
            <form action="/admin/add_method" method="POST">
                <input type="hidden" name="bid" value="{bid}">
                নাম: <input type="text" name="name" placeholder="Bikash" required>
                লোগো URL: <input type="text" name="logo" required>
                মিনিমাম: <input type="number" name="min" required>
                ম্যাক্সিমাম: <input type="number" name="max" required>
                <button type="submit" class="submit-btn" style="background:#4f46e5;">Add Method</button>
            </form>
            <hr>
            <table>
                {% for m in meths %}
                <tr><td><img src="{{m.logo}}" width="30"> {{m.name}}</td><td>{{m.min}}-{{m.max}}৳</td><td><a href="/admin/del_method/{{m._id}}?bot={{bid}}" style="color:red;">Del</a></td></tr>
                {% endfor %}
            </table>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>🔍 ইউজার ও উইথড্র</h3>
            <form method="GET"><input type="hidden" name="bot" value="{bid}"><input type="number" name="q" placeholder="ID দিয়ে সার্চ..."><button type="submit">Search</button></form>
            <table>
                {% for u in users %}
                <tr><td>{{ u.user_id }}</td><td>{{ u.balance }}৳</td><td><a href="/admin/edit_user/{{u.user_id}}?bot={{bid}}">Edit</a></td></tr>
                {% endfor %}
            </table>
            <h4 style="margin-top:20px;">পেন্ডিং উইথড্র ({{ withdraws|length }})</h4>
            {% for w in withdraws %}
            <div style="background:rgba(255,255,255,0.05); padding:10px; margin-top:5px; border-radius:10px;">
                ID: {{ w.user_id }} | {{ w.amount }}৳ | {{ w.method }} ({{ w.acc }})<br>
                <a href="/admin/pay/confirm/{{w._id}}?bot={{bid}}" style="color:green;">Confirm</a> | <a href="/admin/pay/reject/{{w._id}}?bot={{bid}}" style="color:red;">Reject</a>
            </div>
            {% endfor %}
        </div>
    </body></html>
    """, users=users, meths=meths, withdraws=withdraws)

# ================= এডমিন ফাংশনাল লজিক =================

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    bid = request.form.get('bid')
    if session.get('adm') != bid: return redirect('/')
    settings_col.update_one({"bot_id": bid}, {"$set": {
        "bot_name": request.form.get('bot_name'), "logo": request.form.get('logo'),
        "monetag_id": request.form.get('monetag_id'), "ad_seconds": int(request.form.get('ad_seconds')),
        "per_click": float(request.form.get('per_click'))
    }})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/add_method', methods=['POST'])
def add_method():
    bid = request.form.get('bid')
    if session.get('adm') != bid: return redirect('/')
    methods_col.insert_one({
        "bot_id": bid, "name": request.form.get('name'), "logo": request.form.get('logo'),
        "min": float(request.form.get('min')), "max": float(request.form.get('max'))
    })
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
    if action == "confirm":
        withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "success"}})
    else:
        withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id'], "bot_id": bid}, {"$inc": {"balance": req['amount']}})
    return redirect(f'/admin/panel?bot={bid}')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return "লগআউট সফল!"

# ================= উইথড্র লজিক =================
@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    meths = list(methods_col.find({"bot_id": bid}))
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body style="padding:20px;">
        <h2>💳 উত্তোলন</h2>
        <div class="card" style="text-align:left;">
            <p>ব্যালেন্স: {user['balance']:.2f}</p>
            <form action="/do_withdraw" method="POST">
                <input type="hidden" name="user_id" value="{user_id}"><input type="hidden" name="bid" value="{bid}">
                <select name="method">
                    {% for m in meths %}<option value="{{m.name}}">{{m.name}} (Min: {{m.min}}৳)</option>{% endfor %}
                </select>
                <input type="text" name="acc" placeholder="নাম্বার" required>
                <input type="number" step="0.01" name="amt" placeholder="পরিমাণ" required>
                <button type="submit" class="submit-btn">সাবমিট</button>
            </form>
        </div>
    </body></html>
    """, meths=meths)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid, bid, amt = int(request.form.get('user_id')), request.form.get('bid'), float(request.form.get('amt'))
    user = users_col.find_one({"user_id": uid, "bot_id": bid})
    meth = methods_col.find_one({"bot_id": bid, "name": request.form.get('method')})
    if user['balance'] >= amt and meth and amt >= meth['min']:
        withdraw_col.insert_one({"user_id": uid, "bot_id": bid, "amount": amt, "method": meth['name'], "acc": request.form.get('acc'), "status": "pending"})
        users_col.update_one({"user_id": uid, "bot_id": bid}, {"$inc": {"balance": -amt}})
        return "সফল!"
    return "ব্যালেন্স কম!"

# ================= ওয়েব হুক হ্যান্ডলিং =================

@app.route('/webhook/<id>', methods=['POST'])
def webhook_handler(id):
    clone = clones_col.find_one({"bot_id": id})
    if not clone: return "!", 200
    temp_bot = telebot.TeleBot(clone['token'])
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    if update.message and update.message.text:
        uid = update.message.chat.id
        s = get_bot_settings(id)
        # নতুন ইউজার রেজিস্ট্রেশন লজিক (ক্লোন বটের জন্য)
        user = users_col.find_one({"user_id": uid, "bot_id": id})
        if not user:
            users_col.insert_one({"user_id": uid, "bot_id": id, "name": update.message.from_user.first_name, "balance": 0.0, "clicks": 0, "ref_by": None})
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}/dashboard/{uid}?bot={id}"))
        temp_bot.send_message(uid, f"👋 স্বাগতম **{s['bot_name']}** এ!", reply_markup=markup)
    return "!", 200

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route('/')
def main():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "<h1>Multi-Vendor Bot Engine is Active! 🚀</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
