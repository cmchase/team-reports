#!/bin/bash

# =============================================================================
# GitHub Weekly Summary Script
# =============================================================================
# 
# This script generates weekly GitHub repository summaries, providing
# insights into pull requests, commits, issues, and contributor activity.
#
# Usage:
#   ./run_github_weekly_summary.sh                    # Current week
#   ./run_github_weekly_summary.sh 2025-10-07 2025-10-13  # Specific week
#   ./run_github_weekly_summary.sh 2025-10-07 2025-10-13 config.yaml # With custom config
#
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🐙 GitHub Weekly Summary Generator${NC}"
echo -e "${BLUE}===================================${NC}"

# Check if we're in the right directory
if [ ! -f "github_weekly_summary.py" ]; then
    echo -e "${RED}❌ Error: github_weekly_summary.py not found in current directory${NC}"
    echo "Please run this script from the team-reports directory"
    exit 1
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Warning: Virtual environment not found${NC}"
    echo "Attempting to run with system Python..."
    echo "For best results, create a virtual environment:"
    echo -e "${CYAN}  python3 -m venv venv${NC}"
    echo -e "${CYAN}  source venv/bin/activate${NC}"
    echo -e "${CYAN}  pip install -r requirements.txt${NC}"
    echo ""
    PYTHON_CMD="python3"
else
    # Activate virtual environment
    echo -e "${GREEN}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
    PYTHON_CMD="python"
fi

# Check for required dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! $PYTHON_CMD -c "import requests, yaml, dotenv" 2>/dev/null; then
    echo -e "${RED}❌ Error: Missing required Python packages${NC}"
    echo "Please install dependencies:"
    echo -e "${CYAN}  pip install -r requirements.txt${NC}"
    exit 1
fi

# Check for environment file
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env file with your GitHub credentials:"
    echo -e "${CYAN}  cp env.template .env${NC}"
    echo "Then edit .env and add your GITHUB_TOKEN"
    exit 1
fi

# Check for GitHub configuration
CONFIG_FILE="github_config.yaml"

# Check if custom config file is provided as last argument
if [ $# -gt 0 ] && [[ "${!#}" == *.yaml ]]; then
    CONFIG_FILE="${!#}"
    set -- "${@:1:$(($#-1))}"  # Remove config file from arguments
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Error: Configuration file '$CONFIG_FILE' not found${NC}"
    if [ "$CONFIG_FILE" = "github_config.yaml" ]; then
        echo "Please create your GitHub configuration:"
        echo -e "${CYAN}  cp github_config_example.yaml github_config.yaml${NC}"
        echo "Then edit github_config.yaml with your repositories and team members"
    else
        echo "Please ensure the configuration file exists: $CONFIG_FILE"
    fi
    exit 1
fi

# Determine date range
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}📅 No dates provided, using current week${NC}"
    START_DATE=""
    END_DATE=""
    PERIOD_INFO="current week"
elif [ $# -eq 1 ]; then
    START_DATE="$1"
    END_DATE=""
    PERIOD_INFO="week starting $START_DATE"
    echo -e "${YELLOW}📅 Using week starting: $START_DATE${NC}"
elif [ $# -eq 2 ]; then
    START_DATE="$1"
    END_DATE="$2"
    PERIOD_INFO="$START_DATE to $END_DATE"
    echo -e "${YELLOW}📅 Using date range: $START_DATE to $END_DATE${NC}"
else
    echo -e "${RED}❌ Error: Too many arguments${NC}"
    echo "Usage: $0 [start_date] [end_date] [config_file]"
    exit 1
fi

# Show configuration info
echo -e "${BLUE}⚙️  Using configuration: $CONFIG_FILE${NC}"

# Validate GitHub token
if ! grep -q "GITHUB_TOKEN=" .env || grep -q "GITHUB_TOKEN=your-github-personal-access-token" .env; then
    echo -e "${RED}❌ Error: GITHUB_TOKEN not properly configured in .env file${NC}"
    echo "Please add your GitHub Personal Access Token to .env:"
    echo -e "${CYAN}  GITHUB_TOKEN=your_actual_github_token_here${NC}"
    exit 1
fi

# Prepare Python command arguments
PYTHON_ARGS=()
if [ -n "$START_DATE" ]; then
    PYTHON_ARGS+=("$START_DATE")
fi
if [ -n "$END_DATE" ]; then
    PYTHON_ARGS+=("$END_DATE")
fi
if [ "$CONFIG_FILE" != "github_config.yaml" ]; then
    PYTHON_ARGS+=("$CONFIG_FILE")
fi

# Create Reports directory if it doesn't exist
mkdir -p Reports

echo ""
echo -e "${GREEN}🚀 Generating GitHub Weekly Summary for $PERIOD_INFO...${NC}"
echo ""

# Run the Python script
if $PYTHON_CMD github_weekly_summary.py "${PYTHON_ARGS[@]}"; then
    echo ""
    echo -e "${GREEN}✅ GitHub Weekly Summary completed successfully!${NC}"
    echo ""
    echo -e "${CYAN}📁 Reports are saved in the Reports/ directory${NC}"
    echo -e "${CYAN}📊 Review the generated markdown file for insights${NC}"
    echo ""
    echo -e "${BLUE}💡 Tips:${NC}"
    echo "• Use this report for sprint reviews and team standups"
    echo "• Compare weekly trends to identify collaboration patterns"
    echo "• Share with stakeholders to showcase development progress"
    echo "• Combine with Jira reports for complete development insights"
    echo ""
else
    echo ""
    echo -e "${RED}❌ GitHub Weekly Summary failed${NC}"
    echo ""
    echo -e "${YELLOW}🔧 Troubleshooting tips:${NC}"
    echo "1. Verify your GITHUB_TOKEN has the right permissions (repo or public_repo scope)"
    echo "2. Check that repository names in $CONFIG_FILE are correct"
    echo "3. Ensure you have access to all repositories listed"
    echo "4. Check your internet connection and GitHub API status"
    echo "5. Verify date format: YYYY-MM-DD"
    echo ""
    exit 1
fi

# Show quick stats if report was generated
LATEST_REPORT=$(ls -t Reports/github_weekly_summary_*.md 2>/dev/null | head -n1)
if [ -n "$LATEST_REPORT" ] && [ -f "$LATEST_REPORT" ]; then
    echo -e "${PURPLE}📈 Quick Stats from Generated Report:${NC}"
    
    # Extract some key metrics from the report
    if grep -q "Total Pull Requests:" "$LATEST_REPORT"; then
        PR_COUNT=$(grep "Total Pull Requests:" "$LATEST_REPORT" | sed 's/.*: \*\*//' | sed 's/\*\*.*//')
        echo "• Pull Requests: $PR_COUNT"
    fi
    
    if grep -q "Total Commits:" "$LATEST_REPORT"; then
        COMMIT_COUNT=$(grep "Total Commits:" "$LATEST_REPORT" | sed 's/.*: \*\*//' | sed 's/\*\*.*//')
        echo "• Commits: $COMMIT_COUNT"
    fi
    
    if grep -q "Active Contributors:" "$LATEST_REPORT"; then
        CONTRIBUTOR_COUNT=$(grep "Active Contributors:" "$LATEST_REPORT" | sed 's/.*: \*\*//' | sed 's/\*\*.*//')
        echo "• Active Contributors: $CONTRIBUTOR_COUNT"
    fi
    
    echo ""
fi

echo -e "${GREEN}🎉 Done! Happy analyzing! 🚀${NC}"
