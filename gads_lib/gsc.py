"""Google Search Console API functions."""
from .http import get_bearer_headers, request_json

GSC_BASE = "https://www.googleapis.com/webmasters/v3"


def gsc_list_sites(creds):
    """List all verified Search Console sites."""
    return request_json("GET", f"{GSC_BASE}/sites", headers=get_bearer_headers(creds))


def gsc_search_analytics(creds, site_url, start_date, end_date, dimensions=None, row_limit=25, search_type="web"):
    """Query Search Console search analytics.

    site_url: the property URL (e.g. "https://shop.talas.ae/" or "sc-domain:talas.ae")
    start_date/end_date: "YYYY-MM-DD" strings
    dimensions: list of "query", "page", "device", "country", "date"
    """
    import urllib.parse
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "rowLimit": row_limit,
        "type": search_type,
    }
    if dimensions:
        body["dimensions"] = dimensions

    encoded_url = urllib.parse.quote(site_url, safe="")
    return request_json(
        "POST",
        f"{GSC_BASE}/sites/{encoded_url}/searchAnalytics/query",
        headers=get_bearer_headers(creds),
        json_body=body,
    )
