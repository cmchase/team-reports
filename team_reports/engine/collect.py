"""
Run source collectors; return RAW source-shaped objects only.

No stable IDs, last_seen_at, source_type, or instance_id on artifacts.
Instance_id lives only in SourceStatus (from config). Normalization happens in api.py.
"""

from typing import Any, Dict, List, Optional, Tuple

from team_reports.engine.models import SourceStatus

# Instance ids when not in config (single-instance)
DEFAULT_JIRA_INSTANCE = "default-jira"
DEFAULT_GITHUB_INSTANCE = "default-github"
DEFAULT_GITLAB_INSTANCE = "default-gitlab"


def _jira_issue_to_raw(issue: Any) -> Dict[str, Any]:
    """Build a raw dict from a Jira issue object for normalize.py (key, issue_id, fields, assignee, etc.)."""
    raw = getattr(issue, "raw", None) or (issue if isinstance(issue, dict) else {})
    fields = getattr(issue, "fields", None) or raw.get("fields", {})
    if hasattr(fields, "__dict__") and not isinstance(fields, dict):
        f = {}
        if hasattr(fields, "updated"):
            f["updated"] = str(fields.updated) if fields.updated else None
        if hasattr(fields, "resolutiondate"):
            f["resolutiondate"] = str(fields.resolutiondate) if fields.resolutiondate else None
        if hasattr(fields, "status") and fields.status:
            f["status"] = {"name": getattr(fields.status, "name", "")}
        if hasattr(fields, "summary"):
            f["summary"] = getattr(fields, "summary", "") or ""
        if hasattr(fields, "assignee") and fields.assignee:
            f["assignee"] = getattr(fields.assignee, "emailAddress", None) or getattr(fields.assignee, "displayName", None)
        if hasattr(fields, "reporter") and fields.reporter:
            f["reporter"] = getattr(fields.reporter, "emailAddress", None) or getattr(fields.reporter, "displayName", None)
        fields = f
    elif isinstance(fields, dict):
        f = dict(fields)
        if "status" in f and isinstance(f["status"], dict):
            pass
        elif "status" in f and hasattr(f["status"], "name"):
            f["status"] = {"name": getattr(f["status"], "name", "")}
        fields = f
    else:
        fields = {}
    key = getattr(issue, "key", None) or raw.get("key", "")
    issue_id = getattr(issue, "id", None) or raw.get("id")
    summary = fields.get("summary") if isinstance(fields, dict) else (getattr(fields, "summary", "") if hasattr(fields, "summary") else "")
    status_val = ""
    if isinstance(fields, dict) and isinstance(fields.get("status"), dict):
        status_val = (fields.get("status") or {}).get("name", "")
    elif isinstance(fields, dict) and hasattr(fields.get("status"), "name"):
        status_val = getattr(fields["status"], "name", "")
    updated_val = (fields.get("updated") or "") if isinstance(fields, dict) else ""
    res_val = (fields.get("resolutiondate") or "") if isinstance(fields, dict) else ""
    if updated_val and hasattr(updated_val, "isoformat"):
        updated_val = str(updated_val)
    if res_val and hasattr(res_val, "isoformat"):
        res_val = str(res_val)
    out = {
        "key": str(key) if key else "",
        "issue_id": issue_id,
        "fields": fields,
        "summary": summary,
        "status": status_val,
        "updated": updated_val,
        "resolutiondate": res_val,
    }
    if isinstance(fields, dict):
        if fields.get("assignee") is not None:
            out["assignee"] = fields["assignee"].get("emailAddress") or fields["assignee"].get("displayName") if isinstance(fields.get("assignee"), dict) else fields["assignee"]
        if fields.get("reporter") is not None:
            out["reporter"] = fields["reporter"].get("emailAddress") or fields["reporter"].get("displayName") if isinstance(fields.get("reporter"), dict) else fields["reporter"]
    return out


def collect_jira(
    config_path: str,
    start_date: str,
    end_date: str,
    instance_id: Optional[str] = None,
    updated_since: Optional[str] = None,
    cursor: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], SourceStatus]:
    """
    Fetch Jira issues; return list of raw issue dicts and SourceStatus.
    If updated_since is set, JQL adds updated >= updated_since. cursor is accepted for API compat (Jira uses maxResults, no cursor stored).
    """
    from team_reports.utils.config import get_config
    from team_reports.utils.jira_client import JiraApiClient
    from team_reports.utils.jira import build_jql_with_dates, fetch_tickets

    config = get_config([config_path])
    inst = instance_id or (config.get("jira") or {}).get("instance_id") or DEFAULT_JIRA_INSTANCE
    try:
        client = JiraApiClient(config_file=config_path)
        client.initialize()
        base_jql = config.get("base_jql", "") or (config.get("jira") or {}).get("base_jql", "")
        default_filter = (
            (config.get("report_settings") or config.get("report", {}))
            .get("default_status_filter", "completed")
        )
        jql = build_jql_with_dates(
            base_jql, start_date, end_date, config, default_filter, updated_since=updated_since
        )
        max_results = (config.get("report_settings") or config.get("report", {})).get("max_results", 200)
        issues = fetch_tickets(client.jira_client, jql, max_results=max_results)
    except Exception as e:
        return [], SourceStatus(
            source_type="jira",
            instance_id=inst,
            status="error",
            error_message=str(e),
        )

    raw_list = []
    for issue in issues:
        key = getattr(issue, "key", None) or (issue.get("key") if isinstance(issue, dict) else None)
        if not key:
            continue
        raw_list.append(_jira_issue_to_raw(issue))
    return raw_list, SourceStatus(source_type="jira", instance_id=inst, status="ok", cursor={})


def collect_github(
    config_path: str,
    start_date: str,
    end_date: str,
    instance_id: Optional[str] = None,
    updated_since: Optional[str] = None,
    cursor: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, List[Dict]], SourceStatus]:
    """
    Fetch GitHub data; return dict of raw lists (pull_requests, commits, issues, reviews) and SourceStatus.
    If updated_since is set, client may use it to restrict PRs/commits (since param). cursor accepted for API compat.
    """
    from team_reports.utils.config import get_config
    from team_reports.utils.github_client import GitHubApiClient

    config = get_config([config_path])
    inst = instance_id or config.get("github", {}).get("instance_id") or (config.get("github_org") or DEFAULT_GITHUB_INSTANCE)
    try:
        client = GitHubApiClient(config_file=config_path)
        data = client.fetch_all_data(start_date, end_date, updated_since=updated_since, cursor=cursor)
    except Exception as e:
        return (
            {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
            SourceStatus(source_type="github", instance_id=inst, status="error", error_message=str(e)),
        )

    prs = []
    for repo, repo_prs in data.get("pull_requests", {}).items():
        for pr in repo_prs:
            prs.append({
                "repository": repo,
                "number": pr.get("number"),
                "node_id": pr.get("node_id", ""),
                "title": pr.get("title", ""),
                "state": pr.get("state", ""),
                "created_at": pr.get("created_at", ""),
                "updated_at": pr.get("updated_at", ""),
                "merged_at": pr.get("merged_at"),
                "html_url": pr.get("html_url", ""),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "changed_files": pr.get("changed_files", 0),
                "user": pr.get("user"),
            })
    commits = []
    for repo, repo_commits in data.get("commits", {}).items():
        for c in repo_commits:
            commit = c.get("commit", {}) or {}
            author = commit.get("author", {}) or {}
            author_info = c.get("author") or {}
            commits.append({
                "repository": repo,
                "sha": c.get("sha", ""),
                "message": commit.get("message", ""),
                "author_date": author.get("date", ""),
                "html_url": c.get("html_url", ""),
                "author": author_info,
                "commit": commit,
            })
    issues = []
    for repo, repo_issues in data.get("issues", {}).items():
        for iss in repo_issues:
            issues.append({
                "repository": repo,
                "number": iss.get("number"),
                "node_id": iss.get("node_id", ""),
                "title": iss.get("title", ""),
                "state": iss.get("state", ""),
                "created_at": iss.get("created_at", ""),
                "updated_at": iss.get("updated_at", ""),
                "html_url": iss.get("html_url", ""),
            })
    reviews = []
    # Reviews not fetched in fetch_all_data; leave empty unless client adds them later
    return (
        {"pull_requests": prs, "commits": commits, "issues": issues, "reviews": reviews},
        SourceStatus(source_type="github", instance_id=inst, status="ok", cursor={}),
    )


def collect_gitlab(
    config_path: str,
    start_date: str,
    end_date: str,
    instance_id: Optional[str] = None,
    updated_since: Optional[str] = None,
    cursor: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, List[Dict]], SourceStatus]:
    """
    Fetch GitLab data; return dict of raw lists (merge_requests, commits, issues) and SourceStatus.
    If updated_since is set, list endpoints use updated_after where supported. cursor accepted for API compat.
    """
    from team_reports.utils.config import get_config
    from team_reports.utils.gitlab_client import GitLabApiClient

    config = get_config([config_path])
    base = (config.get("base_url") or "https://gitlab.com").rstrip("/")
    inst = instance_id or config.get("gitlab", {}).get("instance_id") or base
    try:
        client = GitLabApiClient(config_file=config_path)
        data = client.fetch_all_data(start_date, end_date, updated_since=updated_since, cursor=cursor)
    except Exception as e:
        return (
            {"merge_requests": [], "commits": [], "issues": []},
            SourceStatus(source_type="gitlab", instance_id=inst, status="error", error_message=str(e)),
        )

    mrs = []
    for repo, repo_mrs in data.get("pull_requests", {}).items():
        for mr in repo_mrs:
            iid = mr.get("number") or mr.get("iid")
            if iid is None:
                continue
            mrs.append({
                "project": repo,
                "iid": iid,
                "number": iid,
                "title": mr.get("title", ""),
                "state": mr.get("state", ""),
                "created_at": mr.get("created_at", ""),
                "updated_at": mr.get("updated_at", ""),
                "merged_at": mr.get("merged_at"),
                "html_url": mr.get("html_url", ""),
                "user": mr.get("user"),
            })
    commits = []
    for repo, repo_commits in data.get("commits", {}).items():
        for c in repo_commits:
            sha = (c.get("sha") or (c.get("commit", {}) or {}).get("id", "")) or ""
            if not sha:
                continue
            author = (c.get("commit") or {}).get("author", {}) or {}
            author_top = c.get("author") or {}
            commits.append({
                "project": repo,
                "sha": sha,
                "message": (c.get("commit") or {}).get("message", ""),
                "author_date": author.get("date", ""),
                "html_url": c.get("html_url", ""),
                "author": author_top,
                "commit": c.get("commit"),
            })
    gl_issues = []
    for repo, repo_issues in data.get("issues", {}).items():
        for iss in repo_issues:
            iid = iss.get("number") or iss.get("iid")
            if iid is None:
                continue
            gl_issues.append({
                "project": repo,
                "iid": iid,
                "number": iid,
                "title": iss.get("title", ""),
                "state": iss.get("state", ""),
                "created_at": iss.get("created_at", ""),
                "updated_at": iss.get("updated_at", ""),
                "html_url": iss.get("html_url", ""),
                "user": iss.get("user"),
            })
    return (
        {"merge_requests": mrs, "commits": commits, "issues": gl_issues},
        SourceStatus(source_type="gitlab", instance_id=inst, status="ok", cursor={}),
    )
