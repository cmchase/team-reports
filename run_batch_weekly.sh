#!/bin/bash
# Batch Weekly Report Generator
# Generate multiple weekly reports efficiently for Jira or GitHub data sources
#
# MODERN CLI: This script is maintained for backwards compatibility.
# New usage: team-reports [jira|github|engineer] [weekly|quarterly|performance] [OPTIONS]
# Example: team-reports jira weekly
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATCH_HELPER="$SCRIPT_DIR/utils/batch_runner.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_help() {
    echo "Batch Weekly Report Generator"
    echo "============================="
    echo ""
    echo "Generate multiple weekly reports efficiently for Jira or GitHub data sources"
    echo ""
    echo "Usage:"
    echo "  $0 [report_type] [option] [config_file]"
    echo ""
    echo "Report Types:"
    echo "  jira         Generate Jira weekly reports"
    echo "  github       Generate GitHub weekly reports"
    echo ""
    echo "Options:"
    echo "  last-N       Generate reports for the last N weeks (e.g., last-4)"
    echo "  YYYY-MM-DD:N Generate N weekly reports starting from date (e.g., 2025-09-01:6)"
    echo "  YYYY-MM-DD to YYYY-MM-DD  Generate reports between two dates (weekly intervals)"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 jira last-4                           # Last 4 Jira weekly reports"
    echo "  $0 github 2025-09-01:6                   # 6 GitHub weekly reports from Sep 1st"
    echo "  $0 jira 2025-09-01 to 2025-10-20         # Jira reports between dates"
    echo "  $0 github last-3 config/custom_github_config.yaml  # GitHub with custom config"
    echo ""
    exit 0
}

# Function to validate report type
validate_report_type() {
    local report_type="$1"
    case "$report_type" in
        "jira"|"github")
            return 0
            ;;
        *)
            echo -e "${RED}❌ Invalid report type: $report_type${NC}"
            echo -e "Supported types: jira, github"
            return 1
            ;;
    esac
}

# Function to get the appropriate script for report type
get_report_script() {
    local report_type="$1"
    case "$report_type" in
        "jira")
            echo "$SCRIPT_DIR/jira_weekly_summary.py"
            ;;
        "github")
            echo "$SCRIPT_DIR/github_weekly_summary.py"
            ;;
        *)
            echo ""
            return 1
            ;;
    esac
}

# Function to get default config for report type
get_default_config() {
    local report_type="$1"
    case "$report_type" in
        "jira")
            echo "config/jira_config.yaml"
            ;;
        "github")
            echo "config/github_config.yaml"
            ;;
        *)
            echo ""
            return 1
            ;;
    esac
}

# Function to generate a single weekly report
generate_weekly_report() {
    local report_type="$1"
    local start_date="$2"
    local end_date="$3"
    local config_file="$4"
    
    local script=$(get_report_script "$report_type")
    if [[ -z "$script" ]] || [[ ! -f "$script" ]]; then
        echo -e "${RED}❌ Report script not found for type: $report_type${NC}"
        return 1
    fi
    
    echo -e "${BLUE}📅 Generating $report_type report for week: $start_date to $end_date${NC}"
    
    if [[ -n "$config_file" ]] && [[ -f "$config_file" ]]; then
        python3 "$script" "$start_date" "$end_date" "$config_file"
    else
        python3 "$script" "$start_date" "$end_date"
    fi
    
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✅ Report generated successfully${NC}"
    else
        echo -e "${RED}❌ Failed to generate $report_type report for $start_date to $end_date${NC}"
        return 1
    fi
    echo ""
}

# Main script logic
main() {
    # Check if help is requested or no arguments
    if [[ $# -eq 0 ]] || [[ "$1" == "help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        print_help
    fi
    
    # Extract report type
    local report_type="$1"
    shift
    
    # Validate report type
    if ! validate_report_type "$report_type"; then
        exit 1
    fi
    
    # Check if report script exists
    local script=$(get_report_script "$report_type")
    if [[ ! -f "$script" ]]; then
        echo -e "${RED}❌ Report script not found: $script${NC}"
        exit 1
    fi
    
    # Parse remaining arguments using Python helper
    echo -e "${BLUE}🔍 Parsing batch arguments...${NC}"
    local batch_config
    if ! batch_config=$(python3 -c "
import sys
import os
sys.path.insert(0, '$SCRIPT_DIR')
from utils.batch import parse_batch_arguments, generate_weekly_date_ranges, generate_last_n_weeks_ranges, generate_n_weeks_from_date_ranges
import json

try:
    args = sys.argv[1:]
    parsed = parse_batch_arguments(args)
    
    # Generate date ranges based on mode
    if parsed['mode'] == 'last_n':
        ranges = generate_last_n_weeks_ranges(parsed['params']['n'])
    elif parsed['mode'] == 'n_from_date':
        ranges = generate_n_weeks_from_date_ranges(parsed['params']['start_date'], parsed['params']['n'])
    elif parsed['mode'] == 'date_range':
        ranges = generate_weekly_date_ranges(parsed['params']['start_date'], parsed['params']['end_date'])
    else:
        raise ValueError('Unknown mode: ' + str(parsed['mode']))
    
    # Output results
    result = {
        'ranges': ranges,
        'config_file': parsed['config_file']
    }
    print(json.dumps(result))
    
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" "$@"); then
        echo -e "${RED}❌ Failed to parse arguments${NC}"
        exit 1
    fi
    
    # Parse JSON output
    local ranges=$(echo "$batch_config" | python3 -c "import sys, json; data=json.load(sys.stdin); [print(f'{r[0]} {r[1]}') for r in data['ranges']]")
    local config_file=$(echo "$batch_config" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['config_file'] or '')")
    
    # Use default config if none specified
    if [[ -z "$config_file" ]]; then
        config_file=$(get_default_config "$report_type")
        if [[ -f "$config_file" ]]; then
            echo -e "${BLUE}📝 Using default config: $config_file${NC}"
        fi
    else
        echo -e "${BLUE}📝 Using custom config: $config_file${NC}"
    fi
    
    # Count total reports
    local total_reports=$(echo "$ranges" | wc -l)
    echo -e "${YELLOW}🚀 Generating $total_reports $report_type weekly reports${NC}"
    printf '=%.0s' {1..60}; echo
    echo ""
    
    # Generate reports
    local report_count=0
    local failed_count=0
    
    while IFS= read -r range_line; do
        if [[ -n "$range_line" ]]; then
            local start_date=$(echo "$range_line" | cut -d' ' -f1)
            local end_date=$(echo "$range_line" | cut -d' ' -f2)
            
            if generate_weekly_report "$report_type" "$start_date" "$end_date" "$config_file"; then
                report_count=$((report_count + 1))
            else
                failed_count=$((failed_count + 1))
            fi
        fi
    done <<< "$ranges"
    
    # Summary
    echo -e "${GREEN}🎉 Batch complete!${NC}"
    echo -e "📊 Generated: ${GREEN}$report_count${NC} reports"
    if [[ $failed_count -gt 0 ]]; then
        echo -e "❌ Failed: ${RED}$failed_count${NC} reports"
    fi
    echo ""
}

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is required but not installed${NC}"
    exit 1
fi

# Check if Python utils are available
if ! python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from utils.batch import parse_batch_arguments" 2>/dev/null; then
    echo -e "${RED}❌ Batch utilities not found. Ensure utils/batch.py is present.${NC}"
    exit 1
fi

# Run main function
main "$@"