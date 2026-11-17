"""
database.py - Modul Pengurusan Pangkalan Data SQLite untuk Telegram AI Agent.

Menyokong:
1. Penyimpanan ingatan perbualan (conversation history) bagi setiap pengguna (multi-turn memory).
2. Penyimpanan dan pengambilan nota/tugasan peribadi (personal notes/tasks).
3. Sokongan asinkronus (aiosqlite) dan segerak (sqlite3) bagi kemudahan function calling alatan.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
import aiosqlite

logger = logging.getLogger(__name__)

# Tetapan fail pangkalan data default
DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "bot_memory.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Mendapatkan laluan fail pangkalan data yang sah."""
    return custom_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)


async def init_db(db_path: Optional[str] = None) -> None:
    """
    Memulakan struktur jadual pangkalan data jika belum wujud.
    Mengaktifkan WAL mode untuk prestasi baca/tulis yang optimum.
    """
    path = get_db_path(db_path)
    logger.info(f"Menginisialisasi pangkalan data SQLite di: {path}")

    async with aiosqlite.connect(path) as db:
        # Dayakan WAL mode untuk kecekapan konkurensi
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")

        # Jadual ingatan perbualan
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'model')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Indeks untuk carian pantas sejarah mengikut pengguna
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_user 
            ON conversations(user_id, created_at);
            """
        )

        # Jadual nota peribadi pengguna
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Indeks untuk carian pantas nota mengikut pengguna
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notes_user 
            ON notes(user_id, created_at);
            """
        )

        await db.commit()
    logger.info("Pangkalan data berjaya diinisialisasi.")


# =====================================================================
# Operasi Ingatan Perbualan (Conversation Memory)
# =====================================================================

async def save_message(user_id: int, role: str, content: str, db_path: Optional[str] = None) -> None:
    """Menyimpan mesej pengguna atau model ke dalam ingatan SQLite."""
    path = get_db_path(db_path)
    try:
        async with aiosqlite.connect(path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Ralat semasa menyimpan mesej ke DB (user {user_id}): {e}")


async def get_conversation_history(user_id: int, limit: int = 15, db_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Mengambil sejarah perbualan terkini bagi pengguna tertentu.
    Dikembalikan dalam susunan kronologi (paling lama ke paling baharu).
    """
    path = get_db_path(db_path)
    try:
        async with aiosqlite.connect(path) as db:
            db.row_factory = aiosqlite.Row
            # Dapatkan rekod terkini secara menurun dahulu, kemudian terbalikkan
            async with db.execute(
                """
                SELECT role, content, created_at 
                FROM conversations 
                WHERE user_id = ? 
                ORDER BY id DESC 
                LIMIT ?
                """,
                (user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                # Balikkan urutan supaya menjadi kronologi (lama -> baru)
                history = [
                    {"role": row["role"], "content": row["content"]}
                    for row in reversed(rows)
                ]
                return history
    except Exception as e:
        logger.error(f"Ralat semasa membaca sejarah perbualan (user {user_id}): {e}")
        return []


async def clear_conversation_history(user_id: int, db_path: Optional[str] = None) -> int:
    """
    Memadam semua rekod perbualan bagi pengguna tertentu (/clear).
    Mengembalikan bilangan rekod yang dipadam.
    """
    path = get_db_path(db_path)
    try:
        async with aiosqlite.connect(path) as db:
            cursor = await db.execute(
                "DELETE FROM conversations WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()
            deleted_count = cursor.rowcount
            logger.info(f"Memori dipadamkan untuk user {user_id} ({deleted_count} rekod).")
            return deleted_count
    except Exception as e:
        logger.error(f"Ralat semasa mengosongkan memori perbualan (user {user_id}): {e}")
        return 0


# =====================================================================
# Operasi Nota Peribadi (Personal Notes) - Async & Sync
# =====================================================================

def sync_save_note(user_id: int, note_text: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Fungsi segerak (synchronous) untuk menyimpan nota.
    Sesuai dipanggil secara terus oleh Function Calling SDK.
    """
    path = get_db_path(db_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (user_id, content) VALUES (?, ?)",
            (user_id, note_text.strip()),
        )
        note_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT id, content, created_at FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return {
            "id": row["id"],
            "content": row["content"],
            "created_at": row["created_at"],
            "status": "success",
        }


def sync_get_notes(user_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fungsi segerak untuk mendapatkan semua nota pengguna.
    """
    path = get_db_path(db_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, created_at FROM notes WHERE user_id = ? ORDER BY id ASC",
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            {"id": row["id"], "content": row["content"], "created_at": row["created_at"]}
            for row in rows
        ]


def sync_delete_note(user_id: int, note_id: int, db_path: Optional[str] = None) -> bool:
    """Fungsi segerak untuk memadam nota tertentu mengikut ID."""
    path = get_db_path(db_path)
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
