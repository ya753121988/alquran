import os
import telebot
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

def get_settings():
    settings = settings_col.find_one({"id": "config"})
    if not settings:
        default = {
            "id": "config",
            "bot_name": "Premium Earning 💎",
            "logo": "https://cdn-icons-png.flaticon.com/512/2184/2184144.png",
            "currency": "BDT ৳",
            "monetag_id": "10351894",
            "per_click": 0.50,
            "per_ref": 1.0
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
            try: bot.send_message(ref_by, f"🎊 অভিনন্দন! নতুন রেফারে {s['per_ref']} বোনাস পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"💎 **স্বাগতম {user_name}!**\nনিচের ড্যাশবোর্ড বাটনে ক্লিক করে কাজ শুরু করুন।", reply_markup=markup)

# ================= HTML টেমপ্লেটসমূহ (Error-Free) =================

HTML_STYLE = """
<style>
    :root { --p: #6366f1; --s: #a855f7; --bg: #f1f5f9; }
    body { font-family: 'Poppins', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #334155; }
    .header { background: linear-gradient(135deg, var(--p), var(--s)); color: white; padding: 40px 20px; text-align: center; border-radius: 0 0 30px 30px; }
    .card { background: white; width: 90%; max-width: 450px; margin: -30px auto 20px; border-radius: 20px; padding: 25px; box-shadow: 0 10px 15px rgba(0,0,0,0.1); text-align: center; box-sizing: border-box; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 15px; max-width: 500px; margin: auto; }
    .m-btn { background: white; padding: 20px; border-radius: 15px; text-decoration: none; color: #334155; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.05); transition: 0.3s; }
    .m-btn:active { transform: scale(0.9); }
    .m-btn i { display: block; font-size: 24px; margin-bottom: 8px; color: var(--p); }
    .earn { grid-column: span 2; background: #10b981; color: white !important; font-size: 18px; }
    .earn i { color: white; }
    input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; font-size: 16px; }
    .sub-btn { background: var(--p); color: white; border: none; padding: 15px; width: 100%; border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }
    th, td { padding: 10px; border: 1px solid #eee; text-align: left; font-size: 13px; }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""

DASHBOARD_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
{{ style|safe }}
<title>Dashboard</title></head><body>
<div class="header">
    <img src="{{ s.logo }}" width="70" style="border-radius:50%; border:3px solid white;">
    <h2>{{ s.bot_name }}</h2>
</div>
<div class="card">
    <p style="color:#64748b; margin:0;">💰 বর্তমান ব্যালেন্স</p>
    <h1 style="color:#10b981; font-size:32px; margin:10px 0;">{{ "{:.2f}".format(user.balance) }} {{ s.currency }}</h1>
    <small>🆔 আইডি: {{ user.user_id }} | ✅ ক্লিক: {{ user.clicks }}</small>
</div>
<div class="grid">
    <a href="/earn_page/{{ user.user_id }}" class="m-btn earn"><i class="fas fa-play-circle"></i> 💎 অ্যাড দেখে আয়</a>
    <a href="javascript:alert('ব্যালেন্স: {{ user.balance }}')" class="m-btn"><i class="fas fa-wallet"></i> 📊 ব্যালেন্স</a>
    <a href="/refer_page/{{ user.user_id }}" class="m-btn"><i class="fas fa-users"></i> 👥 রেফার</a>
    <a href="/withdraw_page/{{ user.user_id }}" class="m-btn"><i class="fas fa-money-check-alt"></i> 💳 উইথড্র</a>
</div>
</body></html>
"""

EARN_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
{{ style|safe }}</head><body style="text-align:center; padding-top:80px;">
<script src='//libtl.com/sdk.js' data-zone='{{ s.monetag_id }}' data-sdk='show_{{ s.monetag_id }}'></script>
<div class="card">
    <h2>🎁 বিজ্ঞাপন লোড হচ্ছে...</h2>
    <p>অ্যাডটি পুরো দেখুন। ৫ সেকেন্ড পর ক্লেম বাটন আসবে।</p>
    <button id="clm" style="display:none;" class="sub-btn" onclick="location.href='/claim/{{ uid }}'">💰 টাকা সংগ্রহ করুন</button>
</div>
<script>
    setTimeout(() => { 
        if(typeof show_{{ s.monetag_id }} === 'function') { show_{{ s.monetag_id }}(); }
        document.getElementById('clm').style.display='block'; 
    }, 5000);
</script>
</body></html>
"""

ADMIN_HTML = """
<!DOCTYPE html><html><head>{{ style|safe }}<title>Admin Panel</title></head><body>
<div style="padding:20px;">
    <h2>🛠 এডমিন ড্যাশবোর্ড <a href="/admin/logout" style="float:right; font-size:14px; color:red;">Logout</a></h2>
    
    <div class="box card" style="text-align:left;">
        <h3>⚙️ বোট ও অ্যাড সেটিংস</h3>
        <form action="/admin/save_config" method="POST">
            বোটের নাম: <input type="text" name="bot_name" value="{{ s.bot_name }}">
            মনিটেগ জোন আইডি (Zone ID): <input type="text" name="monetag_id" value="{{ s.monetag_id }}">
            ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{{ s.per_click }}">
            রেফার বোনাস: <input type="number" step="0.01" name="per_ref" value="{{ s.per_ref }}">
            লোগো URL: <input type="text" name="logo" value="{{ s.logo }}">
            <button type="submit" class="sub-btn">Save Settings</button>
        </form>
    </div>

    <div class="box card" style="text-align:left;">
        <h3>💳 পেমেন্ট মেথড ম্যানেজমেন্ট</h3>
        <form action="/admin/add_method" method="POST">
            মেথড নাম (বিকাশ/নগদ): <input type="text" name="name" required>
            লোগো URL: <input type="text" name="m_logo">
            মিনিমাম: <input type="number" name="min" required>
            ম্যাক্সিমাম: <input type="number" name="max" required>
            <button type="submit" style="background:#4f46e5" class="sub-btn">Add Method</button>
        </form>
        <table>
            <tr><th>নাম</th><th>লিমিট</th><th>অ্যাকশন</th></tr>
            {% for m in methods %}
            <tr><td>{{ m.name }}</td><td>{{ m.min }}-{{ m.max }}</td><td><a href="/admin/del_method/{{ m._id }}">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div class="box card" style="text-align:left;">
        <h3>👥 ইউজার সার্চ ও লিস্ট</h3>
        <form method="GET"><input type="number" name="q" placeholder="ইউজার আইডি দিয়ে সার্চ..."><button type="submit">Search</button></form>
        <table>
            <tr><th>আইডি</th><th>ব্যালেন্স</th><th>অ্যাকশন</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.balance }}</td><td><a href="/admin/edit_user/{{ u.user_id }}">Edit</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div class="box card">
        <h3>💸 পেন্ডিং পেমেন্ট: {{ withdraws|length }}</h3>
        {% for w in withdraws %}
        <div style="border-bottom:1px solid #ddd; padding:10px;">
            ID: {{ w.user_id }} | Amount: {{ w.amount }} | {{ w.method }} ({{ w.acc }})<br>
            <a href="/admin/pay/confirm/{{ w._id }}" style="color:green;">Confirm</a> | <a href="/admin/pay/reject/{{ w._id }}" style="color:red;">Reject</a>
        </div>
        {% endfor %}
    </div>
</div>
</body></html>
"""

# ================= ওয়েবসাইট রাউটস =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "ইউজার পাওয়া যায়নি। টেলিগ্রাম থেকে /start দিন।"
    return render_template_string(DASHBOARD_HTML, user=user, s=get_settings(), style=HTML_STYLE)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    return render_template_string(EARN_HTML, s=get_settings(), uid=user_id, style=HTML_STYLE)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return redirect(url_for('dashboard', user_id=user_id))

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    html = """
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="padding:20px; text-align:center;">
    <div class="card" style="margin-top:50px;">
        <h2>👥 রেফার করুন</h2>
        <p>প্রতি রেফারে পাবেন ১ টাকা বোনাস।</p>
        <input type="text" id="rl" value="{{ ref_link }}" readonly>
        <button class="sub-btn" onclick="copy()">🔗 কপি লিঙ্ক</button>
    </div>
    <a href="/dashboard/{{ uid }}">🔙 ড্যাশবোর্ডে ফিরে যান</a>
    <script>function copy() { navigator.clipboard.writeText("{{ ref_link }}"); alert("লিঙ্ক কপি হয়েছে!"); }</script>
    </body></html>
    """
    return render_template_string(html, ref_link=ref_link, uid=user_id, style=HTML_STYLE)

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    meths = list(methods_col.find())
    return render_template_string("""
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="padding:20px;">
    <div class="card">
        <h2>💳 টাকা উত্তোলন</h2>
        <p>ব্যালেন্স: {{ user.balance }} টাকা</p>
        <form action="/do_withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                {% for m in meths %}<option value="{{ m.name }}">{{ m.name }} (Min: {{ m.min }}৳)</option>{% endfor %}
            </select>
            <input type="text" name="acc" placeholder="অ্যাকাউন্ট নম্বর" required>
            <input type="number" step="0.01" name="amt" placeholder="পরিমাণ" required>
            <button type="submit" class="sub-btn">সাবমিট রিকোয়েস্ট</button>
        </form>
    </div>
    <center><a href="/dashboard/{{ user.user_id }}">🔙 ফিরে যান</a></center>
    </body></html>
    """, user=user, meths=meths, style=HTML_STYLE)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid = int(request.form.get('user_id'))
    amt = float(request.form.get('amt'))
    user = users_col.find_one({"user_id": uid})
    meth = methods_col.find_one({"name": request.form.get('method')})
    if user and user['balance'] >= amt and meth and amt >= meth['min'] and amt <= meth['max']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": meth['name'], "acc": request.form.get('acc'), "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return "<h1>রিকোয়েস্ট সফল! এডমিন পেমেন্ট করে দিবে।</h1><a href='/'>হোম</a>"
    return "<h1>ব্যালেন্স কম অথবা ভুল তথ্য।</h1>"

# ================= এডমিন ফাংশনালিটি =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('u') == ADMIN_USERNAME and request.form.get('p') == ADMIN_PASSWORD:
            session['adm'] = True
            return redirect('/admin/panel')
    return render_template_string("""
    <!DOCTYPE html><html><head>{{ style|safe }}</head><body style="display:flex; justify-content:center; align-items:center; height:100vh;">
    <div class="card" style="width:300px;">
        <h2>🔐 Admin Login</h2>
        <form method="POST"><input type="text" name="u" placeholder="User"><input type="password" name="p" placeholder="Pass"><button class="sub-btn">Login</button></form>
    </div></body></html>
    """, style=HTML_STYLE)

@app.route('/admin/panel')
def admin_panel():
    if not session.get('adm'): return redirect('/admin/login')
    s = get_settings()
    q = request.args.get('q')
    query = {"user_id": int(q)} if q and q.isdigit() else {}
    users = users_col.find(query).limit(20)
    methods = list(methods_col.find())
    withdraws = list(withdraw_col.find({"status": "pending"}))
    return render_template_string(ADMIN_HTML, s=s, users=users, methods=methods, withdraws=withdraws, style=HTML_STYLE)

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    if not session.get('adm'): return redirect('/admin/login')
    settings_col.update_one({"id": "config"}, {"$set": {
        "bot_name": request.form.get('bot_name'),
        "monetag_id": request.form.get('monetag_id'),
        "per_click": float(request.form.get('per_click')),
        "per_ref": float(request.form.get('per_ref')),
        "logo": request.form.get('logo')
    }})
    return redirect('/admin/panel')

@app.route('/admin/add_method', methods=['POST'])
def add_method():
    if not session.get('adm'): return redirect('/admin/login')
    methods_col.insert_one({"name": request.form.get('name'), "min": float(request.form.get('min')), "max": float(request.form.get('max')), "logo": request.form.get('m_logo')})
    return redirect('/admin/panel')

@app.route('/admin/del_method/<id>')
def del_method(id):
    if not session.get('adm'): return redirect('/admin/login')
    methods_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/panel')

@app.route('/admin/pay/<action>/<id>')
def admin_pay(action, id):
    if not session.get('adm'): return redirect('/admin/login')
    req = withdraw_col.find_one({"_id": ObjectId(id)})
    if action == "confirm":
        withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "success"}})
        try: bot.send_message(req['user_id'], "✅ অভিনন্দন! আপনার পেমেন্ট পাঠানো হয়েছে।")
        except: pass
    else:
        withdraw_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        try: bot.send_message(req['user_id'], "❌ আপনার উইথড্র রিজেক্ট করা হয়েছে।")
        except: pass
    return redirect('/admin/panel')

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    if not session.get('adm'): return redirect('/admin/login')
    user = users_col.find_one({"user_id": uid})
    if request.method == 'POST':
        if request.form.get('a') == 'del': users_col.delete_one({"user_id": uid})
        else: users_col.update_one({"user_id": uid}, {"$set": {"balance": float(request.form.get('b'))}})
        return redirect('/admin/panel')
    return f"<h2>Edit {uid}</h2><form method='POST'>Bal: <input type='number' name='b' value='{user['balance']}'><button type='submit'>Save</button><button type='submit' name='a' value='del'>Delete User</button></form>"

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

@app.route('/')
def main():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{BASE_URL}/{TOKEN}")
    return "<h1>Bot is Running Successfully! 🚀</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
