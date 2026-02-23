"""
Integration tests for error scenarios.

These tests verify that the server handles error conditions gracefully
and provides clear, helpful error messages.

Validates: Requirements 2.6, 3.2, 4.1, 4.2, 4.3, 10.3, 10.4, 10.6
"""

import pytest
import os
import sys
import subprocess
import tempfile
from config import ServerConfig


class TestErrorScenarios:
    """
    Integration tests for error scenarios.
    
    These tests verify that the server:
    1. Handles missing required configuration gracefully
    2. Validates port numbers correctly
    3. Provides clear error messages for authentication issues
    4. Handles malformed tokens appropriately
    
    Validates: Requirements 2.6, 3.2, 4.1, 4.2, 4.3, 10.3, 10.4, 10.6
    """
    
    def test_missing_static_token_error(self):
        """
        Test that server fails with clear error when static token is missing.
        
        This test verifies that when HTTP transport with static auth is configured
        but MCP_ADMIN_TOKEN is not set, the server provides a clear error message.
        
        Validates: Requirements 3.2, 10.3, 10.4
        """
        # Create a test script that tries to start server without token
        test_script = """
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Clear any existing token
os.environ.pop('MCP_ADMIN_TOKEN', None)

from config import ServerConfig

# Create configuration for HTTP with static auth but no token
config = ServerConfig(
    host="127.0.0.1",
    port=8000,
    auth_mode="static",
    transport="http",
    admin_token=None  # No token
)

# Try to validate - should raise ValueError
try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    # Check that error message is clear and helpful
    if "MCP_ADMIN_TOKEN" in error_msg:
        print("ERROR_MESSAGE_CLEAR: Yes")
    else:
        print("ERROR_MESSAGE_CLEAR: No")
    
    if "required" in error_msg.lower():
        print("ERROR_MESSAGE_HELPFUL: Yes")
    else:
        print("ERROR_MESSAGE_HELPFUL: No")
    
    sys.exit(0)
"""
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        try:
            # Run the test script
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            # Check output
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MESSAGE_CLEAR: Yes" in result.stdout, \
                f"Error message should mention MCP_ADMIN_TOKEN: {result.stdout}"
            assert "ERROR_MESSAGE_HELPFUL: Yes" in result.stdout, \
                f"Error message should mention 'required': {result.stdout}"
            assert result.returncode == 0, \
                f"Script should exit cleanly: {result.stderr}"
            
            print("✓ Missing static token error is clear and helpful")
        
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def test_missing_jwt_config_error(self):
        """
        Test that server fails with clear error when JWT config is missing.
        
        This test verifies that when HTTP transport with JWT auth is configured
        but required JWT parameters are missing, the server provides clear error messages.
        
        Validates: Requirements 4.1, 4.2, 4.3, 10.3, 10.4
        """
        # Test missing JWKS URI
        test_script_jwks = """
import sys
import os

sys.path.insert(0, os.getcwd())

# Clear JWT environment variables
for key in ['JWT_JWKS_URI', 'JWT_ISSUER', 'JWT_AUDIENCE']:
    os.environ.pop(key, None)

from config import ServerConfig

# Create configuration for HTTP with JWT auth but missing JWKS URI
config = ServerConfig(
    host="127.0.0.1",
    port=8000,
    auth_mode="jwt",
    transport="http",
    jwks_uri=None,  # Missing
    jwt_issuer="https://issuer.example.com",
    jwt_audience="test-audience"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "JWT_JWKS_URI" in error_msg:
        print("ERROR_MENTIONS_JWKS_URI: Yes")
    else:
        print("ERROR_MENTIONS_JWKS_URI: No")
    
    sys.exit(0)
"""
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_jwks)
            script_path = f.name
        
        try:
            # Run the test script
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            # Check output
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_JWKS_URI: Yes" in result.stdout, \
                f"Error message should mention JWT_JWKS_URI: {result.stdout}"
            assert result.returncode == 0, \
                f"Script should exit cleanly: {result.stderr}"
            
            print("✓ Missing JWT JWKS URI error is clear")
        
        finally:
            # Clean up
            if os.path.exists(script_path):
                os.remove(script_path)
        
        # Test missing issuer
        test_script_issuer = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port=8000,
    auth_mode="jwt",
    transport="http",
    jwks_uri="https://example.com/.well-known/jwks.json",
    jwt_issuer=None,  # Missing
    jwt_audience="test-audience"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "JWT_ISSUER" in error_msg:
        print("ERROR_MENTIONS_ISSUER: Yes")
    else:
        print("ERROR_MENTIONS_ISSUER: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_issuer)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_ISSUER: Yes" in result.stdout, \
                f"Error message should mention JWT_ISSUER: {result.stdout}"
            
            print("✓ Missing JWT issuer error is clear")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
        
        # Test missing audience
        test_script_audience = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port=8000,
    auth_mode="jwt",
    transport="http",
    jwks_uri="https://example.com/.well-known/jwks.json",
    jwt_issuer="https://issuer.example.com",
    jwt_audience=None  # Missing
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "JWT_AUDIENCE" in error_msg:
        print("ERROR_MENTIONS_AUDIENCE: Yes")
    else:
        print("ERROR_MENTIONS_AUDIENCE: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_audience)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_AUDIENCE: Yes" in result.stdout, \
                f"Error message should mention JWT_AUDIENCE: {result.stdout}"
            
            print("✓ Missing JWT audience error is clear")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def test_invalid_port_error(self):
        """
        Test that server fails with clear error for invalid port numbers.
        
        This test verifies that the server validates port numbers and provides
        clear error messages for invalid values.
        
        Validates: Requirements 2.6, 10.3, 10.4, 10.6
        """
        # Test port too low (0)
        test_script_low = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port=0,  # Invalid: too low
    auth_mode="static",
    transport="http",
    admin_token="test-token"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "port" in error_msg.lower():
        print("ERROR_MENTIONS_PORT: Yes")
    else:
        print("ERROR_MENTIONS_PORT: No")
    
    if "1" in error_msg and "65535" in error_msg:
        print("ERROR_MENTIONS_RANGE: Yes")
    else:
        print("ERROR_MENTIONS_RANGE: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_low)
            script_path = f.name
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_PORT: Yes" in result.stdout, \
                f"Error message should mention port: {result.stdout}"
            assert "ERROR_MENTIONS_RANGE: Yes" in result.stdout, \
                f"Error message should mention valid range: {result.stdout}"
            
            print("✓ Invalid port (too low) error is clear")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
        
        # Test port too high (65536)
        test_script_high = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port=65536,  # Invalid: too high
    auth_mode="static",
    transport="http",
    admin_token="test-token"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "port" in error_msg.lower():
        print("ERROR_MENTIONS_PORT: Yes")
    
    if "1" in error_msg and "65535" in error_msg:
        print("ERROR_MENTIONS_RANGE: Yes")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_high)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_PORT: Yes" in result.stdout, \
                f"Error message should mention port: {result.stdout}"
            assert "ERROR_MENTIONS_RANGE: Yes" in result.stdout, \
                f"Error message should mention valid range: {result.stdout}"
            
            print("✓ Invalid port (too high) error is clear")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
        
        # Test non-integer port
        test_script_string = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port="not-a-number",  # Invalid: not an integer
    auth_mode="static",
    transport="http",
    admin_token="test-token"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except (ValueError, TypeError) as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "port" in error_msg.lower() or "integer" in error_msg.lower():
        print("ERROR_MENTIONS_PORT_TYPE: Yes")
    else:
        print("ERROR_MENTIONS_PORT_TYPE: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_string)
            script_path = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_PORT_TYPE: Yes" in result.stdout, \
                f"Error message should mention port type: {result.stdout}"
            
            print("✓ Invalid port (non-integer) error is clear")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def test_invalid_auth_mode_error(self):
        """
        Test that server fails with clear error for invalid auth mode.
        
        This test verifies that the server validates auth_mode and provides
        clear error messages for invalid values.
        
        Validates: Requirements 10.3, 10.4, 10.6
        """
        test_script = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

config = ServerConfig(
    host="127.0.0.1",
    port=8000,
    auth_mode="invalid-mode",  # Invalid auth mode
    transport="http",
    admin_token="test-token"
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    if "auth_mode" in error_msg.lower():
        print("ERROR_MENTIONS_AUTH_MODE: Yes")
    else:
        print("ERROR_MENTIONS_AUTH_MODE: No")
    
    if "static" in error_msg and "jwt" in error_msg:
        print("ERROR_MENTIONS_VALID_OPTIONS: Yes")
    else:
        print("ERROR_MENTIONS_VALID_OPTIONS: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_MENTIONS_AUTH_MODE: Yes" in result.stdout, \
                f"Error message should mention auth_mode: {result.stdout}"
            assert "ERROR_MENTIONS_VALID_OPTIONS: Yes" in result.stdout, \
                f"Error message should mention valid options: {result.stdout}"
            
            print("✓ Invalid auth mode error is clear and helpful")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def test_error_messages_no_sensitive_data(self):
        """
        Test that error messages don't expose sensitive data.
        
        This test verifies that error messages don't include tokens or
        other sensitive information.
        
        Validates: Requirements 10.3, 10.4
        """
        test_script = """
import sys
import os

sys.path.insert(0, os.getcwd())

from config import ServerConfig

# Set a token that should NOT appear in error messages
test_token = "super-secret-token-12345"

config = ServerConfig(
    host="127.0.0.1",
    port=0,  # Invalid port to trigger error
    auth_mode="static",
    transport="http",
    admin_token=test_token
)

try:
    config.validate()
    print("ERROR: Validation should have failed")
    sys.exit(1)
except ValueError as e:
    error_msg = str(e)
    print(f"VALIDATION_ERROR: {error_msg}")
    
    # Check that token is NOT in error message
    if test_token in error_msg:
        print("ERROR_EXPOSES_TOKEN: Yes")
    else:
        print("ERROR_EXPOSES_TOKEN: No")
    
    sys.exit(0)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            script_path = f.name
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
                cwd=os.getcwd()
            )
            
            assert "VALIDATION_ERROR" in result.stdout, \
                f"Should get validation error: {result.stdout}\n{result.stderr}"
            assert "ERROR_EXPOSES_TOKEN: No" in result.stdout, \
                f"Error message should NOT expose token: {result.stdout}"
            
            print("✓ Error messages don't expose sensitive data")
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
