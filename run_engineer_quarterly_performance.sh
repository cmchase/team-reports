#!/bin/bash

# Engineer Quarterly Performance Report Generator
#
# MODERN CLI: This script is maintained for backwards compatibility.
# New usage: team-reports [jira|github|engineer] [weekly|quarterly|performance] [OPTIONS]
# Example: team-reports jira weekly
#
# Usage: ./run_engineer_quarterly_performance.sh [year] [quarter] [config_file]
# Examples:
#   ./run_engineer_quarterly_performance.sh 2025 2
#   ./run_engineer_quarterly_performance.sh  # Uses current quarter
#   ./run_engineer_quarterly_performance.sh 2025 2 config/custom_jira_config.yaml

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Engineer Quarterly Performance Report Generator${NC}"
echo "=================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Check if required packages are installed
echo -e "${YELLOW}🔍 Checking dependencies...${NC}"
python3 -c "import jira, dotenv, yaml" 2>/dev/null || {
    echo -e "${RED}❌ Missing required packages. Please install dependencies:${NC}"
    echo "pip install -r requirements.txt"
    exit 1
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found. Make sure environment variables are set.${NC}"
fi

# Run the engineer quarterly performance script
echo -e "${GREEN}📊 Generating engineer quarterly performance report...${NC}"
python3 engineer_quarterly_performance.py "$@"

# Check if the script was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Engineer quarterly performance report generated successfully!${NC}"
    echo -e "${BLUE}📁 Check the Reports/ directory for your report file.${NC}"
else
    echo -e "${RED}❌ Failed to generate engineer quarterly performance report.${NC}"
    exit 1
fi
