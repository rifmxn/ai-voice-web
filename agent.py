"""
agent.py - Modul Otak AI (Gemini AI Agent) untuk Telegram Bot.

Menggunakan SDK rasmi `google-genai` (Gemini API) untuk memproses mesej,
mengekalkan memori perbualan daripada SQLite, dan memanggil fungsi alatan
(function calling) secara autonomi.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Pastikan konfigurasi .env dimuat turun
load_dotenv()

from tools import (
    get_current_datetime,
    save_note,
    get_notes,
    delete_note,
    create_image,
    create_voice,
    create_video,
    set_active_user_id,
)
from database import (
    save_message,
    get_conversation_history,
)

logger = logging.getLogger(__name__)

# Konfigurasi Model Terkini (gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-4-hydrogen)
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# Senarai model lapuk yang perlu dinaik taraf secara automatik
LEGACY_MODELS_MAP = {
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-pro": "gemini-4-hydrogen",
    "gemini-2.0-flash": "gemini-3.5-flash-lite",
    "gemini-1.5-flash": "gemini-3.5-flash-lite",
    "gemini-1.5-pro": "gemini-4-hydrogen",
}

# Arahan Sistem (System Instruction / Persona)
SYSTEM_INSTRUCTION = """
Nama anda ialah Ejen AI Telegram, seorang pembantu peribadi maya yang bijak, mesra, dan berwibawa.

Gaya Komunikasi & Persona:
1. Bahasa: Gunakan Bahasa Melayu yang santai, mesra, semula jadi, dan sopan.
2. Format Paparan Mudah Alih (Mobile-Friendly):
   - Pastikan jawapan ringkas, padat, dan mudah dibaca pada skrin telefon bimbit.
   - Elakkan perenggan dinding teks (wall of text).
   - Gunakan 'bullet points' atau senarai bernombor untuk maklumat berstruktur.
   - Gunakan emoji yang sederhana dan relevan (contoh: ✨, 📅, 📝, ⏰, ✅, 💡) untuk menjadikan perbualan lebih hidup.
3. Keupayaan Alatan (Agentic Tools):
   - Anda mempunyai akses kepada alatan fungsi Python sebenar:
     • get_current_datetime: Gunakan apabila pengguna bertanya waktu, tarikh, hari, atau jadual di Malaysia.
     • save_note: Gunakan apabila pengguna minta menyimpan nota, pesanan, peringatan, atau senarai tugasan (to-do).
     • get_notes: Gunakan apabila pengguna ingin melihat atau menyemak nota/tugasan yang pernah disimpan.
     • delete_note: Gunakan apabila pengguna meminta untuk membuang atau memadam nota mengikut ID.
     • create_image: Gunakan secara autonomi apabila pengguna meminta melukis, mencipta gambar, poster, atau ilustrasi.
     • create_voice: Gunakan secara autonomi apabila pengguna meminta suara, audio, voice note, atau meminta anda bercakap.
     • create_video: Gunakan secara autonomi apabila pengguna meminta menghasilkan video, animasi, atau klip pendek.
4. Ingatan Perbualan:
   - Anda dibekalkan dengan sejarah perbualan terkini bersama pengguna. Gunakan konteks tersebut untuk memberikan jawapan yang berkesinambungan dan peribadi.
""".strip()


class AIAgent:
    """Kelas pengurus Ejen AI Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        raw_model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.model_name = self._resolve_model_name(raw_model)
        self.client: Optional[genai.Client] = None
        self._init_client()

    def _resolve_model_name(self, raw_model: str) -> str:
        """Menyemak dan menaik taraf nama model lapuk secara automatik."""
        clean_name = raw_model.strip().replace("models/", "")
        if clean_name in LEGACY_MODELS_MAP:
            upgraded = LEGACY_MODELS_MAP[clean_name]
            logger.info(
                f"Model '{clean_name}' telah ditamatkan oleh Google. "
                f"Menaik taraf secara automatik kepada '{upgraded}'."
            )
            return upgraded
        return clean_name

    def _init_client(self) -> None:
        """Inisialisasi klien google-genai."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning(
                "GEMINI_API_KEY belum dikonfigurasi! Ejen AI tidak dapat menjana respons sebenar."
            )
            self.client = None
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Klien google-genai berjaya diinisialisasi dengan model: {self.model_name}")
        except Exception as e:
            logger.error(f"Gagal memulakan klien google-genai: {e}")
            self.client = None

    def is_configured(self) -> bool:
        """Menyemak sama ada kunci API telah dikonfigurasi dengan betul."""
        if not self.client or not self.api_key or self.api_key == "your_gemini_api_key_here":
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key and env_key != "your_gemini_api_key_here":
                self.api_key = env_key
                self.model_name = self._resolve_model_name(os.getenv("GEMINI_MODEL", DEFAULT_MODEL))
                self._init_client()
        return bool(self.client and self.api_key and self.api_key != "your_gemini_api_key_here")

    def _build_history_contents(self, history_records: List[Dict[str, str]]) -> List[types.Content]:
        """
        Membina senarai objek Content bagi mematuhi giliran berselang seli
        user -> model untuk sesi chat history Gemini API.
        """
        contents: List[types.Content] = []
        expected_role = "user"

        for item in history_records:
            role = item.get("role", "user")
            text = item.get("content", "").strip()
            if not text:
                continue

            if role == expected_role:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text)],
                    )
                )
                expected_role = "model" if expected_role == "user" else "user"
            elif contents and contents[-1].role == role:
                # Cantumkan teks jika terdapat peranan berturut-turut
                contents[-1].parts.append(types.Part.from_text(text="\n" + text))

        # Sesi chat history mestilah berakhir dengan respon 'model'
        # supaya send_message seterusnya menghantar 'user'
        if contents and contents[-1].role == "user":
            contents.pop()

        return contents

    def _sync_generate_chat(self, history_contents: List[types.Content], current_prompt: str, user_id: int) -> str:
        """
        Menjalankan perbualan menggunakan Chat API rasmi google-genai dengan AFC (Automatic Function Calling).
        Menyokong sandaran model automatik sekiranya berlaku 503 high demand atau 404.
        """
        set_active_user_id(user_id)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[
                get_current_datetime,
                save_note,
                get_notes,
                delete_note,
                create_image,
                create_voice,
                create_video,
            ],
            temperature=0.7,
        )

        # Senarai percubaan model sekiranya berlaku gangguan sementara
        model_candidates = [
            self.model_name,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-4-hydrogen",
        ]
        # Buang pendua sambil mengekalkan susunan
        unique_models = []
        for m in model_candidates:
            if m not in unique_models:
                unique_models.append(m)

        last_error = None
        for candidate_model in unique_models:
            try:
                chat = self.client.chats.create(
                    model=candidate_model,
                    history=history_contents if history_contents else None,
                    config=config,
                )
                response = chat.send_message(current_prompt)

                if response and response.text:
                    if candidate_model != self.model_name:
                        logger.info(f"Berjaya menggunakan model sandaran: {candidate_model}")
                    return response.text.strip()
                elif response and hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    text_parts = []
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if getattr(part, "text", None):
                                text_parts.append(part.text)
                    if text_parts:
                        return "\n".join(text_parts).strip()

            except Exception as e:
                err_msg = str(e)
                last_error = e
                # Jika masalah adalah kapasiti tinggi (503) atau model lama (404), cuba model seterusnya
                if "503" in err_msg or "404" in err_msg or "UNAVAILABLE" in err_msg or "NOT_FOUND" in err_msg:
                    logger.warning(
                        f"Model {candidate_model} mengalami ralat ({err_msg[:80]}). "
                        "Mencuba model seterusnya..."
                    )
                    continue
                else:
                    # Ralat lain seperti API_KEY tidak sah, jangan teruskan loop
                    raise e

        if last_error:
            raise last_error

        return "Maaf, saya tidak dapat memproses mesej tersebut buat masa ini. Sila cuba sebentar lagi."

    async def process_message(self, user_id: int, user_message: str) -> str:
        """
        Memproses mesej pengguna:
        1. Menyimpan mesej pengguna ke dalam SQLite.
        2. Mengambil sejarah perbualan terdahulu.
        3. Berbual bersama Gemini AI Agent dengan pemanggilan alatan automatik.
        4. Menyimpan respons model ke dalam SQLite.
        5. Mengembalikan jawapan akhir.
        """
        if not self.is_configured():
            return (
                "⚠️ **Kunci API Gemini Belum Ditetapkan!**\n\n"
                "Sila masukkan `GEMINI_API_KEY` yang sah ke dalam fail `.env` "
                "untuk membolehkan saya berfikir dan menjawab pertanyaan anda.\n\n"
                "Dapatkan kunci API percuma anda di: https://aistudio.google.com/"
            )

        # 1. Simpan mesej pengguna ke DB memori
        await save_message(user_id=user_id, role="user", content=user_message)

        # 2. Ambil sejarah perbualan (10 pusingan terkini sebelum mesej ini)
        history = await get_conversation_history(user_id=user_id, limit=10)
        past_records = history[:-1] if history else []
        history_contents = self._build_history_contents(past_records)

        # 3. Panggil Gemini dalam threadpool tak segerak (asyncio.to_thread)
        try:
            response_text = await asyncio.to_thread(
                self._sync_generate_chat,
                history_contents,
                user_message,
                user_id,
            )
        except Exception as err:
            error_str = str(err)
            logger.error(f"Ralat dalam pemprosesan mesej user {user_id}: {error_str}")

            if "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                return (
                    "⚠️ **Kuota API Telah Melebihi Had.**\n\n"
                    "Akaun Gemini API anda telah mencapai had kuota percuma. "
                    "Sila tunggu sebentar atau semak status di Google AI Studio."
                )
            elif "API_KEY_INVALID" in error_str or "invalid api key" in error_str.lower():
                return (
                    "❌ **Kunci API Gemini Tidak Sah!**\n\n"
                    "Sila pastikan `GEMINI_API_KEY` dalam fail `.env` adalah tepat."
                )
            else:
                return (
                    "Maaf, saya menghadapi sedikit masalah teknikal semasa berhubung dengan otak AI. 🤖\n\n"
                    f"Perincian ringkas: _{error_str[:120]}..._\n"
                    "Sila cuba hantar semula mesej anda sebentar lagi."
                )

        # 4. Simpan respons model ke dalam ingatan SQLite
        await save_message(user_id=user_id, role="model", content=response_text)

        return response_text
