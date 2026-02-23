# Google Search Console MCP server for SEOs

A tool that connects [Google Search Console](https://search.google.com/search-console/about) (GSC) with Claude AI, allowing you to analyze your SEO data through natural language conversations. This integration gives you access to property information, search analytics, URL inspection, and sitemap management—all through simple chat with Claude.

---

## What Can This Tool Do For SEO Professionals?

1. **Property Management**  
   - See all your GSC properties in one place
   - Get verification details and basic site information
   - Add new properties to your account
   - Remove properties from your account

2. **Search Analytics & Reporting**  
   - Discover which search queries bring visitors to your site
   - Track impressions, clicks, and click-through rates
   - Analyze performance trends over time
   - Compare different time periods to spot changes
   - **Visualize your data** with charts and graphs created by Claude

3. **URL Inspection & Indexing**  
   - Check if specific pages have indexing problems
   - See when Google last crawled your pages
   - Inspect multiple URLs at once to identify patterns
   - Get actionable insights on how to improve indexing

4. **Sitemap Management**  
   - View all your sitemaps and their status
   - Submit new sitemaps directly through Claude
   - Check for errors or warnings in your sitemaps
   - Monitor sitemap processing status

---

## Available Tools

Here's what you can ask Claude to do once you've set up this integration:

| **What You Can Ask For**        | **What It Does**                                            | **What You'll Need to Provide**                                 |
|---------------------------------|-------------------------------------------------------------|----------------------------------------------------------------|
| `list_properties`               | Shows all your GSC properties                               | Nothing - just ask!                                             |
| `get_site_details`              | Shows details about a specific site                         | Your website URL                                                |
| `add_site`                      | Adds a new site to your GSC properties                      | Your website URL                                                |
| `delete_site`                   | Removes a site from your GSC properties                     | Your website URL                                                |
| `get_search_analytics`          | Shows top queries and pages with metrics                    | Your website URL and time period                                |
| `get_performance_overview`      | Gives a summary of site performance                         | Your website URL and time period                                |
| `check_indexing_issues`         | Checks if pages have indexing problems                      | Your website URL and list of pages to check                     |
| `inspect_url_enhanced`          | Detailed inspection of a specific URL                       | Your website URL and the page to inspect                        |
| `get_sitemaps`                  | Lists all sitemaps for your site                            | Your website URL                                                |
| `submit_sitemap`                | Submits a new sitemap to Google                             | Your website URL and sitemap URL                                |

*For a complete list of all 19 available tools and their detailed descriptions, ask Claude to "list tools" after setup.*

---

## Getting Started (No Coding Experience Required!)

### 1. Choose Your Connection Method

This server supports two connection methods:

1. **STDIO Transport (Local Only)** - Traditional method for local Claude Desktop connections
2. **HTTP Transport (Network Access)** - New method enabling remote access with authentication

For most users connecting Claude Desktop locally, continue with the STDIO setup below. For remote access or production deployments, see the [HTTP Transport Configuration](#http-transport-configuration) section.

### 2. Set Up Google Search Console API Access

Before using this tool, you'll need to create API credentials that allow Claude to access your GSC data:

#### Authentication Options

The tool supports two authentication methods:

##### 1. OAuth Authentication (Recommended)

This method allows you to authenticate with your own Google account, which is often more convenient than using a service account. It will have access to the same resources you normally do.

Set `GSC_SKIP_OAUTH` to "true", "1", or "yes" to skip OAuth authentication and use only service account authentication

###### Setup Instructions:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a Google Cloud account if you don't have one
2. Create a new project or select an existing one
3. [Enable the Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com) for your project
4. [Add scope](https://console.cloud.google.com/auth/scopes) `https://www.googleapis.com/auth/webmasters` to your project
5. Go to the ["Credentials" page](https://console.cloud.google.com/apis/credentials)
6. Click "Create Credentials" and select "OAuth client ID"
7. Configure the OAuth consent screen
8. For application type, select "Desktop app"
9. Give your OAuth client a name and click "Create"
10. Download the client secrets JSON file (it will be named something like `client_secrets.json`)
11. Place this file in the same directory as the script or set the `GSC_OAUTH_CLIENT_SECRETS_FILE` environment variable to point to its location

When you run the tool for the first time with OAuth authentication, it will open a browser window asking you to sign in to your Google account and authorize the application. After authorization, the tool will save the token for future use.

##### 2. Service Account Authentication

This method uses a service account, which is useful for automated scripts or when you don't want to use your personal Google account. This requires adding the service account as a user in Google Search Console.

###### Setup Instructions:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a Google Cloud account if you don't have one
2. Create a new project or select an existing one
3. [Enable the Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com) for your project
4. Go to the ["Credentials" page](https://console.cloud.google.com/apis/credentials)
5. Click "Create Credentials" and select "Service Account"
6. Fill in the service account details and click "Create"
7. Click on the newly created service account
8. Go to the "Keys" tab and click "Add Key" > "Create new key"
9. Select JSON format and click "Create"
10. Download the key file and save it as `service_account_credentials.json` in the same directory as the script or set the `GSC_CREDENTIALS_PATH` environment variable to point to its location
11. Add your service account email address to appropriate Search Console properties

**🎬 Watch this beginner-friendly tutorial on Youtube:**

<div align="center">
  <a href="https://youtu.be/PCWsK5BgSd0">
    <img src="https://i.ytimg.com/vi/PCWsK5BgSd0/maxresdefault.jpg" alt="Google Search Console API Setup Tutorial" width="600" style="margin: 20px 0; border-radius: 8px;">
  </a>
</div>

*Click the image above to watch the step-by-step video tutorial*

### 2. Install Required Software

You'll need to install these tools on your computer:

- [Python](https://www.python.org/downloads/) (version 3.11 or newer) - This runs the connection between GSC and Claude
- [Node.js](https://nodejs.org/en) - Required for running the MCP inspector and certain MCP components
- [Claude Desktop](https://claude.ai/download) - The AI assistant you'll chat with

Make sure both Python and Node.js are properly installed and available in your system path before proceeding.

### 3. Download the Google Search Console MCP 

You need to download this tool to your computer. The easiest way is:

1. Click the green "Code" button at the top of this page
2. Select "Download ZIP"
3. Unzip the downloaded file to a location you can easily find (like your Documents folder)

Alternatively, if you're familiar with Git:

```bash
git clone https://github.com/AminForou/mcp-gsc.git
```

### 4. Install Required Components

Open your computer's Terminal (Mac) or Command Prompt (Windows):

1. Navigate to the folder where you unzipped the files:
   ```bash
   # Example (replace with your actual path):
   cd ~/Documents/mcp-gsc-main
   ```

2. Create a virtual environment (this keeps the project dependencies isolated):
   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:
   ```bash
   # On Mac/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   **If you get "pip not found" error:**
   ```bash
   # First ensure pip is installed and updated:
   python3 -m ensurepip --upgrade
   python3 -m pip install --upgrade pip
   
   # Then try installing the requirements again:
   python3 -m pip install -r requirements.txt
   
   ```

When you see `(.venv)` at the beginning of your command prompt, it means the virtual environment is active and the dependencies will be installed there without affecting your system Python installation.

### 5. Connect Claude to Google Search Console

1. Download and install [Claude Desktop](https://claude.ai/download) if you haven't already
2. Make sure you have your Google service account credentials file saved somewhere on your computer
3. Open your computer's Terminal (Mac) or Command Prompt (Windows) and type:

```bash
   # For Mac users:
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # For Windows users:
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```

4. Add the following configuration text (this tells Claude how to connect to GSC):

#### OAuth authentication (using your own account)

   ```json
   {
     "mcpServers": {
       "gscServer": {
         "command": "/FULL/PATH/TO/-main/.venv/bin/python",
         "args": ["/FULL/PATH/TO/mcp-gsc-main/gsc_server.py"],
         "env": {
           "GSC_OAUTH_CLIENT_SECRETS_FILE": "/FULL/PATH/TO/client_secrets.json"
         }
       }
     }
   }
   ```

#### Service account authentication

   ```json
   {
     "mcpServers": {
       "gscServer": {
         "command": "/FULL/PATH/TO/-main/.venv/bin/python",
         "args": ["/FULL/PATH/TO/mcp-gsc-main/gsc_server.py"],
         "env": {
           "GSC_CREDENTIALS_PATH": "/FULL/PATH/TO/service_account_credentials.json",
           "GSC_SKIP_OAUTH": "true"
         }
       }
     }
   }
   ```

   **Important:** Replace all paths with the actual locations on your computer:
   
   - The first path should point to the Python executable inside your virtual environment
   - The second path should point to the `gsc_server.py` file inside the folder you unzipped
   - The third path should point to your Google service account credentials JSON file
   
   Examples:
   - Mac: 
     - Python path: `/Users/yourname/Documents/mcp-gsc/.venv/bin/python`
     - Script path: `/Users/yourname/Documents/mcp-gsc/gsc_server.py`
   - Windows: 
     - Python path: `C:\\Users\\yourname\\Documents\\mcp-gsc\\.venv\\Scripts\\python.exe`
     - Script path: `C:\\Users\\yourname\\Documents\\mcp-gsc\\gsc_server.py`

5. Save the file:
   - Mac: Press Ctrl+O, then Enter, then Ctrl+X to exit
   - Windows: Click File > Save, then close Notepad

6. Restart Claude Desktop
7. When Claude opens, you should now see GSC tools available in the tools section

### 6. Start Analyzing Your SEO Data!

Now you can ask Claude questions about your GSC data! Claude can not only retrieve the data but also analyze it, explain trends, and create visualizations to help you understand your SEO performance better.

Here are some powerful prompts you can use with each tool:

| **Tool Name**                   | **Sample Prompt**                                                                                |
|---------------------------------|--------------------------------------------------------------------------------------------------|
| `list_properties`               | "List all my GSC properties and tell me which ones have the most pages indexed."                 |
| `get_site_details`              | "Analyze the verification status of mywebsite.com and explain what the ownership details mean."  |
| `add_site`                      | "Add my new website https://mywebsite.com to Search Console and verify its status."              |
| `delete_site`                   | "Remove the old test site https://test.mywebsite.com from Search Console."                       |
| `get_search_analytics`          | "Show me the top 20 search queries for mywebsite.com in the last 30 days, highlight any with CTR below 2%, and suggest title improvements." |
| `get_performance_overview`      | "Create a visual performance overview of mywebsite.com for the last 28 days, identify any unusual drops or spikes, and explain possible causes." |
| `check_indexing_issues`         | "Check these important pages for indexing issues and prioritize which ones need immediate attention: mywebsite.com/product, mywebsite.com/services, mywebsite.com/about" |
| `inspect_url_enhanced`          | "Do a comprehensive inspection of mywebsite.com/landing-page and give me actionable recommendations to improve its indexing status." |
| `batch_url_inspection`          | "Inspect my top 5 product pages, identify common crawling or indexing patterns, and suggest technical SEO improvements." |
| `get_sitemaps`                  | "List all sitemaps for mywebsite.com, identify any with errors, and recommend next steps." |
| `list_sitemaps_enhanced`        | "Analyze all my sitemaps for mywebsite.com, focusing on error patterns, and create a prioritized action plan." |
| `submit_sitemap`                | "Submit my new product sitemap at https://mywebsite.com/product-sitemap.xml and explain how long it typically takes for Google to process it." |
| `get_sitemap_details`           | "Check the status of my main sitemap at mywebsite.com/sitemap.xml and explain what the warnings mean for my SEO." |
| `get_search_by_page_query`      | "What search terms are driving traffic to my blog post at mywebsite.com/blog/post-title? Identify opportunities to optimize for related keywords." |
| `compare_search_periods`        | "Compare my site's performance between January and February. What queries improved the most, which declined, and what might explain these changes?" |
| `get_advanced_search_analytics` | "Analyze my mobile search performance for queries with high impressions but positions below 10, and suggest content improvements to help them rank better." |

You can also ask Claude to combine multiple tools and analyze the results. For example:

- "Find my top 20 landing pages by traffic, check their indexing status, and create a report highlighting any pages with both high traffic and indexing issues."

- "Analyze my site's performance trend over the last 90 days, identify my fastest-growing queries, and check if the corresponding landing pages have any technical issues."

- "Compare my desktop vs. mobile search performance, visualize the differences with charts, and recommend specific pages that need mobile optimization based on performance gaps."

- "Identify queries where I'm ranking on page 2 (positions 11-20) that have high impressions but low CTR, then inspect the corresponding URLs and suggest title and meta description improvements."

Claude will use the GSC tools to fetch the data, present it in an easy-to-understand format, create visualizations when helpful, and provide actionable insights based on the results.

---

## HTTP Transport Configuration

The server now supports HTTP transport, enabling remote access with secure token-based authentication. This is ideal for production deployments, team access, or connecting from remote clients.

### Overview

HTTP transport provides:
- Remote network access to the MCP server
- Secure authentication with Bearer tokens
- Two authentication modes: Static tokens (development) and JWT (production)
- RESTful API endpoint at `/mcp`

### Environment Variables

Configure the server using these environment variables:

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `MCP_HOST` | string | No | `0.0.0.0` | Server bind address (use `127.0.0.1` for localhost only) |
| `MCP_PORT` | integer | No | `8000` | Server listen port (1-65535) |
| `MCP_TRANSPORT` | string | No | `http` | Transport mode: `http` or `stdio` |
| `MCP_AUTH_MODE` | string | No | `static` | Authentication mode: `static` or `jwt` |
| `MCP_ADMIN_TOKEN` | string | Yes (static) | - | Admin token for static authentication |
| `JWT_JWKS_URI` | string | Yes (jwt) | - | JWKS endpoint URL for JWT validation |
| `JWT_ISSUER` | string | Yes (jwt) | - | Expected JWT issuer |
| `JWT_AUDIENCE` | string | Yes (jwt) | - | Expected JWT audience |
| `JWT_REQUIRED_SCOPES` | string | No | - | Comma-separated required scopes for JWT |
| `MCP_DEBUG` | string | No | `false` | Enable debug logging (`true`, `1`, or `yes`) |

### Authentication Modes

#### Static Token Authentication (Development)

Simple token-based authentication suitable for development and testing. The server validates requests against a predefined token.

**Setup:**

1. Generate a secure token:
   ```bash
   # On Linux/Mac:
   openssl rand -hex 32
   
   # Or use Python:
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Set environment variables:
   ```bash
   export MCP_TRANSPORT=http
   export MCP_AUTH_MODE=static
   export MCP_ADMIN_TOKEN=your_generated_token_here
   export MCP_HOST=0.0.0.0
   export MCP_PORT=8000
   ```

3. Start the server:
   ```bash
   python gsc_server.py
   ```

4. Test with curl:
   ```bash
   curl -X POST http://localhost:8000/mcp \
     -H "Authorization: Bearer your_generated_token_here" \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list"}'
   ```

**⚠️ Security Warning:** Static tokens are suitable for development only. Do not use in production environments. Always use HTTPS in production to prevent token interception.

#### JWT Authentication (Production)

Production-ready authentication using JSON Web Tokens with cryptographic validation. Integrates with external identity providers (Auth0, Okta, AWS Cognito, etc.).

**Setup:**

1. Configure your JWT provider (Auth0, Okta, etc.)

2. Set environment variables:
   ```bash
   export MCP_TRANSPORT=http
   export MCP_AUTH_MODE=jwt
   export JWT_JWKS_URI=https://your-auth-provider.com/.well-known/jwks.json
   export JWT_ISSUER=https://your-auth-provider.com/
   export JWT_AUDIENCE=your-api-audience
   export JWT_REQUIRED_SCOPES=read:gsc,write:gsc
   export MCP_HOST=0.0.0.0
   export MCP_PORT=8000
   ```

3. Start the server:
   ```bash
   python gsc_server.py
   ```

4. Test with a valid JWT:
   ```bash
   curl -X POST http://localhost:8000/mcp \
     -H "Authorization: Bearer your_jwt_token_here" \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list"}'
   ```

### Command-Line Arguments

Override environment variables with CLI arguments:

```bash
# Start with custom host and port
python gsc_server.py --host 127.0.0.1 --port 9000

# Start with JWT authentication
python gsc_server.py --auth-mode jwt

# Start with STDIO transport (backward compatibility)
python gsc_server.py --transport stdio

# View all options
python gsc_server.py --help
```

**Precedence:** CLI arguments > Environment variables > Defaults

### Example Configurations

#### Development Setup (Local Network)

```bash
# .env file or export these
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=static
export MCP_ADMIN_TOKEN=dev_token_12345
export MCP_HOST=127.0.0.1
export MCP_PORT=8000

python gsc_server.py
```

#### Production Setup (JWT with Auth0)

```bash
# .env file or export these
export MCP_TRANSPORT=http
export MCP_AUTH_MODE=jwt
export JWT_JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
export JWT_ISSUER=https://your-domain.auth0.com/
export JWT_AUDIENCE=https://api.your-domain.com
export JWT_REQUIRED_SCOPES=read:gsc
export MCP_HOST=0.0.0.0
export MCP_PORT=8000

python gsc_server.py
```

### MCP Endpoint

The server exposes the MCP protocol at:

```
POST http://<host>:<port>/mcp
```

All MCP requests must include the `Authorization: Bearer <token>` header.

### Security Best Practices

1. **Use HTTPS in Production**
   - Never expose HTTP servers directly to the internet
   - Use a reverse proxy (nginx, Apache) with SSL/TLS certificates
   - Consider using Let's Encrypt for free SSL certificates

2. **Token Management**
   - Generate strong, random tokens (minimum 32 characters)
   - Rotate tokens regularly (every 90 days recommended)
   - Never commit tokens to version control
   - Use environment variables or secure secret management systems

3. **Network Security**
   - Bind to `127.0.0.1` for localhost-only access
   - Use `0.0.0.0` only when remote access is required
   - Configure firewall rules to restrict access
   - Consider using VPN for remote access

4. **Authentication Mode Selection**
   - Development: Static tokens are acceptable
   - Production: Always use JWT authentication
   - Never use static tokens in production environments

5. **Logging and Monitoring**
   - Enable debug logging during development: `export MCP_DEBUG=true`
   - Monitor authentication failures
   - Review logs regularly for suspicious activity
   - Tokens are automatically redacted from logs

### Troubleshooting

#### Authentication Errors

**Problem:** `401 Unauthorized` response

**Solutions:**
- Verify the token is correct and matches `MCP_ADMIN_TOKEN`
- Check that the `Authorization` header is properly formatted: `Bearer <token>`
- For JWT: Verify the token hasn't expired
- For JWT: Confirm JWKS URI, issuer, and audience are correct
- Check server logs for specific error messages

#### Server Binding Errors

**Problem:** `Address already in use`

**Solutions:**
- Another process is using the port. Try a different port:
  ```bash
  python gsc_server.py --port 8001
  ```
- Find and stop the conflicting process:
  ```bash
  # Linux/Mac:
  lsof -i :8000
  kill <PID>
  
  # Windows:
  netstat -ano | findstr :8000
  taskkill /PID <PID> /F
  ```

**Problem:** `Permission denied`

**Solutions:**
- Ports below 1024 require root/administrator privileges
- Use a port >= 1024 (recommended: 8000-9000)
- Or run with elevated privileges (not recommended)

#### Configuration Errors

**Problem:** `MCP_ADMIN_TOKEN environment variable is required`

**Solution:**
- Set the required environment variable:
  ```bash
  export MCP_ADMIN_TOKEN=your_token_here
  ```

**Problem:** `JWT authentication requires JWT_JWKS_URI, JWT_ISSUER, and JWT_AUDIENCE`

**Solution:**
- Ensure all three JWT variables are set:
  ```bash
  export JWT_JWKS_URI=https://...
  export JWT_ISSUER=https://...
  export JWT_AUDIENCE=your-audience
  ```

#### Connection Errors

**Problem:** Cannot connect to server

**Solutions:**
- Verify server is running: Check for startup log messages
- Check host/port configuration: Ensure client uses correct endpoint
- Test with curl to isolate client vs server issues
- Check firewall rules: Ensure port is not blocked
- For remote access: Verify `MCP_HOST=0.0.0.0` (not `127.0.0.1`)

#### Debug Mode

Enable detailed logging for troubleshooting:

```bash
export MCP_DEBUG=true
python gsc_server.py
```

This provides:
- Detailed request/response logging
- Authentication flow information
- Configuration validation details
- Error stack traces

**Note:** Debug mode may log sensitive information. Disable in production.

---

## Data Visualization Capabilities

Claude can help you visualize your GSC data in various ways:

- **Trend Charts**: See how metrics change over time
- **Comparison Graphs**: Compare different time periods or dimensions
- **Performance Distributions**: Understand how your content performs across positions
- **Correlation Analysis**: Identify relationships between different metrics
- **Heatmaps**: Visualize complex datasets with color-coded representations

Simply ask Claude to "visualize" or "create a chart" when analyzing your data, and it will generate appropriate visualizations to help you understand the information better.

---

## Troubleshooting

### Python Command Not Found

On macOS, the default Python command is often `python3` rather than `python`, which can cause issues with some applications including Node.js integrations.

If you encounter errors related to Python not being found, you can create an alias:

1. Create a Python alias (one-time setup):
   ```bash
   # For macOS users:
   sudo ln -s $(which python3) /usr/local/bin/python
   
   # If that doesn't work, try finding your Python installation:
   sudo ln -s /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /usr/local/bin/python
   ```

2. Verify the alias works:
   ```bash
   python --version
   ```

This creates a symbolic link so that when applications call `python`, they'll actually use your `python3` installation.

### Claude Configuration Issues

If you're having trouble connecting:

1. Make sure all file paths in your configuration are correct and use the full path
2. Check that your service account has access to your GSC properties
3. Restart Claude Desktop after making any changes
4. Look for error messages in Claude's response when you try to use a tool
5. Ensure your virtual environment is activated when running the server manually

### Other Unexpected Issues

If you encounter any other unexpected issues during installation or usage:

1. Copy the exact error message you're receiving
2. Use ChatGPT or Claude and explain your problem in detail, including:
   - What you were trying to do
   - The exact error message
   - Your operating system
   - Any steps you've already tried
3. AI assistants can often help diagnose and resolve technical issues by suggesting specific solutions for your situation

Remember that most issues have been encountered by others before, and there's usually a straightforward solution available.

---

## Contributing

Found a bug or have an idea for improvement? We welcome your input! Open an issue or submit a pull request on GitHub.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
