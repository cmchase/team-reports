#!/usr/bin/env python3
"""
Unit tests for configuration validation functionality

Tests the validation system with various invalid configurations, strict mode,
and clear error message generation.
"""

import pytest
from unittest.mock import patch
import os
import sys
from pathlib import Path

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from utils.config import (
    validate_config,
    get_config,
    ConfigError,
    _get_nested_value,
    _validate_wildcard_path,
    VALIDATION_RULES
)


class TestGetNestedValue:
    """Test _get_nested_value helper function."""
    
    def test_get_simple_value(self):
        """Test getting simple nested values."""
        config = {'a': {'b': {'c': 'value'}}}
        
        assert _get_nested_value(config, 'a.b.c') == 'value'
        assert _get_nested_value(config, 'a.b') == {'c': 'value'}
        assert _get_nested_value(config, 'a') == {'b': {'c': 'value'}}
    
    def test_get_nonexistent_value(self):
        """Test getting nonexistent values returns None."""
        config = {'a': {'b': 'value'}}
        
        assert _get_nested_value(config, 'a.b.c') is None
        assert _get_nested_value(config, 'x.y.z') is None
        assert _get_nested_value(config, 'a.x') is None
    
    def test_get_value_with_none_in_path(self):
        """Test getting value when intermediate path is None."""
        config = {'a': {'b': None}}
        
        assert _get_nested_value(config, 'a.b') is None
        assert _get_nested_value(config, 'a.b.c') is None


class TestValidateWildcardPath:
    """Test _validate_wildcard_path helper function."""
    
    def test_validate_wildcard_numbers(self):
        """Test validating wildcard paths with numbers."""
        config = {
            'thresholds': {
                'performance': {'max_time': 24, 'min_score': 85},
                'quality': {'review_depth': 2.5, 'coverage': 'not_a_number'}
            }
        }
        
        errors = _validate_wildcard_path(config, 'thresholds.*.*', (int, float))
        
        assert len(errors) == 1
        assert "'thresholds.quality.coverage': expected" in errors[0]
        assert "got str" in errors[0]
    
    def test_validate_wildcard_empty_path(self):
        """Test validating wildcard paths with empty or missing sections."""
        config = {'thresholds': {}}
        
        errors = _validate_wildcard_path(config, 'thresholds.*.*', (int, float))
        
        assert errors == []  # No errors for empty dict
    
    def test_validate_wildcard_single_level(self):
        """Test validating single-level wildcard paths."""
        config = {
            'metrics': {
                'cycle_time': True,
                'lead_time': 'not_bool'
            }
        }
        
        errors = _validate_wildcard_path(config, 'metrics.*', bool)
        
        assert len(errors) == 1
        assert "'metrics.lead_time': expected bool, got str" in errors[0]


class TestValidateConfig:
    """Test validate_config function."""
    
    def test_validate_valid_config(self):
        """Test validation passes for valid configuration."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        valid_config_path = fixtures_dir / "valid_config.yaml"
        
        import yaml
        with open(valid_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        errors = validate_config(config)
        
        assert errors == []
    
    def test_validate_invalid_types(self):
        """Test validation catches invalid types."""
        config = {
            'metrics': {
                'flow': {'cycle_time': 'not_bool'},  # Should be bool
                'delivery': {'pr_lead_time': 123}    # Should be bool
            },
            'report': {'show_active_config': 'yes'},  # Should be bool
            'states': {'active': 'not_list'}         # Should be list
        }
        
        errors = validate_config(config)
        
        expected_errors = [
            "'metrics.flow.cycle_time': expected bool, got str",
            "'metrics.delivery.pr_lead_time': expected bool, got int", 
            "'report.show_active_config': expected bool, got str",
            "'states.active': expected list, got str"
        ]
        
        for expected_error in expected_errors:
            assert any(expected_error in error for error in errors), f"Expected error '{expected_error}' not found in {errors}"
    
    def test_validate_wildcard_thresholds(self):
        """Test validation of wildcard threshold paths.""" 
        config = {
            'thresholds': {
                'performance': {
                    'max_time': 24,        # Valid number
                    'invalid': 'not_num'   # Invalid
                },
                'quality': {
                    'score': 85.5,         # Valid number  
                    'bad_score': []        # Invalid
                }
            }
        }
        
        errors = validate_config(config)
        
        assert len(errors) == 2
        assert "'thresholds.performance.invalid': expected" in str(errors)
        assert "'thresholds.quality.bad_score': expected" in str(errors)
    
    def test_validate_list_contents(self):
        """Test validation of list contents for states and bots."""
        config = {
            'states': {
                'active': ['Valid', 123, 'Another'],    # 123 is invalid
                'done': ['All', 'Valid', 'Strings']     # All valid
            },
            'bots': {
                'patterns': ['bot@company.com', 42, True]  # 42 and True are invalid
            }
        }
        
        errors = validate_config(config)
        
        assert len(errors) == 3
        assert "'states.active[1]': expected str, got int" in errors
        assert "'bots.patterns[1]': expected str, got int" in errors
        assert "'bots.patterns[2]': expected str, got bool" in errors
    
    def test_validate_missing_paths_ignored(self):
        """Test that missing configuration paths are ignored (not required)."""
        config = {
            'some_other_key': 'value'
            # Missing all validation paths
        }
        
        errors = validate_config(config)
        
        assert errors == []  # No errors for missing optional paths
    
    def test_validate_partial_paths(self):
        """Test validation with only some paths present."""
        config = {
            'metrics': {
                'flow': {'cycle_time': True}  # Only one metric present
            },
            'report': {'show_active_config': False}
        }
        
        errors = validate_config(config)
        
        assert errors == []  # Should pass validation


class TestGetConfigValidation:
    """Test get_config integration with validation."""
    
    def test_get_config_with_valid_configuration(self):
        """Test get_config succeeds with valid configuration."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        valid_config_path = fixtures_dir / "valid_config.yaml"
        
        # Should not raise any exceptions
        config = get_config([str(valid_config_path)])
        
        assert isinstance(config, dict)
        assert 'metrics' in config
    
    def test_get_config_strict_mode_raises_on_invalid(self):
        """Test get_config raises ConfigError in strict mode with invalid config."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        invalid_config_path = fixtures_dir / "invalid_config.yaml"
        
        with patch.dict(os.environ, {'TEAM_REPORTS_STRICT_CONFIG': '1'}):
            with pytest.raises(ConfigError) as exc_info:
                get_config([str(invalid_config_path)])
            
            error_message = str(exc_info.value)
            assert "Configuration validation failed" in error_message
            assert "expected bool, got str" in error_message
    
    @patch('builtins.print')
    def test_get_config_non_strict_mode_warns_on_invalid(self, mock_print):
        """Test get_config warns but continues in non-strict mode with invalid config."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        invalid_config_path = fixtures_dir / "invalid_config.yaml"
        
        with patch.dict(os.environ, {'TEAM_REPORTS_STRICT_CONFIG': '0'}):
            # Should not raise, just return config with warnings
            config = get_config([str(invalid_config_path)])
            
            assert isinstance(config, dict)
            
            # Check that warning was printed
            warning_calls = [call for call in mock_print.call_args_list if '⚠️' in str(call)]
            assert len(warning_calls) >= 1
            assert any("Configuration validation failed" in str(call) for call in warning_calls)
    
    @patch('builtins.print')
    def test_get_config_default_mode_is_non_strict(self, mock_print):
        """Test that default mode (no env var) is non-strict."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        invalid_config_path = fixtures_dir / "invalid_config.yaml"
        
        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise
            config = get_config([str(invalid_config_path)])
            
            assert isinstance(config, dict)


class TestValidationRules:
    """Test validation rules are comprehensive and correct."""
    
    def test_validation_rules_completeness(self):
        """Test that validation rules cover expected configuration paths."""
        expected_paths = [
            'metrics.flow.cycle_time',
            'metrics.flow.wip', 
            'metrics.flow.blocked_time',
            'metrics.delivery.pr_lead_time',
            'metrics.delivery.review_depth',
            'metrics.growth.enabled',
            'thresholds.*.*',
            'states.active',
            'states.done',
            'states.blocked',
            'bots.patterns',
            'report.show_active_config'
        ]
        
        for path in expected_paths:
            assert path in VALIDATION_RULES, f"Missing validation rule for {path}"
    
    def test_validation_rule_types(self):
        """Test that validation rule types are correct."""
        assert VALIDATION_RULES['metrics.flow.cycle_time'] == bool
        assert VALIDATION_RULES['thresholds.*.*'] == (int, float)
        assert VALIDATION_RULES['states.active'] == list
        assert VALIDATION_RULES['bots.patterns'] == list
        assert VALIDATION_RULES['report.show_active_config'] == bool


class TestConfigErrorMessages:
    """Test that error messages are clear and actionable."""
    
    def test_error_message_format(self):
        """Test error messages include path, expected type, and actual type."""
        config = {
            'metrics': {'flow': {'cycle_time': 'invalid'}},
            'report': {'show_active_config': 123}
        }
        
        errors = validate_config(config)
        
        assert len(errors) == 2
        
        # Check error message format
        for error in errors:
            assert "': expected" in error
            assert ", got" in error
            assert error.startswith("'")  # Path in quotes
    
    def test_comprehensive_error_scenario(self):
        """Test comprehensive validation with multiple error types."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "config"
        invalid_config_path = fixtures_dir / "invalid_config.yaml"
        
        import yaml
        with open(invalid_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        errors = validate_config(config)
        
        # Should catch multiple types of errors
        assert len(errors) > 5
        
        # Verify specific error types are caught
        error_text = " ".join(errors)
        assert "expected bool, got str" in error_text        # Type errors
        assert "expected bool, got int" in error_text        # Type errors 
        assert "expected list, got str" in error_text        # Type errors
        assert "expected str, got int" in error_text         # List content errors


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
