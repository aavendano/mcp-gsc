"""
Authentication factory module for the Google Search Console MCP server.

This module provides authentication verifier creation based on server configuration,
supporting both static token authentication (development) and JWT authentication (production).
"""

from typing import Optional, Any
from config import ServerConfig


def create_auth_verifier(config: ServerConfig) -> Optional[Any]:
    """
    Create and configure authentication verifier based on config.
    
    This factory function returns the appropriate authentication verifier
    based on the server configuration. It supports:
    - None for STDIO transport (no authentication needed)
    - StaticTokenVerifier for development with simple token auth
    - JWTVerifier for production with JWT validation
    
    Args:
        config: Server configuration containing transport and auth settings
        
    Returns:
        Configured verifier instance or None for STDIO transport
        
    Raises:
        ValueError: If configuration is invalid for selected auth mode
    """
    # STDIO transport doesn't require authentication
    if config.transport == "stdio":
        return None
    
    # HTTP transport requires authentication
    if config.auth_mode == "static":
        # Validate required configuration for static auth
        if not config.admin_token:
            raise ValueError(
                "MCP_ADMIN_TOKEN environment variable is required for static authentication mode"
            )
        
        # Import and create StaticTokenVerifier
        # Security Note: StaticTokenVerifier is suitable for development only.
        # For production, use JWT authentication with proper identity providers.
        from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
        
        return StaticTokenVerifier(
            tokens={
                config.admin_token: {
                    "client_id": "admin",
                    "scopes": ["read:gsc", "write:gsc"]
                }
            },
            required_scopes=["read:gsc"]
        )
    
    elif config.auth_mode == "jwt":
        # Validate required configuration for JWT auth
        missing_fields = []
        if not config.jwks_uri:
            missing_fields.append("JWT_JWKS_URI")
        if not config.jwt_issuer:
            missing_fields.append("JWT_ISSUER")
        if not config.jwt_audience:
            missing_fields.append("JWT_AUDIENCE")
        
        if missing_fields:
            raise ValueError(
                f"JWT authentication requires the following environment variables: "
                f"{', '.join(missing_fields)}"
            )
        
        # Import and create JWTVerifier
        # Security Note: JWTVerifier provides cryptographic validation of tokens.
        # It verifies:
        # - Token signature using public keys from JWKS endpoint
        # - Token issuer matches expected issuer
        # - Token audience matches expected audience
        # - Token expiration (exp claim)
        # - Required scopes if specified
        from fastmcp.server.auth.providers.jwt import JWTVerifier
        
        return JWTVerifier(
            jwks_uri=config.jwks_uri,
            issuer=config.jwt_issuer,
            audience=config.jwt_audience,
            required_scopes=config.jwt_required_scopes if config.jwt_required_scopes else None
        )
    
    else:
        raise ValueError(f"Invalid auth_mode: {config.auth_mode}")
