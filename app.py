import os
from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# --- আপনার মংগোডিবি কানেকশন ---
MONGO_URI = "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['quran_db']
collection = db['surahs']

# --- স্টাইল এবং ডিজাইন ---
COMMON_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&family=Noto+Sans+Bengali:wght@400;700&display=swap');
    body { font-family: 'Noto Sans Bengali', sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }
    .header { background: #1b5e20; color: white; text-align: center; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
    .container { max-width: 900px; margin: 20px auto; padding: 20px; background: white; border-radius: 15px; box-shadow: 0 5px 25px rgba(0,0,0,0.1); }
    .surah-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }
    .surah-card { background: #fff; border: 1px solid #ddd; padding: 20px; text-align: center; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; transition: 0.3s; }
    .surah-card:hover { background: #1b5e20; color: white; transform: translateY(-5px); }
    .verse-box { margin-bottom: 25px; padding: 20px; border-bottom: 1px solid #eee; }
    .arabic { font-family: 'Amiri', serif; font-size: 34px; text-align: right; color: #2e7d32; direction: rtl; line-height: 2.0; margin-bottom: 15px; }
    .bangla { font-size: 19px; color: #444; line-height: 1.8; }
    .btn { background: #27ae60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; border: none; cursor: pointer; display: inline-block; }
    #status { margin-top: 20px; font-weight: bold; color: #d35400; }
    progress { width: 100%; height: 25px; margin-top: 15px; }
</style>
"""

@app.route('/')
def index():
    surahs = list(collection.find({}, {"_id": 0, "id": 1, "name": 1, "transliteration": 1}).sort("id", 1))
    if not surahs:
        return render_template_string("""
        <html><head>"""+COMMON_STYLE+"""</head><body style="text-align:center; padding:100px;">
        <div class="container">
            <h2>ডাটাবেস খালি</h2>
            <p>১১৪টি সুরা সেটআপ করতে নিচের বাটনে ক্লিক করুন।</p>
            <a href="/setup" class="btn">সেটআপ করুন</a>
        </div>
        </body></html>
        """)
    
    html = f"<html><head><title>আল-কুরআন</title>{COMMON_STYLE}</head><body>"
    html += "<div class='header'><h1>আল-কুরআন মাজীদ</h1></div><div class='container'><div class='surah-list'>"
    for s in surahs:
        html += f"<a href='/surah/{s['id']}' class='surah-card'><b>{s['id']}. {s['transliteration']}</b><br><small>{s['name']}</small></a>"
    html += "</div></div></body></html>"
    return html

@app.route('/surah/<int:surah_id>')
def surah_detail(surah_id):
    surah = collection.find_one({"id": surah_id}, {"_id": 0})
    if not surah: return "সুরা পাওয়া যায়নি", 404
    html = f"<html><head><title>{surah['transliteration']}</title>{COMMON_STYLE}</head><body>"
    html += f"<div class='header'><a href='/' style='color:white;text-decoration:none;float:left;'>← ফিরে যান</a><h1>{surah['transliteration']}</h1></div>"
    html += "<div class='container'>"
    for v in surah['verses']:
        html += f"<div class='verse-box'><p class='arabic'>{v['text']}</p><p class='bangla'><b>{v['id']}.</b> {v['translation_bn']}</p></div>"
    html += "</div></body></html>"
    return html

@app.route('/setup')
def setup_page():
    return render_template_string("""
    <html><head><title>কুরআন সেটআপ</title>"""+COMMON_STYLE+"""</head>
    <body style="text-align:center; padding:50px;">
        <div class="container">
            <h2>১১৪টি সুরা সেটআপ</h2>
            <p id="msg">এই প্রক্রিয়ায় ১-২ মিনিট সময় লাগতে পারে।</p>
            <button id="startBtn" class="btn" onclick="startSetup()">শুরু করুন</button>
            <div id="status"></div>
            <progress id="prog" value="0" max="114" style="display:none;"></progress>
        </div>

        <script>
            async function startSetup() {
                const status = document.getElementById('status');
                const btn = document.getElementById('startBtn');
                const prog = document.getElementById('prog');
                btn.style.display = 'none';
                prog.style.display = 'block';
                status.innerText = "ফাইল ডাউনলোড হচ্ছে (১৫ এমবি)...";

                try {
                    // JSDelivr CDN ব্যবহার করা হয়েছে যা দ্রুত এবং স্ট্যাবল
                    const response = await fetch('https://cdn.jsdelivr.net/gh/itshatim/quran-json@master/dist/quran_bn.json');
                    let text = await response.text();
                    
                    // এরর ফিক্স: অদৃশ্য ক্যারেক্টার (BOM) মুছে ফেলা
                    text = text.replace(/^\\uFEFF/, '');
                    
                    const data = JSON.parse(text);
                    status.innerText = "আপলোড শুরু হয়েছে... পেজ বন্ধ করবেন না।";
                    
                    for(let i=0; i < data.length; i++) {
                        await fetch('/api/add_surah', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(data[i])
                        });
                        prog.value = i + 1;
                        status.innerText = "সুরক্ষিতভাবে আপলোড হচ্ছে: " + (i+1) + " / 114";
                    }

                    status.innerHTML = "<h3 style='color:green;'>সাফল্যের সাথে ১১৪টি সুরা সেটআপ হয়েছে!</h3><br><a href='/' class='btn'>হোম পেজে যান</a>";
                } catch (err) {
                    status.innerHTML = "<span style='color:red;'>ভুল হয়েছে: " + err + "</span><br><br><button class='btn' onclick='location.reload()'>আবার চেষ্টা করুন</button>";
                }
            }
        </script>
    </body></html>
    """)

@app.route('/api/add_surah', methods=['POST'])
def add_surah():
    data = request.json
    collection.replace_one({"id": data['id']}, data, upsert=True)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
