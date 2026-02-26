#!/usr/bin/env python3
"""
Flow metrics history: load/save JSON records for trend and comparison.

History file is a JSON array of records (newest last). Used for "vs last period",
rolling averages, and traffic-light in flow metrics reports.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_cadence(period_days: int, cadence: Optional[str] = None) -> str:
    """Infer cadence from period_days if not provided."""
    if cadence:
        return cadence
    if 28 <= period_days <= 31:
        return "monthly"
    if 12 <= period_days <= 16:
        return "bi-weekly"
    return "custom"


def load_flow_metrics_history(history_path: str) -> List[Dict[str, Any]]:
    """
    Load history from JSON file. Returns list of records (newest last).
    If file missing or invalid, returns [].
    """
    path = Path(history_path)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def append_flow_metrics_record(
    history_path: str,
    record: Dict[str, Any],
    max_per_cadence: int = 24,
) -> None:
    """
    Append one record to history file. Trim so at most max_per_cadence
    entries per cadence (keep newest). Creates directory if needed.
    """
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_flow_metrics_history(history_path)
    cadence = record.get("cadence", "custom")
    history.append(record)
    # Keep only last max_per_cadence per cadence
    by_cadence: Dict[str, List[Dict[str, Any]]] = {}
    for r in history:
        c = r.get("cadence", "custom")
        by_cadence.setdefault(c, []).append(r)
    trimmed = []
    for c, recs in by_cadence.items():
        trimmed.extend(recs[-max_per_cadence:])
    # Sort by period_end so order is chronological (newest last)
    trimmed.sort(key=lambda r: (r.get("period_start", ""), r.get("period_end", "")))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)


def get_previous_period(
    history: List[Dict[str, Any]],
    period_days: int,
    cadence: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent record with the same cadence (excluding the
    very last if it matches current period). Uses cadence string; if
    cadence is not in records, infer from period_days (28-31 -> monthly,
    12-16 -> bi-weekly) and match by that.
    """
    norm = _normalize_cadence(period_days, cadence)
    same_cadence = [r for r in history if (r.get("cadence") or _normalize_cadence(r.get("period_days", 0))) == norm]
    if not same_cadence:
        return None
    # Most recent record in history is the previous period (current run not yet appended)
    return same_cadence[-1]


def get_rolling(
    history: List[Dict[str, Any]],
    cadence: str,
    periods: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Last N records with same cadence; return dict with mean throughput,
    mean cycle_median_days, mean lead_median_days. Returns None if
    fewer than 1 record (or optionally require periods).
    """
    norm = cadence if cadence in ("monthly", "bi-weekly", "custom") else _normalize_cadence(0, cadence)
    same_cadence = [r for r in history if (r.get("cadence") or _normalize_cadence(r.get("period_days", 0))) == norm]
    if not same_cadence:
        return None
    last_n = same_cadence[-periods:]
    n = len(last_n)
    return {
        "throughput": sum(r.get("throughput", 0) for r in last_n) / n,
        "cycle_median_days": sum(r.get("cycle_median_days", 0) for r in last_n) / n,
        "lead_median_days": sum(r.get("lead_median_days", 0) for r in last_n) / n,
        "periods": n,
    }
