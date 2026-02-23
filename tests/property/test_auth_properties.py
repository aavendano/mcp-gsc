"""
Property-based tests for authentication factory module.

Feature: http-auth-migration
"""

import os
import pytest
from hypothesis import given, strategies as st, settings, assume
from config import ServerConfig
from auth import create_auth_verifier


# Property 6: Static Auth Token Requirement
# Validates: Requirements 3.1, 3.2
@settings(max_examples=100)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535)
)
def test_static_auth_requires_admin_token(host, port):
    """
    Feature: http-auth-migration, Property 6: Static Auth Token Requirement
    
    For any server configuration with auth_mode="static" and transport="http",
    if MCP_ADMIN_TOKEN is not set, the server should raise a ValueError before starting.
    
    Validates: Requirements 3.1, 3.2
    """
    # Create config with static auth mode and HTTP transport, but no admin token
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",
        transport="http",
        admin_token=None  # No token provided
    )
    
    # Should raise ValueError when trying to create auth verifier
    with pytest.raises(ValueError) as exc_info:
        create_auth_verifier(config)
    
    # Verify error message mentions the required token
    error_msg = str(exc_info.value).lower()
    assert "mcp_admin_token" in error_msg or "admin" in error_msg or "token" in error_msg, \
        f"Error message should mention MCP_ADMIN_TOKEN: {str(exc_info.value)}"
    assert "required" in error_msg or "missing" in error_msg, \
        f"Error message should indicate token is required: {str(exc_info.value)}"


@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    admin_token=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters='\x00'))
)
def test_static_auth_succeeds_with_admin_token(host, port, admin_token):
    """
    Feature: http-auth-migration, Property 6: Static Auth Token Requirement
    
    For any server configuration with auth_mode="static" and transport="http",
    if MCP_ADMIN_TOKEN is set, the auth verifier should be created successfully.
    
    Validates: Requirements 3.1, 3.2
    """
    # Create config with static auth mode, HTTP transport, and admin token
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",
        transport="http",
        admin_token=admin_token
    )
    
    # Should successfully create auth verifier without raising exception
    verifier = create_auth_verifier(config)
    
    # Verify verifier was created (not None)
    assert verifier is not None, \
        "Auth verifier should be created when admin_token is provided"


@settings(max_examples=100)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535)
)
def test_stdio_transport_does_not_require_admin_token(host, port):
    """
    Feature: http-auth-migration, Property 6: Static Auth Token Requirement
    
    For any server configuration with transport="stdio",
    the server should start successfully without requiring admin_token,
    regardless of auth_mode setting.
    
    Validates: Requirements 3.1, 3.2
    """
    # Create config with STDIO transport and no admin token
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",  # Auth mode is set but shouldn't matter for STDIO
        transport="stdio",
        admin_token=None  # No token provided
    )
    
    # Should return None for STDIO transport (no auth needed)
    verifier = create_auth_verifier(config)
    
    # Verify no verifier is created for STDIO
    assert verifier is None, \
        "STDIO transport should not require authentication (verifier should be None)"



# Property 7: JWT Configuration Completeness
# Validates: Requirements 4.1, 4.2, 4.3
@settings(max_examples=100)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    # Generate configurations with at least one missing field
    missing_field=st.sampled_from(["jwks_uri", "jwt_issuer", "jwt_audience"])
)
def test_jwt_auth_requires_all_configuration_fields(host, port, missing_field):
    """
    Feature: http-auth-migration, Property 7: JWT Configuration Completeness
    
    For any server configuration with auth_mode="jwt",
    if any of JWT_JWKS_URI, JWT_ISSUER, or JWT_AUDIENCE is missing,
    the server should raise a ValueError before starting.
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    # Create a config with JWT auth mode but one missing field
    config_params = {
        "host": host,
        "port": port,
        "auth_mode": "jwt",
        "transport": "http",
        "jwks_uri": "https://example.com/.well-known/jwks.json",
        "jwt_issuer": "https://example.com",
        "jwt_audience": "my-api"
    }
    
    # Remove the specified field
    config_params[missing_field] = None
    
    config = ServerConfig(**config_params)
    
    # Should raise ValueError when trying to create auth verifier
    with pytest.raises(ValueError) as exc_info:
        create_auth_verifier(config)
    
    # Verify error message mentions the missing field
    error_msg = str(exc_info.value)
    assert "JWT" in error_msg or "jwt" in error_msg.lower(), \
        f"Error message should mention JWT: {error_msg}"
    assert "require" in error_msg.lower() or "missing" in error_msg.lower(), \
        f"Error message should indicate fields are required: {error_msg}"
    
    # Check that the specific missing field is mentioned
    field_name_map = {
        "jwks_uri": "JWKS_URI",
        "jwt_issuer": "ISSUER",
        "jwt_audience": "AUDIENCE"
    }
    expected_field_name = field_name_map[missing_field]
    assert expected_field_name in error_msg, \
        f"Error message should mention the missing field {expected_field_name}: {error_msg}"


@settings(max_examples=100, deadline=None)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535),
    jwks_uri=st.just("https://example.com/.well-known/jwks.json") | st.just("https://auth.example.com/jwks"),
    jwt_issuer=st.just("https://example.com") | st.just("https://auth.example.com"),
    jwt_audience=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters='\x00'))
)
def test_jwt_auth_succeeds_with_complete_configuration(host, port, jwks_uri, jwt_issuer, jwt_audience):
    """
    Feature: http-auth-migration, Property 7: JWT Configuration Completeness
    
    For any server configuration with auth_mode="jwt",
    if all of JWT_JWKS_URI, JWT_ISSUER, and JWT_AUDIENCE are provided,
    the auth verifier should be created successfully.
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    # Create config with JWT auth mode and all required fields
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="jwt",
        transport="http",
        jwks_uri=jwks_uri,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience
    )
    
    # Should successfully create auth verifier without raising exception
    verifier = create_auth_verifier(config)
    
    # Verify verifier was created (not None)
    assert verifier is not None, \
        "Auth verifier should be created when all JWT fields are provided"


@settings(max_examples=100)
@given(
    host=st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters='\x00')),
    port=st.integers(min_value=1, max_value=65535)
)
def test_jwt_auth_with_all_fields_missing(host, port):
    """
    Feature: http-auth-migration, Property 7: JWT Configuration Completeness
    
    For any server configuration with auth_mode="jwt",
    if all JWT configuration fields are missing,
    the error message should list all required fields.
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    # Create config with JWT auth mode but no JWT fields
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="jwt",
        transport="http",
        jwks_uri=None,
        jwt_issuer=None,
        jwt_audience=None
    )
    
    # Should raise ValueError when trying to create auth verifier
    with pytest.raises(ValueError) as exc_info:
        create_auth_verifier(config)
    
    # Verify error message mentions all three required fields
    error_msg = str(exc_info.value)
    assert "JWT_JWKS_URI" in error_msg, \
        f"Error message should mention JWT_JWKS_URI: {error_msg}"
    assert "JWT_ISSUER" in error_msg, \
        f"Error message should mention JWT_ISSUER: {error_msg}"
    assert "JWT_AUDIENCE" in error_msg, \
        f"Error message should mention JWT_AUDIENCE: {error_msg}"
