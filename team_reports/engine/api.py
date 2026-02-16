"""
Public, stable engine API.

- validate_config(config_path) -> list[Warning]
- preview(config_path, team_id, start, end) -> PreviewResult
- refresh(request: RefreshRequest) -> RefreshResult
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from team_reports.engine.models import (
    EstimatedCounts,
    PreviewResult,
    RefreshOptions,
    RefreshRequest,
    RefreshResult,
    SourceStatus,
    SyncSummary,
    Warning,
    asdict_serializable,
)
from team_reports.engine.time_rules import (
    get_weeks_in_range,
    iso_to_local_date,
    is_date_in_week,
    parse_time_rules_from_config,
)
from team_reports.engine.dataset_writer import write_dataset
from team_reports.engine.state import (
    get_source_state,
    load_engine_state,
    save_engine_state,
    update_source_state,
)
from team_reports.engine import collect
from team_reports.engine import normalize as norm


def validate_config(config_path: str) -> List[Warning]:
    """
    Validate configuration at the given path.
    Returns list of warnings (validation errors or hints); empty if valid.
    """
    from team_reports.utils.config import get_config, validate_config as validate_config_impl
    warnings = []
    try:
        cfg = get_config([config_path])
    except Exception as e:
        warnings.append(Warning(code="config_load_error", message=str(e), severity="high", scope="config"))
        return warnings
    errors = validate_config_impl(cfg)
    for msg in errors:
        warnings.append(Warning(code="validation", message=msg, severity="medium", scope="config"))
    team_members = cfg.get("team_members", {})
    if not team_members:
        warnings.append(Warning(
            code="missing_team_members",
            message="No team_members in config; identity mapping may be incomplete.",
            severity="low",
            scope="identity",
        ))
    return warnings


def preview(
    config_path: str,
    team_id: str,
    start: str,
    end: str,
) -> PreviewResult:
    """
    Preview estimated counts and warnings for a range.
    Does not fetch full data; uses total-count endpoints where possible.
    No side effects: does not call dataset_writer or read/write engine_state.
    """
    from team_reports.engine.preview import estimate_counts

    counts, warnings = estimate_counts(config_path, start, end)
    # Merge config/identity warnings (validate_config only reads config, no engine state / file write)
    warnings.extend(validate_config(config_path))
    return PreviewResult(estimated_counts=counts, warnings=warnings)


def refresh(request: RefreshRequest) -> RefreshResult:
    """
    Run a full or incremental refresh: fetch from all sources, normalize to
    artifacts with stable IDs, write dataset bundle and engine state.
    Returns RefreshResult with status/partial/sync_summary and paths.

    """
    from team_reports.utils.config import get_config
    opts = request.options or RefreshOptions()
    config = get_config([request.config_path])
    time_rules = parse_time_rules_from_config(config)

    # Effective window: expand by buffer_days
    start_d = datetime.strptime(request.start, "%Y-%m-%d")
    end_d = datetime.strptime(request.end, "%Y-%m-%d")
    effective_start_d = start_d - timedelta(days=opts.buffer_days)
    effective_end_d = end_d + timedelta(days=opts.buffer_days)
    effective_start = effective_start_d.strftime("%Y-%m-%d")
    effective_end = effective_end_d.strftime("%Y-%m-%d")

    generated_at = datetime.now(timezone.utc).isoformat()
    source_statuses = []
    warnings_list: List[Warning] = []
    artifacts = {
        "jira_issues": [],
        "github_pull_requests": [],
        "github_commits": [],
        "github_reviews": [],
        "gitlab_merge_requests": [],
        "gitlab_commits": [],
        "gitlab_issues": [],
    }
    engine_state = load_engine_state(opts.out_dir, request.team_id)
    mode = opts.mode or "incremental"
    is_full = mode == "full"

    def _updated_since_and_cursor(source_type: str, instance_id: str):
        """For incremental: return (updated_since_iso, cursor_dict) or (None, None) when no prior state."""
        if is_full:
            return None, None
        s = get_source_state(engine_state, source_type, instance_id)
        last = s.get("last_successful_sync_at")
        if not last:
            return None, None
        try:
            # last is ISO8601; subtract safety_margin_hours
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            since_dt = dt - timedelta(hours=opts.safety_margin_hours)
            updated_since = since_dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            cursor = s.get("cursor") or {}
            if not isinstance(cursor, dict):
                cursor = {}
            return updated_since, cursor
        except Exception:
            return None, None

    # ---- Jira ----
    try:
        jira_inst = (config.get("jira") or {}).get("instance_id") or collect.DEFAULT_JIRA_INSTANCE
        updated_since, cursor = _updated_since_and_cursor("jira", jira_inst)
        jira_raw, jira_status = collect.collect_jira(
            request.config_path, effective_start, effective_end,
            updated_since=updated_since, cursor=cursor,
        )
        if mode == "incremental" and updated_since is None:
            warnings_list.append(Warning(
                code="incremental_cold_start",
                message="No prior Jira state; performed full fetch for this source.",
                severity="low",
                scope="jira",
            ))
        artifacts["jira_issues"] = [
            norm.normalize_jira_issue(a, jira_status.instance_id, generated_at)
            for a in jira_raw
        ]
        source_statuses.append(jira_status)
        if jira_status.status == "ok":
            update_source_state(
                engine_state, "jira", jira_status.instance_id,
                last_successful_sync_at=generated_at,
                last_attempt_at=generated_at,
                cursor=jira_status.cursor if hasattr(jira_status, "cursor") else {},
                last_mode=mode,
            )
        else:
            update_source_state(
                engine_state, "jira", jira_status.instance_id,
                last_attempt_at=generated_at, last_error=jira_status.error_message,
                last_mode=mode,
            )
    except Exception as e:
        source_statuses.append(SourceStatus(
            source_type="jira", instance_id="default-jira", status="error", error_message=str(e)
        ))
        warnings_list.append(Warning(code="jira_error", message=str(e), severity="high", scope="jira"))

    # ---- GitHub ----
    try:
        gh_inst = config.get("github", {}).get("instance_id") or (config.get("github_org") or collect.DEFAULT_GITHUB_INSTANCE)
        updated_since, cursor = _updated_since_and_cursor("github", gh_inst)
        gh_data, gh_status = collect.collect_github(
            request.config_path, effective_start, effective_end,
            updated_since=updated_since, cursor=cursor,
        )
        if mode == "incremental" and updated_since is None:
            warnings_list.append(Warning(
                code="incremental_cold_start",
                message="No prior GitHub state; performed full fetch for this source.",
                severity="low",
                scope="github",
            ))
        inst = gh_status.instance_id
        artifacts["github_pull_requests"] = [
            norm.normalize_github_pr(a, inst, generated_at)
            for a in gh_data.get("pull_requests", [])
        ]
        artifacts["github_commits"] = [
            norm.normalize_github_commit(a, inst, generated_at)
            for a in gh_data.get("commits", [])
        ]
        artifacts["github_reviews"] = [
            norm.normalize_github_review(a, inst, generated_at)
            for a in gh_data.get("reviews", [])
        ]
        source_statuses.append(gh_status)
        if gh_status.status == "ok":
            update_source_state(
                engine_state, "github", gh_status.instance_id,
                last_successful_sync_at=generated_at,
                last_attempt_at=generated_at,
                cursor=gh_status.cursor if hasattr(gh_status, "cursor") else {},
                last_mode=mode,
            )
        else:
            update_source_state(
                engine_state, "github", gh_status.instance_id,
                last_attempt_at=generated_at, last_error=gh_status.error_message,
                last_mode=mode,
            )
    except Exception as e:
        source_statuses.append(SourceStatus(
            source_type="github", instance_id="default-github", status="error", error_message=str(e)
        ))
        warnings_list.append(Warning(code="github_error", message=str(e), severity="high", scope="github"))

    # ---- GitLab ----
    try:
        gl_inst = (config.get("gitlab") or {}).get("instance_id") or (config.get("base_url") or "https://gitlab.com").rstrip("/")
        updated_since, cursor = _updated_since_and_cursor("gitlab", gl_inst)
        gl_data, gl_status = collect.collect_gitlab(
            request.config_path, effective_start, effective_end,
            updated_since=updated_since, cursor=cursor,
        )
        if mode == "incremental" and updated_since is None:
            warnings_list.append(Warning(
                code="incremental_cold_start",
                message="No prior GitLab state; performed full fetch for this source.",
                severity="low",
                scope="gitlab",
            ))
        inst = gl_status.instance_id
        artifacts["gitlab_merge_requests"] = [
            norm.normalize_gitlab_mr(a, inst, generated_at)
            for a in gl_data.get("merge_requests", [])
        ]
        artifacts["gitlab_commits"] = [
            norm.normalize_gitlab_commit(a, inst, generated_at)
            for a in gl_data.get("commits", [])
        ]
        artifacts["gitlab_issues"] = [
            norm.normalize_gitlab_issue(a, inst, generated_at)
            for a in gl_data.get("issues", [])
        ]
        source_statuses.append(gl_status)
        if gl_status.status == "ok":
            update_source_state(
                engine_state, "gitlab", gl_status.instance_id,
                last_successful_sync_at=generated_at,
                last_attempt_at=generated_at,
                cursor=gl_status.cursor if hasattr(gl_status, "cursor") else {},
                last_mode=mode,
            )
        else:
            update_source_state(
                engine_state, "gitlab", gl_status.instance_id,
                last_attempt_at=generated_at, last_error=gl_status.error_message,
                last_mode=mode,
            )
    except Exception as e:
        source_statuses.append(SourceStatus(
            source_type="gitlab", instance_id="default-gitlab", status="error", error_message=str(e)
        ))
        warnings_list.append(Warning(code="gitlab_error", message=str(e), severity="high", scope="gitlab"))

    # ---- Dedupe artifacts by stable id (overlap must not double count) ----
    def _dedupe_by_id(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id: Dict[str, Dict[str, Any]] = {}
        no_id_artifact: Optional[Dict[str, Any]] = None
        for a in items:
            aid = a.get("id")
            if aid is not None:
                by_id[aid] = a
            else:
                no_id_artifact = a
        out = list(by_id.values())
        if no_id_artifact is not None:
            out.append(no_id_artifact)
        return out
    for key in artifacts:
        artifacts[key] = _dedupe_by_id(artifacts[key])

    # ---- Status rollup ----
    if not source_statuses:
        status = "error"
        partial = True
        warnings_list.append(Warning(
            code="no_sources_configured",
            message="No sources were configured or ran; check config and credentials.",
            severity="high",
            scope="config",
        ))
    elif all(s.status == "error" for s in source_statuses):
        status = "error"
        partial = True
    elif any(s.status == "error" or s.status == "partial" for s in source_statuses):
        status = "partial"
        partial = True
    else:
        status = "ok"
        partial = False

    # ---- Weekly snapshots (timezone-aware; normalized keys; references + highlights + threshold_flags) ----
    REFS_CAP = 500
    HIGHLIGHTS_CAP = 5
    HIGH_REVIEW_LOAD_THRESHOLD = 20
    tz = time_rules.get("team_timezone", "UTC")
    weeks = get_weeks_in_range(request.start, request.end, time_rules)
    weekly_snapshots = []
    for week_start_d, week_end_d in weeks:
        refs: Dict[str, List[str]] = {
            "jira_issue_ids": [],
            "github_pr_ids": [],
            "github_commit_ids": [],
            "github_review_ids": [],
            "gitlab_mr_ids": [],
            "gitlab_commit_ids": [],
            "gitlab_issue_ids": [],
        }
        snap = {
            "week_start": week_start_d.strftime("%Y-%m-%d"),
            "week_end": week_end_d.strftime("%Y-%m-%d"),
            "jira_count": 0,
            "github_pr_count": 0,
            "github_commit_count": 0,
            "github_review_count": 0,
            "gitlab_mr_count": 0,
            "gitlab_commit_count": 0,
            "gitlab_issue_count": 0,
        }
        for art in artifacts["jira_issues"]:
            ts = art.get("resolved_at") or art.get("updated_at") or ""
            local_d = iso_to_local_date(ts, tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["jira_count"] += 1
                if len(refs["jira_issue_ids"]) < REFS_CAP and art.get("id"):
                    refs["jira_issue_ids"].append(art["id"])
        for art in artifacts["github_pull_requests"]:
            local_d = iso_to_local_date(art.get("merged_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["github_pr_count"] += 1
                if len(refs["github_pr_ids"]) < REFS_CAP and art.get("id"):
                    refs["github_pr_ids"].append(art["id"])
        for art in artifacts["github_commits"]:
            local_d = iso_to_local_date(art.get("authored_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["github_commit_count"] += 1
                if len(refs["github_commit_ids"]) < REFS_CAP and art.get("id"):
                    refs["github_commit_ids"].append(art["id"])
        for art in artifacts["github_reviews"]:
            ts = art.get("submitted_at") or art.get("created_at") or ""
            local_d = iso_to_local_date(ts, tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["github_review_count"] += 1
                if len(refs["github_review_ids"]) < REFS_CAP and art.get("id"):
                    refs["github_review_ids"].append(art["id"])
        for art in artifacts["gitlab_merge_requests"]:
            local_d = iso_to_local_date(art.get("merged_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_mr_count"] += 1
                if len(refs["gitlab_mr_ids"]) < REFS_CAP and art.get("id"):
                    refs["gitlab_mr_ids"].append(art["id"])
        for art in artifacts["gitlab_commits"]:
            local_d = iso_to_local_date(art.get("authored_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_commit_count"] += 1
                if len(refs["gitlab_commit_ids"]) < REFS_CAP and art.get("id"):
                    refs["gitlab_commit_ids"].append(art["id"])
        for art in artifacts["gitlab_issues"]:
            ts = art.get("updated_at") or art.get("created_at") or ""
            local_d = iso_to_local_date(ts, tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_issue_count"] += 1
                if len(refs["gitlab_issue_ids"]) < REFS_CAP and art.get("id"):
                    refs["gitlab_issue_ids"].append(art["id"])
        snap["partial"] = partial
        snap["references"] = refs
        highlights = []
        if snap["jira_count"]:
            highlights.append(f"{snap['jira_count']} Jira issue(s) resolved")
        if snap["github_pr_count"]:
            highlights.append(f"{snap['github_pr_count']} PR(s) merged")
        if snap["github_commit_count"]:
            highlights.append(f"{snap['github_commit_count']} GitHub commit(s)")
        if snap["gitlab_mr_count"]:
            highlights.append(f"{snap['gitlab_mr_count']} GitLab MR(s) merged")
        if snap["gitlab_commit_count"]:
            highlights.append(f"{snap['gitlab_commit_count']} GitLab commit(s)")
        if snap["gitlab_issue_count"]:
            highlights.append(f"{snap['gitlab_issue_count']} GitLab issue(s) updated")
        snap["highlights"] = highlights[:HIGHLIGHTS_CAP]
        weekly_snapshots.append(snap)

    # Threshold flags (deterministic; require full snapshot list for prior-week comparison)
    for i, snap in enumerate(weekly_snapshots):
        flags: List[Dict[str, Any]] = []
        j, pr, gh_c, rev, gl_mr, gl_c, gl_i = (
            snap["jira_count"],
            snap["github_pr_count"],
            snap["github_commit_count"],
            snap["github_review_count"],
            snap["gitlab_mr_count"],
            snap["gitlab_commit_count"],
            snap["gitlab_issue_count"],
        )
        total = j + pr + gh_c + rev + gl_mr + gl_c + gl_i
        if total == 0:
            flags.append({"code": "no_activity", "severity": "medium", "message": "No activity in this week."})
        if pr == 0 and gh_c > 0:
            flags.append({"code": "no_prs_merged", "severity": "medium", "message": "Commits but no PRs merged."})
        if rev > HIGH_REVIEW_LOAD_THRESHOLD:
            flags.append({"code": "high_review_load", "severity": "low", "message": f"High review count ({rev})."})
        if i > 0:
            prev = weekly_snapshots[i - 1]
            prev_pr = prev["github_pr_count"] + prev["gitlab_mr_count"]
            curr_pr = pr + gl_mr
            if prev_pr > 0 and curr_pr >= 2 * prev_pr:
                flags.append({"code": "spike_prs", "severity": "low", "message": "PR/MR count ≥2× prior week."})
        snap["threshold_flags"] = flags

    # ---- Contributors and identity resolution (engine-owned) ----
    from team_reports.engine import identity as identity_mod

    contributors, identity_warnings, legacy_mode = identity_mod.parse_contributors_from_config(config)
    for msg in identity_warnings:
        code = "identity_legacy_mode" if "Using legacy" in msg else "identity_ambiguous"
        severity = "low" if code == "identity_legacy_mode" else "medium"
        warnings_list.append(Warning(code=code, message=msg, severity=severity, scope="identity"))
    index = identity_mod.build_identity_index(contributors)

    # Resolve contributor_id on artifacts and track unmapped
    unmapped: Dict[str, Dict[str, Any]] = {"jira": {"count": 0, "sample": []}, "github": {"count": 0, "sample": []}, "gitlab": {"count": 0, "sample": []}}

    def _resolve_and_set(art: Dict[str, Any], source: str, identifier: Optional[str]) -> None:
        cid = identity_mod.resolve_contributor_id(source, identifier, index) if identifier else None
        art["contributor_id"] = cid
        if identifier and not cid:
            u = unmapped[source]
            u["count"] = u["count"] + 1
            if len(u["sample"]) < identity_mod.MAX_SAMPLE_UNMAPPED and identifier not in u["sample"]:
                u["sample"].append(identifier)

    for art in artifacts["jira_issues"]:
        ident = art.get("assignee_email") or art.get("reporter_email")
        _resolve_and_set(art, "jira", ident)
    for art in artifacts["github_pull_requests"]:
        _resolve_and_set(art, "github", art.get("pr_author_login"))
    for art in artifacts["github_commits"]:
        _resolve_and_set(art, "github", art.get("author_login"))
    for art in artifacts["github_reviews"]:
        _resolve_and_set(art, "github", art.get("review_author_login"))
    for art in artifacts["gitlab_merge_requests"]:
        _resolve_and_set(art, "gitlab", art.get("author_username"))
    for art in artifacts["gitlab_commits"]:
        _resolve_and_set(art, "gitlab", art.get("author_username"))
    for art in artifacts["gitlab_issues"]:
        _resolve_and_set(art, "gitlab", art.get("author_username"))

    for source, u in unmapped.items():
        if u["count"] > 0:
            sample_str = ", ".join(u["sample"][:10])
            msg = f"Unmapped {source.capitalize()} identities: {u['count']} (sample: {sample_str})"
            severity = "medium" if u["count"] > 5 else "low"
            warnings_list.append(Warning(code="unmapped_identity", message=msg, severity=severity, scope="identity"))

    sync_summary = SyncSummary(
        generated_at=generated_at,
        sources=source_statuses,
        warnings=warnings_list,
    )

    # ---- Computed contributor summaries (only artifacts with contributor_id set; explicit per-source counts) ----
    _zero_agg = {
        "github_pr_merged_count": 0,
        "github_commit_count": 0,
        "gitlab_mr_merged_count": 0,
        "gitlab_commit_count": 0,
        "jira_issue_resolved_count": 0,
        "gitlab_issue_count": 0,
    }
    by_cid: Dict[str, Dict[str, int]] = {}
    for c in contributors:
        cid = c.get("id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))
    for art in artifacts["github_pull_requests"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["github_pr_merged_count"] += 1
    for art in artifacts["github_commits"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["github_commit_count"] += 1
    for art in artifacts["gitlab_merge_requests"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["gitlab_mr_merged_count"] += 1
    for art in artifacts["gitlab_commits"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["gitlab_commit_count"] += 1
    for art in artifacts["jira_issues"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["jira_issue_resolved_count"] += 1
    for art in artifacts["gitlab_issues"]:
        cid = art.get("contributor_id")
        if cid:
            by_cid.setdefault(cid, dict(_zero_agg))["gitlab_issue_count"] += 1
    comp_summaries = []
    for c in contributors:
        cid = c.get("id")
        if not cid:
            continue
        agg = by_cid.get(cid, _zero_agg)
        comp_summaries.append({
            "contributor_id": cid,
            "github_pr_merged_count": agg.get("github_pr_merged_count", 0),
            "github_commit_count": agg.get("github_commit_count", 0),
            "gitlab_mr_merged_count": agg.get("gitlab_mr_merged_count", 0),
            "gitlab_commit_count": agg.get("gitlab_commit_count", 0),
            "jira_issue_resolved_count": agg.get("jira_issue_resolved_count", 0),
            "gitlab_issue_count": agg.get("gitlab_issue_count", 0),
            "pr_count": agg.get("github_pr_merged_count", 0) + agg.get("gitlab_mr_merged_count", 0),
            "commit_count": agg.get("github_commit_count", 0) + agg.get("gitlab_commit_count", 0),
            "issue_count": agg.get("jira_issue_resolved_count", 0) + agg.get("gitlab_issue_count", 0),
            "lines_added": 0,
            "lines_removed": 0,
        })

    # ---- Write dataset and state ----
    dataset_path, meta_path, _ = write_dataset(
        out_dir=opts.out_dir,
        team_id=request.team_id,
        requested_start=request.start,
        requested_end=request.end,
        effective_start=effective_start,
        effective_end=effective_end,
        buffer_days=opts.buffer_days,
        safety_margin_hours=opts.safety_margin_hours,
        time_rules=time_rules,
        status=status,
        partial=partial,
        sync_summary=sync_summary,
        weekly_snapshots=weekly_snapshots,
        artifacts=artifacts,
        contributors=contributors,
        computed_contributor_summaries=comp_summaries,
        generated_at=generated_at,
    )
    save_engine_state(opts.out_dir, request.team_id, engine_state)

    weekly_markdown_paths = []
    quarter_markdown_path = None
    if opts.include_markdown:
        # Optional: generate markdown from dataset (no extra API calls)
        pass

    return RefreshResult(
        schema_version="1.0",
        team_id=request.team_id,
        requested_range={"start": request.start, "end": request.end},
        effective_sync_window={
            "start": effective_start,
            "end": effective_end,
            "buffer_days": opts.buffer_days,
            "safety_margin_hours": opts.safety_margin_hours,
        },
        time_rules=time_rules,
        status=status,
        partial=partial,
        sync_summary=sync_summary,
        dataset_path=dataset_path,
        meta_path=meta_path,
        weekly_markdown_paths=weekly_markdown_paths,
        quarter_markdown_path=quarter_markdown_path,
    )


