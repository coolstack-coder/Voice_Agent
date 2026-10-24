"""Ready-to-file drafts, generated from case fields by template (no LLM).

Anything we don't know yet is rendered as [MISSING: ...] so the victim sees
exactly what to find before filing, instead of a confident made-up value.
"""
from __future__ import annotations

from .clock import now_ist
from .models import Case

SCAM_LABELS = {
    "digital_arrest": "Impersonation of police/CBI officials ('digital arrest')",
    "kyc_update": "Fake KYC update / account-block threat",
    "fake_customer_care": "Fake customer care number",
    "investment_task": "Online investment / task fraud",
    "otp_share": "OTP obtained by deception",
    "remote_app": "Remote access (screen-sharing app) fraud",
    "sextortion": "Sextortion",
    "upi_collect": "UPI collect-request fraud",
    "other": "Online financial fraud",
}
CHANNEL_LABELS = {
    "upi": "UPI", "card": "Debit/Credit card", "netbanking": "Internet banking",
    "wallet": "Wallet", "crypto": "Crypto", "cash_deposit": "Cash deposit", "other": "Other",
}


def _v(value, label: str) -> str:
    return str(value) if value not in (None, "") else f"[MISSING: {label}]"


def _money(amount) -> str:
    return f"Rs. {amount:,.0f}" if amount else "[MISSING: amount]"


def _when(case: Case) -> str:
    t = case.incident.fraud_time
    return t.strftime("%d %b %Y, %I:%M %p IST") if t else "[MISSING: date & time]"


def ncrp_packet(case: Case) -> dict:
    """Field-by-field values for the cybercrime.gov.in financial fraud form."""
    inc = case.incident
    return {
        "title": "cybercrime.gov.in – financial fraud complaint",
        "fields": [
            {"label": "Category", "value": "Online Financial Fraud"},
            {"label": "Sub-category", "value": SCAM_LABELS.get(inc.scam_type or "other")},
            {"label": "Date & time of incident", "value": _when(case)},
            {"label": "Payment mode", "value": CHANNEL_LABELS.get(inc.channel, "[MISSING: payment mode]")},
            {"label": "Bank / wallet", "value": _v(inc.victim_bank, "your bank")},
            {"label": "Transaction ID / UTR", "value": _v(inc.txn_ref, "UTR from bank SMS")},
            {"label": "Amount lost", "value": _money(inc.amount)},
            {"label": "Suspect UPI / phone / profile", "value": _v(inc.scammer_handle, "scammer's number or UPI id")},
            {"label": "Incident description", "value": _v(inc.summary, "what happened")},
        ],
    }


def bank_letter(case: Case) -> dict:
    inc = case.incident
    name = inc.victim_name or "[Your name]"
    bank = inc.victim_bank or "[Bank name]"
    body = f"""To,
The Branch Manager / Fraud Cell,
{bank}

Date: {now_ist().strftime('%d %b %Y')}

Subject: Reporting an unauthorised electronic transaction and request to block, reverse and
place a lien on the amount

Dear Sir/Madam,

I am writing to report a fraudulent transaction from my account.

  • Date & time: {_when(case)}
  • Amount: {_money(inc.amount)}
  • Mode: {CHANNEL_LABELS.get(inc.channel, '[MISSING: payment mode]')}{f' via {inc.payment_app}' if inc.payment_app else ''}
  • Transaction ref / UTR: {_v(inc.txn_ref, 'UTR')}
  • Beneficiary: {_v(inc.scammer_handle, 'beneficiary UPI id / account')}

What happened: {_v(inc.summary, 'short description')}

I request you to (1) immediately block further debits, (2) raise a chargeback / dispute and
request the beneficiary bank to place a lien on the amount, and (3) treat this report under the
RBI circular on Limiting Liability of Customers in Unauthorised Electronic Banking Transactions
(RBI/2017-18/15, 6 July 2017). I have also reported this on the national helpline 1930 /
cybercrime.gov.in (acknowledgement no.: [add when received]).

Please acknowledge this complaint with a reference number and date-time stamp.

Yours faithfully,
{name}
"""
    return {"title": f"Dispute letter to {bank}", "body": body}


def all_documents(case: Case) -> dict:
    return {
        "ncrp": ncrp_packet(case),
        "bank_letter": bank_letter(case),
        "missing": case.incident.missing_for_complaint(),
    }
