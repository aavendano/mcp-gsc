"""
Configuration module for the Google Search Console MCP server.

This module provides configuration management for HTTP transport with token authentication,
supporting both environment variables and CLI arguments with proper precedence.
"""

import os
import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ServerConfig:
    """
    Server configuration with validation.
    
    Configuration precedence: CLI arguments > Environment variables > Defaults
    """
    host: str = "0.0.0.0"
    port: int = 8000
    auth_mode: str = "static"  # "static" or "jwt"
    transport: str = "http"  # "http" or "stdio"
    
    # Static token config
    admin_token: Optional[str] = None
    
    # JWT config
    jwks_uri: Optional[str] = None
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_required_scopes: Optional[List[str]] = field(default_factory=list)
    
    @classmethod
    def from_environment(cls) -> 'ServerConfig':
        """
        Load configuration from environment variables.
        
        Returns:
            ServerConfig instance populated from environment variables
        """
        # Parse JWT required scopes if provided
        jwt_scopes_str = os.environ.get("JWT_REQUIRED_SCOPES", "")
        jwt_scopes = [s.strip() for s in jwt_scopes_str.split(",") if s.strip()] if jwt_scopes_str else []
        
        # Parse port with default fallback
        port_str = os.environ.get("MCP_PORT", "8000")
        try:
            port = int(port_str)
        except ValueError:
            port = 8000  # Use default if invalid
        
        return cls(
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=port,
            auth_mode=os.environ.get("MCP_AUTH_MODE", "static"),
            transport=os.environ.get("MCP_TRANSPORT", "http"),
            admin_token=os.environ.get("MCP_ADMIN_TOKEN"),
            jwks_uri=os.environ.get("JWT_JWKS_URI"),
            jwt_issuer=os.environ.get("JWT_ISSUER"),
            jwt_audience=os.environ.get("JWT_AUDIENCE"),
            jwt_required_scopes=jwt_scopes
        )
    
    @classmethod
    def from_cli_args(cls, args: argparse.Namespace) -> 'ServerConfig':
        """
        Load configuration from CLI arguments, merging with environment variables.
        
        CLI arguments take precedence over environment variables.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            ServerConfig instance with CLI args taking precedence over environment
        """
        # Start with environment configuration
        config = cls.from_environment()
        
        # Override with CLI arguments if provided
        if hasattr(args, 'host') and args.host is not None:
            config.host = args.host
        
        if hasattr(args, 'port') and args.port is not None:
            config.port = args.port
        
        if hasattr(args, 'auth_mode') and args.auth_mode is not None:
            config.auth_mode = args.auth_mode
        
        if hasattr(args, 'transport') and args.transport is not None:
            config.transport = args.transport
        
        return config
    
    def validate(self) -> None:
        """
        Validate configuration and raise descriptive errors if invalid.
        
        This method performs comprehensive validation of all configuration parameters
        to ensure the server can start successfully and securely. Validation includes:
        
        - Port range validation (1-65535)
        - Authentication mode validation (static or jwt)
        - Transport mode validation (http or stdio)
        - Required authentication parameters based on mode
        
        Security Note: Validation happens before server startup to prevent
        misconfiguration that could lead to security issues. For example:
        - Missing authentication tokens would allow unauthenticated access
        - Invalid JWT configuration would fail silently without proper validation
        
        Raises:
            ValueError: If configuration is invalid with descriptive error message
        """
        # Validate port range
        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            raise ValueError(
                f"Invalid port value '{self.port}': must be an integer between 1 and 65535"
            )
        
        # Validate auth_mode
        valid_auth_modes = ["static", "jwt"]
        if self.auth_mode not in valid_auth_modes:
            raise ValueError(
                f"Invalid auth_mode: {self.auth_mode}. Must be one of: {', '.join(valid_auth_modes)}"
            )
        
        # Validate transport
        valid_transports = ["http", "stdio"]
        if self.transport not in valid_transports:
            raise ValueError(
                f"Invalid transport: {self.transport}. Must be one of: {', '.join(valid_transports)}"
            )
        
        # STDIO transport should not require authentication
        if self.transport == "stdio":
            # No auth validation needed for STDIO
            return
        
        # HTTP transport requires authentication configuration
        if self.transport == "http":
            if self.auth_mode == "static":
                if not self.admin_token:
                    raise ValueError(
                        "MCP_ADMIN_TOKEN environment variable is required for static authentication mode"
                    )
            
            elif self.auth_mode == "jwt":
                missing_fields = []
                if not self.jwks_uri:
                    missing_fields.append("JWT_JWKS_URI")
                if not self.jwt_issuer:
                    missing_fields.append("JWT_ISSUER")
                if not self.jwt_audience:
                    missing_fields.append("JWT_AUDIENCE")
                
                if missing_fields:
                    raise ValueError(
                        f"JWT authentication requires the following environment variables: "
                        f"{', '.join(missing_fields)}"
                    )


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create CLI argument parser with all server options.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="gsc-server",
        description="Google Search Console MCP Server with HTTP transport and token authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (HTTP on 0.0.0.0:8000, static auth)
  python gsc_server.py
  
  # Start with custom host and port
  python gsc_server.py --host 127.0.0.1 --port 9000
  
  # Start with JWT authentication
  python gsc_server.py --auth-mode jwt
  
  # Start with STDIO transport (backward compatibility)
  python gsc_server.py --transport stdio

Environment Variables:
  MCP_HOST              Server bind address (default: 0.0.0.0)
  MCP_PORT              Server listen port (default: 8000)
  MCP_AUTH_MODE         Authentication mode: static or jwt (default: static)
  MCP_TRANSPORT         Transport mode: http or stdio (default: http)
  MCP_ADMIN_TOKEN       Admin token for static authentication (required for static mode)
  JWT_JWKS_URI          JWKS endpoint URL (required for jwt mode)
  JWT_ISSUER            Expected JWT issuer (required for jwt mode)
  JWT_AUDIENCE          Expected JWT audience (required for jwt mode)
  JWT_REQUIRED_SCOPES   Comma-separated required scopes (optional for jwt mode)

Note: CLI arguments take precedence over environment variables.
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Server bind address (default: from MCP_HOST env or 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server listen port (default: from MCP_PORT env or 8000)"
    )
    
    parser.add_argument(
        "--auth-mode",
        type=str,
        choices=["static", "jwt"],
        default=None,
        dest="auth_mode",
        help="Authentication mode: 'static' for development with simple tokens, 'jwt' for production with JWT validation (default: from MCP_AUTH_MODE env or static)"
    )
    
    parser.add_argument(
        "--transport",
        type=str,
        choices=["http", "stdio"],
        default=None,
        help="Transport mode: 'http' for network access, 'stdio' for local-only (default: from MCP_TRANSPORT env or http)"
    )
    
    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse CLI arguments and return namespace.
    
    Args:
        args: Optional list of arguments to parse (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments as argparse.Namespace
    """
    parser = create_argument_parser()
    return parser.parse_args(args)
