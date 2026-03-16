from datetime import datetime, timezone, timedelta
from vibeblocks import block, ExecutionContext
from states import BaseGSCWorkflowState
from exceptions import UnsupportedContextVersionError
import json
from googleapiclient.errors import HttpError
from vibeblocks.policies.retry import RetryPolicy, BackoffStrategy
from exceptions import TransientGSCError, PermanentGSCError

@block(name="init_run_metadata")
def init_run_metadata(ctx: ExecutionContext[BaseGSCWorkflowState]):
    if not ctx.data.started_at:
        ctx.data.started_at = datetime.now(timezone.utc).isoformat()
    ctx.data.business_status = "running"
    return ctx

@block(name="validate_context_version")
def validate_context_version(ctx: ExecutionContext[BaseGSCWorkflowState]):
    if ctx.data.context_version != "1.0.0":
        raise UnsupportedContextVersionError(f"Unsupported context version: {ctx.data.context_version}")
    return ctx

@block(name="load_runtime_config")
def load_runtime_config(ctx: ExecutionContext[BaseGSCWorkflowState]):
    if "server_config" in ctx.metadata:
        config = ctx.metadata["server_config"]
        ctx.data.transport = config.transport
        ctx.data.auth_mode = config.auth_mode
    return ctx

@block(name="validate_request_contract")
def validate_request_contract(ctx: ExecutionContext[BaseGSCWorkflowState]):
    return ctx

def get_gsc_service_impl():
    from gsc_server import get_gsc_service
    return get_gsc_service()

@block(
    name="build_gsc_client",
    retry_policy=RetryPolicy(
        max_attempts=2,
        delay=1.0,
        backoff=BackoffStrategy.FIXED,
        give_up_on=[FileNotFoundError, ValueError, PermanentGSCError]
    )
)
def build_gsc_client(ctx: ExecutionContext[BaseGSCWorkflowState]):
    if "gsc_service" not in ctx.metadata:
        service = get_gsc_service_impl()
        ctx.metadata["gsc_service"] = service
    return ctx

@block(
    name="execute_gsc_operation",
    retry_policy=RetryPolicy(
        max_attempts=3,
        delay=1.0,
        backoff=BackoffStrategy.EXPONENTIAL,
        retry_on=[TransientGSCError],
        give_up_on=[PermanentGSCError, ValueError, FileNotFoundError]
    )
)
def execute_gsc_operation(ctx: ExecutionContext[BaseGSCWorkflowState]):
    service = ctx.metadata.get("gsc_service")
    if not service:
        raise ValueError("GSC service not initialized")

    data = ctx.data
    req_type = data.request_type

    try:
        if req_type == "list_properties":
            site_list = service.sites().list().execute()
            ctx.metadata["raw_response"] = site_list

        elif req_type == "get_site_details":
            site_info = service.sites().get(siteUrl=data.site_url).execute()
            ctx.metadata["raw_response"] = site_info

        elif req_type == "search_analytics":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=data.days)
            request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": data.dimensions,
                "rowLimit": 20
            }
            response = service.searchanalytics().query(siteUrl=data.site_url, body=request).execute()
            ctx.metadata["raw_response"] = response

        elif req_type == "get_performance_overview":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=data.days)

            total_request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": [],
                "rowLimit": 1
            }
            total_response = service.searchanalytics().query(siteUrl=data.site_url, body=total_request).execute()

            date_request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["date"],
                "rowLimit": data.days
            }
            date_response = service.searchanalytics().query(siteUrl=data.site_url, body=date_request).execute()

            ctx.metadata["raw_response"] = {
                "total": total_response,
                "trend": date_response,
                "days": data.days,
                "site_url": data.site_url
            }

        elif req_type == "inspect_url_enhanced":
            request = {
                "inspectionUrl": data.page_url,
                "siteUrl": data.site_url
            }
            response = service.urlInspection().index().inspect(body=request).execute()
            ctx.metadata["raw_response"] = response

        elif req_type == "batch_url_inspection":
            url_list = [url.strip() for url in data.urls.split('\n') if url.strip()]
            if not url_list:
                raise ValueError("No URLs provided for inspection.")
            if len(url_list) > 10:
                raise ValueError(f"Too many URLs provided ({len(url_list)}). Please limit to 10 URLs per batch.")

            results = []
            for page_url in url_list:
                request = {
                    "inspectionUrl": page_url,
                    "siteUrl": data.site_url
                }
                try:
                    response = service.urlInspection().index().inspect(body=request).execute()
                    results.append({"url": page_url, "response": response})
                except Exception as e:
                    results.append({"url": page_url, "error": str(e)})
            ctx.metadata["raw_response"] = {"batch_results": results, "site_url": data.site_url}

        elif req_type == "check_indexing_issues":
            url_list = [url.strip() for url in data.urls.split('\n') if url.strip()]
            if not url_list:
                raise ValueError("No URLs provided for inspection.")
            if len(url_list) > 10:
                raise ValueError(f"Too many URLs provided ({len(url_list)}). Please limit to 10 URLs per batch.")

            results = []
            for page_url in url_list:
                request = {
                    "inspectionUrl": page_url,
                    "siteUrl": data.site_url
                }
                try:
                    response = service.urlInspection().index().inspect(body=request).execute()
                    results.append({"url": page_url, "response": response})
                except Exception as e:
                    results.append({"url": page_url, "error": str(e)})
            ctx.metadata["raw_response"] = {"issue_results": results, "site_url": data.site_url, "url_list": url_list}

        elif req_type == "advanced_search_analytics":
            end_date = data.end_date
            start_date = data.start_date
            if not end_date:
                end_date = datetime.now().date().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now().date() - timedelta(days=28)).strftime("%Y-%m-%d")

            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": data.dimensions,
                "rowLimit": min(data.row_limit, 25000),
                "startRow": data.start_row,
                "searchType": data.search_type.upper()
            }

            if data.sort_by:
                metric_map = {
                    "clicks": "CLICK_COUNT",
                    "impressions": "IMPRESSION_COUNT",
                    "ctr": "CTR",
                    "position": "POSITION"
                }
                if data.sort_by in metric_map:
                    request["orderBy"] = [{
                        "metric": metric_map[data.sort_by],
                        "direction": data.sort_direction.lower()
                    }]

            if data.filter_dimension and data.filter_expression:
                filter_group = {
                    "filters": [{
                        "dimension": data.filter_dimension,
                        "operator": data.filter_operator,
                        "expression": data.filter_expression
                    }]
                }
                request["dimensionFilterGroups"] = [filter_group]

            response = service.searchanalytics().query(siteUrl=data.site_url, body=request).execute()
            ctx.metadata["raw_response"] = {
                "response": response,
                "data": data.model_dump()
            }

        elif req_type == "compare_search_periods":
            period1_request = {
                "startDate": data.period1_start,
                "endDate": data.period1_end,
                "dimensions": data.dimensions,
                "rowLimit": 1000
            }
            period2_request = {
                "startDate": data.period2_start,
                "endDate": data.period2_end,
                "dimensions": data.dimensions,
                "rowLimit": 1000
            }

            period1_response = service.searchanalytics().query(siteUrl=data.site_url, body=period1_request).execute()
            period2_response = service.searchanalytics().query(siteUrl=data.site_url, body=period2_request).execute()

            ctx.metadata["raw_response"] = {
                "p1": period1_response,
                "p2": period2_response,
                "data": data.model_dump()
            }

        elif req_type == "get_search_by_page_query":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=data.days)

            request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["query"],
                "dimensionFilterGroups": [{
                    "filters": [{
                        "dimension": "page",
                        "operator": "equals",
                        "expression": data.page_url
                    }]
                }],
                "rowLimit": 20,
                "orderBy": [{"metric": "CLICK_COUNT", "direction": "descending"}]
            }
            response = service.searchanalytics().query(siteUrl=data.site_url, body=request).execute()
            ctx.metadata["raw_response"] = {
                "response": response,
                "page_url": data.page_url,
                "days": data.days
            }

        elif req_type == "get_sitemaps" or req_type == "list_sitemaps_enhanced":
            if getattr(data, "sitemap_index", None):
                sitemaps = service.sitemaps().list(siteUrl=data.site_url, sitemapIndex=data.sitemap_index).execute()
            else:
                sitemaps = service.sitemaps().list(siteUrl=data.site_url).execute()

            if req_type == "get_sitemaps":
                ctx.metadata["raw_response"] = sitemaps
            else:
                ctx.metadata["raw_response"] = {
                    "sitemaps": sitemaps,
                    "sitemap_index": data.sitemap_index,
                    "site_url": data.site_url
                }

        elif req_type == "get_sitemap_details":
            details = service.sitemaps().get(siteUrl=data.site_url, feedpath=data.sitemap_url).execute()
            ctx.metadata["raw_response"] = {
                "details": details,
                "sitemap_url": data.sitemap_url
            }

        elif req_type == "add_site":
            response = service.sites().add(siteUrl=data.site_url).execute()
            ctx.metadata["raw_response"] = response

        elif req_type == "delete_site":
            service.sites().delete(siteUrl=data.site_url).execute()
            ctx.metadata["raw_response"] = {"deleted": True, "site_url": data.site_url}

        elif req_type == "submit_sitemap":
            service.sitemaps().submit(siteUrl=data.site_url, feedpath=data.sitemap_url).execute()
            try:
                details = service.sitemaps().get(siteUrl=data.site_url, feedpath=data.sitemap_url).execute()
                ctx.metadata["raw_response"] = {"submitted": True, "details": details, "sitemap_url": data.sitemap_url}
            except:
                ctx.metadata["raw_response"] = {"submitted": True, "sitemap_url": data.sitemap_url}

        elif req_type == "delete_sitemap":
            try:
                service.sitemaps().get(siteUrl=data.site_url, feedpath=data.sitemap_url).execute()
            except Exception as e:
                if "404" in str(e):
                    ctx.metadata["raw_response"] = {"not_found": True, "sitemap_url": data.sitemap_url}
                    return ctx
                else:
                    raise e
            service.sitemaps().delete(siteUrl=data.site_url, feedpath=data.sitemap_url).execute()
            ctx.metadata["raw_response"] = {"deleted": True, "sitemap_url": data.sitemap_url}

        else:
            raise ValueError(f"Unknown request type: {req_type}")

    except HttpError as e:
        error_code = e.resp.status
        if error_code in (429, 500, 503):
            raise TransientGSCError(str(e)) from e
        elif error_code in (400, 401, 403, 404, 409):
            raise PermanentGSCError(str(e)) from e
        else:
            raise
    return ctx

@block(name="normalize_output")
def normalize_output(ctx: ExecutionContext[BaseGSCWorkflowState]):
    if "raw_response" in ctx.metadata:
        ctx.data.result = ctx.metadata["raw_response"]
    return ctx

@block(name="persist_audit_event")
def persist_audit_event(ctx: ExecutionContext[BaseGSCWorkflowState]):
    try:
        pass
    except Exception as e:
        ctx.data.errors.append({"audit_error": str(e)})
    return ctx

@block(name="finalize_run")
def finalize_run(ctx: ExecutionContext[BaseGSCWorkflowState]):
    ctx.data.finished_at = datetime.now(timezone.utc).isoformat()
    if ctx.data.business_status == "running":
        ctx.data.business_status = "succeeded"
    if not ctx.data.decision:
        ctx.data.decision = "completed_successfully"
    return ctx
