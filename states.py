from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional

class BaseGSCWorkflowState(BaseModel):
    # Versionado
    context_version: str = "1.0.0"
    previous_context_version: Optional[str] = None

    # Auditoría
    run_id: str
    started_at: str
    finished_at: Optional[str] = None
    decision: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Contexto técnico serializable
    transport: Literal["http", "stdio"] = "stdio"
    auth_mode: Optional[Literal["static", "jwt"]] = None

    # Resultado de negocio
    result: Optional[Dict[str, Any] | str] = None
    business_status: Literal[
        "pending",
        "running",
        "succeeded",
        "failed",
        "compensated",
        "partial_success",
    ] = "pending"

class ReadOnlyState(BaseGSCWorkflowState):
    request_type: str
    site_url: str
    # Other potential common fields

class SearchAnalyticsState(ReadOnlyState):
    request_type: Literal["search_analytics"] = "search_analytics"
    days: int = 28
    dimensions: List[str] = Field(default_factory=lambda: ["query"])

class AdvancedSearchAnalyticsState(ReadOnlyState):
    request_type: Literal["advanced_search_analytics"] = "advanced_search_analytics"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    dimensions: List[str] = Field(default_factory=lambda: ["query"])
    search_type: str = "WEB"
    row_limit: int = 1000
    start_row: int = 0
    sort_by: str = "clicks"
    sort_direction: str = "descending"
    filter_dimension: Optional[str] = None
    filter_operator: str = "contains"
    filter_expression: Optional[str] = None

class CompareSearchPeriodsState(ReadOnlyState):
    request_type: Literal["compare_search_periods"] = "compare_search_periods"
    period1_start: str
    period1_end: str
    period2_start: str
    period2_end: str
    dimensions: List[str] = Field(default_factory=lambda: ["query"])
    limit: int = 10

class InspectUrlEnhancedState(ReadOnlyState):
    request_type: Literal["inspect_url_enhanced"] = "inspect_url_enhanced"
    page_url: str

class BatchUrlInspectionState(ReadOnlyState):
    request_type: Literal["batch_url_inspection"] = "batch_url_inspection"
    urls: str

class CheckIndexingIssuesState(ReadOnlyState):
    request_type: Literal["check_indexing_issues"] = "check_indexing_issues"
    urls: str

class PerformanceOverviewState(ReadOnlyState):
    request_type: Literal["get_performance_overview"] = "get_performance_overview"
    days: int = 28

class SearchByPageQueryState(ReadOnlyState):
    request_type: Literal["get_search_by_page_query"] = "get_search_by_page_query"
    page_url: str
    days: int = 28

class SiteMutationState(BaseGSCWorkflowState):
    request_type: Literal["add_site", "delete_site"]
    site_url: str

class SitemapMutationState(BaseGSCWorkflowState):
    request_type: Literal["submit_sitemap", "delete_sitemap"]
    site_url: str
    sitemap_url: str

class ListPropertiesState(BaseGSCWorkflowState):
    request_type: Literal["list_properties"] = "list_properties"

class SiteDetailsState(ReadOnlyState):
    request_type: Literal["get_site_details"] = "get_site_details"

class SitemapsListState(ReadOnlyState):
    request_type: Literal["get_sitemaps", "list_sitemaps_enhanced"]
    sitemap_index: Optional[str] = None

class SitemapDetailsState(ReadOnlyState):
    request_type: Literal["get_sitemap_details"] = "get_sitemap_details"
    sitemap_url: str
