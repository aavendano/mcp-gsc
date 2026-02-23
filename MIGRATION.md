# Migration Guide: STDIO to HTTP Transport

This guide helps you migrate from STDIO transport to HTTP transport with authentication.

## Overview

The Google Search Console MCP server now supports HTTP transport, enabling remote access with secure authentication. This migration guide covers:

- Understanding the differences between STDIO and HTTP transport
- Step-by-step migration instructions
- Configuration examples
- Breaking changes (if any)
- Rollback procedures

## Transport Comparison

### STDIO Transport (Original)

- **Access:** Local only (same machine as Claude Desktop)
- **Authentication:** None required
- **Use Case:** Personal use, local development
- **Configuration:** Simple, minimal setup
- **Security:** Relies on local machine security

### HTTP Transport (New)

- **Access:** Network-based (local or remote)
- **Authentication:** Required (Static tokens or JWT)
- **Use Case:** Remote access, team collaboration, production deployments
- **Configuration:** Requires authentication setup
- **Security:** Token-based authentication, HTTPS recommended

## Migration Steps

### Step 1: Verify Current Setup

Before migrating, ensure your current STDIO setup is working:

1. Open Claude Desktop
2. Test a GSC tool (e.g., "list my GSC properties")
3. Verify you receive results

### Step 2: Update Dependencies

Ensure you have the latest dependencies that support HTTP transport:

```bash
# Activate your virtual environment
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate  # Windows

# Update dependencies
pip install --upgrade -r requirements.txt
```

Required versions:
- `fastmcp>=2.11.0` (for authentication support)
- `uvicorn` (for HTTP server)
- `python-jose[cryptography]` (for JWT validation)
- `cryptography` (for cryptographic operations)

### Step 3: Choose Authentication Mode

#### Option A: Static Token (Development/Testing)

Best for: Local development, testing, personal use

Generate a secure token:

```bash
# Linux/Mac:
openssl rand -hex 32

# Or Python:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Save this token securely - you'll need it for configuration.

#### Option B: JWT (Production)

Best for: Production deployments, team access, enterprise use

Requirements:
- JWT provider (Auth0, Okta, AWS Cognito, etc.)
- JWKS URI from your provider
- Issuer and audience configuration

### Step 4: Configure Environment Variables

Create or update your environment configuration:

#### For Static Token Authentication:

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.) or .env file
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=static
export MCP_ADMIN_TOKEN=your_generated_token_here
export MCP_HOST=127.0.0.1  # localhost only
export MCP_PORT=8000
```

#### For JWT Authentication:

```bash
# Add to your shell profile or .env file
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=jwt
export JWT_JWKS_URI=https://your-auth-provider.com/.well-known/jwks.json
export JWT_ISSUER=https://your-auth-provider.com/
export JWT_AUDIENCE=your-api-audience
export JWT_REQUIRED_SCOPES=read:gsc,write:gsc
export MCP_HOST=127.0.0.1
export MCP_PORT=8000
```

### Step 5: Update Claude Desktop Configuration

Update your Claude Desktop configuration file:

**Location:**
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

#### Before (STDIO):

```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/gsc_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/path/to/credentials.json"
      }
    }
  }
}
```

#### After (HTTP with Static Token):

```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/gsc_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/path/to/credentials.json",
        "MCP_TRANSPORT": "http",
        "MCP_AUTH_MODE": "static",
        "MCP_ADMIN_TOKEN": "your_generated_token_here",
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": "8000"
      }
    }
  }
}
```

#### After (HTTP with JWT):

```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/gsc_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/path/to/credentials.json",
        "MCP_TRANSPORT": "http",
        "MCP_AUTH_MODE": "jwt",
        "JWT_JWKS_URI": "https://your-auth-provider.com/.well-known/jwks.json",
        "JWT_ISSUER": "https://your-auth-provider.com/",
        "JWT_AUDIENCE": "your-api-audience",
        "JWT_REQUIRED_SCOPES": "read:gsc,write:gsc",
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": "8000"
      }
    }
  }
}
```

### Step 6: Test the Migration

1. **Restart Claude Desktop** to apply the new configuration

2. **Check server startup:**
   - Look for log messages indicating HTTP transport
   - Verify authentication mode is logged correctly
   - Note the endpoint URL (e.g., `http://127.0.0.1:8000/mcp`)

3. **Test with Claude:**
   - Ask Claude to list your GSC properties
   - Verify you receive results
   - Test a few other tools to ensure everything works

4. **Test with curl (optional):**
   ```bash
   curl -X POST http://127.0.0.1:8000/mcp \
     -H "Authorization: Bearer your_token_here" \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list"}'
   ```

### Step 7: Verify All Tools Work

Test various GSC tools to ensure complete functionality:

- `list_properties` - List all properties
- `get_search_analytics` - Get analytics data
- `inspect_url_enhanced` - Inspect a URL
- `get_sitemaps` - List sitemaps

All existing tools should work identically to STDIO transport.

## Configuration Examples

### Example 1: Local Development

```bash
# Environment variables
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=static
export MCP_ADMIN_TOKEN=dev_token_abc123xyz789
export MCP_HOST=127.0.0.1
export MCP_PORT=8000
export GSC_CREDENTIALS_PATH=/path/to/credentials.json

# Start server
python gsc_server.py
```

### Example 2: Team Access (Same Network)

```bash
# Environment variables
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=static
export MCP_ADMIN_TOKEN=team_shared_token_secure123
export MCP_HOST=0.0.0.0  # Allow network access
export MCP_PORT=8000
export GSC_CREDENTIALS_PATH=/path/to/credentials.json

# Start server
python gsc_server.py
```

**Note:** Share the token securely with team members. They can connect using your machine's IP address.

### Example 3: Production with JWT

```bash
# Environment variables
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=jwt
export JWT_JWKS_URI=https://auth.company.com/.well-known/jwks.json
export JWT_ISSUER=https://auth.company.com/
export JWT_AUDIENCE=https://api.company.com
export JWT_REQUIRED_SCOPES=read:gsc
export MCP_HOST=0.0.0.0
export MCP_PORT=8000
export GSC_CREDENTIALS_PATH=/path/to/credentials.json

# Start server (consider using systemd or supervisor for production)
python gsc_server.py
```

## Breaking Changes

### None

This migration introduces **no breaking changes** to existing functionality:

- All 19+ GSC tools remain unchanged
- Tool interfaces are identical
- Response formats are the same
- STDIO transport remains fully supported

### Backward Compatibility

You can continue using STDIO transport indefinitely:

```bash
# Explicitly use STDIO (default if not specified)
python gsc_server.py --transport stdio

# Or set environment variable
export MCP_TRANSPORT=stdio
python gsc_server.py
```

## Rollback Procedure

If you encounter issues with HTTP transport, you can easily rollback to STDIO:

### Quick Rollback

1. **Update Claude Desktop configuration** to remove HTTP-specific variables:

```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/gsc_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/path/to/credentials.json",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

2. **Restart Claude Desktop**

3. **Verify STDIO works:**
   - Test a GSC tool
   - Confirm you receive results

### Alternative: Use CLI Argument

You can also force STDIO mode without changing configuration:

```bash
python gsc_server.py --transport stdio
```

### Troubleshooting Rollback

If rollback doesn't work:

1. **Check logs** for error messages
2. **Verify credentials** are still valid
3. **Test manually:**
   ```bash
   python gsc_server.py --transport stdio
   ```
4. **Reinstall dependencies** if needed:
   ```bash
   pip install --force-reinstall -r requirements.txt
   ```

## Common Migration Issues

### Issue 1: Authentication Failures

**Symptom:** `401 Unauthorized` errors

**Solutions:**
- Verify `MCP_ADMIN_TOKEN` is set correctly
- Check token matches in both server and client
- Ensure no extra spaces or quotes in token
- For JWT: Verify all three required variables are set

### Issue 2: Server Won't Start

**Symptom:** Server exits immediately or shows error

**Solutions:**
- Check for missing environment variables
- Verify port is not already in use
- Review error messages in logs
- Enable debug mode: `export MCP_DEBUG=true`

### Issue 3: Claude Can't Connect

**Symptom:** Claude shows connection errors

**Solutions:**
- Verify server is running (check logs)
- Confirm host/port in Claude config matches server
- Restart Claude Desktop after config changes
- Check firewall isn't blocking the port

### Issue 4: Tools Don't Work

**Symptom:** Tools fail or return errors

**Solutions:**
- Verify GSC credentials are still valid
- Check all existing environment variables are preserved
- Test with STDIO to isolate transport vs GSC issues
- Review server logs for specific errors

## Security Considerations

### Development vs Production

**Development:**
- Static tokens are acceptable
- Localhost binding (`127.0.0.1`) is sufficient
- HTTP (not HTTPS) is acceptable for local testing

**Production:**
- Always use JWT authentication
- Always use HTTPS (reverse proxy with SSL/TLS)
- Bind to `0.0.0.0` only if remote access is required
- Implement rate limiting and monitoring
- Rotate tokens regularly

### Token Security

1. **Never commit tokens to version control**
   - Add `.env` to `.gitignore`
   - Use secret management systems in production

2. **Generate strong tokens**
   - Minimum 32 characters
   - Use cryptographically secure random generation
   - Avoid predictable patterns

3. **Rotate tokens regularly**
   - Every 90 days recommended
   - Immediately if compromised
   - Document rotation procedures

4. **Secure token transmission**
   - Always use HTTPS in production
   - Never send tokens in URLs or logs
   - Use secure channels for sharing

## Getting Help

If you encounter issues during migration:

1. **Check logs** with debug mode enabled:
   ```bash
   export MCP_DEBUG=true
   python gsc_server.py
   ```

2. **Review documentation:**
   - README.md for detailed configuration
   - This MIGRATION.md for migration-specific guidance

3. **Test incrementally:**
   - Start with STDIO to verify base functionality
   - Add HTTP transport without authentication
   - Add authentication last

4. **Rollback if needed:**
   - Follow the rollback procedure above
   - Report issues with detailed logs

## Summary

This migration adds powerful new capabilities while maintaining full backward compatibility:

- ✅ HTTP transport enables remote access
- ✅ Authentication secures your server
- ✅ All existing tools work identically
- ✅ STDIO transport remains fully supported
- ✅ Easy rollback if needed

Take your time with the migration, test thoroughly, and don't hesitate to rollback if you encounter issues.
