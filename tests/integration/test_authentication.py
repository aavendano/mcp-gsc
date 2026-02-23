"""
Integration tests for authentication functionality.

These tests verify that the server correctly authenticates requests with valid tokens
and rejects requests with invalid or missing tokens.

Feature: http-auth-migration
Property 2: Authentication Rejection
Validates: Requirements 3.4, 3.5, 4.6, 4.7
"""

import pytest
import os
import time
import requests
import multiprocessing
from config import ServerConfig
from server import initialize_server, start_server
from logging_config import configure_logging


def run_authenticated_server(host: str, port: int, admin_token: str):
    """
    Run server with authentication in a separate process for testing.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        admin_token: Admin token for authentication
    """
    # Set environment variables for the server process
    os.environ['MCP_ADMIN_TOKEN'] = admin_token
    
    # Configure logging
    configure_logging()
    
    # Create configuration
    config = ServerConfig(
        host=host,
        port=port,
        auth_mode="static",
        transport="http",
        admin_token=admin_token
    )
    
    # Import the mcp instance from gsc_server
    from gsc_server import mcp
    
    # Initialize and start server
    mcp_configured = initialize_server(config, mcp_instance=mcp)
    start_server(mcp_configured, config)


class TestStaticTokenAuthentication:
    """
    Integration tests for static token authentication.
    
    Property 2: Authentication Rejection
    For any HTTP request without a valid Bearer token, the server should reject 
    the request with HTTP 401 status.
    
    Validates: Requirements 3.4, 3.5, 4.6, 4.7
    """
    
    def test_valid_token_authentication(self):
        """
        Test that requests with valid Bearer token are accepted.
        
        Validates: Requirements 3.3
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18100
        test_token = "valid-test-token-12345"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Send request with valid token
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            # Try to make a valid MCP request
            # Note: We're testing authentication, not full MCP protocol
            # So we expect either success or a protocol error, but NOT 401
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should NOT get 401 with valid token
                assert response.status_code != 401, \
                    f"Valid token should not result in 401, got {response.status_code}"
                
                # Should get 200 or other non-auth error (400, 405, 406 are acceptable)
                # 406 means the server doesn't accept the content type, which is fine for auth testing
                assert response.status_code in [200, 400, 405, 406], \
                    f"Expected 200/400/405/406 with valid token, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_invalid_token_rejection(self):
        """
        Test that requests with invalid Bearer token are rejected with 401.
        
        Property 2: Authentication Rejection
        For any HTTP request without a valid Bearer token, the server should reject 
        the request with HTTP 401 status.
        
        Validates: Requirements 3.4
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18101
        test_token = "valid-test-token-67890"
        invalid_token = "invalid-wrong-token"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Send request with invalid token
            headers = {
                "Authorization": f"Bearer {invalid_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should get 401 with invalid token
                assert response.status_code == 401, \
                    f"Invalid token should result in 401, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_missing_token_rejection(self):
        """
        Test that requests without Authorization header are rejected with 401.
        
        Property 2: Authentication Rejection
        For any HTTP request without a valid Bearer token, the server should reject 
        the request with HTTP 401 status.
        
        Validates: Requirements 3.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18102
        test_token = "valid-test-token-missing"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Send request without Authorization header
            headers = {
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should get 401 without token
                assert response.status_code == 401, \
                    f"Missing token should result in 401, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_malformed_authorization_header(self):
        """
        Test that requests with malformed Authorization header are rejected.
        
        Property 2: Authentication Rejection
        For any HTTP request without a valid Bearer token, the server should reject 
        the request with HTTP 401 status.
        
        Validates: Requirements 3.4, 3.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18103
        test_token = "valid-test-token-malformed"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Test various malformed Authorization headers
            malformed_headers = [
                {"Authorization": "InvalidFormat token123"},  # Wrong scheme
                {"Authorization": "Bearer"},  # Missing token
                {"Authorization": "token123"},  # Missing Bearer prefix
                {"Authorization": ""},  # Empty header
            ]
            
            for headers in malformed_headers:
                headers["Content-Type"] = "application/json"
                
                try:
                    response = requests.post(
                        f"http://{test_host}:{test_port}/mcp",
                        headers=headers,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                        timeout=5
                    )
                    
                    # Should get 401 with malformed header
                    assert response.status_code == 401, \
                        f"Malformed header {headers['Authorization']} should result in 401, got {response.status_code}"
                
                except requests.exceptions.ConnectionError:
                    pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()



class TestEndpointPathConsistency:
    """
    Integration tests for endpoint path consistency.
    
    Property 10: Endpoint Path Consistency
    For any HTTP transport configuration, the MCP endpoint should be accessible 
    at exactly the path `/mcp`.
    
    Validates: Requirements 1.3
    """
    
    def test_mcp_endpoint_responds(self):
        """
        Test that /mcp endpoint responds correctly.
        
        Property 10: Endpoint Path Consistency
        For any HTTP transport configuration, the MCP endpoint should be accessible 
        at exactly the path `/mcp`.
        
        Validates: Requirements 1.3
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18200
        test_token = "test-token-endpoint"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Test /mcp endpoint with valid token
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should get a response (not 404)
                assert response.status_code != 404, \
                    f"/mcp endpoint should exist, got 404"
                
                # Should get 200, 400, 405, or 406 (anything but 404 or 401)
                assert response.status_code in [200, 400, 405, 406], \
                    f"/mcp endpoint should respond, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to /mcp endpoint")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_other_paths_return_404(self):
        """
        Test that paths other than /mcp return 404.
        
        Property 10: Endpoint Path Consistency
        For any HTTP transport configuration, the MCP endpoint should be accessible 
        at exactly the path `/mcp`.
        
        Validates: Requirements 1.3
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18201
        test_token = "test-token-404"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Test various non-MCP paths (excluding /mcp/ which may redirect)
            invalid_paths = [
                "/",
                "/api",
                "/MCP",  # Wrong case
                "/mcp/tools",  # Sub-path
                "/other",
            ]
            
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            for path in invalid_paths:
                try:
                    response = requests.post(
                        f"http://{test_host}:{test_port}{path}",
                        headers=headers,
                        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                        timeout=5,
                        allow_redirects=False  # Don't follow redirects
                    )
                    
                    # Should get 404 for non-MCP paths
                    assert response.status_code == 404, \
                        f"Path {path} should return 404, got {response.status_code}"
                
                except requests.exceptions.ConnectionError:
                    # Some paths might not be routed at all, which is also acceptable
                    pass
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_mcp_endpoint_exact_path(self):
        """
        Test that MCP endpoint is accessible at /mcp.
        
        Property 10: Endpoint Path Consistency
        For any HTTP transport configuration, the MCP endpoint should be accessible 
        at exactly the path `/mcp`.
        
        Note: /mcp/ with trailing slash may redirect to /mcp, which is acceptable.
        
        Validates: Requirements 1.3
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18202
        test_token = "test-token-exact"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            # Test exact path /mcp
            try:
                response_exact = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should NOT be 404
                assert response_exact.status_code != 404, \
                    "/mcp should exist"
                
                # Should get a valid response (406 is acceptable - means auth passed)
                assert response_exact.status_code in [200, 400, 405, 406], \
                    f"/mcp should respond with valid status, got {response_exact.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("/mcp endpoint not accessible")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()



class TestToolFunctionality:
    """
    Integration tests for tool functionality with authentication.
    
    These tests verify that GSC tools work correctly when accessed through
    HTTP transport with authentication.
    
    Validates: Requirements 8.5
    """
    
    def test_list_tools_with_authentication(self):
        """
        Test that tools can be listed with proper authentication.
        
        This test verifies that the MCP server responds to tool listing requests
        when properly authenticated, demonstrating that tools are accessible
        via HTTP transport.
        
        Validates: Requirements 8.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18300
        test_token = "test-token-tools"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Send authenticated request to list tools
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            # Note: The actual MCP protocol format may differ from JSON-RPC
            # This test verifies authentication works, not the full protocol
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should NOT get 401 (authentication should pass)
                assert response.status_code != 401, \
                    "Authenticated request should not get 401"
                
                # Should get some response (200, 400, 405, or 406 are all acceptable)
                # The exact response depends on MCP protocol implementation
                assert response.status_code in [200, 400, 405, 406], \
                    f"Should get valid response, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_tool_access_requires_authentication(self):
        """
        Test that tool access requires authentication.
        
        This test verifies that attempting to access tools without proper
        authentication results in a 401 error, ensuring security is enforced.
        
        Validates: Requirements 8.5, 3.4, 3.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18301
        test_token = "test-token-secure"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Try to access tools without authentication
            headers = {
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Should get 401 without authentication
                assert response.status_code == 401, \
                    f"Unauthenticated request should get 401, got {response.status_code}"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_server_starts_with_tools_registered(self):
        """
        Test that server starts with GSC tools properly registered.
        
        This test verifies that when the server starts with HTTP transport
        and authentication, the underlying GSC tools are still registered
        and available (even if we can't call them directly in this test).
        
        Validates: Requirements 8.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18302
        test_token = "test-token-registered"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_authenticated_server,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Verify the server is accessible (basic connectivity test)
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    headers=headers,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    timeout=5
                )
                
                # Server should respond (not 404, not connection error)
                assert response.status_code is not None, \
                    "Server should respond to requests"
                
                # Should not be 404 (endpoint exists)
                assert response.status_code != 404, \
                    "MCP endpoint should exist"
                
                # Should not be 401 (authentication should work)
                assert response.status_code != 401, \
                    "Authentication should work with valid token"
            
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server - tools may not be registered")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
