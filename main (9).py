import io
import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events, types
from telethon.tl.types import ChatAdminRights, ChannelParticipantsAdmins
from html import escape as escape_html

# ==========================================
# 🌐 FLASK KEEP-ALIVE
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "BoDx System Active!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'
BOT_TOKEN = "7857238353:AAEkDQnXqxyvXOQufwJwzZ7tXlwrmzM6XyI"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"]
allow_col = db["allowed_users"]

bot_client = TelegramClient('bot_session', APP_ID, APP_HASH)

# Bully Task တွေကို သိမ်းထားဖို့ Dictionary
bot_bully_tasks = {}

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def check_admin(chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        permissions = await bot_client.get_permissions(chat_id, user_id)
        return permissions.is_admin
    except: return False

# ==========================================
# 🛡️ COMMANDS SYSTEM
# ==========================================

# [1] /adm - Tag All Admins
@bot_client.on(events.NewMessage(pattern=r'^/adm(?:\s+(.*))?'))
async def tag_admins(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    text = event.pattern_match.group(1) or "Admins ခေါ်နေပါတယ်!"
    try:
        admins = await bot_client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        msg = f"📣 {escape_html(text)}\n\n"
        for a in admins:
            if not a.bot:
                msg += f"• <a href='tg://user?id={a.id}'>{escape_html(a.first_name)}</a>\n"
        await event.respond(bq(msg), parse_mode='html')
    except Exception as e:
        await event.respond(bq(f"Error: {e}"))

# [2] /padm - Promote Admin (Fixing Argument Error)
@bot_client.on(events.NewMessage(pattern=r'^/padm(?:@\w+)?$'))
async def promote_admin(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("Admin ပေးချင်တဲ့သူကို Reply ထောက်ပါ။"), parse_mode='html')
    
    promoter = await event.get_sender()
    target = await reply.get_sender()
    p_mention = f"<a href='tg://user?id={promoter.id}'>{escape_html(promoter.first_name)}</a>"
    t_mention = f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a>"
    
    # Rights Selection
    rights = ChatAdminRights(
        post_messages=True, add_admins=False, change_info=False,
        ban_users=False, anonymous=False, delete_messages=True,
        invite_users=True, pin_messages=True, edit_messages=True, manage_call=True
    )
    
    try:
        # Parameter တွေကို keyword အနေနဲ့ ပေးလိုက်ရင် Error မတက်တော့ပါဘူး
        await bot_client.edit_admin(event.chat_id, target.id, admin_rights=rights, rank="Admin")
        msg = (
            f"{p_mention} က {t_mention} သူ့ကို ADMIN ပေးထားလိုက်ပါပြီ။\n\n"
            f"သူ/သူမ၏ Admin Rights-\n"
            f"✅ Delete Messages\n✅ Pin Messages\n✅ Invite Users\n"
            f"✅ Manage Video Chats\n✅ Edit Messages\n"
            f"❌ Ban Users\n❌ Change Group Info\n❌ Remain Anonymous"
        )
        await event.respond(bq(msg), parse_mode='html')
    except Exception as e:
        await event.respond(bq(f"Error: {e}"), parse_mode='html')

# [3] /dadm - Dismiss Admin
@bot_client.on(events.NewMessage(pattern=r'^/dadm(?:@\w+)?$'))
async def demote_admin(event):
    if not await check_admin(event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("ရာထူးဖြုတ်ချင်တဲ့သူကို Reply ထောက်ပါ။"), parse_mode='html')
    
    empty_rights = ChatAdminRights(
        post_messages=False, add_admins=False, change_info=False, ban_users=False,
        anonymous=False, delete_messages=False, invite_users=False, pin_messages=False,
        edit_messages=False, manage_call=False
    )
    try:
        await bot_client.edit_admin(event.chat_id, reply.sender_id, admin_rights=empty_rights, rank="")
        target = await reply.get_sender()
        await event.respond(bq(f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a> ကို Admin အဖြစ်မှ ဖယ်ရှားလိုက်ပါပြီ။"), parse_mode='html')
    except Exception as e:
        await event.respond(bq(f"Error: {e}"), parse_mode='html')

# [4] /removeallow [id]
@bot_client.on(events.NewMessage(pattern=r'^/removeallow(?:@\w+)?\s+(\d+)'))
async def remove_allow(event):
    if event.sender_id != OWNER_ID: return
    target_id = int(event.pattern_match.group(1))
    res = allow_col.delete_one({"user_id": target_id})
    if res.deleted_count > 0:
        await event.respond(bq(f"User ID {target_id} ကို ပါမစ်မပေးတော့ဘူး"), parse_mode='html')
    else:
        await event.respond(bq("ဒီ User ID ကို List ထဲမှာ မတွေ့ပါ။"), parse_mode='html')

# [5] /b Bully - Fixed Logic
@bot_client.on(events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
async def bot_bully(event):
    if not is_allowed(event.sender_id): 
        return await event.reply(bq("မင်းမှာ ဒီ Command ကို သုံးပိုင်ခွင့်မရှိဘူး။သုံးခွင့်နဲ့အသုံးပြုနည်းများအတွက် @Besties_with_BoD ကိုလာ "), parse_mode='html')
    
    reply = await event.get_reply_message()
    if not reply: 
        return await event.respond(bq("ဘယ်ကောင့်ကို ခေါင်းမဖော်နိုင်အောင် ဆဲပေးရမလဲ၊Replyပြန်လိုက် "), parse_mode='html')

    try: await event.delete() # Command ကို ဖျက်တယ်
    except: pass

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t: return

    target_id = t.id
    if target_id == OWNER_ID:
        await event.respond(bq("ဟိတ်ကောင် Creatorကို ပြန်ပြီးဆဲဆိုခွင့် မပေးထားဘူး🔥"), parse_mode='html')
        return

    bot_bully_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"
    
    # DB က စာလုံးတွေကို ယူတယ်
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    if not words: 
        return await event.respond(bq("DB (filters collection) ထဲမှာ စာလုံးမရှိသေးဘူး Chief!"))

    await event.respond(bq(f"{mention} ကို ခေါင်းမဖော်နိုင်အောင် စဆဲပါပြီ။"), parse_mode='html')

    send_count = 0
    while bot_bully_tasks.get(chat_id):
        try: 
            await bot_client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id, parse_mode='html')
            send_count += 1
            if send_count >= 8: 
                await asyncio.sleep(1)
                send_count = 0 
            else: await asyncio.sleep(0.5) 
        except Exception:
            bot_bully_tasks[chat_id] = False
            break

# [6] /sb Stop Bully
@bot_client.on(events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    try: await event.delete() # Command ကို ဖျက်တယ်
    except: pass
    bot_bully_tasks[event.chat_id] = False
    await event.respond(bq("အခုနားဆိုလို့နားလိုက်မယ်၊စောက်ချိုးမပြေရင်ထပ်ဆဲပေးမယ်"), parse_mode='html')

# ==========================================
# 🚀 EXECUTION
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ BoDx System Online & Fixed!")
    await bot_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
