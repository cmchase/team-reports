"""
Configurable week boundaries and business-day logic.

Single canonical utility for all reports and the engine.
Default week: WEDNESDAY (start) to TUESDAY (end).
Week boundaries and artifact bucketing use team_timezone (local dates).
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


def iso_to_ymd(iso_ts: str) -> Optional[str]:
    """
    Parse ISO8601 or date-only string to YYYY-MM-DD.

    Accepts:
    - ISO8601 with "Z" suffix or timezone offsets (e.g. +00:00)
    - Date-only "YYYY-MM-DD" (returned as-is)

    Returns:
        "YYYY-MM-DD" or None if iso_ts is falsy or parsing fails.
    """
    if not iso_ts or not isinstance(iso_ts, str):
        return None
    s = iso_ts.strip()
    if not s:
        return None
    # Date-only: validate by parsing
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and "T" not in s[:10]:
        try:
            datetime.strptime(s[:10], "%Y-%m-%d")
            return s[:10]
        except ValueError:
            return None
    # Normalize "Z" to "+00:00" for fromisoformat
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.date().strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# Monday=0 ... Sunday=6 (Python datetime.weekday())
WEEKDAY_NAMES = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"
]
NAME_TO_WEEKDAY = {name: i for i, name in enumerate(WEEKDAY_NAMES)}

# Default: Wed–Tue week
DEFAULT_WEEK_START = "WEDNESDAY"
DEFAULT_WEEK_END = "TUESDAY"


def weekday_from_name(name: str) -> int:
    """Convert day name to weekday int (0=Monday, 6=Sunday)."""
    u = name.upper().strip()
    if u not in NAME_TO_WEEKDAY:
        raise ValueError(f"Invalid weekday name: {name}. Use one of {list(NAME_TO_WEEKDAY.keys())}")
    return NAME_TO_WEEKDAY[u]


def get_week_range_for_date(
    date_str: str,
    week_start_day: str = DEFAULT_WEEK_START,
    week_end_day: str = DEFAULT_WEEK_END,
) -> Tuple[str, str]:
    """
    Get the (start_date, end_date) of the week containing the given date,
    using configurable week boundaries.

    Args:
        date_str: Date in YYYY-MM-DD format.
        week_start_day: e.g. "WEDNESDAY"
        week_end_day: e.g. "TUESDAY" (day after start when week "ends"; inclusive)

    Returns:
        (week_start_iso, week_end_iso) in YYYY-MM-DD.

    Example:
        Wed–Tue week containing 2025-01-15 (Wednesday):
        -> ("2025-01-15", "2025-01-21")
    """
    d = datetime.strptime(date_str, "%Y-%m-%d")
    start_w = weekday_from_name(week_start_day)
    end_w = weekday_from_name(week_end_day)

    # Current weekday (0=Mon, 6=Sun)
    current = d.weekday()
    # Days back to most recent week_start
    if current >= start_w:
        days_back = current - start_w
    else:
        days_back = (7 + current) - start_w
    week_start = d - timedelta(days=days_back)
    # End is week_end_day in the same logical week (may wrap to next week)
    days_to_end = (end_w - start_w + 7) % 7
    if days_to_end == 0:
        days_to_end = 7
    week_end = week_start + timedelta(days=days_to_end)
    return week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")


def get_weeks_in_range(
    start_date: str,
    end_date: str,
    week_start_day: str = DEFAULT_WEEK_START,
    week_end_day: str = DEFAULT_WEEK_END,
) -> List[Tuple[str, str]]:
    """
    Split a date range into consecutive weeks (each as (week_start, week_end) YYYY-MM-DD),
    using configurable week boundaries. Weeks are clipped to [start_date, end_date].

    Returns:
        List of (week_start, week_end) for each week overlapping the range.
    """
    start_d = datetime.strptime(start_date, "%Y-%m-%d")
    end_d = datetime.strptime(end_date, "%Y-%m-%d")
    out = []
    current_start, current_end = get_week_range_for_date(start_date, week_start_day, week_end_day)
    cs = datetime.strptime(current_start, "%Y-%m-%d")
    ce = datetime.strptime(current_end, "%Y-%m-%d")
    while cs <= end_d and ce >= start_d:
        clip_start = max(cs, start_d).strftime("%Y-%m-%d")
        clip_end = min(ce, end_d).strftime("%Y-%m-%d")
        out.append((clip_start, clip_end))
        # Next week: start day is the day after current week end
        next_start = ce + timedelta(days=1)
        current_start, current_end = get_week_range_for_date(
            next_start.strftime("%Y-%m-%d"), week_start_day, week_end_day
        )
        cs = datetime.strptime(current_start, "%Y-%m-%d")
        ce = datetime.strptime(current_end, "%Y-%m-%d")
    return out


def get_current_week(
    week_start_day: str = DEFAULT_WEEK_START,
    week_end_day: str = DEFAULT_WEEK_END,
) -> Tuple[str, str]:
    """
    Get current week's date range (Wed–Tue by default).
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return get_week_range_for_date(today, week_start_day, week_end_day)


def business_days_between(
    start_date: str,
    end_date: str,
    working_days: Optional[List[int]] = None,
) -> int:
    """
    Number of working days in [start_date, end_date] (inclusive).
    working_days: list of weekday() values, e.g. [0,1,2,3,4] for Mon–Fri.
    """
    if working_days is None:
        working_days = [0, 1, 2, 3, 4]  # Mon–Fri
    start_d = datetime.strptime(start_date, "%Y-%m-%d")
    end_d = datetime.strptime(end_date, "%Y-%m-%d")
    n = 0
    d = start_d
    while d <= end_d:
        if d.weekday() in working_days:
            n += 1
        d += timedelta(days=1)
    return n


def parse_time_rules_from_config(config: dict) -> Dict[str, Any]:
    """
    Build TimeRules-like dict from config for dataset JSON.
    Config may have engine.time_rules or top-level timezone/week boundaries.
    """
    engine = config.get("engine", {}) or {}
    tr = engine.get("time_rules", {})
    return {
        "team_timezone": tr.get("team_timezone", config.get("report_settings", {}).get("timezone", "UTC")),
        "week_boundary_start_day": tr.get("week_boundary_start_day", DEFAULT_WEEK_START),
        "week_boundary_end_day": tr.get("week_boundary_end_day", DEFAULT_WEEK_END),
        "working_days": tr.get("working_days", [0, 1, 2, 3, 4]),
        "business_day_mode": tr.get("business_day_mode", "weekday_only"),
    }


def iso_to_local_date(iso_ts: str, team_timezone: str) -> Optional[date]:
    """
    Parse ISO8601 (with Z or offset) and convert to local date in team_timezone.
    If input is date-only YYYY-MM-DD, treat as local date (no conversion).
    Returns None on parse failure.
    """
    if not iso_ts or not isinstance(iso_ts, str):
        return None
    s = iso_ts.strip()
    if not s:
        return None
    # Date-only YYYY-MM-DD (no time part): treat as local date
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and (len(s) == 10 or s[10:11] not in ("T", "t")):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    # Normalize "Z" to "+00:00" for fromisoformat
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo(team_timezone))
        return local.date()
    except (ValueError, TypeError, Exception):
        return None


def is_date_in_week(d: date, week_start: date, week_end: date) -> bool:
    """True if d is in [week_start, week_end] inclusive."""
    return week_start <= d <= week_end


def get_weeks_in_range(
    start_ymd: str,
    end_ymd: str,
    time_rules: Dict[str, Any],
) -> List[Tuple[date, date]]:
    """
    Produce week windows (week_start_date, week_end_date) in local dates,
    matching boundary start/end days from time_rules. Covers [start_ymd, end_ymd]
    with deterministic ordering; partial first/last weeks included.
    """
    week_start_day = time_rules.get("week_boundary_start_day", DEFAULT_WEEK_START)
    week_end_day = time_rules.get("week_boundary_end_day", DEFAULT_WEEK_END)
    start_d = datetime.strptime(start_ymd, "%Y-%m-%d").date()
    end_d = datetime.strptime(end_ymd, "%Y-%m-%d").date()
    out: List[Tuple[date, date]] = []
    current_start_s, current_end_s = get_week_range_for_date(start_ymd, week_start_day, week_end_day)
    cs = datetime.strptime(current_start_s, "%Y-%m-%d").date()
    ce = datetime.strptime(current_end_s, "%Y-%m-%d").date()
    while cs <= end_d and ce >= start_d:
        clip_start = max(cs, start_d)
        clip_end = min(ce, end_d)
        out.append((clip_start, clip_end))
        next_start = ce + timedelta(days=1)
        current_start_s, current_end_s = get_week_range_for_date(
            next_start.strftime("%Y-%m-%d"), week_start_day, week_end_day
        )
        cs = datetime.strptime(current_start_s, "%Y-%m-%d").date()
        ce = datetime.strptime(current_end_s, "%Y-%m-%d").date()
    return out
