#!/usr/bin/env python3
"""
Story-point sizing utilities for flow metrics and sizing analysis.

Maps story points (from Jira) to size labels for segmentation and possibly-mis-sized
detection. Team-agnostic: works with any mapping (e.g. t-shirt labels, custom names)
or with raw story point values when no mapping is configured.

Config:
  - team_sizing: optional map of size_key -> story_points (e.g. {"xsmall": 1, "small": 3}
    or {"S": 3, "M": 9}). Keys and values define the scale; order is by value ascending
    unless size_display_order is provided.
  - flow_metrics.size_labels: optional map size_key -> display label (e.g. xsmall -> "XS").
    If absent, the size_key is used as the label.
  - flow_metrics.size_display_order: optional list of size_key in desired table order.
  When team_sizing is omitted or empty, sizes are raw story point values (e.g. "1", "2", "3").
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Default display labels for common config keys (backward compatibility)
# Teams can override via flow_metrics.size_labels
DEFAULT_SIZE_LABELS: Dict[str, str] = {
    "xsmall": "XS",
    "small": "S",
    "medium": "M",
    "large": "L",
    "xlarge": "XL",
}


def story_points_to_size(
    story_points: Optional[float],
    team_sizing: Optional[Dict[str, int]] = None,
    size_labels: Optional[Dict[str, str]] = None,
) -> str:
    """
    Map story points to a size label for segmentation.

    - If team_sizing is None or empty: return str(int(points)) for valid points,
      "Unestimated" for None/0/invalid. (Raw story-point mode; works for any team.)
    - If team_sizing is set: find the key whose value equals points; return
      size_labels.get(key, key) so teams can use custom labels or keys as labels.
    """
    if story_points is None:
        return "Unestimated"
    try:
        pts = int(story_points) if isinstance(story_points, (int, float)) else None
    except (TypeError, ValueError):
        return "Unestimated"
    if pts is None or pts == 0:
        return "Unestimated"

    if not team_sizing:
        return str(pts)

    labels = size_labels if size_labels is not None else {}
    for config_key, point_value in team_sizing.items():
        if point_value == pts:
            return labels.get(config_key, config_key)
    return "Unestimated"


def story_points_to_tshirt(
    story_points: Optional[float],
    team_sizing: Dict[str, int],
) -> str:
    """
    Map story points to a size label using team_sizing and default XS/S/M/L/XL labels.
    Kept for backward compatibility; prefer story_points_to_size with size_labels.
    """
    return story_points_to_size(story_points, team_sizing, DEFAULT_SIZE_LABELS)


def get_size_order(
    team_sizing: Optional[Dict[str, int]] = None,
    size_labels: Optional[Dict[str, str]] = None,
    size_display_order: Optional[List[str]] = None,
) -> List[str]:
    """
    Return size labels in display order for the segment table.

    - If team_sizing is None or empty: return [] (caller will order by observed keys).
    - If team_sizing is set: order by size_display_order if provided, else by points ascending;
      each element is the display label (size_labels.get(key, key)).
    """
    if not team_sizing:
        return []
    labels = size_labels if size_labels is not None else {}
    if size_display_order is not None:
        order_keys = [k for k in size_display_order if k in team_sizing]
    else:
        order_keys = sorted(team_sizing.keys(), key=lambda k: team_sizing[k])
    return [labels.get(k, k) for k in order_keys]


def get_tshirt_size_order(team_sizing: Dict[str, int]) -> List[str]:
    """Return default t-shirt labels in display order. Backward compat."""
    return get_size_order(team_sizing, DEFAULT_SIZE_LABELS, list(DEFAULT_SIZE_LABELS))


def get_ordered_sizes_for_table(
    team_sizing: Optional[Dict[str, int]] = None,
    size_labels: Optional[Dict[str, str]] = None,
    size_display_order: Optional[List[str]] = None,
    observed_keys: Optional[List[str]] = None,
) -> List[str]:
    """
    Order for segment table: Unestimated first, then size labels.
    If team_sizing is set, use get_size_order. If raw-points mode (no team_sizing),
    observed_keys should be the segment keys (e.g. ["1", "2", "3", "5", "8"]); they
    will be sorted numerically where possible.
    """
    unest = "Unestimated"
    if team_sizing:
        order = get_size_order(team_sizing, size_labels, size_display_order)
        return [unest] + order
    if observed_keys is not None:
        rest = [k for k in observed_keys if k != unest]
        def sort_key(s: str):
            try:
                return (0, int(s))
            except ValueError:
                return (1, s)
        rest.sort(key=sort_key)
        return [unest] + rest
    return [unest]


def load_sizing_baseline(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a sizing baseline JSON (e.g. from 9-month analysis).
    Expected shape: { "sizes": { "<label>": { "median_cycle_days": 1, ... }, ... }, "period": {...} }.
    Returns None if file missing or invalid.
    """
    import json
    p = Path(file_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_sizing_baseline(file_path: str, data: Dict[str, Any]) -> bool:
    """Save sizing baseline JSON. Returns True on success."""
    import json
    p = Path(file_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError:
        return False


def median(vals: List[float]) -> float:
    """Return median of non-empty list; 0 for empty."""
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    return (s[(n - 1) // 2] + s[n // 2]) / 2.0


def flag_possibly_missized(
    issue_records: List[Dict[str, Any]],
    size_median_cycle: Dict[str, float],
    min_issues_for_baseline: int = 2,
    cycle_multiple_threshold: float = 2.0,
    size_key: str = "size_label",
) -> List[Dict[str, Any]]:
    """
    From issue_records (each with key, summary, cycle_days, and size_key e.g. size_label),
    return list of issues that may have been mis-sized: cycle time exceeds
    cycle_multiple_threshold times the median cycle for that size.
    """
    result: List[Dict[str, Any]] = []
    for r in issue_records:
        size = r.get(size_key) or r.get("t_shirt_size")
        if not size or size == "Unestimated":
            continue
        cycle = r.get("cycle_days")
        if cycle is None:
            continue
        baseline_median = size_median_cycle.get(size)
        if baseline_median is None or baseline_median <= 0:
            continue
        if cycle > cycle_multiple_threshold * baseline_median:
            result.append({
                **r,
                "baseline_median_cycle_days": baseline_median,
                "multiple": round(cycle / baseline_median, 1),
            })
    return result
