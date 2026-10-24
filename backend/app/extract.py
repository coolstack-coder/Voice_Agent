"""Deterministic safety net under the LLM's extraction.

LLMs occasionally drop a field they clearly heard. For the handful of facts that
have a rigid shape (bank names, payment apps, UTRs, UPI ids, phone numbers) a
regex pass over the user's own words fills gaps - it never overrides the LLM.
"""
from __future__ import annotations

import re

from .models import Incident

BANKS = {
    r"\bsbi\b|state bank": "SBI", r"\bhdfc\b": "HDFC Bank", r"\bicici\b": "ICICI Bank",
    r"\baxis\b": "Axis Bank", r"\bkotak\b": "Kotak Mahindra Bank", r"\bpnb\b|punjab national": "Punjab National Bank",
    r"bank of baroda|\bbob\b": "Bank of Baroda", r"\bcanara\b": "Canara Bank", r"union bank": "Union Bank of India",
    r"\bindusind\b": "IndusInd Bank", r"yes bank": "Yes Bank", r"\bidfc\b": "IDFC First Bank",
    r"एसबीआई|स्टेट बैंक": "SBI", r"एचडीएफसी": "HDFC Bank", r"आईसीआईसीआई": "ICICI Bank",
}
APPS = {
    r"phone ?pe|फोन ?पे": "PhonePe", r"google ?pay|\bgpay\b|गूगल ?पे": "Google Pay",
    r"paytm|पेटीएम": "Paytm", r"\bbhim\b|भीम": "BHIM", r"amazon ?pay": "Amazon Pay",
}
UTR = re.compile(r"(?:utr|ref(?:erence)?|transaction id|यूटीआर)\D{0,15}(\d{12})", re.I)
UPI_ID = re.compile(r"\b[\w.\-]{2,}@[a-z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")


def backfill(inc: Incident, text: str) -> list[str]:
    filled = []
    low = text.lower()
    if not inc.victim_bank:
        for pat, name in BANKS.items():
            if re.search(pat, low):
                inc.victim_bank, _ = name, filled.append("victim_bank")
                break
    if not inc.payment_app:
        for pat, name in APPS.items():
            if re.search(pat, low):
                inc.payment_app, _ = name, filled.append("payment_app")
                if not inc.channel:
                    inc.channel = "upi"
                break
    if not inc.txn_ref and (m := UTR.search(text)):
        inc.txn_ref, _ = m.group(1), filled.append("txn_ref")
    if not inc.scammer_handle:
        if m := UPI_ID.search(text):
            inc.scammer_handle, _ = m.group(0), filled.append("scammer_handle")
        elif m := PHONE.search(text):
            inc.scammer_handle, _ = m.group(1).replace(" ", "").replace("-", ""), filled.append("scammer_handle")
    return filled


HINDI_MARKERS = set(
    "hai hain tha thi ka ki ke ko se pe par mein maine mera meri mere mujhe nahi nahin aur bhi kya kar kiya "
    "diya diye gaya gaye bola boli wo woh abhi bhaiya ji paise rupaye haan accha kaat kat raha rahi".split()
)


def reply_language(text: str) -> str:
    """Pick the reply language deterministically; LLMs drift towards the prompt's examples."""
    if any("ऀ" <= ch <= "ॿ" for ch in text):
        return "Hinglish (Hindi in Roman script)"
    words = re.findall(r"[a-z]+", text.lower())
    hits = sum(w in HINDI_MARKERS for w in words)
    return "Hinglish (Hindi in Roman script)" if hits >= 2 else "English"
