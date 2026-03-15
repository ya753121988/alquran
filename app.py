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
app.secret_key = "ULTIMATE_BOT_SECRET_KEY"
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']
methods_col = db['methods']
clones_col = db['clones'] # ক্লোন সিস্টেমের জন্য নতুন কালেকশন

def get_settings(bot_id="main"):
    settings = settings_col.find_one({"id": bot_id})
    if not settings:
        default = {
            "id": bot_id,
            "bot_name": "Premium Earning 💎",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "BDT ৳",
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0,
            "ad_seconds": 10 # নতুন টাইমার ফিচার
        }
        settings_col.insert_one(default)
        return default
    return settings

# ================= টেলিগ্রাম বট =================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_name = message.from_user.first_name
    s = get_settings()
    
    # মেইন বটের ইউজার চেক (bot_id="main")
    user = users_col.find_one({"user_id": user_id, "bot_id": "main"})
    if not user:
        ref_by = None
        if len(message.text.split()) > 1:
            try: ref_by = int(message.text.split()[1])
            except: pass
        
        users_col.insert_one({
            "user_id": user_id, "name": user_name, "balance": 0.0, 
            "clicks": 0, "ref_by": ref_by, "bot_id": "main"
        })
        if ref_by and ref_by != user_id:
            users_col.update_one({"user_id": ref_by, "bot_id": "main"}, {"$inc": {"balance": s['per_ref']}})
            try: bot.send_message(ref_by, f"🎊 অভিনন্দন! নতুন রেফারে {s['per_ref']} বোনাস পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}?bot=main"))
    bot.send_message(user_id, f"💎 **স্বাগতম {user_name}!**\nনিচের ড্যাশবোর্ড বাটনে ক্লিক করে কাজ শুরু করুন।", reply_markup=markup)

# ================= HTML টেমপ্লেটসমূহ (Updated with Premium UI & Timer) =================

HTML_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --p: #8b5cf6; --s: #d946ef; --bg: #0f172a; --card: rgba(255, 255, 255, 0.05); }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #f8fafc; }
    .header { background: linear-gradient(135deg, var(--p), var(--s)); padding: 50px 20px; text-align: center; border-radius: 0 0 40px 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .card { background: var(--card); backdrop-filter: blur(10px); width: 90%; max-width: 450px; margin: -40px auto 20px; border-radius: 25px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); box-sizing: border-box; text-align: center; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 15px; max-width: 500px; margin: auto; }
    .m-btn { background: var(--card); padding: 20px; border-radius: 20px; text-decoration: none; color: white; font-weight: 600; border: 1px solid rgba(255,255,255,0.1); transition: 0.3s; }
    .m-btn:active { transform: scale(0.9); }
    .m-btn i { display: block; font-size: 28px; margin-bottom: 10px; color: #fbbf24; }
    .earn { grid-column: span 2; background: #10b981; border: none; font-size: 20px; }
    input, select { width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 12px; background: rgba(255,255,255,0.1); color: white; font-size: 16px; box-sizing: border-box; }
    .sub-btn { background: var(--p); color: white; border: none; padding: 18px; width: 100%; border-radius: 12px; cursor: pointer; font-size: 18px; font-weight: bold; }
    .m-logo { width: 40px; height: 40px; border-radius: 10px; vertical-align: middle; margin-right: 10px; border: 1px solid white; }
    table { width: 100%; color: white; border-collapse: collapse; margin-top: 20px; }
    th, td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); text-align: left; }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""

DASHBOARD_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
{{ style|safe }}
<title>Dashboard</title></head><body>
<div class="header">
    <img src="{{ s.logo }}" width="80" style="border-radius:50%; border:4px solid white;">
    <h2 style="margin-top:10px;">{{ s.bot_name }}</h2>
</div>
<div class="card">
    <p style="color:#94a3b8; margin:0;">💰 বর্তমান ব্যালেন্স</p>
    <h1 style="color:#10b981; font-size:42px; margin:10px 0;">{{ "{:.2f}".format(user.balance) }} {{ s.currency }}</h1>
    <p>🆔 আইডি: {{ user.user_id }} | ✅ মোট ক্লিক: {{ user.clicks }}</p>
</div>
<div class="grid">
    <a href="/earn_page/{{ user.user_id }}?bot={{ bot_id }}" class="m-btn earn"><i class="fas fa-play-circle"></i> 💰 অ্যাড দেখে আয়</a>
    <a href="/refer_page/{{ user.user_id }}?bot={{ bot_id }}" class="m-btn"><i class="fas fa-users"></i> 👥 রেফার</a>
    <a href="/withdraw_page/{{ user.user_id }}?bot={{ bot_id }}" class="m-btn"><i class="fas fa-wallet"></i> 💳 উইথড্র</a>
    <a href="/clone_page/{{ user.user_id }}" class="m-btn" style="grid-column: span 2; background: #6366f1;"><i class="fas fa-robot"></i> নিজের বোট ও সাইট বানান (Clone)</a>
</div>
</body></html>
"""

# ================= ওয়েবসাইট রাউটস =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    if not user: return "ইউজার পাওয়া যায়নি। বোট থেকে পুনরায় /start দিন।"
    s = get_settings(bid)
    return render_template_string(DASHBOARD_HTML, user=user, s=s, bot_id=bid, style=HTML_STYLE)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    bid = request.args.get('bot', 'main')
    s = get_settings(bid)
    html = """
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    {{ style|safe }}</head><body style="text-align:center; padding-top:100px;">
    <script src='//libtl.com/sdk.js' data-zone='{{ s.monetag_id }}' data-sdk='show_{{ s.monetag_id }}'></script>
    <div class="card">
        <h2>🎁 বিজ্ঞাপন লোড হচ্ছে...</h2>
        <p id="timer_msg">অপেক্ষা করুন: <span id="time" style="font-weight:bold; color:cyan;">{{ s.ad_seconds }}</span> সেকেন্ড</p>
        <button id="clm" style="display:none;" class="sub-btn" onclick="location.href='/claim/{{ uid }}?bot={{ bid }}'">💰 টাকা সংগ্রহ করুন</button>
    </div>
    <script>
        let count = {{ s.ad_seconds }};
        let counter = setInterval(timer, 1000);
        function timer() {
            count = count - 1;
            if (count <= 0) {
                clearInterval(counter);
                if(typeof show_{{ s.monetag_id }} === 'function') { show_{{ s.monetag_id }}(); }
                document.getElementById('timer_msg').innerHTML = "বিজ্ঞাপন দেখা শেষ!";
                document.getElementById('clm').style.display = 'block';
                return;
            }
            document.getElementById("time").innerHTML = count;
        }
    </script>
    </body></html>
    """
    return render_template_string(html, s=s, uid=user_id, bid=bid, style=HTML_STYLE)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    bid = request.args.get('bot', 'main')
    s = get_settings(bid)
    users_col.update_one({"user_id": user_id, "bot_id": bid}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return redirect(f"/dashboard/{user_id}?bot={bid}")

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bid = request.args.get('bot', 'main')
    bot_username = bot.get_me().username
    if bid != 'main':
        c = clones_col.find_one({"bot_id": bid})
        if c:
            try:
                temp_bot = telebot.TeleBot(c['token'])
                bot_username = temp_bot.get_me().username
            except: pass

    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    html = """
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="padding:20px; text-align:center;">
    <div class="card" style="margin-top:50px;">
        <h2>👥 রেফার করুন</h2>
        <p>প্রতিটি সফল রেফারে পাবেন বোনাস!</p>
        <input type="text" id="rl" value="{{ ref_link }}" readonly>
        <button class="sub-btn" style="margin-top:10px;" onclick="copy()">🔗 লিঙ্ক কপি করুন</button>
    </div>
    <a href="/dashboard/{{ uid }}?bot={{ bid }}" style="color:#94a3b8; text-decoration:none;">🔙 ফিরে যান</a>
    <script>function copy() { navigator.clipboard.writeText("{{ ref_link }}"); alert("লিঙ্ক কপি হয়েছে!"); }</script>
    </body></html>
    """
    return render_template_string(html, ref_link=ref_link, uid=user_id, bid=bid, style=HTML_STYLE)

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    bid = request.args.get('bot', 'main')
    user = users_col.find_one({"user_id": user_id, "bot_id": bid})
    meths = list(methods_col.find({"bot_id": bid}))
    s = get_settings(bid)
    html = """
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="padding:20px;">
    <div class="card" style="text-align:left;">
        <h2 style="text-align:center;">💳 টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: <b>{{ "{:.2f}".format(user.balance) }} {{ s.currency }}</b></p>
        <form action="/do_withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <input type="hidden" name="bot_id" value="{{ bid }}">
            <label>পেমেন্ট মেথড:</label>
            <select name="method" required>
                {% for m in meths %}
                <option value="{{ m.name }}">{{ m.name }} (Min: {{ m.min }}৳)</option>
                {% endfor %}
            </select>
            <div style="margin:10px 0;">
                {% for m in meths %}
                <img src="{{ m.logo }}" class="m-logo" title="{{ m.name }}">
                {% endfor %}
            </div>
            <input type="text" name="acc" placeholder="অ্যাকাউন্ট নম্বর" required>
            <input type="number" step="0.01" name="amt" placeholder="পরিমাণ" required>
            <button type="submit" class="sub-btn">উইথড্র রিকোয়েস্ট পাঠান</button>
        </form>
    </div>
    <center><a href="/dashboard/{{ user.user_id }}?bot={{ bid }}" style="color:#94a3b8; text-decoration:none;">🔙 ফিরে যান</a></center>
    </body></html>
    """
    return render_template_string(html, user=user, meths=meths, bid=bid, s=s, style=HTML_STYLE)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid = int(request.form.get('user_id'))
    bid = request.form.get('bot_id')
    amt = float(request.form.get('amt'))
    user = users_col.find_one({"user_id": uid, "bot_id": bid})
    s = get_settings(bid)
    if user and user['balance'] >= amt and amt >= s['min_withdraw']:
        withdraw_col.insert_one({
            "user_id": uid, "bot_id": bid, "amount": amt, 
            "method": request.form.get('method'), "acc": request.form.get('acc'), 
            "status": "pending"
        })
        users_col.update_one({"user_id": uid, "bot_id": bid}, {"$inc": {"balance": -amt}})
        return f"<script>alert('আবেদন সফল হয়েছে!'); location.href='/dashboard/{uid}?bot={bid}';</script>"
    return "<h1>ব্যালেন্স কম অথবা তথ্য ভুল!</h1>"

# ================= ক্লোন সিস্টেম (The Clone Engine) =================

@app.route('/clone_page/<int:user_id>')
def clone_page(user_id):
    return render_template_string(f"""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">{HTML_STYLE}</head><body style="padding:20px;">
        <h2>🤖 নিজের বোট ও সাইট তৈরি করুন</h2>
        <div class="card" style="text-align:left;">
            <p>আপনার বোটের তথ্যগুলো দিন:</p>
            <form action="/do_clone" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                বোটের নাম: <input type="text" name="s_name" placeholder="যেমন: MyEarning" required>
                বোট টোকেন: <input type="text" name="token" placeholder="BotFather থেকে নিন" required>
                এডমিন ইউজারনেম: <input type="text" name="u" placeholder="Admin Username" required>
                এডমিন পাসওয়ার্ড: <input type="text" name="p" placeholder="Admin Password" required>
                <button type="submit" class="sub-btn">🚀 বোট জেনারেট করুন</button>
            </form>
        </div>
    </body></html>
    """)

@app.route('/do_clone', methods=['POST'])
def do_clone():
    uid = request.form.get('user_id')
    token = request.form.get('token')
    bid = str(ObjectId()) # প্রতিটি ক্লোনের জন্য ইউনিক আইডি
    
    # ক্লোন ডাটা সেভ
    clones_col.insert_one({
        "bot_id": bid, "owner_id": uid, "token": token, 
        "admin_u": request.form.get('u'), "admin_p": request.form.get('p')
    })
    
    # ডিফল্ট সেটিংস ক্লোনের জন্য
    settings_col.insert_one({
        "id": bid, "bot_name": request.form.get('s_name'),
        "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
        "currency": "BDT ৳", "monetag_id": "10351894", "per_click": 0.50, "per_ref": 1.0, "ad_seconds": 10
    })
    
    # ওয়েব হুক সেট করা নতুন বোটের জন্য
    webhook_url = f"https://{BASE_URL}/webhook/{bid}"
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}")
    
    return f"""
    <div style="background:#0f172a; color:white; padding:50px; text-align:center; height:100vh; font-family:sans-serif;">
        <h1>🎉 সফল হয়েছে!</h1>
        <p>আপনার এডমিন প্যানেল: <br><b>https://{BASE_URL}/admin/login?bot={bid}</b></p>
        <p>ইউজারনেম: {request.form.get('u')}<br>পাসওয়ার্ড: {request.form.get('p')}</p>
        <a href="/" style="color:cyan;">হোমে ফিরে যান</a>
    </div>
    """

# ================= এডমিন প্যানেল (Universal for Main & Clones) =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    bid = request.args.get('bot', 'main')
    if request.method == 'POST':
        u, p = request.form.get('u'), request.form.get('p')
        # মেইন এডমিন চেক
        if bid == 'main' and u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['adm'] = bid
            return redirect(f'/admin/panel?bot={bid}')
        # ক্লোন এডমিন চেক
        clone = clones_col.find_one({"bot_id": bid, "admin_u": u, "admin_p": p})
        if clone:
            session['adm'] = bid
            return redirect(f'/admin/panel?bot={bid}')
            
    return render_template_string(f"""
    <!DOCTYPE html><html><head>{HTML_STYLE}</head><body style="display:flex; justify-content:center; align-items:center; height:100vh;">
    <div class="card" style="width:320px;">
        <h2>🔐 Admin Login</h2>
        <form method="POST"><input type="text" name="u" placeholder="User"><input type="password" name="p" placeholder="Pass"><button class="sub-btn">Login</button></form>
    </div></body></html>
    """)

@app.route('/admin/panel')
def admin_panel():
    bid = request.args.get('bot')
    if session.get('adm') != bid: return redirect(f'/admin/login?bot={bid}')
    
    s = get_settings(bid)
    q = request.args.get('q')
    query = {"bot_id": bid}
    if q and q.isdigit(): query["user_id"] = int(q)
    
    users = users_col.find(query).limit(10)
    withdraws = list(withdraw_col.find({"bot_id": bid, "status": "pending"}))
    meths = list(methods_col.find({"bot_id": bid}))
    
    return render_template_string("""
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="padding:20px;">
        <h2>🛠 এডমিন ড্যাশবোর্ড ({{ s.bot_name }}) <a href="/admin/logout" style="float:right; color:red; font-size:14px;">Logout</a></h2>
        
        <div class="card" style="text-align:left; max-width:100%;">
            <h3>⚙️ বোট সেটিংস</h3>
            <form action="/admin/save_config" method="POST">
                <input type="hidden" name="bid" value="{{ bid }}">
                বোটের নাম: <input type="text" name="bot_name" value="{{ s.bot_name }}">
                মনিটেগ আইডি: <input type="text" name="monetag_id" value="{{ s.monetag_id }}">
                অ্যাড টাইমার (সেকেন্ড): <input type="number" name="ad_seconds" value="{{ s.ad_seconds }}">
                ক্লিক পে: <input type="number" step="0.01" name="per_click" value="{{ s.per_click }}">
                লোগো URL: <input type="text" name="logo" value="{{ s.logo }}">
                <button type="submit" class="sub-btn">Save Settings</button>
            </form>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>💳 পেমেন্ট মেথড</h3>
            <form action="/admin/add_method" method="POST">
                <input type="hidden" name="bid" value="{{ bid }}">
                নাম: <input type="text" name="name" placeholder="Bikash" required>
                লোগো URL: <input type="text" name="logo" placeholder="Logo URL" required>
                মিনিমাম: <input type="number" name="min" required>
                ম্যাক্সিমাম: <input type="number" name="max" required>
                <button type="submit" class="sub-btn" style="background:#4f46e5;">মেথড যুক্ত করুন</button>
            </form>
            <table>
                {% for m in meths %}
                <tr><td><img src="{{m.logo}}" width="30"> {{m.name}}</td><td><a href="/admin/del_method/{{m._id}}?bot={{bid}}" style="color:red;">Del</a></td></tr>
                {% endfor %}
            </table>
        </div>

        <div class="card" style="text-align:left; max-width:100%;">
            <h3>👥 ইউজার সার্চ</h3>
            <form method="GET"><input type="hidden" name="bot" value="{{bid}}"><input type="number" name="q" placeholder="ID..."><button type="submit">Search</button></form>
            <table>
                {% for u in users %}
                <tr><td>{{u.user_id}}</td><td>{{u.balance}}৳</td><td><a href="/admin/edit_user/{{u.user_id}}?bot={{bid}}">Edit</a></td></tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="card">
            <h3>💸 পেন্ডিং উইথড্র ({{ withdraws|length }})</h3>
            {% for w in withdraws %}
            <div style="border:1px solid #444; padding:10px; margin-top:10px; border-radius:10px;">
                ID: {{w.user_id}} | {{w.amount}}৳ | {{w.method}} ({{w.acc}})<br>
                <a href="/admin/pay/confirm/{{w._id}}?bot={{bid}}" style="color:green;">Confirm</a> | <a href="/admin/pay/reject/{{w._id}}?bot={{bid}}" style="color:red;">Reject</a>
            </div>
            {% endfor %}
        </div>
    </body></html>
    """, s=s, users=users, bid=bid, withdraws=withdraws, meths=meths, style=HTML_STYLE)

# --- Admin Actions ---
@app.route('/admin/save_config', methods=['POST'])
def save_config():
    bid = request.form.get('bid')
    if session.get('adm') != bid: return redirect('/')
    settings_col.update_one({"id": bid}, {"$set": {
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
        "bot_id": bid, "name": request.form.get('name'), 
        "logo": request.form.get('logo'), "min": float(request.form.get('min')), 
        "max": float(request.form.get('max'))
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

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    bid = request.args.get('bot')
    user = users_col.find_one({"user_id": uid, "bot_id": bid})
    if request.method == 'POST':
        if request.form.get('a') == 'del': 
            users_col.delete_one({"user_id": uid, "bot_id": bid})
        else: 
            users_col.update_one({"user_id": uid, "bot_id": bid}, {"$set": {"balance": float(request.form.get('b'))}})
        return redirect(f'/admin/panel?bot={bid}')
    return f"<h2>Edit {uid}</h2><form method='POST'>Bal: <input type='number' name='b' value='{user['balance']}'><button type='submit'>Save</button><button type='submit' name='a' value='del'>Delete</button></form>"

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')

# ================= ওয়েব হুক হ্যান্ডলার (For Main & Clones) =================

@app.route('/webhook/<id>', methods=['POST'])
def clone_webhook_handler(id):
    clone = clones_col.find_one({"bot_id": id})
    if not clone: return "!", 200
    
    # ক্লোন বোটের জন্য ডাইনামিক হ্যান্ডলিং
    try:
        temp_bot = telebot.TeleBot(clone['token'])
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        if update.message and update.message.text:
            uid = update.message.chat.id
            uname = update.message.from_user.first_name
            # ইউজার রেজিস্ট্রেশন
            user = users_col.find_one({"user_id": uid, "bot_id": id})
            if not user:
                users_col.insert_one({"user_id": uid, "name": uname, "balance": 0.0, "clicks": 0, "bot_id": id})
            
            s = get_settings(id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড", url=f"https://{BASE_URL}/dashboard/{uid}?bot={id}"))
            temp_bot.send_message(uid, f"👋 স্বাগতম **{s['bot_name']}** এ!\nকাজ শুরু করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)
    except: pass
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

<script src="https://quge5.com/88/tag.min.js" data-zone="163361" async data-cfasync="false"></script>
