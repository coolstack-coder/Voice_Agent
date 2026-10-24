import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3")
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "medium")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "elevenlabs")
TTS_CREDIT_BUDGET = int(os.getenv("TTS_CREDIT_BUDGET", "1000"))
# ElevenLabs premade multilingual voice; flash v2.5 costs half the credits of v2
TTS_VOICE_ID = os.getenv("TTS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
TTS_MODEL = os.getenv("TTS_MODEL", "eleven_flash_v2_5")

DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
