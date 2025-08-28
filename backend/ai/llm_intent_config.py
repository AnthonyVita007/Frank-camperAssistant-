"""
Configuration utilities for LLM Intent Detection.

This module provides utilities to read LLM intent detection configuration
from the main config.ini file and apply it to the system.
"""

import os
import configparser
import logging
from typing import Dict, Any, Optional

#----------------------------------------------------------------
# CONFIGURATION CONSTANTS
#----------------------------------------------------------------

DEFAULT_CONFIG = {
    'enabled': True,
    'confidence_threshold_high': 0.8,
    'confidence_threshold_low': 0.5,
    'timeout': 5.0,
    'cache_max_size': 100,
    'cache_ttl': 300.0
}

CONFIG_SECTION = 'llm_intent_detection'

#----------------------------------------------------------------
# CONFIGURATION FUNCTIONS
#----------------------------------------------------------------

def load_llm_intent_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load LLM intent detection configuration from config file.
    
    Args:
        config_path (Optional[str]): Path to config file. If None, looks for config.ini
                                   in the project root.
    
    Returns:
        Dict[str, Any]: Configuration dictionary with all required settings
    """
    config = DEFAULT_CONFIG.copy()
    
    try:
        # Determine config file path
        if config_path is None:
            # Look for config.ini in project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, 'config.ini')
        
        if not os.path.exists(config_path):
            logging.warning(f'[LLMIntentConfig] Config file not found at {config_path}, using defaults')
            return config
        
        # Read configuration file
        parser = configparser.ConfigParser()
        parser.read(config_path)
        
        if CONFIG_SECTION not in parser:
            logging.info(f'[LLMIntentConfig] Section [{CONFIG_SECTION}] not found in config, using defaults')
            return config
        
        section = parser[CONFIG_SECTION]
        
        # Parse configuration values with type conversion and validation
        config.update({
            'enabled': section.getboolean('enabled', DEFAULT_CONFIG['enabled']),
            'confidence_threshold_high': _parse_float_config(
                section, 'confidence_threshold_high', 
                DEFAULT_CONFIG['confidence_threshold_high'], 0.0, 1.0
            ),
            'confidence_threshold_low': _parse_float_config(
                section, 'confidence_threshold_low', 
                DEFAULT_CONFIG['confidence_threshold_low'], 0.0, 1.0
            ),
            'timeout': _parse_float_config(
                section, 'timeout', 
                DEFAULT_CONFIG['timeout'], 1.0, 30.0
            ),
            'cache_max_size': _parse_int_config(
                section, 'cache_max_size', 
                DEFAULT_CONFIG['cache_max_size'], 1, 1000
            ),
            'cache_ttl': _parse_float_config(
                section, 'cache_ttl', 
                DEFAULT_CONFIG['cache_ttl'], 60.0, 3600.0
            )
        })
        
        # Validate threshold relationship
        if config['confidence_threshold_high'] <= config['confidence_threshold_low']:
            logging.warning('[LLMIntentConfig] confidence_threshold_high must be > confidence_threshold_low, adjusting')
            config['confidence_threshold_high'] = config['confidence_threshold_low'] + 0.1
            config['confidence_threshold_high'] = min(1.0, config['confidence_threshold_high'])
        
        logging.info(f'[LLMIntentConfig] Loaded configuration from {config_path}')
        logging.debug(f'[LLMIntentConfig] Config: {config}')
        
        return config
        
    except Exception as e:
        logging.error(f'[LLMIntentConfig] Error loading configuration: {e}, using defaults')
        return DEFAULT_CONFIG.copy()

def _parse_float_config(section, key: str, default: float, min_val: float, max_val: float) -> float:
    """
    Parse a float configuration value with validation.
    
    Args:
        section: ConfigParser section object
        key (str): Configuration key
        default (float): Default value
        min_val (float): Minimum allowed value
        max_val (float): Maximum allowed value
    
    Returns:
        float: Parsed and validated value
    """
    try:
        value = section.getfloat(key, default)
        if value < min_val:
            logging.warning(f'[LLMIntentConfig] {key}={value} below minimum {min_val}, using {min_val}')
            return min_val
        elif value > max_val:
            logging.warning(f'[LLMIntentConfig] {key}={value} above maximum {max_val}, using {max_val}')
            return max_val
        return value
    except (ValueError, TypeError) as e:
        logging.warning(f'[LLMIntentConfig] Invalid {key} value, using default {default}: {e}')
        return default

def _parse_int_config(section, key: str, default: int, min_val: int, max_val: int) -> int:
    """
    Parse an integer configuration value with validation.
    
    Args:
        section: ConfigParser section object
        key (str): Configuration key
        default (int): Default value
        min_val (int): Minimum allowed value
        max_val (int): Maximum allowed value
    
    Returns:
        int: Parsed and validated value
    """
    try:
        value = section.getint(key, default)
        if value < min_val:
            logging.warning(f'[LLMIntentConfig] {key}={value} below minimum {min_val}, using {min_val}')
            return min_val
        elif value > max_val:
            logging.warning(f'[LLMIntentConfig] {key}={value} above maximum {max_val}, using {max_val}')
            return max_val
        return value
    except (ValueError, TypeError) as e:
        logging.warning(f'[LLMIntentConfig] Invalid {key} value, using default {default}: {e}')
        return default

def create_llm_intent_detector_from_config(ai_processor=None, config_path: Optional[str] = None):
    """
    Create an LLMIntentDetector instance using configuration from file.
    
    Args:
        ai_processor: AI processor instance to use
        config_path (Optional[str]): Path to config file
    
    Returns:
        LLMIntentDetector: Configured LLM intent detector instance
    """
    try:
        from .llm_intent_detector import LLMIntentDetector
        
        config = load_llm_intent_config(config_path)
        
        return LLMIntentDetector(
            ai_processor=ai_processor,
            enabled=config['enabled'],
            confidence_threshold_high=config['confidence_threshold_high'],
            confidence_threshold_low=config['confidence_threshold_low'],
            timeout=config['timeout'],
            cache_max_size=config['cache_max_size'],
            cache_ttl=config['cache_ttl']
        )
        
    except Exception as e:
        logging.error(f'[LLMIntentConfig] Error creating LLMIntentDetector from config: {e}')
        # Return a basic instance as fallback
        from .llm_intent_detector import LLMIntentDetector
        return LLMIntentDetector(ai_processor=ai_processor, enabled=False)

def get_config_summary() -> str:
    """
    Get a human-readable summary of the current LLM intent detection configuration.
    
    Returns:
        str: Configuration summary
    """
    config = load_llm_intent_config()
    
    summary = f"""LLM Intent Detection Configuration:
    - Enabled: {config['enabled']}
    - High Confidence Threshold: {config['confidence_threshold_high']:.1f}
    - Low Confidence Threshold: {config['confidence_threshold_low']:.1f}
    - Timeout: {config['timeout']:.1f}s
    - Cache Max Size: {config['cache_max_size']}
    - Cache TTL: {config['cache_ttl']:.0f}s"""
    
    return summary