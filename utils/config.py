#!/usr/bin/env python3
"""
Configuration utilities for loading and validating YAML configuration files.

This module provides reusable functions for handling configuration files
used across different report types and utilities.
"""

import sys
import yaml
from typing import Dict, Any, List, Optional


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
                "description": "Category description",
                "components": ["Component1", "Component2"],  # Optional
                "projects": ["PROJECT_KEY"],                 # Optional
                "keywords": ["keyword1", "keyword2"]         # Optional
            }
        }
    """
    if not isinstance(team_categories, dict):
        print("❌ team_categories must be a dictionary")
        return False
    
    for category_name, rules in team_categories.items():
        if not isinstance(rules, dict):
            print(f"❌ team_categories['{category_name}'] must be a dictionary")
            return False
        
        # Check for required description
        if 'description' not in rules:
            print(f"❌ team_categories['{category_name}'] missing required 'description' field")
            return False
        
        # Validate optional fields if present
        for field in ['components', 'projects', 'keywords']:
            if field in rules and not isinstance(rules[field], list):
                print(f"❌ team_categories['{category_name}']['{field}'] must be a list")
                return False
    
    return True


def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a nested configuration value using dot notation.
    
    Args:
        config: Configuration dictionary
        key_path: Dot-separated path to the value (e.g., 'report_settings.max_results')
        default: Default value if key not found
        
    Returns:
        Any: Configuration value or default
        
    Examples:
        max_results = get_config_value(config, 'report_settings.max_results', 200)
        order_by = get_config_value(config, 'report_settings.order_by', 'updated DESC')
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
    Merge two configuration dictionaries, with override taking precedence.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Dict[str, Any]: Merged configuration
        
    Example:
        merged = merge_configs(default_config, user_config)
    """
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Override the value
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
        config_file: Path to save the configuration file
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        success = save_config(config, 'my_team_config.yaml')
    """
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Configuration saved to {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False


def load_config_with_defaults(config_file: str) -> Dict[str, Any]:
    """
    Load configuration file with default values as fallback.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Dict[str, Any]: Configuration with defaults applied
        
    Example:
        config = load_config_with_defaults('team_config.yaml')
    """
    default_config = get_default_config()
    
    try:
        user_config = load_config(config_file)
        return merge_configs(default_config, user_config)
    except SystemExit:
        print("⚠️  Using default configuration")
        return default_config


def get_team_member_name(config: Dict[str, Any], email: str) -> str:
    """
    Get the display name for a team member by their email address.
    
    Args:
        config: Configuration dictionary containing team_members
        email: Email address to look up
        
    Returns:
        str: Display name if found, otherwise email address
        
    Example:
        name = get_team_member_name(config, "user@company.com")
        # Returns "John Doe" or "user@company.com" if not found
    """
    team_members = config.get('team_members', {})
    
    # Handle both old list format and new dict format for backward compatibility
    if isinstance(team_members, list):
        # Old format: return email as-is
        return email
    elif isinstance(team_members, dict):
        # New format: lookup name by email
        return team_members.get(email, email)
    else:
        return email


def get_all_team_member_emails(config: Dict[str, Any]) -> List[str]:
    """
    Get all team member email addresses from the configuration.
    
    Args:
        config: Configuration dictionary containing team_members
        
    Returns:
        List[str]: List of email addresses
        
    Example:
        emails = get_all_team_member_emails(config)
        # Returns ["user1@company.com", "user2@company.com", ...]
    """
    team_members = config.get('team_members', {})
    
    # Handle both old list format and new dict format
    if isinstance(team_members, list):
        return team_members
    elif isinstance(team_members, dict):
        return list(team_members.keys())
    else:
        return []


def get_team_members_dict(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Get team members as a dictionary mapping email to display name.
    
    Args:
        config: Configuration dictionary containing team_members
        
    Returns:
        Dict[str, str]: Dictionary mapping email to display name
        
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
