import os
import json
from dotenv import load_dotenv

load_dotenv()

# Load service account JSON with error handling
try:
    service_account_json = os.environ.get("SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        raise ValueError("SERVICE_ACCOUNT_JSON environment variable is not set")
    service_account_info = json.loads(service_account_json)
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in SERVICE_ACCOUNT_JSON: {e}")
except KeyError:
    raise ValueError("SERVICE_ACCOUNT_JSON environment variable is missing")

# Load other required environment variables
required_vars = [
    "WEB_CLIENT_ID",
    "WEB_CLIENT_SECRET", 
    "WEB_AUTH_URI",
    "WEB_TOKEN_URI",
    "ADMIN_EMAIL",
    "GOOGLE_DRIVE_FOLDER_ID",
    "GOOGLE_SHEET_ID"
]

missing_vars = [var for var in required_vars if var not in os.environ]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

web_client_id = os.environ["WEB_CLIENT_ID"]
web_client_secret = os.environ["WEB_CLIENT_SECRET"]
web_auth_uri = os.environ["WEB_AUTH_URI"]
web_token_uri = os.environ["WEB_TOKEN_URI"]
admin_email = os.environ["ADMIN_EMAIL"]
google_drive_folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
google_sheet_id = os.environ["GOOGLE_SHEET_ID"]

# Optional settings with defaults
port = os.environ.get("PORT", "8502")
headless = os.environ.get("HEADLESS", "true")
gather_usage_stats = os.environ.get("GATHERUSAGESTATS", "false")

config = {
    "service_account_info": service_account_info,
    "web_client_id": web_client_id,
    "web_client_secret": web_client_secret,
    "web_auth_uri": web_auth_uri,
    "web_token_uri": web_token_uri,
    "admin_email": admin_email,
    "google_drive_folder_id": google_drive_folder_id,
    "google_sheet_id": google_sheet_id,
    "port": port,
    "headless": headless,
    "gather_usage_stats": gather_usage_stats,
}
