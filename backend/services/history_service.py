"""Analysis History Service — persists intelligence reports to a local JSON file.

Endpoints exposed in main.py:
  GET  /api/history           → last N results (default 20)
  GET  /api/history/{name}    → latest result for a specific company
  POST /api/history/clear     → wipe all history
"""

import json
import os
from typing import Optional
from backend.models.schemas import AccountIntelligence

_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")
_MAX_RECORDS = 200  # cap file size


def _load() -> list[dict]:
    if not os.path.isfile(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(records: list[dict]) -> None:
    os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def save_result(intelligence: AccountIntelligence) -> None:
    """Append a completed analysis to the history file."""
    records = _load()
    records.insert(0, intelligence.model_dump())  # newest first
    records = records[:_MAX_RECORDS]
    _save(records)


def get_history(limit: int = 20) -> list[dict]:
    """Return the most recent N analysis results."""
    return _load()[:limit]


def get_by_company(company_name: str) -> Optional[dict]:
    """Return the most recent analysis for a specific company name (case-insensitive)."""
    name_lower = company_name.lower()
    for record in _load():
        found = (
            record.get("company_profile", {}).get("company_name", "").lower() == name_lower
            or record.get("company_identification", {}).get("company_name", "").lower() == name_lower
        )
        if found:
            return record
    return None


def clear_history() -> int:
    """Delete all history records. Returns number of records cleared."""
    records = _load()
    count = len(records)
    _save([])
    return count
