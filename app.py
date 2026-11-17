"""
app.py - Pelayan Web Flask untuk Antaramuka Sembang Teks & Suara AI.

Menyediakan:
1. GET / : Halaman web interaktif (templates/index.html)
2. POST /api/chat : Menerima mesej teks, menjana jawapan ringkas melalui Gemini AI,
                    menjana audio suara, dan mengembalikan teks serta fail audio.
3. GET /api/audio/<filename> : Menyediakan fail audio untuk dimainkan oleh pelayar.
4. POST /api/clear : Mengosongkan sejarah perbualan.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

from google import genai
from google.genai import types

from media_generator import generate_voice, MEDIA_DIR
from tools import get_current_datetime

load_dotenv()

# Konfigurasi Log
logging.basicConfig(
    format="%(asctime)s - [%(name)s] [%(levelname)s] - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AIWebVoiceApp")

app = Flask(__name__)

# Konfigurasi Model & Klien GenAI
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Auto-remap model lapuk
if GEMINI_MODEL in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
    GEMINI_MODEL = "gemini-3.5-flash-lite"

# Sejarah sesi dalam ingatan pelayan (In-Memory perbualan web ringkas)
web_chat_history = []

SYSTEM_PROMPT_CONCISE = """
Anda ialah pembantu AI pintar yang bercakap secara langsung dengan pengguna melalui teks dan audio suara.

Garis Panduan Utama:
1. JAWAB SECARA SANGAT RINGKAS, PADAT, DAN TEPAT dalam Bahasa Melayu standard yang mesra dan semula jadi.
2. Panjang jawapan mestilah MAKSIMUM 1 HINGGA 3 AYAT sahaja (atau 2-3 poin ringkas), kerana jawapan anda akan terus dibacakan menjadi fail audio suara.
3. Jangan gunakan format yang rumit atau simbol pelik yang janggal dibaca oleh suara pertuturan.
4. Anda mempunyai akses kepada alatan fungsi get_current_datetime jika pengguna bertanya mengenai waktu/tarikh.
""".strip()


def get_genai_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Ralat GenAI Client: {e}")
        return None


@app.route("/")
def index():
    """Memaparkan halaman web utama."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Menerima soalan teks dan mengembalikan jawapan teks + audio suara."""
    global web_chat_history

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"status": "error", "error": "Mesej tidak boleh kosong."}), 400

    client = get_genai_client()
    if not client:
        return jsonify({
            "status": "error",
            "error": "GEMINI_API_KEY belum dikonfigurasi dalam fail .env."
        }), 500

    try:
        # Konfigurasi Ejen AI dengan alatan dan persona ringkas
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT_CONCISE,
            tools=[get_current_datetime],
            temperature=0.7,
        )

        # Bina sejarah perbualan (ambil 6 giliran terakhir)
        history_contents = []
        for item in web_chat_history[-6:]:
            history_contents.append(
                types.Content(
                    role=item["role"],
                    parts=[types.Part.from_text(text=item["text"])],
                )
            )

        # Jalankan sesi sembang
        chat = client.chats.create(
            model=GEMINI_MODEL,
            history=history_contents if history_contents else None,
            config=config,
        )
        response = chat.send_message(user_message)
        ai_reply = response.text.strip() if (response and response.text) else "Maaf, saya tidak dapat menjawab soalan tersebut."

        # Simpan ke sejarah perbualan sesi
        web_chat_history.append({"role": "user", "text": user_message})
        web_chat_history.append({"role": "model", "text": ai_reply})

        # Jana fail audio suara untuk jawapan AI
        audio_filename = None
        try:
            # Gunakan jawapan teks ringkas untuk audio
            audio_path = generate_voice(ai_reply)
            audio_filename = os.path.basename(audio_path)
            logger.info(f"Audio suara berjaya dihasilkan: {audio_filename}")
        except Exception as e:
            logger.warning(f"Gagal menjana suara untuk respons web: {e}")

        return jsonify({
            "status": "success",
            "text": ai_reply,
            "audio_url": f"/api/audio/{audio_filename}" if audio_filename else None,
        })

    except Exception as e:
        logger.error(f"Ralat dalam /api/chat: {e}", exc_info=True)
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/audio/<filename>")
def serve_audio(filename):
    """Menyajikan fail audio tempatan untuk dimainkan di pelayar web."""
    # Keselamatan: elakkan traversal direktori
    safe_filename = os.path.basename(filename)
    return send_from_directory(MEDIA_DIR, safe_filename)


@app.route("/api/clear", methods=["POST"])
def clear_api():
    """Mengosongkan sejarah perbualan sesi web."""
    global web_chat_history
    web_chat_history.clear()
    logger.info("Sejarah sembang web dikosongkan.")
    return jsonify({"status": "success", "message": "Sejarah dikosongkan."})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n========================================================")
    print(f"🚀 Laman Web Ejen AI Suara & Teks Sedang Berjalan!")
    print(f"👉 Buka pelayar anda di: http://localhost:{port}")
    print(f"========================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
