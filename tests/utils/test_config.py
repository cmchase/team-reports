#!/usr/bin/env python3
"""
Unit tests for utils.config module

Tests all configuration utility functions with various scenarios and edge cases.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
import yaml
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from team_reports.utils.config import (
    load_config,
    validate_config_structure,
    validate_team_categories,
    get_config_value,
    merge_configs,
    get_default_config,
    save_config,
    load_config_with_defaults,
    get_team_member_name,
    get_all_team_member_emails,
    get_team_members_dict
)


class TestLoadConfig:
    """Test load_config function with various scenarios."""
    
    @patch('builtins.open', new_callable=mock_open, read_data="""
base_jql: "project = TEST"
team_categories:
  Backend:
    components: ["API"]
    description: "Backend work"
""")
    @patch('utils.config.yaml.safe_load')
    def test_load_config_success(self, mock_yaml_load, mock_file):
        """Test successful config loading."""
        expected_config = {
            'base_jql': 'project = TEST',
            'team_categories': {
                'Backend': {
                    'components': ['API'],
                    'description': 'Backend work'
                }
            }
        }
        mock_yaml_load.return_value = expected_config
        
        config = load_config('test_config.yaml')
        
        mock_file.assert_called_once_with('test_config.yaml', 'r')
        mock_yaml_load.assert_called_once()
        assert config == expected_config
    
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_config_file_not_found(self, mock_file):
        """Test behavior when config file is not found."""
        with pytest.raises(SystemExit) as exc_info:
            load_config('nonexistent.yaml')
        
        assert exc_info.value.code == 1
        mock_file.assert_called_once_with('nonexistent.yaml', 'r')
    
    @patch('builtins.open', new_callable=mock_open, read_data="invalid: yaml: content:")
    @patch('utils.config.yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML"))
    def test_load_config_yaml_error(self, mock_yaml_load, mock_file):
        """Test behavior when YAML parsing fails."""
        with pytest.raises(SystemExit) as exc_info:
            load_config('invalid.yaml')
        
        assert exc_info.value.code == 1


class TestValidateConfigStructure:
    """Test validate_config_structure function."""
    
    def test_validate_all_keys_present(self):
        """Test validation when all required keys are present."""
        config = {
            'base_jql': 'test',
            'team_categories': {},
            'report_settings': {}
        }
        required_keys = ['base_jql', 'team_categories']
        
        result = validate_config_structure(config, required_keys)
        
        assert result is True
    
    def test_validate_missing_keys(self):
        """Test validation when required keys are missing."""
        config = {
            'base_jql': 'test'
        }
        required_keys = ['base_jql', 'team_categories', 'report_settings']
        
        result = validate_config_structure(config, required_keys)
        
        assert result is False
    
    def test_validate_empty_required_keys(self):
        """Test validation with empty required keys list."""
        config = {'any': 'value'}
        required_keys = []
        
        result = validate_config_structure(config, required_keys)
        
        assert result is True
    
    def test_validate_empty_config(self):
        """Test validation with empty config."""
        config = {}
        required_keys = ['base_jql']
        
        result = validate_config_structure(config, required_keys)
        
        assert result is False


class TestValidateTeamCategories:
    """Test validate_team_categories function."""
    
    def test_validate_valid_team_categories(self):
        """Test validation with valid team categories structure."""
        team_categories = {
            'Backend': {
                'components': ['API', 'Database'],
                'keywords': ['backend', 'service'],
                'description': 'Backend development'
            },
            'Frontend': {
                'components': ['UI'],
                'projects': ['WEB'],
                'description': 'Frontend development'
            }
        }
        
        result = validate_team_categories(team_categories)
        
        assert result is True
    
    def test_validate_missing_description(self):
        """Test validation when description is missing."""
        team_categories = {
            'Backend': {
                'components': ['API']
                # Missing description
            }
        }
        
        result = validate_team_categories(team_categories)
        
        assert result is False
    
    def test_validate_empty_team_categories(self):
        """Test validation with empty team categories."""
        team_categories = {}
        
        result = validate_team_categories(team_categories)
        
        assert result is True  # Empty is considered valid


class TestGetConfigValue:
    """Test get_config_value function."""
    
    def test_get_top_level_value(self):
        """Test getting top-level configuration value."""
        config = {
            'base_jql': 'project = TEST',
            'debug': True
        }
        
        value = get_config_value(config, 'base_jql')
        
        assert value == 'project = TEST'
    
    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        config = {
            'report_settings': {
                'max_results': 100,
                'order_by': 'updated DESC'
            }
        }
        
        value = get_config_value(config, 'report_settings.max_results')
        
        assert value == 100
    
    def test_get_deep_nested_value(self):
        """Test getting deeply nested configuration value."""
        config = {
            'team_categories': {
                'Backend': {
                    'settings': {
                        'priority': 'high'
                    }
                }
            }
        }
        
        value = get_config_value(config, 'team_categories.Backend.settings.priority')
        
        assert value == 'high'
    
    def test_get_missing_value_with_default(self):
        """Test getting missing value with default."""
        config = {'existing': 'value'}
        
        value = get_config_value(config, 'missing.key', default='default_value')
        
        assert value == 'default_value'
    
    def test_get_missing_value_without_default(self):
        """Test getting missing value without default."""
        config = {'existing': 'value'}
        
        value = get_config_value(config, 'missing.key')
        
        assert value is None


class TestMergeConfigs:
    """Test merge_configs function."""
    
    def test_merge_non_overlapping_configs(self):
        """Test merging configs with no overlapping keys."""
        base_config = {
            'base_jql': 'test',
            'setting_a': 'value_a'
        }
        override_config = {
            'setting_b': 'value_b',
            'setting_c': 'value_c'
        }
        
        result = merge_configs(base_config, override_config)
        
        expected = {
            'base_jql': 'test',
            'setting_a': 'value_a',
            'setting_b': 'value_b',
            'setting_c': 'value_c'
        }
        assert result == expected
    
    def test_merge_overlapping_configs(self):
        """Test merging configs with overlapping keys (override wins)."""
        base_config = {
            'base_jql': 'original',
            'setting_a': 'original_a',
            'setting_b': 'keep_this'
        }
        override_config = {
            'base_jql': 'overridden',
            'setting_a': 'overridden_a'
        }
        
        result = merge_configs(base_config, override_config)
        
        expected = {
            'base_jql': 'overridden',
            'setting_a': 'overridden_a', 
            'setting_b': 'keep_this'
        }
        assert result == expected
    
    def test_merge_nested_configs(self):
        """Test merging configs with nested dictionaries."""
        base_config = {
            'report_settings': {
                'max_results': 50,
                'format': 'markdown'
            },
            'other': 'value'
        }
        override_config = {
            'report_settings': {
                'max_results': 100,
                'new_setting': True
            }
        }
        
        result = merge_configs(base_config, override_config)
        
        expected = {
            'report_settings': {
                'max_results': 100,
                'format': 'markdown',
                'new_setting': True
            },
            'other': 'value'
        }
        assert result == expected
    
    def test_merge_empty_configs(self):
        """Test merging empty configurations."""
        result = merge_configs({}, {})
        assert result == {}
        
        result = merge_configs({'key': 'value'}, {})
        assert result == {'key': 'value'}
        
        result = merge_configs({}, {'key': 'value'})
        assert result == {'key': 'value'}


class TestGetDefaultConfig:
    """Test get_default_config function."""
    
    def test_get_default_config(self):
        """Test that default config has expected structure."""
        default_config = get_default_config()
        
        # Check required top-level keys
        required_keys = ['base_jql', 'team_categories', 'status_filters', 'report_settings']
        for key in required_keys:
            assert key in default_config
        
        # Check some default values
        assert default_config['report_settings']['max_results'] == 200
        assert 'Closed' in default_config['status_filters']['completed']
        assert 'team_categories' in default_config
    
    def test_default_config_is_valid(self):
        """Test that default config passes validation."""
        default_config = get_default_config()
        required_keys = ['base_jql', 'team_categories']
        
        assert validate_config_structure(default_config, required_keys)
        assert validate_team_categories(default_config['team_categories'])


class TestGetTeamMemberName:
    """Test get_team_member_name function."""
    
    def test_get_existing_team_member(self):
        """Test getting name for existing team member."""
        config = {
            'team_members': {
                'john@example.com': 'John Doe',
                'jane@example.com': 'Jane Smith'
            }
        }
        
        name = get_team_member_name(config, 'john@example.com')
        
        assert name == 'John Doe'
    
    def test_get_missing_team_member(self):
        """Test getting name for missing team member (returns email)."""
        config = {
            'team_members': {
                'john@example.com': 'John Doe'
            }
        }
        
        name = get_team_member_name(config, 'missing@example.com')
        
        assert name == 'missing@example.com'
    
    def test_get_team_member_no_config(self):
        """Test getting name when team_members not in config."""
        config = {}
        
        name = get_team_member_name(config, 'test@example.com')
        
        assert name == 'test@example.com'


class TestGetAllTeamMemberEmails:
    """Test get_all_team_member_emails function."""
    
    def test_get_all_emails(self):
        """Test getting all team member emails."""
        config = {
            'team_members': {
                'john@example.com': 'John Doe',
                'jane@example.com': 'Jane Smith',
                'bob@example.com': 'Bob Wilson'
            }
        }
        
        emails = get_all_team_member_emails(config)
        
        expected_emails = ['john@example.com', 'jane@example.com', 'bob@example.com']
        assert sorted(emails) == sorted(expected_emails)
    
    def test_get_emails_no_config(self):
        """Test getting emails when team_members not in config."""
        config = {}
        
        emails = get_all_team_member_emails(config)
        
        assert emails == []
    
    def test_get_emails_empty_team_members(self):
        """Test getting emails when team_members is empty."""
        config = {'team_members': {}}
        
        emails = get_all_team_member_emails(config)
        
        assert emails == []


class TestGetTeamMembersDict:
    """Test get_team_members_dict function."""
    
    def test_get_team_members_dict(self):
        """Test getting team members dictionary."""
        config = {
            'team_members': {
                'john@example.com': 'John Doe',
                'jane@example.com': 'Jane Smith'
            }
        }
        
        members_dict = get_team_members_dict(config)
        
        expected_dict = {
            'john@example.com': 'John Doe',
            'jane@example.com': 'Jane Smith'
        }
        assert members_dict == expected_dict
    
    def test_get_team_members_dict_no_config(self):
        """Test getting dictionary when team_members not in config."""
        config = {}
        
        members_dict = get_team_members_dict(config)
        
        assert members_dict == {}


# Pytest fixtures for common test data
@pytest.fixture
def sample_config():
    """Fixture providing a sample configuration for testing."""
    return {
        'base_jql': 'project = TEST AND assignee = currentUser()',
        'team_categories': {
            'Backend': {
                'components': ['API', 'Database'],
                'keywords': ['backend', 'service'],
                'description': 'Backend development tasks'
            },
            'Frontend': {
                'components': ['UI', 'UX'],
                'projects': ['WEB'],
                'description': 'Frontend and user interface work'
            }
        },
        'team_members': {
            'john@example.com': 'John Doe',
            'jane@example.com': 'Jane Smith',
            'bob@example.com': 'Bob Wilson'
        },
        'status_filters': {
            'completed': ['Closed', 'Done'],
            'active': ['In Progress', 'Review']
        },
        'report_settings': {
            'max_results': 200,
            'order_by': 'updated DESC',
            'default_status_filter': 'completed'
        }
    }


@pytest.fixture
def sample_team_categories():
    """Fixture providing sample team categories for testing."""
    return {
        'Development': {
            'components': ['Backend', 'Frontend'],
            'keywords': ['development', 'coding'],
            'description': 'Software development work'
        },
        'Testing': {
            'components': ['QA', 'Testing'],
            'projects': ['TEST'],
            'keywords': ['test', 'bug'],
            'description': 'Quality assurance and testing'
        },
        'DevOps': {
            'keywords': ['deployment', 'infrastructure'],
            'description': 'DevOps and infrastructure work'
        }
    }


if __name__ == "__main__":
    # Allow running tests directly  
    pytest.main([__file__, "-v"])
