"""
Configuration file for Research Paper Submission System
This file is OPTIONAL - app.py reads directly from environment variables.
Keep this file for reference or if you want centralized config management.
"""

import os
import json
from dotenv import load_dotenv

# Load .env file (for local development only)
load_dotenv()

# Try to load service account JSON (optional - legacy support)
service_account_info = None
try:
    service_account_json = os.environ.get("SERVICE_ACCOUNT_JSON")
    if service_account_json:
        service_account_info = json.loads(service_account_json)
        print("✅ SERVICE_ACCOUNT_JSON loaded successfully")
    else:
        print("ℹ️ SERVICE_ACCOUNT_JSON not found - using OAuth instead (recommended)")
except json.JSONDecodeError as e:
    print(f"⚠️ Warning: Invalid JSON in SERVICE_ACCOUNT_JSON: {e}")
    print("ℹ️ Will use OAuth credentials instead")
except Exception as e:
    print(f"⚠️ Warning: Could not load SERVICE_ACCOUNT_JSON: {e}")
    print("ℹ️ Will use OAuth credentials instead")

# Configuration dictionary
# NOTE: app.py reads directly from os.environ, so this is just for reference
config = {
    # Service Account (Legacy - not recommended)
    "service_account_info": service_account_info,
    
    # OAuth Configuration (RECOMMENDED for Render deployment)
    # These match your Render environment variable names EXACTLY
    "oauth_refresh_token": os.environ.get("OAUTH_REFRESH_TOKEN", ""),
    "web_client_id": os.environ.get("WEB_CLIENT_ID", ""),
    "web_client_secret": os.environ.get("WEB_CLIENT_SECRET", ""),
    "web_auth_uri": os.environ.get("WEB_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "web_token_uri": os.environ.get("WEB_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    
    # Admin Configuration
    "admin_email": os.environ.get("ADMIN_EMAIL", ""),
    "admin_pin": os.environ.get("ADMIN_PIN", "123456"),
    
    # Google Services
    "google_drive_folder_id": os.environ.get("GOOGLE_DRIVE_FOLDER_ID", ""),
    "google_sheet_id": os.environ.get("GOOGLE_SHEET_ID", ""),
    
    # Server Configuration
    "port": os.environ.get("PORT", "8502"),
    "headless": os.environ.get("HEADLESS", "true"),
    "gather_usage_stats": os.environ.get("GATHERUSAGESTATS", "false"),
    
    # Environment Detection
    "is_render": os.environ.get("RENDER") == "true",
    "is_production": os.environ.get("RENDER") == "true" or os.environ.get("STREAMLIT_SHARING_MODE") is not None,
}

# Print configuration status (helpful for debugging)
if __name__ == "__main__":
    print("\n=== Configuration Status ===")
    print(f"Environment: {'Production' if config['is_production'] else 'Development'}")
    print(f"Render: {config['is_render']}")
    print("\nOAuth Configuration:")
    print(f"  OAUTH_REFRESH_TOKEN: {'✓ Set' if config['oauth_refresh_token'] else '✗ Missing'} ({len(config['oauth_refresh_token'])} chars)")
    print(f"  WEB_CLIENT_ID: {'✓ Set' if config['web_client_id'] else '✗ Missing'}")
    print(f"  WEB_CLIENT_SECRET: {'✓ Set' if config['web_client_secret'] else '✗ Missing'} ({len(config['web_client_secret'])} chars)")
    print(f"  WEB_TOKEN_URI: {config['web_token_uri']}")
    print("\nGoogle Services:")
    print(f"  GOOGLE_SHEET_ID: {'✓ Set' if config['google_sheet_id'] else '✗ Missing'}")
    print(f"  GOOGLE_DRIVE_FOLDER_ID: {'✓ Set' if config['google_drive_folder_id'] else '✗ Missing'}")
    print("\nAdmin:")
    print(f"  ADMIN_EMAIL: {'✓ Set' if config['admin_email'] else '✗ Missing'}")
    print(f"  ADMIN_PIN: {'✓ Set' if config['admin_pin'] else '✗ Using default'}")
