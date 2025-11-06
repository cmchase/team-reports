#!/usr/bin/env python3
"""
Unit tests for active configuration rendering functionality

Tests the redaction, hashing, and markdown rendering of active configuration blocks.
"""

import pytest
from unittest.mock import patch
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from team_reports.utils.report import (
    redact_secrets,
    generate_config_hash,
    render_active_config
)


class TestRedactSecrets:
    """Test redact_secrets function with various secret patterns."""
    
    def test_redact_token_keys(self):
        """Test redaction of keys containing 'token'."""
        config = {
            'github_token': 'abc123xyz',
            'jira_token': 'secret456',
            'access_token': 'token789',
            'user_name': 'john'
        }
        
        redacted = redact_secrets(config)
        
        assert redacted['github_token'] == '****'
        assert redacted['jira_token'] == '****'
        assert redacted['access_token'] == '****'
        assert redacted['user_name'] == 'john'  # Not redacted
    
    def test_redact_password_keys(self):
        """Test redaction of keys containing 'password'."""
        config = {
            'db_password': 'secret123',
            'user_password': 'password456',
            'admin_credentials': 'admin789',
            'timeout': 30
        }
        
        redacted = redact_secrets(config)
        
        assert redacted['db_password'] == '****'
        assert redacted['user_password'] == '****' 
        assert redacted['admin_credentials'] == '****'
        assert redacted['timeout'] == 30  # Not redacted
    
    def test_redact_env_namespace(self):
        """Test redaction of all values under env namespace with structured paths."""
        config = {
            'env': {
                'jira': {
                    'server': 'https://company.atlassian.net',
                    'token': 'jira_token_123'
                },
                'github': {
                    'token': 'github_token_456'
                }
            },
            'report': {
                'github_token': 'should_redact',  # Still redacted due to key name
                'max_results': 200
            }
        }
        
        redacted = redact_secrets(config)
        
        # All env values should be redacted (structured)
        assert redacted['env']['jira']['server'] == '****'
        assert redacted['env']['jira']['token'] == '****'
        assert redacted['env']['github']['token'] == '****'
        
        # Non-env values follow normal rules
        assert redacted['report']['github_token'] == '****'  # Key contains 'token'
        assert redacted['report']['max_results'] == 200  # Not redacted
    
    def test_redact_long_alphanumeric_strings(self):
        """Test redaction of long alphanumeric strings that look like tokens."""
        config = {
            'suspicious_string': 'abcd1234efgh5678ijkl9012mnop3456qrst',  # 36 chars, looks like token
            'short_string': 'abc123',  # 6 chars, not redacted
            'normal_text': 'This is a normal sentence with spaces',
            'url': 'https://example.com/path'
        }
        
        redacted = redact_secrets(config)
        
        assert redacted['suspicious_string'] == '****'
        assert redacted['short_string'] == 'abc123'
        assert redacted['normal_text'] == 'This is a normal sentence with spaces'
        assert redacted['url'] == 'https://example.com/path'
    
    def test_redact_nested_structures(self):
        """Test redaction works with nested dictionaries and lists."""
        config = {
            'database': {
                'connection': {
                    'password': 'secret123',
                    'host': 'localhost',
                    'port': 5432
                }
            },
            'tokens': [
                {'name': 'github', 'token': 'gh_token123'},
                {'name': 'jira', 'secret': 'jira_secret456'}
            ]
        }
        
        redacted = redact_secrets(config)
        
        assert redacted['database']['connection']['password'] == '****'
        assert redacted['database']['connection']['host'] == 'localhost'
        assert redacted['database']['connection']['port'] == 5432
        
        assert redacted['tokens'][0]['name'] == 'github'
        assert redacted['tokens'][0]['token'] == '****'
        assert redacted['tokens'][1]['name'] == 'jira'
        assert redacted['tokens'][1]['secret'] == '****'
    
    def test_redact_empty_or_none_values(self):
        """Test redaction handles empty or None values gracefully."""
        config = {
            'empty_token': '',
            'none_password': None,
            'zero_secret': 0,
            'false_key': False,
            'normal_value': 'test'
        }
        
        redacted = redact_secrets(config)
        
        # Empty strings are not redacted to '****'
        assert redacted['empty_token'] == ''
        assert redacted['none_password'] is None
        assert redacted['zero_secret'] == 0
        assert redacted['false_key'] is False
        assert redacted['normal_value'] == 'test'


class TestGenerateConfigHash:
    """Test generate_config_hash function."""
    
    def test_hash_deterministic(self):
        """Test that the same config produces the same hash."""
        config1 = {'a': 1, 'b': {'x': 2, 'y': 3}}
        config2 = {'b': {'y': 3, 'x': 2}, 'a': 1}  # Different order
        
        hash1 = generate_config_hash(config1)
        hash2 = generate_config_hash(config2)
        
        assert hash1 == hash2
        assert len(hash1) == 8  # Short hash
        assert isinstance(hash1, str)
    
    def test_hash_changes_with_content(self):
        """Test that different configs produce different hashes."""
        config1 = {'a': 1, 'b': 2}
        config2 = {'a': 1, 'b': 3}  # Different value
        
        hash1 = generate_config_hash(config1)
        hash2 = generate_config_hash(config2)
        
        assert hash1 != hash2
    
    def test_hash_empty_config(self):
        """Test hash generation for empty config."""
        config = {}
        
        hash_str = generate_config_hash(config)
        
        assert len(hash_str) == 8
        assert isinstance(hash_str, str)


class TestRenderActiveConfig:
    """Test render_active_config function."""
    
    def test_render_when_enabled(self):
        """Test rendering when show_active_config is True."""
        config = {
            'report': {'show_active_config': True},
            'github_token': 'secret123',
            'user': 'john',
            'settings': {'max_results': 100}
        }
        
        with patch('utils.report.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '2025-01-15 14:30:00 UTC'
            
            result = render_active_config(config)
        
        # Check structure
        assert '<details>' in result
        assert '<summary>📋 Active Configuration</summary>' in result
        assert '```yaml' in result
        assert '# Configuration Hash:' in result
        assert '# Generated: 2025-01-15 14:30:00 UTC' in result
        assert '</details>' in result
        
        # Check content is redacted
        assert '****' in result  # github_token should be redacted
        assert 'user: john' in result  # Normal values preserved
        assert 'max_results: 100' in result
    
    def test_render_when_disabled(self):
        """Test no rendering when show_active_config is False."""
        config = {
            'report': {'show_active_config': False},
            'github_token': 'secret123'
        }
        
        result = render_active_config(config)
        
        assert result == ""
    
    def test_render_when_missing_flag(self):
        """Test no rendering when show_active_config is not present."""
        config = {
            'github_token': 'secret123',
            'user': 'john'
        }
        
        result = render_active_config(config)
        
        assert result == ""
    
    def test_render_with_nested_redaction(self):
        """Test rendering with complex nested structures and redaction."""
        config = {
            'report': {'show_active_config': True},
        'env': {
            'jira': {
                'server': 'https://company.atlassian.net',
                'token': 'env_jira_token_123'
            },
            'github': {
                'token': 'env_github_token_456'
            }
        },
            'team_categories': {
                'Backend': {
                    'keywords': ['api', 'database'],
                    'description': 'Backend development'
                }
            },
            'credentials': {
                'api_key': 'very_secret_key_12345678901234567890',
                'username': 'admin'
            }
        }
        
        with patch('utils.report.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '2025-01-15 14:30:00 UTC'
            
            result = render_active_config(config)
        
        # Verify structure
        assert '<details>' in result
        assert 'Configuration Hash:' in result
        
        # Verify redaction worked
        lines = result.split('\n')
        yaml_content = '\n'.join(line for line in lines if not line.strip().startswith('#') and '```' not in line and '<' not in line)
        
        # Secrets should be redacted
        assert '****' in result  # Various tokens should be redacted
        assert 'env_jira_token_123' not in result  # Raw token should not appear
        assert 'env_github_token_456' not in result  # Raw token should not appear
        # Regular content should be preserved
        assert 'Backend' in result
        assert 'api' in result
        assert 'username: admin' in result
    
    def test_render_snapshot_deterministic(self):
        """Test that render output is deterministic (except timestamp)."""
        config = {
            'report': {'show_active_config': True},
            'b_setting': 'value2',
            'a_setting': 'value1'  # Different order
        }
        
        with patch('utils.report.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = 'FIXED_TIME'
            
            result1 = render_active_config(config)
            result2 = render_active_config(config)
        
        assert result1 == result2
        
        # Different order should produce same result (due to sort_keys=True)
        config_reordered = {'a_setting': 'value1', 'b_setting': 'value2'}
        config_reordered['report'] = {'show_active_config': True}
        
        with patch('utils.report.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = 'FIXED_TIME'
            
            result3 = render_active_config(config_reordered)
        
        assert result1 == result3


# Integration test fixtures
@pytest.fixture
def sample_config():
    """Fixture providing sample configuration for testing."""
    return {
        'report': {
            'show_active_config': True,
            'max_results': 200
        },
        'jira': {
            'base_jql': 'project = TEST',
            'server': 'https://test.atlassian.net'
        },
        'github': {
            'org': 'test-org',
            'token': 'gh_test_token_123456789'
        },
        'env': {
            'github_token': 'env_override_token',
            'jira_server': 'https://env.atlassian.net'
        },
        'team_categories': {
            'Backend': {
                'keywords': ['api', 'database'],
                'description': 'Backend development'
            }
        },
        'credentials': {
            'database_password': 'very_secret_db_password',
            'admin_user': 'admin'
        }
    }


class TestActiveConfigIntegration:
    """Integration tests for complete active config workflow."""
    
    def test_full_workflow_enabled(self, sample_config):
        """Test complete workflow when config display is enabled."""
        with patch('utils.report.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '2025-01-15 14:30:00 UTC'
            
            result = render_active_config(sample_config)
        
        # Verify complete structure
        assert result.startswith('\n---\n\n<details>')
        assert result.endswith('</details>\n')
        
        # Verify redaction of all secret types
        assert 'gh_test_token_123456789' not in result  # GitHub token redacted
        assert 'env_override_token' not in result       # Env token redacted
        assert 'very_secret_db_password' not in result  # Password redacted
        
        # Verify preservation of non-secret data
        assert 'test-org' in result                     # GitHub org preserved
        assert 'Backend' in result                      # Team category preserved
        assert 'admin' in result                        # Username preserved
        assert 'max_results: 200' in result             # Settings preserved
    
    def test_full_workflow_disabled(self, sample_config):
        """Test complete workflow when config display is disabled."""
        sample_config['report']['show_active_config'] = False
        
        result = render_active_config(sample_config)
        
        assert result == ""


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
