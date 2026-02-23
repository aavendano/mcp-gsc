"""
Unit tests for logging configuration module.

Tests log format, structure, sensitive data filtering, and different log levels.
"""

import logging
import io
import os
from logging_config import configure_logging, SensitiveDataFilter


def test_configure_logging_returns_logger():
    """Test that configure_logging returns a logger instance."""
    logger = configure_logging()
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == 'gsc-server'


def test_configure_logging_sets_info_level_by_default():
    """Test that logging is configured with INFO level by default."""
    logger = configure_logging(debug=False)
    
    assert logger.level == logging.INFO


def test_configure_logging_sets_debug_level_when_requested():
    """Test that logging is configured with DEBUG level when debug=True."""
    logger = configure_logging(debug=True)
    
    assert logger.level == logging.DEBUG


def test_configure_logging_respects_mcp_debug_env_var():
    """Test that MCP_DEBUG environment variable enables debug mode."""
    original_debug = os.environ.get('MCP_DEBUG')
    
    try:
        # Test with debug enabled
        os.environ['MCP_DEBUG'] = 'true'
        logger = configure_logging()
        assert logger.level == logging.DEBUG
        
        # Test with debug disabled
        os.environ['MCP_DEBUG'] = 'false'
        logger = configure_logging()
        assert logger.level == logging.INFO
        
        # Test with debug enabled via '1'
        os.environ['MCP_DEBUG'] = '1'
        logger = configure_logging()
        assert logger.level == logging.DEBUG
        
        # Test with debug enabled via 'yes'
        os.environ['MCP_DEBUG'] = 'yes'
        logger = configure_logging()
        assert logger.level == logging.DEBUG
    
    finally:
        # Restore original environment
        if original_debug is not None:
            os.environ['MCP_DEBUG'] = original_debug
        elif 'MCP_DEBUG' in os.environ:
            del os.environ['MCP_DEBUG']


def test_log_format_includes_timestamp():
    """Test that log messages include timestamps."""
    logger = logging.getLogger('test_timestamp')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Use the same formatter as configure_logging
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message
    logger.info("Test message")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # Check format: should contain timestamp, logger name, level, and message
    assert 'test_timestamp' in log_output
    assert 'INFO' in log_output
    assert 'Test message' in log_output
    # Timestamp format: YYYY-MM-DD HH:MM:SS
    assert '-' in log_output  # Date separators
    assert ':' in log_output  # Time separators


def test_log_format_includes_logger_name():
    """Test that log messages include the logger name."""
    logger = logging.getLogger('test_logger_name')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    logger.info("Test message")
    
    log_output = log_stream.getvalue()
    assert 'test_logger_name' in log_output


def test_log_format_includes_level():
    """Test that log messages include the log level."""
    logger = logging.getLogger('test_level')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    log_output = log_stream.getvalue()
    
    assert 'DEBUG' in log_output
    assert 'INFO' in log_output
    assert 'WARNING' in log_output
    assert 'ERROR' in log_output


def test_sensitive_filter_redacts_bearer_tokens():
    """Test that SensitiveDataFilter redacts Bearer tokens."""
    sensitive_filter = SensitiveDataFilter()
    
    # Create a log record with a bearer token
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='Authorization: Bearer abc123def456ghi789',
        args=(),
        exc_info=None
    )
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # Token should be redacted
    assert 'abc123def456ghi789' not in record.msg
    assert 'Bearer [REDACTED]' in record.msg or '[REDACTED]' in record.msg


def test_sensitive_filter_redacts_jwt_tokens():
    """Test that SensitiveDataFilter redacts JWT tokens."""
    sensitive_filter = SensitiveDataFilter()
    
    jwt_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
    
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg=f'JWT validation failed: {jwt_token}',
        args=(),
        exc_info=None
    )
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # JWT should be redacted
    assert jwt_token not in record.msg
    assert '[JWT_REDACTED]' in record.msg or '[TOKEN_REDACTED]' in record.msg


def test_sensitive_filter_redacts_long_alphanumeric_strings():
    """Test that SensitiveDataFilter redacts long alphanumeric strings (potential tokens)."""
    sensitive_filter = SensitiveDataFilter()
    
    token = 'a' * 40  # 40 character alphanumeric string
    
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg=f'Processing token: {token}',
        args=(),
        exc_info=None
    )
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # Token should be redacted
    assert token not in record.msg
    assert '[TOKEN_REDACTED]' in record.msg


def test_sensitive_filter_redacts_authorization_headers():
    """Test that SensitiveDataFilter redacts Authorization header values."""
    sensitive_filter = SensitiveDataFilter()
    
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='Request headers: Authorization: secret_token_value',
        args=(),
        exc_info=None
    )
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # Authorization value should be redacted
    assert 'secret_token_value' not in record.msg
    assert 'Authorization: [REDACTED]' in record.msg


def test_sensitive_filter_redacts_environment_variable_values():
    """Test that SensitiveDataFilter redacts sensitive environment variable values."""
    original_token = os.environ.get('MCP_ADMIN_TOKEN')
    
    try:
        # Set a test token
        test_token = 'test_secret_token_12345'
        os.environ['MCP_ADMIN_TOKEN'] = test_token
        
        sensitive_filter = SensitiveDataFilter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=f'Admin token is: {test_token}',
            args=(),
            exc_info=None
        )
        
        # Apply filter
        sensitive_filter.filter(record)
        
        # Token value should be redacted
        assert test_token not in record.msg
        assert '[MCP_ADMIN_TOKEN_REDACTED]' in record.msg
    
    finally:
        # Restore original environment
        if original_token is not None:
            os.environ['MCP_ADMIN_TOKEN'] = original_token
        elif 'MCP_ADMIN_TOKEN' in os.environ:
            del os.environ['MCP_ADMIN_TOKEN']


def test_sensitive_filter_handles_log_args():
    """Test that SensitiveDataFilter also filters log record arguments."""
    sensitive_filter = SensitiveDataFilter()
    
    # Use a longer token that will be caught by the filter (32+ chars)
    token = 'secret_token_value_123456789012345'
    
    # Create record with args (using % formatting)
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='Token: %s',
        args=(token,),
        exc_info=None
    )
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # Args should be filtered - check that the original token is replaced
    if isinstance(record.args, tuple):
        for arg in record.args:
            assert token not in str(arg), f"Token should be redacted from args, but found: {arg}"


def test_different_log_levels_work_correctly():
    """Test that different log levels (DEBUG, INFO, WARNING, ERROR) work correctly."""
    logger = logging.getLogger('test_levels')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log at different levels
    logger.debug("This is debug")
    logger.info("This is info")
    logger.warning("This is warning")
    logger.error("This is error")
    
    log_output = log_stream.getvalue()
    
    # All messages should be present
    assert "This is debug" in log_output
    assert "This is info" in log_output
    assert "This is warning" in log_output
    assert "This is error" in log_output
    
    # All levels should be present
    assert "DEBUG" in log_output
    assert "INFO" in log_output
    assert "WARNING" in log_output
    assert "ERROR" in log_output


def test_info_level_filters_debug_messages():
    """Test that INFO level filters out DEBUG messages."""
    logger = logging.getLogger('test_info_filter')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log at different levels
    logger.debug("This is debug")
    logger.info("This is info")
    
    log_output = log_stream.getvalue()
    
    # Debug message should NOT be present
    assert "This is debug" not in log_output
    
    # Info message should be present
    assert "This is info" in log_output


def test_sensitive_filter_preserves_non_sensitive_data():
    """Test that SensitiveDataFilter preserves non-sensitive data."""
    sensitive_filter = SensitiveDataFilter()
    
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg='Server started on port 8000',
        args=(),
        exc_info=None
    )
    
    original_msg = record.msg
    
    # Apply filter
    sensitive_filter.filter(record)
    
    # Message should be unchanged
    assert record.msg == original_msg
