"""The GoldenHour agent: one user utterance in, one short spoken reply out.

The LLM's job is narrow on purpose: understand a panicked, rambling, code-mixed
story, call tools to record facts, and phrase the next instruction kindly.
Facts, deadlines and documents all come from deterministic code.

Token budget matters (Groq free tier = 8k tokens/min), so every tool returns the
updated plan: a normal turn is exactly two LLM calls, record -> speak.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from . import config
from .clock import now_ist, resolve_when
from .extract import backfill, confirmed_steps, reply_language
from .models import Case, Turn
from .playbook import build_plan, golden_hour_deadline, liability, next_actions

log = logging.getLogger(__name__)

FALLBACK_MODEL = "openai/gpt-oss-20b"
UPI_APPS = {"PhonePe", "Google Pay", "Paytm", "BHIM", "Amazon Pay"}

SYSTEM = """You are Kavach, the calm voice of GoldenHour: first aid for people in India who were JUST \
defrauded online. They are scared and may still be on the scammer's call.

Speak: mirror the user's language. English in -> English out. Hindi/Hinglish in -> Hinglish out, written in Roman script. Max 2 short sentences, under 30 \
words, spoken aloud: no lists, markdown or emojis. Never blame. Give ONE next action and ask at most ONE \
question for the most useful missing fact.

Work: whenever they reveal facts call update_incident (times: "20 minute pehle" -> fraud_minutes_ago=20; \
"kal raat 9 baje" -> fraud_clock_time="21:00", fraud_day_offset=-1). Set still_in_contact only if they say so. If they are still \
on the call, say hang up first; once they say they hung up, set still_in_contact=false and mark "disconnect" done. \
When they confirm doing any step, call mark_step_done. Speak the top step from the tool \
result. Use ONLY steps, numbers and deadlines the tools return; never invent helplines, laws or deadlines. \
Never say internal names like txn_ref or step ids; say "UTR". You are not police or a lawyer.

Example: user "maine abhi 5000 bhej diye, wo abhi bhi line pe hai" -> you "Ghabraiye mat, aap akele nahi hain. \
Pehle call kaat dijiye, phir batayiye paise kis app se gaye?"
"""

# Steps a person can confirm by voice. The written bank dispute is ticked in the UI:
# the model kept confusing "called the bank" with "sent the letter".
STEP_IDS = ["disconnect", "call_1930", "bank_freeze", "uninstall_remote", "ncrp", "evidence"]

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "update_incident",
        "description": "Record facts you actually heard. Returns the updated plan.",
        "parameters": {"type": "object", "properties": {
            "victim_name": {"type": "string"},
            "amount": {"type": "number", "description": "total rupees lost"},
            "channel": {"type": "string", "enum": ["upi", "card", "netbanking", "wallet", "crypto", "cash_deposit", "other"]},
            "scam_type": {"type": "string", "enum": ["digital_arrest", "kyc_update", "fake_customer_care", "investment_task",
                                                     "otp_share", "remote_app", "sextortion", "upi_collect", "other"],
                          "description": "digital_arrest=fake police/CBI/customs threat; kyc_update='account will be blocked'; "
                                         "fake_customer_care=victim called a fake helpline; investment_task=trading/task job; "
                                         "remote_app=made to install AnyDesk; upi_collect=approved a collect request"},
            "fraud_minutes_ago": {"type": "number"},
            "fraud_clock_time": {"type": "string", "description": "24h HH:MM"},
            "fraud_day_offset": {"type": "integer", "description": "0 today, -1 yesterday"},
            "txn_ref": {"type": ["string", "number"], "description": "UTR / transaction id"},
            "victim_bank": {"type": "string"},
            "payment_app": {"type": "string"},
            "scammer_handle": {"type": ["string", "number"], "description": "scammer phone, UPI id or profile"},
            "otp_shared": {"type": "boolean"},
            "still_in_contact": {"type": "boolean"},
            "summary": {"type": "string", "description": "neutral English account of what happened, for the police form"},
        }},
    }},
    {"type": "function", "function": {
        "name": "mark_step_done",
        "description": "Mark a plan step done when the user confirms it. Returns the updated plan.",
        "parameters": {"type": "object", "properties": {
            "step_id": {"type": "string", "enum": STEP_IDS},
        }, "required": ["step_id"]},
    }},
]


def _plan_view(case: Case) -> dict:
    gh = golden_hour_deadline(case)
    return {
        "next_steps": next_actions(case),
        "golden_hour_minutes_left": max(0, round((gh - now_ist()).total_seconds() / 60)) if gh else None,
        "rbi": liability(case)["text"],
        "missing_for_complaint": case.incident.missing_for_complaint(),
        "drafts_ready": not case.incident.missing_for_complaint(),
    }


# A step the model ticks must be mentioned in what the user just said; otherwise
# "1930 pe call kar diya" could tick "bank_freeze" too.
STEP_EVIDENCE = {
    "disconnect": r"call|cut|kaat|kat|hang|काट|कॉल",
    "call_1930": r"1930|helpline|हेल्पलाइन",
    "bank_freeze": r"bank|freeze|block|बैंक|फ्रीज|ब्लॉक",
    "uninstall_remote": r"anydesk|teamviewer|uninstall|app",
    "ncrp": r"cybercrime|portal|online complaint|website|पोर्टल",
    "evidence": r"screenshot|स्क्रीनशॉट|proof|saboot|सबूत",
}


def _run_tool(case: Case, name: str, args: dict, user_text: str = "") -> dict:
    inc = case.incident
    if name == "update_incident":
        if args.get("scam_type") == "other" and inc.scam_type:
            args.pop("scam_type")  # never downgrade a specific classification
        when = {k: args.pop(k) for k in ("fraud_minutes_ago", "fraud_clock_time", "fraud_day_offset") if k in args}
        if when.get("fraud_minutes_ago") is not None or when.get("fraud_clock_time"):
            t = resolve_when(
                minutes_ago=when.get("fraud_minutes_ago"),
                clock_time=when.get("fraud_clock_time"),
                day_offset=int(when.get("fraud_day_offset") or 0),
            )
            # the model often repeats "15 min ago" on later turns; that's the same moment,
            # not a new one, so only accept clear corrections (> 10 min apart)
            if inc.fraud_time is None or abs((t - inc.fraud_time).total_seconds()) > 600:
                inc.fraud_time = t
        for k, v in args.items():
            if hasattr(inc, k) and v not in (None, ""):
                if k == "txn_ref":
                    v = "".join(ch for ch in str(v) if ch.isalnum())
                if k == "scammer_handle" and not any(ch.isdigit() or ch == "@" for ch in str(v)):
                    continue  # "the CBI guy" is not an identifier the police can trace
                setattr(inc, k, v)
        if inc.channel in (None, "wallet", "other") and inc.payment_app in UPI_APPS:
            inc.channel = "upi"  # PhonePe/GPay/Paytm transfers are UPI, not wallet
        if inc.still_in_contact is False and "disconnect" not in case.done_steps:
            case.done_steps.append("disconnect")
        return _plan_view(case)
    if name == "mark_step_done":
        step = args.get("step_id")
        if step not in STEP_IDS or not re.search(STEP_EVIDENCE[step], user_text.lower()):
            return {"ignored": f"user did not say they completed {step}", **_plan_view(case)}
        if step not in case.done_steps:
            case.done_steps.append(step)
        return _plan_view(case)
    return {"error": f"unknown tool {name}"}


async def _chat(messages: list[dict]) -> dict:
    """Groq call with one polite retry on 429, then a smaller fallback model."""
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt, model in enumerate([config.LLM_MODEL, config.LLM_MODEL, FALLBACK_MODEL]):
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                json={"model": model, "messages": messages, "tools": TOOLS,
                      "temperature": 0.3, "reasoning_effort": config.REASONING_EFFORT},
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]
            log.warning("Groq %s on %s: %s", r.status_code, model, r.text[:160])
            if r.status_code == 400 and "tool call validation" in r.text:
                continue  # sampling glitch (e.g. a number where a string was due): just resample
            if r.status_code == 429 and attempt == 0:
                wait = float(r.headers.get("retry-after", "3"))
                if wait <= 8:
                    await asyncio.sleep(wait)
                    continue
            if r.status_code not in (400, 429, 500, 502, 503):
                r.raise_for_status()
        r.raise_for_status()
        raise RuntimeError("LLM unavailable")


async def respond(case: Case, user_text: str) -> tuple[str, list[str]]:
    used: list[str] = []
    reply = ""
    drafts_were_ready = not case.incident.missing_for_complaint()
    if filled := backfill(case.incident, user_text):
        log.info("regex backfill: %s", filled)
    for step in confirmed_steps(user_text):
        if step not in case.done_steps:
            case.done_steps.append(step)
            log.info("user confirmed step: %s", step)
        if step == "disconnect":
            case.incident.still_in_contact = False
    # computed after the deterministic passes so the model starts from the true state
    clock = (f"Now: {now_ist().strftime('%a %d %b %Y %I:%M %p')} IST. "
             f"Reply language for this turn: {reply_language(user_text)}. "
             f"Current state: {json.dumps(_plan_view(case), default=str)}")
    messages = [{"role": "system", "content": SYSTEM + "\n" + clock}, *case.history[-12:],
                {"role": "user", "content": user_text}]
    for _ in range(4):
        msg = await _chat(messages)
        calls = msg.get("tool_calls") or []
        if not calls:
            reply = (msg.get("content") or "").strip()
            if reply:
                break
            # gpt-oss occasionally spends the turn reasoning and says nothing: nudge once
            messages.append({"role": "system", "content": "Now reply to the user, following the rules."})
            continue
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
                log.info("tool %s(%s)", name, args)
                result = _run_tool(case, name, args, user_text)
            except Exception as e:  # a malformed tool call shouldn't kill the turn
                log.exception("tool %s failed", name)
                result = {"error": str(e)}
            used.append(name)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, default=str)})
    if drafts_were_ready is False and not case.incident.missing_for_complaint() and "draft" not in reply.lower():
        # the moment the last field lands, always say so: it's the payoff of the whole call
        reply += (" Your complaint drafts are ready on screen." if reply_language(user_text) == "English"
                  else " Aapke complaint drafts screen par ready hain.")
    if not reply:
        top = next_actions(case, 1)
        reply = top[0]["title"] if top else "I'm here. Tell me what happened."
    # long-term history keeps only spoken text; tool chatter is re-derivable from the case
    case.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
    case.transcript += [Turn(role="user", text=user_text), Turn(role="agent", text=reply, tools=used)]
    return reply, used


def snapshot(case: Case) -> dict:
    """What the UI renders: incident card, plan, countdown, liability."""
    gh = golden_hour_deadline(case)
    return {
        "id": case.id,
        "incident": case.incident.model_dump(mode="json"),
        "plan": [s.to_dict() for s in build_plan(case)],
        "golden_hour_deadline": gh.isoformat() if gh else None,
        "liability": liability(case),
        "missing": case.incident.missing_for_complaint(),
        "transcript": [t.model_dump(mode="json") for t in case.transcript],
        "server_now": now_ist().isoformat(),
    }
