"""Internal library for the Google Business CLI."""

__version__ = "2.1.0"

from .config import (
    PROJECT_ROOT,
    DB_PATH,
    CREDS_PATH,
    SNAPSHOTS_DIR,
    DEV_TOKEN,
    LOGIN_CUSTOMER_ID,
    CUSTOMER_ID,
    API_VERSION,
    MERCHANT_CENTER_ID,
    GA4_PROPERTY_ID,
    TZ_NAME,
    CURRENCY,
)
from .auth import get_credentials
from .ads import run_gaql
from .db import get_db
from .gbp import (
    gbp_delete_reply,
    gbp_get_location,
    gbp_list_accounts,
    gbp_list_locations,
    gbp_list_reviews,
    gbp_reply_review,
)
from .merchant import (
    mc_get_account,
    mc_get_account_status,
    mc_get_datafeed_status,
    mc_get_return_policy,
    mc_get_shipping,
    mc_list_datafeeds,
    mc_list_product_statuses,
    mc_list_products,
)
from .ga4 import (
    ga4_get_metadata,
    ga4_run_realtime_report,
    ga4_run_report,
)
from .output import flatten, print_json, print_table
from .timeutil import now_local, today_local
