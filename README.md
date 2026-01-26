# Team Reports

A comprehensive suite of tools for generating automated team summaries and performance reports from multiple data sources including Jira tickets and GitHub repositories. Create weekly, quarterly, and annual reports with rich analytics, contributor insights, and development metrics.

## 🎯 Features

### 📊 Multiple Report Types
- **📅 Weekly Jira Reports** - Generate weekly team summaries from Jira tickets
- **🐙 Weekly GitHub Reports** - Sprint-focused GitHub repository activity and contributor insights
- **📆 Quarterly Jira Reports** - Long-term analysis with contributor performance metrics  
- **📈 GitHub Quarterly Reports** - Comprehensive GitHub repository analysis and contributor tracking
- **👤 Engineer Quarterly Performance** - Individual engineer tracking with weekly metrics, trend analysis, and coaching insights
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

### Installation

team-reports can be used as a standalone tool or installed as a Python package.

#### Option 1: Standalone Usage (Traditional)

```bash
# Clone repository
git clone https://github.com/cmchase/team-reports.git
cd team-reports

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Option 2: Package Installation (Recommended)

```bash
# Install from GitHub
pip install git+https://github.com/cmchase/team-reports.git

# Or install locally in development mode
cd team-reports
pip install -e .
```

After installation, you get:
- Modern `team-reports` CLI command
- Importable Python library for custom integrations
- All existing shell scripts continue to work

### Prerequisites

- Python 3.8 or higher
- **For Jira Reports**: Jira account with API access and API token
- **For GitHub Reports**: GitHub account with Personal Access Token
- **For Both**: Virtual environment recommended

### Usage Methods

team-reports supports three usage methods:

1. **Modern CLI** (Recommended): `team-reports jira weekly`
2. **Shell Scripts** (Backward Compatible): `./run_jira_weekly_summary.sh`
3. **Python Library** (For Integration): `from team_reports import WeeklyTeamSummary`

### Setup Steps

1. **Install Package** - Choose standalone or package installation
2. **Configure Credentials** - Set up API access for Jira and/or GitHub
3. **Configure Report Settings** - Customize configurations for each report type
4. **Generate Reports** - Start creating automated summaries

## 📊 Report Types Overview

| Report Type | Source | Frequency | Output | Use Case |
|-------------|--------|-----------|--------|----------|
| **Weekly Jira** | Jira API | Weekly | `jira_weekly_summary_YYYY-MM-DD_to_YYYY-MM-DD.md` | Sprint reviews, weekly standup prep |
| **Weekly GitHub** | GitHub API | Weekly | `github_weekly_summary_YYYY-MM-DD_to_YYYY-MM-DD.md` | Sprint demos, code review insights |
| **Quarterly Jira** | Jira API | Quarterly | `jira_quarterly_summary_QX_YYYY.md` | Performance reviews, quarterly planning |
| **GitHub Quarterly** | GitHub API | Quarterly | `github_quarterly_summary_QX_YYYY.md` | Code contribution analysis, developer insights |
| **Engineer Performance** | Jira + GitHub | Quarterly | `engineer_quarterly_performance_QX_YYYY.md` | 1-on-1s, coaching, individual performance tracking |

## 🎮 Modern CLI Usage

After installing the package, use the unified `team-reports` command:

```bash
# Jira reports
team-reports jira weekly                          # Current week
team-reports jira weekly 2025-01-01 2025-01-07   # Specific dates
team-reports jira quarterly                       # Current quarter
team-reports jira quarterly 2025 4                # Q4 2025

# GitHub reports
team-reports github weekly                        # Current week
team-reports github quarterly                     # Current quarter
team-reports github quarterly 2025 4              # Q4 2025

# Engineer performance reports
team-reports engineer performance                 # Current quarter
team-reports engineer performance 2025 2          # Q2 2025

# With options
team-reports jira weekly --config custom.yaml
team-reports jira weekly --jira-token YOUR_TOKEN
team-reports github weekly --github-token YOUR_TOKEN

# Get help
team-reports --help
team-reports jira weekly --help
```

## 📚 Library Usage

Use team-reports in your Python projects:

```python
from team_reports import WeeklyTeamSummary

# With .env credentials
report = WeeklyTeamSummary(config_file='config/jira_config.yaml')
summary, tickets = report.generate_weekly_summary('2025-01-01', '2025-01-07')

# Or with explicit credentials (no .env needed)
report = WeeklyTeamSummary(
    config_file='config/jira_config.yaml',
    jira_server='https://company.atlassian.net',
    jira_email='user@company.com',
    jira_token='your-token'
)
summary, tickets = report.generate_weekly_summary('2025-01-01', '2025-01-07')

# Use the report content
print(summary)  # Formatted markdown report
# Process ticket data if needed
for ticket in tickets:
    print(f"{ticket.key}: {ticket.fields.summary}")
```

**Available Classes:**
```python
from team_reports import (
    WeeklyTeamSummary,            # Jira weekly reports
    QuarterlyTeamSummary,         # Jira quarterly reports
    GitHubWeeklySummary,          # GitHub weekly reports
    GitHubQuarterlySummary,       # GitHub quarterly reports
    EngineerQuarterlyPerformance  # Engineer performance reports
)
```

See [LIBRARY_USAGE.md](LIBRARY_USAGE.md) for complete API documentation and examples.

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
- **Jira (Atlassian Cloud)**: Account Settings → Security → API tokens → Create token
- **Jira (Server/Data Center)**: Profile → Personal Access Tokens → Create token
- **GitHub**: Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
  - Required scopes: `repo` (for private repos) or `public_repo` (for public repos)

### 3. Configure Report Settings

**For Jira Reports:**
```bash
cp config/jira_config_example.yaml config/jira_config.yaml
# Edit config/jira_config.yaml with your team's projects, members, and categorization rules
```

**For GitHub Reports:**
```bash  
cp config/github_config_example.yaml config/github_config.yaml
# Edit config/github_config.yaml with your repositories and team member mapping
```

### 4. Generate Your First Reports

#### 📅 Weekly Jira Reports
```bash
# Generate report for last 7 days
./run_jira_weekly_summary.sh

# Generate report for specific date range  
./run_jira_weekly_summary.sh 2025-09-10 2025-09-16

# Generate multiple weekly reports (batch processing)
./run_batch_weekly.sh jira last-4    # Last 4 Jira reports
./run_batch_weekly.sh github last-4  # Last 4 GitHub reports
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

#### 👤 Engineer Quarterly Performance Reports
```bash
# Generate report for current quarter
./run_engineer_quarterly_performance.sh

# Generate report for specific quarter (Q2 2025)
./run_engineer_quarterly_performance.sh 2025 2

# Custom configuration
./run_engineer_quarterly_performance.sh 2025 2 config/custom_config.yaml
```

## 📁 Project Structure

```
team-reports/
├── 📦 Package (Installable)
│   ├── team_reports/
│   │   ├── __init__.py                  # Public API exports
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   └── main.py                  # Click CLI implementation
│   │   ├── reports/
│   │   │   ├── __init__.py
│   │   │   ├── jira_weekly.py           # Jira weekly report class
│   │   │   ├── jira_quarterly.py        # Jira quarterly report class
│   │   │   ├── github_weekly.py         # GitHub weekly report class
│   │   │   ├── github_quarterly.py      # GitHub quarterly report class
│   │   │   └── engineer_performance.py  # Engineer performance class
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── jira.py                  # Jira API utilities
│   │       ├── github.py                # GitHub API utilities
│   │       ├── config.py                # Configuration management
│   │       ├── date.py                  # Date utilities
│   │       ├── ticket.py                # Ticket processing
│   │       └── report.py                # Report generation
│   └── pyproject.toml                   # Package metadata & dependencies
├── 🚀 Shell Scripts (Backward Compatible)
│   ├── run_jira_weekly_summary.sh       # Weekly Jira report runner
│   ├── run_github_weekly_summary.sh     # Weekly GitHub report runner
│   ├── run_batch_weekly.sh              # Batch weekly report runner
│   ├── run_jira_quarterly_summary.sh    # Quarterly Jira report runner
│   ├── run_github_quarterly_summary.sh  # GitHub quarterly report runner
│   └── run_engineer_quarterly_performance.sh # Engineer performance runner
├── ⚙️ Configuration
│   ├── env.template                     # Environment template
│   ├── config/
│   │   ├── default_config.yaml          # Default settings
│   │   ├── team_config_example.yaml     # Team configuration example
│   │   ├── jira_config_example.yaml     # Jira configuration example
│   │   ├── github_config_example.yaml   # GitHub configuration example
│   │   ├── jira_config.yaml             # Your Jira config (create this)
│   │   └── github_config.yaml           # Your GitHub config (create this)
│   └── .env                             # API credentials (create this)
├── 🛠️ Old Utilities (Deprecated - use team_reports.utils)
│   └── utils/
│       ├── __init__.py                 # Package initialization
│       ├── batch.py                   # Batch processing and date utilities
│       ├── config.py                  # Configuration management
│       ├── date.py                    # Date parsing and ranges
│       ├── engineer_performance.py    # Engineer performance tracking
│       ├── github_client.py           # GitHub API client
│       ├── github.py                  # GitHub API utilities
│       ├── jira_client.py             # Jira API client
│       ├── jira.py                    # Jira API utilities
│       ├── report.py                  # Report formatting and output
│       └── ticket.py                  # Ticket categorization
├── 📄 Documentation
│   ├── README.md                      # This file
│   ├── LIBRARY_USAGE.md               # Python API guide
│   ├── MIGRATION_GUIDE.md             # Upgrade guide
│   ├── CONFIGURATION_GUIDE.md         # Configuration reference
│   ├── WEEKLY_SUMMARY_README.md       # Weekly reports guide
│   ├── GITHUB_QUARTERLY_README.md     # GitHub reports guide
│   └── DEVELOPER_GUIDE.md             # Development guide
├── 📁 Output
│   └── Reports/                       # Generated reports (auto-created)
│       ├── jira_weekly_summary_*.md   # Weekly Jira reports
│       ├── github_weekly_summary_*.md # Weekly GitHub reports
│       ├── jira_quarterly_summary_*.md # Quarterly Jira reports
│       ├── github_quarterly_*.md      # GitHub quarterly reports
│       └── engineer_quarterly_performance_*.md # Engineer performance reports
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

## ⚙️ Configuration Precedence

Team Reports uses a **layered configuration system** with deterministic precedence:

```
1. config/default_config.yaml    (Base defaults)
2. config/jira_config.yaml              (User YAML files)  
3. config/github_config.yaml            (User YAML files)
4. .env environment overrides    (Highest priority)
```

### Environment Variable Mapping

Environment variables are mapped into the `env.*` namespace for secure display in report footers:

| Environment Variable | Config Path | Description |
|---------------------|-------------|-------------|
| `JIRA_SERVER` | `env.jira.server` | Jira instance URL |
| `JIRA_EMAIL` | `env.jira.email` | Jira authentication email |
| `JIRA_API_TOKEN` | `env.jira.token` | Jira API token (redacted) |
| `GITHUB_TOKEN` | `env.github.token` | GitHub API token (redacted) |

**Security Note:** Environment overrides are displayed in report footers (when `report.show_active_config: true`) with automatic redaction of sensitive values like tokens and credentials.

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

**Batch Processing (Multiple Weeks):**
```bash
# Generate Jira reports for the last 4 weeks
./run_batch_weekly.sh jira last-4

# Generate 6 GitHub weekly reports starting from a specific date
./run_batch_weekly.sh github 2025-09-01:6

# Generate all Jira weekly reports between two dates
./run_batch_weekly.sh jira 2025-09-01 to 2025-10-20

# Batch with custom config
./run_batch_weekly.sh github last-3 config/custom_github_config.yaml
```

**Python Direct:**
```bash
# Basic usage
python3 jira_weekly_summary.py

# Specific date range
python3 jira_weekly_summary.py 2025-09-10 2025-09-16

# Custom configuration
python3 jira_weekly_summary.py 2025-09-10 2025-09-16 config/custom_jira_config.yaml
```

### 🐙 Weekly GitHub Reports

**Shell Script (Recommended):**
```bash
# Generate report for current week
./run_github_weekly_summary.sh

# Generate report for specific date range
./run_github_weekly_summary.sh 2025-09-10 2025-09-16

# Custom configuration
./run_github_weekly_summary.sh 2025-09-10 2025-09-16 config/custom_github_config.yaml
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
./run_jira_quarterly_summary.sh 2025 4 config/custom_jira_config.yaml
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
./run_github_quarterly_summary.sh 2025 4 config/custom_github_config.yaml
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

### 👤 Engineer Quarterly Performance Reports

**Shell Script (Recommended):**
```bash
# Current quarter
./run_engineer_quarterly_performance.sh

# Specific quarter (Q2 2025)
./run_engineer_quarterly_performance.sh 2025 2

# Custom configuration
./run_engineer_quarterly_performance.sh 2025 2 config/custom_config.yaml
```

**Python Direct:**
```bash
# Current quarter
python3 engineer_quarterly_performance.py

# Specific quarter
python3 engineer_quarterly_performance.py 2025 2

# With custom config
python3 engineer_quarterly_performance.py 2025 2 custom_config.yaml
```

### 🔄 Batch Report Generation

**Multi-Week Batch Processing:**
```bash
# Generate multiple weeks efficiently
./run_batch_weekly.sh jira last-4                    # Last 4 Jira weekly reports
./run_batch_weekly.sh github 2025-09-01:8            # 8 GitHub reports from Sept 1st
./run_batch_weekly.sh jira 2025-08-01 to 2025-10-01  # All Jira reports in date range

# Custom configurations
./run_batch_weekly.sh github last-6 config/custom_github_config.yaml
```

**Generate all reports for current period:**
```bash
# All weekly reports (Jira + GitHub)
./run_jira_weekly_summary.sh
./run_github_weekly_summary.sh

# All quarterly reports (Jira + GitHub + Engineer Performance)
./run_jira_quarterly_summary.sh  
./run_github_quarterly_summary.sh
./run_engineer_quarterly_performance.sh

# Complete reporting suite
./run_jira_weekly_summary.sh && ./run_github_weekly_summary.sh && ./run_jira_quarterly_summary.sh && ./run_github_quarterly_summary.sh && ./run_engineer_quarterly_performance.sh
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
- **📋 Comprehensive Ticket Lists** - All tickets with detailed categorization

**Example Output:**
```markdown
# 📆 QUARTERLY TEAM SUMMARY: Q4 2025

## 📈 EXECUTIVE SUMMARY  
- **Total Tickets Completed:** 342
- **Total Story Points:** 1,247
- **Active Contributors:** 8 team members
- **Most Active Category:** Backend Development (156 tickets)

## 👥 INDIVIDUAL CONTRIBUTOR PERFORMANCE
### 👤 Jane Smith
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

## 👥 CONTRIBUTOR SUMMARY  
| Contributor | PRs | Commits | Lines + | Lines - |
|-------------|-----|---------|---------|---------|
| Jane Smith | 34 | 89 | +3,421 | -1,876 |
```

### 👤 Engineer Quarterly Performance Reports

**Features:**
- **📊 Weekly Performance Tracking** - 13-week granular view of GitHub and Jira activity
- **📈 Trend Analysis** - Performance trajectories (increasing/stable/decreasing patterns)
- **🤝 Collaboration Metrics** - PR reviews, comments, and team engagement
- **⚡ Velocity Tracking** - Commits, PRs, and Jira ticket completion rates
- **💡 Coaching Insights** - Automated flags for performance concerns with actionable recommendations
- **🔍 Cross-System View** - Unified GitHub and Jira metrics per engineer

**Example Output:**
```markdown
# 👤 ENGINEER QUARTERLY PERFORMANCE: Q2 2025

## 📊 EXECUTIVE SUMMARY
- **Reporting Period:** Q2 2025 (13 weeks)
- **Active Engineers:** 8
- **Total Team Activity:** 234 PRs, 567 commits, 123 tickets completed

### 🏆 Top Performers
1. Jane Smith - High velocity, strong collaboration
2. Bob Developer - Consistent output, improving trend

### ⚠️ Coaching Priorities
- 2 engineers with decreasing velocity trends
- 1 engineer with low collaboration metrics

## 👤 INDIVIDUAL ENGINEER ANALYSIS

### Jane Smith

#### 📈 Performance Trends
- **Velocity:** ⬆️ Increasing (15% improvement over quarter)
- **Collaboration:** ⬆️ Increasing (strong PR review activity)
- **Consistency:** Stable week-over-week

#### 📊 Weekly Metrics (13 weeks)
| Week | PRs | Commits | Reviews | Tickets | Cycle Time |
|------|-----|---------|---------|---------|------------|
| W1   | 3   | 12      | 8       | 4       | 3.2 days   |
| W2   | 4   | 15      | 10      | 5       | 2.8 days   |
```

### 📁 Output Organization

All reports are saved in the `Reports/` directory with consistent naming:
- **Weekly Jira**: `jira_weekly_summary_2025-09-10_to_2025-09-16.md`
- **Weekly GitHub**: `github_weekly_summary_2025-09-10_to_2025-09-16.md`
- **Quarterly Jira**: `jira_quarterly_summary_Q4_2025.md`  
- **GitHub Quarterly**: `github_quarterly_summary_Q4_2025.md`
- **Engineer Performance**: `engineer_quarterly_performance_Q2_2025.md`

## ⚙️ Configuration

### Jira Configuration (`config/jira_config.yaml`)

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

### GitHub Configuration (`config/github_config.yaml`)

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

1. **Edit `config/jira_config.yaml`**
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

1. **Edit `config/github_config.yaml`**
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
| **[LIBRARY_USAGE.md](LIBRARY_USAGE.md)** | Python library API and integration examples | Developers |
| **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** | Upgrading from standalone to package | Existing users |
| **[WEEKLY_SUMMARY_README.md](WEEKLY_SUMMARY_README.md)** | Detailed weekly reports guide | End users |
| **[GITHUB_QUARTERLY_README.md](GITHUB_QUARTERLY_README.md)** | GitHub reports comprehensive guide | End users |
| **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** | Advanced configuration options | Power users |
| **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** | Implementation and extension guide | Developers |

## 🔒 Security

### 🔐 Credential Management
- **Never commit `.env` file** - Contains sensitive API tokens and credentials
- **Never commit configuration files with real data**:
  - `config/jira_config.yaml` - Contains team-specific Jira information
  - `config/github_config.yaml` - Contains GitHub repository and team data
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
config/jira_config.yaml        # Team-specific Jira config  
config/github_config.yaml      # GitHub repositories and team mapping
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
   - Check your JQL filter in `config/jira_config.yaml`
   - Verify date range is correct
   - Ensure you have access to the projects
   - Test the JQL query directly in Jira

4. **Configuration Error**
   - Validate YAML syntax in `config/jira_config.yaml`
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

- **✅ Package Refactor (v1.0)** - Pip-installable with modern CLI and library API
  - Install from GitHub: `pip install git+https://github.com/cmchase/team-reports.git`
  - Modern CLI: `team-reports jira weekly`, `team-reports github quarterly`, etc.
  - Importable library: `from team_reports import WeeklyTeamSummary`
  - Credential passing without .env files for CI/CD and cloud environments
  - Full backward compatibility with existing shell scripts and workflows
  - See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) and [LIBRARY_USAGE.md](LIBRARY_USAGE.md)

- **✅ Engineer Quarterly Performance Reports** - Individual engineer tracking and coaching insights
  - Week-by-week performance tracking (13 weeks per quarter) with granular metrics
  - Cross-platform data integration combining GitHub and Jira activity
  - Automated trend analysis detecting increasing/stable/decreasing performance patterns
  - Collaboration metrics including PR reviews, comments, and team engagement
  - Configurable coaching thresholds with actionable insights for 1-on-1s
  - Executive summary highlighting top performers and coaching priorities

- **✅ Team Configuration Consolidation** - Single source of truth for team data
  - Unified `team_config.yaml` consolidating all team member information
  - Cross-system user mapping linking GitHub usernames to Jira emails
  - Eliminates duplicate team member definitions across config files
  - Shared team categorization rules and sizing estimates

- **✅ Resolution Date Tracking** - Accurate completion date filtering
  - Jira reports now use `resolutiondate` instead of `updated` for precise tracking
  - Shows tickets actually resolved during period, not just updated
  - More accurate weekly and quarterly completion metrics
  - Maintains fallback to `updated` date when resolution date unavailable

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

- **✅ Bot Filtering** - Automatic filtering of bot accounts from reports with configurable patterns
- **✅ Multi-Platform Integration** - Unified credential management for Jira and GitHub APIs
- **✅ Enhanced Configuration** - Separate config files for different report types with layered precedence
- **✅ Shell Script Automation** - Convenient execution scripts with error handling
- **✅ Rich Report Output** - Enhanced Markdown formatting with tables and visual indicators
- **✅ Improved Data Handling** - Robust API pagination and rate limiting
- **✅ Comprehensive Documentation** - Detailed guides for each report type
- **✅ Performance Optimization** - Efficient weekly data aggregation and memory-conscious processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🗺️ Roadmap & Future Vision

See [ROADMAP.md](ROADMAP.md)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.