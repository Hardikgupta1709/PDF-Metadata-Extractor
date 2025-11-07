import streamlit as st
import sys
import os
import csv
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import io
import pickle
import time
from typing import Optional
import pandas as pd
import json

# Set OAuth environment variable
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# ----------------- SETUP SYS.PATH -----------------
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
parser_path = project_root / "parser"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(parser_path) not in sys.path:
    sys.path.insert(0, str(parser_path))

# ----------------- IMPORTS -----------------
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

try:
    # Try importing from parser directory (without src prefix)
    from src.parser.image_extractor import extract_payment_info_from_image, format_payment_details
    from src.parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
    from src.parser.email_extractor import extract_full_text, find_emails
    print("✅ All local modules imported successfully")
except ImportError as e:
    try:
        # Fallback: try with src prefix
        from src.parser.image_extractor import extract_payment_info_from_image, format_payment_details
        from src.parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
        from src.parser.email_extractor import extract_full_text, find_emails
        print("✅ All local modules imported successfully (via src)")
    except ImportError as e2:
        st.error(f"**Failed to import local modules!** Details: {e2}")
        st.warning("📦 Make sure all dependencies are installed")
        st.info("💡 You can still use manual form filling")
        # Set dummy functions to prevent crashes
        def extract_payment_info_from_image(*args, **kwargs):
            return {}
        def format_payment_details(details):
            return "Payment extraction unavailable"
        def parse_pdf_with_grobid(*args, **kwargs):
            return None
        def extract_metadata_from_tei(*args, **kwargs):
            return {}
        def extract_full_text(*args, **kwargs):
            return ""
        def find_emails(*args, **kwargs):
            return []
        
# ----------------- ENVIRONMENT DETECTION (Must be before CONFIG) -----------------
def is_render_environment():
    """Detect if running on Render"""
    is_render = (
        os.getenv("RENDER") == "true" or 
        os.getenv("RENDER_SERVICE_NAME") is not None or
        os.getenv("RENDER_EXTERNAL_URL") is not None
    )
    print(f"🔍 Is Render Environment: {is_render}")
    return is_render

def is_streamlit_cloud():
    """Detect if running on Streamlit Cloud"""
    return os.getenv("STREAMLIT_SHARING_MODE") is not None

def is_production():
    """Check if running in production"""
    return is_render_environment() or is_streamlit_cloud()

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Research Paper Submission", page_icon="📄", layout="wide")

# --- Main Config ---
ADMIN_PIN = os.getenv("ADMIN_PIN", "123456")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
SUBMISSIONS_FOLDER = "submitted_papers"
SUBMISSIONS_FILE = "submissions.csv"

# --- OAuth Config - MATCHES YOUR RENDER VARIABLE NAMES EXACTLY ---
# Priority: Use WEB_* names first (as shown in your Render screenshot)
# Fallback to OAUTH_* for backward compatibility
OAUTH_REFRESH_TOKEN = os.getenv("OAUTH_REFRESH_TOKEN") or os.getenv("WEB_REFRESH_TOKEN") or ""
OAUTH_CLIENT_ID = os.getenv("WEB_CLIENT_ID", "") or os.getenv("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("WEB_CLIENT_SECRET", "") or os.getenv("OAUTH_CLIENT_SECRET", "")
OAUTH_TOKEN_URI = os.getenv("WEB_TOKEN_URI", "") or os.getenv("OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token")

# Local development OAuth config
CLIENT_SECRET_FILE = "client_secret.json"
OAUTH_PORT = int(os.getenv("PORT", "8502"))
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_PORT}"

# Scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# --- Google Services Config ---
GOOGLE_SHEETS_ENABLED = True
GOOGLE_DRIVE_ENABLED = True
GOOGLE_SHEET_NAME = "Research Paper Submissions"
GOOGLE_DRIVE_FOLDER = "Research Paper Submissions - Detailed"

# Google Drive and Sheets IDs from environment
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# Email Configuration
SUBMISSION_DRIVE_EMAIL = os.getenv("SUBMISSION_DRIVE_EMAIL", "")

# Headless mode configuration
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Token settings for local development
TOKEN_DIR = ".streamlit"
TOKEN_FILE = Path(TOKEN_DIR) / "google_token.pickle"
TOKEN_EXPIRY_DAYS = 7

# ----------------- SESSION STATE INIT -----------------
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'metadata': None,
        'extracted': False,
        'admin_authenticated': False,
        'show_success': False,
        'grobid_server': "https://kermitt2-grobid.hf.space",
        'google_creds': None,
        'payment_details': {},
        'token_expiry_date': None,
        'show_oauth_ui': False,
        'oauth_error': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ----------------- OAUTH CREDENTIALS (WORKS EVERYWHERE) -----------------
def get_credentials_from_refresh_token():
    """
    Get credentials from refresh token stored in environment variables.
    This works on Render/production without expiry issues.
    """
    try:
        refresh_token = OAUTH_REFRESH_TOKEN
        client_id = OAUTH_CLIENT_ID
        client_secret = OAUTH_CLIENT_SECRET
        token_uri = OAUTH_TOKEN_URI
        
        # Enhanced debug logging
        print("\n=== OAuth Configuration Check ===")
        print(f"Environment: {'Production (Render)' if is_production() else 'Local Development'}")
        print(f"OAUTH_REFRESH_TOKEN: {'✓ Present' if refresh_token else '✗ MISSING'} ({len(refresh_token)} chars)")
        
        if refresh_token and len(refresh_token) > 20:
            print(f"  Preview: {refresh_token[:20]}...{refresh_token[-10:]}")
        
        print(f"OAUTH_CLIENT_ID: {'✓ Present' if client_id else '✗ MISSING'}")
        if client_id and len(client_id) > 20:
            print(f"  Preview: {client_id[:30]}...")
        
        print(f"OAUTH_CLIENT_SECRET: {'✓ Present' if client_secret else '✗ MISSING'} ({len(client_secret)} chars)")
        print(f"OAUTH_TOKEN_URI: {token_uri}")
        
        if not all([refresh_token, client_id, client_secret]):
            error_msg = "❌ Missing OAuth credentials in environment variables"
            missing = []
            if not refresh_token:
                missing.append("OAUTH_REFRESH_TOKEN")
            if not client_id:
                missing.append("WEB_CLIENT_ID")
            if not client_secret:
                missing.append("WEB_CLIENT_SECRET")
            
            error_msg += f"\nMissing: {', '.join(missing)}"
            print(error_msg)
            st.session_state.oauth_error = error_msg
            return None
        
        # Validate token format - refresh tokens should be 50+ characters
        if len(refresh_token) < 50:
            error_msg = f"❌ OAUTH_REFRESH_TOKEN appears invalid (too short: {len(refresh_token)} chars, expected: 100+)"
            print(error_msg)
            st.session_state.oauth_error = error_msg
            return None
        
        # Create credentials from refresh token
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        
        # Refresh to get access token
        print("🔄 Attempting to refresh OAuth token...")
        creds.refresh(Request())
        print("✅ OAuth token refreshed successfully!")
        st.session_state.oauth_error = None
        return creds
        
    except Exception as e:
        error_msg = f"❌ OAuth Error: {str(e)}"
        print(error_msg)
        print("\n=== Troubleshooting Tips ===")
        print("1. Make sure you generated credentials locally FIRST")
        print("2. The refresh token expires if not used within 6 months")
        print("3. Check that all OAuth environment variables are correctly copied")
        print("4. Verify the credentials are from the same Google Cloud project")
        print("5. Try regenerating the refresh token locally")
        
        st.session_state.oauth_error = str(e)
        return None


# ----------------- LOCAL OAUTH TOKEN MANAGEMENT -----------------
def save_token(creds):
    """Saves OAuth credentials with timestamp (LOCAL ONLY)"""
    os.makedirs(TOKEN_DIR, exist_ok=True)
    expiry_date = datetime.now() + timedelta(days=TOKEN_EXPIRY_DAYS)
    with open(TOKEN_FILE, "wb") as f:
        pickle.dump({
            "creds": creds, 
            "timestamp": datetime.now(),
            "expiry_date": expiry_date
        }, f)
    st.session_state.token_expiry_date = expiry_date
    return expiry_date

def load_token():
    """Loads OAuth credentials and checks expiry (LOCAL ONLY)"""
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "rb") as f:
                data = pickle.load(f)
                creds = data.get("creds")
                timestamp = data.get("timestamp")
                expiry_date = data.get("expiry_date")
                
                if timestamp:
                    days_old = (datetime.now() - timestamp).days
                    if days_old >= TOKEN_EXPIRY_DAYS:
                        return None, None, None, "expired"
                
                st.session_state.token_expiry_date = expiry_date
                return creds, timestamp, expiry_date, "valid"
        except Exception as e:
            return None, None, None, "error"
    return None, None, None, "not_found"

def get_token_status():
    """Get detailed token status for display (LOCAL ONLY)"""
    if not TOKEN_FILE.exists():
        return {
            "status": "not_connected",
            "message": "Not connected to Google",
            "color": "red",
            "days_left": 0
        }
    
    creds, timestamp, expiry_date, status = load_token()
    
    if status == "expired":
        return {
            "status": "expired",
            "message": "Token expired - reconnect required",
            "color": "red",
            "days_left": 0
        }
    
    if status == "error" or not creds:
        return {
            "status": "error",
            "message": "Token corrupted - reconnect required",
            "color": "orange",
            "days_left": 0
        }
    
    if timestamp:
        days_old = (datetime.now() - timestamp).days
        days_left = TOKEN_EXPIRY_DAYS - days_old
        
        if days_left <= 0:
            return {
                "status": "expired",
                "message": "Token expired - reconnect required",
                "color": "red",
                "days_left": 0
            }
        elif days_left <= 2:
            return {
                "status": "expiring_soon",
                "message": f"⚠️ Expires in {days_left} day(s) - reconnect soon",
                "color": "orange",
                "days_left": days_left,
                "expiry_date": expiry_date
            }
        else:
            return {
                "status": "active",
                "message": f"✅ Active - {days_left} days remaining",
                "color": "green",
                "days_left": days_left,
                "expiry_date": expiry_date
            }
    
    return {
        "status": "unknown",
        "message": "Unknown token state",
        "color": "gray",
        "days_left": 0
    }

def clear_token():
    """Clears OAuth token (LOCAL ONLY)"""
    if TOKEN_FILE.exists():
        try:
            os.remove(TOKEN_FILE)
        except OSError:
            pass
    if "google_creds" in st.session_state:
        st.session_state.google_creds = None
    if "token_expiry_date" in st.session_state:
        st.session_state.token_expiry_date = None
    st.success("🔌 Disconnected from Google")
    time.sleep(1)
    st.rerun()

def get_oauth_credentials_local(interactive: bool = True) -> Optional[object]:
    """Get OAuth credentials for local development with 7-day expiry"""
    
    # Check session state first
    if st.session_state.google_creds:
        creds = st.session_state.google_creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_token(creds)
                st.session_state.google_creds = creds
                return creds
            except:
                st.session_state.google_creds = None
                if interactive:
                    st.error("❌ Token refresh failed - reconnection required")
        else:
            return creds
    
    # Try loading from file
    creds, timestamp, expiry_date, status = load_token()
    
    if status == "expired":
        if interactive:
            st.error(f"🔒 Your Google token expired after {TOKEN_EXPIRY_DAYS} days")
            st.warning("Please reconnect to continue using Google services")
        clear_token()
        return None
    
    if status == "valid" and creds:
        try:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            save_token(creds)
            st.session_state.google_creds = creds
            return creds
        except:
            if interactive:
                st.error("❌ Token refresh failed - reconnection required")
            creds = None
    
    # No valid credentials - start OAuth flow
    if not interactive:
        return None
    
    if not os.path.exists(CLIENT_SECRET_FILE):
        st.error(f"❌ **Missing `{CLIENT_SECRET_FILE}`!**")
        st.info("Download from Google Cloud Console and place in project root")
        return None
    
    # Try local server flow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=OAUTH_PORT, prompt="consent", open_browser=True)
        expiry_date = save_token(creds)
        st.session_state.google_creds = creds
        
        # Display success WITHOUT rerun
        st.success(f"✅ Connected! Token valid until {expiry_date.strftime('%B %d, %Y')}")
        
        # ALWAYS SHOW credentials - don't hide in expander
        st.markdown("---")
        st.markdown("### 🔧 **Copy These to Render Environment Variables**")
        st.markdown("**Set these EXACT variable names in Render:**")
        st.code(f"""OAUTH_REFRESH_TOKEN={creds.refresh_token}
WEB_CLIENT_ID={creds.client_id}
WEB_CLIENT_SECRET={creds.client_secret}
WEB_TOKEN_URI={creds.token_uri}
GOOGLE_SHEET_ID=<your_sheet_id_here>
GOOGLE_DRIVE_FOLDER_ID=<your_folder_id_here>""", language="bash")
        st.warning("⚠️ Make sure to copy the FULL refresh_token (it's very long!)")
        st.info("💡 These credentials allow Render to access your Google Drive without expiring!")
        st.markdown("---")
        
        # DON'T rerun - let user see the credentials
        return creds
        
    except Exception as e:
        # Manual flow fallback
        st.warning("⚠️ Automatic auth failed. Using manual flow.")
        
        if 'oauth_flow' not in st.session_state:
            try:
                flow = Flow.from_client_secrets_file(
                    CLIENT_SECRET_FILE,
                    scopes=SCOPES,
                    redirect_uri=OAUTH_REDIRECT_URI
                )
                auth_url, state = flow.authorization_url(
                    access_type="offline",
                    prompt="consent",
                    include_granted_scopes="true"
                )
                st.session_state.oauth_flow = flow
                st.session_state.oauth_state = state
                st.session_state.oauth_auth_url = auth_url
            except Exception as e:
                st.error(f"Failed to initialize OAuth: {e}")
                return None
        
        # Display authorization UI
        st.markdown("---")
        st.markdown("### 🔐 Manual Authorization Required")
        st.markdown("#### Step 1: Authorize")
        st.markdown(f"[🔗 **Click here to authorize with Google**]({st.session_state.oauth_auth_url})")
        
        st.markdown("#### Step 2: Copy URL")
        st.info(f"""
        After authorizing:
        1. Google will redirect you to `localhost:{OAUTH_PORT}`
        2. Your browser will show "This site can't be reached" - **This is normal!**
        3. Copy the **entire URL** from your browser's address bar
        4. It will look like: `http://localhost:{OAUTH_PORT}/?state=...&code=...`
        """)
        
        st.markdown("#### Step 3: Paste URL Below")
        auth_response = st.text_input(
            "Paste the full redirect URL here:",
            key="oauth_url_input",
            placeholder=f"http://localhost:{OAUTH_PORT}/?state=...&code=..."
        )
        
        col1, col2 = st.columns([3, 1])
        with col2:
            submit_btn = st.button("✅ Connect", type="primary", use_container_width=True)
        
        if submit_btn:
            if not auth_response or "code=" not in auth_response:
                st.error("❌ Invalid URL. Make sure you copied the complete URL.")
                return None
            
            try:
                with st.spinner("🔄 Connecting to Google..."):
                    flow = st.session_state.oauth_flow
                    flow.fetch_token(authorization_response=auth_response)
                    creds = flow.credentials
                    
                    expiry_date = save_token(creds)
                    st.session_state.google_creds = creds
                    
                    # Clear OAuth session state
                    del st.session_state.oauth_flow
                    del st.session_state.oauth_state
                    del st.session_state.oauth_auth_url
                    
                    st.success(f"✅ Authorization complete! Token valid until {expiry_date.strftime('%B %d, %Y')}")
                    
                    # ALWAYS SHOW credentials - don't hide in expander
                    st.markdown("---")
                    st.markdown("### 🔧 **Copy These to Render Environment Variables**")
                    st.markdown("**Set these EXACT variable names in Render:**")
                    st.code(f"""OAUTH_REFRESH_TOKEN={creds.refresh_token}
WEB_CLIENT_ID={creds.client_id}
WEB_CLIENT_SECRET={creds.client_secret}
WEB_TOKEN_URI={creds.token_uri}
GOOGLE_SHEET_ID=<your_sheet_id_here>
GOOGLE_DRIVE_FOLDER_ID=<your_folder_id_here>""", language="bash")
                    st.warning("⚠️ Make sure to copy the FULL refresh_token (it's very long!)")
                    st.info("💡 These credentials allow Render to access your Google Drive without expiring!")
                    st.markdown("---")
                    
                    # DON'T rerun - let user see the credentials
                    return creds
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")
                return None
        
        return None

def get_google_credentials(interactive: bool = True):
    """
    Smart credential getter:
    - Production: Uses refresh token from environment (NO EXPIRY)
    - Local: Uses OAuth with 7-day expiry for convenience
    """
    if is_production():
        # PRODUCTION: Use refresh token from environment
        print("🚀 Production environment detected (Render)")
        creds = get_credentials_from_refresh_token()
        
        if not creds and interactive:
            st.error("❌ OAuth Configuration Failed")
            
            if st.session_state.oauth_error:
                st.error(f"Error: {st.session_state.oauth_error}")
            
            with st.expander("🔧 How to Fix OAuth Configuration"):
                st.markdown("""
                ### The refresh token is invalid or expired. Here's how to fix it:
                
                #### Step 1: Generate New Credentials Locally
                1. Run this app on your **local computer** (not on Render)
                2. Make sure you have `client_secret.json` in your project folder
                3. Click "Connect with Google" in the sidebar
                4. Complete the authorization
                5. Copy the credentials shown in the expandable section
                
                #### Step 2: Update Render Environment Variables
                Add these EXACT variable names in your Render dashboard:
                
                ```
                OAUTH_REFRESH_TOKEN=<paste the FULL token here - it's very long!>
                WEB_CLIENT_ID=<paste client id here>
                WEB_CLIENT_SECRET=<paste client secret here>
                WEB_TOKEN_URI=https://oauth2.googleapis.com/token
                GOOGLE_SHEET_ID=<your sheet id>
                GOOGLE_DRIVE_FOLDER_ID=<your folder id>
                ```
                
                #### Step 3: Manual Deploy
                After updating environment variables, click "Manual Deploy" in Render.
                
                #### Common Issues:
                - ❌ **Invalid Grant**: Refresh token expired or revoked
                - ❌ **Missing Variables**: Check all variables are set (especially OAUTH_REFRESH_TOKEN)
                - ❌ **Wrong Credentials**: Must use OAuth credentials, not API keys
                - ❌ **Copy/Paste Error**: Ensure no extra spaces or line breaks, copy the FULL token
                - ❌ **Variable Names**: Must match exactly (WEB_CLIENT_ID, not OAUTH_CLIENT_ID)
                
                #### Why This Happens:
                - Refresh tokens can expire after 6 months of inactivity
                - Changing Google Cloud settings can invalidate tokens
                - Revoking access in Google Account settings invalidates tokens
                """)
                
            st.warning("⚠️ App will work in LOCAL mode only (no Google Drive sync)")
            return None
        
        return creds
    else:
        # LOCAL: Use OAuth with local token file
        print("💻 Local development environment detected")
        return get_oauth_credentials_local(interactive=interactive)

# ----------------- GOOGLE API SERVICES -----------------
def build_drive_service(creds):
    return build("drive", "v3", credentials=creds)

def build_sheets_service(creds):
    return build("sheets", "v4", credentials=creds)

# ----------------- LOCAL STORAGE & CSV -----------------
def init_csv():
    if not os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Submission ID", "Timestamp", "Paper Title", "Authors",
                "Email", "Research Area", "Type",
                "Transaction ID", "Amount", "Payment Method", "Payment Date", "UPI ID",
                "Local PDF Path", "Local Image Path",
                "Drive Document Link", "Drive Folder Link"
            ])
        
        if is_production():
            print("⚠️ WARNING: CSV storage is ephemeral on Render. Data will be lost on restart!")
            print("💡 Google Sheets integration is REQUIRED for persistent storage")

def init_storage():
    os.makedirs(SUBMISSIONS_FOLDER, exist_ok=True)

def save_files_locally(pdf_file, image_file, submission_id, author_name):
    try:
        clean_author = author_name.split(";")[0].strip().replace(" ", "_")[:30]
        folder_name = f"{submission_id}_{clean_author}"
        submission_path = Path(SUBMISSIONS_FOLDER) / folder_name
        os.makedirs(submission_path, exist_ok=True)

        pdf_path = submission_path / pdf_file.name
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getvalue())

        image_path = submission_path / image_file.name
        with open(image_path, "wb") as f:
            f.write(image_file.getvalue())

        return {"pdf_path": str(pdf_path), "image_path": str(image_path), "folder_path": str(submission_path)}
    except Exception as e:
        st.error(f"Error saving locally: {e}")
        return None

def append_to_csv(data):
    with open(SUBMISSIONS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            data["submission_id"], data["timestamp"], data["title"],
            data["authors"], data["corresponding_email"],
            data["research_area"], data["submission_type"],
            data.get("transaction_id", ""), data.get("amount", ""),
            data.get("payment_method", ""), data.get("payment_date", ""),
            data.get("upi_id", ""),
            data.get("pdf_path", ""), data.get("image_path", ""),
            data.get("drive_doc_link", ""), data.get("drive_folder_link", "")
        ])

# ----------------- DRIVE OPERATIONS -----------------
def get_or_create_main_drive_folder(drive_service):
    try:
        if GOOGLE_DRIVE_FOLDER_ID:
            try:
                folder = drive_service.files().get(
                    fileId=GOOGLE_DRIVE_FOLDER_ID,
                    fields='id, name'
                ).execute()
                return GOOGLE_DRIVE_FOLDER_ID
            except:
                pass
        
        query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
        folders = results.get("files", [])
        if folders:
            return folders[0]["id"]
        
        metadata = {"name": GOOGLE_DRIVE_FOLDER, "mimeType": "application/vnd.google-apps.folder"}
        created = drive_service.files().create(body=metadata, fields="id").execute()
        return created.get("id")
    except Exception as e:
        st.error(f"Drive folder error: {e}")
        return None

def create_drive_folder_for_submission(drive_service, main_folder_id, submission_id, author_name):
    try:
        clean_author = author_name.split(";")[0].strip().replace(" ", "_")[:30]
        folder_name = f"{submission_id}_{clean_author}"
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [main_folder_id]
        }
        folder = drive_service.files().create(body=metadata, fields="id, webViewLink").execute()
        return folder.get("id"), folder.get("webViewLink")
    except Exception as e:
        st.error(f"Cannot create submission folder: {e}")
        return None, None

def upload_files_to_drive(drive_service, folder_id, pdf_file, image_file):
    file_links = {}
    try:
        pdf_media = MediaIoBaseUpload(io.BytesIO(pdf_file.getvalue()), mimetype="application/pdf", resumable=True)
        pdf_metadata = {"name": pdf_file.name, "parents": [folder_id]}
        pdf_res = drive_service.files().create(body=pdf_metadata, media_body=pdf_media, fields="id, webViewLink").execute()
        file_links["pdf_link"] = pdf_res.get("webViewLink")

        image_mime = image_file.type
        image_media = MediaIoBaseUpload(io.BytesIO(image_file.getvalue()), mimetype=image_mime, resumable=True)
        image_metadata = {"name": image_file.name, "parents": [folder_id]}
        img_res = drive_service.files().create(body=image_metadata, media_body=image_media, fields="id, webViewLink").execute()
        file_links["image_link"] = img_res.get("webViewLink")

        return file_links
    except Exception as e:
        st.error(f"Drive upload error: {e}")
        return None

def create_detailed_google_doc(drive_service, folder_id, submission_data, file_links):
    try:
        summary = f"""
RESEARCH PAPER SUBMISSION DETAILS
{'=' * 60}

SUBMISSION ID: {submission_data['submission_id']}
DATE: {submission_data['timestamp']}

Title: {submission_data['title']}
Authors: {submission_data['authors']}
Email: {submission_data['corresponding_email']}
Affiliations: {submission_data.get('affiliations', 'N/A')}

Research Area: {submission_data['research_area']}
Type: {submission_data['submission_type']}

--- PAYMENT ---
Transaction ID: {submission_data.get('transaction_id', 'N/A')}
Amount: ₹{submission_data.get('amount', 'N/A')}
Method: {submission_data.get('payment_method', 'N/A')}
Date: {submission_data.get('payment_date', 'N/A')}
UPI: {submission_data.get('upi_id', 'N/A')}

--- ABSTRACT ---
{submission_data.get('abstract', 'N/A')}

--- KEYWORDS ---
{submission_data.get('keywords', 'N/A')}

--- FILES ---
PDF: {file_links.get('pdf_link', 'N/A')}
Receipt: {file_links.get('image_link', 'N/A')}
"""
        media = MediaIoBaseUpload(io.BytesIO(summary.encode('utf-8')), mimetype='text/plain')
        meta = {
            "name": f"{submission_data['submission_id']}_Details.txt",
            "parents": [folder_id],
            "mimeType": "text/plain"
        }
        doc = drive_service.files().create(body=meta, media_body=media, fields="id, webViewLink").execute()
        return doc.get("webViewLink")
    except Exception as e:
        st.error(f"Error creating doc: {e}")
        return None

def append_to_google_sheets(sheets_service, submission_data, doc_link, folder_link):
    try:
        if not SHEET_ID:
            st.warning("⚠️ Sheet ID not configured")
            return False

        row = [
            submission_data["submission_id"],
            submission_data["timestamp"],
            submission_data["title"],
            submission_data["authors"],
            submission_data["corresponding_email"],
            submission_data["research_area"],
            submission_data["submission_type"],
            submission_data.get("transaction_id", ""),
            submission_data.get("amount", ""),
            submission_data.get("payment_method", ""),
            doc_link or "N/A",
            folder_link or "N/A",
        ]
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="Sheet1!A:L",
            valueInputOption="RAW",
            body={"values": [row]}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Sheets error: {e}")
        return False

def upload_complete_submission(creds, pdf_file, image_file, submission_data):
    try:
        drive_service = build_drive_service(creds)
        main_folder_id = get_or_create_main_drive_folder(drive_service)
        if not main_folder_id:
            return None

        folder_id, folder_link = create_drive_folder_for_submission(
            drive_service, main_folder_id, submission_data['submission_id'], submission_data['authors']
        )
        if not folder_id:
            return None

        file_links = upload_files_to_drive(drive_service, folder_id, pdf_file, image_file) or {}
        doc_link = create_detailed_google_doc(drive_service, folder_id, submission_data, file_links)

        sheets_ok = False
        if GOOGLE_SHEETS_ENABLED:
            sheets_service = build_sheets_service(creds)
            sheets_ok = append_to_google_sheets(sheets_service, submission_data, doc_link, folder_link)

        return {
            "folder_link": folder_link,
            "doc_link": doc_link,
            "pdf_link": file_links.get("pdf_link"),
            "image_link": file_links.get("image_link"),
            "sheets_ok": sheets_ok
        }
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# ----------------- UTILITIES -----------------
def extract_affiliations_from_tei(tei_xml: str) -> list:
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(tei_xml)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        affiliations = []
        for affil in root.findall('.//tei:affiliation', ns):
            org_name = affil.find('.//tei:orgName', ns)
            if org_name is not None and org_name.text:
                affiliations.append(org_name.text)
        return list(set(affiliations))
    except:
        return []

def count_submissions():
    if not os.path.exists(SUBMISSIONS_FILE):
        return 0
    try:
        with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1
    except:
        return 0

# ----------------- INIT -----------------
init_csv()
init_storage()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state.admin_authenticated:
        with st.form("admin_login_form"):
            pin_input = st.text_input("Enter PIN", type="password")
            if st.form_submit_button("🔓 Unlock"):
                if pin_input == ADMIN_PIN:
                    st.session_state.admin_authenticated = True
                    st.success("✅ Authenticated!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Wrong PIN")
    else:
        st.success("✅ Admin Mode")
        if st.button("🔒 Lock"):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.markdown("---")
        st.subheader("☁️ Google Connection")
        
        if is_production():
            # PRODUCTION MODE - Using refresh token
            st.info("🚀 Production (Render/Cloud)")
            st.caption("Using OAuth Refresh Token")
            
            creds = get_credentials_from_refresh_token()
            if creds:
                st.success("✅ Connected via Refresh Token")
                st.caption("No expiry - always active!")
            else:
                st.error("❌ Not Connected")
                st.warning("⚠️ OAuth credentials missing or invalid")
                
                with st.expander("📋 Setup Instructions for Render"):
                    st.markdown("""
                    ### Step 1: Authorize Locally First
                    1. Run this app **locally** on your computer
                    2. Click "Connect with Google" below
                    3. Authorize with your Google account
                    4. Copy the credentials shown in the expandable section
                    
                    ### Step 2: Add to Render Environment Variables
                    Set these **EXACT** names in your Render dashboard:
                    ```
                    OAUTH_REFRESH_TOKEN=<your_refresh_token>
                    WEB_CLIENT_ID=<your_client_id>
                    WEB_CLIENT_SECRET=<your_client_secret>
                    WEB_TOKEN_URI=https://oauth2.googleapis.com/token
                    GOOGLE_SHEET_ID=<your_sheet_id>
                    GOOGLE_DRIVE_FOLDER_ID=<your_folder_id>
                    ```
                    
                    ### Step 3: Redeploy on Render
                    Click "Manual Deploy" - your app will now connect automatically!
                    
                    ### Important Notes:
                    - The refresh token is VERY long (100+ characters) - copy it completely!
                    - Variable names must match EXACTLY
                    - No extra spaces or line breaks
                    """)
                
                st.info("💡 Authorize locally first, then deploy to Render with the refresh token")
        
        else:
            # LOCAL MODE - Using token file
            st.info("💻 Local Development")
            
            token_status = get_token_status()
            
            if token_status["status"] == "not_connected":
                st.warning("⚠️ Not Connected")
            elif token_status["status"] == "expired":
                st.error("🔒 Token Expired")
                st.warning(f"{token_status['message']}")
            elif token_status["status"] == "expiring_soon":
                st.warning(f"⏰ {token_status['message']}")
                if token_status.get("expiry_date"):
                    st.caption(f"Expires: {token_status['expiry_date'].strftime('%B %d, %Y')}")
            elif token_status["status"] == "active":
                st.success(f"✅ {token_status['message']}")
                if token_status.get("expiry_date"):
                    st.caption(f"Valid until: {token_status['expiry_date'].strftime('%B %d, %Y')}")
            
            # Connection controls
            if st.session_state.google_creds or token_status["status"] == "active":
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔌 Disconnect", use_container_width=True, key="disconnect_btn"):
                        clear_token()
                with col2:
                    if st.button("🔄 Refresh", use_container_width=True, key="refresh_btn"):
                        st.rerun()
            else:
                if st.button("🔗 Connect with Google", use_container_width=True, type="primary", key="connect_btn"):
                    st.session_state.show_oauth_ui = True
                    st.rerun()

        # Debug info for admin
        if st.session_state.admin_authenticated:
            with st.expander("🔍 Debug Environment Variables"):
                st.code(f"""
Environment: {'Production (Render)' if is_production() else 'Local Development'}
RENDER: {os.getenv('RENDER', 'Not set')}
HEADLESS: {os.getenv('HEADLESS', 'Not set')}

OAuth Configuration:
OAUTH_REFRESH_TOKEN: {'✓ Set' if OAUTH_REFRESH_TOKEN else '✗ Missing'} ({len(OAUTH_REFRESH_TOKEN)} chars)
WEB_CLIENT_ID: {'✓ Set' if OAUTH_CLIENT_ID else '✗ Missing'}
WEB_CLIENT_SECRET: {'✓ Set' if OAUTH_CLIENT_SECRET else '✗ Missing'} ({len(OAUTH_CLIENT_SECRET)} chars)
WEB_TOKEN_URI: {OAUTH_TOKEN_URI}

Google Services:
GOOGLE_SHEET_ID: {'✓ Set' if SHEET_ID else '✗ Missing'}
GOOGLE_DRIVE_FOLDER_ID: {'✓ Set' if GOOGLE_DRIVE_FOLDER_ID else '✗ Missing'}
                """)

        st.markdown("---")
        st.subheader("📊 Dashboard")
        st.metric("Total Submissions", count_submissions())
        
        if st.button("📋 View All", use_container_width=True):
            if os.path.exists(SUBMISSIONS_FILE):
                try:
                    df = pd.read_csv(SUBMISSIONS_FILE)
                    if len(df) > 0:
                        st.dataframe(df, use_container_width=True, height=400)
                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Download CSV",
                            csv_data,
                            f"submissions_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("📭 No submissions yet")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    with st.expander("🔍 Debug"):
                        try:
                            with open(SUBMISSIONS_FILE, 'r') as f:
                                st.text(f.read())
                        except:
                            pass
            else:
                st.info("📭 No submissions file found")

        st.markdown("---")
        st.subheader("⚙️ Settings")
        st.session_state.grobid_server = st.text_input(
            "GROBID Server",
            value=st.session_state.grobid_server
        )

# ----------------- MAIN UI -----------------
st.title("Trust-NET Paper Submission")
st.markdown("Upload your paper and payment receipt")

# OAuth UI
if st.session_state.show_oauth_ui and not st.session_state.google_creds:
    st.markdown("---")
    get_oauth_credentials_local(interactive=True)
    if st.button("Cancel Authorization", key="cancel_oauth"):
        st.session_state.show_oauth_ui = False
        if 'oauth_flow' in st.session_state:
            del st.session_state.oauth_flow
        if 'oauth_state' in st.session_state:
            del st.session_state.oauth_state
        if 'oauth_auth_url' in st.session_state:
            del st.session_state.oauth_auth_url
        st.rerun()
    st.stop()

if st.session_state.show_success:
    st.success(" **Submission successful!**")
    st.info("✅ All details saved. Admin will review shortly.")
    if st.button("➕ Submit Another"):
        st.session_state.show_success = False
        st.session_state.metadata = None
        st.session_state.extracted = False
        st.session_state.payment_details = {}
        st.rerun()
    st.stop()

st.markdown("---")
st.subheader(" Step 1: Upload Files")

col1, col2 = st.columns(2)
with col1:
    st.markdown("####  Research Paper")
    uploaded_pdf = st.file_uploader("Upload PDF *", type=['pdf'], key="pdf")

with col2:
    st.markdown("#### Transaction Receipt")
    uploaded_image = st.file_uploader("Upload receipt *", type=['jpg','jpeg','png','pdf'], key="img")

if uploaded_pdf:
    col1.success(f" {uploaded_pdf.name}")

if uploaded_image:
    col2.success(f"{uploaded_image.name}")
    if uploaded_image.type.startswith("image"):
        col2.image(uploaded_image, width=200)

# EXTRACTION LOGIC
if uploaded_pdf and uploaded_image:
    st.markdown("---")
    st.subheader(" Step 2: Extract Information")
    
    col_extract1, col_extract2 = st.columns(2)
    
    with col_extract1:
        st.markdown("##### 📄 Extract Paper Metadata")
    if st.button("🤖 Auto-Fill from PDF", type="primary", use_container_width=True, key="autofill_pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_pdf.getvalue())
            tmp_path = tmp.name
        
        try:
            with st.spinner("🔄 Extracting metadata from PDF..."):
                # Parse with GROBID
                tei_xml = parse_pdf_with_grobid(tmp_path, st.session_state.grobid_server)
                
                if not tei_xml:
                    raise ValueError("GROBID returned empty response. Server might be down.")
                
                # DEBUG: Show TEI XML structure (only for admin)
                if st.session_state.admin_authenticated:
                    with st.expander("🔍 Debug: TEI XML Preview"):
                        st.text(tei_xml[:1000] + "...")
                        if st.button("📥 Download Full TEI XML"):
                            st.download_button(
                                "Download TEI XML",
                                tei_xml,
                                f"debug_tei_{uploaded_pdf.name}.xml",
                                "text/xml"
                            )
                
                # Extract metadata with debug mode
                metadata = extract_metadata_from_tei(tei_xml, debug=True)
                
                # Extract affiliations (uses same TEI XML)
                from xml.etree import ElementTree as ET
                root = ET.fromstring(tei_xml)
                ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
                affiliations = root.findall('.//tei:affiliation', ns)
                affil_list = []
                for affil in affiliations:
                    org_name = affil.find('.//tei:orgName', ns)
                    if org_name is not None and org_name.text:
                        affil_list.append(org_name.text.strip())
                metadata['affiliations'] = list(set(affil_list))
                
                # Extract emails from PDF text
                metadata['emails'] = find_emails(extract_full_text(tmp_path))
                
                # Store in session state
                st.session_state.metadata = metadata
                st.session_state.extracted = True
                
                st.success("✅ PDF metadata extracted!")
                
                # Show what was extracted
                with st.expander("📊 Extraction Summary", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if metadata.get('title'):
                            st.metric("Title", "✅ Found")
                        else:
                            st.metric("Title", "❌ Not Found")
                    with col2:
                        st.metric("Authors", len(metadata.get('authors', [])))
                    with col3:
                        st.metric("Keywords", len(metadata.get('keywords', [])))
                    
                    if metadata.get('title'):
                        st.info(f"📄 **Title:** {metadata['title'][:150]}...")
                    else:
                        st.warning("⚠️ Title not found. You'll need to enter it manually.")
                    
                    if metadata.get('abstract'):
                        st.info(f"📝 **Abstract:** {metadata['abstract'][:150]}...")
                    else:
                        st.warning("⚠️ Abstract not found. You'll need to enter it manually.")
                    
                    if metadata.get('authors'):
                        st.info(f"👥 **Authors:** {', '.join(metadata['authors'][:3])}{'...' if len(metadata['authors']) > 3 else ''}")
                
                # Show debug info if title is missing (for admin only)
                if not metadata.get('title') and st.session_state.admin_authenticated:
                    with st.expander("🐛 Debug: Why title wasn't extracted"):
                        st.warning("The GROBID parser couldn't find a title in the PDF.")
                        st.info("""
                        **Common reasons:**
                        1. PDF is an image-based scan (not searchable text)
                        2. Title is in an unusual format or location
                        3. PDF has complex formatting or security
                        
                        **Solutions:**
                        - Try a different PDF
                        - Enter the title manually below
                        - Check the TEI XML debug output above
                        """)
                
                # AUTO-RERUN to show filled form
                time.sleep(0.5)
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Extraction failed: {e}")
            st.info("💡 You can fill the form manually")
            
            # Enhanced error info for admin
            if st.session_state.admin_authenticated:
                with st.expander("🐛 Error Details"):
                    st.code(str(e))
                    st.info("""
                    **Troubleshooting:**
                    1. Check GROBID server is running
                    2. Try a different PDF
                    3. Verify PDF is not password-protected
                    4. Check internet connection to GROBID server
                    """)
            
            # Set empty metadata for manual entry
            if not st.session_state.metadata:
                st.session_state.metadata = {
                    'title': '',
                    'authors': [],
                    'abstract': '',
                    'keywords': [],
                    'affiliations': [],
                    'emails': []
                }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    with col_extract2:
        st.markdown("##### Extract Payment Details")
        if st.button(" Extract from Receipt", type="primary", use_container_width=True, key="extract_payment"):
            try:
                with st.spinner(" Extracting payment info..."):
                    uploaded_image.seek(0)
                    payment_details = extract_payment_info_from_image(
                        uploaded_image,
                        use_tesseract=True,
                        use_easyocr=False
                    )
                    st.session_state.payment_details = payment_details
                    
                    if payment_details.get("transaction_id"):
                        st.success(" Payment details extracted!")
                        st.info(format_payment_details(payment_details))
                        
                        # AUTO-RERUN to show filled form
                        st.rerun()
                    else:
                        st.warning(" Could not extract all details.")
                        if payment_details.get("raw_text"):
                            with st.expander("🔍 View Extracted Text"):
                                st.text(payment_details["raw_text"])
            except Exception as e:
                st.error(f" Extraction failed: {e}")
                st.info("💡 You can enter payment details manually")
    
    # Show extraction status
    if st.session_state.extracted or st.session_state.payment_details:
        st.markdown("---")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            if st.session_state.extracted:
                st.success(" PDF metadata extracted - Form auto-filled below!")
            else:
                st.info(" PDF extraction pending (optional)")
        with status_col2:
            if st.session_state.payment_details.get("transaction_id"):
                st.success("Payment details extracted - Form auto-filled below!")
            else:
                st.info("⏭️ Payment extraction pending (optional)")

    # FORM SECTION
    st.markdown("---")
    st.subheader("Step 3: Complete Submission Form")
    
    if st.session_state.extracted:
        st.success("Form auto-filled with extracted data! Please review and complete any missing fields.")
    else:
        st.info("💡 Fill out the form manually or use auto-extraction above")
    
    # Get metadata from session state (will be populated after extraction)
    metadata = st.session_state.get('metadata') or {}
    payment_details = st.session_state.get('payment_details') or {}

    with st.form("submission_form", clear_on_submit=False):
        st.markdown("####  Paper Details")
        
        # AUTO-FILLED: Title
        title = st.text_input(
            "Title *", 
            value=metadata.get('title', ''),
            help="Extracted from PDF" if metadata.get('title') else "Enter paper title"
        )
        
        # AUTO-FILLED: Authors (convert list to semicolon-separated string)
        authors_value = ""
        if metadata.get('authors'):
            if isinstance(metadata['authors'], list):
                authors_value = "; ".join(metadata['authors'])
            else:
                authors_value = metadata['authors']
        
        authors = st.text_area(
            "Authors (semicolon separated) *", 
            value=authors_value,
            height=80,
            help="Extracted from PDF" if authors_value else "Enter authors separated by semicolons"
        )

        st.markdown("#### Contact Information")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # AUTO-FILLED: Email (use first email from list)
            emails_list = metadata.get('emails', [])
            default_email = emails_list[0] if emails_list else ""
            
            email = st.text_input(
                "Corresponding Email *", 
                value=default_email,
                help="Extracted from PDF" if default_email else "Enter corresponding author email"
            )
        
        with col_c2:
            # Display all found emails
            all_emails_display = "; ".join(emails_list) if emails_list else ""
            all_emails = st.text_area(
                "All Found Emails", 
                value=all_emails_display, 
                height=80, 
                disabled=True,
                help="All emails found in the PDF"
            )

        # AUTO-FILLED: Affiliations (convert list to semicolon-separated string)
        affiliations_value = ""
        if metadata.get('affiliations'):
            if isinstance(metadata['affiliations'], list):
                affiliations_value = "; ".join(metadata['affiliations'])
            else:
                affiliations_value = metadata['affiliations']
        
        affiliations = st.text_area(
            "Affiliations (semicolon separated) *", 
            value=affiliations_value,
            height=80,
            help="Extracted from PDF" if affiliations_value else "Enter affiliations separated by semicolons"
        )

        st.markdown("####  Payment Information")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            # AUTO-FILLED: Transaction ID
            transaction_id = st.text_input(
                "Transaction ID *", 
                value=payment_details.get('transaction_id', ''),
                help="Extracted from receipt" if payment_details.get('transaction_id') else "Enter transaction ID"
            )
            
            # AUTO-FILLED: Amount
            amount = st.text_input(
                "Amount Paid (₹) *", 
                value=payment_details.get('amount', ''),
                help="Extracted from receipt" if payment_details.get('amount') else "Enter amount paid"
            )
        
        with col_t2:
            # AUTO-FILLED: Payment Method
            payment_method = st.text_input(
                "Payment Method", 
                value=payment_details.get('payment_method', ''), 
                placeholder="UPI/Card/Net Banking",
                help="Extracted from receipt" if payment_details.get('payment_method') else "Enter payment method"
            )
            
            # AUTO-FILLED: Payment Date
            payment_date = st.text_input(
                "Payment Date", 
                value=payment_details.get('date', ''), 
                placeholder="DD-MM-YYYY",
                help="Extracted from receipt" if payment_details.get('date') else "Enter payment date"
            )
        
        # AUTO-FILLED: UPI ID
        upi_id = st.text_input(
            "UPI ID (if applicable)", 
            value=payment_details.get('upi_id', ''),
            help="Extracted from receipt" if payment_details.get('upi_id') else "Enter UPI ID if applicable"
        )

        st.markdown("#### Abstract & Keywords")
        
        # AUTO-FILLED: Abstract
        abstract = st.text_area(
            "Abstract *", 
            value=metadata.get('abstract', ''), 
            height=150,
            help="Extracted from PDF" if metadata.get('abstract') else "Enter paper abstract"
        )
        
        # AUTO-FILLED: Keywords (convert list to comma-separated string)
        keywords_value = ""
        if metadata.get('keywords'):
            if isinstance(metadata['keywords'], list):
                keywords_value = ", ".join(metadata['keywords'])
            else:
                keywords_value = metadata['keywords']
        
        keywords = st.text_input(
            "Keywords (comma separated) *", 
            value=keywords_value,
            help="Extracted from PDF" if keywords_value else "Enter keywords separated by commas"
        )

        st.markdown("####  Classification")
        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            area = st.selectbox(
                "Research Area *", 
                [
                    "Select...", 
                    "Computer Science", 
                    "Artificial Intelligence", 
                    "Machine Learning", 
                    "Data Science", 
                    "Physics", 
                    "Chemistry", 
                    "Biology", 
                    "Mathematics", 
                    "Engineering", 
                    "Medicine", 
                    "Other"
                ]
            )
        with col_cl2:
            sub_type = st.selectbox(
                "Submission Type *", 
                [
                    "Select...", 
                    "Full Paper", 
                    "Short Paper", 
                    "Poster", 
                    "Extended Abstract", 
                    "Review", 
                    "Case Study"
                ]
            )

        comments = st.text_area("Additional Comments (optional)", height=80)
        
        st.markdown("---")
        consent = st.checkbox("I confirm all information is accurate and I have the right to submit this work *")
        
        st.markdown("")
        col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
        with col_submit2:
            submitted = st.form_submit_button("🚀 **SUBMIT PAPER**", type="primary", use_container_width=True)
            errors = []
            if not title or not title.strip(): 
                errors.append("Title")
            if not authors or not authors.strip(): 
                errors.append("Authors")
            if not email or not email.strip() or '@' not in email: 
                errors.append("Valid Email")
            if not affiliations or not affiliations.strip(): 
                errors.append("Affiliations")
            if not abstract or not abstract.strip(): 
                errors.append("Abstract")
            if not keywords or not keywords.strip(): 
                errors.append("Keywords")
            if area == "Select...": 
                errors.append("Research Area")
            if sub_type == "Select...": 
                errors.append("Submission Type")
            if not transaction_id or not transaction_id.strip(): 
                errors.append("Transaction ID")
            if not amount or not amount.strip(): 
                errors.append("Amount")
            if not consent: 
                errors.append("Consent checkbox")

            if errors:
                st.error(f" **Please complete the following required fields:** {', '.join(errors)}")
            else:
                submission_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                def safe_strip(value):
                    return value.strip() if value else ""
                
                submission_data = {
                    'submission_id': submission_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': safe_strip(title),
                    'authors': safe_strip(authors),
                    'corresponding_email': safe_strip(email),
                    'all_emails': all_emails_display or "",
                    'affiliations': safe_strip(affiliations),
                    'abstract': safe_strip(abstract),
                    'keywords': safe_strip(keywords),
                    'research_area': area,
                    'submission_type': sub_type,
                    'comments': safe_strip(comments),
                    'pdf_filename': uploaded_pdf.name,
                    'image_filename': uploaded_image.name,
                    'transaction_id': safe_strip(transaction_id),
                    'amount': safe_strip(amount),
                    'payment_method': safe_strip(payment_method),
                    'payment_date': safe_strip(payment_date),
                    'upi_id': safe_strip(upi_id)
                }

                with st.spinner("Saving files locally..."):
                    local_data = save_files_locally(uploaded_pdf, uploaded_image, submission_id, authors.strip())

                if local_data:
                    submission_data.update({
                        'pdf_path': local_data['pdf_path'],
                        'image_path': local_data['image_path']
                    })
                    st.success(" Files saved locally")
                else:
                    st.error(" Could not save files locally")
                    st.stop()
                
                google_creds = get_google_credentials(interactive=False)
                if GOOGLE_DRIVE_ENABLED and google_creds:
                    with st.spinner("☁️ Uploading to Google Drive & Sheets..."):
                        drive_data = upload_complete_submission(
                            google_creds, uploaded_pdf, uploaded_image, submission_data
                        )
                        if drive_data:
                            submission_data.update({
                                'drive_doc_link': drive_data.get('doc_link'),
                                'drive_folder_link': drive_data.get('folder_link')
                            })
                            st.success("✅ Uploaded to Google Drive & Sheets!")
                        else:
                            st.warning("⚠️ Drive upload failed. Files saved locally.")
                elif GOOGLE_DRIVE_ENABLED:
                    st.warning("⚠️ Google not connected. Files saved locally only.")
                    if is_production():
                        st.error(" CRITICAL: Google Drive is not configured on Render!")
                        st.info("💡 Files are saved temporarily but will be LOST on restart")
                    else:
                        st.info("💡 Admin can connect Google Drive from the sidebar")

                try:
                    append_to_csv(submission_data)
                    st.success("✅ Logged to local CSV")
                except Exception as e:
                    st.error(f"❌ CSV logging error: {e}")

                st.session_state.show_success = True
                st.rerun()

else:
    st.info("👆 Please upload both your research paper (PDF) and transaction receipt to begin")
    
    with st.expander("📋 Submission Requirements"):
        st.markdown("""
        **Required Documents:**
        - ✅ Research paper in PDF format
        - ✅ Payment receipt (screenshot or PDF)
        
        **Required Information:**
        - Paper title, authors, and affiliations
        - Corresponding author's email
        - Abstract and keywords
        - Research area and paper type
        - Transaction ID and payment amount
        
        **Optional Features:**
        - 🤖 Auto-extract metadata from PDF using GROBID
        - 🔍 Auto-extract payment details from receipt
        - ☁️ Automatic upload to Google Drive (if admin configured)
        """)

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Developed by SDC - Hardik Gupta</div>", unsafe_allow_html=True)
