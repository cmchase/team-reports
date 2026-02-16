"""
Normalization layer: stable IDs, last_seen_at, and source metadata on every artifact.

Collectors return raw shapes; normalizers guarantee id, source_type, instance_id,
last_seen_at, plus external ids and optional _raw. Timestamps are ISO8601 or omitted.
"""

import hashlib
import json
from typing import Any, Dict, Optional

# Max bytes for optional _raw payload
_RAW_MAX_BYTES = 8 * 1024


def stable_id(prefix: str, instance_id: str, external: str) -> str:
    """Deterministic stable id: sha256(prefix:instance_id:external)."""
    payload = f"{prefix}:{instance_id}:{external}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _iso_or_omit(val: Any) -> Optional[str]:
    """Return ISO8601 string or None if missing/invalid."""
    if val is None or val == "":
        return None
    s = str(val).strip()
    if not s:
        return None
    # Already ISO-like (has T or is date)
    if "T" in s or (len(s) >= 10 and s[4] == "-" and s[7] == "-"):
        return s
    return None


def _maybe_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Include _raw only if payload is not huge."""
    try:
        b = json.dumps(raw, default=str).encode("utf-8")
        if len(b) <= _RAW_MAX_BYTES:
            return {"_raw": raw}
    except (TypeError, ValueError):
        pass
    return {}


def normalize_jira_issue(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize Jira issue (raw from collector). Required: id, source_type, instance_id, last_seen_at."""
    key = raw.get("key") or raw.get("external_id") or ""
    ext_id = str(key) if key else ""
    out = {
        "id": stable_id("jira", instance_id, ext_id),
        "source_type": "jira",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if ext_id:
        out["key"] = ext_id
    if raw.get("issue_id") is not None:
        out["issue_id"] = raw["issue_id"]
    for k in ("summary", "status"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    # Identity: only include what exists in raw (collect may put assignee/reporter top-level as string)
    assignee_val = raw.get("assignee")
    if assignee_val is not None and isinstance(assignee_val, dict):
        assignee_val = assignee_val.get("emailAddress") or assignee_val.get("displayName")
    if assignee_val is not None and isinstance(assignee_val, str) and assignee_val.strip():
        out["assignee_email"] = assignee_val.strip()
    reporter_val = raw.get("reporter")
    if reporter_val is not None and isinstance(reporter_val, dict):
        reporter_val = reporter_val.get("emailAddress") or reporter_val.get("displayName")
    if reporter_val is not None and isinstance(reporter_val, str) and reporter_val.strip():
        out["reporter_email"] = reporter_val.strip()
    ts = _iso_or_omit(raw.get("updated"))
    if ts is not None:
        out["updated"] = ts
        out["updated_at"] = ts
    ts = _iso_or_omit(raw.get("resolutiondate"))
    if ts is not None:
        out["resolutiondate"] = ts
        out["resolved_at"] = ts
    out.update(_maybe_raw(raw))
    return out


def normalize_github_pr(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitHub PR. Required fields + repo, number, node_id if present."""
    repo = raw.get("repository", "")
    num = raw.get("number")
    node_id = raw.get("node_id") or ""
    ext_id = node_id or str(num) if num is not None else ""
    out = {
        "id": stable_id("github", instance_id, ext_id),
        "source_type": "github",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if repo:
        out["repository"] = repo
    if num is not None:
        out["number"] = num
    if node_id:
        out["node_id"] = node_id
    for k in ("title", "state", "html_url", "additions", "deletions", "changed_files"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    for k in ("created_at", "updated_at", "merged_at"):
        ts = _iso_or_omit(raw.get(k))
        if ts is not None:
            out[k] = ts
    # Identity: PR author from raw user
    user = raw.get("user")
    if isinstance(user, dict) and user.get("login"):
        out["pr_author_login"] = user["login"]
    out.update(_maybe_raw(raw))
    return out


def normalize_github_commit(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitHub commit. Required fields + repo, sha."""
    repo = raw.get("repository", "")
    sha = raw.get("sha") or raw.get("external_id") or ""
    ext_id = sha
    out = {
        "id": stable_id("github", instance_id, ext_id),
        "source_type": "github",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if repo:
        out["repository"] = repo
    if sha:
        out["sha"] = sha
    if raw.get("message") is not None:
        out["message"] = raw["message"]
    if raw.get("html_url") is not None:
        out["html_url"] = raw["html_url"]
    ts = _iso_or_omit(raw.get("author_date"))
    if ts is not None:
        out["author_date"] = ts
        out["authored_at"] = ts
    # Identity: commit author login
    author = raw.get("author")
    if isinstance(author, dict) and author.get("login"):
        out["author_login"] = author["login"]
    out.update(_maybe_raw(raw))
    return out


def normalize_github_review(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitHub review. Required fields + repo, number/node_id if present."""
    repo = raw.get("repository", "")
    num = raw.get("number")
    node_id = raw.get("node_id") or ""
    ext_id = raw.get("external_id") or node_id or (str(num) if num is not None else "")
    if not ext_id and raw.get("id"):
        ext_id = str(raw["id"])
    out = {
        "id": stable_id("github", instance_id, ext_id),
        "source_type": "github",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if repo:
        out["repository"] = repo
    if num is not None:
        out["number"] = num
    if node_id:
        out["node_id"] = node_id
    for k in ("title", "state", "html_url", "body"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    for k in ("created_at", "updated_at", "submitted_at"):
        ts = _iso_or_omit(raw.get(k))
        if ts is not None:
            out[k] = ts
    # Identity: review author
    user = raw.get("user")
    if isinstance(user, dict) and user.get("login"):
        out["review_author_login"] = user["login"]
    out.update(_maybe_raw(raw))
    return out


def normalize_github_issue(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitHub issue (non-PR). Required fields + repo, number, node_id if present."""
    repo = raw.get("repository", "")
    num = raw.get("number")
    node_id = raw.get("node_id") or ""
    ext_id = node_id or str(num) if num is not None else ""
    out = {
        "id": stable_id("github", instance_id, ext_id),
        "source_type": "github",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if repo:
        out["repository"] = repo
    if num is not None:
        out["number"] = num
    if node_id:
        out["node_id"] = node_id
    for k in ("title", "state", "html_url"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    for k in ("created_at", "updated_at"):
        ts = _iso_or_omit(raw.get(k))
        if ts is not None:
            out[k] = ts
    out.update(_maybe_raw(raw))
    return out


def normalize_gitlab_mr(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitLab merge request. Required fields + project, iid."""
    project = raw.get("project", "")
    iid = raw.get("iid") or raw.get("number")
    ext_id = f"{project}:{iid}" if project and iid is not None else raw.get("external_id", "")
    if not ext_id and iid is not None:
        ext_id = str(iid)
    out = {
        "id": stable_id("gitlab", instance_id, ext_id),
        "source_type": "gitlab",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if project:
        out["project"] = project
    if iid is not None:
        out["iid"] = iid
    for k in ("title", "state", "html_url"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    for k in ("created_at", "updated_at", "merged_at"):
        ts = _iso_or_omit(raw.get(k))
        if ts is not None:
            out[k] = ts
    # Identity: GitLab MR author (normalized shape has user.login)
    user = raw.get("user")
    if isinstance(user, dict) and user.get("login"):
        out["author_username"] = user["login"]
    out.update(_maybe_raw(raw))
    return out


def normalize_gitlab_issue(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitLab issue. Required fields + project, iid."""
    project = raw.get("project", "")
    iid = raw.get("iid") or raw.get("number")
    ext_id = f"{project}:{iid}" if project and iid is not None else raw.get("external_id", "")
    if not ext_id and iid is not None:
        ext_id = str(iid)
    out = {
        "id": stable_id("gitlab", instance_id, ext_id),
        "source_type": "gitlab",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if project:
        out["project"] = project
    if iid is not None:
        out["iid"] = iid
    for k in ("title", "state", "html_url"):
        if raw.get(k) is not None:
            out[k] = raw[k]
    for k in ("created_at", "updated_at"):
        ts = _iso_or_omit(raw.get(k))
        if ts is not None:
            out[k] = ts
    # Identity: GitLab issue author
    user = raw.get("user")
    if isinstance(user, dict) and user.get("login"):
        out["author_username"] = user["login"]
    out.update(_maybe_raw(raw))
    return out


def normalize_gitlab_commit(raw: Dict[str, Any], instance_id: str, generated_at: str) -> Dict[str, Any]:
    """Normalize GitLab commit. Required fields + project, sha."""
    project = raw.get("project", "")
    sha = raw.get("sha") or ""
    ext_id = f"{project}:{sha}" if project and sha else raw.get("external_id", sha)
    out = {
        "id": stable_id("gitlab", instance_id, ext_id),
        "source_type": "gitlab",
        "instance_id": instance_id,
        "last_seen_at": generated_at,
    }
    if project:
        out["project"] = project
    if sha:
        out["sha"] = sha
    if raw.get("message") is not None:
        out["message"] = raw["message"]
    if raw.get("html_url") is not None:
        out["html_url"] = raw["html_url"]
    ts = _iso_or_omit(raw.get("author_date"))
    if ts is not None:
        out["author_date"] = ts
        out["authored_at"] = ts
    # Identity: GitLab commit author (normalized shape has author.login)
    author = raw.get("author")
    if isinstance(author, dict) and author.get("login"):
        out["author_username"] = author["login"]
    out.update(_maybe_raw(raw))
    return out
