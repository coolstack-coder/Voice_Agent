"""Deterministic recovery playbook.

Given what we know about the incident and the current time, produce an ordered list
of steps with real deadlines. The LLM reads from this; it never invents steps,
helplines or legal timelines.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .clock import add_working_days, now_ist
from .models import Case

GOLDEN_HOUR = timedelta(minutes=60)


@dataclass
class Step:
    id: str
    title: str
    why: str
    priority: int                       # 0 = do this second, 3 = when calm
    deadline: Optional[datetime] = None
    action: Optional[str] = None        # tel: / https: link for the UI
    done: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["deadline"] = self.deadline.isoformat() if self.deadline else None
        return d


def golden_hour_deadline(case: Case) -> Optional[datetime]:
    t = case.incident.fraud_time
    return t + GOLDEN_HOUR if t else None


def liability(case: Case, now: datetime | None = None) -> dict:
    """RBI 2017 customer-liability framing for unauthorised electronic transactions."""
    inc = case.incident
    now = now or now_ist()
    if inc.fraud_time is None:
        return {"band": "unknown", "text": "Tell me when it happened to compute your RBI window."}
    zero_by = add_working_days(inc.fraud_time, 3)
    capped_by = add_working_days(inc.fraud_time, 7)
    if inc.otp_shared:
        return {
            "band": "negligence",
            "zero_by": zero_by.isoformat(),
            "text": "OTP/PIN was shared, so the bank can hold you liable until you report. "
                    "Every minute counts: report now to stop further loss.",
        }
    if now <= zero_by:
        band, text = "zero", "Report to your bank in writing before this deadline for zero liability."
    elif now <= capped_by:
        band, text = "capped", "Past 3 working days: liability is capped. Report today."
    else:
        band, text = "bank_policy", "Past 7 working days: the bank's board policy decides. Report anyway."
    return {"band": band, "zero_by": zero_by.isoformat(), "capped_by": capped_by.isoformat(), "text": text}


def build_plan(case: Case, now: datetime | None = None) -> list[Step]:
    inc = case.incident
    now = now or now_ist()
    gh = golden_hour_deadline(case)
    steps: list[Step] = []

    if inc.still_in_contact or inc.scam_type in ("digital_arrest", "remote_app"):
        steps.append(Step(
            "disconnect", "Disconnect the call. Share nothing more.",
            "Scammers keep victims on the line to stop them reporting. Real police never "
            "arrest anyone on a video call." if inc.scam_type == "digital_arrest" else
            "Every extra minute on the line is a chance for a second transfer.",
            priority=0, tags=["urgent"],
        ))

    steps.append(Step(
        "call_1930", "Call 1930, the national cyber-fraud helpline",
        "1930 can ask banks to put a hold on the money before it is moved again. "
        "This works best inside the golden hour.",
        priority=0, deadline=gh, action="tel:1930", tags=["golden-hour"],
    ))

    bank = inc.victim_bank or "your bank"
    if inc.channel == "card":
        title = f"Block the card with {bank}"
    elif inc.channel in ("upi", "wallet"):
        app = f" and {inc.payment_app}" if inc.payment_app else ""
        title = f"Call {bank}{app}: freeze UPI and raise a fraud dispute"
    else:
        title = f"Call {bank}'s fraud line and freeze the account"
    steps.append(Step(
        "bank_freeze", title,
        "Stops any further debits and starts the bank's own fraud record with a timestamp.",
        priority=0, deadline=gh, tags=["golden-hour"],
    ))

    if inc.scam_type == "remote_app":
        steps.append(Step(
            "uninstall_remote", "Uninstall AnyDesk / TeamViewer / screen-share apps, then change UPI PIN",
            "The scammer may still be able to see your screen.",
            priority=1, tags=["urgent"],
        ))

    steps.append(Step(
        "ncrp", "File a complaint on cybercrime.gov.in",
        "Gives you an acknowledgement number that banks and police ask for. "
        "GoldenHour pre-fills the form for you.",
        priority=1, deadline=(inc.fraud_time + timedelta(hours=24)) if inc.fraud_time else None,
        action="https://cybercrime.gov.in", tags=["document"],
    ))

    if inc.fraud_time:
        steps.append(Step(
            "bank_written", f"Send the written dispute to {bank}",
            "RBI: report third-party fraud within 3 working days for zero liability "
            "(Sundays and 2nd/4th Saturdays don't count).",
            priority=1, deadline=add_working_days(inc.fraud_time, 3), tags=["document", "rbi"],
        ))

    steps.append(Step(
        "evidence", "Screenshot everything. Delete nothing.",
        "Chats, call log, the scammer's number and UPI id, bank SMS. Police need them.",
        priority=2,
    ))

    if inc.scam_type == "sextortion":
        steps.append(Step(
            "sextortion", "Do not pay again. Report the profile.",
            "Paying never ends sextortion. Platforms remove content when reported.",
            priority=1,
        ))

    steps.append(Step(
        "recovery_scam", "Ignore anyone offering to 'recover' your money for a fee",
        "Recovery-agent scams target people who were just defrauded.",
        priority=3,
    ))

    for s in steps:
        s.done = s.id in case.done_steps
    steps.sort(key=lambda s: (s.done, s.priority))
    return steps


def next_actions(case: Case, limit: int = 3) -> list[dict]:
    return [
        {"id": s.id, "title": s.title, "deadline": s.deadline.isoformat() if s.deadline else None}
        for s in build_plan(case) if not s.done
    ][:limit]
