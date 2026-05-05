import io
import asyncio
import logging
import random
import os
import threading
import re
from datetime import datetime, timedelta
import pytz
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events, types
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import (
    ChannelParticipantAdmin, 
    ChannelParticipantCreator, 
    ChannelParticipantsAdmins,
    ChatAdminRights
)
from html import escape as escape_html
from PIL import Image, ImageDraw, ImageFont, ImageOps
from groq import Groq
import random

# Groq AI Setup
ai_client = Groq(api_key="Gsk_JfStkGNmhK2o8Ef9KHXkWGdyb3FYgnGjZYLxI14q0IIiweu82iQc")
# ==========================================
# 🌐 DNS FIX FOR MONGODB
# ==========================================
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
except: pass

# ==========================================
# 🌐 FLASK KEEP-ALIVE
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "BoDx Sovereign System & Guard Squad Active!"

def run_flask(): 
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.ERROR)

# ==========================================
# ⚙️ CONFIGURATION & TOKENS
# ==========================================
BOT_TOKEN = "8738081667:AAGr7HkSxO6nC_QhPJJElKR2VKABTEDfNEo"
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
API_ID = 30765851
API_HASH = '235b0bc6f03767302dc75763508f7b75' 

# --- Database ---
client_db = MongoClient(MONGO_URI)
db = client_db["telegram_bot"]
xp_col = db["user_reputation"]
couple_col = db["daily_couples"]
real_couple_col = db["real_life_couples"]

bot = TelegramClient("bod_bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
xp_cooldown = {}

def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def bq(text):
    return f"<blockquote>{text}</blockquote>"

# --- Star & Rank Logic ---
def get_rank_info(level):
    ranks = {
        1: ("The Recruit", "⭐"),
        5: ("The Watcher", "⭐⭐"),
        10: ("The Enforcer", "⭐⭐⭐"),
        20: ("The Dark Knight", "⭐⭐⭐⭐"),
        50: ("The Sovereign", "⭐⭐⭐⭐⭐")
    }
    for lv in sorted(ranks.keys(), reverse=True):
        if level >= lv:
            return ranks[lv]
    return ranks[1]

# --- XP System ---
async def save_xp_to_db(user_id, chat_id, added_xp):
    user_data = xp_col.find_one({"user_id": user_id, "chat_id": chat_id})
    if not user_data:
        xp_col.insert_one({"user_id": user_id, "chat_id": chat_id, "xp": added_xp, "level": 1})
        return added_xp, 1, False

    current_xp = user_data.get("xp", 0) + added_xp
    current_level = user_data.get("level", 1)
    next_level_xp = current_level * 2000 # Hard Mode
    level_up = False

    if current_xp >= next_level_xp:
        current_level += 1
        level_up = True

    xp_col.update_one({"user_id": user_id, "chat_id": chat_id}, {"$set": {"xp": current_xp, "level": current_level}})
    return current_xp, current_level, level_up

@bot.on(events.NewMessage)
async def xp_system(event):
    if event.is_private or not event.sender or event.sender.bot or not event.raw_text: return
    if len(event.raw_text) < 3: return

    user_id, chat_id = event.sender_id, event.chat_id
    key = f"{chat_id}:{user_id}"
    now = datetime.now()

    if key in xp_cooldown and now - xp_cooldown[key] < timedelta(seconds=30): return
    xp_cooldown[key] = now

    xp, level, level_up = await save_xp_to_db(user_id, chat_id, random.randint(5, 15))
    if level_up:
        name, star = get_rank_info(level)
        mention = f"<a href='tg://user?id={user_id}'>{escape_html(event.sender.first_name)}</a>"
        await event.reply(bq(f"🌙 <b>Ascension Complete</b>\n\n{mention} သည် <b>{name}</b> {star} (Level {level}) သို့ ရောက်ရှိသွားပါပြီ။"), parse_mode="html")

@bot.on(events.NewMessage(pattern=r"^/rank$"))
async def show_rank(event):
    user_id = event.sender_id
    if event.is_reply:
        reply = await event.get_reply_message()
        user_id = reply.sender_id

    user_data = xp_col.find_one({"user_id": user_id, "chat_id": event.chat_id})
    if not user_data: return await event.reply(bq("Record မရှိသေးပါ။"))

    level, xp = user_data.get("level", 1), user_data.get("xp", 0)
    name, star = get_rank_info(level)
    next_level_xp = level * 2000
    progress = int((xp / next_level_xp) * 100)
    bar = "█" * (progress // 10) + "░" * (10 - (progress // 10))

    res = f"📊 <b>BOD REPUTATION</b>\n━━━━━━━━━━━━━━━━━━\n👤 Rank: <b>{name}</b>\n🎖️ Distinction: <b>{star}</b>\n🆙 Level: <b>{level}</b>\n✨ XP: <b>{xp}/{next_level_xp}</b>\n📈 [{bar}] {progress}%\n━━━━━━━━━━━━━━━━━━"
    await event.reply(bq(res), parse_mode="html")

@bot.on(events.NewMessage(pattern=r"^/addcouple"))
async def add_real_couple(event):
    if event.sender_id != OWNER_ID: return
    if not event.is_reply or len(event.text.split()) < 2: return await event.reply(bq("အသုံးပြုပုံ: Reply + /addcouple @username"))

    reply = await event.get_reply_message()
    u1_id = reply.sender_id
    try:
        u2 = await bot.get_entity(event.text.split()[1])
        u2_id = u2.id
    except: return await event.reply(bq("User မတွေ့ပါ။"))

    real_couple_col.update_one({"user_id": u1_id}, {"$set": {"partner": u2_id}}, upsert=True)
    real_couple_col.update_one({"user_id": u2_id}, {"$set": {"partner": u1_id}}, upsert=True)
    await event.reply(bq("✅ Couple Saved! သူတို့ကို Random စာရင်းထဲမှ ဖယ်ထုတ်ထားပါမည်။"))

@bot.on(events.NewMessage(pattern=r"^/couple$"))
async def daily_couple(event):
    if event.is_private: return
    chat_id, today = event.chat_id, datetime.now().strftime("%Y-%m-%d")
    existing = couple_col.find_one({"chat_id": chat_id, "date": today})
    if existing: return await event.reply(bq(f"❤️ Today's Couple\n\n{existing['couple_text']}"), parse_mode="html")

    participants = await bot.get_participants(chat_id)
    real_users = [doc["user_id"] for doc in real_couple_col.find()]
    eligible = [u.id for u in participants if not u.bot and u.id not in real_users]

    if len(eligible) < 2: return await event.reply(bq("လူမလုံလောက်ပါ။"))
    c1_id, c2_id = random.sample(eligible, 2)
    u1, u2 = await bot.get_entity(c1_id), await bot.get_entity(c2_id)
    couple_text = f"<a href='tg://user?id={c1_id}'>{escape_html(u1.first_name)}</a> ❤️ <a href='tg://user?id={c2_id}'>{escape_html(u2.first_name)}</a>"
    couple_col.insert_one({"chat_id": chat_id, "date": today, "couple_text": couple_text})
    await event.reply(bq(f"🏹 <b>Daily Couple</b>\n\n{couple_text}"), parse_mode="html")

if __name__ == "__main__":
    print("✅ BoDx Sovereign System & Flask Active...")
    
    # Flask ကို Thread တစ်ခုအနေနဲ့ နောက်ကွယ်မှာ run မယ်
    # ဒါမှ Render က Port ကို ရှာတွေ့မှာပါ
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Telegram Bot ကို Main Thread မှာ run မယ်
    bot.run_until_disconnected()
