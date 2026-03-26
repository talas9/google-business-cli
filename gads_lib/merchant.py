from .config import MERCHANT_CENTER_ID
from .http import get_bearer_headers, request_json

MC_BASE = "https://shoppingcontent.googleapis.com/content/v2.1"


def mc_get_account(creds):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}",
        headers=get_bearer_headers(creds),
    )


def mc_get_account_status(creds):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/accountstatuses/{MERCHANT_CENTER_ID}",
        headers=get_bearer_headers(creds),
    )


def mc_list_products(creds, max_results=50, page_token=None):
    params = {"maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/products",
        headers=get_bearer_headers(creds),
        params=params,
    )


def mc_list_product_statuses(creds, max_results=50, page_token=None):
    params = {"maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/productstatuses",
        headers=get_bearer_headers(creds),
        params=params,
    )


def mc_list_datafeeds(creds):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/datafeeds",
        headers=get_bearer_headers(creds),
    )


def mc_get_datafeed_status(creds, feed_id):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/datafeedstatuses/{feed_id}",
        headers=get_bearer_headers(creds),
    )


def mc_get_shipping(creds):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/shippingsettings/{MERCHANT_CENTER_ID}",
        headers=get_bearer_headers(creds),
    )


def mc_get_return_policy(creds):
    return request_json(
        "GET",
        f"{MC_BASE}/{MERCHANT_CENTER_ID}/returnpolicy",
        headers=get_bearer_headers(creds),
    )
