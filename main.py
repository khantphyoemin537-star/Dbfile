import os
import asyncio
import random
import logging

from telethon import TelegramClient, events
from pymongo import MongoClient
from datetime import datetime, timedelta

# =========================================================
# CONFIG
# =========================================================

# --- Configuration ---
# ကိုကို ပေးထားတဲ့ Token အသစ်
BOT_TOKEN = "8738081667:AAGr7HkSxO6nC_QhPJJElKR2VKABTEDfNEo"

# အရင် main.py ထဲက အချက်အလက်အမှန်များ
API_ID = 23971901
API_HASH = "80562ca6c0e57209304381393699b007"
MONGO_URI = "mongodb+srv://khantthurain2024:khantthurain2024@cluster0.e6tms.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# သခင်လေး Dexter ရဲ့ ID (Admin Command တွေအတွက်)
OWNER_ID = 6006155986 


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)

# =========================================================
# DATABASE
# =========================================================

try:
    client_db = MongoClient(MONGO_URI)
    client_db.admin.command("ping")
    print("✅ MongoDB Connected")
except Exception as e:
    print("❌ MongoDB Error:", e)

db = client_db["telegram_bot"]

xp_col = db["user_reputation"]
couple_col = db["daily_couples"]
real_couple_col = db["real_life_couples"]

# =========================================================
# BOT
# =========================================================

bot = TelegramClient(
    "bod_bot_session",
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)

# =========================================================
# MEMORY
# =========================================================

xp_cooldown = {}

# =========================================================
# HELPERS
# =========================================================

def escape_html(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

def bq(text):
    return f"<blockquote>{text}</blockquote>"

# =========================================================
# XP SYSTEM
# =========================================================

async def save_xp_to_db(user_id, chat_id, added_xp):

    user_data = xp_col.find_one({
        "user_id": user_id,
        "chat_id": chat_id
    })

    if not user_data:

        xp_col.insert_one({
            "user_id": user_id,
            "chat_id": chat_id,
            "xp": added_xp,
            "level": 1
        })

        return added_xp, 1, False

    current_xp = user_data.get("xp", 0) + added_xp
    current_level = user_data.get("level", 1)

    # LEVEL XP
    next_level_xp = current_level * 2000

    level_up = False

    if current_xp >= next_level_xp:
        current_level += 1
        level_up = True

    xp_col.update_one(
        {
            "user_id": user_id,
            "chat_id": chat_id
        },
        {
            "$set": {
                "xp": current_xp,
                "level": current_level
            }
        }
    )

    return current_xp, current_level, level_up

# =========================================================
# AUTO XP
# =========================================================

@bot.on(events.NewMessage)
async def xp_system(event):

    try:

        if event.is_private:
            return

        if not event.sender:
            return

        if event.sender.bot:
            return

        if not event.raw_text:
            return

        # SHORT MESSAGE BLOCK
        if len(event.raw_text) < 3:
            return

        user_id = event.sender_id
        chat_id = event.chat_id

        key = f"{chat_id}:{user_id}"

        now = datetime.now()

        # 30 SEC COOLDOWN
        if key in xp_cooldown:

            if now - xp_cooldown[key] < timedelta(seconds=30):
                return

        xp_cooldown[key] = now

        added_xp = random.randint(5, 15)

        xp, level, level_up = await save_xp_to_db(
            user_id,
            chat_id,
            added_xp
        )

        # LEVEL UP MESSAGE
        if level_up:

            mention = (
                f"<a href='tg://user?id={user_id}'>"
                f"{escape_html(event.sender.first_name or 'User')}"
                f"</a>"
            )

            await event.reply(
                bq(
                    f"🎉 LEVEL UP!\n\n"
                    f"{mention} reached Level {level}!"
                ),
                parse_mode="html"
            )

    except Exception as e:
        print("XP ERROR:", e)

# =========================================================
# RANK COMMAND
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/rank$"))
async def show_rank(event):

    try:

        user_id = event.sender_id

        if event.is_reply:
            reply = await event.get_reply_message()
            user_id = reply.sender_id

        user_data = xp_col.find_one({
            "user_id": user_id,
            "chat_id": event.chat_id
        })

        if not user_data:
            return await event.reply(
                bq(
                    "Reputation Record မရှိသေးပါဘူး။"
                ),
                parse_mode="html"
            )

        level = user_data.get("level", 1)
        xp = user_data.get("xp", 0)

        ranks = {
            1: "Recruit",
            5: "Watcher",
            10: "Elite",
            20: "Shadow Knight",
            35: "Warlord",
            50: "Sovereign",
            100: "Immortal"
        }

        rank_name = next(
            (
                name
                for lv, name in sorted(
                    ranks.items(),
                    reverse=True
                )
                if level >= lv
            ),
            "Recruit"
        )

        next_level_xp = level * 2000

        progress = int(
            (xp / next_level_xp) * 100
        )

        if progress > 100:
            progress = 100

        filled = "█" * (progress // 10)
        empty = "░" * (10 - (progress // 10))

        bar = filled + empty

        res = (
            f"📊 <b>BOD REPUTATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Rank: <b>{rank_name}</b>\n"
            f"🆙 Level: <b>{level}</b>\n"
            f"✨ XP: <b>{xp}</b>\n"
            f"🎯 Next Level: <b>{next_level_xp}</b>\n"
            f"📈 [{bar}] {progress}%\n"
            f"━━━━━━━━━━━━━━━━━━"
        )

        await event.reply(
            bq(res),
            parse_mode="html"
        )

    except Exception as e:
        print("RANK ERROR:", e)

# =========================================================
# TOP COMMAND
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/top$"))
async def leaderboard(event):

    try:

        top_users = xp_col.find({
            "chat_id": event.chat_id
        }).sort("xp", -1).limit(10)

        text = "🏆 <b>BOD TOP USERS</b>\n\n"

        count = 1

        async for user in _async_cursor(top_users):

            try:
                entity = await bot.get_entity(
                    user["user_id"]
                )

                name = escape_html(
                    entity.first_name or "User"
                )

                text += (
                    f"{count}. {name}\n"
                    f"Level: {user['level']} | "
                    f"XP: {user['xp']}\n\n"
                )

                count += 1

            except:
                pass

        await event.reply(
            bq(text),
            parse_mode="html"
        )

    except Exception as e:
        print("TOP ERROR:", e)

# =========================================================
# HELPER
# =========================================================

async def _async_cursor(cursor):
    for doc in cursor:
        yield doc

# =========================================================
# ADD REAL COUPLE
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/addcouple"))
async def add_real_couple(event):

    try:

        if event.sender_id != OWNER_ID:
            return await event.reply(
                bq("Owner Only Command"),
                parse_mode="html"
            )

        if not event.is_reply:
            return await event.reply(
                bq(
                    "Reply User + /addcouple @username"
                ),
                parse_mode="html"
            )

        reply = await event.get_reply_message()

        u1_id = reply.sender_id

        parts = event.text.split()

        if len(parts) < 2:
            return await event.reply(
                bq("Need Username"),
                parse_mode="html"
            )

        try:
            u2 = await bot.get_entity(parts[1])
            u2_id = u2.id

        except:
            return await event.reply(
                bq("User Not Found"),
                parse_mode="html"
            )

        real_couple_col.update_one(
            {"user_id": u1_id},
            {
                "$set": {
                    "partner": u2_id
                }
            },
            upsert=True
        )

        real_couple_col.update_one(
            {"user_id": u2_id},
            {
                "$set": {
                    "partner": u1_id
                }
            },
            upsert=True
        )

        await event.reply(
            bq("✅ Couple Saved"),
            parse_mode="html"
        )

    except Exception as e:
        print("ADD COUPLE ERROR:", e)

# =========================================================
# DAILY COUPLE
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/couple$"))
async def daily_couple(event):

    try:

        if event.is_private:
            return

        chat_id = event.chat_id

        today = datetime.now().strftime("%Y-%m-%d")

        existing = couple_col.find_one({
            "chat_id": chat_id,
            "date": today
        })

        if existing:

            return await event.reply(
                bq(
                    f"❤️ Today's Couple\n\n"
                    f"{existing['couple_text']}"
                ),
                parse_mode="html"
            )

        participants = await bot.get_participants(
            chat_id
        )

        real_users = [
            doc["user_id"]
            for doc in real_couple_col.find()
        ]

        eligible = [
            u.id
            for u in participants
            if not u.bot
            and u.id not in real_users
        ]

        if len(eligible) < 2:

            return await event.reply(
                bq("Not Enough Users"),
                parse_mode="html"
            )

        c1_id, c2_id = random.sample(
            eligible,
            2
        )

        u1 = await bot.get_entity(c1_id)
        u2 = await bot.get_entity(c2_id)

        mention1 = (
            f"<a href='tg://user?id={c1_id}'>"
            f"{escape_html(u1.first_name or 'User')}"
            f"</a>"
        )

        mention2 = (
            f"<a href='tg://user?id={c2_id}'>"
            f"{escape_html(u2.first_name or 'User')}"
            f"</a>"
        )

        couple_text = (
            f"{mention1} ❤️ {mention2}"
        )

        couple_col.insert_one({
            "chat_id": chat_id,
            "date": today,
            "users": [c1_id, c2_id],
            "couple_text": couple_text
        })

        await event.reply(
            bq(
                f"🏹 <b>Daily Couple</b>\n\n"
                f"{couple_text}"
            ),
            parse_mode="html"
        )

    except Exception as e:
        print("COUPLE ERROR:", e)

# =========================================================
# START
# =========================================================

print("✅ BoD Bot Running...")

bot.run_until_disconnected()
