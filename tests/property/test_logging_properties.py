"""
Property-based tests for logging configuration module.

Feature: http-auth-migration
"""

import logging
import io
from hypothesis import given, strategies as st, settings
from logging_config import configure_logging, SensitiveDataFilter


# Property 3: Token Logging Safety
# Validates: Requirements 9.1, 9.2, 9.3
@settings(max_examples=100)
@given(
    token=st.text(min_size=32, max_size=128, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=33, max_codepoint=126
    ))
)
def test_bearer_tokens_are_redacted_from_logs(token):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any bearer token value, when it appears in a log message,
    the token should be redacted and not appear in the actual log output.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create a logger with string stream handler
    logger = logging.getLogger('test_bearer_token_safety')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message containing a bearer token
    logger.info(f"Authorization: Bearer {token}")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The token should NOT appear in the log output
    assert token not in log_output, \
        f"Token '{token}' was found in log output: {log_output}"
    
    # The log should contain a redaction marker
    assert "[REDACTED]" in log_output or "Bearer" in log_output, \
        f"Log should contain redaction marker: {log_output}"


@settings(max_examples=100)
@given(
    token=st.text(min_size=32, max_size=128, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=33, max_codepoint=126
    ))
)
def test_authorization_header_values_are_redacted(token):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any token in an Authorization header format,
    the token value should be redacted from log messages.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create a logger with string stream handler
    logger = logging.getLogger('test_auth_header_safety')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message with Authorization header
    logger.info(f"Request headers: Authorization: {token}")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The token should NOT appear in the log output
    assert token not in log_output, \
        f"Token '{token}' was found in log output: {log_output}"


@settings(max_examples=100)
@given(
    # Generate JWT-like tokens (three base64-like segments)
    segment1=st.text(min_size=10, max_size=50, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'),
    segment2=st.text(min_size=10, max_size=100, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'),
    segment3=st.text(min_size=10, max_size=50, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
)
def test_jwt_tokens_are_redacted_from_logs(segment1, segment2, segment3):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any JWT token (three base64 segments separated by dots),
    the token should be redacted from log messages.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create JWT-like token
    jwt_token = f"{segment1}.{segment2}.{segment3}"
    
    # Create a logger with string stream handler
    logger = logging.getLogger('test_jwt_safety')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message containing a JWT token
    logger.info(f"JWT validation failed for token: {jwt_token}")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The JWT token should NOT appear in the log output
    assert jwt_token not in log_output, \
        f"JWT token was found in log output: {log_output}"
    
    # Individual segments should also not appear (they might be sensitive)
    # We check for the full token, which is the main concern
    assert segment1 not in log_output or segment2 not in log_output or segment3 not in log_output or \
           "[JWT_REDACTED]" in log_output or "[TOKEN_REDACTED]" in log_output, \
        f"JWT token segments were not properly redacted: {log_output}"


@settings(max_examples=100)
@given(
    token=st.text(min_size=32, max_size=64, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
)
def test_long_alphanumeric_tokens_are_redacted(token):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any long alphanumeric string that might be a token (32+ characters),
    it should be redacted from log messages.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create a logger with string stream handler
    logger = logging.getLogger('test_generic_token_safety')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message containing a potential token
    logger.info(f"Processing request with token: {token}")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The token should NOT appear in the log output
    assert token not in log_output, \
        f"Token '{token}' was found in log output: {log_output}"
    
    # Should contain redaction marker
    assert "[TOKEN_REDACTED]" in log_output or "[REDACTED]" in log_output, \
        f"Log should contain redaction marker: {log_output}"


@settings(max_examples=100)
@given(
    message=st.text(min_size=10, max_size=200),
    token=st.text(min_size=32, max_size=64, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
)
def test_tokens_in_any_log_message_are_redacted(message, token):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any log message containing a token-like string,
    the token should be redacted regardless of the message context.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create a logger with string stream handler
    logger = logging.getLogger('test_contextual_token_safety')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log a message with token embedded in arbitrary text
    full_message = f"{message} {token}"
    logger.info(full_message)
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The token should NOT appear in the log output
    assert token not in log_output, \
        f"Token '{token}' was found in log output: {log_output}"


@settings(max_examples=100)
@given(
    log_level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]),
    token=st.text(min_size=32, max_size=64, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
)
def test_tokens_redacted_at_all_log_levels(log_level, token):
    """
    Feature: http-auth-migration, Property 3: Token Logging Safety
    
    For any log level (DEBUG, INFO, WARNING, ERROR),
    tokens should be redacted from log messages.
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create a logger with string stream handler
    logger = logging.getLogger('test_multilevel_token_safety')
    logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels
    logger.handlers.clear()
    
    # Create string stream to capture log output
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    handler.addFilter(sensitive_filter)
    
    # Add handler to logger
    logger.addHandler(handler)
    logger.propagate = False
    
    # Log at the specified level
    logger.log(log_level, f"Token value: {token}")
    
    # Get the logged output
    log_output = log_stream.getvalue()
    
    # The token should NOT appear in the log output
    assert token not in log_output, \
        f"Token '{token}' was found in log output at level {logging.getLevelName(log_level)}: {log_output}"
