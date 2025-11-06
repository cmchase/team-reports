# Migration Guide: Upgrading to team-reports 1.0

This guide helps existing users migrate from standalone scripts to the packaged version of team-reports.

## What Changed?

team-reports v1.0 introduces a proper Python package structure with:
- **Pip installable** from GitHub
- **Modern CLI** with `team-reports` command
- **Library API** for programmatic usage
- **Credential passing** without requiring `.env` files
- **Backward compatible** shell scripts

## For Existing Users

### Your Scripts Still Work!

All existing shell scripts (`run_*.sh`) continue to work exactly as before. They now internally use the new CLI but maintain the same interface.

```bash
# These all still work:
./run_jira_weekly_summary.sh
./run_github_quarterly_summary.sh 2025 4
./run_engineer_quarterly_performance.sh
```

### Your .env Files Still Work!

The `.env` file continues to be the default source for credentials. No changes required.

### Your Config Files Still Work!

All YAML configuration files work exactly as before. No changes needed.

## New Installation Method (Optional)

You can now install team-reports as a package:

```bash
# Install from GitHub
pip install git+https://github.com/cmchase/team-reports.git

# Or install locally in development mode
cd team-reports
pip install -e .
```

## New CLI Commands (Optional)

After installation, you get a modern CLI:

```bash
# Instead of ./run_jira_weekly_summary.sh
team-reports jira weekly

# Instead of ./run_github_quarterly_summary.sh 2025 4  
team-reports github quarterly 2025 4

# Instead of ./run_engineer_quarterly_performance.sh 2025 2
team-reports engineer performance 2025 2
```

### CLI Advantages

- **Shorter commands**: `team-reports jira weekly` vs `./run_jira_weekly_summary.sh`
- **Better help**: `team-reports jira weekly --help` shows all options
- **Credential options**: Pass credentials via command line if needed
- **Consistent interface**: All reports follow the same pattern

## Library Usage (New Feature)

You can now import and use team-reports in your Python code:

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
```

## What You Don't Need to Change

- ✅ Your `.env` file
- ✅ Your YAML config files
- ✅ Your shell scripts usage
- ✅ Your report output locations
- ✅ Your existing workflows

## Gradual Migration Path

1. **Phase 1** (Now): Keep using existing shell scripts - they work as-is
2. **Phase 2** (Optional): Install package and try new CLI commands
3. **Phase 3** (Optional): Use library API for custom integrations

## Troubleshooting

### Shell Script Says "team-reports CLI not found"

The script will automatically try to install the package. If it fails:

```bash
cd /path/to/team-reports
pip install -e .
```

### ImportError when using as library

Make sure the package is installed:

```bash
pip install -e /path/to/team-reports
```

### CLI command not found

Check your Python environment:

```bash
which team-reports  # Should show path to command
pip list | grep team-reports  # Should show installed version
```

## Getting Help

- Run `team-reports --help` for CLI usage
- Run `team-reports jira weekly --help` for command-specific help
- Check [LIBRARY_USAGE.md](LIBRARY_USAGE.md) for programmatic API
- Check [README.md](README.md) for full documentation

## Rollback (If Needed)

If you encounter issues, you can continue using the old scripts:

1. Don't install the package
2. Use shell scripts as before: `./run_jira_weekly_summary.sh`
3. Everything will work with `.env` credentials as it always has

The standalone Python scripts (`jira_weekly_summary.py`, etc.) are kept for backward compatibility.

