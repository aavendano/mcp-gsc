# Design Document: HTTP Transport with Token Authentication

## Overview

This design document describes the architecture and implementation approach for migrating the Google Search Console MCP server from STDIO transport to HTTP transport with flexible token-based authentication. The solution provides a production-ready HTTP API while maintaining backward compatibility with STDIO transport for existing users.

The design follows FastMCP's authentication patterns and leverages built-in verifiers for both development (static tokens) and production (JWT validation) scenarios. The implementation prioritizes security, configurability, and ease of deployment.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Client (Remote)                      │
│                  (Claude, Custom Client, etc.)               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + Bearer Token
                         │ POST /mcp
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Server (uvicorn)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           FastMCP Server Instance                      │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │      Authentication Middleware                   │ │ │
│  │  │                                                  │ │ │
│  │  │  ┌────────────────┐  ┌────────────────────────┐ │ │ │
│  │  │  │ Static Token   │  │   JWT Verifier         │ │ │ │
│  │  │  │ Verifier       │  │   (Production)         │ │ │ │
│  │  │  │ (Development)  │  │                        │ │ │ │
│  │  │  └────────────────┘  └────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │         MCP Request Router                       │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │      GSC Tools (19+ tools)                       │ │ │
│  │  │  - list_properties                               │ │ │
│  │  │  - get_search_analytics                          │ │ │
│  │  │  - inspect_url_enhanced                          │ │ │
│  │  │  - ... (all existing tools)                      │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Google Search Console API                       │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Client Request**: Client sends HTTP POST to `/mcp` with `Authorization: Bearer <token>` header
2. **Authentication**: FastMCP authentication middleware validates the token using configured verifier
3. **Authorization**: If valid, request proceeds with extracted scopes/claims
4. **Routing**: MCP router dispatches to appropriate GSC tool
5. **Execution**: Tool executes against Google Search Console API
6. **Response**: Result returned to client as JSON

## Components and Interfaces

### 1. Configuration Module

**Purpose**: Centralize all configuration logic with precedence: CLI args > Environment variables > Defaults

**Interface**:
```python
@dataclass
class ServerConfig:
    """Server configuration with validation"""
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
    jwt_required_scopes: Optional[List[str]] = None
    
    @classmethod
    def from_environment(cls) -> 'ServerConfig':
        """Load configuration from environment variables"""
        pass
    
    @classmethod
    def from_cli_args(cls, args: argparse.Namespace) -> 'ServerConfig':
        """Load configuration from CLI arguments, merging with environment"""
        pass
    
    def validate(self) -> None:
        """Validate configuration and raise descriptive errors"""
        pass
```

**Implementation Notes**:
- Use `os.environ.get()` for environment variable access
- Implement validation in `validate()` method to check required fields based on auth_mode
- CLI arguments override environment variables
- Port must be integer in range 1-65535
- Auth mode must be "static" or "jwt"

### 2. Authentication Factory

**Purpose**: Create appropriate token verifier based on configuration

**Interface**:
```python
def create_auth_verifier(config: ServerConfig) -> Optional[Any]:
    """
    Create and configure authentication verifier based on config.
    
    Args:
        config: Server configuration
        
    Returns:
        Configured verifier instance or None for STDIO transport
        
    Raises:
        ValueError: If configuration is invalid for selected auth mode
    """
    pass
```

**Implementation Logic**:
```python
def create_auth_verifier(config: ServerConfig) -> Optional[Any]:
    if config.transport == "stdio":
        return None  # No auth needed for STDIO
    
    if config.auth_mode == "static":
        if not config.admin_token:
            raise ValueError("MCP_ADMIN_TOKEN required for static auth mode")
        
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
        if not all([config.jwks_uri, config.jwt_issuer, config.jwt_audience]):
            raise ValueError(
                "JWT_JWKS_URI, JWT_ISSUER, and JWT_AUDIENCE required for jwt auth mode"
            )
        
        from fastmcp.server.auth.providers.jwt import JWTVerifier
        return JWTVerifier(
            jwks_uri=config.jwks_uri,
            issuer=config.jwt_issuer,
            audience=config.jwt_audience,
            required_scopes=config.jwt_required_scopes
        )
    
    else:
        raise ValueError(f"Invalid auth_mode: {config.auth_mode}")
```

### 3. CLI Argument Parser

**Purpose**: Parse and validate command-line arguments

**Interface**:
```python
def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser with all server options"""
    pass

def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments and return namespace"""
    pass
```

**Arguments**:
- `--host`: Bind address (default: from env or 0.0.0.0)
- `--port`: Listen port (default: from env or 8000)
- `--auth-mode`: Authentication mode: static or jwt (default: from env or static)
- `--transport`: Transport mode: http or stdio (default: http)
- `--help`: Display usage information

### 4. Server Initialization

**Purpose**: Initialize and start the MCP server with configured transport and authentication

**Interface**:
```python
def initialize_server(config: ServerConfig) -> FastMCP:
    """
    Initialize FastMCP server with authentication.
    
    Args:
        config: Validated server configuration
        
    Returns:
        Configured FastMCP instance
    """
    pass

def start_server(mcp: FastMCP, config: ServerConfig) -> None:
    """
    Start the MCP server with configured transport.
    
    Args:
        mcp: FastMCP instance
        config: Server configuration
    """
    pass
```

**Implementation**:
```python
def initialize_server(config: ServerConfig) -> FastMCP:
    auth_verifier = create_auth_verifier(config)
    
    # Create FastMCP instance with auth
    if auth_verifier:
        mcp_instance = FastMCP("gsc-server", auth=auth_verifier)
        logger.info(f"Initialized server with {config.auth_mode} authentication")
    else:
        mcp_instance = FastMCP("gsc-server")
        logger.info("Initialized server without authentication (STDIO mode)")
    
    return mcp_instance

def start_server(mcp: FastMCP, config: ServerConfig) -> None:
    if config.transport == "stdio":
        logger.info("Starting server with STDIO transport")
        mcp.run(transport="stdio")
    else:
        logger.info(f"Starting server with HTTP transport on {config.host}:{config.port}")
        logger.info(f"MCP endpoint available at: http://{config.host}:{config.port}/mcp")
        mcp.run(
            transport="http",
            host=config.host,
            port=config.port
        )
```

### 5. Logging Configuration

**Purpose**: Provide structured logging for debugging and monitoring

**Interface**:
```python
def configure_logging() -> logging.Logger:
    """Configure logging with appropriate format and level"""
    pass
```

**Log Levels**:
- INFO: Server startup, configuration, successful requests
- WARNING: Authentication failures, invalid configurations
- ERROR: Server errors, binding failures
- DEBUG: Detailed request/response information (optional via env var)

**Security Considerations**:
- Never log bearer tokens
- Never log sensitive environment variables
- Log authentication failures without token details
- Use structured logging for easier parsing

## Data Models

### ServerConfig

```python
@dataclass
class ServerConfig:
    """Complete server configuration"""
    host: str
    port: int
    auth_mode: str
    transport: str
    admin_token: Optional[str]
    jwks_uri: Optional[str]
    jwt_issuer: Optional[str]
    jwt_audience: Optional[str]
    jwt_required_scopes: Optional[List[str]]
```

### Environment Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `MCP_HOST` | string | No | `0.0.0.0` | Server bind address |
| `MCP_PORT` | integer | No | `8000` | Server listen port |
| `MCP_AUTH_MODE` | string | No | `static` | Authentication mode: `static` or `jwt` |
| `MCP_TRANSPORT` | string | No | `http` | Transport mode: `http` or `stdio` |
| `MCP_ADMIN_TOKEN` | string | Yes (static) | - | Admin token for static auth |
| `JWT_JWKS_URI` | string | Yes (jwt) | - | JWKS endpoint URL |
| `JWT_ISSUER` | string | Yes (jwt) | - | Expected JWT issuer |
| `JWT_AUDIENCE` | string | Yes (jwt) | - | Expected JWT audience |
| `JWT_REQUIRED_SCOPES` | string | No | - | Comma-separated required scopes |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Configuration Precedence

*For any* configuration parameter that can be set via both environment variable and CLI argument, when both are provided, the CLI argument value should be used.

**Validates: Requirements 5.4**

### Property 2: Authentication Rejection

*For any* HTTP request without a valid Bearer token, the server should reject the request with HTTP 401 status.

**Validates: Requirements 3.4, 3.5, 4.6, 4.7**

### Property 3: Token Logging Safety

*For any* log message generated by the server, the message should not contain bearer token values or sensitive credentials.

**Validates: Requirements 9.1, 9.2, 9.3**

### Property 4: Port Validation

*For any* port value provided (via environment or CLI), if the value is not an integer between 1 and 65535, the server should log an error and exit before attempting to bind.

**Validates: Requirements 2.6**

### Property 5: Auth Mode Validation

*For any* auth_mode value provided, if the value is not "static" or "jwt", the server should raise a ValueError with a descriptive message.

**Validates: Requirements 2.3, 2.4, 5.3**

### Property 6: Static Auth Token Requirement

*For any* server configuration with auth_mode="static" and transport="http", if MCP_ADMIN_TOKEN is not set, the server should log an error and exit before starting.

**Validates: Requirements 3.1, 3.2**

### Property 7: JWT Configuration Completeness

*For any* server configuration with auth_mode="jwt", if any of JWT_JWKS_URI, JWT_ISSUER, or JWT_AUDIENCE is missing, the server should raise a ValueError before starting.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 8: Transport Mode Functionality

*For any* valid server configuration, all existing GSC tools should function identically regardless of whether transport is "stdio" or "http".

**Validates: Requirements 8.5**

### Property 9: STDIO No-Auth Requirement

*For any* server configuration with transport="stdio", the server should start successfully without requiring authentication configuration.

**Validates: Requirements 8.4**

### Property 10: Endpoint Path Consistency

*For any* HTTP transport configuration, the MCP endpoint should be accessible at exactly the path `/mcp`.

**Validates: Requirements 1.3**

## Error Handling

### Configuration Errors

**Scenario**: Invalid or missing configuration
**Handling**:
- Validate all configuration before server initialization
- Log descriptive error messages indicating which configuration is missing/invalid
- Exit with non-zero status code
- Never start server with invalid configuration

**Example Error Messages**:
```
ERROR: MCP_ADMIN_TOKEN environment variable is required for static authentication mode
ERROR: Invalid port value '99999': must be between 1 and 65535
ERROR: JWT authentication requires JWT_JWKS_URI, JWT_ISSUER, and JWT_AUDIENCE
```

### Authentication Errors

**Scenario**: Invalid or missing authentication token
**Handling**:
- Return HTTP 401 Unauthorized
- Log authentication failure without exposing token
- Include generic error message in response
- Do not reveal authentication mechanism details

**Example Responses**:
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

### Server Binding Errors

**Scenario**: Unable to bind to specified host/port
**Handling**:
- Log detailed error including host, port, and system error
- Suggest common solutions (port in use, permission denied)
- Exit with non-zero status code

**Example Error Messages**:
```
ERROR: Failed to bind to 0.0.0.0:8000: Address already in use
HINT: Another process may be using port 8000. Try a different port with --port or MCP_PORT
```

### JWT Validation Errors

**Scenario**: JWT token validation fails
**Handling**:
- Return HTTP 401 Unauthorized
- Log specific validation failure reason (expired, invalid signature, wrong issuer)
- Do not expose validation details to client
- Include timestamp for debugging

**Example Log Messages**:
```
WARNING: JWT validation failed: Token expired at 2024-01-15T10:30:00Z
WARNING: JWT validation failed: Invalid signature
WARNING: JWT validation failed: Issuer mismatch (expected: https://auth.example.com, got: https://other.com)
```

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases for configuration and authentication logic:

1. **Configuration Loading**:
   - Test environment variable parsing
   - Test CLI argument parsing
   - Test precedence (CLI > env > default)
   - Test validation of invalid values

2. **Authentication Factory**:
   - Test StaticTokenVerifier creation with valid config
   - Test JWTVerifier creation with valid config
   - Test error handling for missing required config
   - Test None return for STDIO transport

3. **Validation Logic**:
   - Test port range validation (valid: 1-65535, invalid: 0, 65536, "abc")
   - Test auth mode validation (valid: "static", "jwt", invalid: "oauth", "")
   - Test required field validation for each auth mode

4. **Error Messages**:
   - Test that error messages are descriptive
   - Test that error messages don't contain sensitive data
   - Test that appropriate exit codes are used

### Property-Based Tests

Property-based tests will verify universal properties across many generated inputs:

1. **Property Test: Configuration Precedence** (Property 1)
   - Generate random valid configuration values
   - Set both environment variable and CLI argument
   - Verify CLI argument always wins
   - Tag: **Feature: http-auth-migration, Property 1: Configuration Precedence**

2. **Property Test: Port Validation** (Property 4)
   - Generate random port values (valid and invalid)
   - Verify valid ports (1-65535) pass validation
   - Verify invalid ports raise ValueError
   - Tag: **Feature: http-auth-migration, Property 4: Port Validation**

3. **Property Test: Token Logging Safety** (Property 3)
   - Generate random token strings
   - Trigger various log scenarios
   - Verify no log message contains the token
   - Tag: **Feature: http-auth-migration, Property 3: Token Logging Safety**

4. **Property Test: Auth Mode Validation** (Property 5)
   - Generate random auth_mode strings
   - Verify only "static" and "jwt" are accepted
   - Verify others raise ValueError
   - Tag: **Feature: http-auth-migration, Property 5: Auth Mode Validation**

5. **Property Test: Static Auth Requirements** (Property 6)
   - Generate configurations with auth_mode="static"
   - Vary presence of MCP_ADMIN_TOKEN
   - Verify server fails to start when token missing
   - Tag: **Feature: http-auth-migration, Property 6: Static Auth Token Requirement**

6. **Property Test: JWT Configuration Completeness** (Property 7)
   - Generate JWT configurations with various missing fields
   - Verify server fails when any required field missing
   - Verify server starts when all fields present
   - Tag: **Feature: http-auth-migration, Property 7: JWT Configuration Completeness**

### Integration Tests

Integration tests will verify end-to-end functionality:

1. **HTTP Server Startup**:
   - Start server with valid configuration
   - Verify server binds to correct host/port
   - Verify `/mcp` endpoint is accessible
   - Shutdown server cleanly

2. **Static Token Authentication**:
   - Start server with static auth
   - Send request with valid token → expect success
   - Send request with invalid token → expect 401
   - Send request without token → expect 401

3. **STDIO Backward Compatibility**:
   - Start server with transport="stdio"
   - Verify server starts without auth config
   - Verify tools work via STDIO

4. **Tool Functionality**:
   - Start HTTP server with auth
   - Authenticate and call each GSC tool
   - Verify responses match STDIO behavior

### Testing Framework

- **Unit Tests**: pytest
- **Property Tests**: Hypothesis (Python property-based testing library)
- **Integration Tests**: pytest with FastMCP test utilities
- **Minimum Iterations**: 100 per property test

### Test Organization

```
tests/
├── unit/
│   ├── test_configuration.py
│   ├── test_auth_factory.py
│   └── test_validation.py
├── property/
│   ├── test_config_properties.py
│   ├── test_auth_properties.py
│   └── test_logging_properties.py
└── integration/
    ├── test_http_server.py
    ├── test_authentication.py
    └── test_tool_functionality.py
```
