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
