# Implementation Plan: HTTP Transport with Token Authentication

## Overview

This implementation plan breaks down the migration from STDIO to HTTP transport with token authentication into discrete, testable tasks. Each task builds incrementally on previous work, ensuring the server remains functional throughout development. The plan prioritizes core functionality first, with optional testing tasks marked for flexibility.

## Tasks

- [x] 1. Update project dependencies
  - Add `fastmcp>=2.11.0` to requirements.txt for authentication support
  - Add `uvicorn` for HTTP server functionality
  - Add `python-jose[cryptography]` for JWT validation
  - Add `cryptography` for cryptographic operations
  - Add `hypothesis` for property-based testing
  - Add `pytest` and `pytest-asyncio` for testing framework
  - Verify all existing Google API dependencies remain
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 2. Create configuration module
  - [x] 2.1 Implement ServerConfig dataclass
    - Define all configuration fields with types and defaults
    - Implement `from_environment()` class method to load from env vars
    - Implement `from_cli_args()` class method to merge CLI and env config
    - Implement `validate()` method with comprehensive validation logic
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 2.2 Write property test for configuration precedence
    - **Property 1: Configuration Precedence**
    - **Validates: Requirements 5.4**

  - [x] 2.3 Write property test for port validation
    - **Property 4: Port Validation**
    - **Validates: Requirements 2.6**

  - [x] 2.4 Write property test for auth mode validation
    - **Property 5: Auth Mode Validation**
    - **Validates: Requirements 2.3, 2.4, 5.3**

  - [x] 2.5 Write unit tests for ServerConfig
    - Test environment variable parsing with various values
    - Test CLI argument parsing and precedence
    - Test validation error messages
    - Test default values
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Implement authentication factory
  - [x] 3.1 Create create_auth_verifier function
    - Import StaticTokenVerifier and JWTVerifier from fastmcp
    - Implement logic to return None for STDIO transport
    - Implement StaticTokenVerifier creation for static mode
    - Implement JWTVerifier creation for jwt mode
    - Add validation for required configuration per mode
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4_

  - [x] 3.2 Write property test for static auth requirements
    - **Property 6: Static Auth Token Requirement**
    - **Validates: Requirements 3.1, 3.2**

  - [x] 3.3 Write property test for JWT configuration completeness
    - **Property 7: JWT Configuration Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 3.4 Write unit tests for authentication factory
    - Test StaticTokenVerifier creation with valid config
    - Test JWTVerifier creation with valid config
    - Test error handling for missing required config
    - Test None return for STDIO transport
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3_

- [x] 4. Implement CLI argument parser
  - [x] 4.1 Create argument parser with all options
    - Add --host argument with help text
    - Add --port argument with type validation
    - Add --auth-mode argument with choices
    - Add --transport argument with choices
    - Add --help with comprehensive usage information
    - Implement parse_arguments() function
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6_

  - [x] 4.2 Write unit tests for CLI parser
    - Test argument parsing with various combinations
    - Test help text generation
    - Test invalid argument handling
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6_

- [x] 5. Checkpoint - Ensure configuration and auth factory tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement logging configuration
  - [x] 6.1 Create configure_logging function
    - Set up structured logging format with timestamps
    - Configure log levels (INFO, WARNING, ERROR, DEBUG)
    - Add environment variable for debug mode
    - Implement log filtering to prevent token exposure
    - _Requirements: 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 6.2 Write property test for token logging safety
    - **Property 3: Token Logging Safety**
    - **Validates: Requirements 9.1, 9.2, 9.3**

  - [x] 6.3 Write unit tests for logging
    - Test log format and structure
    - Test that sensitive data is filtered
    - Test different log levels
    - _Requirements: 9.1, 9.2, 9.3, 10.1, 10.2, 10.3_

- [x] 7. Implement server initialization
  - [x] 7.1 Create initialize_server function
    - Call create_auth_verifier with config
    - Create FastMCP instance with or without auth
    - Add logging for initialization steps
    - Return configured FastMCP instance
    - _Requirements: 1.1, 1.2, 1.3, 3.6, 4.5, 10.1, 10.2_

  - [x] 7.2 Create start_server function
    - Implement STDIO transport path
    - Implement HTTP transport path with host and port
    - Add startup logging with endpoint information
    - Handle server binding errors gracefully
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 8.1, 8.2, 8.3, 10.5, 10.6_

  - [x] 7.3 Write property test for transport mode functionality
    - **Property 8: Transport Mode Functionality**
    - **Validates: Requirements 8.5**

  - [x] 7.4 Write property test for STDIO no-auth requirement
    - **Property 9: STDIO No-Auth Requirement**
    - **Validates: Requirements 8.4**

  - [x] 7.5 Write unit tests for server initialization
    - Test server creation with static auth
    - Test server creation with JWT auth
    - Test server creation without auth (STDIO)
    - Test error handling for invalid config
    - _Requirements: 1.1, 1.2, 3.6, 4.5, 8.4_

- [x] 8. Refactor main entry point
  - [x] 8.1 Update main block in gsc_server.py
    - Call configure_logging() at startup
    - Parse CLI arguments
    - Load and validate configuration
    - Initialize server with configuration
    - Start server with appropriate transport
    - Add try/except for graceful error handling
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.1, 5.2, 5.3, 5.4, 8.1, 8.2, 8.3, 10.1, 10.2, 10.5, 10.6_

  - [x] 8.2 Write integration test for HTTP server startup
    - Start server with valid HTTP configuration
    - Verify server binds to correct host/port
    - Verify /mcp endpoint is accessible
    - Shutdown server cleanly
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 8.3 Write integration test for STDIO backward compatibility
    - Start server with transport="stdio"
    - Verify server starts without auth config
    - Verify basic tool functionality
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Checkpoint - Ensure server initialization tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Add authentication integration tests
  - [x] 10.1 Write integration test for static token authentication
    - Start server with static auth configuration
    - Send request with valid token → verify success
    - Send request with invalid token → verify 401
    - Send request without token → verify 401
    - **Property 2: Authentication Rejection**
    - **Validates: Requirements 3.4, 3.5, 4.6, 4.7**

  - [x] 10.2 Write integration test for endpoint path consistency
    - Start HTTP server
    - Verify /mcp endpoint responds correctly
    - Verify other paths return 404
    - **Property 10: Endpoint Path Consistency**
    - **Validates: Requirements 1.3**

  - [x] 10.3 Write integration test for tool functionality
    - Start HTTP server with authentication
    - Authenticate and call list_properties tool
    - Authenticate and call get_search_analytics tool
    - Verify responses match expected format
    - _Requirements: 8.5_

- [x] 11. Update documentation
  - [x] 11.1 Update README.md with HTTP configuration
    - Add section on HTTP transport setup
    - Document all environment variables with examples
    - Explain static vs JWT authentication modes
    - Provide curl examples with Bearer tokens
    - Add security warnings and best practices
    - Document the /mcp endpoint path
    - Add troubleshooting section for auth errors
    - Include example configurations for development and production
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 9.4, 9.5, 9.6_

  - [x] 11.2 Create MIGRATION.md guide
    - Document migration steps from STDIO to HTTP
    - Provide before/after configuration examples
    - List breaking changes (if any)
    - Include rollback instructions
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 11.3 Add inline code documentation
    - Add docstrings to all new functions
    - Add type hints to all function signatures
    - Add comments explaining complex logic
    - Document security considerations in code

- [x] 12. Final integration testing
  - [x] 12.1 Test complete development workflow
    - Set up server with static token auth
    - Connect with MCP client using Bearer token
    - Execute multiple GSC tools
    - Verify all tools work correctly
    - _Requirements: 1.1, 1.2, 1.3, 3.3, 3.4, 3.5, 3.6, 8.5_

  - [x] 12.2 Test production configuration
    - Set up server with JWT auth (using test JWT provider)
    - Verify JWT validation works correctly
    - Test with expired JWT → verify rejection
    - Test with invalid signature → verify rejection
    - _Requirements: 4.5, 4.6, 4.7, 4.8_

  - [x] 12.3 Test error scenarios
    - Test server startup with missing required config
    - Test server startup with invalid port
    - Test authentication with malformed tokens
    - Verify all error messages are clear and helpful
    - _Requirements: 2.6, 3.2, 4.1, 4.2, 4.3, 10.3, 10.4, 10.6_

- [x] 13. Final checkpoint - Complete testing and documentation review
  - Ensure all tests pass, ask the user if questions arise.
  - Verify documentation is complete and accurate.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end functionality
- All existing GSC tools remain unchanged throughout migration
