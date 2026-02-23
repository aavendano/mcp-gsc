"""
Property-based tests for server initialization module.

Feature: http-auth-migration
"""

import pytest
from hypothesis import given, strategies as st, settings
from config import ServerConfig
from server import initialize_server
from mcp.server.fastmcp import FastMCP


# Property 8: Transport Mode Functionality
# Validates: Requirements 8.5
# Note: This property tests that server initialization works correctly for both transports.
# Full end-to-end tool functionality testing requires integration tests.
@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    transport=st.sampled_from(["http", "stdio"]),
    admin_token=st.text(min_size=10, max_size=100, alphabet=st.characters(blacklist_characters='\x00'))
)
def test_server_initializes_for_both_transports(host, port, transport, admin_token):
    """
    Feature: http-auth-migration, Property 8: Transport Mode Functionality
    
    For any valid server configuration, the server should initialize successfully
    regardless of whether transport is "stdio" or "http".
    
    This validates that the initialization logic handles both transport modes correctly.
    Full tool functionality testing is covered by integration tests.
    
    Validates: Requirements 8.5
    """
    # Create config for the specified transport
    if transport == "http":
        config = ServerConfig(
            host=host,
            port=port,
            auth_mode="static",
            transport=transport,
            admin_token=admin_token  # HTTP requires auth
        )
    else:
        # STDIO doesn't require auth
        config = ServerConfig(
            host=host,
            port=port,
            auth_mode="static",
            transport=transport,
            admin_token=None
        )
    
    # Create a test MCP instance
    test_mcp = FastMCP("test-server")
    
    # Should successfully initialize server for both transports
    initialized_mcp = initialize_server(config, test_mcp)
    
    # Verify server was initialized
    assert initialized_mcp is not None, \
        f"Server should initialize successfully for {transport} transport"
    assert isinstance(initialized_mcp, FastMCP), \
        f"Initialized server should be a FastMCP instance for {transport} transport"


# Property 9: STDIO No-Auth Requirement
# Validates: Requirements 8.4
@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    auth_mode=st.sampled_from(["static", "jwt"])
)
def test_stdio_transport_does_not_require_auth_config(host, port, auth_mode):
    """
    Feature: http-auth-migration, Property 9: STDIO No-Auth Requirement
    
    For any server configuration with transport="stdio",
    the server should initialize successfully without requiring authentication configuration,
    regardless of the auth_mode setting.
    
    Validates: Requirements 8.4
    """
    # Create config with STDIO transport and no auth configuration
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode=auth_mode,  # Auth mode is set but shouldn't matter for STDIO
        transport="stdio",
        admin_token=None,  # No static token
        jwks_uri=None,  # No JWT config
        jwt_issuer=None,
        jwt_audience=None
    )
    
    # Create a test MCP instance
    test_mcp = FastMCP("test-server")
    
    # Should successfully initialize server without auth config
    initialized_mcp = initialize_server(config, test_mcp)
    
    # Verify server was initialized
    assert initialized_mcp is not None, \
        "Server should initialize successfully for STDIO transport without auth config"
    assert isinstance(initialized_mcp, FastMCP), \
        "Initialized server should be a FastMCP instance"


@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535)
)
def test_stdio_transport_with_various_auth_modes(host, port):
    """
    Feature: http-auth-migration, Property 9: STDIO No-Auth Requirement
    
    For any server configuration with transport="stdio",
    the server should initialize successfully with any auth_mode value,
    since authentication is not used for STDIO transport.
    
    Validates: Requirements 8.4
    """
    # Test with both valid auth modes
    for auth_mode in ["static", "jwt"]:
        config = ServerConfig(
            host=host,
            port=port,
            auth_mode=auth_mode,
            transport="stdio",
            admin_token=None,
            jwks_uri=None,
            jwt_issuer=None,
            jwt_audience=None
        )
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Should successfully initialize server
        initialized_mcp = initialize_server(config, test_mcp)
        
        # Verify server was initialized
        assert initialized_mcp is not None, \
            f"Server should initialize successfully for STDIO transport with auth_mode={auth_mode}"
        assert isinstance(initialized_mcp, FastMCP), \
            f"Initialized server should be a FastMCP instance with auth_mode={auth_mode}"


@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    admin_token=st.text(min_size=10, max_size=100, alphabet=st.characters(blacklist_characters='\x00'))
)
def test_http_transport_requires_auth_config(host, port, admin_token):
    """
    Feature: http-auth-migration, Property 9: STDIO No-Auth Requirement
    
    For any server configuration with transport="http",
    the server should require authentication configuration.
    This is the inverse of the STDIO no-auth requirement.
    
    Validates: Requirements 8.4
    """
    # Create config with HTTP transport and proper auth
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",
        transport="http",
        admin_token=admin_token
    )
    
    # Create a test MCP instance
    test_mcp = FastMCP("test-server")
    
    # Should successfully initialize server with auth
    initialized_mcp = initialize_server(config, test_mcp)
    
    # Verify server was initialized
    assert initialized_mcp is not None, \
        "Server should initialize successfully for HTTP transport with auth config"
    assert isinstance(initialized_mcp, FastMCP), \
        "Initialized server should be a FastMCP instance"
    
    # Now test that HTTP without auth config fails
    config_no_auth = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",
        transport="http",
        admin_token=None  # No auth token
    )
    
    # Should raise ValueError when trying to initialize without auth
    with pytest.raises(ValueError):
        initialize_server(config_no_auth, FastMCP("test-server-2"))
