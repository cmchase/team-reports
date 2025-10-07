#!/bin/bash

# GitHub Quarterly Summary Runner
# Generates quarterly reports from GitHub repositories with error handling and setup

set -e  # Exit on any error

echo "🚀 GitHub Quarterly Summary Generator"
echo "====================================="

# Check if we're in the right directory
if [ ! -f "github_quarterly_summary.py" ]; then
    echo "❌ Error: github_quarterly_summary.py not found in current directory"
    echo "Please run this script from the team-reports directory"
    exit 1
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check for required dependencies
echo "📦 Checking dependencies..."
python -c "import requests, yaml, dotenv" 2>/dev/null || {
    echo "❌ Error: Missing required dependencies"
    echo "Installing dependencies..."
    pip install requests PyYAML python-dotenv
}

# Check for GitHub token
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please create .env file with your GitHub token:"
    echo "  GITHUB_TOKEN=your_personal_access_token_here"
    echo ""
    echo "To create a GitHub token:"
    echo "  1. Go to GitHub Settings > Developer settings > Personal access tokens"
    echo "  2. Generate new token with 'repo' and 'read:org' permissions"
    echo "  3. Add it to .env file"
    exit 1
fi

# Verify GitHub token exists in .env
if ! grep -q "GITHUB_TOKEN" .env; then
    echo "❌ Error: GITHUB_TOKEN not found in .env file"
    echo "Please add your GitHub token to .env file:"
    echo "  GITHUB_TOKEN=your_personal_access_token_here"
    exit 1
fi

# Check for configuration file
CONFIG_FILE="config/github_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "github_config_example.yaml" ]; then
        echo "⚠️  Warning: config/github_config.yaml not found"
        echo "Creating config/github_config.yaml from example file..."
        cp config/github_config_example.yaml config/github_config.yaml
        echo "✅ Created config/github_config.yaml"
        echo "Please edit config/github_config.yaml to configure your repositories and team members"
        echo ""
    else
        echo "❌ Error: No GitHub configuration file found"
        echo "Please create config/github_config.yaml with your repository and team configuration"
        exit 1
    fi
fi

# Create Reports directory if it doesn't exist
if [ ! -d "Reports" ]; then
    echo "📁 Creating Reports directory..."
    mkdir Reports
fi

# Parse command line arguments
YEAR=""
QUARTER=""
CUSTOM_CONFIG=""

if [ $# -ge 2 ]; then
    YEAR=$1
    QUARTER=$2
    if [ $# -ge 3 ]; then
        CUSTOM_CONFIG=$3
    fi
fi

# Run the GitHub quarterly summary
echo "🚀 Generating GitHub quarterly summary..."
echo ""

if [ -n "$CUSTOM_CONFIG" ]; then
    echo "📝 Using custom config: $CUSTOM_CONFIG"
    python github_quarterly_summary.py "$YEAR" "$QUARTER" "$CUSTOM_CONFIG"
elif [ -n "$YEAR" ] && [ -n "$QUARTER" ]; then
    echo "📅 Generating report for Q$QUARTER $YEAR"
    python github_quarterly_summary.py "$YEAR" "$QUARTER"
else
    echo "📅 Generating report for current quarter"
    python github_quarterly_summary.py
fi

echo ""
echo "✅ GitHub quarterly summary generation complete!"
echo ""
echo "📊 Report saved in Reports/ directory"
echo "🔍 Check the generated .md file for detailed contributor analysis"

# Deactivate virtual environment
deactivate
