import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.enums import ChatMemberStatus

# ================== SOZLAMALAR ==================

TOKEN = os.getenv("TOKEN")

SPONSOR_CHANNEL = "@photos_just"      # PUBLIC homiy kanal
PRIVATE_STORAGE = -1003585163421     # maxfiy kanal ID

# ================== BOT ==================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== DATABASE ==================
db = sqlite3.connect("videos.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    downloads INTEGER,
    created TEXT
)
""")
db.commit()

# ================== USER OXIRGI KODI ==================
user_last_code = {}

# ================== OBUNA TEKSHIRISH ==================
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=SPONSOR_CHANNEL,
            user_id=user_id
        )
        return member.status not in (
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED
        )
    except:
        return False

# ================== TUGMA ==================
def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Homiy kanalga obuna bo‘lish",
                url=f"https://t.me/{SPONSOR_CHANNEL.replace('@','')}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Obunani tekshirish",
                callback_data="check_sub"
            )
        ]
    ])

# ================== VIDEO YUBORISH ==================
async def send_video_by_code(chat_id: int, code: str):
    cur.execute(
        "SELECT file_id, downloads FROM videos WHERE code=?",
        (code,)
    )
    row = cur.fetchone()

    if not row:
        await bot.send_message(chat_id, "❌ Bu kod bo‘yicha video topilmadi.")
        return

    file_id, downloads = row

    await bot.send_video(chat_id, file_id)

    cur.execute(
        "UPDATE videos SET downloads=? WHERE code=?",
        (downloads + 1, code)
    )
    db.commit()

    await bot.send_message(
        chat_id,
        f"📊 Yuklab olinganlar soni: {downloads + 1}"
    )

# ================== START ==================
@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "🎬 Kino botga xush kelibsiz!\n\n"
        "📩 3 xonali kodni yuboring."
    )

# ================== KOD QABUL QILISH ==================
@dp.message(F.text.regexp(r"^\d{3}$"))
async def code_handler(message: Message):
    code = message.text
    user_id = message.from_user.id

    user_last_code[user_id] = code

    if not await check_sub(user_id):
        await message.answer(
            "📢 Avval homiy kanalga obuna bo‘ling:",
            reply_markup=subscribe_keyboard()
        )
        return

    await send_video_by_code(message.chat.id, code)

# ================== OBUNANI TEKSHIRISH ==================
@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id

    if not await check_sub(user_id):
        await callback.answer(
            "❌ Hali obuna bo‘lmagansiz",
            show_alert=True
        )
        return

    code = user_last_code.get(user_id)
    if not code:
        await callback.message.answer(
            "❗ Kod topilmadi, iltimos qayta yuboring."
        )
        return

    await send_video_by_code(callback.message.chat.id, code)

# ================== ADMIN: VIDEO QO‘SHISH ==================
@dp.channel_post(F.video)
async def add_video(channel_post: Message):
    if channel_post.chat.id != PRIVATE_STORAGE:
        return

    if not channel_post.caption:
        return

    code = channel_post.caption.strip()

    if not code.isdigit() or len(code) != 3:
        return

    cur.execute(
        "INSERT OR REPLACE INTO videos VALUES (?, ?, ?, ?)",
        (code, channel_post.video.file_id, 0, datetime.now().isoformat())
    )
    db.commit()

    await bot.send_message(
        channel_post.chat.id,
        f"✅ Video saqlandi | Kod: {code}"
    )

# ================== 24 SOATDAN KEYIN O‘CHIRISH ==================
async def auto_cleanup():
    while True:
        limit = (datetime.now() - timedelta(hours=24)).isoformat()
        cur.execute("DELETE FROM videos WHERE created < ?", (limit,))
        db.commit()
        await asyncio.sleep(3600)

# ================== RUN ==================
async def main():
    asyncio.create_task(auto_cleanup())
    print("🤖 Bot ishga tushdi")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

