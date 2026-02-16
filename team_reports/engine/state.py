"""
Engine-owned incremental sync state.

State is per team + source_type + instance_id.
Stored in out_dir/datasets/v1/<team_id>/engine_state.json.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def state_path(out_dir: str, team_id: str) -> Path:
    """Path to engine_state.json. Sanitizes team_id to prevent path traversal."""
    safe_id = "".join(c for c in team_id if c.isalnum() or c in "-_") or "default"
    return Path(out_dir) / "datasets" / "v1" / safe_id / "engine_state.json"


def load_engine_state(out_dir: str, team_id: str) -> Dict[str, Any]:
    """Load engine state; return empty dict if missing."""
    path = state_path(out_dir, team_id)
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_engine_state(
    out_dir: str,
    team_id: str,
    state: Dict[str, Any],
) -> None:
    """Write engine_state.json. Creates parent dirs."""
    path = state_path(out_dir, team_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def get_source_state(
    state: Dict[str, Any],
    source_type: str,
    instance_id: str,
) -> Dict[str, Any]:
    """Get or create state for one source. Schema: last_successful_sync_at, last_attempt_at, cursor (dict), last_error, last_mode."""
    key = f"{source_type}:{instance_id}"
    if key not in state:
        state[key] = {
            "last_successful_sync_at": None,
            "last_attempt_at": None,
            "cursor": {},
            "last_error": None,
            "last_mode": None,
        }
    # Normalize cursor to dict for backward compat
    s = state[key]
    if s.get("cursor") is not None and not isinstance(s.get("cursor"), dict):
        s["cursor"] = {}
    return s


def update_source_state(
    state: Dict[str, Any],
    source_type: str,
    instance_id: str,
    *,
    cursor: Optional[Dict[str, Any]] = None,
    last_successful_sync_at: Optional[str] = None,
    last_attempt_at: Optional[str] = None,
    last_error: Optional[str] = None,
    last_mode: Optional[str] = None,
) -> None:
    """Update state for one source (in-place). Cursor must be a dict (or None to leave unchanged)."""
    s = get_source_state(state, source_type, instance_id)
    if cursor is not None:
        s["cursor"] = dict(cursor) if cursor else {}
    if last_successful_sync_at is not None:
        s["last_successful_sync_at"] = last_successful_sync_at
    if last_attempt_at is not None:
        s["last_attempt_at"] = last_attempt_at
    if last_error is not None:
        s["last_error"] = last_error
    if last_mode is not None:
        s["last_mode"] = last_mode
