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
from config import config

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
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

try:
    from src.parser.image_extractor import extract_payment_info_from_image, format_payment_details
    from src.parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
    from src.parser.email_extractor import extract_full_text, find_emails
except ImportError as e:
    st.error(f"**Failed to import local modules!** Details: {e}")
    st.stop()

# ----------------- CONFIG -----------------
st.set_page_config(page_title="Research Paper Submission", page_icon="📄", layout="wide")

# --- Main Config ---
ADMIN_PIN = os.getenv("ADMIN_PIN", "123456")
SUBMISSIONS_FOLDER = "submitted_papers"
SUBMISSIONS_FILE = "submissions.csv"

# --- OAuth Config ---
CLIENT_SECRET_FILE = "client_secret.json"
OAUTH_PORT = 8502
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
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# Token settings - ENHANCED
TOKEN_DIR = ".streamlit"
TOKEN_FILE = Path(TOKEN_DIR) / "google_token.pickle"
TOKEN_EXPIRY_DAYS = 7  # 7-day expiry

# Sheet ID
try:
    SHEET_ID = st.secrets.get("google_sheet_id", os.getenv("GOOGLE_SHEET_ID", ""))
except:
    SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# ----------------- SESSION STATE INIT -----------------
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'extracted' not in st.session_state:
    st.session_state.extracted = False
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'show_success' not in st.session_state:
    st.session_state.show_success = False
if 'grobid_server' not in st.session_state:
    st.session_state.grobid_server = "https://kermitt2-grobid.hf.space"
if "google_creds" not in st.session_state:
    st.session_state.google_creds = None
if 'payment_details' not in st.session_state:
    st.session_state.payment_details = {}
if 'token_expiry_date' not in st.session_state:
    st.session_state.token_expiry_date = None

# ----------------- ENHANCED TOKEN MANAGEMENT -----------------
def save_token(creds):
    """Saves OAuth credentials with timestamp"""
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
    """Loads OAuth credentials and checks expiry"""
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "rb") as f:
                data = pickle.load(f)
                creds = data.get("creds")
                timestamp = data.get("timestamp")
                expiry_date = data.get("expiry_date")
                
                # Calculate days since creation
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
    """Get detailed token status for display"""
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
    """Clears OAuth token"""
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

def get_oauth_credentials(interactive: bool = True) -> Optional[object]:
    """Get OAuth credentials with 7-day expiry enforcement"""
    
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

    # Try local server flow first
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=OAUTH_PORT, prompt="consent", open_browser=True)
        expiry_date = save_token(creds)
        st.session_state.google_creds = creds
        st.success(f"✅ Connected! Token valid until {expiry_date.strftime('%B %d, %Y')}")
        time.sleep(2)
        st.rerun()
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
                    time.sleep(2)
                    st.rerun()
                    return creds
            except Exception as e:
                st.error(f"❌ Connection failed: {str(e)}")
                return None
        
        return None

def get_service_account_credentials():
    """Get service account credentials for Render/production"""
    try:
        # Try environment variables
        if os.getenv('GCP_TYPE'):
            creds_dict = {
                "type": os.getenv('GCP_TYPE'),
                "project_id": os.getenv('GCP_PROJECT_ID'),
                "private_key_id": os.getenv('GCP_PRIVATE_KEY_ID'),
                "private_key": os.getenv('GCP_PRIVATE_KEY'),
                "client_email": os.getenv('GCP_CLIENT_EMAIL'),
                "client_id": os.getenv('GCP_CLIENT_ID'),
                "auth_uri": os.getenv('GCP_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                "token_uri": os.getenv('GCP_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                "auth_provider_x509_cert_url": os.getenv('GCP_AUTH_PROVIDER_CERT_URL'),
                "client_x509_cert_url": os.getenv('GCP_CLIENT_CERT_URL'),
                "universe_domain": os.getenv('GCP_UNIVERSE_DOMAIN', 'googleapis.com')
            }
            return ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            return ServiceAccountCredentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), 
                scopes=SCOPES
            )
        return None
    except Exception as e:
        return None

def is_render_environment():
    """Detect if running on Render"""
    return os.getenv("RENDER") == "true" or os.getenv("RENDER_SERVICE_NAME") is not None

def is_streamlit_cloud():
    """Detect if running on Streamlit Cloud"""
    return os.getenv("STREAMLIT_SHARING_MODE") is not None

def get_google_credentials(interactive: bool = True):
    """Smart credential getter with 7-day expiry enforcement"""
    # Check if we're on Render or Streamlit Cloud
    if is_render_environment() or is_streamlit_cloud():
        creds = get_service_account_credentials()
        if creds:
            return creds
        else:
            if interactive:
                st.error("❌ Service account not configured for production")
            return None
    
    # Local development - use OAuth with 7-day expiry
    return get_oauth_credentials(interactive=interactive)

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

# ----------------- SIDEBAR WITH ENHANCED TOKEN STATUS -----------------
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
        
        # ENHANCED: Show detailed token status
        if is_render_environment():
            st.info("🚀 Running on Render (Service Account)")
            creds = get_service_account_credentials()
            if creds:
                st.success("✅ Service Account Active")
            else:
                st.error("❌ Service Account Not Configured")
        else:
            st.info("💻 Local Development (OAuth)")
            
            # Get token status
            token_status = get_token_status()
            
            # Display status with color coding
            if token_status["status"] == "active":
                st.success(token_status["message"])
                if token_status.get("expiry_date"):
                    st.caption(f"Valid until: {token_status['expiry_date'].strftime('%B %d, %Y at %I:%M %p')}")
                
                # Show progress bar for days remaining
                progress = token_status["days_left"] / TOKEN_EXPIRY_DAYS
                st.progress(progress)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔌 Disconnect", use_container_width=True):
                        clear_token()
                with col2:
                    if st.button("🔄 Refresh", use_container_width=True):
                        st.rerun()
                        
            elif token_status["status"] == "expiring_soon":
                st.warning(token_status["message"])
                if token_status.get("expiry_date"):
                    st.caption(f"Expires: {token_status['expiry_date'].strftime('%B %d, %Y at %I:%M %p')}")
                
                # Show progress bar
                progress = token_status["days_left"] / TOKEN_EXPIRY_DAYS
                st.progress(progress)
                
                st.info("💡 Reconnect now to avoid interruption")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Reconnect Now", type="primary", use_container_width=True):
                        clear_token()
                        st.session_state.show_oauth_ui = True
                        st.rerun()
                with col2:
                    if st.button("🔌 Disconnect", use_container_width=True):
                        clear_token()
                        
            elif token_status["status"] in ["expired", "error"]:
                st.error(token_status["message"])
                if st.button("🔗 Connect to Google", type="primary", use_container_width=True):
                    st.session_state.show_oauth_ui = True
                    st.rerun()
                    
            else:  # not_connected
                st.info("Not connected to Google Services")
                if st.button("🔗 Connect to Google", type="primary", use_container_width=True):
                    st.session_state.show_oauth_ui = True
                    st.rerun()
        
        st.markdown("---")
        st.subheader("📊 Statistics")
        total = count_submissions()
        st.metric("Total Submissions", total)
        
        st.markdown("---")
        st.subheader("⚙️ GROBID Server")
        grobid_input = st.text_input(
            "Server URL",
            value=st.session_state.grobid_server,
            help="Default: https://kermitt2-grobid.hf.space"
        )
        if st.button("Update GROBID"):
            st.session_state.grobid_server = grobid_input
            st.success("✅ Updated!")

# ----------------- OAUTH UI HANDLER -----------------
if st.session_state.admin_authenticated and st.session_state.get('show_oauth_ui', False):
    st.title("🔐 Google OAuth Connection")
    st.info("Follow the steps below to connect your Google account")
    
    creds = get_oauth_credentials(interactive=True)
    if creds:
        st.session_state.show_oauth_ui = False
        st.rerun()
    
    if st.button("❌ Cancel"):
        st.session_state.show_oauth_ui = False
        st.rerun()
    st.stop()

# ----------------- MAIN APP -----------------
st.title("📄 Research Paper Submission Portal")

# Check authentication
if not st.session_state.admin_authenticated:
    st.warning("🔒 Please authenticate via Admin Panel (sidebar) to access the submission form")
    st.stop()

# Check Google connection
creds = get_google_credentials(interactive=False)
if not creds:
    st.error("❌ Google Services not connected!")
    st.warning("Please connect to Google via the Admin Panel in the sidebar")
    st.info("💡 Click 'Connect to Google' in the sidebar to authenticate")
    st.stop()

# Show connection status at top
token_status = get_token_status()
if token_status["status"] == "expiring_soon":
    st.warning(f"⚠️ {token_status['message']} - Please reconnect via Admin Panel")
elif token_status["status"] == "active":
    st.success(f"✅ Google Connected - {token_status['days_left']} days remaining")

st.markdown("---")

# File uploaders
col1, col2 = st.columns(2)
with col1:
    pdf_file = st.file_uploader("📑 Upload Research Paper (PDF)", type=["pdf"])
with col2:
    image_file = st.file_uploader("🧾 Upload Payment Receipt", type=["png", "jpg", "jpeg"])

# Extraction button
if pdf_file and not st.session_state.extracted:
    if st.button("🔍 Extract Metadata from PDF", type="primary"):
        with st.spinner("Processing PDF with GROBID..."):
            try:
                tei_xml = parse_pdf_with_grobid(pdf_file, st.session_state.grobid_server)
                if tei_xml:
                    metadata = extract_metadata_from_tei(tei_xml)
                    metadata["affiliations"] = "; ".join(extract_affiliations_from_tei(tei_xml))
                    
                    # Extract emails
                    full_text = extract_full_text(tei_xml)
                    emails = find_emails(full_text)
                    metadata["corresponding_email"] = emails[0] if emails else ""
                    
                    st.session_state.metadata = metadata
                    st.session_state.extracted = True
                    st.success("✅ Metadata extracted!")
                    st.rerun()
                else:
                    st.error("Failed to extract metadata")
            except Exception as e:
                st.error(f"Error: {e}")

# Payment extraction
if image_file and not st.session_state.payment_details:
    if st.button("💳 Extract Payment Details", type="secondary"):
        with st.spinner("Processing payment receipt..."):
            try:
                payment_info = extract_payment_info_from_image(image_file)
                if payment_info:
                    st.session_state.payment_details = payment_info
                    st.success("✅ Payment details extracted!")
                    st.rerun()
                else:
                    st.warning("Could not extract payment details automatically")
            except Exception as e:
                st.error(f"Error: {e}")

# Display extracted payment details
if st.session_state.payment_details:
    with st.expander("💳 Extracted Payment Details", expanded=True):
        formatted = format_payment_details(st.session_state.payment_details)
        st.markdown(formatted)

# Submission form
st.markdown("---")
st.subheader("📝 Submission Form")

with st.form("submission_form"):
    meta = st.session_state.metadata or {}
    payment = st.session_state.payment_details or {}
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input("Paper Title*", value=meta.get("title", ""))
        authors = st.text_area("Authors*", value=meta.get("authors", ""), 
                               help="Separate multiple authors with semicolons")
        email = st.text_input("Corresponding Email*", value=meta.get("corresponding_email", ""))
        affiliations = st.text_area("Affiliations", value=meta.get("affiliations", ""))
    
    with col2:
        research_area = st.selectbox("Research Area*", [
            "Computer Science", "Engineering", "Medicine", 
            "Physics", "Chemistry", "Biology", "Mathematics", "Other"
        ])
        submission_type = st.selectbox("Submission Type*", [
            "Full Paper", "Short Paper", "Poster", "Workshop"
        ])
        abstract = st.text_area("Abstract", value=meta.get("abstract", ""), height=100)
        keywords = st.text_input("Keywords", value=meta.get("keywords", ""))
    
    st.markdown("#### 💰 Payment Information")
    
    col3, col4 = st.columns(2)
    with col3:
        transaction_id = st.text_input("Transaction ID*", value=payment.get("transaction_id", ""))
        amount = st.text_input("Amount (₹)*", value=payment.get("amount", ""))
    with col4:
        payment_method = st.text_input("Payment Method*", value=payment.get("payment_method", ""))
        payment_date = st.text_input("Payment Date", value=payment.get("payment_date", ""))
        upi_id = st.text_input("UPI ID", value=payment.get("upi_id", ""))
    
    submit = st.form_submit_button("🚀 Submit Paper", type="primary", use_container_width=True)
    
    if submit:
        # Validation
        if not all([pdf_file, image_file, title, authors, email, transaction_id, amount, payment_method]):
            st.error("❌ Please fill all required fields (*) and upload both files")
        else:
            # Check Google connection before submission
            creds = get_google_credentials(interactive=False)
            if not creds:
                st.error("❌ Google connection lost! Please reconnect via Admin Panel")
                st.stop()
            
            with st.spinner("📤 Submitting your paper..."):
                try:
                    # Generate submission ID
                    submission_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Prepare submission data
                    submission_data = {
                        "submission_id": submission_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "title": title,
                        "authors": authors,
                        "corresponding_email": email,
                        "affiliations": affiliations,
                        "research_area": research_area,
                        "submission_type": submission_type,
                        "abstract": abstract,
                        "keywords": keywords,
                        "transaction_id": transaction_id,
                        "amount": amount,
                        "payment_method": payment_method,
                        "payment_date": payment_date,
                        "upi_id": upi_id
                    }
                    
                    # Save locally
                    local_paths = save_files_locally(pdf_file, image_file, submission_id, authors)
                    if local_paths:
                        submission_data.update(local_paths)
                    
                    # Upload to Google
                    drive_result = upload_complete_submission(creds, pdf_file, image_file, submission_data)
                    
                    if drive_result:
                        submission_data["drive_doc_link"] = drive_result.get("doc_link", "")
                        submission_data["drive_folder_link"] = drive_result.get("folder_link", "")
                    
                    # Save to CSV
                    append_to_csv(submission_data)
                    
                    # Show success
                    st.session_state.show_success = True
                    st.session_state.last_submission = submission_data
                    st.session_state.last_drive_result = drive_result
                    
                    # Clear form
                    st.session_state.metadata = None
                    st.session_state.extracted = False
                    st.session_state.payment_details = {}
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Submission failed: {e}")

# Success message
if st.session_state.show_success:
    st.success("🎉 Paper submitted successfully!")
    
    sub_data = st.session_state.last_submission
    drive_res = st.session_state.last_drive_result
    
    st.info(f"**Submission ID:** {sub_data['submission_id']}")
    
    if drive_res:
        st.markdown("### 📁 Your Submission Links")
        col1, col2 = st.columns(2)
        with col1:
            if drive_res.get("folder_link"):
                st.markdown(f"[📂 View Folder]({drive_res['folder_link']})")
        with col2:
            if drive_res.get("doc_link"):
                st.markdown(f"[📄 View Details]({drive_res['doc_link']})")
    
    if st.button("✅ Submit Another Paper"):
        st.session_state.show_success = False
        st.session_state.last_submission = None
        st.session_state.last_drive_result = None
        st.rerun()

# Footer
st.markdown("---")
st.caption("🔒 Secure submission portal with 7-day Google OAuth renewal")