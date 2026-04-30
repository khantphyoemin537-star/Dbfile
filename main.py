import pymongo
import io
import os
from telethon import TelegramClient, events

# --- Environment Variables (GitHub/Cloud မှာ တင်ရင် ပိုလုံခြုံအောင် သုံးသင့်သည်) ---
# တိုက်ရိုက် ရေးချင်ရင်လည်း အောက်က "" ထဲမှာ အစားထိုးနိုင်ပါတယ်
API_ID = 37675502
API_HASH = "45955dc059f23ca5bfa3dcaff9c0f032"
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597

# MongoDB URI
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

# Bot နှင့် Mongo ကို ချိတ်ဆက်ခြင်း
bot1 = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
client_mongo = pymongo.MongoClient(MONGO_URI)

@bot1.on(events.NewMessage(pattern=r'^dbထဲသိမ်းထားတာအကုန်ပြအုံး$'))
async def send_db_full_report(event):
    # Dexter Morgan တစ်ယောက်တည်းသာ သုံးခွင့်ရှိစေရန်
    if event.sender_id != OWNER_ID:
        return

    status_msg = await event.respond("📊 **Database တစ်ခုလုံးကို စကင်ဖတ်ပြီး File ထုတ်ပေးနေပါတယ်...**")

    try:
        output_text = "📊 Dexter Morgan's Database Full Inventory Report\n"
        output_text += "=" * 60 + "\n\n"

        # Database အားလုံးကို ယူခြင်း
        db_names = client_mongo.list_database_names()
        
        found_data = False
        for db_name in db_names:
            if db_name in ['admin', 'local', 'config']: 
                continue
            
            found_data = True
            output_text += f"📂 DATABASE: {db_name}\n"
            db = client_mongo[db_name]
            
            # Collection အားလုံးကို ယူခြင်း
            for col_name in db.list_collection_names():
                docs = list(db[col_name].find())
                count = len(docs)
                
                output_text += f"   ├── Collection: {col_name} [Total: {count}]\n"
                
                # အထဲက Data များကို List အလိုက် ဖော်ပြခြင်း
                if count > 0:
                    for i, doc in enumerate(docs, 1):
                        doc.pop('_id', None) # ID ကို ဖျက်ထုတ်သည်
                        output_text += f"   │   ({i}) {doc}\n"
                else:
                    output_text += "   │   (No data found)\n"
                output_text += "   │\n"
            output_text += "—" * 40 + "\n\n"

        if not found_data:
            output_text += "⚠️ မည်သည့် Database မှ ရှာမတွေ့ပါ။"

        # Memory ထဲမှာ File အဖြစ် တည်ဆောက်ခြင်း
        file_buffer = io.BytesIO(output_text.encode('utf-8'))
        file_buffer.name = "BoDx_Full_Database.txt"

        # File အဖြစ် ပို့ပေးခြင်း
        await bot1.send_file(
            event.chat_id, 
            file_buffer, 
            caption=f"✅ **DB စာရင်းနှင့် Data အကုန်လုံးကို File ထဲမှာ စီပေးထားပါတယ် Dexter။**",
            reply_to=event.id
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit(f"❌ Error ဖြစ်သွားပါတယ်: `{str(e)}`")

# Bot ကို Run ခြင်း
print("🚀 GitHub Main Bot is running...")
bot1.run_until_disconnected()
