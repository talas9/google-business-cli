import click
import requests

from .config import DEV_TOKEN, LOGIN_CUSTOMER_ID


def request_json(method, url, *, headers=None, params=None, json_body=None, timeout=30):
    resp = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        detail = resp.text[:1200]
        click.secho(f"✗ API Error {resp.status_code}: {detail}", fg="red", err=True)
        raise SystemExit(1)
    if not resp.text:
        return {}
    return resp.json()


def get_bearer_headers(creds):
    return {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }


def get_ads_headers(creds):
    return {
        **get_bearer_headers(creds),
        "developer-token": DEV_TOKEN,
        "login-customer-id": LOGIN_CUSTOMER_ID,
    }
