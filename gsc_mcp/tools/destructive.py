"""Destructive GSC MCP tools (registered only when GSC_ALLOW_DESTRUCTIVE=true)."""

from __future__ import annotations

import json
from typing import Optional

from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

from gsc_mcp import auth
from gsc_mcp.config import Settings
from gsc_mcp.gsc_client import site_not_found_error


def register_destructive_tools(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool()
    async def add_site(site_url: str) -> str:
        """Add a site to Search Console (destructive)."""
        try:
            service = auth.get_gsc_service()
            response = service.sites().add(siteUrl=site_url).execute()
            return json.dumps(
                {
                    "site_url": site_url,
                    "status": "added",
                    "permission_level": response.get("permissionLevel"),
                }
            )
        except HttpError as e:
            return json.dumps({"error": str(e), "code": f"http_{e.resp.status}"})
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def delete_site(site_url: str) -> str:
        """Remove a site from Search Console (destructive)."""
        try:
            service = auth.get_gsc_service()
            service.sites().delete(siteUrl=site_url).execute()
            return json.dumps({"site_url": site_url, "status": "deleted"})
        except HttpError as e:
            return json.dumps({"error": str(e), "code": f"http_{e.resp.status}"})
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def submit_sitemap(site_url: str, sitemap_url: str) -> str:
        """Submit or resubmit a sitemap (destructive)."""
        try:
            service = auth.get_gsc_service()
            service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
            return json.dumps(
                {"site_url": site_url, "sitemap_url": sitemap_url, "status": "submitted"}
            )
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def delete_sitemap(site_url: str, sitemap_url: str) -> str:
        """Delete a sitemap from Search Console (destructive)."""
        try:
            service = auth.get_gsc_service()
            try:
                service.sitemaps().get(siteUrl=site_url, feedpath=sitemap_url).execute()
            except Exception as e:
                if "404" in str(e):
                    return json.dumps(
                        {"error": f"Sitemap not found: {sitemap_url}", "code": "not_found"}
                    )
                raise
            service.sitemaps().delete(siteUrl=site_url, feedpath=sitemap_url).execute()
            return json.dumps(
                {"site_url": site_url, "sitemap_url": sitemap_url, "status": "deleted"}
            )
        except Exception as e:
            return json.dumps({"error": str(e), "code": "error"})

    @mcp.tool()
    async def manage_sitemaps(
        site_url: str,
        action: str,
        sitemap_url: Optional[str] = None,
        sitemap_index: Optional[str] = None,
    ) -> str:
        """Manage sitemaps: list, details, submit, delete."""
        action = action.lower().strip()
        valid = ["list", "details", "submit", "delete"]
        if action not in valid:
            return json.dumps(
                {
                    "error": f"Invalid action '{action}'. Use: {', '.join(valid)}",
                    "code": "invalid_input",
                }
            )
        if action in ("details", "submit", "delete") and not sitemap_url:
            return json.dumps(
                {"error": f"action '{action}' requires sitemap_url", "code": "invalid_input"}
            )
        try:
            service = auth.get_gsc_service()
            if action == "list":
                if sitemap_index:
                    sitemaps = service.sitemaps().list(
                        siteUrl=site_url, sitemapIndex=sitemap_index
                    ).execute()
                else:
                    sitemaps = service.sitemaps().list(siteUrl=site_url).execute()
                if not sitemaps.get("sitemap"):
                    return json.dumps({"site_url": site_url, "count": 0, "sitemaps": []})
                items = []
                for sitemap in sitemaps.get("sitemap", []):
                    items.append(
                        {
                            "path": sitemap.get("path"),
                            "is_pending": sitemap.get("isPending", False),
                            "errors": int(sitemap.get("errors", 0)),
                            "warnings": int(sitemap.get("warnings", 0)),
                        }
                    )
                return json.dumps({"site_url": site_url, "count": len(items), "sitemaps": items})
            if action == "details":
                details = service.sitemaps().get(
                    siteUrl=site_url, feedpath=sitemap_url
                ).execute()
                return json.dumps({"site_url": site_url, "sitemap_url": sitemap_url, **details})
            if action == "submit":
                service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
                return json.dumps(
                    {"site_url": site_url, "sitemap_url": sitemap_url, "status": "submitted"}
                )
            service.sitemaps().delete(siteUrl=site_url, feedpath=sitemap_url).execute()
            return json.dumps(
                {"site_url": site_url, "sitemap_url": sitemap_url, "status": "deleted"}
            )
        except Exception as e:
            if "404" in str(e):
                return json.dumps({"error": site_not_found_error(site_url), "code": "not_found"})
            return json.dumps({"error": str(e), "code": "error"})
