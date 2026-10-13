import json
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

def append_audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        events = json.loads(AUDIT_PATH.read_text(encoding="utf-8")) if AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        events = []
    if not isinstance(events, list):
        events = [events]
    events.append(event)
    AUDIT_PATH.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
