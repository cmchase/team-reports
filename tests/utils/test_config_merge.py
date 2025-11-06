#!/usr/bin/env python3
"""
Unit tests for configuration merge functionality

Tests the new configuration management system with deep_merge, precedence rules,
and environment variable handling.
"""

import pytest
from unittest.mock import patch, mock_open
import os
import sys
from pathlib import Path

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from team_reports.utils.config import (
    load_default_config,
    load_user_configs, 
    load_env_overrides,
    deep_merge,
    get_config
)


class TestDeepMerge:
    """Test deep_merge function with various scenarios."""
    
    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        
        result = deep_merge(base, override)
        
        expected = {'a': 1, 'b': 3, 'c': 4}
        assert result == expected
    
    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {
            'config': {'x': 1, 'y': 2},
            'other': 'value'
        }
        override = {
            'config': {'y': 3, 'z': 4},
            'new': 'item'
        }
        
        result = deep_merge(base, override)
        
        expected = {
            'config': {'x': 1, 'y': 3, 'z': 4},
            'other': 'value',
            'new': 'item'
        }
        assert result == expected
    
    def test_merge_deep_nested_dicts(self):
        """Test merging deeply nested dictionaries."""
        base = {
            'level1': {
                'level2': {
                    'level3': {'a': 1, 'b': 2}
                },
                'other': 'keep'
            }
        }
        override = {
            'level1': {
                'level2': {
                    'level3': {'b': 3, 'c': 4}
                }
            }
        }
        
        result = deep_merge(base, override)
        
        expected = {
            'level1': {
                'level2': {
                    'level3': {'a': 1, 'b': 3, 'c': 4}
                },
                'other': 'keep'
            }
        }
        assert result == expected
    
    def test_merge_lists_replace_entirely(self):
        """Test that lists are replaced entirely, not merged."""
        base = {'items': [1, 2, 3], 'other': 'value'}
        override = {'items': [4, 5]}
        
        result = deep_merge(base, override)
        
        expected = {'items': [4, 5], 'other': 'value'}
        assert result == expected
    
    def test_merge_mixed_types(self):
        """Test merging with mixed data types."""
        base = {
            'string': 'original',
            'number': 42,
            'list': ['a', 'b'],
            'dict': {'nested': 'value'}
        }
        override = {
            'string': 'updated',
            'number': 100,
            'list': ['c', 'd', 'e'],
            'dict': {'nested': 'new', 'added': 'item'}
        }
        
        result = deep_merge(base, override)
        
        expected = {
            'string': 'updated',
            'number': 100,
            'list': ['c', 'd', 'e'],
            'dict': {'nested': 'new', 'added': 'item'}
        }
        assert result == expected
    
    def test_merge_empty_dicts(self):
        """Test merging with empty dictionaries."""
        base = {'a': 1, 'b': 2}
        override = {}
        
        result = deep_merge(base, override)
        assert result == base
        
        result = deep_merge({}, base)
        assert result == base
    
    def test_merge_none_values(self):
        """Test merging with None values."""
        base = {'a': 1, 'b': None}
        override = {'a': None, 'c': 3}
        
        result = deep_merge(base, override)
        
        expected = {'a': None, 'b': None, 'c': 3}
        assert result == expected


class TestLoadDefaultConfig:
    """Test load_default_config function."""
    
    def test_load_default_config_success(self):
        """Test successfully loading default configuration."""
        config = load_default_config()
        
        # Verify structure exists
        assert isinstance(config, dict)
        assert 'jira' in config
        assert 'github' in config
        assert 'report' in config
        assert 'team_categories' in config
        
        # Verify specific default values
        assert config['report']['show_active_config'] is True
        assert config['report']['max_results'] == 200
        assert isinstance(config['team_categories'], dict)
        assert isinstance(config['status_filters'], dict)
    
    @patch('utils.config.Path')
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_default_config_file_not_found(self, mock_open, mock_path):
        """Test behavior when default config file is missing."""
        with pytest.raises(FileNotFoundError):
            load_default_config()


class TestLoadUserConfigs:
    """Test load_user_configs function."""
    
    def test_load_user_configs_with_paths(self):
        """Test loading user configs with explicit paths."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        user_config_path = fixtures_dir / "test_user_config.yaml"
        github_config_path = fixtures_dir / "test_github_config.yaml"
        
        config = load_user_configs([str(user_config_path), str(github_config_path)])
        
        # Should have merged both configs
        assert 'jira' in config
        assert 'github' in config
        assert 'team_categories' in config
        
        # Verify merge - should have Backend, Frontend (from user) and DevOps (from github)
        assert 'Backend' in config['team_categories']
        assert 'Frontend' in config['team_categories'] 
        assert 'DevOps' in config['team_categories']
        
        # Verify override - github config should override user config for team_members
        assert config['team_members']['test@example.com'] == "Test User (Updated)"
        assert 'github@example.com' in config['team_members']
    
    def test_load_user_configs_nonexistent_files(self):
        """Test loading user configs with nonexistent files."""
        config = load_user_configs(['nonexistent1.yaml', 'nonexistent2.yaml'])
        
        # Should return empty dict when no files found
        assert config == {}
    
    @patch('utils.config.Path.exists')
    def test_load_user_configs_auto_detect_none_exist(self, mock_exists):
        """Test auto-detection when no config files exist."""
        mock_exists.return_value = False
        
        config = load_user_configs()
        
        assert config == {}
    
    def test_load_user_configs_minimal(self):
        """Test loading minimal user config."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        minimal_config_path = fixtures_dir / "minimal_config.yaml"
        
        config = load_user_configs([str(minimal_config_path)])
        
        assert config['jira']['base_jql'] == "project = MINIMAL"
        assert config['report']['show_active_config'] is False


class TestLoadEnvOverrides:
    """Test load_env_overrides function."""
    
    @patch.dict(os.environ, {
        'GITHUB_TOKEN': 'env-github-token',
        'JIRA_SERVER': 'https://env-jira.atlassian.net',
        'JIRA_EMAIL': 'env-user@example.com',
        'JIRA_API_TOKEN': 'env-jira-token'
    })
    def test_load_env_overrides_with_values(self):
        """Test loading environment overrides when variables are set."""
        config = load_env_overrides()
        
        assert 'env' in config
        assert config['env']['github']['token'] == 'env-github-token'
        assert config['env']['jira']['server'] == 'https://env-jira.atlassian.net'
        assert config['env']['jira']['email'] == 'env-user@example.com'
        assert config['env']['jira']['token'] == 'env-jira-token'
        
        # All sections present when their variables are set
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_env_overrides_no_values(self):
        """Test loading environment overrides when no variables are set."""
        config = load_env_overrides()
        
        assert config == {}
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'})
    def test_load_env_overrides_partial_values(self):
        """Test loading environment overrides with only some variables set."""
        config = load_env_overrides()
        
        assert config['env']['github']['token'] == 'test-token'
        assert 'jira' not in config['env']


class TestGetConfig:
    """Test get_config function with full integration."""
    
    def test_get_config_defaults_only(self):
        """Test get_config with only defaults (no user configs or env vars)."""
        with patch('utils.config.load_user_configs', return_value={}):
            with patch('utils.config.load_env_overrides', return_value={'env': {}}):
                config = get_config()
                
                # Should have default structure
                assert 'jira' in config
                assert 'github' in config
                assert 'report' in config
                assert config['report']['show_active_config'] is True
                assert config['report']['max_results'] == 200
    
    def test_get_config_with_user_override(self):
        """Test get_config with user config overriding defaults."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        minimal_config_path = fixtures_dir / "minimal_config.yaml"
        
        with patch('utils.config.load_env_overrides', return_value={'env': {}}):
            config = get_config([str(minimal_config_path)])
            
            # User config should override defaults
            assert config['jira']['base_jql'] == "project = MINIMAL"
            assert config['report']['show_active_config'] is False  # Overridden
            assert config['report']['max_results'] == 200  # Default preserved
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'env-override-token'})
    def test_get_config_with_env_override(self):
        """Test get_config with environment variables overriding all."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        github_config_path = fixtures_dir / "test_github_config.yaml"
        
        config = get_config([str(github_config_path)])
        
        # Should have all levels
        assert config['github']['org'] == 'test-org'  # From user config
        assert config['env']['github']['token'] == 'env-override-token'  # From env
        assert config['report']['show_active_config'] is True  # From defaults
    
    def test_get_config_precedence_order(self):
        """Test that precedence order is respected: default < user < env."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        user_config_path = fixtures_dir / "test_user_config.yaml"
        
        # Mock env override for max_results
        env_override = {
            'report': {'max_results': 500},  # Should win over user config
            'env': {'github_token': 'env-token'}
        }
        
        with patch('utils.config.load_env_overrides', return_value=env_override):
            config = get_config([str(user_config_path)])
            
            # Precedence check:
            # Default: max_results = 200
            # User: max_results = 150  
            # Env: max_results = 500 (should win)
            assert config['report']['max_results'] == 500
            assert config['env']['github_token'] == 'env-token'
            assert config['jira']['base_jql'] == "project = TEST AND assignee = currentUser()"


# Integration test fixtures
@pytest.fixture
def temp_config_files(tmp_path):
    """Create temporary config files for testing."""
    # Create default config
    default_config = tmp_path / "default_config.yaml"
    default_config.write_text("""
jira:
  base_jql: ""
  server: ""
report:
  show_active_config: true
  max_results: 200
""")
    
    # Create user config
    user_config = tmp_path / "user_config.yaml" 
    user_config.write_text("""
jira:
  base_jql: "project = USER"
report:
  max_results: 100
""")
    
    return {
        'default': str(default_config),
        'user': str(user_config)
    }


class TestConfigIntegration:
    """Integration tests for complete config loading workflow."""
    
    def test_full_config_merge_workflow(self):
        """Test complete workflow from defaults through user configs to env vars."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        
        # Use real fixture files
        user_config_path = fixtures_dir / "test_user_config.yaml"
        github_config_path = fixtures_dir / "test_github_config.yaml"
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'final-env-token',
            'JIRA_SERVER': 'https://final-env.atlassian.net'
        }):
            config = get_config([str(user_config_path), str(github_config_path)])
            
            # Verify final merged result has all layers
            
            # From defaults
            assert config['status_filters']['completed'] == ["Closed", "Done"]
            
            # From user config (first)
            assert config['jira']['base_jql'] == "project = TEST AND assignee = currentUser()"
            
            # From github config (second user config, should override first)
            assert 'DevOps' in config['team_categories']
            assert config['team_members']['test@example.com'] == "Test User (Updated)"
            
            # From environment (should be in env namespace)
            assert config['env']['github']['token'] == 'final-env-token'
            assert config['env']['jira']['server'] == 'https://final-env.atlassian.net'


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
