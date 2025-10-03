# GitHub Quarterly Reports

Generate comprehensive quarterly reports from GitHub repositories, tracking contributor activity, code contributions, and development metrics.

## 🚀 Quick Start

### 1. Setup Environment

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure GitHub Access**:
   - Copy `env.template` to `.env`
   - Add your GitHub Personal Access Token to `.env`:
     ```
     GITHUB_TOKEN=your_github_personal_access_token_here
     ```

3. **Configure Repositories**:
   - Copy `github_config_example.yaml` to `github_config.yaml`
   - Edit the configuration with your repositories and team members

### 2. Generate Reports

#### Using the Shell Script (Recommended)
```bash
# Generate report for current quarter
./run_github_quarterly_summary.sh

# Generate report for specific quarter
./run_github_quarterly_summary.sh 2025 4

# Use custom configuration
./run_github_quarterly_summary.sh 2025 4 custom_github_config.yaml
```

#### Using Python Directly
```bash
# Current quarter
python github_quarterly_summary.py

# Specific quarter (Q4 2025)
python github_quarterly_summary.py 2025 4

# Custom config
python github_quarterly_summary.py 2025 4 custom_github_config.yaml
```

## 📊 What's Included

### Repository Metrics
- **Pull Requests**: Created, merged, closed PRs with status tracking
- **Commits**: All commits with author attribution and timestamps
- **Issues**: Opened and closed issues (excluding PRs)
- **Code Changes**: Lines added/removed per contributor
- **Repository Activity**: Cross-repository contribution patterns

### Contributor Analysis
- **Individual Performance**: Detailed per-contributor breakdowns
- **Activity Rankings**: Top contributors by various metrics
- **Code Impact**: Lines of code contributed across repositories
- **Time-based Trends**: Monthly activity patterns
- **Repository Contributions**: Which repos each contributor worked on

### Report Sections
1. **Quarterly Overview**: High-level metrics and top contributors
2. **Repository Activity**: Activity breakdown by repository
3. **Individual Contributor Details**: Comprehensive per-person analysis
4. **Recent Activity Tables**: Latest PRs, commits, and issues

## ⚙️ Configuration

### Basic Configuration (`github_config.yaml`)

```yaml
# GitHub Organization (optional)
github_org: "your-organization"

# Repositories to analyze
repositories:
  - "repo1"
  - "repo2"
  - "repo3"

# Team member mapping (GitHub username -> Display name)
team_members:
  "github_username": "Display Name"
  "octocat": "GitHub Mascot"

# Report settings
report_settings:
  max_results: 100
  include_private: true
  track_pull_requests: true
  track_commits: true
  track_issues: true
```

### GitHub Authentication

You need a GitHub Personal Access Token with appropriate permissions:

1. **Go to GitHub Settings**:
   - Settings → Developer settings → Personal access tokens

2. **Generate New Token** with these scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories)
   - `read:org` (for organization information)

3. **Add to `.env` file**:
   ```
   GITHUB_TOKEN=ghp_your_token_here
   ```

## 📁 Output Structure

Reports are saved to the `Reports/` directory with names like:
```
Reports/github_quarterly_summary_Q4_2025.md
```

### Sample Report Structure

```markdown
## 📊 QUARTERLY GITHUB CONTRIBUTOR REPORT: Q4 2025

### 📊 Q4 2025 GITHUB CONTRIBUTOR OVERVIEW
- **Total Pull Requests:** 45
- **Total Commits:** 312
- **Total Issues:** 23
- **Lines Added:** 15,432
- **Lines Removed:** 8,901
- **Active Contributors:** 8

#### 🏆 Top Contributors by Pull Requests
1. **John Doe:** 12 PRs (26.7%) • 89 commits • 5 issues • +3,456 lines
2. **Jane Smith:** 10 PRs (22.2%) • 67 commits • 8 issues • +2,890 lines

## 👥 INDIVIDUAL CONTRIBUTOR DETAILS

### 👤 John Doe
- **Total Pull Requests:** 12
- **Total Commits:** 89
- **Total Issues:** 5
- **Lines Added:** 3,456
- **Lines Removed:** 1,234

#### 🔄 Recent Pull Requests
| Repository | PR | State | Title |
|------------|-------|-------|-------|
| repo1 | [#123](url) | ✅ merged | Add new feature for data processing |
```

## 🔧 Advanced Features

### Repository Filters
- Exclude archived repositories
- Exclude forked repositories
- Filter by activity level

### Contributor Filters
- Exclude bot accounts
- Set minimum contribution thresholds
- Custom bot pattern matching

### Report Customization
- Custom report titles
- Include/exclude specific metrics
- Adjust contributor ranking criteria

## 🆚 Comparison with Jira Reports

| Feature | Jira Reports | GitHub Reports |
|---------|--------------|----------------|
| **Data Source** | Jira tickets & story points | GitHub PRs, commits, issues |
| **Metrics** | Tickets completed, story points | Code contributions, PR activity |
| **Time Tracking** | Issue updates, status changes | Commit dates, PR merges |
| **Contributor Focus** | Ticket assignment & completion | Code authorship & reviews |
| **Work Complexity** | Story points | Lines of code changed |

## 🚨 Troubleshooting

### Common Issues

1. **GitHub API Rate Limits**:
   - GitHub allows 5,000 requests/hour for authenticated users
   - The tool handles pagination and rate limiting automatically
   - Large organizations may need to run reports during off-peak hours

2. **Authentication Errors**:
   - Verify `GITHUB_TOKEN` in `.env` file
   - Check token permissions (repo, read:org)
   - Ensure token hasn't expired

3. **Repository Access**:
   - Private repos require `repo` scope
   - Organization repos may need additional permissions
   - Check repository names in configuration

4. **No Data Found**:
   - Verify repository names are correct
   - Check date ranges (quarters may not have activity)
   - Ensure repositories have commits/PRs in the specified period

### Debug Mode

Set environment variable for verbose logging:
```bash
export GITHUB_DEBUG=1
python github_quarterly_summary.py
```

## 📈 Use Cases

### Development Team Management
- Track individual developer productivity
- Identify code review patterns
- Monitor repository activity trends
- Plan resource allocation

### Open Source Projects
- Recognize top contributors
- Track community engagement
- Analyze project growth patterns
- Generate contributor reports for funding

### Enterprise Development
- Cross-team collaboration analysis
- Code quality and review metrics
- Development velocity tracking
- Quarterly performance reviews

## 🤝 Integration with Existing Workflow

The GitHub quarterly reports complement your existing Jira reports:

1. **Combined Analysis**: Run both Jira and GitHub reports for the same quarter
2. **Cross-Reference**: Compare story point completion with code contributions
3. **Holistic View**: Understand both planning (Jira) and execution (GitHub) metrics
4. **Team Performance**: Get complete picture of contributor productivity

## 📚 Additional Resources

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [Personal Access Token Guide](https://docs.github.com/en/authentication)
- [GitHub Organizations](https://docs.github.com/en/organizations)

---

*Generated quarterly reports provide insights into development activity and contributor performance across your GitHub repositories.*
