# Team Reports

A comprehensive suite of tools for generating automated team summaries and performance reports from multiple data sources including Jira tickets and GitHub repositories. Create weekly, quarterly, and annual reports with rich analytics, contributor insights, and development metrics.

## 🎯 Features

### 📊 Multiple Report Types
- **📅 Weekly Jira Reports** - Generate weekly team summaries from Jira tickets
- **📆 Quarterly Jira Reports** - Long-term analysis with contributor performance metrics  
- **🐙 GitHub Quarterly Reports** - Comprehensive GitHub repository analysis and contributor tracking
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
./run_weekly_summary.sh

# Generate report for specific date range  
./run_weekly_summary.sh 2025-09-10 2025-09-16
```

#### 📆 Quarterly Jira Reports
```bash
# Generate report for current quarter
./run_quarterly_summary.sh

# Generate report for specific quarter
./run_quarterly_summary.sh 2025 4
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
│   ├── weekly_team_summary.py           # Weekly Jira reports  
│   ├── quarterly_team_summary.py        # Quarterly Jira reports
│   └── github_quarterly_summary.py      # GitHub quarterly reports
├── 🚀 Execution Scripts  
│   ├── run_weekly_summary.sh            # Weekly report runner
│   ├── run_quarterly_summary.sh         # Quarterly Jira report runner
│   └── run_github_quarterly_summary.sh  # GitHub report runner
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
│       ├── team_summary_*.md          # Weekly reports
│       ├── quarterly_summary_*.md     # Quarterly Jira reports
│       └── github_quarterly_*.md      # GitHub reports
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
./run_weekly_summary.sh

# Generate report for specific date range  
./run_weekly_summary.sh 2025-09-10 2025-09-16

# Generate report for current week
./run_weekly_summary.sh $(date -d "monday" +%Y-%m-%d) $(date -d "sunday" +%Y-%m-%d)
```

**Python Direct:**
```bash
# Basic usage
python3 weekly_team_summary.py

# Specific date range
python3 weekly_team_summary.py 2025-09-10 2025-09-16

# Custom configuration
python3 weekly_team_summary.py 2025-09-10 2025-09-16 custom_team_config.yaml
```

### 📆 Quarterly Jira Reports

**Shell Script (Recommended):**
```bash
# Current quarter
./run_quarterly_summary.sh

# Specific quarter (Q4 2025)
./run_quarterly_summary.sh 2025 4

# Custom configuration  
./run_quarterly_summary.sh 2025 4 custom_team_config.yaml
```

**Python Direct:**
```bash
# Current quarter
python3 quarterly_team_summary.py

# Specific quarter
python3 quarterly_team_summary.py 2025 4

# With custom config
python3 quarterly_team_summary.py 2025 4 custom_config.yaml
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
# Weekly + Quarterly Jira + GitHub Quarterly
./run_weekly_summary.sh
./run_quarterly_summary.sh  
./run_github_quarterly_summary.sh
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
- **Weekly**: `team_summary_2025-09-10_to_2025-09-16.md`
- **Quarterly Jira**: `quarterly_summary_Q4_2025.md`  
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
   - Verify the `.env` file is in the same directory as `weekly_team_summary.py`

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
   - Ensure `server.py` is in the same directory as `weekly_team_summary.py`
   - Check that all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python version is 3.8 or higher

### Debug Mode

Enable debug logging by modifying the logging level in `weekly_team_summary.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 🆕 Recent Updates

### 🚀 Major New Features

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

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Success!

Your comprehensive Team Reports suite is now ready to use! You can:

### 📊 Multi-Platform Reporting
- ✅ **Generate weekly Jira summaries** for sprint reviews and team standups
- ✅ **Create quarterly Jira analysis** for performance reviews and planning
- ✅ **Produce GitHub quarterly reports** for code contribution insights
- ✅ **Combine insights** across Jira tickets and GitHub contributions

### 🚀 Advanced Capabilities  
- ✅ **Smart ticket categorization** with customizable rules and filters
- ✅ **Individual contributor tracking** with detailed performance metrics
- ✅ **Cross-repository analysis** for complete development visibility  
- ✅ **Rich Markdown output** with tables, links, and visual indicators
- ✅ **Automated execution** via convenient shell scripts
- ✅ **Extensible architecture** using modular utilities package

### 🛠️ Enterprise Ready
- ✅ **Secure credential management** with environment variables
- ✅ **Comprehensive configuration** for different team structures
- ✅ **Robust error handling** and API rate limiting
- ✅ **Detailed documentation** for users and developers
- ✅ **Scalable design** for teams of any size

**Start generating reports and transform your team's development data into actionable insights!** 🚀

Choose your report type:
- `./run_weekly_summary.sh` for sprint insights
- `./run_quarterly_summary.sh` for performance analysis  
- `./run_github_quarterly_summary.sh` for code contribution tracking