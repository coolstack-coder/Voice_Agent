"""Mask secrets the victim might blurt out, without destroying evidence.

The tricky bit: a UPI UTR is 12 digits - exactly like an Aadhaar number. A UTR is
evidence we *need* for the complaint; an Aadhaar is a secret we must not store.
So digit runs are only masked when the surrounding words say what they are.
"""
from __future__ import annotations

import re

_OTP_CTX = re.compile(r"(otp|o\.t\.p|ओटीपी|pin|cvv|password|पिन)", re.I)
_AADHAAR_CTX = re.compile(r"(aadhaar|aadhar|adhar|आधार)", re.I)
_DIGITS = re.compile(r"(?<!\d)(\d[\d ]{2,22}\d)(?!\d)")


def _luhn_ok(num: str) -> bool:
    total, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _mask(num: str, keep: int = 2) -> str:
    return "•" * (len(num) - keep) + num[-keep:]


def redact(text: str) -> str:
    def repl(m: re.Match) -> str:
        raw = m.group(1)
        digits = raw.replace(" ", "")
        window = text[max(0, m.start() - 30): m.start()]
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return _mask(digits, 4)                      # card number
        if len(digits) == 12 and _AADHAAR_CTX.search(window):
            return _mask(digits, 4)                      # aadhaar
        if 4 <= len(digits) <= 8 and _OTP_CTX.search(window):
            return "•" * len(digits)                     # otp / pin / cvv
        return raw
    return _DIGITS.sub(repl, text)
