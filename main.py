"""
main.py - Titik Mula Utama (Main Entrypoint) Telegram AI Agent.

Mengendalikan penyambungan ke Telegram Bot API menggunakan `python-telegram-bot`,
menyediakan arahan /start, /clear, /help, /image, /voice, /video,
serta memproses perbualan teks dan alatan multimedia secara autonomi.
"""

import os
import sys
import re
import asyncio
import logging
from typing import List
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest, NetworkError, TimedOut

from database import init_db, clear_conversation_history
from agent import AIAgent

# Muat turun konfigurasi daripada fail .env
load_dotenv()

# Konfigurasi Sistem Log
logging.basicConfig(
    format="%(asctime)s - [%(name)s] [%(levelname)s] - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("TelegramAIAgent")

# Kurangkan kebisingan log daripada pustaka luar
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Inisialisasi Ejen AI Global
ai_agent = AIAgent()

# Corak RegEx untuk mengesan tag media yang dihasilkan oleh alatan
MEDIA_PATTERN = re.compile(r"\[MEDIA:(IMAGE|VOICE|VIDEO):([^\]]+)\]")


def split_message(text: str, max_chars: int = 4000) -> List[str]:
    """
    Memecahkan teks panjang kepada beberapa bahagian yang selamat
    untuk mengelakkan had maksima 4096 aksara mesej Telegram.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    lines = text.split("\n")
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            while len(line) > max_chars:
                chunks.append(line[:max_chars])
                line = line[max_chars:]
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


async def send_safe_reply(update: Update, text: str) -> None:
    """
    Menghantar mesej teks kepada pengguna dengan percubaan Markdown dahulu.
    Jika berlaku ralat format Markdown, mesej dihantar sebagai teks biasa.
    """
    if not update.effective_chat or not text:
        return

    chunks = split_message(text)
    for chunk in chunks:
        try:
            await update.effective_chat.send_message(
                text=chunk,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            logger.warning(f"Gagal menghantar format Markdown ({e}), menghantar teks biasa...")
            await update.effective_chat.send_message(
                text=chunk,
                parse_mode=None,
            )


async def send_response_with_media(update: Update, text: str) -> None:
    """
    Memeriksa sama ada teks mengandungi tag fail media [MEDIA:TYPE:path].
    Jika ada, fail foto, suara, atau video dihantar terus ke Telegram
    bersama teks pengesahan sebagai kapsyen.
    """
    if not update.effective_chat or not text:
        return

    media_matches = MEDIA_PATTERN.findall(text)
    clean_text = MEDIA_PATTERN.sub("", text).strip()

    if media_matches:
        for media_type, file_path in media_matches:
            if os.path.exists(file_path):
                caption = clean_text[:1024] if clean_text else None
                try:
                    if media_type == "IMAGE":
                        with open(file_path, "rb") as f:
                            await update.effective_chat.send_photo(photo=f, caption=caption)
                    elif media_type == "VOICE":
                        with open(file_path, "rb") as f:
                            await update.effective_chat.send_voice(voice=f, caption=caption)
                    elif media_type == "VIDEO":
                        with open(file_path, "rb") as f:
                            await update.effective_chat.send_video(video=f, caption=caption)
                    # Kapsyen telah dihantar bersama media
                    clean_text = clean_text[1024:] if clean_text else ""
                except Exception as e:
                    logger.error(f"Ralat menghantar media Telegram ({media_type}): {e}")
                    clean_text += f"\n\n(Fail disimpan di pelayan: {file_path})"

    # Hantar baki teks jika masih ada
    if clean_text:
        await send_safe_reply(update, clean_text)


# =====================================================================
# Pengendali Arahan Asas (Core Command Handlers)
# =====================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Arahan /start: Memberikan mesej alu-aluan mesra dalam Bahasa Melayu.
    """
    user = update.effective_user
    first_name = user.first_name if user else "Kawan"

    welcome_message = (
        f"👋 **Hai, {first_name}! Selamat datang ke Ejen AI Telegram Pintar!** ✨\n\n"
        "Saya ialah pembantu peribadi maya anda yang dikuasakan oleh **Google Gemini** "
        "dan dilengkapi pelbagai kemahiran canggih:\n\n"
        "🛠️ **Kemahiran Utama:**\n"
        "• 💬 **Perbualan Pintar:** Tanya apa sahaja dalam Bahasa Melayu.\n"
        "• 🧠 **Ingatan Konteks:** Saya mengingati perbualan terdahulu kita.\n"
        "• ⏰ **Waktu Malaysia:** Semakan masa & tarikh tepat tempatan.\n"
        "• 📝 **Simpan Nota:** Simpan memo atau senarai tugasan to-do.\n"
        "• 🎨 **Jana Gambar AI:** Lukis apa jua gambar mengikut permintaan!\n"
        "• 🎙️ **Mesej Suara (Voice):** Ubah teks kepada suara pertuturan audio.\n"
        "• 🎬 **Jana Video:** Hasilkan video animasi sinematik MP4.\n\n"
        "📌 **Arahan Pantas:**\n"
        "• `/image <prompt>` - Terus lukis gambar AI\n"
        "• `/voice <teks>` - Terus tukar teks kepada suara\n"
        "• `/video <prompt>` - Terus jana video sinematik\n"
        "• `/clear` - Kosongkan ingatan perbualan\n"
        "• `/help` - Panduan lengkap & contoh soalan\n\n"
        "Anda juga boleh terus meminta secara santai seperti:\n"
        "_\"Tolong lukiskan gambar kucing comel\"_ atau _\"Bercakap guna suara\"_! 🚀"
    )

    await send_safe_reply(update, welcome_message)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Arahan /clear: Mengosongkan ingatan perbualan pengguna daripada SQLite.
    """
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    deleted_count = await clear_conversation_history(user_id)

    reply_message = (
        "🧹 **Ingatan Perbualan Dikosongkan!**\n\n"
        f"Sejarah perbualan terdahulu ({deleted_count} mesej) telah dipadam daripada memori.\n"
        "Kita kini boleh memulakan topik baharu dengan segar! ✨\n\n"
        "💡 _Nota peribadi anda di dalam pangkalan data tetap selamat dan tidak dipadam._"
    )

    await send_safe_reply(update, reply_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Arahan /help: Panduan lengkap penggunaan dan contoh interaksi multimedia.
    """
    help_message = (
        "📖 **Panduan Penggunaan Ejen AI Telegram**\n\n"
        "Anda boleh berinteraksi secara biasa atau menggunakan arahan pantas:\n\n"
        "1. 🎨 **Penjanaan Gambar AI:**\n"
        "   - Dalam chat: _\"Tolong lukiskan gambar pemandangan kampung waktu senja\"_\n"
        "   - Arahan: `/image seekor harimau belang memakai sut angkasa`\n\n"
        "2. 🎙️ **Pesanan Suara (Voice Note):**\n"
        "   - Dalam chat: _\"Boleh jawab guna suara ucapan selamat pagi?\"_\n"
        "   - Arahan: `/voice Selamat pagi! Semoga hari anda dipenuhi kejayaan.`\n\n"
        "3. 🎬 **Penjanaan Video Sinematik:**\n"
        "   - Dalam chat: _\"Tolong buatkan video ombak pantai waktu malam\"_\n"
        "   - Arahan: `/video aurora beralun indah di langit malam`\n\n"
        "4. 📝 **Pengurusan Nota Peribadi (SQLite):**\n"
        "   - Simpan: _\"Catat nota: beli tiket tren esok\"_\n"
        "   - Semak: _\"Tunjukkan senarai nota saya\"_\n"
        "   - Padam: _\"Padam nota 1\"_\n\n"
        "5. ⏰ **Waktu & Tarikh Malaysia:**\n"
        "   - _\"Pukul berapa sekarang di KL?\"_\n\n"
        "6. 🧹 **Reset Memori:** Gunakan `/clear` untuk memulakan semula perbualan.\n\n"
        "Cuba sekarang dan lihat keajaiban AI anda! ✨"
    )
    await send_safe_reply(update, help_message)


# =====================================================================
# Pengendali Arahan Multimedia (Direct Multimedia Handlers)
# =====================================================================

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Arahan /image <prompt>: Menjana dan menghantar gambar AI secara terus."""
    if not context.args:
        await send_safe_reply(
            update,
            "🎨 **Sila masukkan keterangan gambar yang diingini!**\n\n"
            "Contoh penggunaan:\n"
            "`/image kucing comel sedang membaca buku di perpustakaan`"
        )
        return

    prompt = " ".join(context.args).strip()
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
    except Exception:
        pass

    status_msg = await update.effective_chat.send_message("🎨 Sedang melukis gambar anda... Sila tunggu sebentar.")

    try:
        from media_generator import generate_image
        img_path = await asyncio.to_thread(generate_image, prompt)
        with open(img_path, "rb") as photo_file:
            await update.effective_chat.send_photo(
                photo=photo_file,
                caption=f"✨ **Hasil Gambar:**\n_{prompt}_",
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Ralat dalam /image: {e}")
        await status_msg.edit_text(f"⚠️ Maaf, gagal menjana gambar: {e}")


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Arahan /voice <teks>: Menukar teks kepada pesanan suara secara terus."""
    if not context.args:
        await send_safe_reply(
            update,
            "🎙️ **Sila masukkan teks yang ingin dituturkan!**\n\n"
            "Contoh penggunaan:\n"
            "`/voice Hai semua! Jangan lupa minum air secukupnya hari ini ya.`"
        )
        return

    text = " ".join(context.args).strip()
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
    except Exception:
        pass

    status_msg = await update.effective_chat.send_message("🎙️ Sedang merakam audio suara AI...")

    try:
        from media_generator import generate_voice
        voice_path = await asyncio.to_thread(generate_voice, text)
        with open(voice_path, "rb") as voice_file:
            await update.effective_chat.send_voice(
                voice=voice_file,
                caption=f"🗣️ _{text[:120]}_",
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Ralat dalam /voice: {e}")
        await status_msg.edit_text(f"⚠️ Maaf, gagal menjana suara: {e}")


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Arahan /video <prompt>: Menjana dan menghantar video sinematik secara terus."""
    if not context.args:
        await send_safe_reply(
            update,
            "🎬 **Sila masukkan keterangan video yang diingini!**\n\n"
            "Contoh penggunaan:\n"
            "`/video matahari terbenam perlahan di tepi pantai tropika`"
        )
        return

    prompt = " ".join(context.args).strip()
    chat_id = update.effective_chat.id

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
    except Exception:
        pass

    status_msg = await update.effective_chat.send_message("🎬 Sedang merender video sinematik... Ini mengambil masa beberapa saat.")

    try:
        from media_generator import generate_video
        video_path = await asyncio.to_thread(generate_video, prompt)
        with open(video_path, "rb") as video_file:
            await update.effective_chat.send_video(
                video=video_file,
                caption=f"🎥 **Video Sinematik:**\n_{prompt}_",
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Ralat dalam /video: {e}")
        await status_msg.edit_text(f"⚠️ Maaf, gagal menjana video: {e}")


# =====================================================================
# Pengendali Mesej Teks Perbualan (Message Handler)
# =====================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Memproses sebarang mesej teks perbualan biasa pengguna.
    AI boleh secara autonomi membuat keputusan memanggil alatan teks atau multimedia.
    """
    if not update.message or not update.message.text or not update.effective_user:
        return

    user_id = update.effective_user.id
    user_text = update.message.text.strip()

    # Beri maklum balas visual bahawa bot sedang berfikir
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )
    except Exception:
        pass

    try:
        # Proses mesej bersama AI Agent
        ai_response = await ai_agent.process_message(
            user_id=user_id,
            user_message=user_text,
        )
        # Hantar mesej berserta media jika alatan multimedia dipanggil
        await send_response_with_media(update, ai_response)

    except Exception as e:
        logger.error(f"Ralat semasa memproses mesej: {e}", exc_info=True)
        fallback_msg = (
            "⚠️ **Maaf, berlaku sedikit ralat semasa memproses permintaan anda.**\n\n"
            "Sila cuba hantar semula mesej anda dalam beberapa saat. "
            "Jika masalah berterusan, gunakan perintah `/clear` untuk memulakan semula sesi."
        )
        await send_safe_reply(update, fallback_msg)


# =====================================================================
# Pengendali Ralat Global (Error Handler)
# =====================================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log ralat sistem dan elakkan bot daripada ranap."""
    logger.error("Pengecualian berlaku semasa mengendalikan kemas kini:", exc_info=context.error)

    if isinstance(context.error, (TimedOut, NetworkError)):
        logger.warning("Ralat rangkaian atau masa tamat dikesan daripada Telegram.")
        return

    if isinstance(update, Update) and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                text="⚠️ Maaf, terdapat ralat teknikal yang tidak dijangka. Sila cuba sebentar lagi.",
            )
        except Exception:
            pass


# =====================================================================
# Fungsi Permulaan Aplikasi (App Initializer)
# =====================================================================

async def post_init(application: Application) -> None:
    """Dijalankan selepas aplikasi dibina untuk memulakan pangkalan data."""
    logger.info("Memulakan struktur pangkalan data SQLite...")
    await init_db()
    logger.info("Pangkalan data sedia untuk beroperasi.")


def main() -> None:
    """Fungsi utama untuk memulakan bot Telegram."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not telegram_token or telegram_token == "your_telegram_bot_token_here":
        logger.error("=" * 60)
        logger.error("RALAT: TELEGRAM_BOT_TOKEN belum ditetapkan dalam fail .env!")
        logger.error("=" * 60)
        sys.exit(1)

    logger.info("Membina aplikasi Telegram bersama kemahiran Multimedia (Gambar, Video & Suara)...")
    application = (
        ApplicationBuilder()
        .token(telegram_token)
        .post_init(post_init)
        .build()
    )

    # Pendaftaran Pengendali Arahan (Commands)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CommandHandler("voice", voice_command))
    application.add_handler(CommandHandler("video", video_command))

    # Pendaftaran Pengendali Mesej Teks Biasa
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Pendaftaran Pengendali Ralat
    application.add_error_handler(error_handler)

    logger.info("Bot sedang berjalan menggunakan polling (Tekan Ctrl+C untuk berhenti)...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
