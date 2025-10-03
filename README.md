# Jira Weekly Reports

A powerful tool for generating automated weekly team summaries from Jira tickets. This tool fetches Jira tickets based on customizable filters and categorizes them into meaningful sections for easy review and reporting.

## 🎯 Features

- **📊 Automated Reports** - Generate weekly summaries with one command
- **🏷️ Smart Categorization** - Automatically categorize tickets by components, projects, and keywords
- **📅 Flexible Date Ranges** - Generate reports for any date range
- **📝 Markdown Output** - Clean, formatted reports in Markdown format
- **⚙️ Customizable Configuration** - YAML-based configuration for easy customization
- **🔍 Advanced Filtering** - Exclude specific statuses and filter by assignees
- **📁 Organized Output** - Reports saved in dedicated Reports folder
- **🔗 Direct Jira Integration** - Built-in Jira API integration for seamless data access

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Jira account with API access
- Jira API token

### Setup Steps

1. **Install Dependencies** - Install required Python packages
2. **Configure Jira Credentials** - Set up your Jira API access
3. **Configure Team Settings** - Customize your team's configuration
4. **Generate Reports** - Start creating weekly summaries

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Jira Credentials

Create a `.env` file with your Jira details:

```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

**Getting your Jira API Token:**
1. Go to your Jira account settings
2. Navigate to Security → API tokens
3. Create a new API token
4. Copy the token and add it to your `.env` file

### 3. Configure Team Settings

Copy the example configuration and customize it:

```bash
cp team_config_example.yaml team_config.yaml
```

Edit `team_config.yaml` with your team's:
- Projects and components
- Team members
- Categorization rules
- Status filters

### 4. Generate Your First Report

```bash
# Generate report for last 7 days
python3 weekly_team_summary.py

# Generate report for specific date range
python3 weekly_team_summary.py 2025-09-10 2025-09-16

# Use the convenient shell script
./run_weekly_summary.sh 2025-09-10 2025-09-16
```

## 📁 Project Structure

```
jira-weekly-reports/
├── weekly_team_summary.py     # Main report generator
├── server.py                  # Built-in Jira API integration
├── run_weekly_summary.sh      # Convenient shell wrapper
├── team_config.yaml           # Your team configuration (create this)
├── team_config_example.yaml   # Example configuration
├── requirements.txt           # Python dependencies
├── .env                       # Jira credentials (create this)
├── Reports/                   # Generated reports (auto-created)
├── README.md                  # This file
├── WEEKLY_SUMMARY_README.md   # Detailed usage guide
└── CONFIGURATION_GUIDE.md     # Configuration guide
```

## 🔗 Dependencies

This project includes built-in Jira API integration:

- **Built-in Jira Integration** (`server.py`)
  - Direct Jira API integration using the `jira` Python library
  - Handles authentication and API communication
  - No external dependencies or separate server processes required
  - Uses your Jira credentials from the `.env` file

## 🎯 Usage Examples

### Basic Usage

```bash
# Generate report for last 7 days
python3 weekly_team_summary.py

# Generate report for specific date range
python3 weekly_team_summary.py 2025-09-10 2025-09-16

# Generate report for current week
python3 weekly_team_summary.py $(date -d "monday" +%Y-%m-%d) $(date -d "friday" +%Y-%m-%d)
```

### Using the Shell Script

```bash
# Make script executable
chmod +x run_weekly_summary.sh

# Generate report for last 7 days
./run_weekly_summary.sh

# Generate report for specific date range
./run_weekly_summary.sh 2025-09-10 2025-09-16
```

## 📊 Report Output

Reports are generated in Markdown format and include:

- **📅 Date Range** - Clear indication of the reporting period
- **📈 Summary Statistics** - Total tickets, categories breakdown
- **🏷️ Categorized Sections** - Tickets organized by your defined categories
- **📋 Ticket Details** - Key, summary, status, assignee, priority, and URL
- **📁 Organized Storage** - Reports saved in `Reports/` folder

### Example Report Structure

```markdown
# 📊 WEEKLY TEAM SUMMARY: 2025-09-10 to 2025-09-16

## 📈 OVERVIEW
- **Total Tickets:** 110
- **Edge Decommission:** 16 tickets
- **Remediations Core:** 53 tickets
- **QE / Integrations:** 20 tickets

### 🎯 REMEDIATIONS CORE - Remediations, Frontend

#### 📌 In Progress (5 tickets)

| Ticket ID | Assignee | Priority | Updated | Title |
|-----------|----------|----------|---------|-------|
| [PROJ-123](url) | John Doe | Major | 2025-09-13 | Implement new API endpoint |
```

## ⚙️ Configuration

### Team Configuration (`team_config.yaml`)

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

# Status filters
status_filters:
  all:
    - "New"
    - "Refinement"
    - "To Do"
    - "In Progress"
    - "Review"
    - "Closed"
  planned_only:
    - "New"
    - "Refinement"
    - "To Do"
  executed_only:
    - "In Progress"
    - "Review"
    - "Closed"
  completed_only:
    - "Closed"
  exclude:
    - "New"
    - "Refinement"
    - "To Do"

# Report settings
report_settings:
  max_results: 200
  order_by: "component ASC, updated DESC"
```

### Environment Variables (`.env`)

```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

## 🔧 Customization

### Adding New Categories

1. Edit `team_config.yaml`
2. Add new category under `team_categories`
3. Define matching rules (components, projects, keywords)
4. Regenerate reports

### Filtering by Status

```yaml
status_filters:
  exclude: ["New", "Refinement", "To Do"]
```

### Filtering by Assignee

```yaml
base_jql: |
  project = PROJ AND assignee in ("manager@company.com", "dev1@company.com")
```

## 📖 Documentation

- **[WEEKLY_SUMMARY_README.md](WEEKLY_SUMMARY_README.md)** - Detailed usage guide
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Advanced configuration options
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Implementation guide for AI assistants and developers

## 🔒 Security

- **Never commit `.env` file** - Contains sensitive credentials
- **Never commit `team_config.yaml`** - Contains team-specific data
- **Use API tokens** instead of passwords
- **Rotate tokens regularly** for security

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

- **✅ Built-in Jira Integration** - No external dependencies or separate server processes required
- **✅ Improved Data Handling** - Direct access to Jira Issue objects with full field information
- **✅ Better Report Formatting** - Enhanced ticket details including proper priorities and statuses
- **✅ Simplified Setup** - Create `.env` file with your Jira credentials and you're ready to go

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎉 Success!

Your Jira Weekly Reports tool is now ready to use! You can:

- ✅ Generate automated weekly summaries
- ✅ Categorize tickets automatically
- ✅ Customize reports for your team
- ✅ Export clean Markdown reports
- ✅ Schedule regular reporting
- ✅ Use built-in Jira API integration for seamless data access

Start generating your first report and see how it transforms your team's Jira data into actionable insights! 🚀