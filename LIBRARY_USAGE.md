# Library Usage Guide

This guide shows how to use team-reports as a Python library in your own projects.

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/cmchase/team-reports.git

# Or install locally in development mode
cd /path/to/team-reports
pip install -e .
```

## Quick Start

```python
from team_reports import WeeklyTeamSummary

# Create report instance
report = WeeklyTeamSummary(config_file='config/jira_config.yaml')

# Generate report (initializes connection and fetches data)
summary, tickets = report.generate_weekly_summary('2025-01-01', '2025-01-07')

# Use the report
print(summary)  # Formatted markdown report

# Access ticket data if needed
for ticket in tickets:
    print(f"{ticket.key}: {ticket.fields.summary}")
```

## Available Report Classes

```python
from team_reports import (
    WeeklyTeamSummary,            # Jira weekly reports
    QuarterlyTeamSummary,         # Jira quarterly reports
    GitHubWeeklySummary,          # GitHub weekly reports
    GitHubQuarterlySummary,       # GitHub quarterly reports
    EngineerQuarterlyPerformance  # Engineer performance reports
)
```

## Credential Management

### Using .env File (Default)

Create a `.env` file:
```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token
GITHUB_TOKEN=your-github-token
```

Then use without passing credentials:
```python
from team_reports import WeeklyTeamSummary

report = WeeklyTeamSummary(config_file='config/jira_config.yaml')
report.initialize()  # Uses .env credentials
```

### Passing Credentials Directly

For environments where you can't use .env files:

```python
from team_reports import WeeklyTeamSummary

report = WeeklyTeamSummary(
    config_file='config/jira_config.yaml',
    jira_server='https://company.atlassian.net',
    jira_email='user@company.com',
    jira_token='your-api-token'
)
report.initialize()
```

### Credential Precedence

Credentials are resolved in this order:
1. Parameters passed to class constructor
2. Environment variables
3. .env file

This allows flexible deployment across different environments.

## Report Types

### 1. Jira Weekly Reports

```python
from team_reports import WeeklyTeamSummary

# Basic usage - returns (summary_text, tickets_list)
report = WeeklyTeamSummary(config_file='config/jira_config.yaml')
summary, tickets = report.generate_weekly_summary('2025-01-01', '2025-01-07')

# Use the report
print(summary)  # Formatted markdown

# Access raw ticket data
print(f"Found {len(tickets)} tickets")
for ticket in tickets:
    print(f"{ticket.key}: {ticket.fields.summary}")
```

### 2. Jira Quarterly Reports

```python
from team_reports import QuarterlyTeamSummary

# Generate quarterly report - returns (summary_text, tickets_list)
report = QuarterlyTeamSummary(config_file='config/jira_config.yaml')
summary, tickets = report.generate_quarterly_summary(year=2025, quarter=4)

# Use the report
print(summary)
print(f"Analyzed {len(tickets)} tickets for Q4 2025")
```

### 3. GitHub Weekly Reports

```python
from team_reports import GitHubWeeklySummary

# Generate report - returns (summary_text, raw_data_dict)
report = GitHubWeeklySummary(
    config_file='config/github_config.yaml',
    github_token='optional-token'  # Or use .env
)

summary, data = report.generate_report('2025-01-01', '2025-01-07', 'config/github_config.yaml')

# Access raw data
for pr in data['pull_requests']:
    print(f"PR #{pr['number']}: {pr['title']}")
```

### 4. GitHub Quarterly Reports

```python
from team_reports import GitHubQuarterlySummary

# Generate quarterly report - returns (summary_text, raw_data_dict)
report = GitHubQuarterlySummary(
    config_file='config/github_config.yaml'
)

summary, data = report.generate_quarterly_summary(year=2025, quarter=4)

# Use the report and data
print(summary)
print(f"Total pull requests: {len(data)}")
```

### 5. Engineer Performance Reports

```python
from team_reports import EngineerQuarterlyPerformance

report = EngineerQuarterlyPerformance(
    jira_config_file='config/jira_config.yaml',
    github_config_file='config/github_config.yaml',
    # Optional credentials
    jira_server='https://company.atlassian.net',
    jira_email='user@company.com',
    jira_token='jira-token',
    github_token='github-token'
)

# Returns report text
summary = report.generate_report(year=2025, quarter=2)
```

## Advanced Usage

### Custom Configuration

You can pass different config files for different teams:

```python
backend_report = WeeklyTeamSummary(config_file='config/backend_team.yaml')
frontend_report = WeeklyTeamSummary(config_file='config/frontend_team.yaml')
```

### Accessing Raw Data

Some reports return both formatted text and raw data:

```python
from team_reports import GitHubWeeklySummary

report = GitHubWeeklySummary(config_file='config/github_config.yaml')
summary_text, raw_data = report.generate_report('2025-01-01', '2025-01-07', 'config/github_config.yaml')

# Access raw data
pull_requests = raw_data['pull_requests']
commits = raw_data['commits']
issues = raw_data['issues']

# Process custom analytics
for repo, prs in pull_requests.items():
    print(f"{repo}: {len(prs)} PRs")
```

### Integration Example: Slack Bot

```python
import os
from team_reports import WeeklyTeamSummary
from slack_sdk import WebClient

def post_weekly_report_to_slack():
    # Generate report
    report = WeeklyTeamSummary(
        config_file='config/jira_config.yaml',
        jira_server=os.environ['JIRA_SERVER'],
        jira_email=os.environ['JIRA_EMAIL'],
        jira_token=os.environ['JIRA_TOKEN']
    )
    
    summary, tickets = report.generate_weekly_summary('2025-01-01', '2025-01-07')
    
    # Post to Slack
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(
        channel='#team-reports',
        text=f"```\n{summary}\n```"
    )

# Run weekly via cron or scheduler
post_weekly_report_to_slack()
```

### Integration Example: CI/CD Pipeline

```python
# in your CI/CD script
from team_reports import QuarterlyTeamSummary

def generate_quarterly_artifacts():
    report = QuarterlyTeamSummary(
        config_file='config/jira_config.yaml',
        jira_server=os.environ['JIRA_SERVER'],
        jira_email=os.environ['JIRA_EMAIL'],
        jira_token=os.environ['JIRA_TOKEN']
    )
    report.initialize()
    
    summary = report.generate_quarterly_summary(2025, 4)
    
    # Save to artifact storage
    with open('artifacts/q4-2025-report.md', 'w') as f:
        f.write(summary)
    
    return summary

if __name__ == '__main__':
    generate_quarterly_artifacts()
```

### Integration Example: Dashboard Data

```python
from team_reports import EngineerQuarterlyPerformance
import json

def get_engineer_metrics(year: int, quarter: int) -> dict:
    """Extract engineer metrics for dashboard visualization."""
    report = EngineerQuarterlyPerformance(
        jira_config_file='config/jira_config.yaml',
        github_config_file='config/github_config.yaml'
    )
    
    # Generate report (internally collects data)
    from team_reports.utils.engineer_performance import collect_weekly_engineer_data
    
    engineer_data = collect_weekly_engineer_data(year, quarter,  
                                                  'config/jira_config.yaml',
                                                  'config/github_config.yaml')
    
    # Extract metrics for visualization
    metrics = {}
    for engineer, data in engineer_data.items():
        metrics[engineer] = {
            'total_prs': sum(week.get('github', {}).get('prs', 0) 
                           for week in data['weeks'].values()),
            'total_commits': sum(week.get('github', {}).get('commits', 0)
                               for week in data['weeks'].values()),
            'total_tickets': sum(week.get('jira', {}).get('tickets_completed', 0)
                                for week in data['weeks'].values())
        }
    
    return metrics

# Use in web dashboard
metrics = get_engineer_metrics(2025, 2)
print(json.dumps(metrics, indent=2))
```

## Error Handling

```python
from team_reports import WeeklyTeamSummary

try:
    report = WeeklyTeamSummary(
        config_file='config/jira_config.yaml',
        jira_server='https://company.atlassian.net',
        jira_email='user@company.com',
        jira_token='token'
    )
    report.initialize()
    tickets = report.fetch_tickets('2025-01-01', '2025-01-07')
    summary = report.generate_summary_report(tickets, '2025-01-01', '2025-01-07')
    
except ValueError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"Connection error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration Files

All report classes require YAML configuration files. See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for details.

### Minimal Jira Config

```yaml
base_jql: |
  project = MYPROJECT

team_categories:
  Development:
    components: ["Backend", "Frontend"]
    description: "Development work"

team_members:
  "user@company.com": "User Name"
```

### Minimal GitHub Config

```yaml
repositories:
  - "my-repo"
  - "another-repo"

team_members:
  "github_username": "Display Name"
```

## API Reference

### WeeklyTeamSummary

```python
WeeklyTeamSummary(
    config_file: str = 'config/jira_config.yaml',
    jira_server: str = None,
    jira_email: str = None,
    jira_token: str = None
)
```

**Methods:**
- `initialize()`: Connect to Jira
- `fetch_tickets(start_date: str, end_date: str)`: Fetch tickets
- `generate_summary_report(tickets, start_date: str, end_date: str) -> str`: Generate report

### QuarterlyJiraSummary

```python
QuarterlyJiraSummary(
    config_file: str = 'config/jira_config.yaml',
    jira_server: str = None,
    jira_email: str = None,
    jira_token: str = None
)
```

**Methods:**
- `initialize()`: Connect to Jira
- `generate_quarterly_summary(year: int, quarter: int) -> str`: Generate report

### GithubWeeklySummary

```python
GithubWeeklySummary(
    config_file: str = 'config/github_config.yaml',
    github_token: str = None
)
```

**Methods:**
- `generate_report(start_date: str, end_date: str, config_file: str) -> Tuple[str, Dict]`

### GithubQuarterlySummary

```python
GithubQuarterlySummary(
    config_file: str = 'config/github_config.yaml',
    github_token: str = None
)
```

**Methods:**
- `generate_quarterly_summary(year: int, quarter: int) -> Tuple[str, Dict]`

### EngineerQuarterlyPerformance

```python
EngineerQuarterlyPerformance(
    jira_config_file: str = 'config/jira_config.yaml',
    github_config_file: str = 'config/github_config.yaml',
    jira_server: str = None,
    jira_email: str = None,
    jira_token: str = None,
    github_token: str = None
)
```

**Methods:**
- `generate_report(year: int, quarter: int) -> str`: Generate report

## Best Practices

1. **Use credential parameters** in production environments instead of `.env` files
2. **Cache API clients** if generating multiple reports
3. **Handle exceptions** appropriately for your use case
4. **Respect API rate limits** when making bulk requests
5. **Validate configuration** before running reports
6. **Store credentials securely** using your platform's secret management

## Troubleshooting

### ImportError: No module named 'team_reports'

```bash
pip install -e /path/to/team-reports
```

### "Missing required credentials"

Pass credentials explicitly or ensure .env file exists with required variables.

### Connection timeouts

Check network connectivity and API endpoint availability.

### Configuration validation errors

Review your YAML syntax and required fields in [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md).

## Support

- Check [README.md](README.md) for overview
- Check [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for config details
- Check [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for upgrading
- Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for contributing

