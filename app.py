import os
import telebot
from flask import Flask, request, render_template_string, redirect, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId

# ================= কনফিগারেশন =================
TOKEN = "8796601390:AAGZ_j1ky67kJIlSfnC55CRlu8ivP4XkIvE"
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "alquran-dun.vercel.app"

# এডমিন লগইন তথ্য (এগুলো আপনি চাইলে পরিবর্তন করতে পারেন)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

app = Flask(__name__)
app.secret_key = "very_secret_key_12345" # সেশন চালানোর জন্য এটি বাধ্যতামূলক
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
            try: bot.send_message(ref_by, f"🎊 আপনার রেফারে একজন নতুন ইউজার জয়েন করেছে! আপনি {s['per_ref']} {s['currency']} বোনাস পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"👋 স্বাগতম {user_name}!\nআয় করতে নিচের বাটনে ক্লিক করে আপনার ড্যাশবোর্ডে প্রবেশ করুন।", reply_markup=markup)

# ================= ওয়েব টেমপ্লেট (HTML) =================

# লগইন পেজ
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login</title>
    <style>
        body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 300px; text-align: center; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .error { color: red; font-size: 14px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Admin Login</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

# এডমিন প্যানেল পেজ
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f8f9fa; }
        .box { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px #ccc; margin-bottom: 20px; }
        input { padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #eee; }
        .logout { float: right; color: red; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <a href="/admin/logout" class="logout">Logout</a>
    <h2>🛠 এডমিন প্যানেল</h2>

    <div class="box">
        <h3>⚙️ বোট সেটিংস</h3>
        <form method="POST" action="/admin/save_settings">
            বোটের নাম: <input type="text" name="bot_name" value="{{ s.bot_name }}">
            লোগো URL: <input type="text" name="logo" value="{{ s.logo }}">
            মনিটেগ আইডি: <input type="text" name="monetag_id" value="{{ s.monetag_id }}">
            ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{{ s.per_click }}">
            রেফার বোনাস: <input type="number" step="0.01" name="per_ref" value="{{ s.per_ref }}">
            মিনিমাম উইথড্র: <input type="number" name="min_withdraw" value="{{ s.min_withdraw }}">
            <button type="submit">সেভ সেটিংস</button>
        </form>
    </div>

    <div class="box">
        <h3>💸 পেন্ডিং উইথড্র রিকোয়েস্ট</h3>
        <table>
            <tr><th>ইউজার আইডি</th><th>পরিমাণ</th><th>মেথড</th><th>অ্যাকশন</th></tr>
            {% for req in withdraws %}
            <tr>
                <td>{{ req.user_id }}</td>
                <td>{{ req.amount }}</td>
                <td>{{ req.method }}</td>
                <td>
                    <a href="/admin/withdraw/confirm/{{ req._id }}" style="color: green;">Confirm</a> | 
                    <a href="/admin/withdraw/reject/{{ req._id }}" style="color: red;">Reject</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="box">
        <h3>👥 ইউজার লিস্ট (সর্বশেষ ৫০ জন)</h3>
        <table>
            <tr><th>আইডি</th><th>নাম</th><th>ব্যালেন্স</th><th>অ্যাকশন</th></tr>
            {% for u in users %}
            <tr>
                <td>{{ u.user_id }}</td>
                <td>{{ u.name }}</td>
                <td>{{ u.balance }}</td>
                <td><a href="/admin/edit/{{ u.user_id }}">এডিট</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# ইউজার ড্যাশবোর্ড পেজ
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

# ================= ওয়েব রাউটস =================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin/panel')
        else:
            error = "ভুল ইউজারনেম বা পাসওয়ার্ড!"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'): return redirect('/admin/login')
    s = get_settings()
    withdraws = list(withdraw_col.find({"status": "pending"}))
    users = list(users_col.find().sort("_id", -1).limit(50))
    return render_template_string(ADMIN_HTML, s=s, withdraws=withdraws, users=users)

@app.route('/admin/save_settings', methods=['POST'])
def save_settings():
    if not session.get('admin_logged_in'): return redirect('/admin/login')
    settings_col.update_one({"id": "config"}, {"$set": {
        "bot_name": request.form.get('bot_name'),
        "logo": request.form.get('logo'),
        "monetag_id": request.form.get('monetag_id'),
        "per_click": float(request.form.get('per_click')),
        "per_ref": float(request.form.get('per_ref')),
        "min_withdraw": float(request.form.get('min_withdraw'))
    }})
    return redirect('/admin/panel')

@app.route('/admin/withdraw/<action>/<req_id>')
def manage_withdraw(action, req_id):
    if not session.get('admin_logged_in'): return redirect('/admin/login')
    req = withdraw_col.find_one({"_id": ObjectId(req_id)})
    if action == "confirm":
        withdraw_col.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "success"}})
        try: bot.send_message(req['user_id'], "✅ অভিনন্দন! আপনার উইথড্র রিকোয়েস্ট সফলভাবে পেমেন্ট করা হয়েছে।")
        except: pass
    else:
        withdraw_col.update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        try: bot.send_message(req['user_id'], "❌ আপনার উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে। ব্যালেন্স ফেরত দেওয়া হয়েছে।")
        except: pass
    return redirect('/admin/panel')

@app.route('/admin/edit/<int:uid>', methods=['GET', 'POST'])
def admin_edit_user(uid):
    if not session.get('admin_logged_in'): return redirect('/admin/login')
    user = users_col.find_one({"user_id": uid})
    if request.method == 'POST':
        if request.form.get('action') == "delete":
            users_col.delete_one({"user_id": uid})
        else:
            users_col.update_one({"user_id": uid}, {"$set": {"balance": float(request.form.get('balance'))}})
        return redirect('/admin/panel')
    return f"<h2>ইউজার এডিট</h2><form method='POST'>ব্যালেন্স: <input type='number' step='0.1' name='balance' value='{user.get('balance',0)}'><br><button type='submit'>Save</button><button type='submit' name='action' value='delete' style='color:red;'>Delete User</button></form>"

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>ইউজার পাওয়া যায়নি! বোট থেকে /start দিন।</h1>"
    s = get_settings()
    return render_template_string(DASHBOARD_HTML, user_id=user_id, balance=round(user.get('balance', 0), 2), logo=s['logo'], bot_name=s['bot_name'], currency=s['currency'])

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    html = """
    <div style="text-align:center; padding:50px; font-family:sans-serif;">
        <h2>👥 রেফার করুন</h2>
        <div style="background:#eee; padding:15px; border-radius:10px; word-break:break-all;">{{ ref_link }}</div><br>
        <button onclick="copyRef()" style="padding:10px 20px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer;">লিঙ্ক কপি করুন</button>
        <br><br><a href="/dashboard/{{ user_id }}">ফিরে যান</a>
        <script>
            function copyRef() {
                navigator.clipboard.writeText("{{ ref_link }}");
                alert("লিঙ্ক কপি হয়েছে!");
            }
        </script>
    </div>
    """
    return render_template_string(html, ref_link=ref_link, user_id=user_id)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    html = """
    <body style="text-align:center; padding-top:100px; font-family:sans-serif;">
        <script src='//libtl.com/sdk.js' data-zone='{{ mid }}' data-sdk='show_{{ mid }}'></script>
        <h2>বিজ্ঞাপন লোড হচ্ছে...</h2>
        <button id="cl" style="display:none; padding:15px; background:green; color:white; border:none; border-radius:5px;" onclick="location.href='/claim/{{ uid }}'">💰 টাকা নিন</button>
        <script>
            setTimeout(() => { 
                if(typeof show_{{ mid }} === 'function') { show_{{ mid }}(); }
                document.getElementById('cl').style.display='inline-block'; 
            }, 5000);
        </script>
    </body>
    """
    return render_template_string(html, mid=s['monetag_id'], uid=user_id)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return f"<div style='text-align:center; padding:50px;'><h1>✅ সফল!</h1><a href='/dashboard/{user_id}'>ফিরে যান</a></div>"

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    return f"<div style='text-align:center; padding:30px;'><h2>💳 উত্তোলন</h2><form action='/do_withdraw' method='POST'><input type='hidden' name='user_id' value='{user_id}'><input type='text' name='method' placeholder='বিকাশ/নগদ নাম্বার' required><br><br><input type='number' name='amount' placeholder='পরিমাণ' required><br><br><button type='submit'>সাবমিট</button></form></div>"

@app.route('/do_withdraw', methods=['POST'])
def do_withdraw():
    uid, amt = int(request.form.get('user_id')), float(request.form.get('amount'))
    user, s = users_col.find_one({"user_id": uid}), get_settings()
    if user['balance'] >= amt and amt >= s['min_withdraw']:
        withdraw_col.insert_one({"user_id": uid, "amount": amt, "method": request.form.get('method'), "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        return "<h1>✅ আবেদন সফল!</h1>"
    return "<h1>❌ ব্যালেন্স কম!</h1>"

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
