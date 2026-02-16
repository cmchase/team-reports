"""
Metrics engine for team-reports.

Produces deterministic structured datasets (JSON) and optional markdown reports.
Consumed in-process by TeamApp; engine owns all source-of-record IO and state.
"""

from team_reports.engine.api import (
    validate_config,
    preview,
    refresh,
    RefreshRequest,
    RefreshResult,
    RefreshOptions,
    PreviewResult,
)
from team_reports.engine import api

__all__ = [
    "api",
    "validate_config",
    "preview",
    "refresh",
    "RefreshRequest",
    "RefreshResult",
    "RefreshOptions",
    "PreviewResult",
]
