#!/usr/bin/env python3
"""
Unit tests for engineer performance analysis utilities.

Tests cover:
- Weekly date range generation
- Engineer data collection and aggregation
- Trend analysis algorithms
- Coaching insights generation
- Performance metric calculations
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from team_reports.utils.engineer_performance import (
    generate_weekly_date_ranges,
    collect_weekly_engineer_data,
    compute_engineer_trends,
    generate_coaching_insights,
    format_weekly_metrics_table,
    _extract_github_engineer_metrics,
    _extract_jira_engineer_metrics,
    _empty_github_metrics,
    _empty_jira_metrics,
    _calculate_trend,
    _is_bot_user,
    _normalize_user_id,
    filter_active_engineers,
    validate_data_quality
)


class TestWeeklyDateRanges(unittest.TestCase):
    """Test weekly date range generation."""
    
    def test_generate_weekly_date_ranges_q2_2025(self):
        """Test generating weekly ranges for Q2 2025."""
        weekly_ranges = generate_weekly_date_ranges(2025, 2)
        
        # Q2 2025 should be April 1 - June 30
        self.assertTrue(len(weekly_ranges) >= 13)  # At least 13 weeks
        self.assertTrue(weekly_ranges[0][0].startswith('2025-'))
        self.assertTrue(weekly_ranges[-1][1].startswith('2025-'))
        
        # Check first and last weeks
        first_week_start = datetime.strptime(weekly_ranges[0][0], '%Y-%m-%d')
        last_week_end = datetime.strptime(weekly_ranges[-1][1], '%Y-%m-%d')
        
        # Should start in March or April (Monday of week containing April 1)
        self.assertIn(first_week_start.month, [3, 4])
        # Should end in June or July (Sunday of week containing June 30)
        self.assertIn(last_week_end.month, [6, 7])
    
    def test_weekly_ranges_are_seven_days_apart(self):
        """Test that weekly ranges are exactly 7 days apart."""
        weekly_ranges = generate_weekly_date_ranges(2025, 1)
        
        for i in range(len(weekly_ranges) - 1):
            current_end = datetime.strptime(weekly_ranges[i][1], '%Y-%m-%d')
            next_start = datetime.strptime(weekly_ranges[i + 1][0], '%Y-%m-%d')
            
            # Next week should start exactly 1 day after current week ends
            self.assertEqual((next_start - current_end).days, 1)
    
    def test_each_week_is_valid_range(self):
        """Test that each week has valid start <= end dates."""
        weekly_ranges = generate_weekly_date_ranges(2025, 3)
        
        for start_str, end_str in weekly_ranges:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
            
            self.assertLessEqual(start_date, end_date)
            self.assertLessEqual((end_date - start_date).days, 6)  # Max 6 days apart


class TestGitHubMetricsExtraction(unittest.TestCase):
    """Test GitHub engineer metrics extraction."""
    
    def test_extract_github_engineer_metrics_basic(self):
        """Test basic GitHub metrics extraction."""
        github_data = {
            'pull_requests': {
                'repo1': [
                    {
                        'user': {'login': 'john.doe'},
                        'merged_at': '2025-04-15T10:00:00Z',
                        'additions': 100,
                        'deletions': 50,
                        'reviews': [
                            {'user': {'login': 'jane.smith'}},
                            {'user': {'login': 'bob.wilson'}}
                        ],
                        'review_comments': [
                            {'user': {'login': 'jane.smith'}},
                            {'user': {'login': 'jane.smith'}},
                            {'user': {'login': 'bob.wilson'}}
                        ]
                    }
                ]
            },
            'commits': {
                'repo1': [
                    {'author': {'login': 'john.doe'}},
                    {'author': {'login': 'john.doe'}},
                    {'author': {'login': 'jane.smith'}}
                ]
            }
        }
        
        config = {'bots': {'patterns': []}}
        metrics = _extract_github_engineer_metrics(github_data, config)
        
        # Check john.doe metrics
        john_metrics = metrics['john.doe']
        self.assertEqual(john_metrics['prs_created'], 1)
        self.assertEqual(john_metrics['prs_merged'], 1)
        self.assertEqual(john_metrics['commits'], 2)
        self.assertEqual(john_metrics['lines_added'], 100)
        self.assertEqual(john_metrics['lines_deleted'], 50)
        
        # Check jane.smith metrics (reviewer)
        jane_metrics = metrics['jane.smith']
        self.assertEqual(jane_metrics['prs_created'], 0)
        self.assertEqual(jane_metrics['commits'], 1)
        self.assertEqual(jane_metrics['reviews_given'], 1)
        self.assertEqual(jane_metrics['comments_given'], 2)
    
    def test_extract_github_metrics_empty_data(self):
        """Test GitHub metrics extraction with empty data."""
        github_data = {'pull_requests': {}, 'commits': {}}
        config = {'bots': {'patterns': []}}
        
        metrics = _extract_github_engineer_metrics(github_data, config)
        self.assertEqual(metrics, {})
    
    def test_empty_github_metrics_structure(self):
        """Test empty GitHub metrics structure."""
        empty = _empty_github_metrics()
        
        expected_keys = [
            'prs_created', 'prs_merged', 'commits', 'lines_added', 'lines_deleted',
            'reviews_given', 'reviews_received', 'comments_given', 'comments_received'
        ]
        
        for key in expected_keys:
            self.assertIn(key, empty)
            self.assertEqual(empty[key], 0)


class TestJiraMetricsExtraction(unittest.TestCase):
    """Test Jira engineer metrics extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_ticket_completed = Mock()
        self.mock_ticket_completed.fields.assignee.emailAddress = 'john.doe@company.com'
        self.mock_ticket_completed.fields.status.name = 'Done'
        
        self.mock_ticket_in_progress = Mock()
        self.mock_ticket_in_progress.fields.assignee.emailAddress = 'jane.smith@company.com'
        self.mock_ticket_in_progress.fields.status.name = 'In Progress'
        
        self.config = {
            'team_members': {
                'john.doe@company.com': 'John Doe',
                'jane.smith@company.com': 'Jane Smith'
            },
            'status_filters': {
                'completed': ['Done', 'Closed']
            },
            'states': {
                'active': ['In Progress', 'Review'],
                'in_progress': 'In Progress'
            }
        }
    
    def test_extract_jira_engineer_metrics_basic(self):
        """Test basic Jira metrics extraction."""
        tickets = [self.mock_ticket_completed, self.mock_ticket_in_progress]
        
        with patch('utils.jira.compute_cycle_time_days', return_value=2.5):
            metrics = _extract_jira_engineer_metrics(
                tickets, '2025-04-01', '2025-04-07', self.config, Mock()
            )
        
        # Check john.doe metrics (completed ticket)
        john_metrics = metrics['john.doe@company.com']
        self.assertEqual(john_metrics['tickets_completed'], 1)
        self.assertEqual(john_metrics['current_wip'], 0)
        self.assertEqual(john_metrics['avg_cycle_time'], 2.5)
        
        # Check jane.smith metrics (in progress ticket)
        jane_metrics = metrics['jane.smith@company.com']
        self.assertEqual(jane_metrics['tickets_completed'], 0)
        self.assertEqual(jane_metrics['current_wip'], 1)
        self.assertEqual(jane_metrics['avg_cycle_time'], 0.0)
    
    def test_extract_jira_metrics_unassigned_ticket(self):
        """Test Jira metrics extraction with unassigned ticket."""
        mock_unassigned = Mock()
        mock_unassigned.fields.assignee = None
        mock_unassigned.fields.status.name = 'Done'
        
        metrics = _extract_jira_engineer_metrics(
            [mock_unassigned], '2025-04-01', '2025-04-07', self.config, Mock()
        )
        
        self.assertEqual(metrics, {})
    
    def test_empty_jira_metrics_structure(self):
        """Test empty Jira metrics structure."""
        empty = _empty_jira_metrics()
        
        expected_keys = ['tickets_completed', 'current_wip', 'cycle_times', 'avg_cycle_time']
        
        for key in expected_keys:
            self.assertIn(key, empty)
        
        self.assertEqual(empty['tickets_completed'], 0)
        self.assertEqual(empty['current_wip'], 0)
        self.assertEqual(empty['cycle_times'], [])
        self.assertEqual(empty['avg_cycle_time'], 0.0)


class TestTrendAnalysis(unittest.TestCase):
    """Test trend analysis algorithms."""
    
    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing pattern."""
        series = [1, 2, 3, 5, 6, 8]  # Clear increasing trend
        trend = _calculate_trend(series)
        self.assertEqual(trend, "increasing")
    
    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing pattern."""
        series = [8, 6, 5, 3, 2, 1]  # Clear decreasing trend
        trend = _calculate_trend(series)
        self.assertEqual(trend, "decreasing")
    
    def test_calculate_trend_stable(self):
        """Test trend calculation for stable pattern."""
        series = [3, 4, 3, 4, 3, 4]  # Stable pattern
        trend = _calculate_trend(series)
        self.assertEqual(trend, "stable")
    
    def test_calculate_trend_with_zeros(self):
        """Test trend calculation handling zero values."""
        series = [0, 0, 1, 2, 3, 4]  # Should ignore zeros
        trend = _calculate_trend(series)
        self.assertEqual(trend, "increasing")
    
    def test_calculate_trend_insufficient_data(self):
        """Test trend calculation with insufficient data."""
        series = [1, 2]  # Too few points
        trend = _calculate_trend(series)
        self.assertEqual(trend, "stable")
    
    def test_compute_engineer_trends_basic(self):
        """Test complete engineer trends computation."""
        engineer_data = {
            'john.doe': {
                'weeks': {
                    '2025-04-07': {
                        'github': {'prs_merged': 1, 'commits': 2, 'reviews_given': 1, 'lines_added': 50, 'lines_deleted': 10},
                        'jira': {'tickets_completed': 2}
                    },
                    '2025-04-14': {
                        'github': {'prs_merged': 2, 'commits': 3, 'reviews_given': 2, 'lines_added': 100, 'lines_deleted': 20},
                        'jira': {'tickets_completed': 3}
                    },
                    '2025-04-21': {
                        'github': {'prs_merged': 3, 'commits': 4, 'reviews_given': 3, 'lines_added': 150, 'lines_deleted': 30},
                        'jira': {'tickets_completed': 4}
                    }
                }
            }
        }
        
        trends = compute_engineer_trends(engineer_data)
        
        john_trends = trends['john.doe']
        self.assertEqual(john_trends['productivity_trend'], 'increasing')
        self.assertEqual(john_trends['collaboration_trend'], 'increasing')
        self.assertEqual(john_trends['velocity_trend'], 'increasing')
        
        # Check weekly totals
        weekly_totals = john_trends['weekly_totals']
        self.assertEqual(weekly_totals['total_prs'], 6)  # 1+2+3
        self.assertEqual(weekly_totals['total_tickets'], 9)  # 2+3+4
        self.assertEqual(weekly_totals['avg_prs_per_week'], 2.0)  # 6/3
        self.assertEqual(weekly_totals['avg_tickets_per_week'], 3.0)  # 9/3


class TestCoachingInsights(unittest.TestCase):
    """Test coaching insights generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            'coaching': {
                'min_prs_per_week': 1.0,
                'max_wip_threshold': 3,
                'min_review_participation': 0.5,
                'productivity_concern_weeks': 3
            }
        }
        
        self.engineer_data = {
            'low.performer': {
                'weeks': {
                    '2025-04-07': {
                        'github': {'prs_merged': 0, 'reviews_given': 0, 'reviews_received': 2},
                        'jira': {'current_wip': 5, 'tickets_completed': 0}  # Added missing field
                    },
                    '2025-04-14': {
                        'github': {'prs_merged': 0, 'reviews_given': 0, 'reviews_received': 1},
                        'jira': {'current_wip': 4, 'tickets_completed': 0}  # Added missing field
                    }
                },
                'total_weeks': 2
            },
            'good.performer': {
                'weeks': {
                    '2025-04-07': {
                        'github': {'prs_merged': 2, 'reviews_given': 3, 'reviews_received': 2},
                        'jira': {'current_wip': 2, 'tickets_completed': 2}  # Added missing field
                    },
                    '2025-04-14': {
                        'github': {'prs_merged': 3, 'reviews_given': 2, 'reviews_received': 1},
                        'jira': {'current_wip': 1, 'tickets_completed': 3}  # Added missing field
                    }
                },
                'total_weeks': 2
            }
        }
        
        self.trends = {
            'low.performer': {
                'productivity_trend': 'decreasing',
                'weekly_totals': {'avg_prs_per_week': 0.0}
            },
            'good.performer': {
                'productivity_trend': 'increasing',
                'weekly_totals': {'avg_prs_per_week': 2.5}
            }
        }
    
    def test_generate_coaching_insights_low_performer(self):
        """Test coaching insights for low performer."""
        insights = generate_coaching_insights(self.engineer_data, self.trends, self.config)
        
        low_performer_insights = insights['low.performer']
        
        # Should flag multiple issues
        self.assertTrue(len(low_performer_insights) > 0)
        
        # Check for specific insight types
        insight_text = ' '.join(low_performer_insights)
        self.assertIn('Low PR output', insight_text)
        self.assertIn('Not participating in code reviews', insight_text)
        self.assertIn('High WIP levels', insight_text)
        self.assertIn('Productivity trend decreasing', insight_text)
    
    def test_generate_coaching_insights_good_performer(self):
        """Test coaching insights for good performer."""
        insights = generate_coaching_insights(self.engineer_data, self.trends, self.config)
        
        good_performer_insights = insights['good.performer']
        
        # Should have minimal or positive insights
        insight_text = ' '.join(good_performer_insights)
        if insight_text:
            self.assertIn('increasing', insight_text.lower())  # Positive trend
    
    def test_coaching_insights_empty_data(self):
        """Test coaching insights with empty data."""
        insights = generate_coaching_insights({}, {}, self.config)
        self.assertEqual(insights, {})


class TestWeeklyMetricsTable(unittest.TestCase):
    """Test weekly metrics table formatting."""
    
    def test_format_weekly_metrics_table_basic(self):
        """Test basic weekly metrics table formatting."""
        engineer_data = {
            'weeks': {
                '2025-04-07': {
                    'github': {'prs_merged': 1, 'commits': 2, 'reviews_given': 1, 'lines_added': 50, 'lines_deleted': 10},
                    'jira': {'tickets_completed': 2}
                },
                '2025-04-14': {
                    'github': {'prs_merged': 2, 'commits': 3, 'reviews_given': 2, 'lines_added': 100, 'lines_deleted': 20},
                    'jira': {'tickets_completed': 3}
                }
            }
        }
        
        trends = {
            'productivity_trend': 'increasing',
            'collaboration_trend': 'stable',
            'velocity_trend': 'increasing'
        }
        
        table = format_weekly_metrics_table('john.doe', engineer_data, trends)
        
        # Check table structure
        self.assertIn('| Metric |', table)
        self.assertIn('Week 1', table)
        self.assertIn('Week 2', table)
        self.assertIn('Trend |', table)
        
        # Check metrics are present
        self.assertIn('PRs Merged', table)
        self.assertIn('Commits', table)
        self.assertIn('Tickets Done', table)
        self.assertIn('Reviews Given', table)
        self.assertIn('Lines Changed', table)
        
        # Check trend indicators
        self.assertIn('📈 increasing', table)
        self.assertIn('➡️ stable', table)
    
    def test_format_weekly_metrics_table_empty_weeks(self):
        """Test table formatting with empty weeks."""
        engineer_data = {'weeks': {}}
        trends = {}
        
        table = format_weekly_metrics_table('john.doe', engineer_data, trends)
        
        # Should still have basic structure
        self.assertIn('| Metric |', table)
        self.assertIn('Trend |', table)


class TestEngineerPerformanceIntegration(unittest.TestCase):
    """Integration tests for engineer performance analysis."""
    
    @patch('utils.engineer_performance.GitHubApiClient')
    @patch('utils.engineer_performance.JiraApiClient')
    @patch('utils.engineer_performance.get_config')
    def test_collect_weekly_engineer_data_integration(self, mock_get_config, mock_jira_client_class, mock_github_client_class):
        """Test end-to-end weekly data collection."""
        # Mock GitHub client
        mock_github_client = Mock()
        mock_github_client.fetch_all_data.return_value = {
            'pull_requests': {
                'repo1': [
                    {
                        'user': {'login': 'john.doe'},
                        'merged_at': '2025-04-15T10:00:00Z',
                        'additions': 100,
                        'deletions': 50
                    }
                ]
            },
            'commits': {
                'repo1': [
                    {'author': {'login': 'john.doe'}}
                ]
            }
        }
        mock_github_client_class.return_value = mock_github_client
        
        # Mock Jira client
        mock_jira_client = Mock()
        mock_ticket = Mock()
        mock_ticket.fields.assignee.emailAddress = 'john.doe@company.com'
        mock_ticket.fields.status.name = 'Done'
        mock_jira_client.fetch_tickets.return_value = [mock_ticket]
        mock_jira_client_class.return_value = mock_jira_client
        
        config = {
            'team_members': {
                'john.doe@company.com': 'John Doe'
            },
            'status_filters': {
                'completed': ['Done']
            },
            'states': {
                'active': ['In Progress']
            }
        }
        
        # Mock get_config to return our test config
        mock_get_config.return_value = config
        
        # This would be a long-running test in reality, so we'll mock the weekly ranges
        with patch('utils.engineer_performance.generate_weekly_date_ranges', 
                  return_value=[('2025-04-07', '2025-04-13')]):
            
            engineer_data = collect_weekly_engineer_data(2025, 2, 'mock_jira_config.yaml', 'mock_github_config.yaml')
            
            # Verify structure
            self.assertIn('john.doe', engineer_data)
            self.assertIn('weeks', engineer_data['john.doe'])
            self.assertIn('2025-04-07', engineer_data['john.doe']['weeks'])
            
            week_data = engineer_data['john.doe']['weeks']['2025-04-07']
            self.assertIn('github', week_data)
            self.assertIn('jira', week_data)


class TestBotDetection(unittest.TestCase):
    """Test bot detection and filtering functionality."""
    
    def test_is_bot_user_basic_patterns(self):
        """Test basic bot detection patterns."""
        config = {
            'bots': {
                'patterns': ['.*bot.*', 'konflux-.*', 'dependabot']
            }
        }
        
        # Should detect bots
        self.assertTrue(_is_bot_user('github-bot', config))
        self.assertTrue(_is_bot_user('konflux-internal-p02', config))
        self.assertTrue(_is_bot_user('dependabot', config))
        self.assertTrue(_is_bot_user('sourcery-ai[bot]', config))
        
        # Should not detect regular users
        self.assertFalse(_is_bot_user('john.doe', config))
        self.assertFalse(_is_bot_user('jane.smith@company.com', config))
        self.assertFalse(_is_bot_user('mirekdlugosz', config))
    
    def test_is_bot_user_case_insensitive(self):
        """Test that bot detection is case insensitive."""
        config = {
            'bots': {
                'patterns': ['.*BOT.*']
            }
        }
        
        self.assertTrue(_is_bot_user('GitHub-Bot', config))
        self.assertTrue(_is_bot_user('github-bot', config))
        self.assertTrue(_is_bot_user('GITHUB-BOT', config))
    
    def test_is_bot_user_empty_patterns(self):
        """Test bot detection with empty patterns."""
        config = {'bots': {'patterns': []}}
        
        self.assertFalse(_is_bot_user('any-user', config))
        self.assertFalse(_is_bot_user('github-bot', config))
    
    def test_is_bot_user_invalid_regex(self):
        """Test bot detection handles invalid regex gracefully."""
        config = {
            'bots': {
                'patterns': ['[invalid', '.*bot.*']  # First pattern is invalid regex
            }
        }
        
        # Should still work with valid patterns
        self.assertTrue(_is_bot_user('github-bot', config))
        self.assertFalse(_is_bot_user('john.doe', config))
    
    def test_normalize_user_id_bot_filtering(self):
        """Test that _normalize_user_id filters out bots."""
        config = {
            'bots': {
                'patterns': ['.*bot.*', 'konflux-.*']
            },
            'user_mapping': {
                'github_to_jira': {
                    'john.doe': 'john.doe@company.com'
                }
            }
        }
        
        # Regular users should be normalized
        self.assertEqual(_normalize_user_id('john.doe', 'github', config), 'john.doe@company.com')
        self.assertEqual(_normalize_user_id('jane@company.com', 'jira', config), 'jane@company.com')
        
        # Bots should return None
        self.assertIsNone(_normalize_user_id('github-bot', 'github', config))
        self.assertIsNone(_normalize_user_id('konflux-internal-p02', 'github', config))
        self.assertIsNone(_normalize_user_id('sourcery-ai[bot]', 'jira', config))
    
    def test_normalize_user_id_cross_system_mapping(self):
        """Test cross-system user identity mapping."""
        config = {
            'bots': {'patterns': []},
            'user_mapping': {
                'github_to_jira': {
                    'infinitewarp': 'brasmith@redhat.com',
                    'nicolearagao': 'naragao@redhat.com',
                    'mirekdlugosz': 'mzalewsk@redhat.com'
                }
            }
        }
        
        # GitHub users should map to Jira emails
        self.assertEqual(_normalize_user_id('infinitewarp', 'github', config), 'brasmith@redhat.com')
        self.assertEqual(_normalize_user_id('nicolearagao', 'github', config), 'naragao@redhat.com')
        self.assertEqual(_normalize_user_id('mirekdlugosz', 'github', config), 'mzalewsk@redhat.com')
        
        # Unmapped GitHub users should remain unchanged
        self.assertEqual(_normalize_user_id('unknown-user', 'github', config), 'unknown-user')
        
        # Jira users should remain unchanged (canonical form)
        self.assertEqual(_normalize_user_id('brasmith@redhat.com', 'jira', config), 'brasmith@redhat.com')


class TestActiveEngineerFiltering(unittest.TestCase):
    """Test filtering of active engineers based on activity thresholds."""
    
    def test_filter_active_engineers_basic(self):
        """Test basic active engineer filtering."""
        engineer_data = {
            'high.activity': {'weeks': {}},
            'medium.activity': {'weeks': {}},
            'low.activity': {'weeks': {}}
        }
        
        trends = {
            'high.activity': {'weekly_totals': {'total_prs': 5, 'total_tickets': 8}},
            'medium.activity': {'weekly_totals': {'total_prs': 2, 'total_tickets': 1}},
            'low.activity': {'weekly_totals': {'total_prs': 0, 'total_tickets': 1}}
        }
        
        active_engineers = filter_active_engineers(engineer_data, trends)
        
        # Should include engineers with ≥1 PR OR ≥3 tickets
        self.assertIn('high.activity', active_engineers)  # 5 PRs, 8 tickets
        self.assertIn('medium.activity', active_engineers)  # 2 PRs, 1 ticket (≥1 PR)
        self.assertNotIn('low.activity', active_engineers)  # 0 PRs, 1 ticket (below threshold)
    
    def test_filter_active_engineers_edge_cases(self):
        """Test edge cases for active engineer filtering."""
        engineer_data = {
            'exactly.one.pr': {'weeks': {}},
            'exactly.three.tickets': {'weeks': {}},
            'zero.activity': {'weeks': {}}
        }
        
        trends = {
            'exactly.one.pr': {'weekly_totals': {'total_prs': 1, 'total_tickets': 0}},
            'exactly.three.tickets': {'weekly_totals': {'total_prs': 0, 'total_tickets': 3}},
            'zero.activity': {'weekly_totals': {'total_prs': 0, 'total_tickets': 0}}
        }
        
        active_engineers = filter_active_engineers(engineer_data, trends)
        
        # Should include engineers at threshold boundaries
        self.assertIn('exactly.one.pr', active_engineers)
        self.assertIn('exactly.three.tickets', active_engineers)
        self.assertNotIn('zero.activity', active_engineers)


class TestDataQualityValidation(unittest.TestCase):
    """Test data quality validation against official benchmarks."""
    
    def test_validate_data_quality_perfect_match(self):
        """Test validation with perfect data alignment."""
        engineer_data = {
            'eng1': {'weeks': {}},
            'eng2': {'weeks': {}},
            'eng3': {'weeks': {}},
            'eng4': {'weeks': {}},
            'eng5': {'weeks': {}},
            'eng6': {'weeks': {}},
            'eng7': {'weeks': {}},
            'eng8': {'weeks': {}}
        }
        
        trends = {
            'eng1': {'weekly_totals': {'total_prs': 12, 'total_tickets': 13}},
            'eng2': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng3': {'weekly_totals': {'total_prs': 10, 'total_tickets': 11}},
            'eng4': {'weekly_totals': {'total_prs': 10, 'total_tickets': 10}},
            'eng5': {'weekly_totals': {'total_prs': 9, 'total_tickets': 10}},
            'eng6': {'weekly_totals': {'total_prs': 8, 'total_tickets': 9}},
            'eng7': {'weekly_totals': {'total_prs': 8, 'total_tickets': 8}},
            'eng8': {'weekly_totals': {'total_prs': 24, 'total_tickets': 33}}  # Total: 92 PRs, 106 tickets
        }
        
        validation = validate_data_quality(engineer_data, trends)
        
        # Should show perfect alignment
        self.assertEqual(validation['computed_totals']['prs'], 92)
        self.assertEqual(validation['computed_totals']['tickets'], 106)
        self.assertEqual(validation['computed_totals']['contributors'], 8)
        
        self.assertTrue(validation['validation_status']['pr_accuracy'])
        self.assertTrue(validation['validation_status']['ticket_accuracy'])
        self.assertTrue(validation['validation_status']['contributor_count_valid'])
        self.assertTrue(validation['validation_status']['overall_valid'])
        
        self.assertEqual(validation['variance_percentages']['prs'], 0.0)
        self.assertEqual(validation['variance_percentages']['tickets'], 0.0)
    
    def test_validate_data_quality_with_variance(self):
        """Test validation with acceptable variance."""
        engineer_data = {
            'eng1': {'weeks': {}},
            'eng2': {'weeks': {}},
            'eng3': {'weeks': {}},
            'eng4': {'weeks': {}},
            'eng5': {'weeks': {}},
            'eng6': {'weeks': {}},
            'eng7': {'weeks': {}},
            'eng8': {'weeks': {}},
            'eng9': {'weeks': {}}  # 9 contributors (within range)
        }
        
        trends = {
            'eng1': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng2': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng3': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng4': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng5': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng6': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng7': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng8': {'weekly_totals': {'total_prs': 11, 'total_tickets': 12}},
            'eng9': {'weekly_totals': {'total_prs': 7, 'total_tickets': 10}}  # Total: 95 PRs, 106 tickets
        }
        
        validation = validate_data_quality(engineer_data, trends)
        
        # Should show small acceptable variance
        self.assertEqual(validation['computed_totals']['prs'], 95)  # 8*11 + 7 = 95
        self.assertEqual(validation['computed_totals']['tickets'], 106)  # 8*12 + 10 = 106
        self.assertEqual(validation['computed_totals']['contributors'], 9)
        
        # 95 vs 92 = 3.3% variance (within 5%)
        # 106 vs 106 = 0% variance (within 5%)
        self.assertTrue(validation['validation_status']['pr_accuracy'])  # Within 5%
        self.assertTrue(validation['validation_status']['ticket_accuracy'])  # Exact match
        self.assertTrue(validation['validation_status']['contributor_count_valid'])
        self.assertTrue(validation['validation_status']['overall_valid'])  # All passed
    
    def test_validate_data_quality_excessive_variance(self):
        """Test validation with excessive variance."""
        engineer_data = {
            'eng1': {'weeks': {}},
            'eng2': {'weeks': {}},
            'eng3': {'weeks': {}},
            'eng4': {'weeks': {}},
            'eng5': {'weeks': {}},
            'eng6': {'weeks': {}},
            'eng7': {'weeks': {}},
            'eng8': {'weeks': {}},
            'eng9': {'weeks': {}},
            'eng10': {'weeks': {}},
            'eng11': {'weeks': {}},
            'eng12': {'weeks': {}}  # 12 contributors (outside range)
        }
        
        trends = {
            'eng1': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng2': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng3': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng4': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng5': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng6': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng7': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng8': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng9': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng10': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng11': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}},
            'eng12': {'weekly_totals': {'total_prs': 15, 'total_tickets': 15}}  # Total: 180 PRs, 180 tickets
        }
        
        validation = validate_data_quality(engineer_data, trends)
        
        # Should show excessive variance
        self.assertEqual(validation['computed_totals']['prs'], 180)
        self.assertEqual(validation['computed_totals']['tickets'], 180)
        self.assertEqual(validation['computed_totals']['contributors'], 12)
        
        # 180 vs 92 = 95.7% variance (way over 5%)
        # 180 vs 106 = 69.8% variance (way over 5%)
        self.assertFalse(validation['validation_status']['pr_accuracy'])
        self.assertFalse(validation['validation_status']['ticket_accuracy'])
        self.assertFalse(validation['validation_status']['contributor_count_valid'])
        self.assertFalse(validation['validation_status']['overall_valid'])


if __name__ == '__main__':
    unittest.main()
