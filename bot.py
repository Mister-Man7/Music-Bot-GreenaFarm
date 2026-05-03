import asyncio
import logging
import os

from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

from queue_manager import MusicQueue
from youtube import search_youtube, get_stream_url

# ==========================================
# KONFIGURASI — dari environment variable Railway
# ==========================================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
SESSION_STRING = os.environ["SESSION_STRING"]  # generate pakai gen_session.py
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Inisialisasi client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(userbot)

queue = MusicQueue()


async def play_next(chat_id: int):
    """Mainkan lagu berikutnya di queue."""
    track = queue.next(chat_id)
    if not track:
        await pytgcalls.leave_call(chat_id)
        return

    url = await get_stream_url(track["url"])
    await pytgcalls.change_stream(chat_id, MediaStream(url))
    await app.send_message(
        chat_id,
        f"▶️ *Sekarang diputar:*\n🎵 {track['title']}\n⏱ Durasi: {track['duration']}",
        parse_mode="markdown"
    )


@app.on_message(filters.command("play") & filters.group)
async def play(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.command[1:]:
        await message.reply("❌ Contoh: `/play Judul Lagu`", parse_mode="markdown")
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

    # Cek apakah sudah ada yang main
    if queue.is_playing(chat_id):
        queue.add(chat_id, track)
        await msg.edit(
            f"➕ *Ditambahkan ke queue:*\n🎵 {track['title']}\n"
            f"📋 Posisi: #{queue.position(chat_id)}",
            parse_mode="markdown"
        )
        return

    queue.add(chat_id, track)
    url = await get_stream_url(result["url"])

    try:
        await pytgcalls.join_group_call(chat_id, MediaStream(url))
        queue.set_playing(chat_id, True)
        await msg.edit(
            f"▶️ *Sekarang diputar:*\n🎵 {track['title']}\n"
            f"⏱ Durasi: {track['duration']}\n"
            f"👤 Diminta oleh: {track['requested_by']}",
            parse_mode="markdown"
        )
    except Exception as e:
        await msg.edit(f"❌ Gagal join voice chat!\nPastikan ada voice chat aktif di grup.\n\n`{e}`", parse_mode="markdown")
        queue.clear(chat_id)


@app.on_message(filters.command("skip") & filters.group)
async def skip(client: Client, message: Message):
    chat_id = message.chat.id

    if not queue.is_playing(chat_id):
        await message.reply("❌ Tidak ada lagu yang sedang diputar!")
        return

    await message.reply("⏭ Melewati lagu...")
    await play_next(chat_id)


@app.on_message(filters.command("stop") & filters.group)
async def stop(client: Client, message: Message):
    chat_id = message.chat.id

    if not queue.is_playing(chat_id):
        await message.reply("❌ Tidak ada lagu yang sedang diputar!")
        return

    queue.clear(chat_id)
    await pytgcalls.leave_call(chat_id)
    await message.reply("⏹ Musik dihentikan dan bot keluar dari voice chat!")


@app.on_message(filters.command("queue") & filters.group)
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

    await message.reply(text, parse_mode="markdown")


@app.on_message(filters.command("pause") & filters.group)
async def pause(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply("⏸ Musik dijeda!")
    except Exception:
        await message.reply("❌ Tidak ada musik yang diputar!")


@app.on_message(filters.command("resume") & filters.group)
async def resume(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply("▶️ Musik dilanjutkan!")
    except Exception:
        await message.reply("❌ Tidak ada musik yang dijeda!")


@app.on_message(filters.command("help") & filters.group)
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
        parse_mode="markdown"
    )


async def main():
    await userbot.start()
    await pytgcalls.start()
    await app.start()
    print("✅ Bot music aktif!")
    await idle()
    await app.stop()
    await userbot.stop()


if __name__ == "__main__":
    asyncio.run(main())
