import os
import telebot
from flask import Flask, request, render_template_string, jsonify, redirect
from pymongo import MongoClient
from bson.objectid import ObjectId

# --- ১. কনফিগারেশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "8796601390:AAFsWMertAVwnnmCL1KT2i6DbH8vHOJirkk"
BASE_URL = "alquran-dun.vercel.app"
ADMIN_PASS = "admin123"

# --- ২. ডাটাবেস কানেকশন ---
client = MongoClient(MONGO_URI)
db = client['monetag_only_db']
users_col, settings_col, gateways_col, withdraws_col = db['users'], db['settings'], db['gateways'], db['withdraws']

# ডিফল্ট সেটিংস (শুধুমাত্র মনিটেগ)
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({
        "type": "config", 
        "monetag_id": "10351894", 
        "monetag_pts": 15, 
        "monetag_status": "on", 
        "monetag_link": "", # ডাইরেক্ট লিংকের জন্য
        "currency": "BDT"
    })

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# --- ৩. প্রফেশনাল ডিজাইন (CSS) ---
CSS = """
<style>
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --dark: #1e272e; --white: #ffffff; --success: #27ae60; }
    * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
    body { margin: 0; background: #f1f2f6; color: var(--dark); overflow-x: hidden; }
    .container { max-width: 500px; margin: auto; padding: 15px; }
    .card { background: var(--white); padding: 20px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .header-card { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; text-align: center; }
    .balance { font-size: 45px; font-weight: bold; margin: 5px 0; }
    .btn { display: block; width: 100%; padding: 16px; margin: 12px 0; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.3s; color: white; text-align: center; text-decoration: none; }
    .btn-monetag { background: #5f27cd; border-left: 5px solid #00d2ff; }
    .btn-withdraw { background: var(--success); }
    input, select { width: 100%; padding: 14px; margin: 10px 0; border: 1px solid #ddd; border-radius: 10px; }
    
    /* Admin Sidebar */
    .sidebar { background: var(--dark); color: white; width: 260px; height: 100vh; position: fixed; left: 0; top: 0; padding-top: 20px; z-index: 1000; }
    .sidebar-menu { list-style: none; padding: 0; }
    .sidebar-menu li { padding: 15px 25px; cursor: pointer; border-left: 4px solid transparent; transition: 0.3s; }
    .sidebar-menu li.active { background: #34495e; border-left-color: var(--primary); }
    .admin-main { margin-left: 260px; padding: 30px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: white; margin-top: 15px; font-size: 14px; }
    th, td { padding: 12px; border: 1px solid #eee; text-align: left; }

    @media (max-width: 768px) {
        .sidebar { width: 100%; height: auto; position: relative; display: flex; overflow-x: auto; padding-top: 0; }
        .admin-main { margin-left: 0; padding: 15px; }
        .sidebar-menu { display: flex; }
        .sidebar-menu li { white-space: nowrap; padding: 10px 20px; }
    }
</style>
"""

# --- ৪. ইউজার ড্যাশবোর্ড HTML ---
USER_HTML = CSS + """
<div class="container">
    <div class="card header-card">
        <p style="margin:0; opacity:0.8;">মোট ব্যালেন্স</p>
        <div class="balance">{{ user.points }}</div>
        <p style="margin:0; font-size:14px;">{{ config.currency }} | ID: {{ user.user_id }}</p>
    </div>

    <div class="card">
        <h3 style="text-align:center; margin-bottom:15px;">Daily Tasks</h3>
        {% if config.monetag_status == 'on' %}
        <button class="btn btn-monetag" onclick="runMonetag()">💰 Watch Monetag Ad (+{{ config.monetag_pts }})</button>
        {% else %}
        <p style="text-align:center; color:gray;">বর্তমানে কোন কাজ নেই।</p>
        {% endif %}
    </div>

    <div class="card">
        <h3 style="text-align:center; margin-bottom:15px;">উত্তোলন</h3>
        <form action="/withdraw" method="POST">
            <input type="hidden" name="user_id" value="{{ user.user_id }}">
            <select name="method" required>
                <option value="">পেমেন্ট মেথড সিলেক্ট করুন</option>
                {% for g in gateways %}
                <option value="{{ g.name }}">{{ g.name }} (Min: {{ g.min }})</option>
                {% endfor %}
            </select>
            <input type="text" name="number" placeholder="একাউন্ট নাম্বার" required>
            <input type="number" name="amount" placeholder="পরিমাণ" required>
            <button class="btn btn-withdraw">উইথড্র রিকোয়েস্ট পাঠান</button>
        </form>
    </div>
</div>

<!-- Monetag SDK -->
<script src='//libtl.com/sdk.js' data-zone='{{ config.monetag_id }}' data-sdk='show_{{ config.monetag_id }}'></script>

<script>
function rewardUser() {
    fetch(`/add_pts?id={{ user.user_id }}&amt={{ config.monetag_pts }}`).then(() => {
        alert("Monetag Reward Successful!");
        location.reload();
    });
}

function runMonetag() {
    let mFunc = 'show_{{ config.monetag_id }}';
    if(typeof window[mFunc] === 'function') {
        window[mFunc]().then(() => rewardUser()).catch(() => {
            // যদি স্ক্রিপ্ট কাজ না করে তবে ডাইরেক্ট লিংকে পাঠাবে
            if("{{ config.monetag_link }}") {
                window.open("{{ config.monetag_link }}", "_blank");
                rewardUser();
            } else { alert("Ad Error! Please try again later."); }
        });
    } else if("{{ config.monetag_link }}") {
        window.open("{{ config.monetag_link }}", "_blank");
        rewardUser();
    } else {
        alert("Ad is loading... please wait.");
    }
}
</script>
"""

# --- ৫. অ্যাডমিন প্যানেল HTML ---
ADMIN_HTML = CSS + """
<div class="sidebar">
    <h2 style="text-align:center; color:var(--primary);">অ্যাডমিন</h2>
    <ul class="sidebar-menu">
        <li class="active" onclick="tab(event, 'dash')">ড্যাশবোর্ড</li>
        <li onclick="tab(event, 'ads')">মনিটেগ সেটিংস</li>
        <li onclick="tab(event, 'pay')">পেমেন্ট মেথড</li>
        <li onclick="tab(event, 'req')">রিকোয়েস্ট</li>
        <li onclick="tab(event, 'user')">ইউজার লিস্ট</li>
    </ul>
</div>

<div class="admin-main">
    <div id="dash" class="tab-content active">
        <h2>পরিসংখ্যান</h2>
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div class="card" style="flex:1; min-width:200px;"><h3>{{ users|length }}</h3><p>মোট ইউজার</p></div>
            <div class="card" style="flex:1; min-width:200px;"><h3>{{ withdraws|length }}</h3><p>পেন্ডিং রিকোয়েস্ট</p></div>
        </div>
    </div>

    <div id="ads" class="tab-content">
        <h2>Monetag Control</h2>
        <form action="/admin/save_config" method="POST" class="card">
            Zone ID: <input name="monetag_id" value="{{ config.monetag_id }}">
            Points: <input type="number" name="monetag_pts" value="{{ config.monetag_pts }}">
            Direct Link (Optional): <input name="monetag_link" value="{{ config.monetag_link }}" placeholder="Direct Link for Backup">
            Status: 
            <select name="monetag_status">
                <option value="on" {% if config.monetag_status=='on' %}selected{% endif %}>On</option>
                <option value="off" {% if config.monetag_status=='off' %}selected{% endif %}>Off</option>
            </select>
            Currency Name: <input name="currency" value="{{ config.currency }}">
            <button class="btn btn-withdraw">সেটিংস সেভ করুন</button>
        </form>
    </div>

    <div id="pay" class="tab-content">
        <h2>Payment Gateways</h2>
        <form action="/admin/add_gateway" method="POST" class="card">
            <input name="name" placeholder="বিকাশ / নগদ / রিচার্জ" required>
            <input type="number" name="min" placeholder="মিনিমাম উইথড্র" required>
            <button class="btn btn-withdraw">অ্যাড করুন</button>
        </form>
        <table>
            <tr><th>Gateway</th><th>Min</th><th>Action</th></tr>
            {% for g in gateways %}
            <tr><td>{{ g.name }}</td><td>{{ g.min }}</td><td><a href="/admin/del_gateway/{{ g._id }}" style="color:red;">Delete</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="req" class="tab-content">
        <h2>Withdrawal Requests</h2>
        <table>
            <tr><th>ইউজার আইডি</th><th>মেথড</th><th>নাম্বার</th><th>পরিমাণ</th><th>অ্যাকশন</th></tr>
            {% for w in withdraws %}
            <tr><td>{{ w.user_id }}</td><td>{{ w.method }}</td><td>{{ w.number }}</td><td>{{ w.amount }}</td>
            <td><a href="/admin/approve/{{ w._id }}" style="color:green; font-weight:bold;">Approve</a></td></tr>
            {% endfor %}
        </table>
    </div>

    <div id="user" class="tab-content">
        <h2>User Database</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Balance</th></tr>
            {% for u in users %}
            <tr><td>{{ u.user_id }}</td><td>{{ u.name }}</td><td>{{ u.points }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<script>
function tab(evt, name) {
    var i, content, items;
    content = document.getElementsByClassName("tab-content");
    for (i = 0; i < content.length; i++) { content[i].style.display = "none"; }
    items = document.querySelectorAll(".sidebar-menu li");
    items.forEach(li => li.classList.remove("active"));
    document.getElementById(name).style.display = "block";
    evt.currentTarget.classList.add("active");
}
</script>
"""

# --- ৬. ফ্ল্যাস্ক রুটস ---

@app.route('/')
def home():
    uid = request.args.get('id')
    if not uid: return "<h1>Invalid Access</h1>"
    user = users_col.find_one({"user_id": int(uid)})
    if not user: return "<h1>User Not Found</h1>"
    return render_template_string(USER_HTML, user=user, config=settings_col.find_one({"type": "config"}), gateways=list(gateways_col.find()))

@app.route('/admin')
def admin_p():
    if request.args.get('pass') != ADMIN_PASS: return "Wrong Password", 403
    return render_template_string(ADMIN_HTML, users=list(users_col.find()), config=settings_col.find_one({"type": "config"}), 
                                 gateways=list(gateways_col.find()), withdraws=list(withdraws_col.find({"status": "pending"})))

@app.route('/add_pts')
def add_pts():
    uid, amt = int(request.args.get('id')), int(request.args.get('amt'))
    users_col.update_one({"user_id": uid}, {"$inc": {"points": amt}})
    return jsonify({"success": True})

@app.route('/withdraw', methods=['POST'])
def handle_w():
    uid = int(request.form.get('user_id'))
    method, num, amt = request.form.get('method'), request.form.get('number'), int(request.form.get('amount'))
    user = users_col.find_one({"user_id": uid})
    if user['points'] >= amt:
        withdraws_col.insert_one({"user_id": uid, "method": method, "number": num, "amount": amt, "status": "pending"})
        users_col.update_one({"user_id": uid}, {"$inc": {"points": -amt}})
        bot.send_message(uid, f"✅ আপনার {amt} উত্তোলনের রিকোয়েস্ট জমা হয়েছে।")
    return redirect(f'/?id={uid}')

# Admin Actions
@app.route('/admin/save_config', methods=['POST'])
def save_c():
    settings_col.update_one({"type": "config"}, {"$set": {
        "monetag_id": request.form.get('monetag_id'), 
        "monetag_pts": int(request.form.get('monetag_pts')), 
        "monetag_status": request.form.get('monetag_status'),
        "monetag_link": request.form.get('monetag_link'),
        "currency": request.form.get('currency')
    }})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/add_gateway', methods=['POST'])
def add_g():
    gateways_col.insert_one({"name": request.form.get('name'), "min": int(request.form.get('min'))})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/del_gateway/<id>')
def del_g(id):
    gateways_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/admin/approve/<id>')
def approve_w(id):
    withdraws_col.update_one({"_id": ObjectId(id)}, {"$set": {"status": "paid"}})
    return redirect(f'/admin?pass={ADMIN_PASS}')

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
    return 'ok', 200

# --- ৭. টেলিগ্রাম বট কমান্ড ---

@bot.message_handler(commands=['start'])
def start_bot(message):
    uid, name = message.from_user.id, message.from_user.first_name
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "name": name, "points": 0})
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🚀 Open Dashboard", url=f"https://{BASE_URL}?id={uid}"))
    bot.reply_to(message, f"আসসালামু আলাইকুম {name}! স্বাগতম আমাদের অ্যাপে।", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def get_admin(message):
    bot.reply_to(message, f"অ্যাডমিন প্যানেল লিংক:\nhttps://{BASE_URL}/admin?pass={ADMIN_PASS}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
