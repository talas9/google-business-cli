import re
import click
import requests

from .config import API_VERSION, CUSTOMER_ID, DEV_TOKEN, LOGIN_CUSTOMER_ID


def get_ads_headers(creds):
    return {
        "Authorization": f"Bearer {creds.token}",
        "developer-token": DEV_TOKEN,
        "login-customer-id": LOGIN_CUSTOMER_ID,
        "Content-Type": "application/json",
    }


def sanitize_keyword(keyword):
    """Remove special characters and collapse whitespace.
    
    Removes: ! @ % , * '
    Collapses multiple spaces to single space.
    """
    # Remove special chars
    sanitized = re.sub(r'[!@%,*\']', '', keyword)
    # Collapse whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized


def run_gaql(creds, query):
    """Execute a GAQL query via the REST searchStream endpoint."""
    resp = requests.post(
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}/googleAds:searchStream",
        headers=get_ads_headers(creds),
        json={"query": query},
    )
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)

    results = []
    for batch in resp.json():
        results.extend(batch.get("results", []))
    return results


def ads_search(creds, query):
    """Execute a GAQL query via the REST search endpoint (paginated).
    
    Uses pageToken loop instead of searchStream.
    Returns list of all results across pages.
    """
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}/googleAds:search"
    )
    headers = get_ads_headers(creds)
    results = []
    page_token = None
    
    while True:
        payload = {"query": query}
        if page_token:
            payload["pageToken"] = page_token
        
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            detail = resp.text[:800]
            click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
            raise SystemExit(1)
        
        data = resp.json()
        results.extend(data.get("results", []))
        
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    
    return results


def ads_mutate(creds, resource_path, operations):
    """Single-resource mutate operation.
    
    POST to /{resource_path}:mutate with {"operations": operations}
    Returns response JSON.
    """
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}/{resource_path}:mutate"
    )
    headers = get_ads_headers(creds)
    payload = {"operations": operations}
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    
    return resp.json()


def ads_batch_mutate(creds, mutate_operations):
    """Cross-resource batch mutate operation.
    
    POST to /googleAds:mutate with {"mutateOperations": mutate_operations}
    KEY: use "mutateOperations" NOT "operations"
    Returns response JSON.
    """
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}/googleAds:mutate"
    )
    headers = get_ads_headers(creds)
    payload = {"mutateOperations": mutate_operations}
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    
    return resp.json()


def ads_upload_click_conversions(creds, conversions, conversion_action_id):
    """Upload click conversions.
    
    POST to /customers/{CID}:uploadClickConversions
    Injects conversion_action_id into each conversion object.
    """
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}:uploadClickConversions"
    )
    headers = get_ads_headers(creds)
    
    # Inject conversion_action_id into each conversion
    enriched_conversions = []
    for conv in conversions:
        enriched = dict(conv)
        enriched["conversionAction"] = conversion_action_id
        enriched_conversions.append(enriched)
    
    payload = {
        "conversions": enriched_conversions,
        "partialFailure": True,
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    
    return resp.json()


def generate_keyword_ideas(creds, keywords=None, url=None, language_id="1000", geo_ids=None):
    """Generate keyword ideas.
    
    POST to /customers/{CID}:generateKeywordIdeas
    Supports keywordSeed, urlSeed, or both.
    Sanitizes keywords before sending.
    """
    if not keywords and not url:
        click.secho("✗ Must provide either keywords or url", fg="red", err=True)
        raise SystemExit(1)
    
    url_endpoint = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}:generateKeywordIdeas"
    )
    headers = get_ads_headers(creds)
    
    payload = {}
    
    if keywords:
        # Sanitize keywords
        sanitized = [sanitize_keyword(kw) for kw in keywords]
        payload["keywordSeed"] = {"keywords": sanitized}
    
    if url:
        payload["urlSeed"] = {"url": url}
    
    # Add language and geo targeting
    payload["languageId"] = language_id
    if geo_ids:
        payload["geoTargetConstants"] = [{"resourceName": f"geoTargetConstants/{geo_id}"} for geo_id in geo_ids]
    
    resp = requests.post(url_endpoint, headers=headers, json=payload)
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    
    return resp.json()


def generate_keyword_forecast(creds, keywords, language_id="1000", geo_ids=None):
    """Generate keyword forecast metrics.
    
    POST to /customers/{CID}:generateKeywordForecastMetrics
    Sanitizes keywords before sending.
    """
    url_endpoint = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{CUSTOMER_ID}:generateKeywordForecastMetrics"
    )
    headers = get_ads_headers(creds)
    
    # Sanitize keywords
    sanitized_keywords = [sanitize_keyword(kw) for kw in keywords]
    
    payload = {
        "campaignToForecast": {
            "keywordPlanKeywords": [
                {"keyword": kw} for kw in sanitized_keywords
            ],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            "languageConstants": [f"languageConstants/{language_id}"],
        }
    }
    
    if geo_ids:
        payload["campaignToForecast"]["geoTargetConstants"] = [
            f"geoTargetConstants/{geo_id}" for geo_id in geo_ids
        ]
    
    resp = requests.post(url_endpoint, headers=headers, json=payload)
    if resp.status_code != 200:
        detail = resp.text[:800]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    
    return resp.json()
