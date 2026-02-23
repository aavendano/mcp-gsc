"""
Unit tests for server initialization module.

Feature: http-auth-migration
"""

import pytest
from mcp.server.fastmcp import FastMCP
from config import ServerConfig
from server import initialize_server, _sanitize_host_for_url


class TestHostSanitization:
    """Tests for host sanitization function."""
    
    def test_sanitize_valid_hostname(self):
        """Test that valid hostnames pass through unchanged."""
        assert _sanitize_host_for_url("localhost") == "localhost"
        assert _sanitize_host_for_url("example.com") == "example.com"
        assert _sanitize_host_for_url("sub.example.com") == "sub.example.com"
    
    def test_sanitize_valid_ipv4(self):
        """Test that valid IPv4 addresses pass through unchanged."""
        assert _sanitize_host_for_url("127.0.0.1") == "127.0.0.1"
        assert _sanitize_host_for_url("192.168.1.1") == "192.168.1.1"
        assert _sanitize_host_for_url("0.0.0.0") == "0.0.0.0"
    
    def test_sanitize_invalid_hosts(self):
        """Test that invalid hosts are sanitized to localhost."""
        # Empty or whitespace
        assert _sanitize_host_for_url("") == "localhost"
        assert _sanitize_host_for_url("   ") == "localhost"
        
        # Invalid characters
        assert _sanitize_host_for_url("host@name") == "localhost"
        assert _sanitize_host_for_url("host name") == "localhost"
        
        # Incomplete IPv6 brackets (the bug we fixed)
        assert _sanitize_host_for_url("[") == "localhost"
        assert _sanitize_host_for_url("]") == "localhost"
        assert _sanitize_host_for_url("[::") == "localhost"
        assert _sanitize_host_for_url("::1]") == "localhost"
        
        # Mismatched brackets
        assert _sanitize_host_for_url("[[::1]]") == "localhost"
        
        # Invalid start/end characters
        assert _sanitize_host_for_url(".example.com") == "localhost"
        assert _sanitize_host_for_url("example.com.") == "localhost"
        assert _sanitize_host_for_url("-example.com") == "localhost"
    
    def test_sanitize_valid_ipv6(self):
        """Test that valid IPv6 addresses pass through unchanged."""
        assert _sanitize_host_for_url("[::1]") == "[::1]"
        assert _sanitize_host_for_url("[2001:db8::1]") == "[2001:db8::1]"


class TestServerInitialization:
    """Tests for server initialization with different configurations."""
    
    def test_server_creation_with_static_auth(self):
        """
        Test that server is created successfully with static authentication.
        
        Requirements: 1.1, 1.2, 3.6
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="http",
            admin_token="test-token-123"
        )
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Initialize server
        initialized_mcp = initialize_server(config, test_mcp)
        
        # Verify server was initialized
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
        assert initialized_mcp is test_mcp  # Should return the same instance
    
    def test_server_creation_with_jwt_auth(self):
        """
        Test that server is created successfully with JWT authentication.
        
        Requirements: 1.1, 1.2, 4.5
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
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Initialize server
        initialized_mcp = initialize_server(config, test_mcp)
        
        # Verify server was initialized
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
        assert initialized_mcp is test_mcp
    
    def test_server_creation_without_auth_stdio(self):
        """
        Test that server is created successfully without auth for STDIO transport.
        
        Requirements: 1.1, 1.2, 8.4
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="stdio",
            admin_token=None  # No auth needed for STDIO
        )
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Initialize server
        initialized_mcp = initialize_server(config, test_mcp)
        
        # Verify server was initialized
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
        assert initialized_mcp is test_mcp
    
    def test_server_creation_without_existing_instance(self):
        """
        Test that server creates a new FastMCP instance when none is provided.
        
        Note: In practice, the MCP instance is created globally in gsc_server.py,
        but this tests the fallback behavior.
        
        Requirements: 1.1, 1.2
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="stdio",  # Use STDIO to avoid auth complexity
            transport="stdio",
            admin_token=None
        )
        
        # Initialize server without providing an instance
        initialized_mcp = initialize_server(config, mcp_instance=None)
        
        # Verify a new server was created
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
    
    def test_error_handling_for_invalid_config(self):
        """
        Test that server initialization fails with invalid configuration.
        
        Requirements: 3.6
        """
        # Config with HTTP transport but no auth token
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="static",
            transport="http",
            admin_token=None  # Missing required token
        )
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Should raise ValueError due to missing auth token
        with pytest.raises(ValueError) as exc_info:
            initialize_server(config, test_mcp)
        
        error_msg = str(exc_info.value)
        assert "MCP_ADMIN_TOKEN" in error_msg or "token" in error_msg.lower()
    
    def test_server_with_jwt_missing_fields(self):
        """
        Test that server initialization fails when JWT fields are missing.
        
        Requirements: 4.5
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",
            transport="http",
            jwks_uri=None,  # Missing
            jwt_issuer="https://example.com",
            jwt_audience="my-api"
        )
        
        # Create a test MCP instance
        test_mcp = FastMCP("test-server")
        
        # Should raise ValueError due to missing JWT configuration
        with pytest.raises(ValueError) as exc_info:
            initialize_server(config, test_mcp)
        
        error_msg = str(exc_info.value)
        assert "JWT" in error_msg
        assert "JWKS_URI" in error_msg


class TestServerInitializationEdgeCases:
    """Tests for edge cases in server initialization."""
    
    def test_server_with_different_ports(self):
        """
        Test that server can be initialized with various port numbers.
        
        Requirements: 1.1, 1.2
        """
        ports = [8000, 8080, 9000, 3000, 5000]
        
        for port in ports:
            config = ServerConfig(
                host="localhost",
                port=port,
                auth_mode="static",
                transport="http",
                admin_token="test-token"
            )
            
            test_mcp = FastMCP(f"test-server-{port}")
            initialized_mcp = initialize_server(config, test_mcp)
            
            assert initialized_mcp is not None
            assert isinstance(initialized_mcp, FastMCP)
    
    def test_server_with_different_hosts(self):
        """
        Test that server can be initialized with various host addresses.
        
        Requirements: 1.1, 1.2
        """
        hosts = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.1.1"]
        
        for host in hosts:
            config = ServerConfig(
                host=host,
                port=8000,
                auth_mode="static",
                transport="http",
                admin_token="test-token"
            )
            
            test_mcp = FastMCP(f"test-server-{host}")
            initialized_mcp = initialize_server(config, test_mcp)
            
            assert initialized_mcp is not None
            assert isinstance(initialized_mcp, FastMCP)
    
    def test_server_with_jwt_and_required_scopes(self):
        """
        Test that server can be initialized with JWT and required scopes.
        
        Requirements: 4.5
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
        
        test_mcp = FastMCP("test-server")
        initialized_mcp = initialize_server(config, test_mcp)
        
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
    
    def test_stdio_with_jwt_mode_still_works(self):
        """
        Test that STDIO transport works even with JWT auth mode set.
        Auth mode should be ignored for STDIO.
        
        Requirements: 8.4
        """
        config = ServerConfig(
            host="localhost",
            port=8000,
            auth_mode="jwt",  # JWT mode but STDIO transport
            transport="stdio",
            jwks_uri=None,  # No JWT config needed
            jwt_issuer=None,
            jwt_audience=None
        )
        
        test_mcp = FastMCP("test-server")
        initialized_mcp = initialize_server(config, test_mcp)
        
        # Should succeed because STDIO doesn't require auth
        assert initialized_mcp is not None
        assert isinstance(initialized_mcp, FastMCP)
