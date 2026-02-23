# Requirements Document

## Introduction

This document specifies the requirements for migrating the Google Search Console MCP server from STDIO transport to HTTP transport with token-based authentication. The migration will enable remote access to the server while maintaining security through flexible authentication mechanisms suitable for both development and production environments.

## Glossary

- **MCP_Server**: The FastMCP server instance that exposes Google Search Console tools
- **STDIO_Transport**: Standard input/output communication method for local-only server access
- **HTTP_Transport**: Network-based communication method enabling remote server access
- **Token_Verifier**: Component responsible for validating authentication tokens
- **Static_Token_Verifier**: Development-only verifier that accepts predefined tokens from environment variables
- **JWT_Verifier**: Production-ready verifier that validates JSON Web Tokens using JWKS endpoints
- **Bearer_Token**: Authentication token passed in the HTTP Authorization header
- **JWKS_Endpoint**: JSON Web Key Set endpoint providing public keys for JWT validation
- **Environment_Variable**: System-level configuration value accessible to the application
- **GSC_Tool**: Any of the 19+ Google Search Console tools exposed by the server

## Requirements

### Requirement 1: HTTP Transport Configuration

**User Story:** As a developer, I want to configure the server to use HTTP transport instead of STDIO, so that I can access the MCP server remotely over a network.

#### Acceptance Criteria

1. WHEN the server starts, THE MCP_Server SHALL bind to a configurable host address
2. WHEN the server starts, THE MCP_Server SHALL listen on a configurable port number
3. THE MCP_Server SHALL expose the MCP endpoint at the path `/mcp`
4. WHEN host is not specified, THE MCP_Server SHALL default to `0.0.0.0` (all interfaces)
5. WHEN port is not specified, THE MCP_Server SHALL default to port `8000`
6. WHEN the server starts successfully, THE MCP_Server SHALL log the accessible endpoint URL

### Requirement 2: Environment-Based Configuration

**User Story:** As a system administrator, I want to configure server settings through environment variables, so that I can deploy the server without modifying code.

#### Acceptance Criteria

1. WHEN the `MCP_HOST` environment variable is set, THE MCP_Server SHALL use its value as the bind address
2. WHEN the `MCP_PORT` environment variable is set, THE MCP_Server SHALL use its value as the listen port
3. WHEN the `MCP_AUTH_MODE` environment variable is set to `static`, THE MCP_Server SHALL use Static_Token_Verifier
4. WHEN the `MCP_AUTH_MODE` environment variable is set to `jwt`, THE MCP_Server SHALL use JWT_Verifier
5. WHEN the `MCP_AUTH_MODE` environment variable is not set, THE MCP_Server SHALL default to `static` mode
6. WHEN port value is invalid, THE MCP_Server SHALL log an error and exit gracefully

### Requirement 3: Static Token Authentication (Development)

**User Story:** As a developer, I want to use simple token-based authentication during development, so that I can test the server quickly without complex OAuth setup.

#### Acceptance Criteria

1. WHEN Static_Token_Verifier is active, THE MCP_Server SHALL require the `MCP_ADMIN_TOKEN` environment variable
2. WHEN `MCP_ADMIN_TOKEN` is not set, THE MCP_Server SHALL log an error and exit
3. WHEN a request includes a Bearer_Token matching `MCP_ADMIN_TOKEN`, THE MCP_Server SHALL authenticate the request
4. WHEN a request includes an invalid Bearer_Token, THE MCP_Server SHALL reject the request with HTTP 401
5. WHEN a request lacks an Authorization header, THE MCP_Server SHALL reject the request with HTTP 401
6. WHEN Static_Token_Verifier is active, THE MCP_Server SHALL assign default scopes `["read:gsc", "write:gsc"]` to authenticated requests

### Requirement 4: JWT Authentication (Production)

**User Story:** As a security engineer, I want to use JWT-based authentication in production, so that I can integrate with external identity providers and validate tokens cryptographically.

#### Acceptance Criteria

1. WHEN JWT_Verifier is active, THE MCP_Server SHALL require the `JWT_JWKS_URI` environment variable
2. WHEN JWT_Verifier is active, THE MCP_Server SHALL require the `JWT_ISSUER` environment variable
3. WHEN JWT_Verifier is active, THE MCP_Server SHALL require the `JWT_AUDIENCE` environment variable
4. WHEN `JWT_REQUIRED_SCOPES` is set, THE MCP_Server SHALL validate that tokens contain all required scopes
5. WHEN a request includes a valid JWT Bearer_Token, THE MCP_Server SHALL authenticate the request
6. WHEN a request includes an expired JWT, THE MCP_Server SHALL reject the request with HTTP 401
7. WHEN a request includes a JWT with invalid signature, THE MCP_Server SHALL reject the request with HTTP 401
8. WHEN JWT validation fails, THE MCP_Server SHALL log the failure reason

### Requirement 5: Command-Line Interface

**User Story:** As a developer, I want to configure server settings via command-line arguments, so that I can override environment variables for testing.

#### Acceptance Criteria

1. WHEN the `--host` argument is provided, THE MCP_Server SHALL use it as the bind address
2. WHEN the `--port` argument is provided, THE MCP_Server SHALL use it as the listen port
3. WHEN the `--auth-mode` argument is provided, THE MCP_Server SHALL use it to select the Token_Verifier
4. WHEN both environment variable and CLI argument are provided, THE MCP_Server SHALL prioritize the CLI argument
5. WHEN the `--help` argument is provided, THE MCP_Server SHALL display usage information and exit
6. THE MCP_Server SHALL validate all CLI arguments before starting

### Requirement 6: Dependency Management

**User Story:** As a developer, I want all required dependencies to be properly specified, so that I can install and run the server without missing packages.

#### Acceptance Criteria

1. THE requirements.txt file SHALL include `fastmcp>=2.11.0` for authentication support
2. THE requirements.txt file SHALL include `uvicorn` for HTTP server functionality
3. THE requirements.txt file SHALL include `python-jose[cryptography]` for JWT validation
4. THE requirements.txt file SHALL include `cryptography` for cryptographic operations
5. THE requirements.txt file SHALL maintain all existing Google API dependencies
6. WHEN dependencies are installed, THE MCP_Server SHALL start without import errors

### Requirement 7: Documentation Updates

**User Story:** As a user, I want clear documentation on how to configure and run the HTTP server, so that I can deploy it successfully.

#### Acceptance Criteria

1. THE README.md SHALL document the HTTP transport configuration
2. THE README.md SHALL provide examples of environment variable configuration
3. THE README.md SHALL explain the difference between static and JWT authentication modes
4. THE README.md SHALL include example Bearer_Token usage with curl or HTTP clients
5. THE README.md SHALL warn against exposing the server without authentication
6. THE README.md SHALL document the `/mcp` endpoint path
7. THE README.md SHALL provide troubleshooting guidance for common authentication errors

### Requirement 8: Backward Compatibility

**User Story:** As an existing user, I want the option to continue using STDIO transport, so that my current setup is not disrupted.

#### Acceptance Criteria

1. WHEN the `--transport` CLI argument is set to `stdio`, THE MCP_Server SHALL use STDIO transport
2. WHEN the `--transport` CLI argument is set to `http`, THE MCP_Server SHALL use HTTP transport
3. WHEN the `--transport` argument is not provided, THE MCP_Server SHALL default to HTTP transport
4. WHEN STDIO transport is used, THE MCP_Server SHALL not require authentication configuration
5. THE MCP_Server SHALL maintain all existing GSC_Tool functionality regardless of transport

### Requirement 9: Security Best Practices

**User Story:** As a security-conscious administrator, I want the server to follow security best practices, so that I can deploy it safely.

#### Acceptance Criteria

1. THE MCP_Server SHALL never log Bearer_Token values
2. THE MCP_Server SHALL never log sensitive environment variable values
3. WHEN authentication fails, THE MCP_Server SHALL log the failure without exposing token details
4. THE README.md SHALL recommend using HTTPS in production deployments
5. THE README.md SHALL warn against using Static_Token_Verifier in production
6. THE README.md SHALL recommend rotating tokens regularly

### Requirement 10: Error Handling and Logging

**User Story:** As a system administrator, I want clear error messages and logging, so that I can diagnose and resolve issues quickly.

#### Acceptance Criteria

1. WHEN the server starts, THE MCP_Server SHALL log the transport mode being used
2. WHEN the server starts, THE MCP_Server SHALL log the authentication mode being used
3. WHEN authentication configuration is invalid, THE MCP_Server SHALL log a descriptive error
4. WHEN a request is rejected, THE MCP_Server SHALL log the rejection reason
5. WHEN the server binds successfully, THE MCP_Server SHALL log the listening address and port
6. WHEN the server fails to bind, THE MCP_Server SHALL log the error and exit gracefully
