"""
Unit tests for GitHub utilities and PR lead time calculations.

Tests the compute_pr_lead_time_hours function and related PR analysis
functionality for delivery metrics.
"""

import pytest
from datetime import datetime, timezone
from utils.github import (
    compute_pr_lead_time_hours,
    compute_pr_lead_time_stats,
    is_trivial_pr,
    format_lead_time_duration,
    is_bot_user,
    compute_pr_review_depth,
    compute_review_depth_stats
)


class TestPRLeadTime:
    """Test PR lead time calculation functionality"""
    
    def test_compute_pr_lead_time_hours_basic(self):
        """Test basic PR lead time calculation"""
        pr_data = {
            'merged_at': '2025-01-15T16:30:00Z',
            'created_at': '2025-01-14T10:15:00Z'
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        
        # Should be approximately 30.25 hours (30 hours 15 minutes)
        assert lead_time is not None
        assert 30.0 < lead_time < 31.0
    
    def test_compute_pr_lead_time_hours_not_merged(self):
        """Test that non-merged PRs return None"""
        pr_data = {
            'merged_at': None,
            'created_at': '2025-01-14T10:15:00Z'
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        assert lead_time is None
    
    def test_compute_pr_lead_time_hours_missing_created_at(self):
        """Test handling of missing created_at"""
        pr_data = {
            'merged_at': '2025-01-15T16:30:00Z'
            # missing created_at
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        assert lead_time is None
    
    def test_compute_pr_lead_time_hours_same_time(self):
        """Test PR merged at creation time (edge case)"""
        pr_data = {
            'merged_at': '2025-01-15T16:30:00Z',
            'created_at': '2025-01-15T16:30:00Z'
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        
        # Should be 0 hours
        assert lead_time == 0.0
    
    def test_compute_pr_lead_time_hours_negative_time(self):
        """Test handling of negative lead time (data issue)"""
        pr_data = {
            'merged_at': '2025-01-14T10:15:00Z',  # Before created_at
            'created_at': '2025-01-15T16:30:00Z'
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        
        # Should return None for negative lead time
        assert lead_time is None
    
    def test_compute_pr_lead_time_hours_invalid_date_format(self):
        """Test handling of invalid date formats"""
        pr_data = {
            'merged_at': 'invalid-date',
            'created_at': '2025-01-14T10:15:00Z'
        }
        
        lead_time = compute_pr_lead_time_hours(pr_data)
        assert lead_time is None


class TestPRLeadTimeStats:
    """Test PR lead time statistics computation"""
    
    def test_compute_pr_lead_time_stats_basic(self):
        """Test basic statistics computation with multiple PRs"""
        prs = [
            {
                'number': 1,
                'title': 'Fix bug A',
                'user': {'login': 'user1'},
                'html_url': 'https://github.com/repo/pull/1',
                'merged_at': '2025-01-15T16:30:00Z',
                'created_at': '2025-01-15T14:30:00Z',  # 2 hours
                'additions': 10,
                'deletions': 5
            },
            {
                'number': 2,
                'title': 'Add feature B',
                'user': {'login': 'user2'},
                'html_url': 'https://github.com/repo/pull/2',
                'merged_at': '2025-01-16T12:00:00Z',
                'created_at': '2025-01-15T12:00:00Z',  # 24 hours
                'additions': 50,
                'deletions': 10
            },
            {
                'number': 3,
                'title': 'Update docs',
                'user': {'login': 'user3'},
                'html_url': 'https://github.com/repo/pull/3',
                'merged_at': '2025-01-17T08:00:00Z',
                'created_at': '2025-01-16T20:00:00Z',  # 12 hours
                'additions': 20,
                'deletions': 2
            }
        ]
        
        stats = compute_pr_lead_time_stats(prs, min_lines_changed=5)
        
        assert stats['count'] == 3
        assert stats['avg'] == pytest.approx((2 + 24 + 12) / 3, rel=0.1)
        assert stats['median'] == 12.0  # Middle value
        assert len(stats['fastest']) <= 5
        assert len(stats['slowest']) <= 5
        assert len(stats['all_prs']) == 3
    
    def test_compute_pr_lead_time_stats_trivial_pr_filtered(self):
        """Test that trivial PRs are filtered out"""
        prs = [
            {
                'number': 1,
                'title': 'Fix typo',
                'user': {'login': 'user1'},
                'html_url': 'https://github.com/repo/pull/1',
                'merged_at': '2025-01-15T16:30:00Z',
                'created_at': '2025-01-15T14:30:00Z',
                'additions': 1,  # Only 3 lines total (below threshold)
                'deletions': 2
            },
            {
                'number': 2,
                'title': 'Major refactor',
                'user': {'login': 'user2'},
                'html_url': 'https://github.com/repo/pull/2',
                'merged_at': '2025-01-16T12:00:00Z',
                'created_at': '2025-01-15T12:00:00Z',
                'additions': 100,  # 110 lines total (above threshold)
                'deletions': 10
            }
        ]
        
        stats = compute_pr_lead_time_stats(prs, min_lines_changed=5)
        
        # Only the second PR should be included
        assert stats['count'] == 1
        assert len(stats['all_prs']) == 1
        assert stats['all_prs'][0]['number'] == 2
    
    def test_compute_pr_lead_time_stats_no_merged_prs(self):
        """Test handling of no merged PRs"""
        prs = [
            {
                'number': 1,
                'title': 'Open PR',
                'user': {'login': 'user1'},
                'html_url': 'https://github.com/repo/pull/1',
                'merged_at': None,  # Not merged
                'created_at': '2025-01-15T14:30:00Z',
                'additions': 10,
                'deletions': 5
            }
        ]
        
        stats = compute_pr_lead_time_stats(prs, min_lines_changed=5)
        
        assert stats['count'] == 0
        assert stats['avg'] == 0
        assert stats['median'] == 0
        assert stats['p90'] == 0
        assert len(stats['fastest']) == 0
        assert len(stats['slowest']) == 0
    
    def test_compute_pr_lead_time_stats_empty_list(self):
        """Test handling of empty PR list"""
        prs = []
        
        stats = compute_pr_lead_time_stats(prs, min_lines_changed=5)
        
        assert stats['count'] == 0
        assert stats['avg'] == 0
        assert len(stats['all_prs']) == 0


class TestTrivialPRFiltering:
    """Test trivial PR identification"""
    
    def test_is_trivial_pr_below_threshold(self):
        """Test PR below threshold is considered trivial"""
        pr = {
            'additions': 2,
            'deletions': 1
            # Total: 3 lines, below default threshold of 5
        }
        
        assert is_trivial_pr(pr) is True
    
    def test_is_trivial_pr_above_threshold(self):
        """Test PR above threshold is not trivial"""
        pr = {
            'additions': 10,
            'deletions': 5
            # Total: 15 lines, above default threshold of 5
        }
        
        assert is_trivial_pr(pr) is False
    
    def test_is_trivial_pr_custom_threshold(self):
        """Test PR filtering with custom threshold"""
        pr = {
            'additions': 8,
            'deletions': 2
            # Total: 10 lines
        }
        
        # With threshold 15, this should be trivial
        assert is_trivial_pr(pr, min_lines_threshold=15) is True
        
        # With threshold 5, this should not be trivial
        assert is_trivial_pr(pr, min_lines_threshold=5) is False
    
    def test_is_trivial_pr_missing_fields(self):
        """Test handling of missing additions/deletions fields"""
        pr = {}  # Missing both fields
        
        # Should default to 0 + 0 = 0, which is below any reasonable threshold
        assert is_trivial_pr(pr) is True


class TestLeadTimeDurationFormatting:
    """Test lead time duration formatting"""
    
    def test_format_lead_time_duration_hours(self):
        """Test formatting for durations less than a day"""
        assert format_lead_time_duration(2.5) == "2.5h"
        assert format_lead_time_duration(0.5) == "0.5h"
        assert format_lead_time_duration(23.9) == "23.9h"
    
    def test_format_lead_time_duration_days(self):
        """Test formatting for durations in days"""
        assert format_lead_time_duration(24.0) == "1d"
        assert format_lead_time_duration(48.0) == "2d"
        assert format_lead_time_duration(72.0) == "3d"
    
    def test_format_lead_time_duration_days_and_hours(self):
        """Test formatting for durations with days and hours"""
        assert format_lead_time_duration(26.5) == "1d 2.5h"
        assert format_lead_time_duration(50.2) == "2d 2.2h"
        assert format_lead_time_duration(169.3) == "7d 1.3h"
    
    def test_format_lead_time_duration_exact_days(self):
        """Test formatting for exact day durations"""
        assert format_lead_time_duration(48.0) == "2d"
        assert format_lead_time_duration(120.0) == "5d"


class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_full_pr_analysis_workflow(self):
        """Test complete workflow from PR data to statistics"""
        # Sample PR data with mixed lead times and sizes
        prs = [
            {
                'number': 1,
                'title': 'Quick fix',
                'user': {'login': 'developer1'},
                'html_url': 'https://github.com/org/repo/pull/1',
                'merged_at': '2025-01-15T14:00:00Z',
                'created_at': '2025-01-15T12:00:00Z',  # 2 hours - fast
                'additions': 3,
                'deletions': 1  # 4 lines - trivial, should be filtered
            },
            {
                'number': 2,
                'title': 'Feature implementation',
                'user': {'login': 'developer2'},
                'html_url': 'https://github.com/org/repo/pull/2',
                'merged_at': '2025-01-16T18:00:00Z',
                'created_at': '2025-01-15T18:00:00Z',  # 24 hours - medium
                'additions': 100,
                'deletions': 20  # 120 lines - substantial
            },
            {
                'number': 3,
                'title': 'Complex refactor',
                'user': {'login': 'developer3'},
                'html_url': 'https://github.com/org/repo/pull/3',
                'merged_at': '2025-01-18T12:00:00Z',
                'created_at': '2025-01-15T12:00:00Z',  # 72 hours - slow
                'additions': 200,
                'deletions': 50  # 250 lines - large
            },
            {
                'number': 4,
                'title': 'Documentation update',
                'user': {'login': 'developer1'},
                'html_url': 'https://github.com/org/repo/pull/4',
                'merged_at': '2025-01-17T09:00:00Z',
                'created_at': '2025-01-16T21:00:00Z',  # 12 hours - fast-medium
                'additions': 15,
                'deletions': 5  # 20 lines - moderate
            }
        ]
        
        # Analyze with default threshold (5 lines)
        stats = compute_pr_lead_time_stats(prs, min_lines_changed=5)
        
        # Verify trivial PR was filtered out
        assert stats['count'] == 3  # PR #1 should be excluded
        
        # Verify statistics make sense
        assert stats['median'] == 24.0  # Middle of 12, 24, 72
        assert stats['avg'] == pytest.approx((12 + 24 + 72) / 3, rel=0.1)
        
        # Verify fastest/slowest ordering
        fastest_pr = stats['fastest'][0]
        assert fastest_pr['number'] == 4  # 12 hours
        assert fastest_pr['lead_time_hours'] == 12.0
        
        slowest_pr = stats['slowest'][0]
        assert slowest_pr['number'] == 3  # 72 hours
        assert slowest_pr['lead_time_hours'] == 72.0
        
        # Verify all PRs are properly formatted
        for pr_info in stats['all_prs']:
            assert 'number' in pr_info
            assert 'author' in pr_info
            assert 'lead_time_hours' in pr_info
            assert 'additions' in pr_info
            assert 'deletions' in pr_info


class TestBotExclusion:
    """Test bot user identification and exclusion"""
    
    def test_is_bot_user_matches_patterns(self):
        """Test that bot patterns correctly identify bot users"""
        bot_patterns = ['.*bot.*', 'dependabot', 'github-actions.*']
        
        # Test bot users that should match
        assert is_bot_user('dependabot[bot]', bot_patterns) is True
        assert is_bot_user('github-actions[bot]', bot_patterns) is True
        assert is_bot_user('renovate-bot', bot_patterns) is True
        assert is_bot_user('codecov-bot', bot_patterns) is True
        assert is_bot_user('my-custom-bot', bot_patterns) is True
        
        # Test regular users that should not match
        assert is_bot_user('john-doe', bot_patterns) is False
        assert is_bot_user('alice-smith', bot_patterns) is False
        assert is_bot_user('developer1', bot_patterns) is False
    
    def test_is_bot_user_case_insensitive(self):
        """Test that bot pattern matching is case insensitive"""
        bot_patterns = ['DEPENDABOT', '.*BOT.*']
        
        assert is_bot_user('dependabot[bot]', bot_patterns) is True
        assert is_bot_user('DependaBot', bot_patterns) is True
        assert is_bot_user('my-bot-service', bot_patterns) is True
        assert is_bot_user('MY-BOT-SERVICE', bot_patterns) is True
    
    def test_is_bot_user_empty_patterns(self):
        """Test behavior with empty bot patterns"""
        assert is_bot_user('dependabot[bot]', []) is False
        assert is_bot_user('regular-user', []) is False
    
    def test_is_bot_user_empty_username(self):
        """Test behavior with empty or None username"""
        bot_patterns = ['.*bot.*']
        
        assert is_bot_user('', bot_patterns) is False
        assert is_bot_user(None, bot_patterns) is False
    
    def test_is_bot_user_invalid_regex(self):
        """Test handling of invalid regex patterns"""
        # Invalid regex pattern with unmatched bracket
        bot_patterns = ['[invalid-regex', '.*bot.*']
        
        # Should still work for valid patterns, skip invalid ones
        assert is_bot_user('my-bot', bot_patterns) is True
        assert is_bot_user('regular-user', bot_patterns) is False


class TestReviewDepth:
    """Test PR review depth calculation functionality"""
    
    def test_compute_pr_review_depth_basic(self):
        """Test basic review depth calculation"""
        config = {
            'bots': {'patterns': ['.*bot.*', 'dependabot']}
        }
        
        pr_data = {
            'reviews': [
                {'user': {'login': 'reviewer1'}},
                {'user': {'login': 'reviewer2'}},
                {'user': {'login': 'dependabot[bot]'}},  # Should be excluded
                {'user': {'login': 'reviewer1'}}  # Duplicate, should count as 1 reviewer
            ],
            'review_comments': [
                {'user': {'login': 'reviewer1'}},
                {'user': {'login': 'reviewer1'}},
                {'user': {'login': 'reviewer2'}},
                {'user': {'login': 'code-bot'}},  # Should be excluded
                {'user': {'login': 'reviewer3'}}
            ]
        }
        
        result = compute_pr_review_depth(pr_data, config)
        
        # Should have 2 unique reviewers (reviewer1, reviewer2) - dependabot excluded
        assert result['reviewers_count'] == 2
        # Should have 4 comments - code-bot comment excluded
        assert result['review_comments_count'] == 4
    
    def test_compute_pr_review_depth_no_bots_config(self):
        """Test review depth calculation with no bot patterns configured"""
        config = {}  # No bots configuration
        
        pr_data = {
            'reviews': [
                {'user': {'login': 'reviewer1'}},
                {'user': {'login': 'dependabot[bot]'}}  # Should be included when no bot patterns
            ],
            'review_comments': [
                {'user': {'login': 'reviewer1'}},
                {'user': {'login': 'dependabot[bot]'}}
            ]
        }
        
        result = compute_pr_review_depth(pr_data, config)
        
        # Should include all users when no bot patterns configured
        assert result['reviewers_count'] == 2
        assert result['review_comments_count'] == 2
    
    def test_compute_pr_review_depth_empty_data(self):
        """Test review depth calculation with empty review data"""
        config = {'bots': {'patterns': ['.*bot.*']}}
        
        pr_data = {
            'reviews': [],
            'review_comments': []
        }
        
        result = compute_pr_review_depth(pr_data, config)
        
        assert result['reviewers_count'] == 0
        assert result['review_comments_count'] == 0
    
    def test_compute_pr_review_depth_missing_data(self):
        """Test review depth calculation with missing review data"""
        config = {'bots': {'patterns': ['.*bot.*']}}
        
        pr_data = {}  # Missing reviews and review_comments keys
        
        result = compute_pr_review_depth(pr_data, config)
        
        assert result['reviewers_count'] == 0
        assert result['review_comments_count'] == 0


class TestReviewDepthStats:
    """Test review depth statistics computation"""
    
    def test_compute_review_depth_stats_basic(self):
        """Test basic review depth statistics computation"""
        config = {'bots': {'patterns': ['.*bot.*']}}
        
        prs = [
            {
                'merged_at': '2025-01-15T16:30:00Z',
                'reviews': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer2'}}
                ],
                'review_comments': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer2'}}
                ]
            },
            {
                'merged_at': '2025-01-16T12:00:00Z',
                'reviews': [
                    {'user': {'login': 'reviewer3'}}
                ],
                'review_comments': [
                    {'user': {'login': 'reviewer3'}}
                ]
            },
            {
                'merged_at': '2025-01-17T08:00:00Z',
                'reviews': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer2'}},
                    {'user': {'login': 'reviewer3'}}
                ],
                'review_comments': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer2'}},
                    {'user': {'login': 'reviewer3'}},
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'reviewer2'}}
                ]
            }
        ]
        
        stats = compute_review_depth_stats(prs, config)
        
        assert stats['count'] == 3
        
        # Reviewer counts: [2, 1, 3] -> median = 2.0
        assert stats['median_reviewers'] == 2.0
        assert stats['avg_reviewers'] == pytest.approx(2.0, rel=0.1)
        
        # Comment counts: [3, 1, 5] -> median = 3.0
        assert stats['median_comments'] == 3.0
        assert stats['avg_comments'] == pytest.approx(3.0, rel=0.1)
    
    def test_compute_review_depth_stats_filters_non_merged(self):
        """Test that non-merged PRs are filtered out"""
        config = {'bots': {'patterns': []}}
        
        prs = [
            {
                'merged_at': '2025-01-15T16:30:00Z',  # Merged PR
                'reviews': [{'user': {'login': 'reviewer1'}}],
                'review_comments': [{'user': {'login': 'reviewer1'}}]
            },
            {
                'merged_at': None,  # Not merged - should be excluded
                'reviews': [{'user': {'login': 'reviewer2'}}],
                'review_comments': [{'user': {'login': 'reviewer2'}}]
            }
        ]
        
        stats = compute_review_depth_stats(prs, config)
        
        # Only the merged PR should be counted
        assert stats['count'] == 1
        assert stats['median_reviewers'] == 1.0
        assert stats['median_comments'] == 1.0
    
    def test_compute_review_depth_stats_empty_prs(self):
        """Test handling of empty PR list"""
        config = {'bots': {'patterns': []}}
        
        stats = compute_review_depth_stats([], config)
        
        assert stats['count'] == 0
        assert stats['median_reviewers'] == 0.0
        assert stats['median_comments'] == 0.0
        assert stats['avg_reviewers'] == 0.0
        assert stats['avg_comments'] == 0.0
    
    def test_compute_review_depth_stats_excludes_bots(self):
        """Test that bot users are properly excluded from statistics"""
        config = {'bots': {'patterns': ['.*bot.*', 'dependabot']}}
        
        prs = [
            {
                'merged_at': '2025-01-15T16:30:00Z',
                'reviews': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'dependabot[bot]'}},  # Should be excluded
                    {'user': {'login': 'reviewer2'}}
                ],
                'review_comments': [
                    {'user': {'login': 'reviewer1'}},
                    {'user': {'login': 'codecov-bot'}},  # Should be excluded
                    {'user': {'login': 'reviewer2'}},
                    {'user': {'login': 'reviewer2'}}
                ]
            }
        ]
        
        stats = compute_review_depth_stats(prs, config)
        
        assert stats['count'] == 1
        # Should have 2 reviewers (excluding dependabot)
        assert stats['median_reviewers'] == 2.0
        # Should have 3 comments (excluding codecov-bot)
        assert stats['median_comments'] == 3.0
