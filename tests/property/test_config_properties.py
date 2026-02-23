"""
Property-based tests for configuration module.

Feature: http-auth-migration
"""

import os
import argparse
from hypothesis import given, strategies as st, settings
from config import ServerConfig


# Property 1: Configuration Precedence
# Validates: Requirements 5.4
@settings(max_examples=100)
@given(
    env_value=st.text(
        min_size=1, 
        max_size=50, 
        alphabet=st.characters(
            blacklist_characters='\x00',
            blacklist_categories=('Cs',)  # Exclude surrogate characters
        )
    ),
    cli_value=st.text(
        min_size=1, 
        max_size=50, 
        alphabet=st.characters(
            blacklist_characters='\x00',
            blacklist_categories=('Cs',)  # Exclude surrogate characters
        )
    )
)
def test_cli_args_override_environment_variables(env_value, cli_value):
    """
    Feature: http-auth-migration, Property 1: Configuration Precedence
    
    For any configuration parameter that can be set via both environment variable 
    and CLI argument, when both are provided, the CLI argument value should be used.
    
    Validates: Requirements 5.4
    """
    # Test with host parameter
    original_host = os.environ.get("MCP_HOST")
    try:
        # Set environment variable
        os.environ["MCP_HOST"] = env_value
        
        # Create args with CLI value
        args = argparse.Namespace(
            host=cli_value,
            port=None,
            auth_mode=None,
            transport=None
        )
        
        # Load config from CLI args (which merges with environment)
        config = ServerConfig.from_cli_args(args)
        
        # CLI value should win
        assert config.host == cli_value, \
            f"Expected CLI value '{cli_value}' but got '{config.host}'"
    
    finally:
        # Restore original environment
        if original_host is not None:
            os.environ["MCP_HOST"] = original_host
        elif "MCP_HOST" in os.environ:
            del os.environ["MCP_HOST"]


@settings(max_examples=100)
@given(
    env_port=st.integers(min_value=1, max_value=65535),
    cli_port=st.integers(min_value=1, max_value=65535)
)
def test_cli_port_overrides_environment_port(env_port, cli_port):
    """
    Feature: http-auth-migration, Property 1: Configuration Precedence
    
    For port configuration, when both environment variable and CLI argument 
    are provided, the CLI argument value should be used.
    
    Validates: Requirements 5.4
    """
    original_port = os.environ.get("MCP_PORT")
    try:
        # Set environment variable
        os.environ["MCP_PORT"] = str(env_port)
        
        # Create args with CLI value
        args = argparse.Namespace(
            host=None,
            port=cli_port,
            auth_mode=None,
            transport=None
        )
        
        # Load config from CLI args
        config = ServerConfig.from_cli_args(args)
        
        # CLI value should win
        assert config.port == cli_port, \
            f"Expected CLI port {cli_port} but got {config.port}"
    
    finally:
        # Restore original environment
        if original_port is not None:
            os.environ["MCP_PORT"] = original_port
        elif "MCP_PORT" in os.environ:
            del os.environ["MCP_PORT"]


@settings(max_examples=100)
@given(
    env_mode=st.sampled_from(["static", "jwt"]),
    cli_mode=st.sampled_from(["static", "jwt"])
)
def test_cli_auth_mode_overrides_environment_auth_mode(env_mode, cli_mode):
    """
    Feature: http-auth-migration, Property 1: Configuration Precedence
    
    For auth_mode configuration, when both environment variable and CLI argument 
    are provided, the CLI argument value should be used.
    
    Validates: Requirements 5.4
    """
    original_auth_mode = os.environ.get("MCP_AUTH_MODE")
    try:
        # Set environment variable
        os.environ["MCP_AUTH_MODE"] = env_mode
        
        # Create args with CLI value
        args = argparse.Namespace(
            host=None,
            port=None,
            auth_mode=cli_mode,
            transport=None
        )
        
        # Load config from CLI args
        config = ServerConfig.from_cli_args(args)
        
        # CLI value should win
        assert config.auth_mode == cli_mode, \
            f"Expected CLI auth_mode '{cli_mode}' but got '{config.auth_mode}'"
    
    finally:
        # Restore original environment
        if original_auth_mode is not None:
            os.environ["MCP_AUTH_MODE"] = original_auth_mode
        elif "MCP_AUTH_MODE" in os.environ:
            del os.environ["MCP_AUTH_MODE"]


@settings(max_examples=100)
@given(
    env_transport=st.sampled_from(["http", "stdio"]),
    cli_transport=st.sampled_from(["http", "stdio"])
)
def test_cli_transport_overrides_environment_transport(env_transport, cli_transport):
    """
    Feature: http-auth-migration, Property 1: Configuration Precedence
    
    For transport configuration, when both environment variable and CLI argument 
    are provided, the CLI argument value should be used.
    
    Validates: Requirements 5.4
    """
    original_transport = os.environ.get("MCP_TRANSPORT")
    try:
        # Set environment variable
        os.environ["MCP_TRANSPORT"] = env_transport
        
        # Create args with CLI value
        args = argparse.Namespace(
            host=None,
            port=None,
            auth_mode=None,
            transport=cli_transport
        )
        
        # Load config from CLI args
        config = ServerConfig.from_cli_args(args)
        
        # CLI value should win
        assert config.transport == cli_transport, \
            f"Expected CLI transport '{cli_transport}' but got '{config.transport}'"
    
    finally:
        # Restore original environment
        if original_transport is not None:
            os.environ["MCP_TRANSPORT"] = original_transport
        elif "MCP_TRANSPORT" in os.environ:
            del os.environ["MCP_TRANSPORT"]



# Property 4: Port Validation
# Validates: Requirements 2.6
@settings(max_examples=100)
@given(port=st.integers(min_value=1, max_value=65535))
def test_valid_ports_pass_validation(port):
    """
    Feature: http-auth-migration, Property 4: Port Validation
    
    For any port value that is an integer between 1 and 65535, 
    the validation should pass without raising an error.
    
    Validates: Requirements 2.6
    """
    config = ServerConfig(port=port, transport="stdio")
    
    # Should not raise any exception
    config.validate()


@settings(max_examples=100)
@given(
    port=st.one_of(
        st.integers(max_value=0),  # Below valid range
        st.integers(min_value=65536),  # Above valid range
    )
)
def test_invalid_ports_fail_validation(port):
    """
    Feature: http-auth-migration, Property 4: Port Validation
    
    For any port value that is not an integer between 1 and 65535,
    the validation should raise a ValueError with a descriptive message.
    
    Validates: Requirements 2.6
    """
    config = ServerConfig(port=port, transport="stdio")
    
    # Should raise ValueError
    try:
        config.validate()
        assert False, f"Expected ValueError for invalid port {port}, but validation passed"
    except ValueError as e:
        # Verify error message is descriptive
        assert "port" in str(e).lower(), \
            f"Error message should mention 'port': {str(e)}"
        assert str(port) in str(e) or "must be" in str(e).lower(), \
            f"Error message should be descriptive: {str(e)}"


@settings(max_examples=100)
@given(port_value=st.one_of(st.text(), st.floats(), st.none()))
def test_non_integer_ports_fail_validation(port_value):
    """
    Feature: http-auth-migration, Property 4: Port Validation
    
    For any port value that is not an integer type,
    the validation should raise a ValueError.
    
    Validates: Requirements 2.6
    """
    # Skip if the value happens to be convertible to a valid int
    if isinstance(port_value, (int, bool)):
        return
    
    config = ServerConfig(port=port_value, transport="stdio")
    
    # Should raise ValueError
    try:
        config.validate()
        assert False, f"Expected ValueError for non-integer port {port_value}, but validation passed"
    except ValueError as e:
        # Verify error message mentions port
        assert "port" in str(e).lower(), \
            f"Error message should mention 'port': {str(e)}"



# Property 5: Auth Mode Validation
# Validates: Requirements 2.3, 2.4, 5.3
@settings(max_examples=100)
@given(auth_mode=st.sampled_from(["static", "jwt"]))
def test_valid_auth_modes_pass_validation(auth_mode):
    """
    Feature: http-auth-migration, Property 5: Auth Mode Validation
    
    For any auth_mode value that is "static" or "jwt",
    the validation should pass without raising an error.
    
    Validates: Requirements 2.3, 2.4, 5.3
    """
    config = ServerConfig(auth_mode=auth_mode, transport="stdio")
    
    # Should not raise any exception
    config.validate()


@settings(max_examples=100)
@given(
    auth_mode=st.text(min_size=1, max_size=50).filter(
        lambda x: x not in ["static", "jwt"]
    )
)
def test_invalid_auth_modes_fail_validation(auth_mode):
    """
    Feature: http-auth-migration, Property 5: Auth Mode Validation
    
    For any auth_mode value that is not "static" or "jwt",
    the validation should raise a ValueError with a descriptive message.
    
    Validates: Requirements 2.3, 2.4, 5.3
    """
    config = ServerConfig(auth_mode=auth_mode, transport="stdio")
    
    # Should raise ValueError
    try:
        config.validate()
        assert False, f"Expected ValueError for invalid auth_mode '{auth_mode}', but validation passed"
    except ValueError as e:
        # Verify error message is descriptive
        error_msg = str(e).lower()
        assert "auth" in error_msg or "mode" in error_msg, \
            f"Error message should mention 'auth' or 'mode': {str(e)}"
        assert auth_mode in str(e) or "static" in error_msg or "jwt" in error_msg, \
            f"Error message should be descriptive and mention valid options: {str(e)}"
