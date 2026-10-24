"""GoldenHour API."""
from __future__ import annotations

import base64
import logging
import time

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import config, store
from .agent import respond, snapshot
from .documents import all_documents
from .models import Case
from .extract import reply_language
from .redact import redact
from .speech import budget, synthesize, transcribe

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("goldenhour")

app = FastAPI(title="GoldenHour")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _case(case_id: str) -> Case:
    case = store.load(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "tts": config.TTS_PROVIDER,
        "tts_credits_left": budget.remaining(),
        "llm": config.LLM_MODEL,
        "stt": config.STT_MODEL,
    }


@app.post("/api/cases")
def create_case():
    case = Case()
    store.save(case)
    return snapshot(case)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    return snapshot(_case(case_id))


@app.post("/api/cases/{case_id}/turn")
async def turn(case_id: str, audio: UploadFile | None = File(None), text: str | None = Form(None)):
    case = _case(case_id)
    timings = {}
    t0 = time.perf_counter()
    if audio is not None:
        raw = await audio.read()
        if len(raw) < 1500:
            raise HTTPException(400, "recording too short")
        heard = await transcribe(raw, audio.filename or "speech.webm")
        timings["stt_ms"] = round((time.perf_counter() - t0) * 1000)
    elif text:
        heard = text
    else:
        raise HTTPException(400, "send audio or text")

    heard = redact(heard)
    if not heard.strip():
        raise HTTPException(422, "couldn't hear anything")

    t1 = time.perf_counter()
    reply, tools = await respond(case, heard)
    timings["llm_ms"] = round((time.perf_counter() - t1) * 1000)
    store.save(case)

    t2 = time.perf_counter()
    mp3 = await synthesize(reply, "hi" if reply_language(reply) != "English" else "en")
    timings["tts_ms"] = round((time.perf_counter() - t2) * 1000)
    log.info("turn %s tools=%s timings=%s", case.id, tools, timings)

    return {
        "heard": heard,
        "reply": reply,
        "tools": tools,
        "audio": base64.b64encode(mp3).decode() if mp3 else None,
        "timings": timings,
        "case": snapshot(case),
        "tts_credits_left": budget.remaining(),
    }


@app.post("/api/cases/{case_id}/steps/{step_id}")
def toggle_step(case_id: str, step_id: str):
    case = _case(case_id)
    if step_id in case.done_steps:
        case.done_steps.remove(step_id)
    else:
        case.done_steps.append(step_id)
    store.save(case)
    return snapshot(case)


@app.get("/api/cases/{case_id}/documents")
def documents(case_id: str):
    return all_documents(_case(case_id))
