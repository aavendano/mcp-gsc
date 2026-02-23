"""
Integration tests for STDIO backward compatibility.

These tests verify that the server can still start with STDIO transport
without requiring authentication configuration, maintaining backward
compatibility with existing deployments.
"""

import pytest
import os
import subprocess
import time
import json


class TestSTDIOBackwardCompatibility:
    """Integration tests for STDIO backward compatibility."""
    
    def test_stdio_starts_without_auth_config(self):
        """
        Test that server starts with STDIO transport without auth configuration.
        
        Validates: Requirements 8.1, 8.2, 8.3, 8.4
        """
        # Create a test script that starts the server with STDIO
        test_script = """
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Clear any auth-related environment variables
for key in ['MCP_ADMIN_TOKEN', 'JWT_JWKS_URI', 'JWT_ISSUER', 'JWT_AUDIENCE']:
    os.environ.pop(key, None)

# Set transport to STDIO
os.environ['MCP_TRANSPORT'] = 'stdio'

# Import and configure
from logging_config import configure_logging
from config import ServerConfig
from server import initialize_server

# Configure logging
logger = configure_logging()

# Create configuration for STDIO
config = ServerConfig(
    transport="stdio",
    auth_mode="static",  # This should be ignored for STDIO
    admin_token=None  # No token needed for STDIO
)

# Validate - should not raise error for missing token
try:
    config.validate()
    print("VALIDATION_SUCCESS")
except Exception as e:
    print(f"VALIDATION_ERROR: {e}")
    sys.exit(1)

# Initialize server - should work without auth
from gsc_server import mcp
try:
    mcp_configured = initialize_server(config, mcp_instance=mcp)
    print("INITIALIZATION_SUCCESS")
except Exception as e:
    print(f"INITIALIZATION_ERROR: {e}")
    sys.exit(1)

# Don't actually start the server (would block), just verify we got this far
print("STDIO_READY")
sys.exit(0)
"""
        
        # Write test script to temporary file
        with open('/tmp/test_stdio_server.py', 'w') as f:
            f.write(test_script)
        
        try:
            # Run the test script with proper environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                ['python', '/tmp/test_stdio_server.py'],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            # Check output
            assert "VALIDATION_SUCCESS" in result.stdout, \
                f"Validation failed: {result.stdout}\n{result.stderr}"
            assert "INITIALIZATION_SUCCESS" in result.stdout, \
                f"Initialization failed: {result.stdout}\n{result.stderr}"
            assert "STDIO_READY" in result.stdout, \
                f"Server not ready: {result.stdout}\n{result.stderr}"
            assert result.returncode == 0, \
                f"Script failed with code {result.returncode}: {result.stderr}"
        
        finally:
            # Clean up
            if os.path.exists('/tmp/test_stdio_server.py'):
                os.remove('/tmp/test_stdio_server.py')
    
    def test_stdio_ignores_auth_mode(self):
        """
        Test that STDIO transport ignores auth_mode setting.
        
        Validates: Requirements 8.4
        """
        # Create a test script that verifies auth is not required for STDIO
        test_script = """
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Clear auth environment variables
for key in ['MCP_ADMIN_TOKEN', 'JWT_JWKS_URI', 'JWT_ISSUER', 'JWT_AUDIENCE']:
    os.environ.pop(key, None)

from config import ServerConfig

# Create STDIO config with JWT mode (should not require JWT config)
config = ServerConfig(
    transport="stdio",
    auth_mode="jwt",  # This should be ignored
    jwks_uri=None,  # No JWT config needed
    jwt_issuer=None,
    jwt_audience=None
)

# Validate - should succeed even without JWT config
try:
    config.validate()
    print("VALIDATION_SUCCESS")
except Exception as e:
    print(f"VALIDATION_ERROR: {e}")
    sys.exit(1)

print("STDIO_AUTH_IGNORED")
sys.exit(0)
"""
        
        # Write test script to temporary file
        with open('/tmp/test_stdio_auth.py', 'w') as f:
            f.write(test_script)
        
        try:
            # Run the test script with proper environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                ['python', '/tmp/test_stdio_auth.py'],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            # Check output
            assert "VALIDATION_SUCCESS" in result.stdout, \
                f"Validation should succeed for STDIO: {result.stdout}\n{result.stderr}"
            assert "STDIO_AUTH_IGNORED" in result.stdout, \
                f"Auth mode should be ignored: {result.stdout}\n{result.stderr}"
            assert result.returncode == 0, \
                f"Script failed with code {result.returncode}: {result.stderr}"
        
        finally:
            # Clean up
            if os.path.exists('/tmp/test_stdio_auth.py'):
                os.remove('/tmp/test_stdio_auth.py')
    
    def test_stdio_tool_functionality(self):
        """
        Test that basic tool functionality works with STDIO transport.
        
        This is a minimal test that verifies the server can be initialized
        with STDIO and tools are accessible.
        
        Validates: Requirements 8.5
        """
        # Create a test script that verifies tools are available
        test_script = """
import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Set transport to STDIO
os.environ['MCP_TRANSPORT'] = 'stdio'

from logging_config import configure_logging
from config import ServerConfig
from server import initialize_server

# Configure logging
logger = configure_logging()

# Create STDIO configuration
config = ServerConfig(
    transport="stdio",
    auth_mode="static",
    admin_token=None
)

# Initialize server
from gsc_server import mcp
mcp_configured = initialize_server(config, mcp_instance=mcp)

# Verify tools are registered (using async)
async def check_tools():
    tools = await mcp_configured.list_tools()
    tool_names = [tool.name for tool in tools]
    
    # Check for some expected GSC tools
    expected_tools = ['list_properties', 'get_search_analytics', 'inspect_url_enhanced']
    for tool_name in expected_tools:
        if tool_name in tool_names:
            print(f"TOOL_FOUND: {tool_name}")
        else:
            print(f"TOOL_MISSING: {tool_name}")
            sys.exit(1)
    
    print("TOOLS_AVAILABLE")

# Run async check
asyncio.run(check_tools())
sys.exit(0)
"""
        
        # Write test script to temporary file
        with open('/tmp/test_stdio_tools.py', 'w') as f:
            f.write(test_script)
        
        try:
            # Run the test script with proper environment
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                ['python', '/tmp/test_stdio_tools.py'],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            # Check output
            assert "TOOL_FOUND: list_properties" in result.stdout, \
                f"list_properties tool not found: {result.stdout}\n{result.stderr}"
            assert "TOOL_FOUND: get_search_analytics" in result.stdout, \
                f"get_search_analytics tool not found: {result.stdout}\n{result.stderr}"
            assert "TOOL_FOUND: inspect_url_enhanced" in result.stdout, \
                f"inspect_url_enhanced tool not found: {result.stdout}\n{result.stderr}"
            assert "TOOLS_AVAILABLE" in result.stdout, \
                f"Tools not available: {result.stdout}\n{result.stderr}"
            assert result.returncode == 0, \
                f"Script failed with code {result.returncode}: {result.stderr}"
        
        finally:
            # Clean up
            if os.path.exists('/tmp/test_stdio_tools.py'):
                os.remove('/tmp/test_stdio_tools.py')
