"""
Unit tests for authentication factory module.

Feature: http-auth-migration
"""

import pytest
from config import ServerConfig
from auth import create_auth_verifier


class TestStaticTokenVerifier:
    """Tests for StaticTokenVerifier creation."""
    
    def test_static_verifier_creation_with_valid_config(self):
        """
        Test that StaticTokenVerifier is created successfully with valid configuration.
        
        Requirements: 3.1, 3.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="http",
            admin_token="test-token-123"
        )
        
        verifier = create_auth_verifier(config)
        
        # Verify verifier was created
        assert verifier is not None
        # Verify it's the correct type
        assert verifier.__class__.__name__ == "StaticTokenVerifier"
    
    def test_static_verifier_fails_without_admin_token(self):
        """
        Test that StaticTokenVerifier creation fails when admin_token is missing.
        
        Requirements: 3.1, 3.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="http",
            admin_token=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "MCP_ADMIN_TOKEN" in error_msg or "admin" in error_msg.lower()
        assert "required" in error_msg.lower() or "require" in error_msg.lower()
    
    def test_static_verifier_with_empty_token(self):
        """
        Test that StaticTokenVerifier creation fails with empty admin_token.
        
        Requirements: 3.1, 3.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="http",
            admin_token=""
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "MCP_ADMIN_TOKEN" in error_msg or "admin" in error_msg.lower()


class TestJWTVerifier:
    """Tests for JWTVerifier creation."""
    
    def test_jwt_verifier_creation_with_valid_config(self):
        """
        Test that JWTVerifier is created successfully with valid configuration.
        
        Requirements: 4.1, 4.2, 4.3
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer="https://example.com",
            jwt_audience="my-api"
        )
        
        verifier = create_auth_verifier(config)
        
        # Verify verifier was created
        assert verifier is not None
        # Verify it's the correct type
        assert verifier.__class__.__name__ == "JWTVerifier"
    
    def test_jwt_verifier_fails_without_jwks_uri(self):
        """
        Test that JWTVerifier creation fails when jwks_uri is missing.
        
        Requirements: 4.1
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri=None,
            jwt_issuer="https://example.com",
            jwt_audience="my-api"
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "JWT_JWKS_URI" in error_msg
        assert "JWT" in error_msg
    
    def test_jwt_verifier_fails_without_issuer(self):
        """
        Test that JWTVerifier creation fails when jwt_issuer is missing.
        
        Requirements: 4.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer=None,
            jwt_audience="my-api"
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "JWT_ISSUER" in error_msg
        assert "JWT" in error_msg
    
    def test_jwt_verifier_fails_without_audience(self):
        """
        Test that JWTVerifier creation fails when jwt_audience is missing.
        
        Requirements: 4.3
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer="https://example.com",
            jwt_audience=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "JWT_AUDIENCE" in error_msg
        assert "JWT" in error_msg
    
    def test_jwt_verifier_fails_with_all_fields_missing(self):
        """
        Test that JWTVerifier creation fails with all JWT fields missing.
        Error message should list all required fields.
        
        Requirements: 4.1, 4.2, 4.3
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri=None,
            jwt_issuer=None,
            jwt_audience=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        # All three fields should be mentioned
        assert "JWT_JWKS_URI" in error_msg
        assert "JWT_ISSUER" in error_msg
        assert "JWT_AUDIENCE" in error_msg
    
    def test_jwt_verifier_with_optional_scopes(self):
        """
        Test that JWTVerifier is created with optional required_scopes.
        
        Requirements: 4.1, 4.2, 4.3
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer="https://example.com",
            jwt_audience="my-api",
            jwt_required_scopes=["read:data", "write:data"]
        )
        
        verifier = create_auth_verifier(config)
        
        # Verify verifier was created
        assert verifier is not None
        assert verifier.__class__.__name__ == "JWTVerifier"


class TestSTDIOTransport:
    """Tests for STDIO transport (no authentication)."""
    
    def test_stdio_transport_returns_none(self):
        """
        Test that STDIO transport returns None (no authentication needed).
        
        Requirements: 3.1, 3.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="stdio",
            admin_token=None  # No token needed for STDIO
        )
        
        verifier = create_auth_verifier(config)
        
        # STDIO should return None
        assert verifier is None
    
    def test_stdio_transport_ignores_auth_mode(self):
        """
        Test that STDIO transport returns None regardless of auth_mode.
        
        Requirements: 3.1, 3.2
        """
        # Test with static mode
        config_static = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="stdio"
        )
        assert create_auth_verifier(config_static) is None
        
        # Test with jwt mode
        config_jwt = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="stdio"
        )
        assert create_auth_verifier(config_jwt) is None


class TestInvalidAuthMode:
    """Tests for invalid auth_mode values."""
    
    def test_invalid_auth_mode_raises_error(self):
        """
        Test that invalid auth_mode raises ValueError.
        
        Requirements: 3.1
        """
        # Note: This should be caught by config validation first,
        # but we test the auth factory's handling as well
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="oauth",  # Invalid mode
            transport="http",
            admin_token="test-token"
        )
        
        # Skip validation to test auth factory directly
        with pytest.raises(ValueError) as exc_info:
            create_auth_verifier(config)
        
        error_msg = str(exc_info.value)
        assert "auth_mode" in error_msg.lower() or "invalid" in error_msg.lower()
