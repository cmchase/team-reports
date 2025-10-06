# Team Reports

A comprehensive suite of tools for generating automated team summaries and performance reports from multiple data sources including Jira tickets and GitHub repositories. Create weekly, quarterly, and annual reports with rich analytics, contributor insights, and development metrics.

## 🎯 Features

### 📊 Multiple Report Types
- **📅 Weekly Jira Reports** - Generate weekly team summaries from Jira tickets
- **🐙 Weekly GitHub Reports** - Sprint-focused GitHub repository activity and contributor insights
- **📆 Quarterly Jira Reports** - Long-term analysis with contributor performance metrics  
- **📈 GitHub Quarterly Reports** - Comprehensive GitHub repository analysis and contributor tracking
- **🔄 Cross-Platform Insights** - Combine Jira and GitHub data for complete development visibility

### 🚀 Advanced Capabilities
- **🏷️ Smart Categorization** - Automatically categorize tickets by components, projects, and keywords
- **📅 Flexible Date Ranges** - Generate reports for any date range (weekly, quarterly, custom)
- **📝 Rich Markdown Output** - Clean, formatted reports with tables, links, and visual indicators
- **⚙️ Modular Configuration** - YAML-based configuration for each report type
- **🔍 Advanced Filtering** - Configurable status filters and assignee filtering
- **📁 Organized Output** - Reports saved in dedicated Reports folder with consistent naming
- **🔗 Multi-Platform Integration** - Built-in Jira and GitHub API integration
- **🛠️ Modular Architecture** - Reusable utilities package for easy extensibility

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- **For Jira Reports**: Jira account with API access and API token
- **For GitHub Reports**: GitHub account with Personal Access Token
- **For Both**: Virtual environment recommended

### Setup Steps

1. **Install Dependencies** - Set up Python environment and install packages
2. **Configure Credentials** - Set up API access for Jira and/or GitHub
3. **Configure Report Settings** - Customize configurations for each report type
4. **Generate Reports** - Start creating automated summaries

## 📊 Report Types Overview

| Report Type | Source | Frequency | Output | Use Case |
|-------------|--------|-----------|--------|----------|
| **Weekly Jira** | Jira API | Weekly | `team_summary_YYYY-MM-DD_to_YYYY-MM-DD.md` | Sprint reviews, weekly standup prep |
| **Weekly GitHub** | GitHub API | Weekly | `github_weekly_summary_YYYY-MM-DD_to_YYYY-MM-DD.md` | Sprint demos, code review insights |
| **Quarterly Jira** | Jira API | Quarterly | `quarterly_summary_QX_YYYY.md` | Performance reviews, quarterly planning |
| **GitHub Quarterly** | GitHub API | Quarterly | `github_quarterly_summary_QX_YYYY.md` | Code contribution analysis, developer insights |

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Configure Credentials

Create a `.env` file with your API credentials:

```bash
# Copy template and edit
cp env.template .env
```

**For Jira Reports** - Add your Jira credentials to `.env`:
```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

**For GitHub Reports** - Add your GitHub token to `.env`:
```bash
GITHUB_TOKEN=your-github-personal-access-token
```

**Getting API Tokens:**
- **Jira**: Account Settings → Security → API tokens → Create token
- **GitHub**: Settings → Developer settings → Personal access tokens → Generate new token
  - Required scopes: `repo` (for private repos) or `public_repo` (for public repos)

### 3. Configure Report Settings

**For Jira Reports:**
```bash
cp team_config_example.yaml team_config.yaml
# Edit team_config.yaml with your team's projects, members, and categorization rules
```

**For GitHub Reports:**
```bash  
cp github_config_example.yaml github_config.yaml
# Edit github_config.yaml with your repositories and team member mapping
```

### 4. Generate Your First Reports

#### 📅 Weekly Jira Reports
```bash
# Generate report for last 7 days
./run_jira_weekly_summary.sh

# Generate report for specific date range  
./run_jira_weekly_summary.sh 2025-09-10 2025-09-16
```

#### 🐙 Weekly GitHub Reports
```bash
# Generate report for current week
./run_github_weekly_summary.sh

# Generate report for specific date range
./run_github_weekly_summary.sh 2025-09-10 2025-09-16
```

#### 📆 Quarterly Jira Reports
```bash
# Generate report for current quarter
./run_jira_quarterly_summary.sh

# Generate report for specific quarter
./run_jira_quarterly_summary.sh 2025 4
```

#### 🐙 GitHub Quarterly Reports
```bash
# Generate report for current quarter
./run_github_quarterly_summary.sh

# Generate report for specific quarter
./run_github_quarterly_summary.sh 2025 4
```

## 📁 Project Structure

```
team-reports/
├── 📊 Core Report Generators
│   ├── jira_weekly_summary.py           # Weekly Jira reports  
│   ├── github_weekly_summary.py         # Weekly GitHub reports
│   ├── jira_quarterly_summary.py        # Quarterly Jira reports
│   └── github_quarterly_summary.py      # GitHub quarterly reports
├── 🚀 Execution Scripts  
│   ├── run_jira_weekly_summary.sh       # Weekly Jira report runner
│   ├── run_github_weekly_summary.sh     # Weekly GitHub report runner
│   ├── run_jira_quarterly_summary.sh    # Quarterly Jira report runner
│   └── run_github_quarterly_summary.sh  # GitHub quarterly report runner
├── ⚙️ Configuration
│   ├── env.template                     # Environment template
│   ├── team_config_example.yaml        # Jira configuration example
│   ├── github_config_example.yaml      # GitHub configuration example
│   ├── team_config.yaml               # Your Jira config (create this)
│   ├── github_config.yaml             # Your GitHub config (create this)  
│   └── .env                           # API credentials (create this)
├── 🛠️ Utilities Package
│   └── utils/
│       ├── __init__.py                 # Package initialization
│       ├── jira.py                    # Jira API utilities
│       ├── config.py                  # Configuration management
│       ├── date.py                    # Date parsing and ranges
│       ├── report.py                  # Report formatting and output
│       └── ticket.py                  # Ticket categorization
├── 📄 Documentation
│   ├── README.md                      # This file
│   ├── WEEKLY_SUMMARY_README.md       # Weekly reports guide
│   ├── GITHUB_QUARTERLY_README.md     # GitHub reports guide
│   ├── CONFIGURATION_GUIDE.md         # Configuration reference
│   └── DEVELOPER_GUIDE.md            # Development guide
├── 📁 Output
│   └── Reports/                       # Generated reports (auto-created)
│       ├── jira_weekly_summary_*.md   # Weekly Jira reports
│       ├── github_weekly_summary_*.md # Weekly GitHub reports
│       ├── jira_quarterly_summary_*.md # Quarterly Jira reports
│       └── github_quarterly_*.md      # GitHub quarterly reports
├── 🔧 Dependencies
│   ├── requirements.txt               # Python package dependencies
│   └── venv/                         # Virtual environment (create this)
└── 📜 Project Files
    ├── LICENSE                       # MIT license
    └── .gitignore                   # Git ignore rules
```

## 🔗 Dependencies & Integrations

### API Integrations
- **Jira API Integration** (`utils/jira.py`)
  - Direct Jira API integration using the `jira` Python library
  - Handles authentication, pagination, and API communication  
  - JQL query building and ticket fetching utilities
  - No external dependencies or separate server processes required

- **GitHub API Integration** (`github_quarterly_summary.py`)
  - Native GitHub REST API integration using `requests`
  - Supports pull requests, commits, and issues tracking
  - Rate limiting and pagination handling
  - Organization and repository analysis

### Python Dependencies (requirements.txt)
```python
jira>=3.10.5          # Jira API client
requests>=2.31.0      # HTTP requests for GitHub API  
python-dotenv>=1.1.1  # Environment variable management
pyyaml>=6.0.3         # YAML configuration parsing
```

### Modular Architecture
- **Utilities Package** (`utils/`) - Reusable components across all report types
  - Configuration management and validation
  - Date parsing and range calculations  
  - Report formatting and output handling
  - Ticket categorization and analysis
  - Shared authentication and API utilities

## 🎯 Usage Examples

### 📅 Weekly Jira Reports

**Shell Script (Recommended):**
```bash
# Generate report for last 7 days
./run_jira_weekly_summary.sh

# Generate report for specific date range  
./run_jira_weekly_summary.sh 2025-09-10 2025-09-16

# Generate report for current week
./run_jira_weekly_summary.sh $(date -d "monday" +%Y-%m-%d) $(date -d "sunday" +%Y-%m-%d)
```

**Python Direct:**
```bash
# Basic usage
python3 jira_weekly_summary.py

# Specific date range
python3 jira_weekly_summary.py 2025-09-10 2025-09-16

# Custom configuration
python3 jira_weekly_summary.py 2025-09-10 2025-09-16 custom_team_config.yaml
```

### 🐙 Weekly GitHub Reports

**Shell Script (Recommended):**
```bash
# Generate report for current week
./run_github_weekly_summary.sh

# Generate report for specific date range
./run_github_weekly_summary.sh 2025-09-10 2025-09-16

# Custom configuration
./run_github_weekly_summary.sh 2025-09-10 2025-09-16 custom_github_config.yaml
```

**Python Direct:**
```bash
# Current week
python3 github_weekly_summary.py

# Specific date range
python3 github_weekly_summary.py 2025-09-10 2025-09-16

# With custom config
python3 github_weekly_summary.py 2025-09-10 2025-09-16 custom_config.yaml
```

### 📆 Quarterly Jira Reports

**Shell Script (Recommended):**
```bash
# Current quarter
./run_jira_quarterly_summary.sh

# Specific quarter (Q4 2025)
./run_jira_quarterly_summary.sh 2025 4

# Custom configuration  
./run_jira_quarterly_summary.sh 2025 4 custom_team_config.yaml
```

**Python Direct:**
```bash
# Current quarter
python3 jira_quarterly_summary.py

# Specific quarter
python3 jira_quarterly_summary.py 2025 4

# With custom config
python3 jira_quarterly_summary.py 2025 4 custom_config.yaml
```

### 🐙 GitHub Quarterly Reports

**Shell Script (Recommended):**
```bash
# Current quarter
./run_github_quarterly_summary.sh

# Specific quarter (Q4 2025)
./run_github_quarterly_summary.sh 2025 4

# Custom configuration
./run_github_quarterly_summary.sh 2025 4 custom_github_config.yaml
```

**Python Direct:**
```bash
# Current quarter
python3 github_quarterly_summary.py

# Specific quarter
python3 github_quarterly_summary.py 2025 4

# With custom config  
python3 github_quarterly_summary.py 2025 4 custom_config.yaml
```

### 🔄 Batch Report Generation

**Generate all reports for current period:**
```bash
# All weekly reports (Jira + GitHub)
./run_jira_weekly_summary.sh
./run_github_weekly_summary.sh

# All quarterly reports (Jira + GitHub)
./run_jira_quarterly_summary.sh  
./run_github_quarterly_summary.sh

# Complete reporting suite
./run_jira_weekly_summary.sh && ./run_github_weekly_summary.sh && ./run_jira_quarterly_summary.sh && ./run_github_quarterly_summary.sh
```

## 📊 Report Output

All reports are generated in clean Markdown format with rich formatting, tables, and links.

### 📅 Weekly Jira Reports

**Features:**
- **📅 Date Range** - Clear indication of the reporting period  
- **📈 Summary Statistics** - Total tickets and category breakdown
- **🏷️ Categorized Sections** - Tickets organized by your defined categories
- **📋 Ticket Details** - Key, summary, status, assignee, priority, and URL
- **📊 Status Breakdown** - Tickets grouped by status with counts

**Example Output:**
```markdown
# 📊 WEEKLY TEAM SUMMARY: 2025-09-10 to 2025-09-16

## 📈 OVERVIEW
- **Total Tickets:** 110  
- **Backend Development:** 53 tickets
- **Frontend Development:** 32 tickets
- **QE / Testing:** 20 tickets

### 🎯 BACKEND DEVELOPMENT - API, Services

#### 📌 In Progress (5 tickets)
| Ticket ID | Assignee | Priority | Updated | Title |
|-----------|----------|----------|---------|-------|
| [PROJ-123](url) | John Doe | Major | 2025-09-13 | Implement new API endpoint |
```

### 🐙 Weekly GitHub Reports

**Features:**
- **🔄 Pull Request Activity** - Recent PRs with code change metrics
- **💻 Commit Tracking** - Individual contributor commit activity
- **🐛 Issue Updates** - Issues created, updated, and closed during the week
- **📊 Daily Activity Patterns** - Day-by-day breakdown of development activity
- **🏆 Top Contributors** - Weekly recognition with contribution metrics
- **📁 Repository Breakdown** - Activity across multiple repositories

**Example Output:**
```markdown
# 🐙 WEEKLY GITHUB SUMMARY: 2025-10-07 to 2025-10-13

### 📊 WEEKLY GITHUB ACTIVITY OVERVIEW
- **Total Pull Requests:** 23
- **Total Commits:** 67
- **Total Issues Updated:** 12
- **Lines Added:** +2,847
- **Lines Removed:** -1,234
- **Active Contributors:** 8

#### 🏆 Top Contributors This Week
**1. Jane Smith** - 8 PRs, 19 commits, +847/-203 lines
**2. John Doe** - 5 PRs, 15 commits, +623/-98 lines

## 👥 INDIVIDUAL CONTRIBUTOR DETAILS
### 👤 Jane Smith
- **Pull Requests:** 8
- **Commits:** 19
- **Code Changes:** +847/-203 lines

#### 🔄 Pull Requests This Week
| Repository | PR | State | Lines | Title |
|------------|----|---------|----- |-------|
| api-service | [#156](url) | merged | +234/-67 | Add user authentication endpoint |
```

### 📆 Quarterly Jira Reports

**Features:**
- **👥 Individual Contributor Analysis** - Detailed performance per team member
- **📊 Story Point Tracking** - Completion metrics and productivity analysis
- **📈 Trend Analysis** - Quarter-over-quarter performance insights
- **🏆 Top Contributors** - Recognition of high-performing team members
- **📋 Comprehensive Ticket Lists** - All tickets with detailed categorization

**Example Output:**
```markdown
# 📆 QUARTERLY TEAM SUMMARY: Q4 2025

## 📈 EXECUTIVE SUMMARY  
- **Total Tickets Completed:** 342
- **Total Story Points:** 1,247
- **Top Contributor:** Jane Smith (89 tickets, 276 story points)
- **Most Active Category:** Backend Development (156 tickets)

## 👥 INDIVIDUAL CONTRIBUTOR PERFORMANCE
### 🏆 Jane Smith
- **Tickets Completed:** 89 tickets
- **Story Points:** 276 points  
- **Average per Month:** 29.7 tickets, 92 story points
```

### 🐙 GitHub Quarterly Reports  

**Features:**
- **🔄 Pull Request Analysis** - Contribution tracking across repositories
- **💻 Code Metrics** - Lines added/removed, files changed
- **📊 Repository Activity** - Cross-repo contribution analysis
- **👥 Contributor Insights** - Individual and team performance metrics
- **📈 Monthly Trends** - Activity patterns over the quarter

**Example Output:**
```markdown
# 🐙 GITHUB QUARTERLY REPORT: Q4 2025

## 📈 QUARTER OVERVIEW
- **Total Contributors:** 12
- **Total Pull Requests:** 156  
- **Total Commits:** 423
- **Lines Added:** +12,847
- **Lines Removed:** -8,234

## 🏆 TOP CONTRIBUTORS  
| Contributor | PRs | Commits | Lines + | Lines - |
|-------------|-----|---------|---------|---------|
| Jane Smith | 34 | 89 | +3,421 | -1,876 |
```

### 📁 Output Organization

All reports are saved in the `Reports/` directory with consistent naming:
- **Weekly Jira**: `jira_weekly_summary_2025-09-10_to_2025-09-16.md`
- **Weekly GitHub**: `github_weekly_summary_2025-09-10_to_2025-09-16.md`
- **Quarterly Jira**: `jira_quarterly_summary_Q4_2025.md`  
- **GitHub Quarterly**: `github_quarterly_summary_Q4_2025.md`

## ⚙️ Configuration

### Jira Configuration (`team_config.yaml`)

**For Weekly & Quarterly Jira Reports**

```yaml
# Base JQL filter for your team
base_jql: |
  project = PROJ AND assignee in ("user1@company.com", "user2@company.com")

# Team categorization rules
team_categories:
  Backend Development:
    components: ["Backend", "API"]
    keywords: ["database", "service"]  
    description: "Backend services and API development"

  Frontend Development:
    components: ["Frontend", "UI"]
    keywords: ["react", "typescript"]
    description: "Frontend and user interface work"

  Quality Engineering:
    components: ["QE", "Testing"]
    projects: ["TESTS"]
    description: "Quality engineering and testing"

# Team member mapping (email to display name)
team_members:
  "user1@company.com": "John Developer"
  "user2@company.com": "Jane Engineer"
  "qa@company.com": "Bob Tester"

# Status filters for different report types
status_filters:
  all:
    - "New"
    - "Refinement" 
    - "To Do"
    - "In Progress"
    - "Review"
    - "Closed"
  completed:
    - "Closed"
  execution:
    - "In Progress"
    - "Review"

# Report settings
report_settings:
  max_results: 200
  order_by: "component ASC, updated DESC"
  default_status_filter: "completed"
```

### GitHub Configuration (`github_config.yaml`)

**For GitHub Quarterly Reports**

```yaml
# GitHub organization (optional)
github_org: "your-organization"

# Repositories to analyze 
repositories:
  - "repo1"
  - "repo2"
  - "repo3"

# Team member mapping (GitHub username → Display name)
team_members:
  "github_username1": "John Developer"
  "github_username2": "Jane Engineer" 
  "octocat": "GitHub Mascot"

# Report settings
report_settings:
  max_results: 100
  include_private: true
  track_pull_requests: true
  track_commits: true
  track_issues: true

# Repository filters
repository_filters:
  exclude_archived: true
  exclude_forks: true
  only_active_repos: true

# Contributor filters  
contributor_filters:
  exclude_bots: true
  bot_patterns:
    - "bot"
    - "dependabot"
    - "renovate"
  min_contributions: 1
```

### Environment Variables (`.env`)

**API Credentials for all reports**

```bash
# Jira API credentials (for Jira reports)
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# GitHub API credentials (for GitHub reports)  
GITHUB_TOKEN=your-github-personal-access-token
```

## 🔧 Customization

### Adding New Jira Categories

1. **Edit `team_config.yaml`**
2. **Add new category** under `team_categories`
3. **Define matching rules** (components, projects, keywords)
4. **Regenerate reports** to see new categorization

```yaml
team_categories:
  DevOps:
    keywords: ["deployment", "infrastructure", "kubernetes"]
    description: "DevOps and infrastructure work"
  
  Security:
    keywords: ["security", "vulnerability", "audit"] 
    description: "Security-related work and vulnerability fixes"
```

### Configuring Status Filters

**Multiple filter types for different use cases:**

```yaml
status_filters:
  # Show all tickets regardless of status
  all: ["New", "To Do", "In Progress", "Review", "Closed"]
  
  # Show only completed work  
  completed: ["Closed"]
  
  # Show work in active execution
  execution: ["In Progress", "Review"]
  
  # Custom filter
  my_filter: ["To Do", "In Progress"]
```

### Adding GitHub Repositories

1. **Edit `github_config.yaml`**
2. **Add repositories** to the list
3. **Map contributors** in `team_members` section
4. **Regenerate reports** to include new repos

```yaml
repositories:
  - "new-repo"
  - "another-project"
  
team_members:
  "new_github_user": "New Team Member"
```

### Extending with Utils Package

**The modular utilities package allows easy extension:**

```python
# Custom report using existing utilities
from utils.jira import fetch_tickets_for_date_range
from utils.config import load_config  
from utils.report import save_report

# Build custom analysis with reusable components
config = load_config('my_config.yaml')
tickets = fetch_tickets_for_date_range(start_date, end_date, config)
# ... custom analysis logic ...
save_report(content, filename)
```

## 📖 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|  
| **[WEEKLY_SUMMARY_README.md](WEEKLY_SUMMARY_README.md)** | Detailed weekly reports guide | End users |
| **[GITHUB_QUARTERLY_README.md](GITHUB_QUARTERLY_README.md)** | GitHub reports comprehensive guide | End users |
| **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** | Advanced configuration options | Power users |
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | Implementation and extension guide | Developers |

## 🔒 Security

### 🔐 Credential Management
- **Never commit `.env` file** - Contains sensitive API tokens and credentials
- **Never commit configuration files with real data**:
  - `team_config.yaml` - Contains team-specific Jira information
  - `github_config.yaml` - Contains GitHub repository and team data
- **Use example files as templates** - Copy from `*_example.yaml` files
- **Store credentials securely** - Use `.env` file for all API tokens

### 🛡️ API Token Security  
- **Use API tokens instead of passwords** for both Jira and GitHub
- **Rotate tokens regularly** for enhanced security
- **Minimum required permissions**:
  - **Jira**: Read access to projects and issues
  - **GitHub**: `repo` scope for private repositories, `public_repo` for public only
- **Monitor token usage** through provider dashboards

### 📁 File Security
**Files properly ignored in `.gitignore`:**
```
.env                    # API credentials
team_config.yaml        # Team-specific Jira config  
github_config.yaml      # GitHub repositories and team mapping
Reports/                # Generated reports (may contain sensitive data)
```

**Safe to commit:**
```
*_example.yaml          # Template configuration files
env.template           # Environment variable template
run_*.sh               # Execution scripts
*.py                   # Source code
```

## 🐛 Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Ensure `.env` file exists with correct Jira credentials
   - Check that `JIRA_SERVER`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` are set
   - Verify the `.env` file is in the same directory as `jira_weekly_summary.py`

2. **Authentication Error**
   - Check your API token is correct
   - Ensure your email matches your Jira account
   - Verify token hasn't expired
   - Test your Jira credentials by logging into Jira directly

3. **No Tickets Found**
   - Check your JQL filter in `team_config.yaml`
   - Verify date range is correct
   - Ensure you have access to the projects
   - Test the JQL query directly in Jira

4. **Configuration Error**
   - Validate YAML syntax in `team_config.yaml`
   - Check file permissions
   - Ensure all required fields are present

5. **Import Errors**
   - Ensure all scripts are in the same directory for proper imports
   - Check that all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python version is 3.8 or higher

### Debug Mode

Enable debug logging by modifying the logging level in `jira_weekly_summary.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 🆕 Recent Updates

### 🚀 Major New Features

- **✅ GitHub Weekly Reports** - Sprint-focused GitHub repository analysis system
  - Weekly pull request, commit, and issue activity tracking  
  - Daily activity patterns and contributor insights for sprint reviews
  - Code contribution metrics with lines added/removed tracking
  - Perfect complement to weekly Jira reports for complete sprint visibility

- **✅ GitHub Quarterly Reports** - Complete GitHub repository analysis system
  - Pull request, commit, and issue tracking across multiple repositories
  - Contributor performance analysis with code change metrics
  - Repository activity breakdown and cross-repo insights
  - Team member mapping from GitHub usernames to display names
  
- **✅ Quarterly Jira Analysis** - Long-term team performance reporting
  - Individual contributor performance tracking with story point analysis
  - Quarterly trend analysis and productivity metrics
  - Executive summary with key insights and top contributor recognition
  - Comprehensive ticket categorization and completion tracking

- **✅ Modular Utilities Architecture** - Reusable component system
  - Organized `utils/` package with specialized modules
  - Shared configuration management and validation
  - Common date parsing and report formatting utilities
  - Extensible architecture for custom report development

### 🛠️ Technical Improvements

- **✅ Multi-Platform Integration** - Unified credential management for Jira and GitHub APIs
- **✅ Enhanced Configuration** - Separate config files for different report types
- **✅ Shell Script Automation** - Convenient execution scripts with error handling
- **✅ Rich Report Output** - Enhanced Markdown formatting with tables and visual indicators
- **✅ Improved Data Handling** - Robust API pagination and rate limiting
- **✅ Comprehensive Documentation** - Detailed guides for each report type

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🗺️ Roadmap & Future Enhancements

### 🔮 Planned Features

Perfect — here’s a **single, polished Markdown roadmap** ready to drop into your repo (e.g., as `ROADMAP.md` or appended to your README).

It merges your existing roadmap with the new data-driven and coaching features, grouped into clear, concise phases while maintaining your professional tone and consistent formatting.

---

# 🗺️ Project Roadmap

This roadmap outlines the planned evolution of **Team Reports** — expanding from automated summaries to deeper insights that support team productivity, flow, and growth.
All new features maintain the same **Markdown-only**, **configuration-driven**, and **API-integrated** design philosophy.

---

## 🚀 Phase 1 — Current Capabilities (✅ Implemented)

* **Individual Reports**

  * Weekly and quarterly **Jira** reports for team performance and activity.
  * Weekly and quarterly **GitHub** reports for repository and contributor insights.
* **Multi-Platform Integration**

  * Separate Jira and GitHub data sources with shared configuration and credentials.
* **Smart Categorization & Filters**

  * Component-, project-, and keyword-based ticket grouping.
  * Flexible date ranges and customizable status filters.
* **Rich Markdown Output**

  * Structured reports with tables, highlights, and contributor summaries.
* **Automation**

  * Shell script execution for fast report generation.
* **Extensible Architecture**

  * Modular utilities for configuration, date handling, and API access.

---

## 🔥 Phase 2 — Data-Driven Metrics (In Progress)

### Flow Metrics (Jira)

* **Cycle Time** – Time from “In Progress” → “Done” with team median and p90 values.
* **Work In Progress (WIP)** – Current active tickets per engineer and team total.
* **Blocked Time** – Total time spent in Blocked or equivalent states.

### Delivery Metrics (GitHub)

* **PR Lead Time** – Duration from first commit → merge, with filtering for trivial PRs.
* **Review Depth** – Reviewers per PR, number of comments, and review-to-author mapping (bot exclusion supported).

### Data Quality & Guardrails

* Identify missing transition histories, unlinked PR↔Issue relationships, and API fetch gaps.
* Add **Pass/Warn/Fail badges** and optional `fail_on_error` flag.

### Configuration Centralization

* Add feature flags for each metric (e.g., `metrics.flow.cycle_time`).
* Centralize thresholds, active states, and bot filters in YAML configuration.
* Display an active config hash in report footers for traceability.

---

## 📈 Phase 3 — Insights & Coaching (Planned)

### Growth & Coaching Signals

Derived indicators to support performance coaching and 1:1 conversations:

* **Autonomy** – % of Jira tickets opened by the assignee.
* **Collaboration** – Reviews given vs. received per engineer.
* **Quality Focus** – % of PRs adding tests or documentation.
* **Rework Ratio** – % of commits editing files modified in the last 14 days.
* Reports only surface **noteworthy deviations** (beyond ±1 std. dev.) to reduce noise.

### Correlation & Analysis

* **PR Size vs. Cycle Time** – Compute correlation (Pearson r).
* Output a short interpretive insight line and simple ASCII scatter bins.
* Enable CSV export for further visualization.

### Gentle Nudges

* Light “nudge” alerts in weekly reports:

  * PRs waiting for review >48h.
  * Engineers with 0 merged PRs or 0 closed tickets in 10 days.
  * Consistent WIP over limit for 5+ days.
* Include JSON export (`nudges.json`) for optional Slack or dashboard integration.

---

## 📊 Phase 4 — Longitudinal Insights (Upcoming)

* **Quarterly Trendlines** – ASCII mini-sparklines showing week-over-week trends for:

  * Cycle Time
  * PR Lead Time
  * Review Depth
  * Rework Ratio
* **CSV Artifact Exports** – Output minimal datasets for dashboards:

  * `flow_cycle_time.csv`
  * `delivery_prs.csv`
  * `coaching_signals.csv`
* **Unified Combined Reports (Optional)** – Create a single weekly file merging Jira + GitHub summaries with aligned time ranges.

---

## 🧪 Phase 5 — Quality & Scalability (Future)

* **Testing Coverage** – Raise test coverage for new modules to ≥85%. (Optional)
* **Fixtures & Stability** – Add deterministic fixtures for Jira/GitHub APIs and date ranges.
* **Report Polish**

  * Normalize all Markdown table formats.
  * Add a concise **Glossary** section with metric definitions.
  * Use inline footnotes (†) linking metrics to glossary anchors.
* **Change Tracking**

  * Maintain short, imperative changelog entries.
  * Version report schema changes clearly in output headers.

---

## 💡 Phase 6 — Stretch Goals (Exploratory)

* **Jira↔GitHub Auto-Linking**

  * Match PRs and commits to Jira tickets by key in branch names, titles, or commit messages.
* **Scheduled Reporting**

  * Lightweight cron-based automation for weekly and quarterly report generation.
* **Slack / Teams Integration**

  * Post summarized Markdown sections directly into team channels.
* **Dashboard Layer**

  * Optional static-site dashboard rendering CSV data into trend charts.
* **Multi-Team Support**

  * Generate reports for multiple teams from a single configuration file.

---

## 🧭 Implementation Strategy

Each new capability will be developed as **incremental, self-contained commits**:

1. Implement metric or feature.
2. Add config flag and documentation.
3. Extend Markdown output and glossary.
4. Update tests and changelog.

---

## ✅ Priority Summary

| Category                            | Focus                                 | Priority  |
| ----------------------------------- | ------------------------------------- | --------- |
| **Unified Reports (Jira+GitHub)**   | Cross-platform correlation            | 🔥 High   |
| **Flow & Delivery Metrics**         | Jira/GitHub performance indicators    | 🔥 High   |
| **Coaching Signals**                | Growth-oriented insights              | 🔥 High   |
| **Trend Analysis & CSV Exports**    | Historical and external visualization | 🔧 Medium |
| **Slack/Dashboard Integrations**    | Quality-of-life enhancements          | 💡 Future |
| **Scheduling & Multi-Team Support** | Scalability improvements              | 💡 Future |

---

### ✨ Goal

Empower engineering leaders and teams to **see their progress, friction, and growth patterns**—all through a simple, private, Markdown-based reporting suite that turns Jira and GitHub data into meaningful, actionable insight.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Success!

Your comprehensive Team Reports suite is now ready to use! You can:

### 📊 Multi-Platform Reporting
- ✅ **Generate weekly Jira summaries** for sprint reviews and team standups
- ✅ **Create weekly GitHub reports** for code contribution and sprint demo insights  
- ✅ **Produce quarterly Jira analysis** for performance reviews and planning
- ✅ **Generate GitHub quarterly reports** for long-term code contribution analysis
- ✅ **Generate complementary reports** from both Jira tickets and GitHub contributions for the same time periods

### 🚀 Advanced Capabilities  
- ✅ **Smart ticket categorization** with customizable rules and filters
- ✅ **Individual contributor tracking** with detailed performance metrics
- ✅ **Cross-repository analysis** for complete development visibility  
- ✅ **Rich Markdown output** with tables, links, and visual indicators
- ✅ **Automated execution** via convenient shell scripts
- ✅ **Extensible architecture** using modular utilities package
- ✅ **Time-aligned reporting** enabling side-by-side analysis of Jira and GitHub activities

### 🛠️ Enterprise Ready
- ✅ **Secure credential management** with environment variables
- ✅ **Comprehensive configuration** for different team structures
- ✅ **Robust error handling** and API rate limiting
- ✅ **Detailed documentation** for users and developers
- ✅ **Scalable design** for teams of any size

**Start generating reports and transform your team's development data into actionable insights!** 🚀

Choose your report type:
- `./run_jira_weekly_summary.sh` for Jira sprint insights
- `./run_github_weekly_summary.sh` for GitHub sprint insights
- `./run_jira_quarterly_summary.sh` for Jira performance analysis  
- `./run_github_quarterly_summary.sh` for GitHub contribution tracking