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
