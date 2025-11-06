#!/usr/bin/env python3
"""
Shared GitHub API client for eliminating code duplication.

This module provides a centralized GitHub API client that can be shared
between weekly summaries, quarterly summaries, and lead time analysis.
"""

import os
import requests
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

from .config import get_config

# Load environment variables
load_dotenv()


class GitHubApiClient:
    """Centralized GitHub API client with common operations."""
    
    def __init__(
        self,
        config_file: str = 'config/github_config.yaml',
        github_token: Optional[str] = None
    ):
        """
        Initialize the GitHub API client with configuration.
        
        Credential Precedence (highest to lowest):
            1. github_token parameter
            2. GITHUB_TOKEN environment variable
            3. .env file (loaded via python-dotenv)
        
        Args:
            config_file: Path to YAML configuration file
            github_token: Optional GitHub API token (overrides environment)
        
        Raises:
            ValueError: If GitHub token is not provided via parameter or environment
        """
        # Load GitHub token with precedence: parameter > environment
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError(
                "GitHub token required. Provide via github_token parameter or "
                "GITHUB_TOKEN environment variable"
            )
        
        # Load configuration
        self.config = get_config([config_file])
        
        # Extract commonly used config values
        self.repositories = self.config.get('repositories', [])
        self.github_org = self.config.get('github_org', '')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Make a request to GitHub API with pagination support."""
        url = f"{self.base_url}/{endpoint}"
        all_data = []
        page = 1
        
        while True:
            request_params = {'page': page, 'per_page': 100}
            if params:
                request_params.update(params)
            
            response = requests.get(url, headers=self.headers, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
                
            all_data.extend(data)
            page += 1
            
            # GitHub API returns less than per_page if it's the last page
            if len(data) < 100:
                break
        
        return all_data
    
    def _fetch_pr_details(self, repo: str, pr_number: int) -> Dict:
        """Fetch detailed information for a specific pull request."""
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        
        # Add small delay to avoid hitting rate limits
        time.sleep(0.1)
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        pr_data = response.json()
        return {
            'additions': pr_data.get('additions', 0),
            'deletions': pr_data.get('deletions', 0),
            'changed_files': pr_data.get('changed_files', 0)
        }
    
    def _fetch_pr_reviews(self, repo: str, pr_number: int) -> List[Dict]:
        """Fetch reviews for a specific pull request."""
        endpoint = f"repos/{repo}/pulls/{pr_number}/reviews"
        
        # Add small delay to avoid hitting rate limits
        time.sleep(0.1)
        
        try:
            return self._make_request(endpoint)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not fetch reviews for PR #{pr_number}: {e}")
            return []
    
    def _fetch_pr_review_comments(self, repo: str, pr_number: int) -> List[Dict]:
        """Fetch review comments for a specific pull request."""
        endpoint = f"repos/{repo}/pulls/{pr_number}/comments"
        
        # Add small delay to avoid hitting rate limits
        time.sleep(0.1)
        
        try:
            return self._make_request(endpoint)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not fetch review comments for PR #{pr_number}: {e}")
            return []
    
    def _fetch_commits_from_merged_prs(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch commits from PRs that were merged in the date range."""
        repo_path = self._build_repo_path(repo)
        
        # Get PRs that were merged in the date range
        endpoint = f"repos/{repo_path}/pulls"
        params = {
            'state': 'closed',
            'sort': 'updated',
            'direction': 'desc'
        }
        
        prs = self._make_request(endpoint, params)
        
        # Filter for PRs merged in the date range
        start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        
        merged_prs = []
        for pr in prs:
            if pr.get('merged_at'):
                merged_at = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                if start_dt <= merged_at <= end_dt:
                    merged_prs.append(pr)
        
        # Fetch commits from each merged PR
        all_commits = []
        for pr in merged_prs:
            try:
                pr_commits_endpoint = f"repos/{repo_path}/pulls/{pr['number']}/commits"
                time.sleep(0.1)  # Rate limiting
                pr_commits = self._make_request(pr_commits_endpoint)
                all_commits.extend(pr_commits)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not fetch commits for merged PR #{pr['number']}: {e}")
        
        return all_commits
    
    def _build_repo_path(self, repo: str) -> str:
        """Build full repository path with organization if configured."""
        return f"{self.github_org}/{repo}" if self.github_org else repo
    
    def fetch_pull_requests(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch pull requests for a repository in the date range with detailed information."""
        print(f"🔍 Fetching pull requests for {repo} from {start_date} to {end_date}...")
        
        repo_path = self._build_repo_path(repo)
        endpoint = f"repos/{repo_path}/pulls"
        params = {
            'state': 'all',  # Get open, closed, and merged PRs
            'since': start_date,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        prs = self._make_request(endpoint, params)
        
        # Filter by date range (GitHub API doesn't support date range filtering directly)
        filtered_prs = []
        for pr in prs:
            updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
            end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
            
            if start_dt <= updated_at <= end_dt:
                # Only include merged PRs for delivery reports
                if not pr.get('merged_at'):
                    continue  # Skip unmerged PRs
                
                # Check if the PR was actually merged in the date range  
                merged_at = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                if not (start_dt <= merged_at <= end_dt):
                    continue  # Skip PRs merged outside date range
                
                # Fetch detailed PR info for code metrics
                try:
                    detailed_pr = self._fetch_pr_details(repo_path, pr['number'])
                    pr.update(detailed_pr)
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not fetch details for PR #{pr['number']}: {e}")
                    pr['additions'] = 0
                    pr['deletions'] = 0
                    pr['changed_files'] = 0

                # Fetch reviews and review comments if review_depth is enabled
                if self.config.get('metrics', {}).get('delivery', {}).get('review_depth', False):
                    pr['reviews'] = self._fetch_pr_reviews(repo_path, pr['number'])
                    pr['review_comments'] = self._fetch_pr_review_comments(repo_path, pr['number'])
                else:
                    pr['reviews'] = []
                    pr['review_comments'] = []

                filtered_prs.append(pr)
        
        return filtered_prs
    
    def fetch_commits(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch commits for a repository in the date range."""
        print(f"🔍 Fetching commits for {repo} from {start_date} to {end_date}...")
        
        repo_path = self._build_repo_path(repo)
        endpoint = f"repos/{repo_path}/commits"
        params = {
            'since': f"{start_date}T00:00:00Z",
            'until': f"{end_date}T23:59:59Z"
        }
        
        # Fetch commits by commit date
        commits_by_date = self._make_request(endpoint, params)
        
        # Also fetch commits from merged PRs in the date range (even if commit dates are outside range)
        commits_from_prs = self._fetch_commits_from_merged_prs(repo, start_date, end_date)
        
        # Combine and deduplicate commits by SHA
        all_commits = commits_by_date.copy()
        existing_shas = {commit['sha'] for commit in commits_by_date}
        
        for commit in commits_from_prs:
            if commit['sha'] not in existing_shas:
                all_commits.append(commit)
                existing_shas.add(commit['sha'])
        
        print(f"  📊 Found {len(commits_by_date)} commits by date, {len(commits_from_prs)} from merged PRs, {len(all_commits)} total")
        return all_commits
    
    def fetch_issues(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch issues for a repository in the date range."""
        print(f"🔍 Fetching issues for {repo} from {start_date} to {end_date}...")
        
        repo_path = self._build_repo_path(repo)
        endpoint = f"repos/{repo_path}/issues"
        params = {
            'state': 'all',
            'since': f"{start_date}T00:00:00Z",
            'sort': 'updated',
            'direction': 'desc'
        }
        
        issues = self._make_request(endpoint, params)
        
        # Filter out pull requests (GitHub API includes PRs in issues) and by date range
        filtered_issues = []
        for issue in issues:
            if 'pull_request' not in issue:
                updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
                end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
                
                if start_dt <= updated_at <= end_dt:
                    filtered_issues.append(issue)
        
        return filtered_issues
    
    def fetch_all_data(self, start_date: str, end_date: str) -> Dict[str, Dict[str, List[Dict]]]:
        """Fetch all GitHub data for the specified date range."""
        all_data = {
            'pull_requests': {},
            'commits': {},
            'issues': {}
        }
        
        print(f"🚀 Fetching GitHub data for {len(self.repositories)} repositories...")
        
        for repo in self.repositories:
            repo_path = self._build_repo_path(repo)
            print(f"\n📁 Processing repository: {repo}")
            
            try:
                all_data['pull_requests'][repo_path] = self.fetch_pull_requests(repo, start_date, end_date)
                all_data['commits'][repo_path] = self.fetch_commits(repo, start_date, end_date)
                all_data['issues'][repo_path] = self.fetch_issues(repo, start_date, end_date)
                
                pr_count = len(all_data['pull_requests'][repo_path])
                commit_count = len(all_data['commits'][repo_path])
                issue_count = len(all_data['issues'][repo_path])
                
                print(f"  ✅ Found: {pr_count} PRs, {commit_count} commits, {issue_count} issues")
                
            except Exception as e:
                print(f"  ❌ Error fetching data for {repo}: {e}")
                all_data['pull_requests'][repo_path] = []
                all_data['commits'][repo_path] = []
                all_data['issues'][repo_path] = []
        
        return all_data
    
    def get_merged_prs_for_lead_time(self, start_date: str, end_date: str, 
                                   all_prs_data: Optional[Dict[str, List[Dict]]] = None) -> List[Dict]:
        """
        Get merged PRs for lead time analysis, using pre-fetched data if available.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format  
            all_prs_data: Optional pre-fetched PR data to avoid duplicate API calls
            
        Returns:
            List of merged PRs with detailed information
        """
        if all_prs_data:
            print("✅ Using pre-fetched PR data (optimized)")
            # Collect all merged PRs from pre-fetched data
            all_prs = []
            for repo_path, prs in all_prs_data.items():
                for pr in prs:
                    if pr.get('merged_at'):
                        merged_date = pr['merged_at'][:10]  # Extract YYYY-MM-DD
                        if start_date <= merged_date <= end_date:
                            all_prs.append(pr)
            return all_prs
        else:
            print("⚠️  Making fresh API calls (not optimized)")
            # Fallback: reuse existing fetch_all_data method to avoid duplication
            all_data = self.fetch_all_data(start_date, end_date)
            
            # Extract merged PRs from the fetched data
            all_prs = []
            for repo_path, prs in all_data['pull_requests'].items():
                for pr in prs:
                    if pr.get('merged_at'):
                        merged_date = pr['merged_at'][:10]  # Extract YYYY-MM-DD
                        if start_date <= merged_date <= end_date:
                            all_prs.append(pr)
            
            return all_prs
