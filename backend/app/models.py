"""Case state for one fraud incident. Everything the agent learns lands here."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .clock import now_ist

Channel = Literal["upi", "card", "netbanking", "wallet", "crypto", "cash_deposit", "other"]
ScamType = Literal[
    "digital_arrest",      # fake CBI / customs / police video call
    "kyc_update",          # "your account will be blocked, update KYC"
    "fake_customer_care",  # searched a helpline on Google, got a fraudster
    "investment_task",     # like-videos / trading group / task scams
    "otp_share",           # tricked into reading out an OTP
    "remote_app",          # made to install AnyDesk / screen share
    "sextortion",
    "upi_collect",         # approved a "receive money" collect request
    "other",
]


class Incident(BaseModel):
    victim_name: Optional[str] = None
    amount: Optional[float] = None
    channel: Optional[Channel] = None
    scam_type: Optional[ScamType] = None
    fraud_time: Optional[datetime] = None
    txn_ref: Optional[str] = None          # UTR / RRN / transaction id
    victim_bank: Optional[str] = None
    payment_app: Optional[str] = None      # PhonePe / GPay / Paytm ...
    scammer_handle: Optional[str] = None   # UPI id, phone number, profile
    otp_shared: Optional[bool] = None
    still_in_contact: Optional[bool] = None
    summary: Optional[str] = None          # one-line neutral narrative

    def missing_for_complaint(self) -> list[str]:
        needed = {
            "amount": self.amount,
            "fraud_time": self.fraud_time,
            "txn_ref": self.txn_ref,
            "victim_bank": self.victim_bank,
            "scammer_handle": self.scammer_handle,
        }
        return [k for k, v in needed.items() if v in (None, "")]


class Turn(BaseModel):
    role: Literal["user", "agent"]
    text: str
    at: datetime = Field(default_factory=now_ist)
    tools: list[str] = Field(default_factory=list)


class Case(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: datetime = Field(default_factory=now_ist)
    incident: Incident = Field(default_factory=Incident)
    done_steps: list[str] = Field(default_factory=list)
    transcript: list[Turn] = Field(default_factory=list)
    # raw LLM message history (role/content/tool calls) kept server-side only
    history: list[dict] = Field(default_factory=list)
