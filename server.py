"""
Server initialization module for the Google Search Console MCP server.

This module provides functions to initialize and start the FastMCP server
with configured transport and authentication.
"""

import logging
import re
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import AuthSettings
from pydantic import HttpUrl

from config import ServerConfig
from auth import create_auth_verifier


# Get logger
logger = logging.getLogger('gsc-server')


def _sanitize_host_for_url(host: str) -> str:
    """
    Sanitize a host string to ensure it's valid for URL construction.
    
    This function validates and sanitizes host strings to prevent issues
    when constructing URLs for authentication settings. It handles:
    - Empty or whitespace-only hosts
    - Invalid characters
    - Malformed IP addresses
    - Invalid IPv6 addresses
    - Incomplete IPv6 brackets
    
    Security Note: This is a defense-in-depth measure to prevent
    malformed URLs from causing authentication bypass or other issues.
    
    Args:
        host: The host string to sanitize
        
    Returns:
        A valid host string suitable for URL construction (defaults to 'localhost' if invalid)
    """
    if not host or not host.strip():
        return 'localhost'
    
    # Remove whitespace
    host = host.strip()
    
    # Check for minimum length (at least 1 character)
    if len(host) < 1:
        return 'localhost'
    
    # Check if it's a valid hostname or IP address
    # Valid hostname: alphanumeric, dots, hyphens
    # Valid IPv4: digits and dots
    # Valid IPv6: hex digits, colons, brackets
    
    # Simple validation: only allow alphanumeric, dots, hyphens, colons, brackets
    if not re.match(r'^[a-zA-Z0-9.\-:\[\]]+$', host):
        return 'localhost'
    
    # Check for incomplete or mismatched brackets (IPv6)
    open_brackets = host.count('[')
    close_brackets = host.count(']')
    if open_brackets != close_brackets:
        # Mismatched brackets - invalid
        return 'localhost'
    if open_brackets > 1 or close_brackets > 1:
        # Multiple brackets - invalid
        return 'localhost'
    if '[' in host or ']' in host:
        # Has brackets - should be properly formatted IPv6
        if not (host.startswith('[') and host.endswith(']')):
            # Brackets not at start/end - invalid
            return 'localhost'
        # Extract content between brackets
        ipv6_content = host[1:-1]
        if not ipv6_content:
            # Empty brackets - invalid
            return 'localhost'
        # IPv6 should have colons
        if ':' not in ipv6_content:
            return 'localhost'
        # For valid IPv6, we'll let the URL validator catch any remaining issues
    
    # Don't allow hosts that start or end with special characters (except brackets for IPv6)
    if not host.startswith('['):
        if host[0] in '.-:' or host[-1] in '.-:':
            return 'localhost'
    
    # Don't allow hosts that look like invalid IP addresses (e.g., '08')
    # If it's all digits, it should be a valid IP component
    if host.isdigit():
        # Single number hosts like '08' are invalid
        return 'localhost'
    
    # Don't allow hosts with colons that aren't valid IPv6
    # Simple check: if it has colons and no brackets, it should have at least 2 colons
    if ':' in host and '[' not in host:
        # Very simple IPv6 validation: should have multiple colons
        colon_count = host.count(':')
        if colon_count < 2:  # IPv6 needs at least 2 colons
            return 'localhost'
    
    # Additional validation: try to construct a URL to verify it's valid
    # This catches edge cases that regex might miss
    try:
        # Test if we can construct a valid URL with this host
        test_url = f'http://{host}:8000'
        HttpUrl(test_url)
    except Exception:
        # If URL construction fails, the host is invalid
        return 'localhost'
    
    return host


def initialize_server(config: ServerConfig, mcp_instance: Optional[FastMCP] = None) -> FastMCP:
    """
    Initialize FastMCP server with authentication.
    
    This function creates or configures a FastMCP instance with the appropriate
    authentication verifier based on the server configuration. It supports:
    - No authentication for STDIO transport
    - Static token authentication for development
    - JWT authentication for production
    
    Args:
        config: Validated server configuration
        mcp_instance: Optional existing FastMCP instance to configure (if None, creates new one)
        
    Returns:
        Configured FastMCP instance
        
    Raises:
        ValueError: If authentication configuration is invalid
    """
    # Create authentication verifier based on config
    auth_verifier = create_auth_verifier(config)
    
    # If an existing MCP instance is provided, we need to work with it
    # Otherwise create a new one
    if mcp_instance is None:
        # Create FastMCP instance with authentication
        if auth_verifier:
            # Create minimal auth settings required by FastMCP
            # For static token auth, we use localhost URLs as placeholders
            # Sanitize host to ensure it's a valid URL component
            safe_host = _sanitize_host_for_url(config.host)
            auth_settings = AuthSettings(
                issuer_url=HttpUrl(f'http://{safe_host}:{config.port}'),
                resource_server_url=HttpUrl(f'http://{safe_host}:{config.port}')
            )
            mcp_instance = FastMCP("gsc-server", token_verifier=auth_verifier, auth=auth_settings)
            logger.info(f"Initialized server with {config.auth_mode} authentication")
        else:
            mcp_instance = FastMCP("gsc-server")
            logger.info("Initialized server without authentication (STDIO mode)")
    else:
        # For existing instance, we need to set the token_verifier and auth attributes
        # This is a workaround since FastMCP doesn't support adding auth after creation
        if auth_verifier:
            # Create minimal auth settings
            # Sanitize host to ensure it's a valid URL component
            safe_host = _sanitize_host_for_url(config.host)
            auth_settings = AuthSettings(
                issuer_url=HttpUrl(f'http://{safe_host}:{config.port}'),
                resource_server_url=HttpUrl(f'http://{safe_host}:{config.port}')
            )
            # Set both the token verifier and auth settings on the existing instance
            mcp_instance._token_verifier = auth_verifier
            mcp_instance.settings.auth = auth_settings
            logger.info(f"Configured existing server with {config.auth_mode} authentication")
        else:
            logger.info("Configured existing server without authentication (STDIO mode)")
    
    return mcp_instance


def start_server(mcp: FastMCP, config: ServerConfig) -> None:
    """
    Start the MCP server with configured transport.
    
    This function starts the FastMCP server using either STDIO or HTTP transport
    based on the configuration. It handles server binding errors gracefully and
    provides appropriate logging for debugging and monitoring.
    
    Args:
        mcp: FastMCP instance to start
        config: Server configuration containing transport and network settings
        
    Raises:
        OSError: If server fails to bind to the specified host/port
        ValueError: If configuration is invalid
    """
    try:
        if config.transport == "stdio":
            logger.info("Starting server with STDIO transport")
            mcp.run(transport="stdio")
        else:
            # HTTP transport - use uvicorn to run the ASGI app
            logger.info(f"Starting server with HTTP transport on {config.host}:{config.port}")
            logger.info(f"Authentication mode: {config.auth_mode}")
            logger.info(f"MCP endpoint available at: http://{config.host}:{config.port}/mcp")
            
            # Get the ASGI app from FastMCP and run with uvicorn
            import uvicorn
            
            # FastMCP provides streamable_http_app for HTTP transport
            uvicorn.run(
                mcp.streamable_http_app,
                host=config.host,
                port=config.port,
                log_level="info"
            )
    except OSError as e:
        # Handle binding errors
        if "Address already in use" in str(e) or "address already in use" in str(e).lower():
            logger.error(f"Failed to bind to {config.host}:{config.port}: Address already in use")
            logger.error(f"HINT: Another process may be using port {config.port}. Try a different port with --port or MCP_PORT")
            raise
        elif "Permission denied" in str(e) or "permission denied" in str(e).lower():
            logger.error(f"Failed to bind to {config.host}:{config.port}: Permission denied")
            logger.error(f"HINT: Ports below 1024 require root/administrator privileges. Try a port >= 1024")
            raise
        else:
            logger.error(f"Failed to bind to {config.host}:{config.port}: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        raise
