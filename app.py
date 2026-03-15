import os
import telebot
from flask import Flask, request, render_template_string, redirect
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

# সেটিংস লোড করার ফাংশন
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
            try: bot.send_message(ref_by, f"🎊 রেফার বোনাস {s['per_ref']} {s['currency']} পেয়েছেন।")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🌐 ড্যাশবোর্ড ওপেন করুন", url=f"https://{BASE_URL}/dashboard/{user_id}"))
    bot.send_message(user_id, f"👋 স্বাগতম {user_name}!\nআমাদের {s['bot_name']} এ আয় করতে নিচের ড্যাশবোর্ড বাটনে ক্লিক করুন।", reply_markup=markup)

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
        bot.send_message(ADMIN_ID, "❌ বর্তমানে কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই।")
        return
    for req in pending:
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"pay_confirm_{req['_id']}"),
              telebot.types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject_{req['_id']}"))
        bot.send_message(ADMIN_ID, f"💰 **উইথড্র রিকোয়েস্ট:**\nইউজার আইডি: `{req['user_id']}`\nপরিমাণ: {req['amount']}\nমেথড: {req['method']}", reply_markup=m)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment(call):
    data = call.data.split("_")
    action, req_id = data[1], ObjectId(data[2])
    req = withdraw_col.find_one({"_id": req_id})
    if action == "confirm":
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "success"}})
        bot.send_message(req['user_id'], "✅ অভিনন্দন! আপনার উইথড্র সফলভাবে পেমেন্ট করা হয়েছে।")
        bot.edit_message_text("✅ Payment Confirmed", call.message.chat.id, call.message.message_id)
    else:
        withdraw_col.update_one({"_id": req_id}, {"$set": {"status": "rejected"}})
        users_col.update_one({"user_id": req['user_id']}, {"$inc": {"balance": req['amount']}})
        bot.send_message(req['user_id'], "❌ দুঃখিত! আপনার উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে। ব্যালেন্স ফেরত দেওয়া হয়েছে।")
        bot.edit_message_text("❌ Payment Rejected", call.message.chat.id, call.message.message_id)

# ================= ওয়েবসাইট ড্যাশবোর্ড সেকশন =================

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user: return "<h1>User Not Found! Please /start the bot first.</h1>"
    s = get_settings()
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {{ font-family: sans-serif; background: #f4f6f9; margin: 0; text-align: center; }}
            .header {{ background: #007bff; color: white; padding: 40px 20px; border-bottom-left-radius: 25px; border-bottom-right-radius: 25px; }}
            .card {{ background: white; width: 85%; margin: -30px auto 20px; border-radius: 15px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .menu-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }}
            .menu-item {{ background: white; padding: 20px; border-radius: 12px; text-decoration: none; color: #333; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .menu-item i {{ display: block; font-size: 28px; color: #007bff; margin-bottom: 10px; }}
            .btn-earn {{ grid-column: span 2; background: #28a745; color: white !important; }}
            .btn-earn i {{ color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{s['logo']}" width="70" style="border-radius:50%; background:white; padding:5px;">
            <h2>{s['bot_name']}</h2>
        </div>
        <div class="card">
            <p style="margin:0; color:#666;">বর্তমান ব্যালেন্স</p>
            <h1 style="margin:10px 0; color:#28a745;">{user['balance']:.2f} {s['currency']}</h1>
            <small>ইউজার আইডি: {user_id}</small>
        </div>
        <div class="menu-grid">
            <a href="/earn_page/{user_id}" class="menu-item btn-earn"><i class="fas fa-play-circle"></i> 💰 অ্যাড দেখে আয়</a>
            <a href="javascript:alert('ব্যালেন্স: {user['balance']:.2f} {s['currency']}\\nক্লিক: {user['clicks']} টি')" class="menu-item"><i class="fas fa-wallet"></i> 📊 ব্যালেন্স</a>
            <a href="/refer_page/{user_id}" class="menu-item"><i class="fas fa-users"></i> 👥 রেফার করুন</a>
            <a href="/withdraw_page/{user_id}" class="menu-item"><i class="fas fa-money-bill-wave"></i> 💳 টাকা তুলুন</a>
        </div>
    </body>
    </html>
    """)

@app.route('/refer_page/<int:user_id>')
def refer_page(user_id):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return render_template_string(f"""
    <div style="text-align:center; padding:50px; font-family:sans-serif; background:#fff; height:100vh;">
        <h2>👥 রেফারেল প্রোগ্রাম</h2>
        <p>আপনার রেফার লিঙ্কে কেউ জয়েন করলেই বোনাস পাবেন!</p>
        <div style="background:#f4f4f4; padding:15px; border-radius:10px; border:1px dashed #007bff; word-break:break-all;" id="refText">{ref_link}</div>
        <br>
        <button onclick="copyRef()" style="padding:15px 30px; background:#007bff; color:white; border:none; border-radius:5px; font-size:16px;">কপি করুন</button>
        <br><br><a href="/dashboard/{user_id}">ড্যাশবোর্ডে ফিরে যান</a>
        <script>
            function copyRef() {{
                var text = document.getElementById("refText").innerText;
                navigator.clipboard.writeText(text).then(function() {{
                    alert("লিঙ্কটি কপি করা হয়েছে!");
                }});
            }}
        </script>
    </div>
    """)

@app.route('/earn_page/<int:user_id>')
def earn_page(user_id):
    s = get_settings()
    # মনিটেগ অ্যাড লোড করার স্ক্রিপ্ট
    return render_template_string(f"""
    <body style="text-align:center; padding-top:100px; font-family:sans-serif; background:#f4f4f4;">
        <script src='//libtl.com/sdk.js' data-zone='{s['monetag_id']}' data-sdk='show_{s['monetag_id']}'></script>
        <div id="ad-container">
            <h2>বিজ্ঞাপন লোড হচ্ছে...</h2>
            <p>৫ সেকেন্ড অপেক্ষা করুন, এরপর বাটন আসবে।</p>
        </div>
        <button id="claim" style="display:none; padding:15px 40px; background:#28a745; color:white; border:none; border-radius:10px; font-size:22px; cursor:pointer;" onclick="location.href='/claim/{user_id}'">💰 টাকা সংগ্রহ করুন</button>
        <script>
            setTimeout(() => {{ 
                if(typeof show_{s['monetag_id']} === 'function') {{
                    show_{s['monetag_id']}(); 
                }}
                document.getElementById('ad-container').innerHTML = "<h2>বিজ্ঞাপন দেখা শেষ হয়েছে?</h2>";
                document.getElementById('claim').style.display='inline-block'; 
            }}, 5000);
        </script>
    </body>
    """)

@app.route('/claim/<int:user_id>')
def claim(user_id):
    s = get_settings()
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": s['per_click'], "clicks": 1}})
    return render_template_string(f"""
    <div style="text-align:center; padding:100px; font-family:sans-serif;">
        <h1 style="color:green;">✅ সফল!</h1>
        <h3>{s['per_click']} {s['currency']} আপনার ব্যালেন্সে যোগ করা হয়েছে।</h3>
        <br><a href="/dashboard/{user_id}" style="text-decoration:none; padding:10px 20px; background:#007bff; color:white; border-radius:5px;">ড্যাশবোর্ডে ফিরে যান</a>
    </div>
    """)

@app.route('/withdraw_page/<int:user_id>')
def withdraw_page(user_id):
    user = users_col.find_one({"user_id": user_id})
    s = get_settings()
    return render_template_string(f"""
    <div style="text-align:center; padding:30px; font-family:sans-serif;">
        <h2>💳 টাকা উত্তোলন করুন</h2>
        <div style="background:#e9ecef; padding:20px; border-radius:10px;">
            <p>আপনার ব্যালেন্স: <b>{user['balance']:.2f} {s['currency']}</b></p>
            <p style="color:red;">মিনিমাম উইথড্র: {s['min_withdraw']} {s['currency']}</p>
        </div>
        <form action="/do_withdraw" method="POST" style="margin-top:20px;">
            <input type="hidden" name="user_id" value="{user_id}">
            <input type="text" name="method" placeholder="বিকাশ / নগদ নম্বর" required style="padding:15px; width:85%; margin-bottom:15px; border:1px solid #ccc; border-radius:8px;"><br>
            <input type="number" step="0.01" name="amount" placeholder="টাকার পরিমাণ" required style="padding:15px; width:85%; margin-bottom:15px; border:1px solid #ccc; border-radius:8px;"><br>
            <button type="submit" style="padding:15px 30px; background:#007bff; color:white; border:none; border-radius:8px; width:85%; font-size:16px;">রিকোয়েস্ট সাবমিট করুন</button>
        </form>
        <br><a href="/dashboard/{user_id}">ড্যাশবোর্ডে ফিরে যান</a>
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
        return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1>✅ আবেদন সফল!</h1><p>আপনার উইথড্র রিকোয়েস্ট পেন্ডিং আছে।</p><a href='/dashboard/{uid}'>ফিরে যান</a></div>"
    return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1 style='color:red;'>❌ ব্যালেন্স পর্যাপ্ত নয়!</h1><a href='/dashboard/{uid}'>ফিরে যান</a></div>"

# ================= এডমিন প্যানেল (Web) =================

@app.route('/admin/panel', methods=['GET', 'POST'])
def admin_web_panel():
    s = get_settings()
    if request.method == 'POST':
        # সেটিংস আপডেট লজিক
        update_data = {
            "bot_name": request.form.get('bot_name'),
            "logo": request.form.get('logo'),
            "currency": request.form.get('currency'),
            "monetag_id": request.form.get('monetag_id'),
            "min_withdraw": float(request.form.get('min_withdraw')),
            "per_click": float(request.form.get('per_click')),
            "per_ref": float(request.form.get('per_ref'))
        }
        settings_col.update_one({"id": "config"}, {"$set": update_data})
        return redirect('/admin/panel')

    # ইউজার লিস্ট এবং সার্চ
    query = request.args.get('search')
    if query:
        users = users_col.find({"user_id": int(query)})
    else:
        users = users_col.find().limit(50)

    return render_template_string(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Web Admin</title>
    <style>
        body{{font-family:sans-serif; background:#f8f9fa; padding:20px;}}
        .box{{background:#fff; padding:20px; border-radius:10px; box-shadow:0 2px 10px #ddd; margin-bottom:20px;}}
        input{{padding:10px; margin:5px 0; width:100%; box-sizing:border-box;}}
        table{{width:100%; border-collapse:collapse; margin-top:20px;}}
        th, td{{padding:12px; border:1px solid #ddd; text-align:left;}}
        th{{background:#eee;}}
    </style></head>
    <body>
        <h2>🛠 এডমিন কন্ট্রোল প্যানেল</h2>
        
        <div class="box">
            <h3>⚙️ বোট সেটিংস আপডেট করুন</h3>
            <form method="POST">
                বোটের নাম: <input type="text" name="bot_name" value="{s['bot_name']}">
                লোগো লিঙ্ক: <input type="text" name="logo" value="{s['logo']}">
                কারেন্সি: <input type="text" name="currency" value="{s['currency']}">
                মনিটেগ জোন আইডি: <input type="text" name="monetag_id" value="{s['monetag_id']}">
                মিনিমাম উইথড্র: <input type="number" step="0.1" name="min_withdraw" value="{s['min_withdraw']}">
                ক্লিক বোনাস: <input type="number" step="0.01" name="per_click" value="{s['per_click']}">
                রেফার বোনাস: <input type="number" step="0.01" name="per_ref" value="{s['per_ref']}">
                <button type="submit" style="background:blue; color:white; padding:15px; width:100%; border:none; border-radius:5px; cursor:pointer;">সেটিংস সেভ করুন</button>
            </form>
        </div>

        <div class="box">
            <h3>👥 ইউজার ম্যানেজমেন্ট</h3>
            <form method="GET">
                <input type="number" name="search" placeholder="ইউজার আইডি দিয়ে সার্চ দিন" style="width:70%;">
                <button type="submit" style="padding:10px; width:28%;">সার্চ</button>
            </form>
            <table>
                <tr><th>আইডি</th><th>নাম</th><th>ব্যালেন্স</th><th>অ্যাকশন</th></tr>
                {"".join([f"<tr><td>{u['user_id']}</td><td>{u['name']}</td><td>{u['balance']:.2f}</td><td><a href='/admin/edit/{u['user_id']}'>এডিট</a></td></tr>" for u in users])}
            </table>
        </div>
    </body>
    </html>
    """)

@app.route('/admin/edit/<int:uid>', methods=['GET', 'POST'])
def edit_user_bal(uid):
    user = users_col.find_one({"user_id": uid})
    if request.method == 'POST':
        new_bal = float(request.form.get('balance'))
        if request.form.get('action') == "delete":
            users_col.delete_one({"user_id": uid})
            return redirect('/admin/panel')
        users_col.update_one({"user_id": uid}, {"$set": {"balance": new_bal}})
        return redirect('/admin/panel')
    
    return f"""
    <div style='padding:50px; font-family:sans-serif;'>
        <h2>ইউজার এডিট: {user['name']} ({uid})</h2>
        <form method='POST'>
            ব্যালেন্স: <input type='number' step='0.1' name='balance' value='{user['balance']}' style='padding:10px; width:200px;'><br><br>
            <button type='submit' name='action' value='update' style='background:green; color:white; padding:10px;'>আপডেট</button>
            <button type='submit' name='action' value='delete' style='background:red; color:white; padding:10px;'>ইউজার ডিলিট</button>
        </form>
        <br><a href='/admin/panel'>ফিরে যান</a>
    </div>
    """

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
    return "<h1>Bot is Running Perfectly!</h1>", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
