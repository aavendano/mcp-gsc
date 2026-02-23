"""
Unit tests for configuration module.

Tests specific examples, edge cases, and error conditions for ServerConfig.
"""

import os
import argparse
import pytest
from config import ServerConfig


class TestServerConfigEnvironment:
    """Test environment variable parsing."""
    
    def test_from_environment_with_defaults(self):
        """Test that default values are used when no environment variables are set."""
        # Clear relevant environment variables
        env_vars = ["MCP_HOST", "MCP_PORT", "MCP_AUTH_MODE", "MCP_TRANSPORT", 
                    "MCP_ADMIN_TOKEN", "JWT_JWKS_URI", "JWT_ISSUER", 
                    "JWT_AUDIENCE", "JWT_REQUIRED_SCOPES"]
        
        original_values = {}
        for var in env_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            config = ServerConfig.from_environment()
            
            assert config.host == "0.0.0.0"
            assert config.port == 8000
            assert config.auth_mode == "static"
            assert config.transport == "http"
            assert config.admin_token is None
            assert config.jwks_uri is None
            assert config.jwt_issuer is None
            assert config.jwt_audience is None
            assert config.jwt_required_scopes == []
        
        finally:
            # Restore original environment
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
    
    def test_from_environment_with_custom_values(self):
        """Test that environment variables override defaults."""
        original_values = {
            "MCP_HOST": os.environ.get("MCP_HOST"),
            "MCP_PORT": os.environ.get("MCP_PORT"),
            "MCP_AUTH_MODE": os.environ.get("MCP_AUTH_MODE"),
            "MCP_TRANSPORT": os.environ.get("MCP_TRANSPORT"),
            "MCP_ADMIN_TOKEN": os.environ.get("MCP_ADMIN_TOKEN"),
        }
        
        try:
            os.environ["MCP_HOST"] = "127.0.0.1"
            os.environ["MCP_PORT"] = "9000"
            os.environ["MCP_AUTH_MODE"] = "jwt"
            os.environ["MCP_TRANSPORT"] = "stdio"
            os.environ["MCP_ADMIN_TOKEN"] = "test-token-123"
            
            config = ServerConfig.from_environment()
            
            assert config.host == "127.0.0.1"
            assert config.port == 9000
            assert config.auth_mode == "jwt"
            assert config.transport == "stdio"
            assert config.admin_token == "test-token-123"
        
        finally:
            # Restore original environment
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
    
    def test_from_environment_with_jwt_scopes(self):
        """Test parsing of JWT required scopes from environment."""
        original_value = os.environ.get("JWT_REQUIRED_SCOPES")
        
        try:
            os.environ["JWT_REQUIRED_SCOPES"] = "read:gsc,write:gsc,admin"
            
            config = ServerConfig.from_environment()
            
            assert config.jwt_required_scopes == ["read:gsc", "write:gsc", "admin"]
        
        finally:
            if original_value is not None:
                os.environ["JWT_REQUIRED_SCOPES"] = original_value
            elif "JWT_REQUIRED_SCOPES" in os.environ:
                del os.environ["JWT_REQUIRED_SCOPES"]
    
    def test_from_environment_with_invalid_port(self):
        """Test that invalid port in environment falls back to default."""
        original_value = os.environ.get("MCP_PORT")
        
        try:
            os.environ["MCP_PORT"] = "invalid"
            
            config = ServerConfig.from_environment()
            
            # Should fall back to default
            assert config.port == 8000
        
        finally:
            if original_value is not None:
                os.environ["MCP_PORT"] = original_value
            elif "MCP_PORT" in os.environ:
                del os.environ["MCP_PORT"]


class TestServerConfigCLI:
    """Test CLI argument parsing and precedence."""
    
    def test_from_cli_args_overrides_environment(self):
        """Test that CLI arguments override environment variables."""
        original_values = {
            "MCP_HOST": os.environ.get("MCP_HOST"),
            "MCP_PORT": os.environ.get("MCP_PORT"),
        }
        
        try:
            # Set environment variables
            os.environ["MCP_HOST"] = "0.0.0.0"
            os.environ["MCP_PORT"] = "8000"
            
            # Create CLI args that override
            args = argparse.Namespace(
                host="192.168.1.1",
                port=3000,
                auth_mode=None,
                transport=None
            )
            
            config = ServerConfig.from_cli_args(args)
            
            # CLI values should win
            assert config.host == "192.168.1.1"
            assert config.port == 3000
        
        finally:
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
    
    def test_from_cli_args_with_none_values(self):
        """Test that None CLI args don't override environment."""
        original_value = os.environ.get("MCP_HOST")
        
        try:
            os.environ["MCP_HOST"] = "10.0.0.1"
            
            args = argparse.Namespace(
                host=None,  # Not provided
                port=None,
                auth_mode=None,
                transport=None
            )
            
            config = ServerConfig.from_cli_args(args)
            
            # Environment value should be used
            assert config.host == "10.0.0.1"
        
        finally:
            if original_value is not None:
                os.environ["MCP_HOST"] = original_value
            elif "MCP_HOST" in os.environ:
                del os.environ["MCP_HOST"]


class TestServerConfigValidation:
    """Test validation logic."""
    
    def test_validate_with_stdio_transport_no_auth_required(self):
        """Test that STDIO transport doesn't require authentication."""
        config = ServerConfig(transport="stdio")
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_http_static_auth_requires_token(self):
        """Test that HTTP with static auth requires admin token."""
        config = ServerConfig(
            transport="http",
            auth_mode="static",
            admin_token=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "MCP_ADMIN_TOKEN" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()
    
    def test_validate_http_static_auth_with_token_succeeds(self):
        """Test that HTTP with static auth and token passes validation."""
        config = ServerConfig(
            transport="http",
            auth_mode="static",
            admin_token="test-token"
        )
        
        # Should not raise
        config.validate()
    
    def test_validate_http_jwt_auth_requires_all_fields(self):
        """Test that HTTP with JWT auth requires all JWT fields."""
        # Missing all JWT fields
        config = ServerConfig(
            transport="http",
            auth_mode="jwt",
            jwks_uri=None,
            jwt_issuer=None,
            jwt_audience=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value)
        assert "JWT_JWKS_URI" in error_msg
        assert "JWT_ISSUER" in error_msg
        assert "JWT_AUDIENCE" in error_msg
    
    def test_validate_http_jwt_auth_missing_one_field(self):
        """Test that missing even one JWT field causes validation to fail."""
        config = ServerConfig(
            transport="http",
            auth_mode="jwt",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer="https://example.com",
            jwt_audience=None  # Missing this one
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "JWT_AUDIENCE" in str(exc_info.value)
    
    def test_validate_http_jwt_auth_with_all_fields_succeeds(self):
        """Test that HTTP with JWT auth and all fields passes validation."""
        config = ServerConfig(
            transport="http",
            auth_mode="jwt",
            jwks_uri="https://example.com/.well-known/jwks.json",
            jwt_issuer="https://example.com",
            jwt_audience="my-api"
        )
        
        # Should not raise
        config.validate()
    
    def test_validate_invalid_port_zero(self):
        """Test that port 0 fails validation."""
        config = ServerConfig(port=0, transport="stdio")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "port" in str(exc_info.value).lower()
        assert "0" in str(exc_info.value)
    
    def test_validate_invalid_port_negative(self):
        """Test that negative port fails validation."""
        config = ServerConfig(port=-1, transport="stdio")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "port" in str(exc_info.value).lower()
    
    def test_validate_invalid_port_too_large(self):
        """Test that port > 65535 fails validation."""
        config = ServerConfig(port=65536, transport="stdio")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "port" in str(exc_info.value).lower()
        assert "65535" in str(exc_info.value)
    
    def test_validate_invalid_auth_mode(self):
        """Test that invalid auth_mode fails validation."""
        config = ServerConfig(auth_mode="oauth", transport="stdio")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        error_msg = str(exc_info.value).lower()
        assert "auth" in error_msg or "mode" in error_msg
        assert "oauth" in str(exc_info.value)
    
    def test_validate_invalid_transport(self):
        """Test that invalid transport fails validation."""
        config = ServerConfig(transport="websocket")
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "transport" in str(exc_info.value).lower()
        assert "websocket" in str(exc_info.value)


class TestServerConfigDefaults:
    """Test default values."""
    
    def test_default_values(self):
        """Test that ServerConfig has correct default values."""
        config = ServerConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.auth_mode == "static"
        assert config.transport == "http"
        assert config.admin_token is None
        assert config.jwks_uri is None
        assert config.jwt_issuer is None
        assert config.jwt_audience is None
        assert config.jwt_required_scopes == []



class TestCLIArgumentParser:
    """Test CLI argument parser functionality."""
    
    def test_parse_arguments_with_no_args(self):
        """Test parsing with no arguments returns defaults (None values)."""
        from config import parse_arguments
        
        args = parse_arguments([])
        
        # All should be None (will fall back to environment or defaults)
        assert args.host is None
        assert args.port is None
        assert args.auth_mode is None
        assert args.transport is None
    
    def test_parse_arguments_with_host(self):
        """Test parsing --host argument."""
        from config import parse_arguments
        
        args = parse_arguments(["--host", "192.168.1.100"])
        
        assert args.host == "192.168.1.100"
        assert args.port is None
        assert args.auth_mode is None
        assert args.transport is None
    
    def test_parse_arguments_with_port(self):
        """Test parsing --port argument."""
        from config import parse_arguments
        
        args = parse_arguments(["--port", "9000"])
        
        assert args.host is None
        assert args.port == 9000
        assert args.auth_mode is None
        assert args.transport is None
    
    def test_parse_arguments_with_auth_mode_static(self):
        """Test parsing --auth-mode static."""
        from config import parse_arguments
        
        args = parse_arguments(["--auth-mode", "static"])
        
        assert args.host is None
        assert args.port is None
        assert args.auth_mode == "static"
        assert args.transport is None
    
    def test_parse_arguments_with_auth_mode_jwt(self):
        """Test parsing --auth-mode jwt."""
        from config import parse_arguments
        
        args = parse_arguments(["--auth-mode", "jwt"])
        
        assert args.host is None
        assert args.port is None
        assert args.auth_mode == "jwt"
        assert args.transport is None
    
    def test_parse_arguments_with_transport_http(self):
        """Test parsing --transport http."""
        from config import parse_arguments
        
        args = parse_arguments(["--transport", "http"])
        
        assert args.host is None
        assert args.port is None
        assert args.auth_mode is None
        assert args.transport == "http"
    
    def test_parse_arguments_with_transport_stdio(self):
        """Test parsing --transport stdio."""
        from config import parse_arguments
        
        args = parse_arguments(["--transport", "stdio"])
        
        assert args.host is None
        assert args.port is None
        assert args.auth_mode is None
        assert args.transport == "stdio"
    
    def test_parse_arguments_with_all_options(self):
        """Test parsing all arguments together."""
        from config import parse_arguments
        
        args = parse_arguments([
            "--host", "10.0.0.1",
            "--port", "3000",
            "--auth-mode", "jwt",
            "--transport", "http"
        ])
        
        assert args.host == "10.0.0.1"
        assert args.port == 3000
        assert args.auth_mode == "jwt"
        assert args.transport == "http"
    
    def test_parse_arguments_invalid_auth_mode(self):
        """Test that invalid auth-mode raises error."""
        from config import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments(["--auth-mode", "oauth"])
    
    def test_parse_arguments_invalid_transport(self):
        """Test that invalid transport raises error."""
        from config import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments(["--transport", "websocket"])
    
    def test_parse_arguments_invalid_port_type(self):
        """Test that non-integer port raises error."""
        from config import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments(["--port", "not-a-number"])
    
    def test_parse_arguments_help_flag(self):
        """Test that --help flag exits with help message."""
        from config import parse_arguments
        
        with pytest.raises(SystemExit) as exc_info:
            parse_arguments(["--help"])
        
        # Help should exit with code 0
        assert exc_info.value.code == 0
    
    def test_create_argument_parser_has_correct_prog_name(self):
        """Test that parser has correct program name."""
        from config import create_argument_parser
        
        parser = create_argument_parser()
        
        assert parser.prog == "gsc-server"
    
    def test_create_argument_parser_has_description(self):
        """Test that parser has a description."""
        from config import create_argument_parser
        
        parser = create_argument_parser()
        
        assert parser.description is not None
        assert "Google Search Console" in parser.description
        assert "MCP Server" in parser.description
    
    def test_create_argument_parser_has_epilog_with_examples(self):
        """Test that parser has epilog with usage examples."""
        from config import create_argument_parser
        
        parser = create_argument_parser()
        
        assert parser.epilog is not None
        assert "Examples:" in parser.epilog
        assert "Environment Variables:" in parser.epilog
        assert "MCP_HOST" in parser.epilog
        assert "MCP_PORT" in parser.epilog
    
    def test_parse_arguments_with_mixed_order(self):
        """Test that argument order doesn't matter."""
        from config import parse_arguments
        
        args1 = parse_arguments(["--port", "5000", "--host", "localhost"])
        args2 = parse_arguments(["--host", "localhost", "--port", "5000"])
        
        assert args1.host == args2.host == "localhost"
        assert args1.port == args2.port == 5000
