#!/bin/bash

# =============================================================================
# Quarterly Team Summary Script
# =============================================================================
# 
# This script generates quarterly team summaries from Jira data, providing
# comprehensive analysis of team performance, trends, and insights.
#
# Usage:
#   ./run_quarterly_summary.sh                    # Current quarter
#   ./run_quarterly_summary.sh 2025 4            # Specific quarter  
#   ./run_quarterly_summary.sh 2025 4 config.yaml # With custom config
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

# Default values
YEAR=""
QUARTER=""
CONFIG_FILE="team_config.yaml"
VIRTUAL_ENV_PATH="./venv"
PYTHON_SCRIPT="quarterly_team_summary.py"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${PURPLE}===============================================================================${NC}"
    echo -e "${PURPLE}                    📊 QUARTERLY TEAM SUMMARY GENERATOR${NC}"
    echo -e "${PURPLE}===============================================================================${NC}"
    echo ""
}

print_usage() {
    echo -e "${CYAN}Usage:${NC}"
    echo "  $0                           # Generate for current quarter"
    echo "  $0 2025 4                    # Generate for Q4 2025"  
    echo "  $0 2025 4 custom_config.yaml # Use custom config file"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  $0                           # Current quarter with default config"
    echo "  $0 2025 1                    # Q1 2025 report"
    echo "  $0 2025 3 team_config.yaml  # Q3 2025 with specific config"
    echo ""
}

print_error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check if Python script exists
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        print_error "Python script '$PYTHON_SCRIPT' not found!"
        echo "Please ensure you're running this script from the project root directory."
        exit 1
    fi
    
    # Check for virtual environment
    if [[ ! -d "$VIRTUAL_ENV_PATH" ]]; then
        print_warning "Virtual environment not found at '$VIRTUAL_ENV_PATH'"
        print_info "Attempting to use system Python..."
        PYTHON_CMD="python3"
    else
        print_success "Virtual environment found"
        PYTHON_CMD="$VIRTUAL_ENV_PATH/bin/python"
    fi
    
    # Check if Python is available
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        print_error "Python not found! Please install Python 3.7+ or set up the virtual environment."
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_info "Using Python $PYTHON_VERSION"
    
    # Check if required packages are installed
    print_info "Checking required packages..."
    if ! $PYTHON_CMD -c "import jira, yaml, dotenv" 2>/dev/null; then
        print_warning "Some required packages may be missing"
        print_info "If you encounter import errors, run: pip install -r requirements.txt"
    fi
}

validate_quarter() {
    if [[ -n "$QUARTER" ]] && [[ ! "$QUARTER" =~ ^[1-4]$ ]]; then
        print_error "Quarter must be 1, 2, 3, or 4. Got: $QUARTER"
        exit 1
    fi
    
    if [[ -n "$YEAR" ]] && [[ ! "$YEAR" =~ ^[0-9]{4}$ ]]; then
        print_error "Year must be a 4-digit number. Got: $YEAR"
        exit 1
    fi
}

check_config_file() {
    print_info "Checking configuration..."
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "Configuration file '$CONFIG_FILE' not found!"
        echo ""
        echo "Please create a configuration file. You can:"
        echo "1. Copy team_config_example.yaml to $CONFIG_FILE"
        echo "2. Follow the CONFIGURATION_GUIDE.md for setup instructions"
        exit 1
    fi
    
    print_success "Configuration file found: $CONFIG_FILE"
}

check_environment() {
    print_info "Checking environment setup..."
    
    # Check for .env file or environment variables
    if [[ ! -f ".env" ]]; then
        print_warning ".env file not found"
        print_info "Make sure JIRA connection environment variables are set:"
        print_info "  - JIRA_SERVER, JIRA_USERNAME, JIRA_API_TOKEN"
    else
        print_success "Environment file found"
    fi
    
    # Check if Reports directory exists
    if [[ ! -d "Reports" ]]; then
        print_info "Creating Reports directory..."
        mkdir -p Reports
        print_success "Reports directory created"
    fi
}

generate_quarterly_summary() {
    print_info "Starting quarterly summary generation..."
    echo ""
    
    # Build command arguments
    CMD_ARGS=()
    
    if [[ -n "$YEAR" && -n "$QUARTER" ]]; then
        CMD_ARGS+=("$YEAR" "$QUARTER")
        print_info "Generating summary for Q$QUARTER $YEAR"
    else
        print_info "Generating summary for current quarter"
    fi
    
    if [[ "$CONFIG_FILE" != "team_config.yaml" ]]; then
        CMD_ARGS+=("$CONFIG_FILE")
        print_info "Using config file: $CONFIG_FILE"
    fi
    
    # Run the Python script
    print_info "Executing: $PYTHON_CMD $PYTHON_SCRIPT ${CMD_ARGS[*]}"
    echo ""
    
    if $PYTHON_CMD "$PYTHON_SCRIPT" "${CMD_ARGS[@]}"; then
        echo ""
        print_success "Quarterly summary generated successfully!"
        
        # Show reports directory contents
        echo ""
        print_info "Reports available in ./Reports/:"
        ls -la Reports/ | grep -E "\.(md|pdf|html)$" || print_info "No report files found"
        
    else
        print_error "Failed to generate quarterly summary"
        echo ""
        echo "Common troubleshooting steps:"
        echo "1. Check your .env file and JIRA credentials"
        echo "2. Verify your team_config.yaml is properly formatted"
        echo "3. Ensure you have network access to your JIRA instance"
        echo "4. Check that the date range contains valid tickets"
        exit 1
    fi
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    print_header
    
    # Parse command line arguments
    case $# in
        0)
            # Use current quarter
            ;;
        1)
            if [[ "$1" == "-h" || "$1" == "--help" ]]; then
                print_usage
                exit 0
            fi
            print_error "Invalid number of arguments"
            print_usage
            exit 1
            ;;
        2)
            YEAR="$1"
            QUARTER="$2"
            ;;
        3)
            YEAR="$1"
            QUARTER="$2"
            CONFIG_FILE="$3"
            ;;
        *)
            print_error "Too many arguments"
            print_usage
            exit 1
            ;;
    esac
    
    # Validate inputs
    validate_quarter
    
    # Run all checks
    check_dependencies
    check_config_file
    check_environment
    
    # Show configuration summary
    echo ""
    print_info "Configuration Summary:"
    echo "  📅 Quarter: ${QUARTER:-'Current'}"
    echo "  📅 Year: ${YEAR:-'Current'}"
    echo "  📋 Config: $CONFIG_FILE"
    echo "  🐍 Python: $PYTHON_CMD"
    echo ""
    
    # Generate the report
    generate_quarterly_summary
    
    print_success "Quarterly summary generation complete!"
}

# =============================================================================
# Script Execution
# =============================================================================

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}⚠️  Operation cancelled by user${NC}"; exit 130' INT

# Run main function
main "$@"
