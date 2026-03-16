"""
Google Search Console MCP Server

This module provides a Model Context Protocol (MCP) server for Google Search Console,
enabling AI assistants like Claude to interact with GSC data through natural language.

The server supports two transport modes:
- STDIO: Local-only communication (original method)
- HTTP: Network-based communication with token authentication (new)

Authentication modes for HTTP transport:
- Static Token: Simple token-based auth for development
- JWT: Production-ready authentication with cryptographic validation

All GSC tools remain unchanged regardless of transport mode, ensuring backward compatibility.

Security Considerations:
- Tokens are never logged (filtered by logging_config.py)
- HTTPS is recommended for production HTTP transport
- JWT validation includes issuer, audience, and signature verification
- Static tokens should only be used in development environments

Usage:
    # STDIO mode (default, backward compatible)
    python gsc_server.py --transport stdio
    
    # HTTP mode with static token
    export MCP_ADMIN_TOKEN=your_token
    python gsc_server.py --transport http --auth-mode static
    
    # HTTP mode with JWT
    export JWT_JWKS_URI=https://...
    export JWT_ISSUER=https://...
    export JWT_AUDIENCE=your-audience
    python gsc_server.py --transport http --auth-mode jwt

For detailed configuration, see README.md and MIGRATION.md
"""

from typing import Any, Dict, List, Optional
import os
import sys
import json
from datetime import datetime, timedelta, timezone

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse
import uuid
from vibeblocks.utils.execution import execute_flow
from states import (
    ListPropertiesState, SiteDetailsState, SearchAnalyticsState,
    AdvancedSearchAnalyticsState, CompareSearchPeriodsState,
    InspectUrlEnhancedState, BatchUrlInspectionState, CheckIndexingIssuesState,
    PerformanceOverviewState, SearchByPageQueryState, SiteMutationState,
    SitemapMutationState, SitemapsListState, SitemapDetailsState
)
from exceptions import TransientGSCError, PermanentGSCError
from flows import gsc_read_workflow, gsc_site_mutation_workflow, gsc_sitemap_mutation_workflow


# MCP
from fastmcp import FastMCP

mcp = FastMCP("gsc-server")

# Path to your service account JSON or user credentials JSON
# First check if GSC_CREDENTIALS_PATH environment variable is set
# Then try looking in the script directory and current working directory as fallbacks
GSC_CREDENTIALS_PATH = os.environ.get("GSC_CREDENTIALS_PATH")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_CREDENTIAL_PATHS = [
    GSC_CREDENTIALS_PATH,  # First try the environment variable if set
    os.path.join(SCRIPT_DIR, "service_account_credentials.json"),
    os.path.join(os.getcwd(), "service_account_credentials.json"),
    # Add any other potential paths here
]

# OAuth client secrets file path
OAUTH_CLIENT_SECRETS_FILE = os.environ.get("GSC_OAUTH_CLIENT_SECRETS_FILE")
if not OAUTH_CLIENT_SECRETS_FILE:
    OAUTH_CLIENT_SECRETS_FILE = os.path.join(SCRIPT_DIR, "client_secrets.json")

# Token file path for storing OAuth tokens
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.json")

# Environment variable to skip OAuth authentication
SKIP_OAUTH = os.environ.get("GSC_SKIP_OAUTH", "").lower() in ("true", "1", "yes")

SCOPES = ["https://www.googleapis.com/auth/webmasters"]

# Runtime settings (for HTTP/server deployment)
DEFAULT_HTTP_HOST = os.environ.get("FASTMCP_HOST", "127.0.0.1")
DEFAULT_HTTP_PORT = os.environ.get("FASTMCP_PORT", "8011")
DEFAULT_HTTP_PATH = (
    os.environ.get("FASTMCP_HTTP_PATH")
    or os.environ.get("FASTMCP_STREAMABLE_HTTP_PATH")
    or "/"
)

def get_gsc_service():
    """
    Returns an authorized Search Console service object.
    First tries OAuth authentication, then falls back to service account.
    """
    # Try OAuth authentication first if not skipped
    if not SKIP_OAUTH:
        try:
            return get_gsc_service_oauth()
        except Exception as e:
            # If OAuth fails, try service account
            print(f"OAuth authentication failed: {str(e)}")
            pass
    
    # Try service account authentication
    for cred_path in POSSIBLE_CREDENTIAL_PATHS:
        if cred_path and os.path.exists(cred_path):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    cred_path, scopes=SCOPES
                )
                return build("searchconsole", "v1", credentials=creds)
            except Exception as e:
                continue  # Try the next path if this one fails
    
    # If we get here, none of the authentication methods worked
    raise FileNotFoundError(
        f"Authentication failed. Please either:\n"
        f"1. Set up OAuth by placing a client_secrets.json file in the script directory, or\n"
        f"2. Set the GSC_CREDENTIALS_PATH environment variable or place a service account credentials file in one of these locations: "
        f"{', '.join([p for p in POSSIBLE_CREDENTIAL_PATHS[1:] if p])}"
    )

def get_gsc_service_oauth():
    """
    Returns an authorized Search Console service object using OAuth.
    """
    creds = None
    
    # Check if token file exists
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            # If token file is corrupted, delete it
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            creds = None
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                # If refresh fails, delete the bad token and trigger new OAuth flow
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                # Fall through to the OAuth flow below
                creds = None
        
        # Start new OAuth flow if we don't have valid credentials
        if not creds or not creds.valid:
            # Check if client secrets file exists
            if not os.path.exists(OAUTH_CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"OAuth client secrets file not found. Please place a client_secrets.json file in the script directory "
                    f"or set the GSC_OAUTH_CLIENT_SECRETS_FILE environment variable."
                )
            
            # Start OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for future use
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
    
    # Build and return the service
    return build("searchconsole", "v1", credentials=creds)


@mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def health_check(_request: StarletteRequest):
    """
    Simple health endpoint for reverse proxy and service monitoring.
    """
    return JSONResponse(
        {
            "status": "ok",
            "service": "mcp-gsc",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

@mcp.tool()
async def list_properties() -> str:
    """
    Retrieves and returns the user's Search Console properties.
    """
    state = ListPropertiesState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat()
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)

    if outcome.status == "FAILED" or not state.result:
        for err in state.errors:
            if "FileNotFoundError" in str(err):
                return (
                    "Error: Service account credentials file not found.\n\n"
                    "To access Google Search Console, please:\n"
                    "1. Create a service account in Google Cloud Console\n"
                    "2. Download the JSON credentials file\n"
                    "3. Save it as 'service_account_credentials.json' in the same directory as this script\n"
                    "4. Share your GSC properties with the service account email"
                )
        if hasattr(outcome, 'exception') and isinstance(outcome.exception, FileNotFoundError):
             return (
                "Error: Service account credentials file not found.\n\n"
                "To access Google Search Console, please:\n"
                "1. Create a service account in Google Cloud Console\n"
                "2. Download the JSON credentials file\n"
                "3. Save it as 'service_account_credentials.json' in the same directory as this script\n"
                "4. Share your GSC properties with the service account email"
             )
        return f"Error retrieving properties: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"

    site_list = state.result
    sites = site_list.get("siteEntry", [])

    if not sites:
        return "No Search Console properties found."

    lines = []
    for site in sites:
        site_url = site.get("siteUrl", "Unknown")
        permission = site.get("permissionLevel", "Unknown permission")
        lines.append(f"- {site_url} ({permission})")

    return "\n".join(lines)
@mcp.tool()
async def add_site(site_url: str) -> str:
    """
    Add a site to your Search Console properties.
    
    Args:
        site_url: The URL of the site to add (must be exact match e.g. https://example.com, or https://www.example.com, or https://subdomain.example.com/path/, for domain properties use format: sc-domain:example.com)
    """
    state = SiteMutationState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        request_type="add_site"
    )
    outcome = await execute_flow(gsc_site_mutation_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        exc = getattr(outcome, 'exception', None)
        if exc and isinstance(exc, PermanentGSCError):
            err_str = str(exc)
            if "409" in err_str:
                return f"Site {site_url} is already added to Search Console."
            elif "403" in err_str:
                 return f"Error: Permission denied (403). Ensure you have permissions or verify ownership. Details: {err_str}"
            elif "400" in err_str:
                 return f"Error: Bad request (400). Invalid URL format. Details: {err_str}"
            elif "401" in err_str:
                 return "Error: Unauthorized. Please check your credentials."
        elif exc and isinstance(exc, TransientGSCError):
             return f"Error: Transient API error. Please try again later. Details: {str(exc)}"

        return f"Error adding site: {exc if exc else 'Unknown error'}"
        
    response = state.result
    result_lines = [f"Site {site_url} has been added to Search Console."]

    if "permissionLevel" in response:
        result_lines.append(f"Permission level: {response['permissionLevel']}")

    return "\n".join(result_lines)
@mcp.tool()
async def delete_site(site_url: str) -> str:
    """
    Remove a site from your Search Console properties.
    
    Args:
        site_url: The URL of the site to remove (must be exact match e.g. https://example.com, or https://www.example.com, or https://subdomain.example.com/path/, for domain properties use format: sc-domain:example.com)
    """
    state = SiteMutationState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        request_type="delete_site"
    )
    outcome = await execute_flow(gsc_site_mutation_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        exc = getattr(outcome, 'exception', None)
        if exc and isinstance(exc, PermanentGSCError):
            err_str = str(exc)
            if "404" in err_str:
                return f"Site {site_url} was not found in Search Console."
            elif "403" in err_str:
                 return f"Error: Permission denied (403). Details: {err_str}"
            elif "400" in err_str:
                 return f"Error: Bad request (400). Details: {err_str}"
            elif "401" in err_str:
                 return "Error: Unauthorized. Please check your credentials."
        elif exc and isinstance(exc, TransientGSCError):
             return f"Error: Transient API error. Please try again later. Details: {str(exc)}"

        return f"Error removing site: {exc if exc else 'Unknown error'}"
        
    return f"Site {site_url} has been removed from Search Console."
@mcp.tool()
async def get_search_analytics(site_url: str, days: int = 28, dimensions: str = "query") -> str:
    """
    Get search analytics data for a specific property.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        days: Number of days to look back (default: 28)
        dimensions: Dimensions to group by (default: query). Options: query, page, device, country, date
                   You can provide multiple dimensions separated by comma (e.g., "query,page")
    """
    dimension_list = [d.strip() for d in dimensions.split(",")]
    state = SearchAnalyticsState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        days=days,
        dimensions=dimension_list
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving search analytics: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    response = state.result
    if not response.get("rows"):
        return f"No search analytics data found for {site_url} in the last {days} days."

    result_lines = [f"Search analytics for {site_url} (last {days} days):"]
    result_lines.append("\n" + "-" * 80 + "\n")

    header = []
    for dim in dimension_list:
        header.append(dim.capitalize())
    header.extend(["Clicks", "Impressions", "CTR", "Position"])
    result_lines.append(" | ".join(header))
    result_lines.append("-" * 80)

    for row in response.get("rows", []):
        data = []
        for dim_value in row.get("keys", []):
            data.append(dim_value[:100])
        
        data.append(str(row.get("clicks", 0)))
        data.append(str(row.get("impressions", 0)))
        data.append(f"{row.get('ctr', 0) * 100:.2f}%")
        data.append(f"{row.get('position', 0):.1f}")
        
        result_lines.append(" | ".join(data))

    return "\n".join(result_lines)
@mcp.tool()
async def get_site_details(site_url: str) -> str:
    """
    Get detailed information about a specific Search Console property.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
    """
    state = SiteDetailsState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving site details: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    site_info = state.result
    result_lines = [f"Site details for {site_url}:"]
    result_lines.append("-" * 50)

    result_lines.append(f"Permission level: {site_info.get('permissionLevel', 'Unknown')}")

    if "siteVerificationInfo" in site_info:
        verify_info = site_info["siteVerificationInfo"]
        result_lines.append(f"Verification state: {verify_info.get('verificationState', 'Unknown')}")
        
        if "verifiedUser" in verify_info:
            result_lines.append(f"Verified by: {verify_info['verifiedUser']}")
            
        if "verificationMethod" in verify_info:
            result_lines.append(f"Verification method: {verify_info['verificationMethod']}")

    if "ownershipInfo" in site_info:
        owner_info = site_info["ownershipInfo"]
        result_lines.append("\nOwnership Information:")
        result_lines.append(f"Owner: {owner_info.get('owner', 'Unknown')}")
        
        if "verificationMethod" in owner_info:
            result_lines.append(f"Ownership verification: {owner_info['verificationMethod']}")

    return "\n".join(result_lines)
@mcp.tool()
async def get_sitemaps(site_url: str) -> str:
    """
    List all sitemaps for a specific Search Console property.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
    """
    state = SitemapsListState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        request_type="get_sitemaps"
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving sitemaps: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    sitemaps = state.result
    if not sitemaps.get("sitemap"):
        return f"No sitemaps found for {site_url}."

    result_lines = [f"Sitemaps for {site_url}:"]
    result_lines.append("-" * 80)

    result_lines.append("Path | Last Downloaded | Status | Indexed URLs | Errors")
    result_lines.append("-" * 80)

    for sitemap in sitemaps.get("sitemap", []):
        path = sitemap.get("path", "Unknown")
        last_downloaded = sitemap.get("lastDownloaded", "Never")
        
        if last_downloaded != "Never":
            try:
                dt = datetime.fromisoformat(last_downloaded.replace('Z', '+00:00'))
                last_downloaded = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        status = "Valid"
        if "errors" in sitemap and sitemap["errors"] > 0:
            status = "Has errors"
        
        warnings = sitemap.get("warnings", 0)
        errors = sitemap.get("errors", 0)
        
        indexed_urls = "N/A"
        if "contents" in sitemap:
            for content in sitemap["contents"]:
                if content.get("type") == "web":
                    indexed_urls = content.get("submitted", "0")
                    break
        
        result_lines.append(f"{path} | {last_downloaded} | {status} | {indexed_urls} | {errors}")

    return "\n".join(result_lines)
@mcp.tool()
async def inspect_url_enhanced(site_url: str, page_url: str) -> str:
    """
    Enhanced URL inspection to check indexing status and rich results in Google.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match, for domain properties use format: sc-domain:example.com)
        page_url: The specific URL to inspect
    """
    state = InspectUrlEnhancedState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        page_url=page_url
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error inspecting URL: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    response = state.result
    if not response or "inspectionResult" not in response:
        return f"No inspection data found for {page_url}."

    inspection = response["inspectionResult"]
    result_lines = [f"URL Inspection for {page_url}:"]
    result_lines.append("-" * 80)

    if "inspectionResultLink" in inspection:
        result_lines.append(f"Search Console Link: {inspection['inspectionResultLink']}")
        result_lines.append("-" * 80)

    index_status = inspection.get("indexStatusResult", {})
    verdict = index_status.get("verdict", "UNKNOWN")
    result_lines.append(f"Indexing Status: {verdict}")

    if "coverageState" in index_status:
        result_lines.append(f"Coverage: {index_status['coverageState']}")

    if "lastCrawlTime" in index_status:
        try:
            crawl_time = datetime.fromisoformat(index_status["lastCrawlTime"].replace('Z', '+00:00'))
            result_lines.append(f"Last Crawled: {crawl_time.strftime('%Y-%m-%d %H:%M')}")
        except:
            result_lines.append(f"Last Crawled: {index_status['lastCrawlTime']}")

    if "pageFetchState" in index_status:
        result_lines.append(f"Page Fetch: {index_status['pageFetchState']}")

    if "robotsTxtState" in index_status:
        result_lines.append(f"Robots.txt: {index_status['robotsTxtState']}")

    if "indexingState" in index_status:
        result_lines.append(f"Indexing State: {index_status['indexingState']}")

    if "googleCanonical" in index_status:
        result_lines.append(f"Google Canonical: {index_status['googleCanonical']}")

    if "userCanonical" in index_status and index_status.get("userCanonical") != index_status.get("googleCanonical"):
        result_lines.append(f"User Canonical: {index_status['userCanonical']}")

    if "crawledAs" in index_status:
        result_lines.append(f"Crawled As: {index_status['crawledAs']}")

    if "referringUrls" in index_status and index_status["referringUrls"]:
        result_lines.append("\nReferring URLs:")
        for url in index_status["referringUrls"][:5]:
            result_lines.append(f"- {url}")
        
        if len(index_status["referringUrls"]) > 5:
            result_lines.append(f"... and {len(index_status['referringUrls']) - 5} more")

    if "richResultsResult" in inspection:
        rich = inspection["richResultsResult"]
        result_lines.append(f"\nRich Results: {rich.get('verdict', 'UNKNOWN')}")
        
        if "detectedItems" in rich and rich["detectedItems"]:
            result_lines.append("Detected Rich Result Types:")
            
            for item in rich["detectedItems"]:
                rich_type = item.get("richResultType", "Unknown")
                result_lines.append(f"- {rich_type}")
                
                if "items" in item and item["items"]:
                    for i, subitem in enumerate(item["items"][:3]):
                        if "name" in subitem:
                            result_lines.append(f"  • {subitem['name']}")
                    
                    if len(item["items"]) > 3:
                        result_lines.append(f"  • ... and {len(item['items']) - 3} more items")
        
        if "richResultsIssues" in rich and rich["richResultsIssues"]:
            result_lines.append("\nRich Results Issues:")
            for issue in rich["richResultsIssues"]:
                severity = issue.get("severity", "Unknown")
                message = issue.get("message", "Unknown issue")
                result_lines.append(f"- [{severity}] {message}")

    return "\n".join(result_lines)
@mcp.tool()
async def batch_url_inspection(site_url: str, urls: str) -> str:
    """
    Inspect multiple URLs in batch (within API limits).
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match, for domain properties use format: sc-domain:example.com)
        urls: List of URLs to inspect, one per line
    """
    state = BatchUrlInspectionState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        urls=urls
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        # If it failed due to validation in the block
        if hasattr(outcome, 'exception') and isinstance(outcome.exception, ValueError):
             return str(outcome.exception)
        return f"Error performing batch inspection: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    batch_results = res.get("batch_results", [])
    site_url_res = res.get("site_url", site_url)

    results = []
    for item in batch_results:
        page_url = item["url"]
        if "error" in item:
            results.append(f"{page_url}: Error - {item['error']}")
            continue
            
        response = item["response"]
        if not response or "inspectionResult" not in response:
            results.append(f"{page_url}: No inspection data found")
            continue
            
        inspection = response["inspectionResult"]
        index_status = inspection.get("indexStatusResult", {})
        verdict = index_status.get("verdict", "UNKNOWN")
        coverage = index_status.get("coverageState", "Unknown")
        last_crawl = "Never"
        
        if "lastCrawlTime" in index_status:
            try:
                crawl_time = datetime.fromisoformat(index_status["lastCrawlTime"].replace('Z', '+00:00'))
                last_crawl = crawl_time.strftime('%Y-%m-%d')
            except:
                last_crawl = index_status["lastCrawlTime"]

        rich_results = "None"
        if "richResultsResult" in inspection:
            rich = inspection["richResultsResult"]
            if rich.get("verdict") == "PASS" and "detectedItems" in rich and rich["detectedItems"]:
                rich_types = [r_item.get("richResultType", "Unknown") for r_item in rich["detectedItems"]]
                rich_results = ", ".join(rich_types)

        results.append(f"{page_url}:\n  Status: {verdict} - {coverage}\n  Last Crawl: {last_crawl}\n  Rich Results: {rich_results}\n")

    return f"Batch URL Inspection Results for {site_url_res}:\n\n" + "\n".join(results)
@mcp.tool()
async def check_indexing_issues(site_url: str, urls: str) -> str:
    """
    Check for specific indexing issues across multiple URLs.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match, for domain properties use format: sc-domain:example.com)
        urls: List of URLs to check, one per line
    """
    state = CheckIndexingIssuesState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        urls=urls
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        if hasattr(outcome, 'exception') and isinstance(outcome.exception, ValueError):
             return str(outcome.exception)
        return f"Error checking indexing issues: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    issue_results = res.get("issue_results", [])
    url_list = res.get("url_list", [])

    issues_summary = {
        "not_indexed": [],
        "canonical_issues": [],
        "robots_blocked": [],
        "fetch_issues": [],
        "indexed": []
    }

    for item in issue_results:
        page_url = item["url"]
        if "error" in item:
            issues_summary["not_indexed"].append(f"{page_url} - Error: {item['error']}")
            continue
            
        response = item["response"]
        if not response or "inspectionResult" not in response:
            issues_summary["not_indexed"].append(f"{page_url} - No inspection data found")
            continue
            
        inspection = response["inspectionResult"]
        index_status = inspection.get("indexStatusResult", {})
        verdict = index_status.get("verdict", "UNKNOWN")
        coverage = index_status.get("coverageState", "Unknown")
        
        if verdict != "PASS" or "not indexed" in coverage.lower() or "excluded" in coverage.lower():
            issues_summary["not_indexed"].append(f"{page_url} - {coverage}")
        else:
            issues_summary["indexed"].append(page_url)
        
        google_canonical = index_status.get("googleCanonical", "")
        user_canonical = index_status.get("userCanonical", "")
        
        if google_canonical and user_canonical and google_canonical != user_canonical:
            issues_summary["canonical_issues"].append(
                f"{page_url} - Google chose: {google_canonical} instead of user-declared: {user_canonical}"
            )
        
        robots_state = index_status.get("robotsTxtState", "")
        if robots_state == "BLOCKED":
            issues_summary["robots_blocked"].append(page_url)
        
        fetch_state = index_status.get("pageFetchState", "")
        if fetch_state != "SUCCESSFUL":
            issues_summary["fetch_issues"].append(f"{page_url} - {fetch_state}")

    result_lines = [f"Indexing Issues Report for {site_url}:"]
    result_lines.append("-" * 80)

    result_lines.append(f"Total URLs checked: {len(url_list)}")
    result_lines.append(f"Indexed: {len(issues_summary['indexed'])}")
    result_lines.append(f"Not indexed: {len(issues_summary['not_indexed'])}")
    result_lines.append(f"Canonical issues: {len(issues_summary['canonical_issues'])}")
    result_lines.append(f"Robots.txt blocked: {len(issues_summary['robots_blocked'])}")
    result_lines.append(f"Fetch issues: {len(issues_summary['fetch_issues'])}")
    result_lines.append("-" * 80)

    if issues_summary["not_indexed"]:
        result_lines.append("\nNot Indexed URLs:")
        for issue in issues_summary["not_indexed"]:
            result_lines.append(f"- {issue}")

    if issues_summary["canonical_issues"]:
        result_lines.append("\nCanonical Issues:")
        for issue in issues_summary["canonical_issues"]:
            result_lines.append(f"- {issue}")

    if issues_summary["robots_blocked"]:
        result_lines.append("\nRobots.txt Blocked URLs:")
        for url in issues_summary["robots_blocked"]:
            result_lines.append(f"- {url}")

    if issues_summary["fetch_issues"]:
        result_lines.append("\nFetch Issues:")
        for issue in issues_summary["fetch_issues"]:
            result_lines.append(f"- {issue}")

    return "\n".join(result_lines)
@mcp.tool()
async def get_performance_overview(site_url: str, days: int = 28) -> str:
    """
    Get a performance overview for a specific property.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        days: Number of days to look back (default: 28)
    """
    state = PerformanceOverviewState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        days=days
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving performance overview: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    total_response = res["total"]
    date_response = res["trend"]

    result_lines = [f"Performance Overview for {site_url} (last {days} days):"]
    result_lines.append("-" * 80)

    if total_response.get("rows"):
        row = total_response["rows"][0]
        result_lines.append(f"Total Clicks: {row.get('clicks', 0):,}")
        result_lines.append(f"Total Impressions: {row.get('impressions', 0):,}")
        result_lines.append(f"Average CTR: {row.get('ctr', 0) * 100:.2f}%")
        result_lines.append(f"Average Position: {row.get('position', 0):.1f}")
    else:
        result_lines.append("No data available for the selected period.")
        return "\n".join(result_lines)

    if date_response.get("rows"):
        result_lines.append("\nDaily Trend:")
        result_lines.append("Date | Clicks | Impressions | CTR | Position")
        result_lines.append("-" * 80)
        
        sorted_rows = sorted(date_response["rows"], key=lambda x: x["keys"][0])
        
        for row in sorted_rows:
            date_str = row["keys"][0]
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%m/%d")
            except:
                date_formatted = date_str
            
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0) * 100
            position = row.get("position", 0)
            
            result_lines.append(f"{date_formatted} | {clicks:.0f} | {impressions:.0f} | {ctr:.2f}% | {position:.1f}")

    return "\n".join(result_lines)
@mcp.tool()
async def get_advanced_search_analytics(
    site_url: str, 
    start_date: str = None, 
    end_date: str = None, 
    dimensions: str = "query", 
    search_type: str = "WEB",
    row_limit: int = 1000,
    start_row: int = 0,
    sort_by: str = "clicks",
    sort_direction: str = "descending",
    filter_dimension: str = None,
    filter_operator: str = "contains", 
    filter_expression: str = None
) -> str:
    """
    Get advanced search analytics data with sorting, filtering, and pagination.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        start_date: Start date in YYYY-MM-DD format (defaults to 28 days ago)
        end_date: End date in YYYY-MM-DD format (defaults to today)
        dimensions: Dimensions to group by, comma-separated (e.g., "query,page,device")
        search_type: Type of search results (WEB, IMAGE, VIDEO, NEWS, DISCOVER)
        row_limit: Maximum number of rows to return (max 25000)
        start_row: Starting row for pagination
        sort_by: Metric to sort by (clicks, impressions, ctr, position)
        sort_direction: Sort direction (ascending or descending)
        filter_dimension: Dimension to filter on (query, page, country, device)
        filter_operator: Filter operator (contains, equals, notContains, notEquals)
        filter_expression: Filter expression value
    """
    dimension_list = [d.strip() for d in dimensions.split(",")]
    state = AdvancedSearchAnalyticsState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimension_list,
        search_type=search_type,
        row_limit=row_limit,
        start_row=start_row,
        sort_by=sort_by,
        sort_direction=sort_direction,
        filter_dimension=filter_dimension,
        filter_operator=filter_operator,
        filter_expression=filter_expression
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving advanced search analytics: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    response = res["response"]
    data_dict = res["data"]

    used_start_date = data_dict.get("start_date") or start_date
    used_end_date = data_dict.get("end_date") or end_date
    if not used_end_date:
        used_end_date = datetime.now().date().strftime("%Y-%m-%d")
    if not used_start_date:
        from datetime import timedelta
        used_start_date = (datetime.now().date() - timedelta(days=28)).strftime("%Y-%m-%d")

    if not response.get("rows"):
        filter_msg = f"- Filter: {filter_dimension} {filter_operator} '{filter_expression}'" if filter_dimension else "- No filter applied"
        return (f"No search analytics data found for {site_url} with the specified parameters.\n\n"
               f"Parameters used:\n"
               f"- Date range: {used_start_date} to {used_end_date}\n"
               f"- Dimensions: {dimensions}\n"
               f"- Search type: {search_type}\n"
               f"{filter_msg}")

    result_lines = [f"Search analytics for {site_url}:"]
    result_lines.append(f"Date range: {used_start_date} to {used_end_date}")
    result_lines.append(f"Search type: {search_type}")
    if filter_dimension:
        result_lines.append(f"Filter: {filter_dimension} {filter_operator} '{filter_expression}'")
    result_lines.append(f"Showing rows {start_row+1} to {start_row+len(response.get('rows', []))} (sorted by {sort_by} {sort_direction})")
    result_lines.append("\n" + "-" * 80 + "\n")

    header = []
    for dim in dimension_list:
        header.append(dim.capitalize())
    header.extend(["Clicks", "Impressions", "CTR", "Position"])
    result_lines.append(" | ".join(header))
    result_lines.append("-" * 80)

    for row in response.get("rows", []):
        data = []
        for dim_value in row.get("keys", []):
            data.append(dim_value[:100])
        
        data.append(str(row.get("clicks", 0)))
        data.append(str(row.get("impressions", 0)))
        data.append(f"{row.get('ctr', 0) * 100:.2f}%")
        data.append(f"{row.get('position', 0):.1f}")
        
        result_lines.append(" | ".join(data))

    if len(response.get("rows", [])) == min(row_limit, 25000):
        next_start = start_row + min(row_limit, 25000)
        result_lines.append("\nThere may be more results available. To see the next page, use:")
        result_lines.append(f"start_row: {next_start}, row_limit: {row_limit}")

    return "\n".join(result_lines)
@mcp.tool()
async def compare_search_periods(
    site_url: str,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    dimensions: str = "query",
    limit: int = 10
) -> str:
    """
    Compare search analytics data between two time periods.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        period1_start: Start date for period 1 (YYYY-MM-DD)
        period1_end: End date for period 1 (YYYY-MM-DD)
        period2_start: Start date for period 2 (YYYY-MM-DD)
        period2_end: End date for period 2 (YYYY-MM-DD)
        dimensions: Dimensions to group by (default: query)
        limit: Number of top results to compare (default: 10)
    """
    dimension_list = [d.strip() for d in dimensions.split(",")]
    state = CompareSearchPeriodsState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end,
        dimensions=dimension_list,
        limit=limit
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error comparing search periods: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    period1_response = res["p1"]
    period2_response = res["p2"]

    period1_rows = period1_response.get("rows", [])
    period2_rows = period2_response.get("rows", [])

    if not period1_rows and not period2_rows:
        return f"No data found for either period for {site_url}."

    period1_data = {tuple(row.get("keys", [])): row for row in period1_rows}
    period2_data = {tuple(row.get("keys", [])): row for row in period2_rows}

    all_keys = set(period1_data.keys()) | set(period2_data.keys())
    comparison_data = []

    for key in all_keys:
        p1_row = period1_data.get(key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
        p2_row = period2_data.get(key, {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0})
        
        click_diff = p2_row.get("clicks", 0) - p1_row.get("clicks", 0)
        click_pct = (click_diff / p1_row.get("clicks", 1)) * 100 if p1_row.get("clicks", 0) > 0 else float('inf')
        
        imp_diff = p2_row.get("impressions", 0) - p1_row.get("impressions", 0)
        imp_pct = (imp_diff / p1_row.get("impressions", 1)) * 100 if p1_row.get("impressions", 0) > 0 else float('inf')
        
        ctr_diff = p2_row.get("ctr", 0) - p1_row.get("ctr", 0)
        pos_diff = p1_row.get("position", 0) - p2_row.get("position", 0)
        
        comparison_data.append({
            "key": key,
            "p1_clicks": p1_row.get("clicks", 0),
            "p2_clicks": p2_row.get("clicks", 0),
            "click_diff": click_diff,
            "click_pct": click_pct,
            "p1_impressions": p1_row.get("impressions", 0),
            "p2_impressions": p2_row.get("impressions", 0),
            "imp_diff": imp_diff,
            "imp_pct": imp_pct,
            "p1_ctr": p1_row.get("ctr", 0),
            "p2_ctr": p2_row.get("ctr", 0),
            "ctr_diff": ctr_diff,
            "p1_position": p1_row.get("position", 0),
            "p2_position": p2_row.get("position", 0),
            "pos_diff": pos_diff
        })

    comparison_data.sort(key=lambda x: abs(x["click_diff"]), reverse=True)

    result_lines = [f"Search analytics comparison for {site_url}:"]
    result_lines.append(f"Period 1: {period1_start} to {period1_end}")
    result_lines.append(f"Period 2: {period2_start} to {period2_end}")
    result_lines.append(f"Dimension(s): {dimensions}")
    result_lines.append(f"Top {min(limit, len(comparison_data))} results by change in clicks:")
    result_lines.append("\n" + "-" * 100 + "\n")

    dim_header = " | ".join([d.capitalize() for d in dimension_list])
    result_lines.append(f"{dim_header} | P1 Clicks | P2 Clicks | Change | % | P1 Pos | P2 Pos | Pos Δ")
    result_lines.append("-" * 100)

    for item in comparison_data[:limit]:
        key_str = " | ".join([str(k)[:100] for k in item["key"]])
        
        click_change = item["click_diff"]
        click_pct = item["click_pct"] if item["click_pct"] != float('inf') else "N/A"
        click_pct_str = f"{click_pct:.1f}%" if click_pct != "N/A" else "N/A"
        
        pos_change = item["pos_diff"]
        
        result_lines.append(
            f"{key_str} | {item['p1_clicks']} | {item['p2_clicks']} | "
            f"{click_change:+d} | {click_pct_str} | "
            f"{item['p1_position']:.1f} | {item['p2_position']:.1f} | {pos_change:+.1f}"
        )

    return "\n".join(result_lines)
@mcp.tool()
async def get_search_by_page_query(
    site_url: str,
    page_url: str,
    days: int = 28
) -> str:
    """
    Get search analytics data for a specific page, broken down by query.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        page_url: The specific page URL to analyze
        days: Number of days to look back (default: 28)
    """
    state = SearchByPageQueryState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        page_url=page_url,
        days=days
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving page query data: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    response = res["response"]

    if not response.get("rows"):
        return f"No search data found for page {page_url} in the last {days} days."

    result_lines = [f"Search queries for page {page_url} (last {days} days):"]
    result_lines.append("\n" + "-" * 80 + "\n")

    result_lines.append("Query | Clicks | Impressions | CTR | Position")
    result_lines.append("-" * 80)

    for row in response.get("rows", []):
        query = row.get("keys", ["Unknown"])[0]
        clicks = row.get("clicks", 0)
        impressions = row.get("impressions", 0)
        ctr = row.get("ctr", 0) * 100
        position = row.get("position", 0)
        
        result_lines.append(f"{query[:100]} | {clicks} | {impressions} | {ctr:.2f}% | {position:.1f}")

    total_clicks = sum(row.get("clicks", 0) for row in response.get("rows", []))
    total_impressions = sum(row.get("impressions", 0) for row in response.get("rows", []))
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    result_lines.append("-" * 80)
    result_lines.append(f"TOTAL | {total_clicks} | {total_impressions} | {avg_ctr:.2f}% | -")

    return "\n".join(result_lines)
@mcp.tool()
async def list_sitemaps_enhanced(site_url: str, sitemap_index: str = None) -> str:
    """
    List all sitemaps for a specific Search Console property with detailed information.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        sitemap_index: Optional sitemap index URL to list child sitemaps
    """
    state = SitemapsListState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        request_type="list_sitemaps_enhanced",
        sitemap_index=sitemap_index
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving sitemaps: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    sitemaps = res["sitemaps"]

    source = f"child sitemaps from index: {sitemap_index}" if sitemap_index else "all submitted sitemaps"

    if not sitemaps.get("sitemap"):
        return f"No sitemaps found for {site_url}" + (f" in index {sitemap_index}" if sitemap_index else ".")

    result_lines = [f"Sitemaps for {site_url} ({source}):"]
    result_lines.append("-" * 100)

    result_lines.append("Path | Last Submitted | Last Downloaded | Type | URLs | Errors | Warnings")
    result_lines.append("-" * 100)

    for sitemap in sitemaps.get("sitemap", []):
        path = sitemap.get("path", "Unknown")
        
        last_submitted = sitemap.get("lastSubmitted", "Never")
        if last_submitted != "Never":
            try:
                dt = datetime.fromisoformat(last_submitted.replace('Z', '+00:00'))
                last_submitted = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        last_downloaded = sitemap.get("lastDownloaded", "Never")
        if last_downloaded != "Never":
            try:
                dt = datetime.fromisoformat(last_downloaded.replace('Z', '+00:00'))
                last_downloaded = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        sitemap_type = "Index" if sitemap.get("isSitemapsIndex", False) else "Sitemap"
        errors = sitemap.get("errors", 0)
        warnings = sitemap.get("warnings", 0)
        
        url_count = "N/A"
        if "contents" in sitemap:
            for content in sitemap["contents"]:
                if content.get("type") == "web":
                    url_count = content.get("submitted", "0")
                    break
        
        result_lines.append(f"{path} | {last_submitted} | {last_downloaded} | {sitemap_type} | {url_count} | {errors} | {warnings}")

    pending_count = sum(1 for sitemap in sitemaps.get("sitemap", []) if sitemap.get("isPending", False))
    if pending_count > 0:
        result_lines.append(f"\nNote: {pending_count} sitemaps are still pending processing by Google.")

    return "\n".join(result_lines)
@mcp.tool()
async def get_sitemap_details(site_url: str, sitemap_url: str) -> str:
    """
    Get detailed information about a specific sitemap.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        sitemap_url: The full URL of the sitemap to inspect
    """
    state = SitemapDetailsState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        sitemap_url=sitemap_url
    )
    outcome = await execute_flow(gsc_read_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error retrieving sitemap details: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    details = state.result["details"]

    if not details:
        return f"No details found for sitemap {sitemap_url}."

    result_lines = [f"Sitemap Details for {sitemap_url}:"]
    result_lines.append("-" * 80)

    is_index = details.get("isSitemapsIndex", False)
    result_lines.append(f"Type: {'Sitemap Index' if is_index else 'Sitemap'}")

    is_pending = details.get("isPending", False)
    result_lines.append(f"Status: {'Pending processing' if is_pending else 'Processed'}")

    if "lastSubmitted" in details:
        try:
            dt = datetime.fromisoformat(details["lastSubmitted"].replace('Z', '+00:00'))
            result_lines.append(f"Last Submitted: {dt.strftime('%Y-%m-%d %H:%M')}")
        except:
            result_lines.append(f"Last Submitted: {details['lastSubmitted']}")

    if "lastDownloaded" in details:
        try:
            dt = datetime.fromisoformat(details["lastDownloaded"].replace('Z', '+00:00'))
            result_lines.append(f"Last Downloaded: {dt.strftime('%Y-%m-%d %H:%M')}")
        except:
            result_lines.append(f"Last Downloaded: {details['lastDownloaded']}")

    result_lines.append(f"Errors: {details.get('errors', 0)}")
    result_lines.append(f"Warnings: {details.get('warnings', 0)}")

    if "contents" in details and details["contents"]:
        result_lines.append("\nContent Breakdown:")
        for content in details["contents"]:
            content_type = content.get("type", "Unknown").upper()
            submitted = content.get("submitted", 0)
            indexed = content.get("indexed", "N/A")

            result_lines.append(f"- {content_type}: {submitted} submitted, {indexed} indexed")

    if is_index:
        result_lines.append("\nThis is a sitemap index. To list child sitemaps, use:")
        result_lines.append(f"list_sitemaps_enhanced with sitemap_index={sitemap_url}")

    return "\n".join(result_lines)
@mcp.tool()
async def submit_sitemap(site_url: str, sitemap_url: str) -> str:
    """
    Submit a new sitemap or resubmit an existing one to Google.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        sitemap_url: The full URL of the sitemap to submit
    """
    state = SitemapMutationState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        sitemap_url=sitemap_url,
        request_type="submit_sitemap"
    )
    outcome = await execute_flow(gsc_sitemap_mutation_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error submitting sitemap: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    
    if "details" in res:
        details = res["details"]
        result_lines = [f"Successfully submitted sitemap: {sitemap_url}"]

        if "lastSubmitted" in details:
            try:
                dt = datetime.fromisoformat(details["lastSubmitted"].replace('Z', '+00:00'))
                result_lines.append(f"Submission time: {dt.strftime('%Y-%m-%d %H:%M')}")
            except:
                result_lines.append(f"Submission time: {details['lastSubmitted']}")

        is_pending = details.get("isPending", True)
        result_lines.append(f"Status: {'Pending processing' if is_pending else 'Processing started'}")
        result_lines.append("\nNote: Google may take some time to process the sitemap. Check back later for full details.")

        return "\n".join(result_lines)
    else:
        return f"Successfully submitted sitemap: {sitemap_url}\n\nGoogle will queue it for processing."
@mcp.tool()
async def delete_sitemap(site_url: str, sitemap_url: str) -> str:
    """
    Delete (unsubmit) a sitemap from Google Search Console.
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        sitemap_url: The full URL of the sitemap to delete
    """
    state = SitemapMutationState(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc).isoformat(),
        site_url=site_url,
        sitemap_url=sitemap_url,
        request_type="delete_sitemap"
    )
    outcome = await execute_flow(gsc_sitemap_mutation_workflow, state, async_mode=True)
    if outcome.status == "FAILED" or not state.result:
        return f"Error deleting sitemap: {outcome.exception if hasattr(outcome, 'exception') else 'Unknown error'}"
        
    res = state.result
    if "not_found" in res:
        return f"Sitemap not found: {sitemap_url}. It may have already been deleted or was never submitted."
        
    return f"Successfully deleted sitemap: {sitemap_url}\n\nNote: This only removes the sitemap from Search Console. Any URLs already indexed will remain in Google's index."
@mcp.tool()
async def manage_sitemaps(site_url: str, action: str, sitemap_url: str = None, sitemap_index: str = None) -> str:
    """
    All-in-one tool to manage sitemaps (list, get details, submit, delete).
    
    Args:
        site_url: The URL of the site in Search Console (must be exact match)
        action: The action to perform (list, details, submit, delete)
        sitemap_url: The full URL of the sitemap (required for details, submit, delete)
        sitemap_index: Optional sitemap index URL for listing child sitemaps (only used with 'list' action)
    """
    try:
        # Validate inputs
        action = action.lower().strip()
        valid_actions = ["list", "details", "submit", "delete"]
        
        if action not in valid_actions:
            return f"Invalid action: {action}. Please use one of: {', '.join(valid_actions)}"
        
        if action in ["details", "submit", "delete"] and not sitemap_url:
            return f"The {action} action requires a sitemap_url parameter."
        
        # Perform the requested action
        if action == "list":
            return await list_sitemaps_enhanced(site_url, sitemap_index)
        elif action == "details":
            return await get_sitemap_details(site_url, sitemap_url)
        elif action == "submit":
            return await submit_sitemap(site_url, sitemap_url)
        elif action == "delete":
            return await delete_sitemap(site_url, sitemap_url)
    
    except Exception as e:
        return f"Error managing sitemaps: {str(e)}"

@mcp.tool()
async def get_creator_info() -> str:
    """
    Provides information about Amin Foroutan, the creator of the MCP-GSC tool.
    """
    creator_info = """
# About the Creator: Amin Foroutan

Amin Foroutan is an SEO consultant with over a decade of experience, specializing in technical SEO, Python-driven tools, and data analysis for SEO performance.

## Connect with Amin:

- **LinkedIn**: [Amin Foroutan](https://www.linkedin.com/in/ma-foroutan/)
- **Personal Website**: [aminforoutan.com](https://aminforoutan.com/)
- **YouTube**: [Amin Forout](https://www.youtube.com/channel/UCW7tPXg-rWdH4YzLrcAdBIw)
- **X (Twitter)**: [@aminfseo](https://x.com/aminfseo)

## Notable Projects:

Amin has created several popular SEO tools including:
- Advanced GSC Visualizer (6.4K+ users)
- SEO Render Insight Tool (3.5K+ users)
- Google AI Overview Impact Analysis (1.2K+ users)
- Google AI Overview Citation Analysis (900+ users)
- SEMRush Enhancer (570+ users)
- SEO Page Inspector (115+ users)

## Expertise:

Amin combines technical SEO knowledge with programming skills to create innovative solutions for SEO challenges.
"""
    return creator_info

def _normalize_http_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    return path


def _resolve_http_port(raw_port: str) -> int:
    try:
        return int(raw_port)
    except (TypeError, ValueError):
        return 8011


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()

    # Keep stdio as default for local MCP clients; use HTTP for production serving.
    if transport in {"http", "streamable-http", "sse"}:
        mcp.run(
            transport="streamable-http" if transport == "http" else transport,
            host=DEFAULT_HTTP_HOST,
            port=_resolve_http_port(DEFAULT_HTTP_PORT),
            path=_normalize_http_path(DEFAULT_HTTP_PATH),
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
