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

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Jira account with API access
- Jira API token
- **Jira MCP Server** - Required for Jira API integration

### 🔗 Jira MCP Server Setup

This project requires the **Jira MCP Server** to function. The MCP server provides the Jira API integration layer.

**Option 1: Use the Official Jira MCP Server**
- Clone and setup: [jira-mcp-server](https://github.com/sthirugn/jira-mcp-server)
- Follow the setup instructions in that repository
- Ensure the MCP server is running and accessible

**Option 2: Use Your Own MCP Server**
- If you have your own Jira MCP server implementation
- Ensure it provides the required Jira API functionality
- Configure the connection settings accordingly

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

**Note:** These credentials are used by the Jira MCP Server. Make sure the MCP server is configured with the same credentials.

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

### 4. Start the Jira MCP Server

Before generating reports, ensure the Jira MCP Server is running:

```bash
# Navigate to your jira-mcp-server directory
cd /path/to/jira-mcp-server

# Start the MCP server
python3 server.py
```

The MCP server should be running in the background while you generate reports.

### 5. Generate Your First Report

```bash
# Generate report for last 7 days
python3 weekly_team_summary.py

# Generate report for specific date range
python3 weekly_team_summary.py 2025-01-01 2025-01-07

# Use the convenient shell script
./run_weekly_summary.sh 2025-01-01 2025-01-07
```

## 📁 Project Structure

```
jira-weekly-reports/
├── weekly_team_summary.py     # Main report generator
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

This project depends on the **Jira MCP Server** for Jira API integration:

- **[jira-mcp-server](https://github.com/sthirugn/jira-mcp-server)** - Official Jira MCP Server
  - Provides Jira API integration via Model Context Protocol
  - Handles authentication and API communication
  - Must be running when generating reports

## 🎯 Usage Examples

### Basic Usage

```bash
# Generate report for last 7 days
python3 weekly_team_summary.py

# Generate report for specific date range
python3 weekly_team_summary.py 2025-01-01 2025-01-07

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
./run_weekly_summary.sh 2025-01-01 2025-01-07
```

## 📊 Report Output

Reports are generated in Markdown format and include:

- **📅 Date Range** - Clear indication of the reporting period
- **📈 Summary Statistics** - Total tickets, categories breakdown
- **🏷️ Categorized Sections** - Tickets organized by your defined categories
- **📋 Ticket Details** - Key, summary, status, assignee, and URL
- **📁 Organized Storage** - Reports saved in `Reports/` folder

### Example Report Structure

```markdown
# Weekly Team Summary
**Date Range:** 2025-01-01 to 2025-01-07

## 📊 Summary
- **Total Tickets:** 25
- **Categories:** 4

## 🏷️ Backend Development
| Ticket | Status | Assignee | Title |
|--------|--------|----------|-------|
| [PROJ-123](url) | In Progress | John Doe | Implement new API endpoint |

## 🏷️ Frontend Development
| Ticket | Status | Assignee | Title |
|--------|--------|----------|-------|
| [PROJ-124](url) | Done | Jane Smith | Update user interface |
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
  exclude: ["New", "Backlog"]
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
  exclude: ["New", "Backlog", "Refinement"]
```

### Filtering by Assignee

```yaml
base_jql: |
  project = PROJ AND assignee in ("manager@company.com", "dev1@company.com")
```

## 📖 Documentation

- **[WEEKLY_SUMMARY_README.md](WEEKLY_SUMMARY_README.md)** - Detailed usage guide
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Advanced configuration options
- **[jira-mcp-server](https://github.com/sthirugn/jira-mcp-server)** - Jira MCP Server documentation and setup

## 🔒 Security

- **Never commit `.env` file** - Contains sensitive credentials
- **Never commit `team_config.yaml`** - Contains team-specific data
- **Use API tokens** instead of passwords
- **Rotate tokens regularly** for security

## 🐛 Troubleshooting

### Common Issues

1. **MCP Server Connection Error**
   - Ensure the Jira MCP Server is running (`python3 server.py`)
   - Check that the MCP server is accessible
   - Verify the MCP server configuration matches your `.env` file
   - See [jira-mcp-server troubleshooting](https://github.com/sthirugn/jira-mcp-server#troubleshooting)

2. **Authentication Error**
   - Check your API token is correct
   - Ensure your email matches your Jira account
   - Verify token hasn't expired
   - Confirm credentials are configured in both projects

3. **No Tickets Found**
   - Check your JQL filter in `team_config.yaml`
   - Verify date range is correct
   - Ensure you have access to the projects
   - Test the JQL query directly in Jira

4. **Configuration Error**
   - Validate YAML syntax in `team_config.yaml`
   - Check file permissions
   - Ensure all required fields are present

### Debug Mode

Enable debug logging by modifying the logging level in `weekly_team_summary.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

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

Start generating your first report and see how it transforms your team's Jira data into actionable insights! 🚀
