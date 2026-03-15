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
app.secret_key = "premium_secret_key_99"
bot = telebot.TeleBot(TOKEN, threaded=False)

# ================= ডাটাবেস কানেকশন =================
client = MongoClient(MONGO_URI)
db = client['earning_bot_db']
users_col = db['users']
settings_col = db['settings']
withdraw_col = db['withdrawals']
methods_col = db['methods'] # নতুন পেমেন্ট মেথড কালেকশন

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
        ref_by = int(message.text.split()[1]) if len(message.text.split()) > 1 and message.text.split()[1].isdigit() else None
        users_col.insert_one({"user_id": user_id, "name": user_name, "balance": 0.0, "clicks": 0, "ref_by": ref_by})
        if ref_by:
            users_col.update_one({"user_id": ref_by}, {"$inc": {"balance": s['per_ref']}})
            try: bot.send_message(ref_by, f"🎊 আপনার রেফারে {user_name} জয়েন করেছে! +{s['per_ref']} বোনাস।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"💎 **স্বাগতম {user_name}!**\nনিচের বাটনে ক্লিক করে আয় শুরু করুন।", reply_markup=markup)

# ================= প্রিমিয়াম ওয়েব UI (HTML) =================

HTML_HEAD = """
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --primary: #6366f1; --secondary: #a855f7; --bg: #f8fafc; --white: #ffffff; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); margin: 0; padding: 0; color: #1e293b; }
        .header { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 40px 20px; text-align: center; border-radius: 0 0 30px 30px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        .card { background: var(--white); width: 90%; max-width: 500px; margin: -30px auto 20px; border-radius: 20px; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; padding: 15px; max-width: 550px; margin: auto; }
        .menu-btn { background: var(--white); padding: 20px; border-radius: 15px; text-decoration: none; color: #334155; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: 0.3s; }
        .menu-btn:active { transform: scale(0.95); }
        .menu-btn i { display: block; font-size: 28px; margin-bottom: 8px; color: var(--primary); }
        .earn-btn { grid-column: span 2; background: #10b981; color: white !important; font-size: 18px; }
        .earn-btn i { color: white; }
        .input-group { text-align: left; margin-bottom: 15px; }
        input, select { width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; box-sizing: border-box; }
        .submit-btn { background: var(--primary); color: white; border: none; padding: 15px; width: 100%; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border: 1px solid #e2e8f0; text-align: left; font-size: 14px; }
        th { background: #f1f5f9; }
    </style>
</head>
"""

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "ইউজার পাওয়া যায়নি। বোট থেকে পুনরায় স্টার্ট দিন।"
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}<body>
    <div class="header">
        <img src="{s['logo']}" width="80" style="border-radius:50%; border:4px solid white;">
        <h2>{s['bot_name']}</h2>
    </div>
    <div class="card">
        <p style="color:#64748b; margin:0;">💎 বর্তমান ব্যালেন্স</p>
        <h1 style="font-size:36px; margin:10px 0; color:#10b981;">{user.get('balance', 0):.2f} {s['currency']}</h1>
        <p>🆔 আইডি: {user_id} | ✅ মোট ক্লিক: {user.get('clicks',0)}</p>
    </div>
    <div class="grid">
        <a href="/earn_page/{user_id}" class="menu-btn earn-btn"><i class="fas fa-play-circle"></i> 💰 অ্যাড দেখে আয়</a>
        <a href="javascript:alert('ব্যালেন্স: {user.get('balance',0):.2f} {s['currency']}')" class="menu-item menu-btn"><i class="fas fa-wallet"></i> 📊 ব্যালেন্স</a>
        <a href="/refer_page/{user_id}" class="menu-btn"><i class="fas fa-users"></i> 👥 রেফার করুন</a>
        <a href="/withdraw_page/{user_id}" class="menu-btn"><i class="fas fa-money-check-alt"></i> 💳 টাকা তুলুন</a>
    </div>
    </body></html>
    """)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    mid = s['monetag_id']
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}
    <body style="text-align:center; padding-top:100px;">
        <script src='//libtl.com/sdk.js' data-zone='{mid}' data-sdk='show_{mid}'></script>
        <h2>🎁 বিজ্ঞাপন লোড হচ্ছে...</h2>
        <p>৫ সেকেন্ড পর বাটন আসবে। বিজ্ঞাপন দেখা শেষ করে টাকা নিন।</p>
        <button id="clm" style="display:none;" class="submit-btn" onclick="location.href='/claim/{user_id}'">💰 টাকা সংগ্রহ করুন</button>
        <script>
            setTimeout(() => {{ 
                if(typeof show_{mid} === 'function') {{ show_{mid}(); }}
                document.getElementById('clm').style.display='block'; 
            }}, 5000);
        </script>
    </body></html>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return redirect(f"/dashboard/{user_id}")

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}<body style="padding:20px; text-align:center;">
        <h2>👥 রেফারাল প্রোগ্রাম</h2>
        <div class="card" style="margin-top:20px;">
            <p>প্রতিটি রেফারে পাবেন ১.০০ টাকা বোনাস!</p>
            <input type="text" id="r" value="{ref_link}" readonly>
            <button class="submit-btn" style="margin-top:15px;" onclick="copy()">🔗 লিঙ্ক কপি করুন</button>
        </div>
        <a href="/dashboard/{user_id}">🔙 ড্যাশবোর্ডে ফিরে যান</a>
        <script>function copy() {{ navigator.clipboard.writeText("{ref_link}"); alert("লিঙ্ক কপি হয়েছে!"); }}</script>
    </body></html>
    """)

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    meths = list(methods_col.find())
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}<body style="padding:20px;">
        <h2>💳 টাকা উত্তোলন</h2>
        <div class="card">
            <p>আপনার ব্যালেন্স: {user.get('balance',0):.2f} {s['currency']}</p>
            <form action="/do_withdraw" method="POST">
                <input type="hidden" name="user_id" value="{user_id}">
                <div class="input-group">
                    <label>পেমেন্ট মেথড:</label>
                    <select name="method" required>
                        {% for m in meths %}
                        <option value="{{ m.name }}">{{ m.name }} (Min: {{ m.min }}৳)</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="input-group"><input type="text" name="acc" placeholder="অ্যাকাউন্ট নাম্বার" required></div>
                <div class="input-group"><input type="number" step="0.01" name="amt" placeholder="টাকার পরিমাণ" required></div>
                <button type="submit" class="submit-btn">✅ রিকোয়েস্ট পাঠান</button>
            </form>
        </div>
        <center><a href="/dashboard/{user_id}">🔙 ফিরে যান</a></center>
    </body></html>
    """, meths=meths)

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid = int(request.form.get('user_id'))
    amt = float(request.form.get('amt'))
    user = users_col.find_one({"user_id": uid})
    meth = methods_col.find_one({"name": request.form.get('method')})
    
    if user['balance'] >= amt and meth and amt >= meth['min'] and amt <= meth['max']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": meth['name'], "acc": request.form.get('acc'), "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return f"<script>alert('আবেদন সফল হয়েছে!'); location.href='/dashboard/{uid}';</script>"
    return "<h1>ব্যালেন্স কম অথবা লিমিট ভুল!</h1>"

# ================= এডমিন প্যানেল (লগইন ও সেটিংস) =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('u') == ADMIN_USERNAME and request.form.get('p') == ADMIN_PASSWORD:
            session['adm'] = True
            return redirect('/admin/panel')
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}<body style="display:flex; justify-content:center; align-items:center; height:100vh;">
    <div class="card" style="width:300px;">
        <h2>🔐 Admin Login</h2>
        <form method="POST">
            <input type="text" name="u" placeholder="Username" required><br><br>
            <input type="password" name="p" placeholder="Password" required><br><br>
            <button type="submit" class="submit-btn">Login</button>
        </form>
    </div>
    </body></html>
    """)

@app.route('/admin/panel')
def admin_panel():
    if not session.get('adm'): return redirect('/admin/login')
    s = get_settings()
    
    # সার্চ ফিল্টার
    search = request.args.get('q')
    query = {"user_id": int(search)} if search and search.isdigit() else {}
    users = users_col.find(query).limit(20)
    
    meths = list(methods_col.find())
    withdraws = list(withdraw_col.find({"status": "pending"}))
    
    return render_template_string(f"""
    <!DOCTYPE html><html>{HTML_HEAD}<body style="padding:20px;">
        <h2>🛠 Premium Admin Panel <a href="/admin/logout" style="float:right; font-size:14px; color:red;">Logout</a></h2>
        
        <div class="box card" style="text-align:left;">
            <h3>⚙️ গ্লোবাল সেটিংস</h3>
            <form action="/admin/save_config" method="POST">
                বোটের নাম: <input type="text" name="bot_name" value="{s['bot_name']}">
                মনিটেগ জোন আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}">
                ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{s['per_click']}">
                <button type="submit" class="submit-btn">Save Settings</button>
            </form>
        </div>

        <div class="box card" style="text-align:left;">
            <h3>💳 পেমেন্ট মেথড (আনলিমিটেড)</h3>
            <form action="/admin/add_method" method="POST">
                নাম: <input type="text" name="name" placeholder="বিকাশ / নগদ" required>
                মিনিমাম: <input type="number" name="min" placeholder="Min Amount" required>
                ম্যাক্সিমাম: <input type="number" name="max" placeholder="Max Amount" required>
                <button type="submit" style="background:blue; color:white;" class="submit-btn">Add Method</button>
            </form>
            <hr>
            <table>
                <tr><th>মেথড</th><th>Min-Max</th><th>অ্যাকশন</th></tr>
                {% for m in meths %}
                <tr><td>{{ m.name }}</td><td>{{ m.min }}-{{ m.max }}</td><td><a href="/admin/del_method/{{ m._id }}">Delete</a></td></tr>
                {% endfor %}
            </table>
        </div>

        <div class="box card" style="text-align:left;">
            <h3>👥 ইউজার ম্যানেজমেন্ট</h3>
            <form method="GET"><input type="number" name="q" placeholder="ইউজার আইডি দিয়ে সার্চ দিন..."><button type="submit">Search</button></form>
            <table>
                <tr><th>আইডি</th><th>ব্যালেন্স</th><th>অ্যাকশন</th></tr>
                {% for u in users %}
                <tr><td>{{ u.user_id }}</td><td>{{ u.balance }}</td><td><a href="/admin/edit_user/{{ u.user_id }}">Edit</a></td></tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="box card">
            <h3>💸 উইথড্র রিকোয়েস্ট ({{ withdraws|length }})</h3>
            {% for w in withdraws %}
            <div style="border:1px solid #ddd; padding:10px; margin-bottom:5px;">
                ID: {{ w.user_id }} | {{ w.amount }}৳ | {{ w.method }} ({{ w.acc }})<br>
                <a href="/admin/pay/confirm/{{ w._id }}" style="color:green;">Confirm</a> | <a href="/admin/pay/reject/{{ w._id }}" style="color:red;">Reject</a>
            </div>
            {% endfor %}
        </div>
    </body></html>
    """, users=users, meths=meths, withdraws=withdraws)

# ================= এডমিন ফাংশনালিটি =================

@app.route('/admin/save_config', methods=['POST'])
def save_config():
    if not session.get('adm'): return redirect('/admin/login')
    settings_col.update_one({"id": "config"}, {"$set": {
        "bot_name": request.form.get('bot_name'),
        "monetag_id": request.form.get('monetag_id'),
        "per_click": float(request.form.get('per_click'))
    }})
    return redirect('/admin/panel')

@app.route('/admin/add_method', methods=['POST'])
def add_method():
    if not session.get('adm'): return redirect('/admin/login')
    methods_col.insert_one({
        "name": request.form.get('name'),
        "min": float(request.form.get('min')),
        "max": float(request.form.get('max'))
    })
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
        try: bot.send_message(req['user_id'], "❌ আপনার উইথড্র রিজেক্ট করা হয়েছে। ব্যালেন্স ফেরত দেওয়া হয়েছে।")
        except: pass
    return redirect('/admin/panel')

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    if not session.get('adm'): return redirect('/admin/login')
    user = users_col.find_one({"user_id": uid})
    if request.method == 'POST':
        if request.form.get('a') == 'del':
            users_col.delete_one({"user_id": uid})
        else:
            users_col.update_one({"user_id": uid}, {"$set": {"balance": float(request.form.get('b'))}})
        return redirect('/admin/panel')
    return f"<h2>Edit User {uid}</h2><form method='POST'>Balance: <input type='number' step='0.1' name='b' value='{user['balance']}'><button type='submit'>Save</button><button type='submit' name='a' value='del'>Delete User</button></form>"

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
