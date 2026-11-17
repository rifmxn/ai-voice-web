"""
tools.py - Alatan Ejen (Agentic Tools) untuk Telegram AI Agent.

Fungsi-fungsi di bawah didaftarkan ke Gemini API sebagai Function Calling tools:
1. get_current_datetime: Mendapatkan tarikh dan masa semasa di Malaysia (Asia/Kuala_Lumpur).
2. save_note: Menyimpan nota atau peringatan peribadi pengguna ke SQLite.
3. get_notes: Mengambil senarai nota peribadi pengguna dari SQLite.
4. delete_note: Memadam nota peribadi pengguna berdasarkan ID.
5. create_image: Menjana gambar berdasarkan teks menggunakan AI.
6. create_voice: Menjana suara (Voice Note audio) daripada teks.
7. create_video: Menjana video pendek sinematik MP4 berdasarkan prompt.
"""

import contextvars
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
import logging

from database import sync_save_note, sync_get_notes, sync_delete_note

logger = logging.getLogger(__name__)

# Pembolehubah konteks untuk ID pengguna semasa (Thread-safe & Task-safe)
current_user_id_var: contextvars.ContextVar[int] = contextvars.ContextVar(
    "current_user_id", default=0
)


def set_active_user_id(user_id: int) -> None:
    """Menetapkan ID pengguna Telegram yang sedang berinteraksi."""
    current_user_id_var.set(user_id)


def get_active_user_id() -> int:
    """Mendapatkan ID pengguna Telegram semasa daripada konteks."""
    return current_user_id_var.get()


def get_current_datetime() -> str:
    """
    Mengembalikan tarikh, hari, dan masa semasa di Malaysia (zon masa Asia/Kuala_Lumpur, UTC+8).
    Gunakan fungsi ini apabila pengguna bertanya tentang waktu semasa, tarikh hari ini,
    atau memerlukan rujukan waktu untuk peringatan/jadual.

    Returns:
        str: Maklumat tarikh dan masa dalam Bahasa Melayu.
    """
    try:
        tz = ZoneInfo("Asia/Kuala_Lumpur")
        now = datetime.now(tz)

        # Pemetaan hari dan bulan ke Bahasa Melayu
        hari_list = {
            "Monday": "Isnin",
            "Tuesday": "Selasa",
            "Wednesday": "Rabu",
            "Thursday": "Khamis",
            "Friday": "Jumaat",
            "Saturday": "Sabtu",
            "Sunday": "Ahad",
        }
        bulan_list = {
            1: "Januari",
            2: "Februari",
            3: "Mac",
            4: "April",
            5: "Mei",
            6: "Jun",
            7: "Julai",
            8: "Ogos",
            9: "September",
            10: "Oktober",
            11: "November",
            12: "Disember",
        }

        nama_hari = hari_list.get(now.strftime("%A"), now.strftime("%A"))
        nama_bulan = bulan_list.get(now.month, now.strftime("%B"))
        format_masa = now.strftime("%I:%M:%S %p")
        format_24j = now.strftime("%H:%M:%S")

        result = (
            f"Hari: {nama_hari}\n"
            f"Tarikh: {now.day} {nama_bulan} {now.year}\n"
            f"Waktu: {format_masa} ({format_24j} format 24 jam)\n"
            f"Zon Masa: Asia/Kuala_Lumpur (MYT, UTC+8)"
        )
        logger.info("Alat get_current_datetime() berjaya dipanggil.")
        return result
    except Exception as e:
        logger.error(f"Ralat dalam get_current_datetime: {e}")
        return f"Ralat membaca masa semasa: {e}"


def save_note(note_text: str, user_id: Optional[int] = None) -> str:
    """
    Menyimpan nota, memo, tugasan (to-do) atau maklumat penting untuk pengguna ke dalam pangkalan data.
    Gunakan fungsi ini apabila pengguna meminta untuk mencatat, menyimpan nota, membuat senarai,
    atau mengingati sesuatu perkara.

    Args:
        note_text (str): Kandungan teks nota atau tugasan yang ingin disimpan.
        user_id (Optional[int]): ID pengguna Telegram (jika tiada, sistem akan menggunakan pengguna aktif).

    Returns:
        str: Mesej pengesahan penyimpanan nota.
    """
    try:
        effective_user_id = int(user_id) if user_id is not None and int(user_id) > 0 else get_active_user_id()
        if not effective_user_id:
            return "Ralat: ID pengguna tidak sah untuk menyimpan nota."

        if not note_text or not note_text.strip():
            return "Ralat: Kandungan nota tidak boleh kosong."

        saved = sync_save_note(user_id=effective_user_id, note_text=note_text.strip())
        logger.info(f"Nota ID {saved['id']} berjaya disimpan untuk user {effective_user_id}.")
        return (
            f"Nota berjaya disimpan!\n"
            f"- ID Nota: {saved['id']}\n"
            f"- Kandungan: {saved['content']}\n"
            f"- Masa Dicipta: {saved['created_at']}"
        )
    except Exception as e:
        logger.error(f"Ralat dalam save_note: {e}")
        return f"Gagal menyimpan nota: {str(e)}"


def get_notes(user_id: Optional[int] = None) -> str:
    """
    Mengambil semua nota, memo, atau tugasan yang pernah disimpan oleh pengguna daripada pangkalan data.
    Gunakan fungsi ini apabila pengguna bertanya tentang senarai nota mereka, apa yang telah disimpan,
    atau meminta senarai to-do mereka.

    Args:
        user_id (Optional[int]): ID pengguna Telegram (jika tiada, sistem akan menggunakan pengguna aktif).

    Returns:
        str: Senarai semua nota pengguna atau makluman bahawa tiada nota disimpan.
    """
    try:
        effective_user_id = int(user_id) if user_id is not None and int(user_id) > 0 else get_active_user_id()
        if not effective_user_id:
            return "Ralat: ID pengguna tidak sah untuk mengambil nota."

        notes = sync_get_notes(user_id=effective_user_id)
        if not notes:
            return "Tiada nota atau tugasan yang disimpan setakat ini."

        lines = [f"Senarai Nota Anda (Jumlah: {len(notes)}):"]
        for idx, item in enumerate(notes, start=1):
            created = item.get("created_at", "-")
            content = item.get("content", "")
            nid = item.get("id")
            lines.append(f"{idx}. [ID #{nid}] {content} (Dicipta: {created})")

        logger.info(f"Mengambil {len(notes)} nota untuk user {effective_user_id}.")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Ralat dalam get_notes: {e}")
        return f"Gagal mengambil nota: {str(e)}"


def delete_note(note_id: int, user_id: Optional[int] = None) -> str:
    """
    Memadam nota tertentu milik pengguna berdasarkan ID nota.
    Gunakan fungsi ini apabila pengguna meminta untuk memadam atau membuang sesuatu nota mengikut ID.

    Args:
        note_id (int): ID nota yang ingin dipadam.
        user_id (Optional[int]): ID pengguna Telegram.

    Returns:
        str: Pengesahan sama ada nota berjaya dipadam atau tidak dijumpai.
    """
    try:
        effective_user_id = int(user_id) if user_id is not None and int(user_id) > 0 else get_active_user_id()
        if not effective_user_id:
            return "Ralat: ID pengguna tidak sah untuk memadam nota."

        success = sync_delete_note(user_id=effective_user_id, note_id=int(note_id))
        if success:
            logger.info(f"Nota #{note_id} berjaya dipadam untuk user {effective_user_id}.")
            return f"Nota [ID #{note_id}] telah berjaya dipadam."
        else:
            return f"Nota [ID #{note_id}] tidak dijumpai dalam rekod anda."
    except Exception as e:
        logger.error(f"Ralat dalam delete_note: {e}")
        return f"Gagal memadam nota: {str(e)}"


def create_image(prompt: str) -> str:
    """
    Menjana gambar atau lukisan AI berdasarkan penerangan visual (prompt).
    Gunakan fungsi ini apabila pengguna meminta untuk menghasilkan gambar, lukisan,
    foto, ilustrasi, visual atau karya seni.

    Args:
        prompt (str): Keterangan visual terperinci mengenai gambar yang ingin dihasilkan.

    Returns:
        str: Status dan tag fail gambar [MEDIA:IMAGE:filepath].
    """
    try:
        from media_generator import generate_image
        path = generate_image(prompt)
        logger.info(f"Alat create_image berjaya menghasilkan: {path}")
        return f"[MEDIA:IMAGE:{path}] Gambar untuk '{prompt}' telah siap dihasilkan!"
    except Exception as e:
        logger.error(f"Ralat dalam create_image: {e}")
        return f"Maaf, gagal menghasilkan gambar: {e}"


def create_voice(text: str) -> str:
    """
    Menjana mesej audio suara pertuturan (Voice Note audio) daripada teks.
    Gunakan fungsi ini apabila pengguna meminta mesej dalam bentuk suara, audio,
    atau meminta anda bercakap/berbual menggunakan suara.

    Args:
        text (str): Teks yang ingin dituturkan dalam fail audio suara.

    Returns:
        str: Status dan tag fail audio suara [MEDIA:VOICE:filepath].
    """
    try:
        from media_generator import generate_voice
        path = generate_voice(text)
        logger.info(f"Alat create_voice berjaya menghasilkan: {path}")
        return f"[MEDIA:VOICE:{path}] Mesej suara telah siap dijana!"
    except Exception as e:
        logger.error(f"Ralat dalam create_voice: {e}")
        return f"Maaf, gagal menghasilkan suara: {e}"


def create_video(prompt: str) -> str:
    """
    Menjana video pendek animasi atau sinematik MP4 berdasarkan penerangan adegan (prompt).
    Gunakan fungsi ini apabila pengguna meminta untuk membuat video, animasi, klip,
    atau pergerakan visual.

    Args:
        prompt (str): Keterangan adegan video yang ingin dihasilkan.

    Returns:
        str: Status dan tag fail video [MEDIA:VIDEO:filepath].
    """
    try:
        from media_generator import generate_video
        path = generate_video(prompt)
        logger.info(f"Alat create_video berjaya menghasilkan: {path}")
        return f"[MEDIA:VIDEO:{path}] Video untuk '{prompt}' telah siap dihasilkan!"
    except Exception as e:
        logger.error(f"Ralat dalam create_video: {e}")
        return f"Maaf, gagal menghasilkan video: {e}"

