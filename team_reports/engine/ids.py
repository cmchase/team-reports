"""
Stable deterministic IDs for engine artifacts.

Do NOT use random UUIDs. IDs are sha256(source_type:instance_id:external_id).
"""

import hashlib
from typing import Any, Optional


def stable_artifact_id(
    source_type: str,
    instance_id: str,
    external_id: str,
) -> str:
    """
    Produce a stable, deterministic engine id for an artifact.

    Args:
        source_type: "jira" | "github" | "gitlab"
        instance_id: Config-defined key (e.g. "redhat-jira", "github.com/org")
        external_id: External system id (issue key, PR number, node_id, sha, etc.)

    Returns:
        Hex digest (e.g. sha256 of "jira:redhat-jira:PROJ-123").
    """
    payload = f"{source_type}:{instance_id}:{external_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def jira_issue_external_id(issue: Any) -> str:
    """External id for a Jira issue (issue key)."""
    if hasattr(issue, "key"):
        return str(issue.key)
    return str(issue.get("key", ""))
