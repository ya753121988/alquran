import os
from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# --- ডাটাবেস কানেকশন ---
MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['quran_db']
collection = db['surahs']

# --- ডিজাইন (CSS) ---
COMMON_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri&family=Noto+Sans+Bengali:wght@400;700&display=swap');
    body { font-family: 'Noto Sans Bengali', sans-serif; background-color: #f0f4f8; margin: 0; padding: 0; }
    .header { background: #1b5e20; color: white; text-align: center; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .container { max-width: 900px; margin: 20px auto; padding: 15px; background: white; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
    .surah-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; }
    .surah-card { background: #fff; border: 1px solid #ddd; padding: 15px; text-align: center; border-radius: 10px; text-decoration: none; color: #333; font-weight: bold; transition: 0.3s; }
    .surah-card:hover { background: #1b5e20; color: white; transform: translateY(-3px); }
    .arabic { font-family: 'Amiri', serif; font-size: 32px; text-align: right; color: #2e7d32; direction: rtl; line-height: 1.8; margin: 15px 0; }
    .bangla { font-size: 18px; color: #444; line-height: 1.7; border-bottom: 1px solid #eee; padding-bottom: 15px; }
    .btn { background: #27ae60; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; border: none; cursor: pointer; }
    #status { margin-top: 20px; font-weight: bold; color: #d35400; }
</style>
"""

# --- পেজ টেমপ্লেটসমূহ ---

# হোম পেজ
@app.route('/')
def index():
    surahs = list(collection.find({}, {"_id": 0, "id": 1, "name": 1, "transliteration": 1}).sort("id", 1))
    if not surahs:
        return render_template_string("""
        <html><head>"""+COMMON_STYLE+"""</head><body style="text-align:center; padding:100px;">
        <h2>ডাটাবেসে কোনো সুরা নেই</h2>
        <a href="/setup" class="btn">সেটআপ পেজে যান</a>
        </body></html>
        """)
    
    html = f"<html><head><title>আল-কুরআন</title>{COMMON_STYLE}</head><body>"
    html += "<div class='header'><h1>আল-কুরআন মাজীদ</h1></div><div class='container'><div class='surah-list'>"
    for s in surahs:
        html += f"<a href='/surah/{s['id']}' class='surah-card'>{s['id']}. {s['transliteration']}<br><small>{s['name']}</small></a>"
    html += "</div></div></body></html>"
    return html

# সুরা পেজ
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

# --- স্মার্ট সেটআপ পেজ (জাভাস্ক্রিপ্ট ব্যবহার করে ডাটা আপলোড) ---
@app.route('/setup')
def setup_page():
    return render_template_string("""
    <html><head><title>কুরআন সেটআপ</title>"""+COMMON_STYLE+"""</head>
    <body style="text-align:center; padding:50px;">
        <div class="container">
            <h2>১১৪টি সুরা সেটআপ সিস্টেম</h2>
            <p>নিচের বাটনে ক্লিক করলে আপনার ব্রাউজার সরাসরি ইন্টারনেট থেকে ডাটা নিয়ে আপনার মংগোডিবি-তে সেভ করবে। এতে কোনো এরর আসবে না।</p>
            <button id="startBtn" class="btn" onclick="startSetup()">সেটআপ শুরু করুন</button>
            <div id="status">অপেক্ষা করুন...</div>
            <progress id="prog" value="0" max="114" style="width:100%; display:none;"></progress>
        </div>

        <script>
            async function startSetup() {
                const status = document.getElementById('status');
                const btn = document.getElementById('startBtn');
                const prog = document.getElementById('prog');
                btn.disabled = true;
                prog.style.display = 'block';
                status.innerText = "১১৪টি সুরার ফাইল ডাউনলোড হচ্ছে (১৫ এমবি), দয়া করে অপেক্ষা করুন...";

                try {
                    const response = await fetch('https://raw.githubusercontent.com/itshatim/quran-json/master/dist/quran_bn.json');
                    const data = await response.json();
                    
                    status.innerText = "ডাটাবেসে আপলোড শুরু হয়েছে... পেজ বন্ধ করবেন না।";
                    
                    // একে একে সুরা আপলোড করা যাতে টাইম আউট না হয়
                    for(let i=0; i < data.length; i++) {
                        await fetch('/api/add_surah', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(data[i])
                        });
                        prog.value = i + 1;
                        status.innerText = "আপলোড হচ্ছে: " + (i+1) + " / 114";
                    }

                    status.innerHTML = "সফলভাবে ১১৪টি সুরা আপলোড হয়েছে! <br><br> <a href='/' class='btn'>হোম পেজে যান</a>";
                } catch (err) {
                    status.innerText = "ভুল হয়েছে: " + err;
                    btn.disabled = false;
                }
            }
        </script>
    </body></html>
    """)

# ডাটা গ্রহণ করার API
@app.route('/api/add_surah', methods=['POST'])
def add_surah():
    data = request.json
    collection.replace_one({"id": data['id']}, data, upsert=True)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
