"""
Write dataset bundle (dataset_latest.json, meta, timestamped copy).

Schema v1.0; required top-level keys and structure as specified.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from team_reports.engine.models import SyncSummary, asdict_serializable


SCHEMA_VERSION = "1.0"


def _engine_version() -> str:
    """Package version + git sha if available."""
    try:
        from team_reports import __version__
        ver = __version__
    except Exception:
        ver = "0.0.0"
    try:
        import subprocess
        repo = Path(__file__).resolve().parent.parent.parent
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return f"{ver}+{sha}"
    except Exception:
        return ver


def dataset_dir(out_dir: str, team_id: str) -> Path:
    """Directory for dataset files. Sanitizes team_id to prevent path traversal."""
    safe_id = "".join(c for c in team_id if c.isalnum() or c in "-_") or "default"
    return Path(out_dir) / "datasets" / "v1" / safe_id


def write_dataset(
    out_dir: str,
    team_id: str,
    requested_start: str,
    requested_end: str,
    effective_start: str,
    effective_end: str,
    buffer_days: int,
    safety_margin_hours: int,
    time_rules: Dict[str, Any],
    status: str,
    partial: bool,
    sync_summary: SyncSummary,
    weekly_snapshots: List[Dict[str, Any]],
    artifacts: Dict[str, List[Dict[str, Any]]],
    contributors: List[Dict[str, Any]],
    computed_contributor_summaries: List[Dict[str, Any]],
    generated_at: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Write dataset_latest.json, dataset_latest.meta.json, and timestamped copy.
    Creates directories as needed.

    Returns:
        (dataset_path, meta_path, timestamped_dataset_path)
    """
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    ts_short = generated_at[:19].replace("T", "_").replace(":", "-").replace("Z", "")

    base = dataset_dir(out_dir, team_id)
    base.mkdir(parents=True, exist_ok=True)

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "team_id": team_id,
        "requested_range": {"start": requested_start, "end": requested_end},
        "effective_sync_window": {
            "start": effective_start,
            "end": effective_end,
            "buffer_days": buffer_days,
            "safety_margin_hours": safety_margin_hours,
        },
        "time_rules": time_rules,
        "status": status,
        "partial": partial,
        "sync_summary": asdict_serializable(sync_summary),
        "weekly_snapshots": weekly_snapshots,
        "artifacts": {
            "jira_issues": artifacts.get("jira_issues", []),
            "github_pull_requests": artifacts.get("github_pull_requests", []),
            "github_commits": artifacts.get("github_commits", []),
            "github_reviews": artifacts.get("github_reviews", []),
            "gitlab_merge_requests": artifacts.get("gitlab_merge_requests", []),
            "gitlab_commits": artifacts.get("gitlab_commits", []),
            "gitlab_issues": artifacts.get("gitlab_issues", []),
        },
        "contributors": contributors,
        "computed_contributor_summaries": computed_contributor_summaries,
    }

    dataset_path = base / "dataset_latest.json"
    with open(dataset_path, "w") as f:
        json.dump(dataset, f, indent=2)

    timestamped_path = base / f"dataset_{requested_start}_{requested_end}_{ts_short}.json"
    with open(timestamped_path, "w") as f:
        json.dump(dataset, f, indent=2)

    meta = {
        "generated_at": generated_at,
        "engine_version": _engine_version(),
        "sources": [asdict_serializable(s) for s in sync_summary.sources],
        "warnings": [asdict_serializable(w) for w in sync_summary.warnings],
        "dataset_path": str(dataset_path),
        "previous_dataset_path": None,
    }
    meta_path = base / "dataset_latest.meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return str(dataset_path), str(meta_path), str(timestamped_path)
