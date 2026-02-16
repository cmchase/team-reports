"""
Type-safe models for the metrics engine API.

Uses dataclasses for consistency and minimal dependencies.
All models are JSON-serializable via asdict() or equivalent.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# -----------------------------------------------------------------------------
# Status and primitives
# -----------------------------------------------------------------------------

Status = Literal["ok", "partial", "error"]
WarningSeverity = Literal["low", "medium", "high"]


@dataclass
class Warning:
    """Configuration or runtime warning."""
    code: str
    message: str
    severity: WarningSeverity  # "low" | "medium" | "high"
    scope: Optional[str] = None  # e.g. "config", "identity", "jira", "github", "gitlab"

    def __post_init__(self) -> None:
        if self.severity not in ("low", "medium", "high"):
            raise ValueError(f"severity must be one of low, medium, high; got {self.severity!r}")


@dataclass
class SourceStatus:
    """Per-source sync status."""
    source_type: str       # "jira" | "github" | "gitlab"
    instance_id: str       # config-defined key, e.g. "redhat-jira", "github.com/orgX"
    status: Status
    error_message: Optional[str] = None
    rate_limit_reset_at: Optional[str] = None  # ISO datetime if known
    cursor: Dict[str, Any] = field(default_factory=dict)  # pagination/watermark state, not a string


@dataclass
class SyncSummary:
    """Summary of sync run across all sources."""
    generated_at: str       # ISO datetime
    sources: List[SourceStatus]
    warnings: List[Warning]


# -----------------------------------------------------------------------------
# Refresh request/options/result
# -----------------------------------------------------------------------------

@dataclass
class RefreshOptions:
    """Options for a refresh run."""
    mode: Literal["incremental", "full"] = "incremental"
    include_markdown: bool = False
    out_dir: str = "."
    buffer_days: int = 0
    safety_margin_hours: int = 24


@dataclass
class RefreshRequest:
    """Request for a full refresh."""
    config_path: str
    team_id: str
    start: str   # YYYY-MM-DD
    end: str     # YYYY-MM-DD
    options: Optional[RefreshOptions] = None


@dataclass
class RefreshResult:
    """Result of a refresh run."""
    schema_version: str
    team_id: str
    requested_range: Dict[str, str]   # {start, end}
    effective_sync_window: Dict[str, Any]  # start, end, buffer_days, safety_margin_hours
    time_rules: Dict[str, Any]
    status: Status
    partial: bool
    sync_summary: SyncSummary
    dataset_path: Optional[str] = None
    meta_path: Optional[str] = None
    weekly_markdown_paths: List[str] = field(default_factory=list)
    quarter_markdown_path: Optional[str] = None


# -----------------------------------------------------------------------------
# Preview
# -----------------------------------------------------------------------------

@dataclass
class EstimatedCounts:
    """Estimated artifact counts per scope (for preview)."""
    jira_issues: int = 0
    github_pull_requests: int = 0
    github_commits: int = 0
    github_reviews: int = 0
    gitlab_merge_requests: int = 0
    gitlab_commits: int = 0
    gitlab_issues: int = 0


@dataclass
class PreviewResult:
    """Result of preview (estimated counts and warnings)."""
    estimated_counts: EstimatedCounts
    warnings: List[Warning]


# -----------------------------------------------------------------------------
# Dataset schema (for writing dataset_latest.json)
# -----------------------------------------------------------------------------

@dataclass
class WeeklySnapshot:
    """One week's snapshot summary (for dataset)."""
    week_start: str
    week_end: str
    jira_count: int = 0
    github_pr_count: int = 0
    github_commit_count: int = 0
    gitlab_mr_count: int = 0
    gitlab_commit_count: int = 0
    gitlab_issue_count: int = 0


@dataclass
class Contributor:
    """Resolved contributor identity (for dataset)."""
    id: str           # stable engine id
    display_name: str
    jira_email: Optional[str] = None
    github_username: Optional[str] = None
    gitlab_username: Optional[str] = None


@dataclass
class ContributorSummary:
    """Aggregated contributor metrics (for dataset)."""
    contributor_id: str
    pr_count: int = 0
    commit_count: int = 0
    issue_count: int = 0
    lines_added: int = 0
    lines_removed: int = 0


def asdict_serializable(obj: Any) -> Any:
    """Recursively convert dataclass to dict for JSON; handle nested dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: asdict_serializable(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, list):
        return [asdict_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: asdict_serializable(v) for k, v in obj.items()}
    return obj
