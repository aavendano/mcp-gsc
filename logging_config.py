"""
Logging configuration module for the Google Search Console MCP server.

This module provides structured logging with security features to prevent
exposure of sensitive authentication tokens and credentials.
"""

import logging
import os
import sys
import re
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that removes sensitive data from log messages.
    
    This filter prevents bearer tokens, API keys, and other sensitive
    credentials from being logged, which is critical for security.
    
    Security Rationale:
    - Logs are often stored in plain text and may be accessible to multiple users
    - Tokens in logs can be extracted and used for unauthorized access
    - Compliance requirements (PCI-DSS, GDPR, etc.) often prohibit logging credentials
    - Defense in depth: Even if other security measures fail, tokens won't be in logs
    
    The filter uses multiple strategies:
    1. Pattern matching for common token formats (Bearer, JWT, API keys)
    2. Environment variable value replacement
    3. Generic long alphanumeric string detection
    
    All sensitive data is replaced with redaction markers like [REDACTED] or [TOKEN_REDACTED].
    """
    
    # Patterns to detect and redact sensitive data
    SENSITIVE_PATTERNS = [
        # Bearer tokens in Authorization headers
        (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), 'Bearer [REDACTED]'),
        # JWT tokens (three base64 segments separated by dots)
        (re.compile(r'\b[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b'), '[JWT_REDACTED]'),
        # Generic tokens (long alphanumeric strings that might be tokens, including underscores and hyphens)
        (re.compile(r'\b[A-Za-z0-9_-]{32,}\b'), '[TOKEN_REDACTED]'),
        # Authorization header values
        (re.compile(r'Authorization:\s*[^\s]+', re.IGNORECASE), 'Authorization: [REDACTED]'),
        # API keys
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9\-_]+', re.IGNORECASE), 'api_key=[REDACTED]'),
    ]
    
    # Environment variable names that contain sensitive data
    SENSITIVE_ENV_VARS = [
        'MCP_ADMIN_TOKEN',
        'JWT_JWKS_URI',
        'JWT_ISSUER',
        'JWT_AUDIENCE',
        'GSC_CREDENTIALS_PATH',
        'GSC_OAUTH_CLIENT_SECRETS_FILE',
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to remove sensitive data.
        
        Args:
            record: Log record to filter
            
        Returns:
            True to allow the record to be logged (always returns True after filtering)
        """
        # Filter the main message
        if isinstance(record.msg, str):
            record.msg = self._redact_sensitive_data(record.msg)
        
        # Filter arguments if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._redact_sensitive_data(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact_sensitive_data(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        return True
    
    def _redact_sensitive_data(self, text: str) -> str:
        """
        Redact sensitive data from text using pattern matching.
        
        Args:
            text: Text to redact
            
        Returns:
            Text with sensitive data redacted
        """
        result = text
        
        # Apply all sensitive patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        
        # Redact sensitive environment variable values
        for env_var in self.SENSITIVE_ENV_VARS:
            value = os.environ.get(env_var)
            if value and value in result:
                result = result.replace(value, f'[{env_var}_REDACTED]')
        
        return result


def configure_logging(debug: Optional[bool] = None) -> logging.Logger:
    """
    Configure logging with appropriate format and level.
    
    Sets up structured logging with:
    - Timestamps for all log messages
    - Appropriate log levels (INFO, WARNING, ERROR, DEBUG)
    - Security filtering to prevent token exposure
    - Optional debug mode via environment variable or parameter
    
    Args:
        debug: Optional boolean to enable debug mode. If None, checks MCP_DEBUG env var.
        
    Returns:
        Configured logger instance for the application
    """
    # Determine debug mode
    if debug is None:
        debug = os.environ.get('MCP_DEBUG', '').lower() in ('true', '1', 'yes')
    
    # Set log level based on debug mode
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create logger
    logger = logging.getLogger('gsc-server')
    logger.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter with timestamps
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Log initial configuration
    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
    if debug:
        logger.debug("Debug mode enabled")
    
    return logger
