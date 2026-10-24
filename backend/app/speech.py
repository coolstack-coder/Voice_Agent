"""Speech in (Groq Whisper) and speech out (ElevenLabs) with a hard credit guard."""
from __future__ import annotations

import hashlib
import json
import logging

import httpx

from . import config

log = logging.getLogger(__name__)

# Biases Whisper towards the vocabulary of Indian payment fraud, so "UTR" doesn't
# become "utter" and "PhonePe" doesn't become "phone pay".
STT_PROMPT = (
    "UPI, UTR, OTP, 1930, PhonePe, Google Pay, GPay, Paytm, SBI, HDFC, ICICI, Axis, "
    "CBI, customs, digital arrest, KYC, AnyDesk, rupaye, paise, hazaar, lakh."
)


async def transcribe(audio: bytes, filename: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            data={"model": config.STT_MODEL, "prompt": STT_PROMPT, "temperature": "0"},
            files={"file": (filename, audio)},
        )
    r.raise_for_status()
    return r.json()["text"].strip()


class TTSBudget:
    """Persists characters spent so a restart can't silently burn credits."""

    path = config.DATA_DIR / "tts_usage.json"

    def used(self) -> int:
        try:
            return json.loads(self.path.read_text())["chars"]
        except (FileNotFoundError, KeyError, ValueError):
            return 0

    def remaining(self) -> int:
        return max(0, config.TTS_CHAR_BUDGET - self.used())

    def spend(self, n: int) -> None:
        self.path.write_text(json.dumps({"chars": self.used() + n}))


budget = TTSBudget()
CACHE = config.DATA_DIR / "tts_cache"
CACHE.mkdir(exist_ok=True)


async def synthesize(text: str) -> bytes | None:
    """Returns mp3 bytes, or None to tell the browser to speak it itself."""
    if config.TTS_PROVIDER != "elevenlabs" or not config.ELEVENLABS_API_KEY:
        return None
    key = hashlib.sha1(f"{config.TTS_VOICE_ID}|{config.TTS_MODEL}|{text}".encode()).hexdigest()
    cached = CACHE / f"{key}.mp3"
    if cached.exists():
        return cached.read_bytes()
    if len(text) > budget.remaining():
        log.warning("TTS budget exhausted, falling back to browser voice")
        return None
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{config.TTS_VOICE_ID}",
            params={"output_format": "mp3_44100_64"},
            headers={"xi-api-key": config.ELEVENLABS_API_KEY},
            json={
                "text": text,
                "model_id": config.TTS_MODEL,
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
            },
        )
    if r.status_code != 200:
        log.warning("ElevenLabs %s: %s", r.status_code, r.text[:200])
        return None
    budget.spend(len(text))
    cached.write_bytes(r.content)
    return r.content
