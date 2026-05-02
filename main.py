import asyncio
import pymongo
import random
import re
from telethon.sync import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
import dns.resolver

# Termux DNS Fix
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']

# --- CONFIGURATION ---
API_ID = 30765851
API_HASH = '235b0bc6f03767302dc75763508f7b75'
BOT_TOKEN = '8575371720:AAEWWV42CGrwooM_joiJXdo2iEw2_7atyXU'
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"

# Chat IDs & Owner
STRING_CHAT = -1003836655698
CONTROL_CHAT = -1003580630981
OWNER_ID = 6015356597

# DB Setup
client_mongo = pymongo.MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
autobio_col = db["autobio_col"]

bot = TelegramClient('main_autospam_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Global Variable for Master Spam Task
active_spam_task = None

# ==========================================
# ၁။ Session String များကို DB သို့ သိမ်းဆည်းခြင်း
# ==========================================
@bot.on(events.NewMessage(chats=STRING_CHAT, pattern=r'^/string$'))
async def save_session_string(event):
    reply = await event.get_reply_message()
    if reply and reply.text:
        if not autobio_col.find_one({"session": reply.text}):
            autobio_col.insert_one({"session": reply.text})
            await bot.send_message(event.chat_id, "✅ Session String ကို 'autobio_col' တွင် အောင်မြင်စွာ သိမ်းဆည်းလိုက်ပါပြီ။", reply_to=event.id)
        else:
            await bot.send_message(event.chat_id, "⚠️ ဤ String သည် Database တွင် ရှိနှင့်ပြီးဖြစ်ပါသည်။", reply_to=event.id)

# ==========================================
# ၂။ Bio ပြောင်းလဲခြင်း
# ==========================================
@bot.on(events.NewMessage(chats=CONTROL_CHAT, pattern=r'(?i)^Bioထား$'))
async def change_bio_cmd(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if not reply or not reply.text: return
    
    sessions = list(autobio_col.find())
    for s in sessions:
        asyncio.create_task(update_bio_task(s['session'], reply.text, event.chat_id, event.id))

async def update_bio_task(session_str, bio_text, chat_id, reply_id):
    user_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await user_client.connect()
        if await user_client.is_user_authorized():
            await user_client(UpdateProfileRequest(about=bio_text))
            await user_client.send_message(chat_id, f"✅ Bio အား '{bio_text}' သို့ ပြောင်းလဲပြီးပါပြီ။", reply_to=reply_id)
    except Exception:
        pass
    finally:
        if user_client.is_connected(): await user_client.disconnect()

# ==========================================
# ၃။ Auto Join (Account အကုန်မဝင်အောင် Limit လုပ်ထားသည်)
# ==========================================
@bot.on(events.NewMessage(chats=CONTROL_CHAT, pattern=r'(?i)^ဝင်လိုက်ကြ$'))
async def auto_join_cmd(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if not reply or not reply.text: return

    # Link ကို ရှာဖွေခြင်း (t.me/username သို့မဟုတ် t.me/+hash)
    link_match = re.search(r'(https?://t\.me/[^\s]+)', reply.text)
    if not link_match:
        return await event.respond("⚠️ Reply လုပ်ထားသောစာတွင် Telegram Link မတွေ့ပါ။")
    
    link = link_match.group(1)
    sessions = list(autobio_col.find())
    if not sessions: return

    # Account အကုန်မဝင်စေရန် ကျပန်း ၂ ခု သို့မဟုတ် ၃ ခုကိုသာ ရွေးချယ်မည်
    join_limit = min(3, len(sessions)) 
    target_sessions = random.sample(sessions, join_limit)
    
    await event.respond(f"⏳ Group လုံခြုံရေးအရ Account ({join_limit}) ခုဖြင့်သာ Group သို့ ဝင်ရောက်နေပါသည်...")

    for s in target_sessions:
        asyncio.create_task(join_group_task(s['session'], link, event.chat_id, event.id))

async def join_group_task(session_str, link, chat_id, reply_id):
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    try:
        await client.connect()
        if await client.is_user_authorized():
            if '+' in link or 'joinchat' in link:
                hash_val = link.split('/')[-1].replace('+', '')
                await client(ImportChatInviteRequest(hash_val))
            else:
                username = link.split('/')[-1]
                await client(JoinChannelRequest(username))
            
            await client.send_message(chat_id, f"✅ {link} သို့ အောင်မြင်စွာ ဝင်ရောက်ပြီးပါပြီ။", reply_to=reply_id)
    except Exception as e:
        await client.send_message(chat_id, f"❌ ဝင်ရောက်ရန် မအောင်မြင်ပါ: {str(e)}", reply_to=reply_id)
    finally:
        if client.is_connected(): await client.disconnect()

# ==========================================
# ၄။ လူခိုး Command - Master Spammer (၂ ခုထက်ပိုမပို့သောစနစ်)
# ==========================================
@bot.on(events.NewMessage(chats=CONTROL_CHAT, pattern=r'^လူခိုး\s*(\d+)min$'))
async def auto_spam_cmd(event):
    global active_spam_task
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if not reply or not reply.text: return
    
    minutes = int(event.pattern_match.group(1))
    spam_text = reply.text
    
    # ယခင် Run နေသော Spam Loop ရှိပါက ရပ်တန့်မည်
    if active_spam_task:
        active_spam_task.cancel()
    
    # Master Task အသစ်စတင်မည်
    active_spam_task = asyncio.create_task(master_spammer(spam_text, minutes, event.chat_id, event.id))

async def master_spammer(spam_text, mins, chat_id, reply_id):
    # စတင်ကြောင်း Owner ထံ အရင် Ack ပြန်ပို့မည် (Account တစ်ခုချင်းစီမှ)
    initial_sessions = list(autobio_col.find())
    for s in initial_sessions:
        client = TelegramClient(StringSession(s['session']), API_ID, API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                ack_msg = f"Group တိုင်းကိုလိုက်ပို့မည်\nပို့မည့်စာက \"{spam_text}\"\nအချိန်သတ်မှတ်ချက် {mins} မိနစ်တစ်ခါ"
                await client.send_message(chat_id, ack_msg, reply_to=reply_id)
        except Exception:
            pass
        finally:
            if client.is_connected(): await client.disconnect()

    # Main Spam Loop စတင်ခြင်း
    try:
        while True:
            sessions = list(autobio_col.find())
            # Group တစ်ခုကို အကောင့်ဘယ်နှစ်ခုက ပို့ပြီးပြီလဲ မှတ်သားမည့် Dictionary (Loop တစ်ပတ်တိုင်း အသစ်ပြန်စသည်)
            spammed_groups = {} 
            
            for s in sessions:
                user_client = TelegramClient(StringSession(s['session']), API_ID, API_HASH)
                try:
                    await user_client.connect()
                    if not await user_client.is_user_authorized():
                        continue
                    
                    async for dialog in user_client.iter_dialogs():
                        if dialog.is_group:
                            # ဒီ Group ကို ပို့ပြီးသား အကြိမ်အရေအတွက်ကို ယူမည်
                            current_count = spammed_groups.get(dialog.id, 0)
                            
                            # ၂ ကြိမ်အောက်သာ ပို့ရမည်
                            if current_count < 2:
                                try:
                                    await user_client.send_message(dialog.id, spam_text)
                                    spammed_groups[dialog.id] = current_count + 1
                                    await asyncio.sleep(2) # Flood wait မဖြစ်စေရန်
                                except Exception:
                                    pass # Mute ခံထားရပါက ကျော်သွားမည်
                except Exception:
                    pass
                finally:
                    if user_client.is_connected(): await user_client.disconnect()
            
            # သတ်မှတ်ထားသော မိနစ်ပြည့်အောင် စောင့်မည်
            await asyncio.sleep(mins * 60)
            
    except asyncio.CancelledError:
        print("ယခင် Spam Loop ကို ရပ်တန့်လိုက်ပါသည်။")

# ==========================================
print("🚀 Dexter's Super Spammer Bot စတင် အလုပ်လုပ်နေပါပြီ...")
bot.run_until_disconnected()
