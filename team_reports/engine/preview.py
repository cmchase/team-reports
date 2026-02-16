"""
Lightweight preview: estimated counts per source for setup wizard.
No dataset write, no engine state. Uses total-count endpoints where possible.
"""

import os
from typing import Any, Dict, List, Tuple

from team_reports.engine.models import EstimatedCounts, Warning


def _jira_count(config_path: str, start: str, end: str) -> Tuple[int, List[Warning]]:
    """Jira: JQL search with maxResults=0 to get total. Returns (count, warnings)."""
    warnings: List[Warning] = []
    try:
        from team_reports.utils.config import get_config
        from team_reports.utils.jira import build_jql_with_dates
        from team_reports.utils.jira_client import JiraApiClient

        cfg = get_config([config_path])
        base_jql = cfg.get("base_jql") or (cfg.get("jira") or {}).get("base_jql") or ""
        if not base_jql.strip():
            return 0, warnings
        default_filter = (
            (cfg.get("report_settings") or cfg.get("report", {})).get("default_status_filter", "completed")
        )
        jql = build_jql_with_dates(base_jql, start, end, cfg, default_filter)
        client = JiraApiClient(config_file=config_path)
        client.initialize()
        result = client.jira_client.search_issues(jql, maxResults=0)
        total = getattr(result, "total", 0)
        if total is None:
            total = 0
        return int(total), warnings
    except Exception as e:
        warnings.append(
            Warning(
                code="jira_preview_error",
                message=f"Jira count unavailable: {e}",
                severity="medium",
                scope="jira",
            )
        )
        return 0, warnings


def _github_counts(config_path: str, start: str, end: str) -> Tuple[Dict[str, int], List[Warning]]:
    """GitHub: search/issues for PRs (total_count); commits rough/omitted. Returns (counts dict, warnings)."""
    warnings: List[Warning] = []
    counts = {"pr": 0, "commit": 0, "review": 0}
    try:
        import requests
        from team_reports.utils.config import get_config

        cfg = get_config([config_path])
        token = os.environ.get("GITHUB_TOKEN") or (cfg.get("github") or {}).get("token")
        if not token:
            warnings.append(
                Warning(
                    code="github_preview_no_token",
                    message="GitHub token missing; counts will be 0.",
                    severity="medium",
                    scope="github",
                )
            )
            return counts, warnings
        repos = cfg.get("repositories") or (cfg.get("github") or {}).get("repositories") or []
        org = cfg.get("github_org") or (cfg.get("github") or {}).get("github_org") or ""
        if not repos and not org:
            return counts, warnings
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        # Search PRs merged in range
        q_parts = ["is:pr", f"merged:{start}..{end}"]
        if org:
            q_parts.append(f"org:{org}")
        elif repos:
            repo_path = (org + "/" + repos[0]) if org else repos[0]
            q_parts.append(f"repo:{repo_path}")
        q = " ".join(q_parts)
        resp = requests.get(
            "https://api.github.com/search/issues",
            params={"q": q, "per_page": 1},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        counts["pr"] = int(data.get("total_count", 0))
        # Commits: no cheap total from GitHub search for commits in range; omit and warn
        if repos or org:
            warnings.append(
                Warning(
                    code="github_commit_estimate",
                    message="Commit count not estimated in preview; run refresh for full data.",
                    severity="low",
                    scope="github",
                )
            )
    except Exception as e:
        warnings.append(
            Warning(
                code="github_preview_error",
                message=f"GitHub counts unavailable: {e}",
                severity="medium",
                scope="github",
            )
        )
    return counts, warnings


def _gitlab_counts(config_path: str, start: str, end: str) -> Tuple[Dict[str, int], List[Warning]]:
    """GitLab: list with per_page=1, read X-Total from headers. Returns (counts dict, warnings)."""
    warnings: List[Warning] = []
    counts = {"mr": 0, "issue": 0, "commit": 0}
    try:
        import urllib.parse
        import requests
        from team_reports.utils.config import get_config

        cfg = get_config([config_path])
        token = os.environ.get("GITLAB_TOKEN") or (cfg.get("gitlab") or {}).get("token")
        if not token:
            warnings.append(
                Warning(
                    code="gitlab_preview_no_token",
                    message="GitLab token missing; counts will be 0.",
                    severity="medium",
                    scope="gitlab",
                )
            )
            return counts, warnings
        projects = cfg.get("projects") or (cfg.get("gitlab") or {}).get("projects") or []
        if not projects:
            return counts, warnings
        base = (cfg.get("base_url") or (cfg.get("gitlab") or {}).get("base_url") or "https://gitlab.com").rstrip("/")
        api_base = f"{base}/api/v4"
        headers = {"PRIVATE-TOKEN": token}
        verify = (cfg.get("api_settings") or {}).get("verify_ssl", True)
        if isinstance(verify, bool):
            verify_ssl = verify
        else:
            verify_ssl = True

        def _get_total(endpoint: str, params: Dict[str, Any]) -> int:
            url = f"{api_base}/{endpoint}"
            params = dict(params)
            params.setdefault("per_page", 1)
            params.setdefault("page", 1)
            try:
                r = requests.get(url, headers=headers, params=params, timeout=15, verify=verify_ssl)
                r.raise_for_status()
                total = r.headers.get("X-Total") or r.headers.get("x-total")
                return int(total) if total is not None and total.isdigit() else 0
            except Exception:
                return 0

        for project in projects:
            proj_id = urllib.parse.quote(project, safe="")
            counts["mr"] += _get_total(
                f"projects/{proj_id}/merge_requests",
                {"state": "all", "order_by": "updated_at", "sort": "desc"},
            )
            counts["issue"] += _get_total(
                f"projects/{proj_id}/issues",
                {"state": "all", "order_by": "updated_at", "sort": "desc"},
            )
            counts["commit"] += _get_total(
                f"projects/{proj_id}/repository/commits",
                {"since": f"{start}T00:00:00Z", "until": f"{end}T23:59:59Z"},
            )
    except Exception as e:
        warnings.append(
            Warning(
                code="gitlab_preview_error",
                message=f"GitLab counts unavailable: {e}",
                severity="medium",
                scope="gitlab",
            )
        )
    return counts, warnings


def estimate_counts(config_path: str, start: str, end: str) -> Tuple[EstimatedCounts, List[Warning]]:
    """
    Compute estimated counts for the range. No side effects (no dataset write, no engine state).
    """
    from team_reports.utils.config import get_config

    counts = EstimatedCounts()
    warnings: List[Warning] = []
    try:
        cfg = get_config([config_path])
    except Exception as e:
        warnings.append(
            Warning(code="config_load_error", message=str(e), severity="high", scope="config")
        )
        return counts, warnings

    if not cfg.get("base_jql") and not (cfg.get("jira") or {}).get("base_jql"):
        warnings.append(
            Warning(
                code="missing_jira_jql",
                message="No base_jql configured; Jira issues will be empty.",
                severity="medium",
                scope="jira",
            )
        )
    else:
        jira_n, jira_w = _jira_count(config_path, start, end)
        counts.jira_issues = jira_n
        warnings.extend(jira_w)

    gh, gh_w = _github_counts(config_path, start, end)
    counts.github_pull_requests = gh["pr"]
    counts.github_commits = gh["commit"]
    counts.github_reviews = gh["review"]
    warnings.extend(gh_w)

    gl, gl_w = _gitlab_counts(config_path, start, end)
    counts.gitlab_merge_requests = gl["mr"]
    counts.gitlab_issues = gl["issue"]
    counts.gitlab_commits = gl["commit"]
    warnings.extend(gl_w)

    return counts, warnings
