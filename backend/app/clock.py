"""Time helpers. All reasoning happens in IST, and 'now' is overridable for tests/demos."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
_frozen: datetime | None = None


def now_ist() -> datetime:
    if _frozen is not None:
        return _frozen
    if os.getenv("FAKE_NOW"):
        return datetime.fromisoformat(os.environ["FAKE_NOW"]).astimezone(IST)
    return datetime.now(IST)


def freeze(at: datetime | None) -> None:
    global _frozen
    _frozen = at


def resolve_when(
    minutes_ago: float | None = None,
    clock_time: str | None = None,
    day_offset: int = 0,
    now: datetime | None = None,
) -> datetime:
    """Turn what the victim *said* into an absolute timestamp.

    The LLM only extracts the shape ("20 minute pehle" -> minutes_ago=20,
    "kal shaam 7 baje" -> clock_time="19:00", day_offset=-1); the arithmetic
    is done here so it can never hallucinate a date.
    """
    now = now or now_ist()
    if minutes_ago is not None:
        return now - timedelta(minutes=float(minutes_ago))
    if clock_time:
        hh, mm = (clock_time.strip().split(":") + ["0"])[:2]
        t = now.replace(hour=int(hh) % 24, minute=int(mm), second=0, microsecond=0)
        t += timedelta(days=day_offset)
        # A fraud can't be in the future: "11 baje" said at 9am means last night.
        if t > now:
            t -= timedelta(days=1)
        return t
    return now + timedelta(days=day_offset)


def is_bank_holiday(d: date) -> bool:
    """Sundays plus the 2nd and 4th Saturday of every month (RBI calendar rule).

    National/state holidays are not modelled; the UI says so.
    """
    if d.weekday() == 6:
        return True
    if d.weekday() == 5:
        nth = (d.day - 1) // 7 + 1
        return nth in (2, 4)
    return False


def add_working_days(start: datetime, days: int) -> datetime:
    """RBI counts working days excluding the day the customer got the alert."""
    d = start
    added = 0
    while added < days:
        d += timedelta(days=1)
        if not is_bank_holiday(d.date()):
            added += 1
    return d.replace(hour=23, minute=59, second=0, microsecond=0)
