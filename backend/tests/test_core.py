from datetime import datetime

from app.clock import IST, add_working_days, is_bank_holiday, resolve_when
from app.models import Case
from app.playbook import build_plan, liability
from app.redact import redact

NOW = datetime(2026, 10, 24, 15, 0, tzinfo=IST)   # a Saturday (4th of the month)


def test_resolve_minutes_ago():
    assert resolve_when(minutes_ago=20, now=NOW) == datetime(2026, 10, 24, 14, 40, tzinfo=IST)


def test_resolve_clock_time_never_in_future():
    # "saade das baje" said at 3pm -> 10:30 today; "8 baje" said at 3pm with no day -> 8am today
    assert resolve_when(clock_time="10:30", now=NOW).day == 24
    assert resolve_when(clock_time="20:00", now=NOW).day == 23   # 8pm must be last night


def test_bank_holidays():
    assert is_bank_holiday(datetime(2026, 10, 24).date())       # 4th Saturday
    assert not is_bank_holiday(datetime(2026, 10, 3).date())    # 1st Saturday
    assert is_bank_holiday(datetime(2026, 10, 25).date())       # Sunday


def test_working_days_skip_weekend():
    # Fri 23 Oct -> skip Sat 24 (4th Sat), Sun 25 -> Mon 26, Tue 27, Wed 28
    fri = datetime(2026, 10, 23, 18, 0, tzinfo=IST)
    assert add_working_days(fri, 3).date() == datetime(2026, 10, 28).date()


def test_redact_keeps_utr_masks_aadhaar_and_otp():
    out = redact("UTR 412345678901 hai, mera aadhaar 1234 5678 9012 aur OTP 482913 bata diya")
    assert "412345678901" in out
    assert "••••••••9012" in out and "1234 5678" not in out
    assert "482913" not in out


def test_redact_card_luhn():
    assert "4111111111111111" not in redact("card 4111111111111111 se gaya")


def test_plan_digital_arrest_starts_with_disconnect():
    c = Case()
    c.incident.scam_type = "digital_arrest"
    c.incident.fraud_time = NOW
    plan = build_plan(c, now=NOW)
    assert plan[0].id == "disconnect"
    assert any(s.id == "call_1930" and s.deadline for s in plan)


def test_done_steps_sink():
    c = Case()
    c.done_steps = ["call_1930"]
    plan = build_plan(c, now=NOW)
    assert plan[-1].id == "call_1930" and plan[-1].done


def test_liability_bands():
    c = Case()
    c.incident.fraud_time = NOW
    assert liability(c, now=NOW)["band"] == "zero"
    c.incident.otp_shared = True
    assert liability(c, now=NOW)["band"] == "negligence"


def test_backfill_extracts_rigid_fields():
    from app.extract import backfill
    from app.models import Incident
    inc = Incident()
    filled = backfill(inc, "SBI account hai, PhonePe se bheja, UTR 412398765432, number 98765 43210 tha")
    assert inc.victim_bank == "SBI" and inc.payment_app == "PhonePe" and inc.channel == "upi"
    assert inc.txn_ref == "412398765432" and inc.scammer_handle == "9876543210"
    assert set(filled) == {"victim_bank", "payment_app", "txn_ref", "scammer_handle"}


def test_reply_language():
    from app.extract import reply_language
    assert reply_language("Someone called me and I gave the OTP") == "English"
    assert reply_language("maine 5000 bhej diye, wo abhi bhi line pe hai").startswith("Hinglish")
    assert reply_language("मैंने पैसे भेज दिए").startswith("Hinglish")


def test_confirmed_steps():
    from app.extract import confirmed_steps
    assert confirmed_steps("ठीक है, कॉल काट दिया।") == ["disconnect"]
    assert confirmed_steps("1930 पे कॉल कर दिया, उन्होंने कंप्लेंट ले ली") == ["call_1930"]
    assert confirmed_steps("Bank को भी call कर दिया, UPI freeze हो गया") == ["bank_freeze"]
    assert confirmed_steps("I haven't called anyone yet") == []
