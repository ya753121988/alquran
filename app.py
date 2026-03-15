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

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

app = Flask(__name__)
app.secret_key = "ULTRA_PREMIUM_SECURE_KEY"
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']
methods_col = db['methods']
clones_col = db['clones'] # ক্লোন বটের তথ্যের জন্য

def get_settings():
    settings = settings_col.find_one({"id": "config"})
    if not settings:
        default = {
            "id": "config",
            "bot_name": "Premium Earn 💎",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "BDT ৳",
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0,
            "ad_seconds": 10  # ডিফল্ট ১০ সেকেন্ড
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
        ref_by = int(message.text.split()[1]) if len(message.text.split()) > 1 and message.text.split()[1].isdigit() else None
        users_col.insert_one({"user_id": user_id, "name": user_name, "balance": 0.0, "clicks": 0, "ref_by": ref_by})
        if ref_by:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": s['per_ref']}})
            try: bot.send_message(ref_by, f"🎊 আপনার রেফারে {user_name} জয়েন করেছে! +{s['per_ref']} বোনাস।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"💎 **স্বাগতম {user_name}!**\nসবচেয়ে বিশ্বস্ত আর্নিং প্ল্যাটফর্মে আপনাকে স্বাগতম। কাজ শুরু করতে ড্যাশবোর্ডে যান।", reply_markup=markup)

# ================= প্রিমিয়াম ইউআই (CSS) =================

HTML_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --main: #6366f1; --accent: #8b5cf6; --success: #10b981; --bg: #0f172a; --card: #1e293b; }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); margin: 0; color: #f8fafc; overflow-x: hidden; }
    .header { background: linear-gradient(45deg, var(--main), var(--accent)); padding: 50px 20px; text-align: center; border-radius: 0 0 40px 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .card { background: var(--card); width: 90%; max-width: 450px; margin: -40px auto 20px; border-radius: 25px; padding: 25px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3); text-align: center; box-sizing: border-box; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 15px; max-width: 500px; margin: auto; }
    .btn { background: #2d3748; padding: 20px; border-radius: 20px; text-decoration: none; color: white; font-weight: 600; transition: 0.3s; display: block; border: 1px solid #4a5568; }
    .btn:hover { background: var(--main); transform: translateY(-5px); }
    .btn i { display: block; font-size: 30px; margin-bottom: 10px; color: #fbbf24; }
    .earn-btn { grid-column: span 2; background: var(--success); border: none; font-size: 20px; }
    input, select { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px; background: #334155; color: white; font-size: 16px; }
    .submit-btn { background: var(--main); color: white; border: none; padding: 18px; width: 100%; border-radius: 12px; cursor: pointer; font-size: 18px; font-weight: bold; transition: 0.3s; }
    .submit-btn:hover { opacity: 0.9; }
    .method-img { width: 40px; height: 40px; border-radius: 8px; vertical-align: middle; margin-right: 10px; }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""

# ================= ওয়েবসাইট পেজসমূহ =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "টেলিগ্রাম থেকে বোটটি স্টার্ট দিন।"
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body>
    <div class="header">
        <img src="{s['logo']}" width="90" style="border-radius:50%; border:5px solid rgba(255,255,255,0.2);">
        <h1>{s['bot_name']}</h1>
    </div>
    <div class="card">
        <p style="color:#94a3b8; margin:0;">💰 আপনার মোট ব্যালেন্স</p>
        <h1 style="color:var(--success); font-size:40px; margin:10px 0;">{user.get('balance',0):.2f} {s['currency']}</h1>
        <p>📊 মোট ক্লিক: {user.get('clicks',0)} | 🆔 আইডি: {user_id}</p>
    </div>
    <div class="grid">
        <a href="/earn_page/{user_id}" class="btn earn-btn"><i class="fas fa-play-circle"></i> অ্যাড দেখে আয় করুন</a>
        <a href="/refer_page/{user_id}" class="btn"><i class="fas fa-users"></i> রেফার করুন</a>
        <a href="/withdraw_page/{user_id}" class="btn"><i class="fas fa-wallet"></i> টাকা তুলুন</a>
        <a href="/clone_page/{user_id}" class="btn" style="grid-column: span 2; background: #6366f1;"><i class="fas fa-robot"></i> নিজের বট ও সাইট বানান (Clone)</a>
    </div>
    </body></html>
    """)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head>
    <body style="text-align:center; padding-top:100px;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <div class="card">
            <h2>🎁 বিজ্ঞাপন লোড হচ্ছে</h2>
            <p id="timer_text">অপেক্ষা করুন: <span id="sec">{s['ad_seconds']}</span> সেকেন্ড</p>
            <button id="clm" style="display:none;" class="submit-btn" onclick="location.href='/claim/{user_id}'">💰 টাকা সংগ্রহ করুন</button>
        </div>
        <script>
            let s = {s['ad_seconds']};
            let itv = setInterval(() => {{
                s--; document.getElementById('sec').innerText = s;
                if(s <= 0) {{
                    clearInterval(itv);
                    if(typeof show_{s['monetag_id']} === 'function') {{ show_{s['monetag_id']}(); }}
                    document.getElementById('timer_text').innerHTML = "বিজ্ঞাপন দেখা শেষ!";
                    document.getElementById('clm').style.display='block';
                }}
            }}, 1000);
        </script>
    </body></html>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return redirect(f"/dashboard/{user_id}")

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    meths = list(methods_col.find())
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body style="padding:20px;">
        <h2>💳 টাকা উত্তোলন</h2>
        <div class="card" style="text-align:left;">
            <p>আপনার ব্যালেন্স: {user.get('balance',0):.2f} {s['currency']}</p>
            <form action="/do_withdraw" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <label>পেমেন্ট মেথড বেছে নিন:</label>
                <select name="method" required>
                    {% for m in meths %}
                    <option value="{{ m.name }}"> {{ m.name }} (Min: {{ m.min }}৳)</option>
                    {% endfor %}
                </select>
                <div style="margin-top:10px;">
                    {% for m in meths %}
                    <img src="{{ m.logo }}" class="method-img" title="{{ m.name }}">
                    {% endfor %}
                </div>
                <input type="text" name="acc" placeholder="আপনার বিকাশ/নগদ নাম্বার" required>
                <input type="number" step="0.01" name="amt" placeholder="টাকার পরিমাণ" required>
                <button type="submit" class="submit-btn">✅ উত্তোলন রিকোয়েস্ট পাঠান</button>
            </form>
        </div>
        <center><a href="/dashboard/{user_id}" style="color:#94a3b8; text-decoration:none;">🔙 ফিরে যান</a></center>
    </body></html>
    """, meths=meths)

@app.route('/clone_page/<int:user_id>')
def clone_page(user_id):
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body style="padding:20px;">
        <h2>🤖 নিজের বট ও সাইট ক্লোন করুন</h2>
        <div class="card">
            <p>নিচের তথ্যগুলো দিলে আপনার নিজস্ব বট ও সাইট লিঙ্ক জেনারেট হবে।</p>
            <form action="/do_clone" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <input type="text" name="site_name" placeholder="সাইট নাম (যেমন: MyEarn)" required>
                <input type="text" name="bot_token" placeholder="বট টোকেন (BotFather থেকে নিন)" required>
                <input type="text" name="username" placeholder="এডমিন ইউজারনেম" required>
                <input type="text" name="password" placeholder="এডমিন পাসওয়ার্ড" required>
                <button type="submit" class="submit-btn">🚀 ক্লোন লিঙ্ক জেনারেট করুন</button>
            </form>
        </div>
        <center><a href="/dashboard/{user_id}" style="color:#94a3b8;">🔙 ফিরে যান</a></center>
    </body></html>
    """)

@app.route('/do_clone', methods=['POST'])
def do_clone():
    uid = request.form.get('user_id')
    token = request.form.get('bot_token')
    # ক্লোন ডাটা সেভ
    clone_id = clones_col.insert_one({
        "owner_id": uid, "site_name": request.form.get('site_name'),
        "token": token, "admin_u": request.form.get('username'),
        "admin_p": request.form.get('password')
    }).inserted_id
    
    # ক্লোনড বটের জন্য ওয়েব হুক সেট করা
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url=https://{BASE_URL}/clone_webhook/{clone_id}")
    
    return f"""
    <div style="background:#0f172a; color:white; padding:50px; text-align:center; height:100vh; font-family:sans-serif;">
        <h1>🎉 ক্লোন সফল হয়েছে!</h1>
        <p>আপনার ব্যক্তিগত সাইট লিঙ্ক: <br><b>https://{BASE_URL}/dashboard/{uid}?clone={clone_id}</b></p>
        <p>আপনার বটের কাজ শুরু হয়ে গেছে।</p>
        <a href="/dashboard/{uid}" style="color:cyan;">ফিরে যান</a>
    </div>
    """

# ================= এডমিন প্যানেল =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('u') == ADMIN_USERNAME and request.form.get('p') == ADMIN_PASSWORD:
            session['adm'] = True
            return redirect('/admin/panel')
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
    if not session.get('adm'): return redirect('/admin/login')
    s = get_settings()
    
    # সার্চ অপশন
    q = request.args.get('q')
    query = {"user_id": int(q)} if q and q.isdigit() else {}
    users = users_col.find(query).limit(10)
    
    meths = list(methods_col.find())
    withdraws = list(withdraw_col.find({"status": "pending"}))
    
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{HTML_STYLE}<title>Admin</title></head><body style="padding:20px;">
        <h2>🛠 এডমিন ড্যাশবোর্ড <a href="/admin/logout" style="float:right; color:red; font-size:15px;">Logout</a></h2>
        
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>⚙️ গ্লোবাল সেটিংস</h3>
            <form action="/admin/save_config" method="POST">
                বোটের নাম: <input type="text" name="bot_name" value="{s['bot_name']}">
                মনিটেগ আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}">
                অ্যাড টাইমার (সেকেন্ড): <input type="number" name="ad_seconds" value="{s['ad_seconds']}">
                ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{s['per_click']}">
                <button type="submit" class="submit-btn">Save All</button>
            </form>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>💳 পেমেন্ট মেথড যুক্ত করুন</h3>
            <form action="/admin/add_method" method="POST">
                নাম: <input type="text" name="name" placeholder="Bikash" required>
                লোগো URL: <input type="text" name="logo" placeholder="https://logo-url.com" required>
                মিনিমাম: <input type="number" name="min" required>
                ম্যাক্সিমাম: <input type="number" name="max" required>
                <button type="submit" class="submit-btn" style="background:blue;">মেথড অ্যাড করুন</button>
            </form>
            <table style="width:100%; margin-top:10px; border-top:1px solid #444;">
                {% for m in meths %}
                <tr><td><img src="{{m.logo}}" width="30"> {{ m.name }}</td><td>{{ m.min }}-{{m.max}}</td><td><a href="/admin/del_method/{{ m._id }}" style="color:red;">Delete</a></td></tr>
                {% endfor %}
            </table>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>🔍 ইউজার সার্চ</h3>
            <form method="GET"><input type="number" name="q" placeholder="আইডি দিয়ে সার্চ..."><button type="submit" class="submit-btn">Search</button></form>
            <table style="width:100%;">
                {% for u in users %}
                <tr><td>{{ u.user_id }}</td><td>{{ u.balance }}৳</td><td><a href="/admin/edit_user/{{ u.user_id }}">Edit</a></td></tr>
                {% endfor %}
            </table>
        </div>
    </body></html>
    """, users=users, meths=meths, withdraws=withdraws)

# ================= সেভিং ও অ্যাকশন লজিক =================

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    if not session.get('adm'): return redirect('/admin/login')
    settings_col.update_one({"id": "config"}, {"$set": {
        "bot_name": request.form.get('bot_name'),
        "monetag_id": request.form.get('monetag_id'),
        "ad_seconds": int(request.form.get('ad_seconds')),
        "per_click": float(request.form.get('per_click'))
    }})
    return redirect('/admin/panel')

@app.route('/admin/add_method', methods=['POST'])
def add_method():
    if not session.get('adm'): return redirect('/admin/login')
    methods_col.insert_one({
        "name": request.form.get('name'), "logo": request.form.get('logo'),
        "min": float(request.form.get('min')), "max": float(request.form.get('max'))
    })
    return redirect('/admin/panel')

@app.route('/admin/del_method/<id>')
def del_method(id):
    methods_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/panel')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')

# ================= ওয়েব হুক =================

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# ক্লোনড বটের জন্য আলাদা হুক
@app.route('/clone_webhook/<id>', methods=['POST'])
def clone_webhook(id):
    clone = clones_col.find_one({"_id": ObjectId(id)})
    if clone:
        temp_bot = telebot.TeleBot(clone['token'])
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        # এখানে ক্লোন বটের আলাদা লজিক দেওয়া যায়, এখন মেইন বটের মতোই কাজ করবে
        temp_bot.send_message(update.message.chat.id, f"👋 স্বাগতম {clone['site_name']} বোট-এ!\nআপনার সাইট: https://{BASE_URL}/dashboard/{update.message.chat.id}")
    return "!", 200

@app.route('/')
def main():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "<h1>Premium Bot Engine is Online! 🚀</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
