import os
import requests
from flask import Flask, render_template_string, redirect, url_for
from pymongo import MongoClient

app = Flask(__name__)

# --- কনফিগারেশন ---
# Vercel-এ ডিপ্লয় করার সময় Environment Variable হিসেবে MONGODB_URI সেট করবেন।
# লোকাল পিসিতে টেস্ট করার জন্য নিচে আপনার লিঙ্কটি দিন।
MONGO_URI = os.getenv("MONGODB_URI", "আপনার_মংগোডিবি_লিঙ্ক_এখানে_দিন")
client = MongoClient(MONGO_URI)
db = client['quran_db']
collection = db['surahs']

# --- HTML ডিজাইন (একই ফাইলে) ---
LAYOUT_STYLE = """
<style>
    body { font-family: 'SolaimanLipi', Arial, sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; }
    .header { background: #27ae60; color: white; text-align: center; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .container { max-width: 800px; margin: 20px auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .surah-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
    .surah-card { background: #fff; border: 1px solid #ddd; padding: 15px; text-align: center; border-radius: 8px; text-decoration: none; color: #333; font-weight: bold; transition: 0.2s; }
    .surah-card:hover { background: #27ae60; color: white; border-color: #27ae60; }
    .verse-box { border-bottom: 1px solid #eee; padding: 20px 0; }
    .arabic { font-size: 30px; text-align: right; color: #1a5276; margin-bottom: 10px; direction: rtl; font-family: 'Traditional Arabic', serif; }
    .bangla { font-size: 18px; color: #444; line-height: 1.8; }
    .btn { background: #27ae60; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px; }
</style>
"""

# --- রুটস (Routes) ---

@app.route('/')
def index():
    # ডাটাবেস থেকে সুরার লিস্ট আনা
    surahs = list(collection.find({}, {"_id": 0, "id": 1, "name": 1, "transliteration": 1}).sort("id", 1))
    
    if not surahs:
        return f"""
        <div style="text-align:center; padding:50px; font-family:Arial;">
            <h2>আপনার ডাটাবেস খালি!</h2>
            <p>প্রথমে ডাটাবেসে ১১৪টি সুরা আপলোড করতে নিচের বাটনে ক্লিক করুন:</p>
            <a href="/setup" style="background:green; color:white; padding:15px; text-decoration:none; border-radius:5px;">১১৪টি সুরা আপলোড করুন</a>
        </div>
        """
    
    html = f"<html><head><title>আল-কুরআন</title>{LAYOUT_STYLE}</head><body>"
    html += "<div class='header'><h1>আল-কুরআন (বাংলা ও আরবি)</h1></div>"
    html += "<div class='container'><div class='surah-list'>"
    for s in surahs:
        html += f"<a href='/surah/{s['id']}' class='surah-card'>{s['id']}. {s['transliteration']}<br><small>{s['name']}</small></a>"
    html += "</div></div></body></html>"
    return html

@app.route('/surah/<int:surah_id>')
def surah_detail(surah_id):
    surah = collection.find_one({"id": surah_id}, {"_id": 0})
    if not surah: return "সুরা পাওয়া যায়নি!", 404
    
    html = f"<html><head><title>{surah['transliteration']}</title>{LAYOUT_STYLE}</head><body>"
    html += f"<div class='header'><h1>{surah['id']}. {surah['transliteration']} ({surah['name']})</h1><a href='/' style='color:white;'>← ফিরে যান</a></div>"
    html += "<div class='container'>"
    for v in surah['verses']:
        html += f"<div class='verse-box'><p class='arabic'>{v['text']}</p><p class='bangla'><b>[{v['id']}]</b> {v['translation_bn']}</p></div>"
    html += "</div></body></html>"
    return html

# --- ১১৪টি সুরা অটো-আপলোড করার ম্যাজিক রুট ---
@app.route('/setup')
def setup():
    try:
        url = "https://raw.githubusercontent.com/itshatim/quran-json/master/dist/quran_bn.json"
        data = requests.get(url).json()
        collection.delete_many({})  # আগের ডাটা মুছে ফেলা
        collection.insert_many(data) # নতুন ১১৪টি সুরা ঢুকানো
        return "<h1>অভিনন্দন! ১১৪টি সুরা আপনার ডাটাবেসে সফলভাবে লোড হয়েছে।</h1><a href='/'>হোম পেজে যান</a>"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
