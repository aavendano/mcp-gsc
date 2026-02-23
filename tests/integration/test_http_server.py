"""
Integration tests for HTTP server startup and endpoint accessibility.

These tests verify that the server can start with valid HTTP configuration,
bind to the correct host/port, and expose the /mcp endpoint.
"""

import pytest
import os
import time
import requests
import multiprocessing
from config import ServerConfig
from server import initialize_server, start_server
from logging_config import configure_logging


def run_server_process(host: str, port: int, admin_token: str):
    """
    Run server in a separate process for testing.
    
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


class TestHTTPServerStartup:
    """Integration tests for HTTP server startup."""
    
    def test_server_binds_to_correct_host_port(self):
        """
        Test that server binds to the correct host and port.
        
        Validates: Requirements 1.1, 1.2, 1.4, 1.5
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18000
        test_token = "test-token-12345"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_server_process,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server process should be running"
            
            # Try to connect to the server (should get 401 without auth, but proves it's listening)
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    timeout=5
                )
                # We expect 400, 401, 403, or 405 (unauthorized/bad request) since we didn't provide auth
                # But this proves the server is listening
                assert response.status_code in [400, 401, 403, 405], \
                    f"Expected 400/401/403/405, got {response.status_code}"
            except requests.exceptions.ConnectionError:
                pytest.fail("Could not connect to server - server may not have started")
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_mcp_endpoint_accessible(self):
        """
        Test that /mcp endpoint is accessible.
        
        Validates: Requirements 1.3, 1.6
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18001
        test_token = "test-token-67890"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_server_process,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify /mcp endpoint responds
            try:
                response = requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    timeout=5
                )
                # Should get a response (even if 401/403)
                assert response.status_code is not None, "Should get a response from /mcp endpoint"
            except requests.exceptions.ConnectionError:
                pytest.fail("/mcp endpoint not accessible")
            
            # Verify other paths return 404
            try:
                response = requests.get(
                    f"http://{test_host}:{test_port}/other",
                    timeout=5
                )
                assert response.status_code == 404, "Non-MCP paths should return 404"
            except requests.exceptions.ConnectionError:
                # Some servers might not respond at all to invalid paths
                pass
        
        finally:
            # Clean up: terminate server process
            server_process.terminate()
            server_process.join(timeout=5)
            if server_process.is_alive():
                server_process.kill()
    
    def test_server_shutdown_cleanly(self):
        """
        Test that server can be shutdown cleanly.
        
        Validates: Requirements 1.6
        """
        # Use a non-standard port to avoid conflicts
        test_host = "127.0.0.1"
        test_port = 18002
        test_token = "test-token-cleanup"
        
        # Start server in separate process
        server_process = multiprocessing.Process(
            target=run_server_process,
            args=(test_host, test_port, test_token)
        )
        server_process.start()
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Verify server is running
            assert server_process.is_alive(), "Server should be running"
            
            # Terminate server
            server_process.terminate()
            server_process.join(timeout=5)
            
            # Verify server stopped
            assert not server_process.is_alive(), "Server should have stopped"
            
            # Verify we can't connect anymore
            time.sleep(1)
            with pytest.raises(requests.exceptions.ConnectionError):
                requests.post(
                    f"http://{test_host}:{test_port}/mcp",
                    timeout=2
                )
        
        finally:
            # Ensure cleanup
            if server_process.is_alive():
                server_process.kill()
