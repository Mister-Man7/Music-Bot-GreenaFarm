import logging
import os
import asyncio

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream

from queue_manager import MusicQueue
from youtube import search_youtube, get_stream_url

# ==========================================
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

userbot = Client(
    name="userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

bot = Client(
    name="bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

pytgcalls = PyTgCalls(userbot)
queue = MusicQueue()


async def play_next(chat_id: int):
    track = queue.next(chat_id)
    if not track:
        await pytgcalls.leave_call(chat_id)
        return
    url = await get_stream_url(track["url"])
    await pytgcalls.play(chat_id, MediaStream(url))
    await bot.send_message(
        chat_id,
        f"▶️ *Sekarang diputar:*\n🎵 {track['title']}\n⏱ Durasi: {track['duration']}",
        parse_mode=enums.ParseMode.MARKDOWN
    )


@bot.on_message(filters.command("play") & filters.group)
async def play(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.command[1:]:
        await message.reply("❌ Contoh: `/play Judul Lagu`", parse_mode=enums.ParseMode.MARKDOWN)
        return

    query = " ".join(message.command[1:])
    msg = await message.reply("🔍 Mencari lagu...")

    result = await search_youtube(query)
    if not result:
        await msg.edit("❌ Lagu tidak ditemukan!")
        return

    track = {
        "title": result["title"],
        "url": result["url"],
        "duration": result["duration"],
        "requested_by": message.from_user.first_name
    }

    if queue.is_playing(chat_id):
        queue.add(chat_id, track)
        await msg.edit(
            f"➕ *Ditambahkan ke queue:*\n🎵 {track['title']}\n📋 Posisi: #{queue.position(chat_id)}",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    queue.add(chat_id, track)
    url = await get_stream_url(result["url"])

    try:
        await pytgcalls.play(chat_id, MediaStream(url))
        queue.set_playing(chat_id, True)
        await msg.edit(
            f"▶️ *Sekarang diputar:*\n🎵 {track['title']}\n"
            f"⏱ Durasi: {track['duration']}\n"
            f"👤 Diminta oleh: {track['requested_by']}",
            parse_mode=enums.ParseMode.MARKDOWN
        )
    except Exception as e:
        await msg.edit(
            f"❌ Gagal join voice chat!\n"
            f"Pastikan ada voice chat aktif di grup.\n\n`{e}`",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        queue.clear(chat_id)


@bot.on_message(filters.command("skip") & filters.group)
async def skip(client: Client, message: Message):
    chat_id = message.chat.id
    if not queue.is_playing(chat_id):
        await message.reply("❌ Tidak ada lagu yang sedang diputar!")
        return
    await message.reply("⏭ Melewati lagu...")
    await play_next(chat_id)


@bot.on_message(filters.command("stop") & filters.group)
async def stop(client: Client, message: Message):
    chat_id = message.chat.id
    if not queue.is_playing(chat_id):
        await message.reply("❌ Tidak ada lagu yang sedang diputar!")
        return
    queue.clear(chat_id)
    await pytgcalls.leave_call(chat_id)
    await message.reply("⏹ Musik dihentikan!")


@bot.on_message(filters.command("queue") & filters.group)
async def show_queue(client: Client, message: Message):
    chat_id = message.chat.id
    tracks = queue.get_all(chat_id)
    if not tracks:
        await message.reply("📋 Queue kosong!")
        return
    text = "📋 *Queue Musik:*\n━━━━━━━━━━━━━━━━━━\n"
    for i, track in enumerate(tracks):
        prefix = "▶️" if i == 0 else f"{i}."
        text += f"{prefix} {track['title']}\n    👤 {track['requested_by']} | ⏱ {track['duration']}\n"
    await message.reply(text, parse_mode=enums.ParseMode.MARKDOWN)


@bot.on_message(filters.command("pause") & filters.group)
async def pause(client: Client, message: Message):
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸ Musik dijeda!")
    except Exception:
        await message.reply("❌ Tidak ada musik yang diputar!")


@bot.on_message(filters.command("resume") & filters.group)
async def resume(client: Client, message: Message):
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ Musik dilanjutkan!")
    except Exception:
        await message.reply("❌ Tidak ada musik yang dijeda!")


@bot.on_message(filters.command(["start", "help"]))
async def help_cmd(client: Client, message: Message):
    await message.reply(
        "🎵 *Bot Music — Daftar Command:*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "▶️ /play <judul> — Putar lagu dari YouTube\n"
        "⏭ /skip — Lewati lagu sekarang\n"
        "⏸ /pause — Jeda musik\n"
        "▶️ /resume — Lanjutkan musik\n"
        "⏹ /stop — Hentikan & keluar voice chat\n"
        "📋 /queue — Lihat antrian lagu\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 Pastikan ada *Voice Chat aktif* di grup sebelum /play!",
        parse_mode=enums.ParseMode.MARKDOWN
    )


async def main():
    await userbot.start()
    await pytgcalls.start()
    await bot.start()
    print("✅ Bot music aktif!")
    await idle()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
