import pymongo
import io
import os
from telethon import TelegramClient, events

# --- Config ---
API_ID = 37675502
API_HASH = "45955dc059f23ca5bfa3dcaff9c0f032"
BOT_TOKEN = "8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

bot1 = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
client_mongo = pymongo.MongoClient(MONGO_URI)

@bot1.on(events.NewMessage(pattern=r'^dbထဲသိမ်းထားတာအကုန်ပြအုံး$'))
async def list_db_files(event):
    if event.sender_id != OWNER_ID:
        return

    status_msg = await event.respond("📁 **Database Structure ကို စစ်ဆေးနေပါတယ်...**")

    try:
        report = "📂 **Dexter's DB Structure (File Names Only)**\n"
        report += "=" * 45 + "\n\n"

        db_names = client_mongo.list_database_names()
        
        for db_name in db_names:
            if db_name in ['admin', 'local', 'config']: 
                continue
            
            report += f"📁 DB: **{db_name}**\n"
            db = client_mongo[db_name]
            
            col_names = db.list_collection_names()
            for col in col_names:
                count = db[col].count_documents({})
                report += f"   ├── 📄 `{col}` ({count} docs)\n"
            report += "\n"

        # စာသားနည်းနည်းပဲမို့လို့ File မဟုတ်ဘဲ Message နဲ့ပဲ တန်းပို့ပေးလိုက်မယ်
        await status_msg.edit(report)
        
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")

print("🚀 DB List Bot is running...")
bot1.run_until_disconnected()
