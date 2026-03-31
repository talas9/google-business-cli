from .http import get_bearer_headers, request_json

GBP_ACCOUNT_BASE = "https://mybusinessaccountmanagement.googleapis.com/v1"
GBP_INFO_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"
GBP_V4_BASE = "https://mybusiness.googleapis.com/v4"


def gbp_list_accounts(creds):
    return request_json("GET", f"{GBP_ACCOUNT_BASE}/accounts", headers=get_bearer_headers(creds))


def gbp_list_locations(creds, account_name, page_size=100, read_mask=None):
    params = {"pageSize": page_size}
    if read_mask:
        params["readMask"] = read_mask
    return request_json(
        "GET",
        f"{GBP_INFO_BASE}/{account_name}/locations",
        headers=get_bearer_headers(creds),
        params=params,
    )


def gbp_get_location(creds, location_name, read_mask=None):
    params = {}
    if read_mask:
        params["readMask"] = read_mask
    return request_json(
        "GET",
        f"{GBP_INFO_BASE}/{location_name}",
        headers=get_bearer_headers(creds),
        params=params,
    )


def gbp_list_reviews(creds, location_name, page_size=50):
    return request_json(
        "GET",
        f"{GBP_V4_BASE}/{location_name}/reviews",
        headers=get_bearer_headers(creds),
        params={"pageSize": page_size},
    )


def gbp_reply_review(creds, review_name, comment):
    return request_json(
        "PUT",
        f"{GBP_V4_BASE}/{review_name}/reply",
        headers=get_bearer_headers(creds),
        json_body={"comment": comment},
    )


def gbp_delete_reply(creds, review_name):
    return request_json(
        "DELETE",
        f"{GBP_V4_BASE}/{review_name}/reply",
        headers=get_bearer_headers(creds),
    )


# ── GBP Performance API ─────────────────────────────────────

GBP_PERF_BASE = "https://businessprofileperformance.googleapis.com/v1"

# All available daily metrics
DAILY_METRICS = [
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
    "BUSINESS_CONVERSATIONS",
    "BUSINESS_DIRECTION_REQUESTS",
    "CALL_CLICKS",
    "WEBSITE_CLICKS",
    "BUSINESS_BOOKINGS",
    "BUSINESS_FOOD_ORDERS",
    "BUSINESS_FOOD_MENU_CLICKS",
]


def gbp_daily_metrics(creds, location_name, metric, start_date, end_date):
    """Fetch a single daily metric time series for a location.

    start_date/end_date: date objects or (year, month, day) tuples.
    Returns list of {date: "YYYY-MM-DD", value: int}.
    """
    if hasattr(start_date, "year"):
        sy, sm, sd = start_date.year, start_date.month, start_date.day
    else:
        sy, sm, sd = start_date
    if hasattr(end_date, "year"):
        ey, em, ed = end_date.year, end_date.month, end_date.day
    else:
        ey, em, ed = end_date

    params = {
        "dailyMetric": metric,
        "dailyRange.startDate.year": sy,
        "dailyRange.startDate.month": sm,
        "dailyRange.startDate.day": sd,
        "dailyRange.endDate.year": ey,
        "dailyRange.endDate.month": em,
        "dailyRange.endDate.day": ed,
    }
    data = request_json(
        "GET",
        f"{GBP_PERF_BASE}/{location_name}:getDailyMetricsTimeSeries",
        headers=get_bearer_headers(creds),
        params=params,
    )
    results = []
    for dv in data.get("timeSeries", {}).get("datedValues", []):
        d = dv["date"]
        results.append({
            "date": f"{d['year']}-{d['month']:02d}-{d['day']:02d}",
            "value": int(dv.get("value", 0)),
        })
    return results


def gbp_multi_daily_metrics(creds, location_name, metrics, start_date, end_date):
    """Fetch multiple daily metrics in a single API call.

    Returns dict of {metric_name: [{date, value}, ...]}.
    """
    if hasattr(start_date, "year"):
        sy, sm, sd = start_date.year, start_date.month, start_date.day
    else:
        sy, sm, sd = start_date
    if hasattr(end_date, "year"):
        ey, em, ed = end_date.year, end_date.month, end_date.day
    else:
        ey, em, ed = end_date

    params = {
        "dailyRange.startDate.year": sy,
        "dailyRange.startDate.month": sm,
        "dailyRange.startDate.day": sd,
        "dailyRange.endDate.year": ey,
        "dailyRange.endDate.month": em,
        "dailyRange.endDate.day": ed,
    }
    # fetchMultiDailyMetricsTimeSeries uses repeated dailyMetrics param
    param_str = "&".join(f"dailyMetrics={m}" for m in metrics)
    base_str = "&".join(f"{k}={v}" for k, v in params.items())

    import requests as _requests
    resp = _requests.get(
        f"{GBP_PERF_BASE}/{location_name}:fetchMultiDailyMetricsTimeSeries?{param_str}&{base_str}",
        headers=get_bearer_headers(creds),
        timeout=30,
    )
    if resp.status_code >= 400:
        import click
        click.secho(f"✗ API Error {resp.status_code}: {resp.text[:800]}", fg="red", err=True)
        raise SystemExit(1)

    result = {}
    for group in resp.json().get("multiDailyMetricTimeSeries", []):
        for series in group.get("dailyMetricTimeSeries", []):
            metric_name = series.get("dailyMetric", "UNKNOWN")
            values = []
            for dv in series.get("timeSeries", {}).get("datedValues", []):
                d = dv["date"]
                values.append({
                    "date": f"{d['year']}-{d['month']:02d}-{d['day']:02d}",
                    "value": int(dv.get("value", 0)),
                })
            result[metric_name] = values
    return result


def gbp_search_keywords_monthly(creds, location_name, start_month, end_month, page_size=100):
    """Fetch monthly search keyword impressions.

    start_month/end_month: (year, month) tuples.
    Returns list of {keyword, impressions}.
    """
    sy, sm = start_month
    ey, em = end_month
    params = {
        "monthlyRange.startMonth.year": sy,
        "monthlyRange.startMonth.month": sm,
        "monthlyRange.endMonth.year": ey,
        "monthlyRange.endMonth.month": em,
        "pageSize": page_size,
    }

    all_keywords = []
    while True:
        data = request_json(
            "GET",
            f"{GBP_PERF_BASE}/{location_name}/searchkeywords/impressions/monthly",
            headers=get_bearer_headers(creds),
            params=params,
        )
        for kw in data.get("searchKeywordsCounts", []):
            all_keywords.append({
                "keyword": kw.get("searchKeyword", ""),
                "impressions": int(kw.get("insightsValue", {}).get("value", 0)),
            })
        token = data.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token

    return sorted(all_keywords, key=lambda x: -x["impressions"])
