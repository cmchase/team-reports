#!/bin/bash

# GitLab Quarterly Summary Runner
#
# Generates quarterly reports from GitLab projects (including self-hosted/VPN instances)
# with error handling and setup. Mirrors run_github_quarterly_summary.sh.
#
# Usage:
#   ./run_gitlab_quarterly_summary.sh                    # Current quarter
#   ./run_gitlab_quarterly_summary.sh 2025 4             # Q4 2025
#   ./run_gitlab_quarterly_summary.sh 2025 4 config/gitlab_config.yaml

set -e

echo "GitLab Quarterly Summary Generator"
echo "==================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "Warning: Virtual environment not found"
    echo "Attempting to run with system Python..."
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check for GitLab token
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Please create .env with GITLAB_TOKEN for GitLab API access (e.g. self-hosted/VPN)."
    echo ""
fi

if [ -f ".env" ] && ! grep -q "GITLAB_TOKEN" .env; then
    echo "Warning: GITLAB_TOKEN not found in .env"
    echo "Add GITLAB_TOKEN for GitLab API access."
    echo ""
fi

# Check for configuration file
CONFIG_FILE="config/gitlab_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "config/gitlab_config_example.yaml" ]; then
        echo "Warning: config/gitlab_config.yaml not found"
        echo "Copy config/gitlab_config_example.yaml to config/gitlab_config.yaml and set base_url and projects."
        exit 1
    else
        echo "Error: No GitLab configuration file found"
        exit 1
    fi
fi

# Create Reports directory if needed
mkdir -p Reports

# Parse arguments
YEAR=""
QUARTER=""
CUSTOM_CONFIG=""

if [ $# -ge 2 ]; then
    YEAR=$1
    QUARTER=$2
    [ $# -ge 3 ] && CUSTOM_CONFIG=$3
fi

echo "Generating GitLab quarterly summary..."
echo ""

if [ -n "$CUSTOM_CONFIG" ]; then
    python3 -m team_reports.reports.gitlab_quarterly "$YEAR" "$QUARTER" "$CUSTOM_CONFIG"
elif [ -n "$YEAR" ] && [ -n "$QUARTER" ]; then
    python3 -m team_reports.reports.gitlab_quarterly "$YEAR" "$QUARTER"
else
    python3 -m team_reports.reports.gitlab_quarterly
fi

echo ""
echo "GitLab quarterly summary generation complete!"
echo "Report saved in Reports/ directory"

[ -d "venv" ] && deactivate 2>/dev/null || true
