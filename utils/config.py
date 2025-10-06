#!/usr/bin/env python3
"""
Configuration utilities for loading and validating YAML configuration files.

This module provides reusable functions for handling configuration files
used across different report types and utilities.
"""

import sys
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union


def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file with error handling.
    
    Args:
        config_file: Path to the YAML configuration file
        
    Returns:
        Dict[str, Any]: Parsed configuration dictionary
        
    Raises:
        SystemExit: If file not found or YAML parsing fails
        
    Example:
        config = load_config('team_config.yaml')
        base_jql = config['base_jql']
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ Loaded configuration from {config_file}")
        return config
        
    except FileNotFoundError:
        print(f"❌ Configuration file {config_file} not found!")
        print("Please create a team_config.yaml file or specify a valid config file.")
        sys.exit(1)
        
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML configuration: {e}")
        sys.exit(1)


def validate_config_structure(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    Validate that configuration contains all required keys.
    
    Args:
        config: Configuration dictionary to validate
        required_keys: List of required top-level keys
        
    Returns:
        bool: True if all required keys present, False otherwise
        
    Example:
        is_valid = validate_config_structure(config, ['base_jql', 'team_categories'])
    """
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        print(f"❌ Missing required configuration keys: {missing_keys}")
        return False
    
    return True


def validate_team_categories(team_categories: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate the structure of team_categories configuration.
    
    Args:
        team_categories: Team categories configuration dictionary
        
    Returns:
        bool: True if structure is valid, False otherwise
        
    Expected structure:
        {
            "Category Name": {
                "components": ["Component1", "Component2"],  # Optional
                "projects": ["PROJECT_KEY"],                 # Optional  
                "keywords": ["keyword1", "keyword2"],        # Optional
                "description": "Human readable description"  # Required
            }
        }
    """
    if not isinstance(team_categories, dict):
        print("❌ team_categories must be a dictionary")
        return False
        
    for category_name, category_config in team_categories.items():
        if not isinstance(category_config, dict):
            print(f"❌ Category '{category_name}' must be a dictionary")
            return False
            
        if 'description' not in category_config:
            print(f"❌ Category '{category_name}' missing required 'description' field")
            return False
            
        # Optional fields validation
        for field in ['components', 'projects', 'keywords']:
            if field in category_config and not isinstance(category_config[field], list):
                print(f"❌ Category '{category_name}' field '{field}' must be a list")
                return False
    
    return True


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a configuration value using dot notation path.
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., 'report_settings.max_results')
        default: Default value if key path not found
        
    Returns:
        Configuration value or default
        
    Example:
        max_results = get_config_value(config, 'report_settings.max_results', 100)
    """
    keys = key_path.split('.')
    value = config
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries with override precedence.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration (takes precedence)
        
    Returns:
        Dict[str, Any]: Merged configuration dictionary
        
    Example:
        merged = merge_configs(default_config, user_config)
    """
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Override with new value
            merged[key] = value
    
    return merged


def get_default_config() -> Dict[str, Any]:
    """
    Get a default configuration structure.
    
    Returns:
        Dict[str, Any]: Default configuration with sensible defaults
        
    Useful for:
        - Creating new configuration files
        - Providing fallback values
        - Configuration validation
    """
    return {
        'base_jql': '',
        'team_categories': {},
        'status_filters': {
            'planned': ['New', 'Refinement', 'To Do'],
            'execution': ['In Progress', 'Review'], 
            'completed': ['Closed'],
            'all': ['New', 'Refinement', 'To Do', 'In Progress', 'Review', 'Closed']
        },
        'report_settings': {
            'max_results': 200,
            'order_by': 'component ASC, updated DESC',
            'default_status_filter': 'completed'
        }
    }


def save_config(config: Dict[str, Any], config_file: str) -> bool:
    """
    Save configuration to a YAML file.
    
    Args:
        config: Configuration dictionary to save
        config_file: Path to output YAML file
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        success = save_config(config, 'my_config.yaml')
    """
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Saved configuration to {config_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False


def load_config_with_defaults(config_file: str) -> Dict[str, Any]:
    """
    Load configuration with default fallbacks.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Dict[str, Any]: Merged configuration with defaults
        
    Example:
        config = load_config_with_defaults('team_config.yaml')
    """
    defaults = get_default_config()
    
    try:
        user_config = load_config(config_file)
        return merge_configs(defaults, user_config)
    except SystemExit:
        print("⚠️  Using default configuration only")
        return defaults


def get_team_member_name(config: Dict[str, Any], email: str) -> str:
    """
    Get display name for a team member by email.
    
    Args:
        config: Configuration dictionary
        email: Email address to look up
        
    Returns:
        str: Display name or email if not found
        
    Example:
        name = get_team_member_name(config, 'john@company.com')
        # Returns "John Doe" or "john@company.com" if not mapped
    """
    team_members = config.get('team_members', {})
    
    # Handle both old list format and new dict format
    if isinstance(team_members, list):
        # Old format: return email as-is
        return email
    elif isinstance(team_members, dict):
        # New format: look up display name
        return team_members.get(email, email)
    else:
        return email


def get_all_team_member_emails(config: Dict[str, Any]) -> List[str]:
    """
    Get all team member email addresses.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List[str]: List of email addresses
        
    Example:
        emails = get_all_team_member_emails(config)
        # Returns ['john@company.com', 'jane@company.com', ...]
    """
    team_members = config.get('team_members', {})
    
    if isinstance(team_members, list):
        # Old format: emails are the list items
        return list(team_members)
    elif isinstance(team_members, dict):
        # New format: emails are the keys
        return list(team_members.keys())
    else:
        return []


def get_team_members_dict(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Get team members dictionary from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict[str, str]: Dictionary mapping emails to display names
        
    Example:
        members = get_team_members_dict(config)
        # Returns {"user@company.com": "User Name", ...}
    """
    team_members = config.get('team_members', {})
    
    # Handle both old list format and new dict format
    if isinstance(team_members, list):
        # Old format: create dictionary with email as both key and value
        return {email: email for email in team_members}
    elif isinstance(team_members, dict):
        # New format: return as-is
        return team_members
    else:
        return {}


# =============================================================================
# NEW CONFIGURATION MANAGEMENT SYSTEM
# =============================================================================

def load_default_config() -> Dict[str, Any]:
    """
    Load the default configuration from config/default_config.yaml.
    
    Returns:
        Dict[str, Any]: Default configuration dictionary
        
    Raises:
        FileNotFoundError: If default config file is not found
        yaml.YAMLError: If YAML parsing fails
        
    Example:
        defaults = load_default_config()
        print(defaults['report']['show_active_config'])  # True
    """
    config_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Default config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing default config: {e}")


def load_user_configs(paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Load user configuration files (team_config.yaml, github_config.yaml).
    
    Args:
        paths: Optional list of config file paths. If None, auto-detect
               team_config.yaml and github_config.yaml in repo root.
    
    Returns:
        Dict[str, Any]: Merged user configuration dictionary
        
    Example:
        user_config = load_user_configs()
        user_config = load_user_configs(['custom_config.yaml'])
    """
    if paths is None:
        # Auto-detect user config files in repo root
        repo_root = Path(__file__).parent.parent
        paths = []
        
        for config_name in ['team_config.yaml', 'github_config.yaml']:
            config_path = repo_root / config_name
            if config_path.exists():
                paths.append(str(config_path))
    
    merged_config = {}
    
    for path in paths:
        try:
            with open(path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            merged_config = deep_merge(merged_config, user_config)
            print(f"✅ Loaded user config from {path}")
        except FileNotFoundError:
            print(f"⚠️  User config file not found: {path}")
        except yaml.YAMLError as e:
            print(f"❌ Error parsing user config {path}: {e}")
    
    return merged_config


def load_env_overrides() -> Dict[str, Any]:
    """
    Load configuration overrides from environment variables.
    
    Maps selected environment variables into config structure under env.* namespace.
    This allows displaying env vars in active config without writing them to disk.
    
    Returns:
        Dict[str, Any]: Configuration with env overrides
        
    Environment Variables:
        JIRA_SERVER -> env.jira_server
        GITHUB_TOKEN -> env.github_token  
        JIRA_TOKEN -> env.jira_token
        
    Example:
        env_config = load_env_overrides()
        print(env_config['env']['github_token'])  # from GITHUB_TOKEN env var
    """
    env_config = {"env": {}}
    
    # Map environment variables to config paths
    env_mappings = {
        'JIRA_SERVER': 'jira_server',
        'GITHUB_TOKEN': 'github_token', 
        'JIRA_TOKEN': 'jira_token',
        'JIRA_USERNAME': 'jira_username',
        'JIRA_PASSWORD': 'jira_password'
    }
    
    for env_var, config_key in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            env_config['env'][config_key] = value
    
    return env_config


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries with "override wins" semantics.
    
    Args:
        base: Base dictionary 
        override: Override dictionary (values in this dict win)
        
    Returns:
        Dict[str, Any]: Merged dictionary
        
    Merge Rules:
        - Nested dicts are merged recursively
        - Lists are replaced entirely (no merging)
        - Primitive values in override replace base values
        - New keys from override are added
        
    Example:
        base = {'a': {'x': 1, 'y': 2}, 'b': [1, 2]}
        override = {'a': {'y': 3, 'z': 4}, 'b': [3, 4, 5]}
        result = deep_merge(base, override)
        # {'a': {'x': 1, 'y': 3, 'z': 4}, 'b': [3, 4, 5]}
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Replace value (handles primitives, lists, and new keys)
            result[key] = value
    
    return result


def get_config(paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Load complete configuration with deterministic precedence.
    
    Precedence (later overrides earlier):
    1. Default config (config/default_config.yaml)
    2. User YAML files (team_config.yaml, github_config.yaml) 
    3. Environment variable overrides
    
    Args:
        paths: Optional list of user config paths. If None, auto-detect
               team_config.yaml/github_config.yaml at repo root.
    
    Returns:
        Dict[str, Any]: Complete merged configuration
        
    Example:
        config = get_config()
        config = get_config(['custom_team.yaml'])
    """
    print("🔧 Loading configuration...")
    
    # Step 1: Load defaults
    try:
        config = load_default_config()
        print("✅ Loaded default configuration")
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"❌ Failed to load default config: {e}")
        config = {}
    
    # Step 2: Merge user configs
    try:
        user_config = load_user_configs(paths)
        config = deep_merge(config, user_config)
    except Exception as e:
        print(f"⚠️  Error loading user configs: {e}")
    
    # Step 3: Apply environment overrides
    try:
        env_config = load_env_overrides()
        config = deep_merge(config, env_config)
        if env_config.get('env'):
            print("✅ Applied environment variable overrides")
    except Exception as e:
        print(f"⚠️  Error loading env overrides: {e}")
    
    print("🎯 Configuration loading complete")
    return config
