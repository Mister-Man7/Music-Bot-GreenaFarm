import logging
import os
import asyncio

from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram import enums
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream, AudioQuality

from queue_manager import MusicQueue
from youtube import search_youtube, get_stream_url

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

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
userbot_username = None


@pytgcalls.on_stream_end()
async def on_stream_end(client, update):
    chat_id = update.chat_id
    logging.info(f"Lagu selesai di {chat_id}, auto next...")
    await play_next(chat_id)


async def ensure_userbot_in_group(chat_id: int) -> bool:
    """Cek apakah userbot sudah ada di grup. Return True kalau sudah."""
    try:
        member = await userbot.get_chat_member(chat_id, "me")
        if member.status in [
            enums.ChatMemberStatus.MEMBER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        ]:
            return True
        return False
    except Exception:
        return False


async def play_next(chat_id: int):
    track = queue.next(chat_id)
    if not track:
        try:
            await pytgcalls.leave_call(chat_id)
        except Exception:
            pass
        return
    url = await get_stream_url(track["url"])
    await pytgcalls.play(
        chat_id,
        MediaStream(
            url,
            audio_parameters=AudioQuality.HIGH,
            video_flags=MediaStream.Flags.IGNORE,
        )
    )
    await bot.send_message(
        chat_id,
        f"▶️ Sekarang diputar:\n🎵 {track['title']}\n⏱ Durasi: {track['duration']}"
    )


# ===== HANDLER: Bot di-add ke grup =====
@bot.on_message(filters.new_chat_members)
async def bot_added_to_group(client: Client, message: Message):
    """Otomatis kirim pesan setup waktu bot di-add ke grup."""
    bot_me = await bot.get_me()
    for member in message.new_chat_members:
        if member.id == bot_me.id:
            # Bot baru di-add ke grup ini
            uname = f"@{userbot_username}" if userbot_username else "akun musik"
            await message.reply(
                "👋 Halo! Makasih udah add gw ke grup ini!\n\n"
                "⚙️ Sebelum bisa dipakai, ada beberapa langkah setup:\n\n"
                f"1️⃣ Add {uname} ke grup ini\n"
                f"2️⃣ Jadikan {uname} sebagai Admin (dengan izin Manage Voice Chats)\n"
                "3️⃣ Aktifkan Voice Chat di grup (klik nama grup → Voice Chat)\n\n"
                "Setelah selesai, ketik /play nama_lagu dan musik siap diputar! 🎵\n\n"
                "Ketik /setup kapanpun untuk lihat panduan ini lagi."
            )
            break


@bot.on_message(filters.command("play") & filters.group)
async def play(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.command[1:]:
        await message.reply("❌ Contoh: /play Judul Lagu")
        return

    query = " ".join(message.command[1:])
    msg = await message.reply("🔍 Mencari lagu...")

    # Cek userbot ada di grup
    if not await ensure_userbot_in_group(chat_id):
        uname = f"@{userbot_username}" if userbot_username else "akun musik"
        await msg.edit(
            f"❌ Setup belum selesai!\n\n"
            f"Silakan add {uname} ke grup ini dan jadikan Admin terlebih dahulu.\n"
            f"Ketik /setup untuk panduan lengkap."
        )
        return

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
        await msg.edit(f"➕ Ditambahkan ke queue:\n🎵 {track['title']}\n📋 Posisi: #{queue.position(chat_id)}")
        return

    queue.add(chat_id, track)

    try:
        await msg.edit("⏳ Menyiapkan musik...")
        url = await get_stream_url(result["url"])
        logging.info(f"Stream URL: {url[:80]}")

        await pytgcalls.play(
            chat_id,
            MediaStream(
                url,
                audio_parameters=AudioQuality.HIGH,
                video_flags=MediaStream.Flags.IGNORE,
            )
        )
        queue.set_playing(chat_id, True)
        await msg.edit(
            f"▶️ Sekarang diputar:\n🎵 {track['title']}\n"
            f"⏱ Durasi: {track['duration']}\n"
            f"👤 Diminta oleh: {track['requested_by']}"
        )
        logging.info(f"Berhasil play di {chat_id}")

    except Exception as e:
        logging.error(f"Error play: {type(e).__name__}: {e}")
        if "voice chat" in str(e).lower() or "groupcall" in str(e).lower():
            await msg.edit("❌ Voice Chat belum aktif!\nKlik nama grup → Voice Chat → Start Voice Chat dulu ya!")
        else:
            await msg.edit(f"❌ Error: {type(e).__name__}\n{e}")
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
    queue.clear(chat_id)
    try:
        await pytgcalls.leave_call(chat_id)
    except Exception:
        pass
    await message.reply("⏹ Musik dihentikan!")


@bot.on_message(filters.command("queue") & filters.group)
async def show_queue(client: Client, message: Message):
    chat_id = message.chat.id
    tracks = queue.get_all(chat_id)
    if not tracks:
        await message.reply("📋 Queue kosong!")
        return
    text = "📋 Queue Musik:\n"
    for i, track in enumerate(tracks):
        prefix = "▶️" if i == 0 else f"{i}."
        text += f"{prefix} {track['title']} | {track['requested_by']} | {track['duration']}\n"
    await message.reply(text)


@bot.on_message(filters.command("pause") & filters.group)
async def pause(client: Client, message: Message):
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸ Musik dijeda!")
    except Exception as e:
        await message.reply(f"❌ {e}")


@bot.on_message(filters.command("resume") & filters.group)
async def resume(client: Client, message: Message):
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ Musik dilanjutkan!")
    except Exception as e:
        await message.reply(f"❌ {e}")


@bot.on_message(filters.command("setup"))
async def setup_cmd(client: Client, message: Message):
    uname = f"@{userbot_username}" if userbot_username else "akun musik"
    await message.reply(
        "⚙️ Panduan Setup Bot Music:\n\n"
        f"1️⃣ Add {uname} ke grup\n"
        f"2️⃣ Jadikan {uname} Admin (izin: Manage Voice Chats)\n"
        "3️⃣ Aktifkan Voice Chat di grup\n"
        "4️⃣ Ketik /play nama_lagu\n\n"
        "Command yang tersedia:\n"
        "/play judul - Putar lagu\n"
        "/skip - Skip lagu\n"
        "/pause - Jeda\n"
        "/resume - Lanjutkan\n"
        "/stop - Stop musik\n"
        "/queue - Lihat antrian"
    )


@bot.on_message(filters.command(["start", "help"]))
async def help_cmd(client: Client, message: Message):
    uname = f"@{userbot_username}" if userbot_username else "akun musik"
    await message.reply(
        "🎵 Bot Music\n\n"
        "Command:\n"
        "/play judul - Putar lagu dari YouTube\n"
        "/skip - Skip lagu\n"
        "/pause - Jeda musik\n"
        "/resume - Lanjutkan musik\n"
        "/stop - Stop musik\n"
        "/queue - Lihat antrian\n"
        "/setup - Panduan setup\n\n"
        f"Butuh bantuan setup? Ketik /setup"
    )


async def main():
    global userbot_username
    await userbot.start()
    await pytgcalls.start()
    await bot.start()
    me = await userbot.get_me()
    userbot_username = me.username or str(me.id)
    print(f"✅ Bot music aktif! Userbot: @{userbot_username}")
    await idle()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
