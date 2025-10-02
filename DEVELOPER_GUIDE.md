# Developer Guide - Jira Weekly Reports

> **Audience**: AI assistants, developers, and technical implementers  
> **Purpose**: Ensure correct report generation process and prevent common implementation errors

## 🚨 CRITICAL STEPS TO FOLLOW

### 1. ALWAYS Use Team Configuration First
- **NEVER** use generic date-only JQL queries
- **ALWAYS** read and use the `base_jql` from `team_config.yaml`
- **ALWAYS** combine team filter with date filter

### 2. Correct JQL Query Structure
```sql
(
    [base_jql from team_config.yaml]
) AND updated >= "YYYY-MM-DD" AND updated <= "YYYY-MM-DD" AND status NOT IN ("New", "Backlog", "Blocked") ORDER BY [order_by from config]
```

### 3. Step-by-Step Process

#### Step 1: Read Team Configuration
```bash
read_file team_config.yaml
```

#### Step 2: Extract base_jql
- Copy the `base_jql` section exactly
- Note the `status_filters.exclude` values
- Note the `report_settings.order_by` value

#### Step 3: Build Complete JQL
```sql
(
    project = PROJ AND Component in ("Backend", "Frontend", "API", "Testing", "Operations", "Compliance")
) OR (
    project in (PROJ, PROJ2, PROJ3, PROJ4) AND assignee in ("user@company.com")
) OR (
    project = PROJ AND "QA Contact" in ("user@company.com")
) AND updated >= "2024-09-16" AND updated <= "2024-09-24" AND status NOT IN ("New", "Backlog", "Blocked") ORDER BY component ASC, updated DESC
```

#### Step 4: Execute Search
```python
from jira import JIRA
jira_client = JIRA(server=server, token_auth=api_token)
issues = jira_client.search_issues(jql=complete_jql, maxResults=50)
```

#### Step 5: Get Issue Details
```python
issue = jira_client.issue(issue_key)
```

#### Step 6: Generate Report
- Use team categories from config
- Apply proper categorization logic
- Include team-specific insights

### 4. Common Mistakes to Avoid

❌ **WRONG**: `updated >= "2025-09-16" AND updated <= "2025-09-24"`
✅ **CORRECT**: Use team base_jql + date filter

❌ **WRONG**: Generic date-only queries
✅ **CORRECT**: Team-filtered queries

❌ **WRONG**: Using placeholder values in config
✅ **CORRECT**: Update config with real team details

❌ **WRONG**: Ignoring status filters
✅ **CORRECT**: Apply status exclusions from config

### 5. Configuration Requirements

#### team_config.yaml must have:
- Real project names (not "PROJ")
- Real team member emails (not "manager@company.com")
- Real components (not generic placeholders)
- Proper categorization rules

#### Example Real Configuration:
```yaml
base_jql: |
  (
      project = PROJ AND Component in ("Backend", "Frontend", "API", "Testing", "Operations", "Compliance")
  ) OR (
      project in (PROJ, PROJ2, PROJ3, PROJ4) AND assignee in ("user@company.com")
  ) OR (
      project = PROJ AND "QA Contact" in ("user@company.com")
  )
```

### 6. Validation Checklist

Before generating report:
- [ ] Read team_config.yaml
- [ ] Verify base_jql has real values (not placeholders)
- [ ] Build complete JQL with team filter + date filter
- [ ] Test JQL query returns reasonable results
- [ ] Use proper categorization from config
- [ ] Apply status filters from config

### 7. Report Quality Checks

After generating report:
- [ ] All issues are from correct team projects
- [ ] Date range is correct (not future dates)
- [ ] Categories match team configuration
- [ ] No generic placeholder data
- [ ] Team-specific insights included

## 🎯 Success Criteria

A proper weekly report should:
1. **Be team-specific**: Only include issues from your team's projects and members
2. **Use correct dates**: Not future dates or wrong years
3. **Apply proper filtering**: Use status filters and categorization from config
4. **Provide actionable insights**: Team-specific achievements and areas for improvement
5. **Be properly categorized**: Issues grouped according to team categories

## 📝 Example Commands

```bash
# 1. Read configuration
read_file team_config.yaml

# 2. Build and test JQL
python3 weekly_team_summary.py 2024-09-16 2024-09-24

# 3. Or use direct Jira API
from jira import JIRA
jira_client = JIRA(server=server, token_auth=api_token)
issues = jira_client.search_issues(jql="[team_base_jql] AND updated >= '2024-09-16' AND updated <= '2024-09-24'")

# 4. Generate report
python3 weekly_team_summary.py start_date end_date
```

---

**Remember**: Always use team configuration first, never generic queries!





