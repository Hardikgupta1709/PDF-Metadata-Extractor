import os
import json
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

# Try to load service account JSON (optional - don't fail if missing)
service_account_info = None
try:
    service_account_json = os.environ.get("SERVICE_ACCOUNT_JSON")
    if service_account_json:
        service_account_info = json.loads(service_account_json)
        print("✅ SERVICE_ACCOUNT_JSON loaded successfully")
    else:
        print("ℹ️ SERVICE_ACCOUNT_JSON not found - using individual env vars or OAuth")
except json.JSONDecodeError as e:
    print(f"⚠️ Warning: Invalid JSON in SERVICE_ACCOUNT_JSON: {e}")
    print("ℹ️ Will try individual environment variables instead")
except Exception as e:
    print(f"⚠️ Warning: Could not load SERVICE_ACCOUNT_JSON: {e}")
    print("ℹ️ Will try individual environment variables instead")

# Configuration dictionary
config = {
    "service_account_info": service_account_info,
    "web_client_id": os.environ.get("WEB_CLIENT_ID", ""),
    "web_client_secret": os.environ.get("WEB_CLIENT_SECRET", ""),
    "web_auth_uri": os.environ.get("WEB_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "web_token_uri": os.environ.get("WEB_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "admin_email": os.environ.get("ADMIN_EMAIL", ""),
    "google_drive_folder_id": os.environ.get("GOOGLE_DRIVE_FOLDER_ID", ""),
    "google_sheet_id": os.environ.get("GOOGLE_SHEET_ID", ""),
    "port": os.environ.get("PORT", "8502"),
    "headless": os.environ.get("HEADLESS", "true"),
    "gather_usage_stats": os.environ.get("GATHERUSAGESTATS", "false"),
}
