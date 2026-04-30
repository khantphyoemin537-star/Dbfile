import pymongo
import io
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telethon import TelegramClient, events

# --- Render Port Error ကို ဖြေရှင်းရန် Fake Server ---
def run_fake_server():
    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running!")
    
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Background thread မှာ server ကို run ထားမယ်
threading.Thread(target=run_fake_server, daemon=True).start()

# --- သင်၏ မူလ Bot Code များ ---
API_ID = 37675502
API_HASH = "45955dc059f23ca5bfa3dcaff9c0f032"
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

bot1 = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
client_mongo = pymongo.MongoClient(MONGO_URI)

@bot1.on(events.NewMessage(pattern=r'^dbထဲသိမ်းထားတာအကုန်ပြအုံး$'))
async def send_db_full_report(event):
    if event.sender_id != OWNER_ID: return
    status_msg = await event.respond("📊 **Database တစ်ခုလုံးကို စကင်ဖတ်ပြီး File ထုတ်ပေးနေပါတယ်...**")
    try:
        output_text = "📊 Dexter Morgan's Database Full Inventory Report\n" + "=" * 60 + "\n\n"
        db_names = client_mongo.list_database_names()
        for db_name in db_names:
            if db_name in ['admin', 'local', 'config']: continue
            output_text += f"📂 DATABASE: {db_name}\n"
            db = client_mongo[db_name]
            for col_name in db.list_collection_names():
                docs = list(db[col_name].find())
                count = len(docs)
                output_text += f"   ├── Collection: {col_name} [Total: {count}]\n"
                if count > 0:
                    for i, doc in enumerate(docs, 1):
                        doc.pop('_id', None)
                        output_text += f"   │   ({i}) {doc}\n"
                else:
                    output_text += "   │   (No data found)\n"
                output_text += "   │\n"
            output_text += "—" * 40 + "\n\n"
        file_buffer = io.BytesIO(output_text.encode('utf-8'))
        file_buffer.name = "BoDx_Full_Database.txt"
        await bot1.send_file(event.chat_id, file_buffer, caption="✅ **DB စာရင်းနှင့် Data အကုန်လုံးကို File ထဲမှာ စီပေးထားပါတယ် Dexter။**")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")

print("🚀 Bot is starting with Port bypass...")
bot1.run_until_disconnected()
