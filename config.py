import os
import json

# Load service account JSON directly from environment
service_account_info = json.loads(os.environ["service_account_json"])

# Load other environment variables
web_client_id = os.environ["web_client_id"]
web_client_secret = os.environ["web_client_secret"]
web_auth_uri = os.environ["web_auth_uri"]
web_token_uri = os.environ["web_token_uri"]
admin_email = os.environ["admin_email"]
google_drive_folder_id = os.environ["google_drive_folder_id"]
google_sheet_id = os.environ["google_sheet_id"]

# Optional: defaults for server/browser settings
port = os.environ.get("port", "8502")
headless = os.environ.get("headless", "true")
gather_usage_stats = os.environ.get("gatherusagestats", "false")

# Export a dictionary if you want to import it easily elsewhere
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
