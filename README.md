# 🤖 Telegram AI Agent & Web (Gemini Brain + Memory + Multimedia)

Sebuah sistem **Telegram AI Agent & Web App** sedia produksi yang dibina menggunakan **Python 3.11+**, SDK rasmi **`google-genai`** (Gemini API), **`python-telegram-bot`** (asinkronus v20+), serta **SQLite** (`aiosqlite`) untuk ingatan perbualan dan pengurusan nota peribadi.

Dilengkapi kemahiran **Multimedia Penuh**: **Jana Gambar AI**, **Penjanaan Suara (Voice Note)**, dan **Jana Video Sinematik MP4**! 🎨🎙️🎬

---

## 🌟 Ciri-Ciri Utama (Core Features)

1. **Otak AI Gemini Terkini**:
   - Menggunakan SDK rasmi generasi baharu `google-genai`.
   - Persona ramah, ringkas, santai, dan mudah dibaca pada skrin telefon pintar (senarai poin & emoji sederhana).
   - Menyokong model generasi terkini (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-4-hydrogen`).

2. **Kemahiran Multimedia Penuh (Gambar, Video & Suara)**:
   - 🎨 **Jana Gambar AI**: Menjana imej berkualiti tinggi berdasarkan keterangan teks pengguna (`/image` atau perbualan biasa).
   - 🎙️ **Pertuturan Suara (Voice Note)**: Menukar teks kepada pesanan suara audio sebenar (`.wav`/`.mp3`) dalam Bahasa Melayu menggunakan Gemini 3.8 Flash TTS / gTTS (`/voice` atau perbualan biasa).
   - 🎬 **Jana Video Sinematik**: Menghasilkan klip video sinematik animasi berformat `.mp4` yang boleh dimainkan terus di Telegram (`/video` atau perbualan biasa).

3. **Laman Web Interaktif (Web Interface)**:
   - Antaramuka moden di `http://localhost:5000` (`app.py`).
   - Menaip mesej dan AI membalas dalam bentuk teks ringkas serta memainkan suara pertuturan secara automatik.

4. **Ingatan Perbualan Tempatan (Multi-Turn SQLite Memory)**:
   - Setiap mesej dan jawapan disimpan ke dalam pangkalan data SQLite tempatan (`bot_memory.db`).
   - Memori diasingkan mengikut `user_id` Telegram.
   - Perintah `/clear` disediakan untuk memadam sejarah perbualan pengguna tanpa menjejaskan nota peribadi.

---

## 📁 Struktur Projek

```
ripAgent/
├── generated_media/     # Folder simpanan fail gambar, audio, dan video yang dijana
├── templates/
│   └── index.html       # Antaramuka web moden untuk sembang teks & suara
├── static/
│   ├── css/style.css    # Gaya UI moden (Dark theme, glassmorphism, responsive)
│   └── js/app.js        # Logik sembang web & kawalan pemain audio suara
├── app.py               # Pelayan web Flask (http://localhost:5000)
├── media_generator.py   # Modul penjanaan Gambar, Video sinematik, dan Suara TTS
├── agent.py             # Logik Ejen AI (google-genai, prompt, memory retrieval)
├── tools.py             # Definisi fungsi Function Calling (media, datetime & nota)
├── database.py          # Lapisan pangkalan data SQLite async (aiosqlite)
├── main.py              # Pengendali bot Telegram (/start, /clear, /image, /voice, /video)
├── Procfile             # Arahan permulaan untuk Render / Railway Cloud
├── requirements.txt     # Senarai pustaka dependensi Python
├── .env.example         # Templat fail konfigurasi kunci API
├── .env                 # Fail konfigurasi peribadi anda (jangan kongsikan!)
├── .gitignore           # Menghalang fail rahsia dan media dimuat naik ke Git
└── README.md            # Dokumentasi panduan dalam Bahasa Melayu
```

---

## 🚀 Panduan Pemasangan & Persediaan

### Langkah 1: Kunci API

1. **Telegram Bot Token**: Dapatkan daripada [@BotFather](https://t.me/BotFather) di Telegram.
2. **Gemini API Key**: Dapatkan percuma daripada [Google AI Studio](https://aistudio.google.com/).

---

### Langkah 2: Fail Konfigurasi `.env`

Pastikan fail `.env` mengandungi tetapan berikut:

```env
# Token Bot Telegram daripada @BotFather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Kunci API Gemini daripada Google AI Studio
GEMINI_API_KEY=your_gemini_api_key_here

# Model Gemini pilihan (Default: gemini-3.5-flash-lite)
GEMINI_MODEL=gemini-3.5-flash-lite

# Nama fail pangkalan data SQLite
DATABASE_PATH=bot_memory.db
```

---

### Langkah 3: Jalankan Sistem

#### A. Menjalankan Laman Web (Teks & Suara):
```powershell
.\.venv\Scripts\python app.py
```
Buka pelayar web anda di:
👉 **http://localhost:5000**

#### B. Menjalankan Bot Telegram:
```powershell
.\.venv\Scripts\python main.py
```

---

## 💬 Contoh Penggunaan & Arahan

### 1. Arahan Pantas (Commands)
| Arahan | Fungsi | Contoh |
|---|---|---|
| `/start` | Mesej alu-aluan dan pengenalan kebolehan | `/start` |
| `/image <prompt>` | Terus menjana dan menghantar gambar AI | `/image kucing comel pakai kaca mata hitam` |
| `/voice <teks>` | Terus menukar teks kepada pesanan suara | `/voice Selamat pagi semua, semoga harimu ceria!` |
| `/video <prompt>` | Terus menjana dan menghantar video MP4 | `/video matahari terbit di puncak gunung yang indah` |
| `/clear` | Padam memori perbualan dan mula topik baharu | `/clear` |
| `/help` | Panduan lengkap arahan dan alatan | `/help` |

### 2. Berbual Secara Autonomi (Natural Chat)
- _"Tolong lukiskan saya gambar seekor naga ais terbang di atas gunung"_ ➡️ Ejen menghantar gambar! 🖼️
- _"Boleh awak hantar pesanan suara selamat malam?"_ ➡️ Ejen menghantar Voice Note Telegram! 🎙️
- _"Buatkan video ombak pantai waktu senja"_ ➡️ Ejen menghantar video MP4! 🎬
- _"Pukul berapa sekarang di Malaysia?"_ ➡️ Ejen menjawab waktu semasa. ⏰
- _"Simpan nota: beli minyak masak petang nanti"_ ➡️ Ejen menyimpan nota ke SQLite. 📝
