"""
media_generator.py - Modul Penjanaan Multimedia AI (Gambar, Video & Suara).

Menyediakan fungsi:
1. generate_image: Menjana gambar berdasarkan teks menggunakan Gemini Image / Flux fallback.
2. generate_voice: Menukar teks kepada fail audio pertuturan (TTS) menggunakan Gemini TTS / gTTS fallback.
3. generate_video: Menjana video pendek MP4 berdasarkan prompt teks.
"""

import os
import random
import uuid
import base64
import logging
import urllib.parse
import urllib.request
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

# Direktori penyimpanan media tempatan
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_media")
os.makedirs(MEDIA_DIR, exist_ok=True)


def get_genai_client(api_version: str = "v1") -> Optional[genai.Client]:
    """Mendapatkan klien Google GenAI."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    try:
        return genai.Client(api_key=api_key, http_options={"api_version": api_version})
    except Exception as e:
        logger.error(f"Gagal memulakan GenAI client ({api_version}): {e}")
        return None


# =====================================================================
# 1. Penjanaan Gambar (Image Generation)
# =====================================================================

def generate_image(prompt: str) -> str:
    """
    Menjana gambar berdasarkan prompt pengguna.
    Mencuba Gemini Image API dahulu; sekiranya kuota Free Tier terhad,
    ia beralih kepada enjin Flux secara lancar tanpa ralat.
    """
    output_filename = f"img_{uuid.uuid4().hex[:10]}.jpg"
    output_path = os.path.join(MEDIA_DIR, output_filename)

    logger.info(f"Memulakan penjanaan gambar untuk: '{prompt[:60]}...'")

    # 1. Cuba Gemini Image API jika ada kunci
    client = get_genai_client(api_version="v1beta")
    if client:
        try:
            res = client.models.generate_content(
                model="gemini-3.1-flash-lite-image",
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
            if res and hasattr(res, "parts") and res.parts:
                for part in res.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        with open(output_path, "wb") as f:
                            f.write(part.inline_data.data)
                        logger.info(f"Gambar berjaya dihasilkan dengan Gemini: {output_path}")
                        return output_path
        except Exception as e:
            logger.info(f"Gemini Image dialihkan ke enjin sandaran Flux: {str(e)[:80]}")

    # 2. Sandaran Pantas & Berkualiti Tinggi (Flux Engine)
    try:
        seed = random.randint(1000, 999999)
        clean_prompt = prompt.strip().replace("\n", " ")
        encoded = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=768&height=768"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=20) as response:
            image_data = response.read()

        with open(output_path, "wb") as f:
            f.write(image_data)
        logger.info(f"Gambar berjaya dijana dan disimpan: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Ralat semasa menjana gambar melalui sandaran: {e}")
        raise RuntimeError(f"Gagal menjana gambar: {e}")


# =====================================================================
# 2. Penjanaan Suara (Text-to-Speech / Voice)
# =====================================================================

def generate_voice(text: str) -> str:
    """
    Menukar teks kepada pertuturan audio (suara) dalam Bahasa Melayu.
    Mencuba model Gemini 3.8 Flash TTS dahulu, dan menggunakan gTTS sebagai sandaran.
    """
    output_filename = f"voice_{uuid.uuid4().hex[:10]}.wav"
    output_path = os.path.join(MEDIA_DIR, output_filename)

    clean_text = text.strip()
    if not clean_text:
        raise ValueError("Teks untuk suara tidak boleh kosong.")

    if len(clean_text) > 600:
        clean_text = clean_text[:600] + "..."

    logger.info(f"Memulakan penjanaan suara bagi: '{clean_text[:50]}...'")

    # 1. Cuba Gemini 3.8 Flash Lite TTS
    client = get_genai_client(api_version="v1beta")
    if client:
        try:
            interaction = client.interactions.create(
                model="gemini-3.8-flash-lite-tts",
                input=[{
                    "type": "user_input",
                    "content": [{
                        "type": "text",
                        "text": clean_text,
                        "annotations": [{
                            "type": "speech_metadata",
                            "style": "cheerful and friendly",
                        }],
                    }],
                }],
                response_format={"type": "audio"},
                generation_config={
                    "speech_config": [
                        {"voice": "Kore"}
                    ]
                },
            )
            if interaction.output_audio and interaction.output_audio.data:
                audio_bytes = base64.b64decode(interaction.output_audio.data)
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"Suara Gemini berjaya disimpan ke: {output_path}")
                return output_path
        except Exception as e:
            logger.info(f"Gemini TTS dialihkan ke gTTS: {str(e)[:80]}")

    # 2. Sandaran Pantas (gTTS Bahasa Melayu)
    try:
        from gtts import gTTS
        mp3_path = output_path.replace(".wav", ".mp3")
        tts = gTTS(text=clean_text, lang="ms", slow=False)
        tts.save(mp3_path)
        logger.info(f"Suara gTTS (Bahasa Melayu) berjaya disimpan ke: {mp3_path}")
        return mp3_path
    except Exception as e:
        logger.error(f"Ralat gTTS: {e}")
        raise RuntimeError(f"Gagal menjana suara audio: {e}")


# =====================================================================
# 3. Penjanaan Video (Video Generation)
# =====================================================================

def generate_video(prompt: str) -> str:
    """
    Menjana video MP4 berdasarkan prompt.
    Menghasilkan video gerakan sinematik berdefinisi tinggi (Cinematic Motion Video)
    daripada visual adegan AI menggunakan imageio-ffmpeg.
    Pantas, lancar, dan sedia dimainkan di Telegram.
    """
    output_filename = f"video_{uuid.uuid4().hex[:10]}.mp4"
    output_path = os.path.join(MEDIA_DIR, output_filename)

    logger.info(f"Memulakan penjanaan video sinematik untuk: '{prompt[:60]}...'")

    # Sekiranya Gemini Omni diaktifkan secara eksplisit dalam .env
    if os.getenv("USE_GEMINI_OMNI_VIDEO", "").lower() in ("true", "1", "yes"):
        client = get_genai_client(api_version="v1beta")
        if client:
            try:
                logger.info("Mencuba model gemini-omni-1.2-flash...")
                interaction = client.interactions.create(
                    model="gemini-omni-1.2-flash",
                    input=[{"type": "text", "text": prompt}],
                    response_format={"type": "video", "delivery": "uri"},
                )
                if interaction.output_video and interaction.output_video.uri:
                    video_bytes = client.files.download(file=interaction.output_video.uri)
                    with open(output_path, "wb") as f:
                        f.write(video_bytes)
                    logger.info(f"Video Gemini berjaya disimpan ke: {output_path}")
                    return output_path
            except Exception as e:
                logger.warning(f"Gemini Omni gagal ({e}). Menggunakan render sinematik pantas...")

    # Penjanaan Video Gerakan Sinematik HD (Smooth Motion Video MP4)
    try:
        import imageio
        from PIL import Image
        import numpy as np

        # Dapatkan gambar asas adegan
        scene_img_path = generate_image(prompt)
        base_img = Image.open(scene_img_path).convert("RGB")

        # Saiz video 512x512 (sangat pantas dirender dan ringan untuk data mobile)
        target_w, target_h = 512, 512
        base_img = base_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        fps = 12
        duration_sec = 2.5
        total_frames = int(fps * duration_sec)
        frames = []

        # Hasilkan efek gerakan sinematik (Smooth Ken Burns Zoom & Pan)
        for i in range(total_frames):
            progress = i / float(total_frames)
            zoom = 1.0 + (0.12 * progress)
            w_crop = int(target_w / zoom)
            h_crop = int(target_h / zoom)

            left = int((target_w - w_crop) * 0.5 + (progress * 10))
            top = int((target_h - h_crop) * 0.5 + (progress * 6))
            right = left + w_crop
            bottom = top + h_crop

            cropped = base_img.crop((left, top, right, bottom))
            resized = cropped.resize((target_w, target_h), Image.Resampling.BILINEAR)
            frames.append(np.array(resized))

        # Tulis ke MP4 menggunakan libx264
        writer = imageio.get_writer(
            output_path,
            fps=fps,
            codec="libx264",
            format="FFMPEG",
            quality=6,
            pixelformat="yuv420p",
        )
        for frame in frames:
            writer.append_data(frame)
        writer.close()

        logger.info(f"Video sinematik berjaya dicipta: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Ralat mencipta video: {e}")
        raise RuntimeError(f"Gagal menjana video: {e}")
