"""Tiny JSON-file case store. One file per case keeps the demo dependency-free."""
from __future__ import annotations

from .config import DATA_DIR
from .models import Case

CASES = DATA_DIR / "cases"
CASES.mkdir(exist_ok=True)


def save(case: Case) -> None:
    (CASES / f"{case.id}.json").write_text(case.model_dump_json(indent=2))


def load(case_id: str) -> Case | None:
    p = CASES / f"{case_id}.json"
    if not p.exists() or not case_id.isalnum():
        return None
    return Case.model_validate_json(p.read_text())
