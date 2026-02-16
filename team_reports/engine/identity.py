"""
Canonical contributor model and identity resolution.

One person = one contributor_id across Jira / GitHub / GitLab.
Contributors are engine-owned data derived from config + discovered identities.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

# Contributor shape (dict): id, display_name, identities { jira_emails, github_logins, gitlab_usernames }
CONTRIBUTOR_ID_PREFIX = "contributor:"
MAX_SAMPLE_UNMAPPED = 10


def _slug(s: str) -> str:
    """Stable slug for display_name: lowercase, alphanumeric and hyphens only."""
    if not s or not isinstance(s, str):
        return ""
    normalized = re.sub(r"[^a-z0-9\-]", "-", s.lower().strip())
    return re.sub(r"-+", "-", normalized).strip("-") or "unknown"


def _contributor_id_from_slug(slug: str) -> str:
    """Stable contributor id from user-chosen or derived slug."""
    if not slug or not slug.strip():
        return f"{CONTRIBUTOR_ID_PREFIX}{hashlib.sha256(b'unknown').hexdigest()[:12]}"
    s = slug.strip()
    if s.startswith(CONTRIBUTOR_ID_PREFIX):
        return s
    return f"{CONTRIBUTOR_ID_PREFIX}{s}"


def _list_or_empty(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if x is not None and str(x).strip()]
    return [str(val).strip()] if str(val).strip() else []


def parse_contributors_from_config(config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str], bool]:
    """
    Build canonical contributors from config.

    If config has top-level "contributors" (list of dicts with id, display_name,
    jira_emails, github_logins, gitlab_usernames), use it as canonical.

    Otherwise fall back to team_members / github_team_members / gitlab_team_members
    (identifier -> display_name). Merge by display_name where unambiguous; do not
    merge when same display_name maps to multiple different identities (emit warning).

    Returns:
        (contributors, warnings, legacy_mode)
        contributors: list of contributor dicts with id, display_name, identities.
        warnings: list of warning messages (e.g. ambiguous merge).
        legacy_mode: True when fallback to team_members merge-by-display_name was used.
    """
    warnings: List[str] = []
    raw = config.get("contributors")
    if isinstance(raw, list) and len(raw) > 0:
        return _parse_canonical_contributors(raw), warnings, False
    warnings.append(
        "Using legacy identity mapping and merge-by-display_name; prefer config.contributors for deterministic mapping."
    )
    contributors = _build_contributors_from_legacy_mappings(config, warnings)
    return contributors, warnings, True


def _content_hash(display_name: str, jira_emails: List[str], github_logins: List[str], gitlab_usernames: List[str], raw_id: str) -> str:
    """Deterministic hash from contributor content (for duplicate id suffix)."""
    canonical = "|".join([
        display_name,
        ",".join(sorted(jira_emails)),
        ",".join(sorted(github_logins)),
        ",".join(sorted(gitlab_usernames)),
        raw_id,
    ])
    return hashlib.sha256(canonical.encode()).hexdigest()[:8]


def _parse_canonical_contributors(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse new config format: contributors: [{ id, display_name, jira_emails, ... }]."""
    # First pass: build entries with base_id and content_hash
    by_base_id: Dict[str, List[Dict[str, Any]]] = {}
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            continue
        display_name = (entry.get("display_name") or "").strip() or f"Contributor {i}"
        raw_id = (entry.get("id") or "")
        raw_id = raw_id.strip() if isinstance(raw_id, str) else ""
        jira_emails = _list_or_empty(entry.get("jira_emails"))
        github_logins = _list_or_empty(entry.get("github_logins"))
        gitlab_usernames = _list_or_empty(entry.get("gitlab_usernames"))
        if raw_id:
            base_cid = _contributor_id_from_slug(raw_id)
        else:
            base_cid = _contributor_id_from_slug(_slug(display_name))
        content_hash = _content_hash(display_name, jira_emails, github_logins, gitlab_usernames, raw_id)
        rec = {
            "display_name": display_name,
            "identities": {"jira_emails": jira_emails, "github_logins": github_logins, "gitlab_usernames": gitlab_usernames},
            "base_cid": base_cid,
            "content_hash": content_hash,
        }
        by_base_id.setdefault(base_cid, []).append(rec)
    # Second pass: assign final id; for duplicates, give unsuffixed id to lexicographically first content_hash
    out = []
    for base_cid, recs in by_base_id.items():
        recs_sorted = sorted(recs, key=lambda r: r["content_hash"])
        for j, rec in enumerate(recs_sorted):
            final_id = base_cid if j == 0 and len(recs_sorted) == 1 else f"{base_cid}-{rec['content_hash']}"
            out.append({
                "id": final_id,
                "display_name": rec["display_name"],
                "identities": rec["identities"],
            })
    return out


def _build_contributors_from_legacy_mappings(
    config: Dict[str, Any],
    warnings: List[str],
) -> List[Dict[str, Any]]:
    """
    Build contributors by merging team_members / github_team_members / gitlab_team_members.
    Same display_name -> same person. If same name maps to multiple different external
    identities (e.g. two emails), do NOT merge; emit warning.
    """
    from team_reports.utils.config import (
        load_team_config,
        generate_jira_team_members,
        generate_github_team_members,
        generate_gitlab_team_members,
    )
    try:
        team_config = load_team_config()
        jira_m = generate_jira_team_members(team_config) if team_config else {}
        github_m = generate_github_team_members(team_config) if team_config else {}
        gitlab_m = generate_gitlab_team_members(team_config) if team_config else {}
    except Exception:
        jira_m = config.get("team_members", {}) if isinstance(config.get("team_members"), dict) else {}
        github_m = config.get("github_team_members", {}) if isinstance(config.get("github_team_members"), dict) else {}
        gitlab_m = config.get("gitlab_team_members", {}) if isinstance(config.get("gitlab_team_members"), dict) else {}
        if not github_m and isinstance(jira_m, dict):
            github_m = jira_m
        if not gitlab_m and isinstance(jira_m, dict):
            gitlab_m = jira_m

    # By display_name: list of (source, identifier)
    by_name: Dict[str, List[Tuple[str, str]]] = {}
    for email, name in (jira_m or {}).items():
        name = (name or "").strip() or email
        by_name.setdefault(name, []).append(("jira", email))
    for login, name in (github_m or {}).items():
        name = (name or "").strip() or login
        by_name.setdefault(name, []).append(("github", login))
    for username, name in (gitlab_m or {}).items():
        name = (name or "").strip() or username
        by_name.setdefault(name, []).append(("gitlab", username))

    contributors = []
    seen_ids = set()
    for display_name, pairs in by_name.items():
        jira_emails = sorted({p[1] for p in pairs if p[0] == "jira"})
        github_logins = sorted({p[1] for p in pairs if p[0] == "github"})
        gitlab_usernames = sorted({p[1] for p in pairs if p[0] == "gitlab"})
        # Ambiguity: same display_name with multiple different identities in same source
        if len(jira_emails) > 1 or len(github_logins) > 1 or len(gitlab_usernames) > 1:
            warnings.append(
                f"Ambiguous identity: display_name={display_name!r} maps to multiple "
                f"identities (jira_emails={len(jira_emails)}, github_logins={len(github_logins)}, "
                f"gitlab_usernames={len(gitlab_usernames)}). Not merging; each identity treated as separate."
            )
            # Treat each identity as its own contributor (no merge)
            for src, ident in pairs:
                cid = hashlib.sha256(f"{CONTRIBUTOR_ID_PREFIX}{src}:{ident}".encode()).hexdigest()[:16]
                cid = f"{CONTRIBUTOR_ID_PREFIX}{cid}"
                if cid in seen_ids:
                    cid = f"{cid}-{ident[:8]}"
                seen_ids.add(cid)
                identities = {"jira_emails": [], "github_logins": [], "gitlab_usernames": []}
                if src == "jira":
                    identities["jira_emails"] = [ident]
                elif src == "github":
                    identities["github_logins"] = [ident]
                else:
                    identities["gitlab_usernames"] = [ident]
                contributors.append({
                    "id": cid,
                    "display_name": display_name,
                    "identities": identities,
                })
            continue
        cid = _contributor_id_from_slug(_slug(display_name))
        if cid in seen_ids:
            cid = f"{cid}-{hashlib.sha256(display_name.encode()).hexdigest()[:8]}"
        seen_ids.add(cid)
        contributors.append({
            "id": cid,
            "display_name": display_name,
            "identities": {
                "jira_emails": jira_emails,
                "github_logins": github_logins,
                "gitlab_usernames": gitlab_usernames,
            },
        })
    return contributors


def build_identity_index(contributors: List[Dict[str, Any]]) -> Dict[Tuple[str, str], str]:
    """
    Build mapping (source, identifier) -> contributor_id.

    source is "jira" | "github" | "gitlab".
    identifier is email (jira), login (github), username (gitlab).
    """
    index: Dict[Tuple[str, str], str] = {}
    for c in contributors:
        cid = c.get("id") or ""
        if not cid:
            continue
        identities = c.get("identities") or {}
        for email in identities.get("jira_emails") or []:
            if email:
                index[("jira", email)] = cid
        for login in identities.get("github_logins") or []:
            if login:
                index[("github", login)] = cid
        for username in identities.get("gitlab_usernames") or []:
            if username:
                index[("gitlab", username)] = cid
    return index


def resolve_contributor_id(
    source: str,
    identifier: Optional[str],
    index: Dict[Tuple[str, str], str],
) -> Optional[str]:
    """Resolve (source, identifier) to contributor_id. Returns None if unmapped."""
    if not identifier or not isinstance(identifier, str) or not identifier.strip():
        return None
    key = (source, identifier.strip())
    return index.get(key)
