from .config import GA4_PROPERTY_ID
from .http import get_bearer_headers, request_json

GA4_DATA_BASE = "https://analyticsdata.googleapis.com/v1beta"


def _require_property():
    if not GA4_PROPERTY_ID:
        import click
        click.secho("✗ GOOGLE_GA4_PROPERTY_ID not set in .env", fg="red", err=True)
        raise SystemExit(1)
    return GA4_PROPERTY_ID


def ga4_get_metadata(creds, property_id=None):
    pid = property_id or _require_property()
    return request_json(
        "GET",
        f"{GA4_DATA_BASE}/properties/{pid}/metadata",
        headers=get_bearer_headers(creds),
    )


def ga4_run_report(creds, dimensions, metrics, date_ranges, property_id=None, limit=10000):
    pid = property_id or _require_property()
    body = {
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "dateRanges": date_ranges,
        "limit": limit,
    }
    return request_json(
        "POST",
        f"{GA4_DATA_BASE}/properties/{pid}:runReport",
        headers=get_bearer_headers(creds),
        json_body=body,
    )


def ga4_run_realtime_report(creds, dimensions, metrics, property_id=None):
    pid = property_id or _require_property()
    body = {
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
    }
    return request_json(
        "POST",
        f"{GA4_DATA_BASE}/properties/{pid}:runRealtimeReport",
        headers=get_bearer_headers(creds),
        json_body=body,
    )
