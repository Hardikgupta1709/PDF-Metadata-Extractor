# import streamlit as st
# import sys
# import os
# import csv
# import tempfile
# from pathlib import Path
# from datetime import datetime
# import io


# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 

# # Add src to path
# project_root = Path(__file__).parent
# src_path = project_root / "src"
# if str(src_path) not in sys.path:
#     sys.path.insert(0, str(src_path))

# from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
# from parser.email_extractor import extract_full_text, find_emails

# # Page configuration
# st.set_page_config(
#     page_title="Research Paper Submission",
#     page_icon="📄",
#     layout="wide"
# )

# # ==================== CONFIGURATION ====================
# ADMIN_PIN = "123456"  # ⚠️ CHANGE THIS!
# GOOGLE_SHEETS_ENABLED = True
# GOOGLE_SHEET_NAME = "Research Paper Submissions"
# GOOGLE_DRIVE_ENABLED = True
# GOOGLE_DRIVE_FOLDER = "Research Paper Submissions - Detailed"
# SUBMISSIONS_FOLDER = "submitted_papers"
# SUBMISSIONS_FILE = "submissions.csv"
# # =======================================================

# # ==================== OAUTH AUTHENTICATION ====================
# def get_drive_service_oauth():
#     """OAuth with file-based token persistence"""
#     from google_auth_oauthlib.flow import Flow
#     from googleapiclient.discovery import build
#     from google.auth.transport.requests import Request
#     import pickle
#     import os
    
#     TOKEN_FILE = '.streamlit/drive_token.pickle'
    
#     # Try to load existing token
#     creds = None
#     if os.path.exists(TOKEN_FILE):
#         try:
#             with open(TOKEN_FILE, 'rb') as token:
#                 creds = pickle.load(token)
                
#             # Check if token is still valid
#             if creds and creds.valid:
#                 service = build('drive', 'v3', credentials=creds)
#                 service.files().list(pageSize=1).execute()
#                 st.session_state.google_creds = creds
#                 return service
#             elif creds and creds.expired and creds.refresh_token:
#                 # Refresh expired token
#                 creds.refresh(Request())
#                 with open(TOKEN_FILE, 'wb') as token:
#                     pickle.dump(creds, token)
#                 st.session_state.google_creds = creds
#                 service = build('drive', 'v3', credentials=creds)
#                 return service
#         except Exception as e:
#             st.warning(f"Token issue: {str(e)}")
#             if os.path.exists(TOKEN_FILE):
#                 os.remove(TOKEN_FILE)
    
#     # Need new authorization
#     st.warning("🔐 Please authorize Google Drive access")
    
#     try:
#         client_config = {
#             "web": {
#                 "client_id": st.secrets["oauth_credentials"]["web.client_id"],
#                 "client_secret": st.secrets["oauth_credentials"]["web.client_secret"],
#                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                 "token_uri": "https://oauth2.googleapis.com/token",
#                 "redirect_uris": ["http://localhost:8501"]
#             }
#         }
        
#         scopes = [
#             'https://www.googleapis.com/auth/drive.file',
#             'https://www.googleapis.com/auth/drive'
#         ]
        
#         flow = Flow.from_client_config(
#             client_config,
#             scopes=scopes,
#             redirect_uri="http://localhost:8501"
#         )
        
#         # Generate authorization URL
#         auth_url, state = flow.authorization_url(
#             access_type='offline',
#             prompt='consent',
#             include_granted_scopes='true'
#         )
        
#         st.markdown(f"### [🔗 Click Here to Authorize Google Drive]({auth_url})")
#         st.info("📋 After authorization, **copy the entire URL** from your browser and paste below")
        
#         # Input for redirect URL
#         auth_response = st.text_input(
#             "Paste redirect URL here:",
#             key="drive_auth_input",
#             placeholder="http://localhost:8501/?state=...&code=...",
#             help="Must include ?state= and &code= parameters"
#         )
        
#         # Add a submit button
#         col1, col2 = st.columns([3, 1])
#         with col2:
#             submit_auth = st.button("✅ Connect", type="primary")
        
#         if submit_auth and auth_response:
#             if len(auth_response) < 50:
#                 st.error("❌ URL too short. Did you paste the complete URL?")
#                 return None
                
#             if not auth_response.startswith("http://localhost:8501"):
#                 st.error("❌ URL must start with http://localhost:8501")
#                 return None
                
#             if "code=" not in auth_response:
#                 st.error("❌ URL must contain authorization code (?code=...)")
#                 return None
            
#             try:
#                 with st.spinner("🔄 Connecting to Google Drive..."):
#                     # Exchange code for token
#                     flow.fetch_token(authorization_response=auth_response)
#                     creds = flow.credentials
                    
#                     # Save token to file
#                     os.makedirs('.streamlit', exist_ok=True)
#                     with open(TOKEN_FILE, 'wb') as token:
#                         pickle.dump(creds, token)
                    
#                     # Test the connection
#                     service = build('drive', 'v3', credentials=creds)
#                     result = service.files().list(pageSize=1).execute()
                    
#                     # Save to session state
#                     st.session_state.google_creds = creds
                    
#                     st.success("✅ Successfully connected to Google Drive!")
#                     st.balloons()
#                     st.info("Token saved. You won't need to authorize again unless token expires.")
                    
#                     # Force refresh
#                     import time
#                     time.sleep(1)
#                     st.rerun()
                    
#             except Exception as e:
#                 st.error(f"❌ Connection failed: {str(e)}")
#                 st.error("**Troubleshooting:**")
#                 st.error("• Make sure the URL is complete")
#                 st.error("• Try clicking the authorization link again")
#                 st.error("• Check that you're using the same Google account")
                
#                 with st.expander("🔍 Technical Details"):
#                     import traceback
#                     st.code(traceback.format_exc())
                
#                 return None
                
#     except KeyError as e:
#         st.error(f"❌ OAuth config error: {str(e)}")
#         st.error("Check your .streamlit/secrets.toml file")
#     except Exception as e:
#         st.error(f"❌ Setup error: {str(e)}")
#         with st.expander("Details"):
#             import traceback
#             st.code(traceback.format_exc())
    
#     return None
# # ==================== HELPER FUNCTIONS ====================
# def init_csv():
#     """Create CSV with headers"""
#     if not os.path.exists(SUBMISSIONS_FILE):
#         with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                 'Submission ID', 'Timestamp', 'Paper Title', 'Authors',
#                 'Email', 'Research Area', 'Type', 
#                 'Local PDF Path', 'Local Image Path',
#                 'Drive Document Link', 'Drive Folder Link'
#             ])

# def init_storage():
#     """Create local storage directory"""
#     if not os.path.exists(SUBMISSIONS_FOLDER):
#         os.makedirs(SUBMISSIONS_FOLDER)

# def save_files_locally(pdf_file, image_file, submission_id, author_name):
#     """Save files to local storage"""
#     try:
#         clean_author = author_name.split(';')[0].strip().replace(' ', '_')[:30]
#         folder_name = f"{submission_id}_{clean_author}"
#         submission_path = os.path.join(SUBMISSIONS_FOLDER, folder_name)
#         os.makedirs(submission_path, exist_ok=True)
        
#         pdf_path = os.path.join(submission_path, pdf_file.name)
#         with open(pdf_path, 'wb') as f:
#             f.write(pdf_file.getvalue())
        
#         image_path = os.path.join(submission_path, image_file.name)
#         with open(image_path, 'wb') as f:
#             f.write(image_file.getvalue())
        
#         return {'pdf_path': pdf_path, 'image_path': image_path, 'folder_path': submission_path}
#     except Exception as e:
#         st.error(f"Error saving locally: {str(e)}")
#         return None

# def create_drive_folder_for_submission(drive_service, main_folder_id, submission_id, author_name):
#     """Create a Google Drive folder for this submission"""
#     try:
#         clean_author = author_name.split(';')[0].strip().replace(' ', '_')[:30]
#         folder_name = f"{submission_id}_{clean_author}"
        
#         file_metadata = {
#             'name': folder_name,
#             'mimeType': 'application/vnd.google-apps.folder',
#             'parents': [main_folder_id]
#         }
        
#         folder = drive_service.files().create(
#             body=file_metadata,
#             fields='id, webViewLink'
#         ).execute()
        
#         return folder.get('id'), folder.get('webViewLink')
#     except Exception as e:
#         st.error(f"Error creating Drive folder: {str(e)}")
#         return None, None

# def upload_files_to_drive(drive_service, folder_id, pdf_file, image_file):
#     """Upload PDF and image to Google Drive"""
#     file_links = {}
    
#     try:
#         from googleapiclient.http import MediaIoBaseUpload
        
#         # Upload PDF
#         try:
#             st.write(f"  Uploading PDF: {pdf_file.name}")
#             pdf_metadata = {
#                 'name': pdf_file.name,
#                 'parents': [folder_id]
#             }
#             pdf_media = MediaIoBaseUpload(
#                 io.BytesIO(pdf_file.getvalue()),
#                 mimetype='application/pdf',
#                 resumable=True
#             )
#             pdf_result = drive_service.files().create(
#                 body=pdf_metadata,
#                 media_body=pdf_media,
#                 fields='id, webViewLink'
#             ).execute()
            
#             file_links['pdf_link'] = pdf_result.get('webViewLink')
#             st.write(f"  ✓ PDF uploaded")
                
#         except Exception as e:
#             st.error(f"  ❌ PDF upload failed: {str(e)}")
        
#         # Upload Image
#         try:
#             st.write(f"  Uploading image: {image_file.name}")
#             image_metadata = {
#                 'name': image_file.name,
#                 'parents': [folder_id]
#             }
            
#             # Determine MIME type
#             image_mime = 'image/jpeg'
#             if image_file.name.lower().endswith('.png'):
#                 image_mime = 'image/png'
#             elif image_file.name.lower().endswith('.pdf'):
#                 image_mime = 'application/pdf'
            
#             image_media = MediaIoBaseUpload(
#                 io.BytesIO(image_file.getvalue()),
#                 mimetype=image_mime,
#                 resumable=True
#             )
#             image_result = drive_service.files().create(
#                 body=image_metadata,
#                 media_body=image_media,
#                 fields='id, webViewLink'
#             ).execute()
            
#             file_links['image_link'] = image_result.get('webViewLink')
#             st.write(f"  ✓ Image uploaded")
                
#         except Exception as e:
#             st.error(f"  ❌ Image upload failed: {str(e)}")
        
#         return file_links if file_links else None
        
#     except Exception as e:
#         st.error(f"❌ File upload error: {str(e)}")
#         return None

# def create_detailed_google_doc(drive_service, folder_id, submission_data, file_links):
#     """Create a Google Doc with ALL submission details"""
#     try:
#         from googleapiclient.http import MediaIoBaseUpload
        
#         # Create detailed document content
#         doc_content = f"""
# RESEARCH PAPER SUBMISSION DETAILS
# {'='*60}

# SUBMISSION ID: {submission_data['submission_id']}
# SUBMISSION DATE: {submission_data['timestamp']}

# {'='*60}
# PAPER INFORMATION
# {'='*60}

# Title: {submission_data['title']}

# Authors: {submission_data['authors']}

# Author Affiliations:
# {submission_data['affiliations']}

# {'='*60}
# CONTACT INFORMATION
# {'='*60}

# Corresponding Author Email: {submission_data['corresponding_email']}

# All Co-author Emails:
# {submission_data['all_emails']}

# {'='*60}
# ABSTRACT
# {'='*60}

# {submission_data['abstract']}

# {'='*60}
# KEYWORDS & CLASSIFICATION
# {'='*60}

# Keywords: {submission_data['keywords']}

# Research Area: {submission_data['research_area']}

# Submission Type: {submission_data['submission_type']}

# {'='*60}
# ADDITIONAL COMMENTS
# {'='*60}

# {submission_data['comments'] if submission_data['comments'] else 'None'}

# {'='*60}
# ATTACHED FILES
# {'='*60}

# Research Paper PDF: {submission_data['pdf_filename']}
# Link: {file_links.get('pdf_link', 'Not available')}

# Transaction Receipt: {submission_data['image_filename']}
# Link: {file_links.get('image_link', 'Not available')}

# {'='*60}
# VERIFICATION STATUS
# {'='*60}

# Status: Pending Review
# Reviewed By: [To be filled by admin]
# Review Date: [To be filled by admin]
# Decision: [To be filled by admin]
# Comments: [To be filled by admin]

# {'='*60}
# """
        
#         # Create Google Doc
#         doc_metadata = {
#             'name': f"{submission_data['submission_id']}_Details.txt",
#             'parents': [folder_id],
#             'mimeType': 'text/plain'
#         }
        
#         media = MediaIoBaseUpload(
#             io.BytesIO(doc_content.encode('utf-8')),
#             mimetype='text/plain',
#             resumable=True
#         )
        
#         doc = drive_service.files().create(
#             body=doc_metadata,
#             media_body=media,
#             fields='id, webViewLink'
#         ).execute()
        
#         return doc.get('webViewLink')
#     except Exception as e:
#         st.error(f"Error creating document: {str(e)}")
#         return None

# def get_or_create_main_drive_folder(drive_service):
#     """Get or create main Google Drive folder"""
#     try:
#         query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
#         results = drive_service.files().list(
#             q=query,
#             spaces='drive',
#             fields='files(id, name)'
#         ).execute()
#         folders = results.get('files', [])
        
#         if folders:
#             return folders[0]['id']
        
#         # Create folder
#         file_metadata = {
#             'name': GOOGLE_DRIVE_FOLDER,
#             'mimeType': 'application/vnd.google-apps.folder'
#         }
#         folder = drive_service.files().create(
#             body=file_metadata,
#             fields='id'
#         ).execute()
        
#         return folder.get('id')
#     except Exception as e:
#         st.error(f"Error with main folder: {str(e)}")
#         return None

# # def upload_complete_submission_to_drive(pdf_file, image_file, submission_data):
# #     """Upload everything to Google Drive with detailed document using OAuth"""
# #     try:
# #         st.write("🔍 Starting Drive upload...")
        
# #         # NEW - Use OAuth instead of service account
# #         drive_service = get_drive_service_oauth()
# #         if not drive_service:
# #             st.error("❌ Please authenticate with Google Drive first")
# #             st.info("💡 Click the 'Connect Drive' button in the admin panel sidebar")
# #             return None
        
# #         st.write("✓ Connected to Drive")
        
# #         # Get main folder
# #         main_folder_id = get_or_create_main_drive_folder(drive_service)
# #         if not main_folder_id:
# #             st.error("❌ Could not create main folder")
# #             return None
        
# #         st.write(f"✓ Main folder ID: {main_folder_id}")
        
# #         # Create submission folder
# #         folder_id, folder_link = create_drive_folder_for_submission(
# #             drive_service,
# #             main_folder_id,
# #             submission_data['submission_id'],
# #             submission_data['authors']
# #         )
        
# #         if not folder_id:
# #             st.error("❌ Could not create submission folder")
# #             return None
        
# #         st.write(f"✓ Submission folder created")
        
# #         # Upload files
# #         try:
# #             file_links = upload_files_to_drive(drive_service, folder_id, pdf_file, image_file)
# #             if file_links:
# #                 st.write("✓ Files uploaded")
# #             else:
# #                 st.warning("⚠️ File upload returned None - continuing anyway")
# #                 file_links = {}
# #         except Exception as e:
# #             st.warning(f"⚠️ File upload issue: {str(e)} - continuing anyway")
# #             file_links = {}
        
# #         # Create detailed document
# #         try:
# #             doc_link = create_detailed_google_doc(drive_service, folder_id, submission_data, file_links)
# #             if doc_link:
# #                 st.write("✓ Details document created")
# #             else:
# #                 st.warning("⚠️ Could not create details document")
# #         except Exception as e:
# #             st.warning(f"⚠️ Document creation issue: {str(e)}")
# #             doc_link = None
        
# #         return {
# #             'folder_link': folder_link,
# #             'doc_link': doc_link,
# #             'pdf_link': file_links.get('pdf_link'),
# #             'image_link': file_links.get('image_link')
# #         }
        
# #     except Exception as e:
# #         st.error(f"❌ Drive upload error: {str(e)}")
# #         import traceback
# #         st.error(f"Traceback: {traceback.format_exc()}")
# #         return None
# def upload_complete_submission_to_drive(pdf_file, image_file, submission_data):
#     """Upload to Drive - returns None if not connected"""
    
#     # Check if Drive is connected
#     if 'google_creds' not in st.session_state or not st.session_state.google_creds:
#         st.warning("⚠️ Google Drive not connected. Files saved locally only.")
#         st.info("Admin: Connect Drive in sidebar to enable cloud backup.")
#         return None
    
#     try:
#         from googleapiclient.discovery import build
        
#         st.write("🔍 Starting Drive upload...")
        
#         # Use stored credentials
#         drive_service = build('drive', 'v3', credentials=st.session_state.google_creds)
        
#         st.write("✓ Connected to Drive")
        
#         # ... rest of your upload code
#         # Get main folder
#         main_folder_id = get_or_create_main_drive_folder(drive_service)
#         if not main_folder_id:
#             st.error("❌ Could not create main folder")
#             return None
        
#         st.write(f"✓ Main folder ID: {main_folder_id}")
        
#         # Create submission folder
#         folder_id, folder_link = create_drive_folder_for_submission(
#             drive_service,
#             main_folder_id,
#             submission_data['submission_id'],
#             submission_data['authors']
#         )
        
#         if not folder_id:
#             st.error("❌ Could not create submission folder")
#             return None
        
#         st.write(f"✓ Submission folder created")
        
#         # Upload files
#         try:
#             file_links = upload_files_to_drive(drive_service, folder_id, pdf_file, image_file)
#             if file_links:
#                 st.write("✓ Files uploaded")
#             else:
#                 st.warning("⚠️ File upload returned None - continuing anyway")
#                 file_links = {}
#         except Exception as e:
#             st.warning(f"⚠️ File upload issue: {str(e)} - continuing anyway")
#             file_links = {}
        
#         # Create detailed document
#         try:
#             doc_link = create_detailed_google_doc(drive_service, folder_id, submission_data, file_links)
#             if doc_link:
#                 st.write("✓ Details document created")
#             else:
#                 st.warning("⚠️ Could not create details document")
#         except Exception as e:
#             st.warning(f"⚠️ Document creation issue: {str(e)}")
#             doc_link = None
        
#         return {
#             'folder_link': folder_link,
#             'doc_link': doc_link,
#             'pdf_link': file_links.get('pdf_link'),
#             'image_link': file_links.get('image_link')
#         }

        
#     except Exception as e:
#         st.error(f"❌ Drive upload failed: {str(e)}")
#         st.info("Files are still saved locally")
#         return None

# def append_to_csv(data):
#     """Append to CSV"""
#     with open(SUBMISSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow([
#             data['submission_id'], data['timestamp'], data['title'],
#             data['authors'], data['corresponding_email'],
#             data['research_area'], data['submission_type'],
#             data.get('pdf_path', ''), data.get('image_path', ''),
#             data.get('drive_doc_link', ''), data.get('drive_folder_link', '')
#         ])

# def append_to_google_sheets(data):
#     """Append basic info to Google Sheets"""
#     try:
#         import gspread
#         from google.oauth2.service_account import Credentials

#         creds_dict = st.secrets["gcp_service_account"]
#         scopes = [
#             'https://www.googleapis.com/auth/spreadsheets',
#             'https://www.googleapis.com/auth/drive'
#         ]

#         creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
#         client = gspread.authorize(creds)
#         sheet = client.open(GOOGLE_SHEET_NAME).sheet1

#         row = [
#             data['submission_id'],
#             data['timestamp'],
#             data['title'],
#             data['authors'],
#             data['corresponding_email'],
#             data['research_area'],
#             data['submission_type'],
#             data.get('drive_doc_link', 'Not available'),
#             data.get('drive_folder_link', 'Not available')
#         ]
        
#         sheet.append_row(row)
#         return True
#     except Exception as e:
#         st.error(f"Sheets error: {str(e)}")
#         return False

# def extract_affiliations_from_tei(tei_xml: str) -> list:
#     """Extract affiliations from TEI XML"""
#     from xml.etree import ElementTree as ET
#     root = ET.fromstring(tei_xml)
#     ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
#     affiliations = []
#     for affil in root.findall('.//tei:affiliation', ns):
#         org_name = affil.find('.//tei:orgName', ns)
#         if org_name is not None and org_name.text:
#             affiliations.append(org_name.text)
#     return list(set(affiliations))

# def count_submissions():
#     """Count submissions"""
#     if not os.path.exists(SUBMISSIONS_FILE):
#         return 0
#     with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
#         return sum(1 for line in f) - 1

# # ==================== INITIALIZE ====================
# # Initialize session state
# if 'metadata' not in st.session_state:
#     st.session_state.metadata = None
# if 'extracted' not in st.session_state:
#     st.session_state.extracted = False
# if 'admin_authenticated' not in st.session_state:
#     st.session_state.admin_authenticated = False
# if 'show_success' not in st.session_state:
#     st.session_state.show_success = False
# if 'grobid_server' not in st.session_state:
#     st.session_state.grobid_server = "https://kermitt2-grobid.hf.space"

# init_csv()
# init_storage()

# # ==================== ADMIN PANEL ====================
# with st.sidebar:
#     st.header("🔐 Admin Access")
    
#     if not st.session_state.admin_authenticated:
#         with st.form("admin_login"):
#             pin_input = st.text_input("Enter PIN", type="password", max_chars=6)
#             if st.form_submit_button("🔓 Unlock"):
#                 if pin_input == ADMIN_PIN:
#                     st.session_state.admin_authenticated = True
#                     st.success("✅ Authenticated!")
#                     st.rerun()
#                 else:
#                     st.error("❌ Wrong PIN")
#     else:
#         st.success("✅ Admin Mode")
        
#         if st.button("🔒 Lock"):
#             st.session_state.admin_authenticated = False
#             st.rerun()
        
#         # Google Drive Connection Section - OUTSIDE any form
#         st.markdown("---")
#         st.subheader("☁️ Google Drive")
        
#         if 'google_creds' not in st.session_state or not st.session_state.google_creds:
#             st.warning("⚠️ Not Connected")
            
#             # Show authorization UI only when clicked
#             if 'show_drive_auth' not in st.session_state:
#                 st.session_state.show_drive_auth = False
            
#             if not st.session_state.show_drive_auth:
#                 if st.button("🔗 Connect Drive", use_container_width=True, type="primary"):
#                     st.session_state.show_drive_auth = True
#                     st.rerun()
#             else:
#                 # Show OAuth authorization
#                 try:
#                     from google_auth_oauthlib.flow import Flow
#                     from googleapiclient.discovery import build
#                     import pickle
#                     import os
                    
#                     client_config = {
#                         "web": {
#                             "client_id": st.secrets["oauth_credentials"]["web.client_id"],
#                             "client_secret": st.secrets["oauth_credentials"]["web.client_secret"],
#                             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                             "token_uri": "https://oauth2.googleapis.com/token",
#                             "redirect_uris": ["http://localhost:8501"]
#                         }
#                     }
                    
#                     scopes = [
#                         'https://www.googleapis.com/auth/drive.file',
#                         'https://www.googleapis.com/auth/drive'
#                     ]
                    
#                     # Save state to session to prevent mismatch
#                     if 'oauth_state' not in st.session_state or 'oauth_auth_url' not in st.session_state:
#                         flow = Flow.from_client_config(
#                         client_config,
#                         scopes=scopes,
#                         redirect_uri="http://localhost:8501"
#                         )
    
#                         auth_url, state = flow.authorization_url(
#                         access_type='offline',
#                         prompt='consent'
#                         )
    
#                     # Save to session state
#                         st.session_state.oauth_state = state
#                         st.session_state.oauth_auth_url = auth_url

#                     st.markdown(f"### [🔗 Authorize]({st.session_state.oauth_auth_url})")
                    
#                     auth_response = st.text_input(
#                         "Paste URL here:",
#                         key="drive_auth_url",
#                         placeholder="http://localhost:8501/?state=..."
#                     )
                    
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         if st.button("✅ Submit", key="submit_auth"):
#                             if auth_response and len(auth_response) > 50:
#                                 try:
#                                     # Recreate flow with saved state
#                                     flow = Flow.from_client_config(
#                                     client_config,
#                                     scopes=scopes,
#                                     redirect_uri="http://localhost:8501",
#                                     state=st.session_state.oauth_state  # Use saved state
#                                     )
            
#                                     flow.fetch_token(authorization_response=auth_response)
#                                     creds = flow.credentials
                                    
#                                     # Save to file
#                                     TOKEN_FILE = '.streamlit/drive_token.pickle'
#                                     os.makedirs('.streamlit', exist_ok=True)
#                                     with open(TOKEN_FILE, 'wb') as token:
#                                         pickle.dump(creds, token)
                                    
#                                     # Test connection
#                                     service = build('drive', 'v3', credentials=creds)
#                                     service.files().list(pageSize=1).execute()
                                    
#                                     st.session_state.google_creds = creds
#                                     st.session_state.show_drive_auth = False
#                                     st.success("✅ Connected!")
#                                     st.rerun()
                                    
#                                 except Exception as e:
#                                     st.error(f"Failed: {str(e)}")
#                             else:
#                                 st.error("Invalid URL")
                    
                
#                     with col2:
#                         if st.button("❌ Cancel", key="cancel_auth"):
#                             st.session_state.show_drive_auth = False
#                             # Clear OAuth state
#                             if 'oauth_state' in st.session_state:
#                                 del st.session_state.oauth_state
#                             if 'oauth_auth_url' in st.session_state:
#                                 del st.session_state.oauth_auth_url
#                             st.rerun()
                            
#                 except Exception as e:
#                     st.error(f"Error: {str(e)}")
                    
#         else:
#             st.success("✅ Connected")
            
#             col1, col2 = st.columns(2)
#             with col1:
#                 if st.button("🔓 Disconnect", use_container_width=True):
#                     st.session_state.google_creds = None
#                     TOKEN_FILE = '.streamlit/drive_token.pickle'
#                     if os.path.exists(TOKEN_FILE):
#                         os.remove(TOKEN_FILE)
#                     st.rerun()
#             with col2:
#                 if st.button("📁 Drive", use_container_width=True):
#                     st.markdown("[Open](https://drive.google.com)")
        
#         # Dashboard Section
#         st.markdown("---")
#         st.subheader("📊 Dashboard")
#         st.metric("Total Submissions", count_submissions())
        
#         if st.button("👁️ View All Submissions", use_container_width=True):
#             if os.path.exists(SUBMISSIONS_FILE):
#                 import pandas as pd
#                 df = pd.read_csv(SUBMISSIONS_FILE)
#                 st.dataframe(df, use_container_width=True, height=400)
                
#                 csv_data = df.to_csv(index=False).encode('utf-8')
#                 st.download_button(
#                     "📥 Download CSV",
#                     csv_data,
#                     f"submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
#                     "text/csv",
#                     use_container_width=True
#                 )
#             else:
#                 st.info("No submissions yet")
        
#         if st.button("🔍 View Latest", use_container_width=True):
#             if os.path.exists(SUBMISSIONS_FILE):
#                 import pandas as pd
#                 df = pd.read_csv(SUBMISSIONS_FILE)
#                 if len(df) > 0:
#                     latest = df.iloc[-1]
#                     st.json(latest.to_dict())
#                 else:
#                     st.info("No submissions yet")
        
#         # Storage Info
#         st.markdown("---")
#         st.info("💾 **Storage:** Local + Google Drive")
#         st.caption("✓ Files saved locally")
#         st.caption("✓ Details in Google Sheets")
#         st.caption("✓ Full backup in Drive")
        
#         # GROBID Configuration
#         st.markdown("---")
#         st.subheader("⚙️ Configuration")
#         st.session_state.grobid_server = st.text_input(
#             "GROBID Server URL",
#             value=st.session_state.grobid_server,
#             help="PDF parsing service"
#         )
        
#         # Drive Status
#         if GOOGLE_DRIVE_ENABLED:
#             if 'google_creds' in st.session_state and st.session_state.google_creds:
#                 st.success("☁️ Drive uploads: Enabled")
#             else:
#                 st.warning("☁️ Drive uploads: Disabled")
#                 st.caption("Connect Drive to enable")

# # ==================== MAIN FORM ====================
# st.title("📝 Research Paper Submission")
# st.markdown("Upload your paper and transaction proof")

# if st.session_state.show_success:
#     st.success("🎉 Submission successful!")
#     st.info("✅ All details saved to Google Drive. Admin will review and contact you.")
    
#     if st.button("➕ Submit Another"):
#         st.session_state.show_success = False
#         st.session_state.metadata = None
#         st.session_state.extracted = False
#         st.rerun()
#     st.stop()

# st.markdown("---")
# st.subheader("📤 Step 1: Upload Files")

# col1, col2 = st.columns(2)

# with col1:
#     st.markdown("#### 📄 Research Paper")
#     uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'], key="pdf")
#     if uploaded_pdf:
#         st.success(f"✅ {uploaded_pdf.name}")

# with col2:
#     st.markdown("#### 💳 Transaction Proof")
#     uploaded_image = st.file_uploader("Upload receipt", type=['jpg', 'jpeg', 'png', 'pdf'], key="img")
#     if uploaded_image:
#         st.success(f"✅ {uploaded_image.name}")
#         if uploaded_image.type.startswith('image'):
#             st.image(uploaded_image, width=200)

# if uploaded_pdf and uploaded_image:
#     if st.button("🤖 Auto-Fill Form", type="primary", use_container_width=True):
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
#             tmp.write(uploaded_pdf.getvalue())
#             tmp_path = tmp.name
        
#         try:
#             with st.spinner("🔄 Extracting..."):
#                 tei_xml = parse_pdf_with_grobid(tmp_path, st.session_state.grobid_server)
#                 metadata = extract_metadata_from_tei(tei_xml)
#                 metadata['affiliations'] = extract_affiliations_from_tei(tei_xml)
#                 metadata['emails'] = find_emails(extract_full_text(tmp_path))
                
#                 st.session_state.metadata = metadata
#                 st.session_state.extracted = True
#                 st.success("✅ Auto-filled!")
#         except Exception as e:
#             st.error(f"❌ Auto-fill failed: {str(e)}")
#             st.info("💡 Fill manually below")
#         finally:
#             if os.path.exists(tmp_path):
#                 os.unlink(tmp_path)

# if uploaded_pdf and uploaded_image:
#     st.markdown("---")
#     st.subheader("📋 Step 2: Complete Form")
    
#     if st.session_state.extracted:
#         st.info("✨ Auto-filled! Please review.")
    
#     metadata = st.session_state.metadata or {}
    
#     with st.form("submission"):
#         st.markdown("### 📄 Paper Details")
        
#         title = st.text_input("Title *", value=metadata.get('title', ''))
#         authors = st.text_area("Authors (semicolon separated) *", 
#                               value="; ".join(metadata.get('authors', [])),
#                               height=80)
        
#         st.markdown("### 📧 Contact")
        
#         col1, col2 = st.columns(2)
#         with col1:
#             emails_list = metadata.get('emails', [])
#             if emails_list:
#                 email = st.selectbox("Corresponding Email *", ['Select...'] + emails_list)
#                 if email == 'Select...':
#                     email = st.text_input("Or enter manually *")
#             else:
#                 email = st.text_input("Corresponding Email *")
        
#         with col2:
#             all_emails = st.text_area("All Emails (optional)",
#                                      value="; ".join(emails_list),
#                                      height=80)
        
#         affiliations = st.text_area("Affiliations *",
#                                    value="; ".join(metadata.get('affiliations', [])),
#                                    height=80)
        
#         st.markdown("### 📝 Abstract & Keywords")
#         abstract = st.text_area("Abstract *", value=metadata.get('abstract', ''), height=150)
#         keywords = st.text_input("Keywords *", value=", ".join(metadata.get('keywords', [])))
        
#         st.markdown("### 🔬 Classification")
#         col1, col2 = st.columns(2)
#         with col1:
#             area = st.selectbox("Research Area *", [
#                 "Select...", "Computer Science", "AI", "Machine Learning",
#                 "Data Science", "Physics", "Chemistry", "Biology",
#                 "Mathematics", "Engineering", "Medicine", "Other"
#             ])
#         with col2:
#             sub_type = st.selectbox("Type *", [
#                 "Select...", "Full Paper", "Short Paper", "Poster",
#                 "Extended Abstract", "Review", "Case Study"
#             ])
        
#         comments = st.text_area("Comments (optional)", height=80)
        
#         st.markdown("---")
#         consent = st.checkbox("I confirm all information is accurate *")
        
#         col1, col2, col3 = st.columns([1, 2, 1])
#         with col2:
#             submitted = st.form_submit_button("✅ Submit", type="primary", use_container_width=True)
        
#         if submitted:
#             errors = []
#             if not title.strip(): errors.append("Title")
#             if not authors.strip(): errors.append("Authors")
#             if not email.strip() or email == 'Select...': errors.append("Email")
#             if not affiliations.strip(): errors.append("Affiliations")
#             if not abstract.strip(): errors.append("Abstract")
#             if not keywords.strip(): errors.append("Keywords")
#             if area == "Select...": errors.append("Research Area")
#             if sub_type == "Select...": errors.append("Type")
#             if not consent: errors.append("Consent")
            
#             if errors:
#                 st.error(f"❌ Required: {', '.join(errors)}")
#             else:
#                 submission_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
#                 # Prepare data
#                 submission_data = {
#                     'submission_id': submission_id,
#                     'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#                     'title': title.strip(),
#                     'authors': authors.strip(),
#                     'corresponding_email': email.strip(),
#                     'all_emails': all_emails.strip(),
#                     'affiliations': affiliations.strip(),
#                     'abstract': abstract.strip(),
#                     'keywords': keywords.strip(),
#                     'research_area': area,
#                     'submission_type': sub_type,
#                     'comments': comments.strip(),
#                     'pdf_filename': uploaded_pdf.name,
#                     'image_filename': uploaded_image.name
#                 }
                
#                 # Save locally
#                 with st.spinner("💾 Saving files..."):
#                     local_data = save_files_locally(uploaded_pdf, uploaded_image, 
#                                                    submission_id, authors.strip())
                
#                 if local_data:
#                     submission_data.update({
#                         'pdf_path': local_data['pdf_path'],
#                         'image_path': local_data['image_path']
#                     })
                    
#                     # Upload to Drive with full details
#                     if GOOGLE_DRIVE_ENABLED:
#                         with st.spinner("☁️ Uploading to Google Drive..."):
#                             drive_data = upload_complete_submission_to_drive(
#                                 uploaded_pdf, uploaded_image, submission_data
#                             )
                            
#                             if drive_data:
#                                 submission_data.update({
#                                     'drive_doc_link': drive_data.get('doc_link'),
#                                     'drive_folder_link': drive_data.get('folder_link')
#                                 })
#                                 st.success("✅ Uploaded to Drive!")
                    
#                     # Save to CSV
#                     try:
#                         append_to_csv(submission_data)
#                     except Exception as e:
#                         st.error(f"CSV error: {str(e)}")
                    
#                     # Save to Sheets
#                     if GOOGLE_SHEETS_ENABLED:
#                         append_to_google_sheets(submission_data)
                    
#                     st.session_state.show_success = True
#                     st.rerun()

# st.markdown("---")
# st.markdown(
#     "<div style='text-align: center; color: gray;'>"
#     "🔒 Secure System • Full details stored in Google Drive<br>"
#     "Powered by AI & GROBID"
#     "</div>",
#     unsafe_allow_html=True
# )




import streamlit as st
import sys
import os
import csv
import tempfile
from pathlib import Path
from datetime import datetime
import io

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
from parser.email_extractor import extract_full_text, find_emails

# Page configuration
st.set_page_config(
    page_title="Research Paper Submission",
    page_icon="📄",
    layout="wide"
)

# ==================== CONFIGURATION ====================
ADMIN_PIN = "123456"  # ⚠️ CHANGE THIS!
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEET_NAME = "Research Paper Submissions"
GOOGLE_DRIVE_ENABLED = True
GOOGLE_DRIVE_FOLDER = "Research Paper Submissions"
GOOGLE_DRIVE_FOLDER_ID = "1f1YT5McP0w6Ub4rl5MT1MgjTX7s7j21j"  
SUBMISSIONS_FOLDER = "submitted_papers"
SUBMISSIONS_FILE = "submissions.csv"

# 🔑 IMPORTANT: Your dedicated submissions Gmail
# Make sure to add this to secrets.toml as well
SUBMISSIONS_DRIVE_EMAIL = st.secrets.get("submission_drive_email", "researchsubmissions.trustnet@gmail.com")
# =======================================================

# ==================== GOOGLE DRIVE SERVICE ACCOUNT ====================
def get_drive_service():
    """Get Drive service using service account - uploads to shared folder"""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        
        # Test connection
        service.files().list(pageSize=1).execute()
        
        return service
    except Exception as e:
        st.error(f"❌ Drive service error: {str(e)}")
        return None

# ==================== SETUP GUIDE ====================
def show_drive_setup_guide():
    """Show complete setup guide for folder sharing method"""
    
    st.markdown("### 🎯 Google Drive Setup Guide")
    
    st.info("""
    **What we're doing:** Setting up automatic upload to your dedicated Gmail's Drive.
    
    The service account will upload files to a folder YOU create and share with it.
    """)
    
    # Get service account email
    try:
        service_account_email = st.secrets["gcp_service_account"]["client_email"]
    except:
        st.error("❌ Service account not found in secrets.toml")
        return
    
    st.markdown("---")
    
    # Step 1
    with st.expander("📧 STEP 1: Login to Your Submissions Gmail", expanded=True):
        st.markdown(f"""
        1. Open **Google Drive** in a new tab: https://drive.google.com
        2. **Login** with your submissions account:
           ```
           {SUBMISSIONS_DRIVE_EMAIL}
           ```
        3. Make sure you're in the correct account (check top-right corner)
        """)
    
    # Step 2
    with st.expander("📁 STEP 2: Create Main Folder", expanded=True):
        st.markdown(f"""
        1. In Drive, click **"+ New"** → **"New folder"**
        2. Name it exactly:
           ```
           {GOOGLE_DRIVE_FOLDER}
           ```
        3. Press **Enter** to create
        4. The folder will appear in "My Drive"
        """)
    
    # Step 3
    with st.expander("🔗 STEP 3: Share Folder with Service Account (CRITICAL)", expanded=True):
        st.markdown(f"""
        **This is the KEY step that fixes the storage quota error!**
        
        1. **Right-click** the folder you just created
        2. Click **"Share"**
        3. In the "Add people and groups" field, paste this email:
        """)
        
        st.code(service_account_email)
        
        if st.button("📋 Copy Service Account Email"):
            st.success("☝️ Email shown above - copy it manually")
        
        st.markdown(f"""
        4. **IMPORTANT:** Change role from "Viewer" to **"Editor"**
        5. **Uncheck** "Notify people" (service accounts can't read emails)
        6. Click **"Share"** or **"Done"**
        
        ✅ Now the service account can create subfolders and upload files to YOUR Drive!
        
        💡 **Why this works:** The service account doesn't use its own storage (which doesn't exist). 
        It uses YOUR Gmail account's storage because you shared the folder with it.
        """)
    
    # Step 4
    with st.expander("🔢 STEP 4: Get Folder ID (Optional)", expanded=False):
        st.markdown(f"""
        **This makes uploads faster but is optional:**
        
        1. **Open** the folder you created in Drive
        2. Look at the URL in your browser:
           ```
           https://drive.google.com/drive/folders/XXXXXXXXXXXXX
           ```
        3. Copy the **XXXXXXXXXXXXX** part (the Folder ID)
        4. Update in your code:
           ```python
           GOOGLE_DRIVE_FOLDER_ID = "XXXXXXXXXXXXX"
           ```
        
        💡 If you skip this, the app will search for the folder by name (slightly slower).
        """)
    
    # Step 5
    with st.expander("✅ STEP 5: Verify Setup", expanded=False):
        st.markdown("""
        After completing the steps above:
        
        1. Click the **"🧪 Test Drive Setup"** button below
        2. If successful, you'll see green checkmarks
        3. Try submitting a test paper
        
        **Common issues:**
        - ❌ "Folder not found" → Check folder name spelling
        - ❌ "Permission denied" → Make sure you gave "Editor" access, not "Viewer"
        - ❌ "Storage quota exceeded" → You didn't share the folder correctly
        """)
    
    st.markdown("---")
    
    # Test button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🧪 Test Drive Setup", type="primary", use_container_width=True):
            test_drive_setup()

# ==================== TEST SETUP ====================
def test_drive_setup():
    """Test if Drive setup is working correctly"""
    
    st.markdown("### 🧪 Testing Drive Setup...")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Test 1: Service Account Connection
    status_text.text("1/5 Connecting to service account...")
    progress_bar.progress(20)
    
    drive_service = get_drive_service()
    if not drive_service:
        st.error("❌ Failed: Could not connect service account")
        st.info("Check if gcp_service_account is in secrets.toml")
        return
    
    st.success("✅ Service account connected")
    
    # Show service account email for verification
    try:
        sa_email = st.secrets["gcp_service_account"]["client_email"]
        st.info(f"📧 Service Account: {sa_email}")
        if st.button("📋 Copy Service Account Email", key="copy_sa_test"):
            st.code(sa_email)
    except:
        pass
    
    # Test 2: Search for Main Folder
    status_text.text("2/4 Looking for main folder...")
    progress_bar.progress(50)
    
    try:
        if GOOGLE_DRIVE_FOLDER_ID:
            # Try direct access
            try:
                folder = drive_service.files().get(
                    fileId=GOOGLE_DRIVE_FOLDER_ID,
                    fields='id, name'
                ).execute()
                folder_id = GOOGLE_DRIVE_FOLDER_ID
                st.success(f"✅ Found folder by ID: {folder['name']}")
            except:
                st.warning("⚠️ Folder ID not working, searching by name...")
                query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
                folders = results.get('files', [])
                if not folders:
                    st.error(f"❌ Failed: Folder '{GOOGLE_DRIVE_FOLDER}' not found")
                    st.info("💡 Create the folder and share it with the service account")
                    return
                folder_id = folders[0]['id']
                st.success(f"✅ Found folder: {folders[0]['name']}")
                st.info(f"💡 Update config: GOOGLE_DRIVE_FOLDER_ID = '{folder_id}'")
        else:
            # Search by name
            query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            if not folders:
                st.error(f"❌ Failed: Folder '{GOOGLE_DRIVE_FOLDER}' not found")
                st.info("💡 Create the folder and share it with the service account")
                return
            
            folder = folders[0]
            folder_id = folder['id']
            st.success(f"✅ Found folder: {folder['name']}")
            st.info(f"📁 Folder ID: `{folder_id}`")
            st.caption("💡 Add this to config as GOOGLE_DRIVE_FOLDER_ID for faster access")
        
    except Exception as e:
        st.error(f"❌ Failed: {str(e)}")
        return
    
    # Test 3: Check Write Permissions
    status_text.text("3/4 Testing write permissions...")
    progress_bar.progress(75)
    
    try:
        # Try to create a test file
        test_file_metadata = {
            'name': '_test_connection.txt',
            'parents': [folder_id],
            'mimeType': 'text/plain'
        }
        
        from googleapiclient.http import MediaIoBaseUpload
        
        media = MediaIoBaseUpload(
            io.BytesIO(b"Connection test successful"),
            mimetype='text/plain'
        )
        
        test_file = drive_service.files().create(
            body=test_file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        st.success("✅ Can create files in folder")
        st.success("✅ Write permissions working!")
        
        # Clean up test file
        try:
            drive_service.files().delete(fileId=test_file['id']).execute()
            st.caption("🧹 Test file cleaned up")
        except:
            pass
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ Failed: Cannot write to folder")
        
        if "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            st.error("**Problem:** Service account doesn't have Editor access")
            st.error("**Solution:** Right-click folder → Share → Add service account → Select 'Editor' role")
        elif "quota" in error_msg.lower():
            st.error("**Problem:** Storage quota error - folder not properly shared")
            st.error("**Solution:** Make sure you shared the folder FROM your Gmail account WITH the service account")
        else:
            st.error(f"Error details: {error_msg}")
        return
    
    # Test 4: Final Status
    status_text.text("4/4 Finalizing...")
    progress_bar.progress(100)
    
    st.markdown("---")
    st.success("🎉 **SETUP COMPLETE!**")
    st.balloons()
    
    st.info("✅ Your app is ready! All submissions will automatically upload to Google Drive.")
    
    # Show folder link
    try:
        folder_info = drive_service.files().get(
            fileId=folder_id,
            fields='webViewLink'
        ).execute()
        
        folder_link = folder_info.get('webViewLink')
        st.markdown(f"📁 [Open Your Submissions Folder]({folder_link})")
    except:
        pass

# ==================== HELPER FUNCTIONS ====================
def init_csv():
    """Create CSV with headers"""
    if not os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Submission ID', 'Timestamp', 'Paper Title', 'Authors',
                'Email', 'Research Area', 'Type', 
                'Local PDF Path', 'Local Image Path',
                'Drive Document Link', 'Drive Folder Link'
            ])

def init_storage():
    """Create local storage directory"""
    if not os.path.exists(SUBMISSIONS_FOLDER):
        os.makedirs(SUBMISSIONS_FOLDER)

def save_files_locally(pdf_file, image_file, submission_id, author_name):
    """Save files to local storage"""
    try:
        clean_author = author_name.split(';')[0].strip().replace(' ', '_')[:30]
        folder_name = f"{submission_id}_{clean_author}"
        submission_path = os.path.join(SUBMISSIONS_FOLDER, folder_name)
        os.makedirs(submission_path, exist_ok=True)
        
        pdf_path = os.path.join(submission_path, pdf_file.name)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_file.getvalue())
        
        image_path = os.path.join(submission_path, image_file.name)
        with open(image_path, 'wb') as f:
            f.write(image_file.getvalue())
        
        return {'pdf_path': pdf_path, 'image_path': image_path, 'folder_path': submission_path}
    except Exception as e:
        st.error(f"Error saving locally: {str(e)}")
        return None

def get_or_create_main_drive_folder(drive_service):
    """Get main Google Drive folder"""
    try:
        # If we have folder ID, use it directly (fastest)
        if GOOGLE_DRIVE_FOLDER_ID:
            try:
                folder = drive_service.files().get(
                    fileId=GOOGLE_DRIVE_FOLDER_ID,
                    fields='id, name'
                ).execute()
                st.write(f"✓ Using folder: {folder.get('name')}")
                return GOOGLE_DRIVE_FOLDER_ID
            except Exception as e:
                st.warning(f"⚠️ Configured folder ID not accessible: {str(e)}")
        
        # Search for folder by name
        query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            st.write(f"✓ Found folder: {folders[0]['name']}")
            if not GOOGLE_DRIVE_FOLDER_ID:
                st.info(f"💡 TIP: Add to config for faster access:\nGOOGLE_DRIVE_FOLDER_ID = '{folder_id}'")
            return folder_id
        
        # Folder not found
        st.error("❌ Main folder not found!")
        st.error(f"**Please create:** '{GOOGLE_DRIVE_FOLDER}'")
        st.error(f"**In account:** {SUBMISSIONS_DRIVE_EMAIL}")
        
        try:
            sa_email = st.secrets['gcp_service_account']['client_email']
            st.error(f"**Then share with:** {sa_email}")
            st.error("**Role:** Editor")
        except:
            pass
        
        return None
        
    except Exception as e:
        st.error(f"Error accessing Drive: {str(e)}")
        return None

def create_drive_folder_for_submission(drive_service, main_folder_id, submission_id, author_name):
    """Create a Google Drive folder for this submission"""
    try:
        clean_author = author_name.split(';')[0].strip().replace(' ', '_')[:30]
        folder_name = f"{submission_id}_{clean_author}"
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [main_folder_id]
        }
        
        folder = drive_service.files().create(
            body=file_metadata,
            fields='id, webViewLink'
        ).execute()
        
        return folder.get('id'), folder.get('webViewLink')
    except Exception as e:
        st.error(f"Error creating Drive folder: {str(e)}")
        return None, None

def upload_files_to_drive(drive_service, folder_id, pdf_file, image_file):
    """Upload PDF and image to Google Drive"""
    file_links = {}
    
    try:
        from googleapiclient.http import MediaIoBaseUpload
        
        # Upload PDF
        try:
            st.write(f"  Uploading PDF: {pdf_file.name}")
            pdf_metadata = {
                'name': pdf_file.name,
                'parents': [folder_id]
            }
            pdf_media = MediaIoBaseUpload(
                io.BytesIO(pdf_file.getvalue()),
                mimetype='application/pdf',
                resumable=True
            )
            pdf_result = drive_service.files().create(
                body=pdf_metadata,
                media_body=pdf_media,
                fields='id, webViewLink'
            ).execute()
            
            file_links['pdf_link'] = pdf_result.get('webViewLink')
            st.write(f"  ✓ PDF uploaded")
                
        except Exception as e:
            st.error(f"  ❌ PDF upload failed: {str(e)}")
        
        # Upload Image
        try:
            st.write(f"  Uploading image: {image_file.name}")
            image_metadata = {
                'name': image_file.name,
                'parents': [folder_id]
            }
            
            # Determine MIME type
            image_mime = 'image/jpeg'
            if image_file.name.lower().endswith('.png'):
                image_mime = 'image/png'
            elif image_file.name.lower().endswith('.pdf'):
                image_mime = 'application/pdf'
            
            image_media = MediaIoBaseUpload(
                io.BytesIO(image_file.getvalue()),
                mimetype=image_mime,
                resumable=True
            )
            image_result = drive_service.files().create(
                body=image_metadata,
                media_body=image_media,
                fields='id, webViewLink'
            ).execute()
            
            file_links['image_link'] = image_result.get('webViewLink')
            st.write(f"  ✓ Image uploaded")
                
        except Exception as e:
            st.error(f"  ❌ Image upload failed: {str(e)}")
        
        return file_links if file_links else None
        
    except Exception as e:
        st.error(f"❌ File upload error: {str(e)}")
        return None

def create_detailed_google_doc(drive_service, folder_id, submission_data, file_links):
    """Create a text document with ALL submission details"""
    try:
        from googleapiclient.http import MediaIoBaseUpload
        
        # Create detailed document content
        doc_content = f"""
RESEARCH PAPER SUBMISSION DETAILS
{'='*60}

SUBMISSION ID: {submission_data['submission_id']}
SUBMISSION DATE: {submission_data['timestamp']}

{'='*60}
PAPER INFORMATION
{'='*60}

Title: {submission_data['title']}

Authors: {submission_data['authors']}

Author Affiliations:
{submission_data['affiliations']}

{'='*60}
CONTACT INFORMATION
{'='*60}

Corresponding Author Email: {submission_data['corresponding_email']}

All Co-author Emails:
{submission_data['all_emails']}

{'='*60}
ABSTRACT
{'='*60}

{submission_data['abstract']}

{'='*60}
KEYWORDS & CLASSIFICATION
{'='*60}

Keywords: {submission_data['keywords']}

Research Area: {submission_data['research_area']}

Submission Type: {submission_data['submission_type']}

{'='*60}
ADDITIONAL COMMENTS
{'='*60}

{submission_data['comments'] if submission_data['comments'] else 'None'}

{'='*60}
ATTACHED FILES
{'='*60}

Research Paper PDF: {submission_data['pdf_filename']}
Link: {file_links.get('pdf_link', 'Not available')}

Transaction Receipt: {submission_data['image_filename']}
Link: {file_links.get('image_link', 'Not available')}

{'='*60}
VERIFICATION STATUS
{'='*60}

Status: Pending Review
Reviewed By: [To be filled by admin]
Review Date: [To be filled by admin]
Decision: [To be filled by admin]
Comments: [To be filled by admin]

{'='*60}
"""
        
        # Create text document
        doc_metadata = {
            'name': f"{submission_data['submission_id']}_Details.txt",
            'parents': [folder_id],
            'mimeType': 'text/plain'
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(doc_content.encode('utf-8')),
            mimetype='text/plain',
            resumable=True
        )
        
        doc = drive_service.files().create(
            body=doc_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return doc.get('webViewLink')
    except Exception as e:
        st.error(f"Error creating document: {str(e)}")
        return None

def upload_complete_submission_to_drive(pdf_file, image_file, submission_data):
    """Upload everything to Google Drive - automatic for all users"""
    
    try:
        st.write("🔍 Starting Drive upload...")
        
        # Get service account credentials
        drive_service = get_drive_service()
        
        if not drive_service:
            st.warning("⚠️ Drive service unavailable. Files saved locally.")
            return None
        
        st.write("✓ Connected to Drive")
        
        # Get main folder
        main_folder_id = get_or_create_main_drive_folder(drive_service)
        if not main_folder_id:
            st.error("❌ Could not access main folder")
            st.info("💡 Run the setup guide from admin panel")
            return None
        
        st.write(f"✓ Main folder ready")
        
        # Create submission folder
        folder_id, folder_link = create_drive_folder_for_submission(
            drive_service,
            main_folder_id,
            submission_data['submission_id'],
            submission_data['authors']
        )
        
        if not folder_id:
            st.error("❌ Could not create submission folder")
            return None
        
        st.write(f"✓ Submission folder created")
        
        # Upload files
        file_links = {}
        try:
            file_links = upload_files_to_drive(drive_service, folder_id, pdf_file, image_file)
            if file_links:
                st.write("✓ Files uploaded")
            else:
                st.warning("⚠️ File upload incomplete")
                file_links = {}
        except Exception as e:
            st.warning(f"⚠️ File upload issue: {str(e)}")
            file_links = {}
        
        # Create detailed document
        doc_link = None
        try:
            doc_link = create_detailed_google_doc(drive_service, folder_id, submission_data, file_links)
            if doc_link:
                st.write("✓ Details document created")
        except Exception as e:
            st.warning(f"⚠️ Document creation issue: {str(e)}")
        
        return {
            'folder_link': folder_link,
            'doc_link': doc_link,
            'pdf_link': file_links.get('pdf_link'),
            'image_link': file_links.get('image_link')
        }
        
    except Exception as e:
        st.error(f"❌ Drive upload error: {str(e)}")
        st.info("Files are saved locally")
        return None

def check_drive_setup_status():
    """Check if Drive is properly configured"""
    try:
        drive_service = get_drive_service()
        if not drive_service:
            return "❌ Service account not configured", None
        
        # Try to find the folder
        if GOOGLE_DRIVE_FOLDER_ID:
            try:
                folder = drive_service.files().get(
                    fileId=GOOGLE_DRIVE_FOLDER_ID,
                    fields='id, name, webViewLink'
                ).execute()
                folder_id = GOOGLE_DRIVE_FOLDER_ID
                folder_link = folder.get('webViewLink')
            except:
                return "⚠️ Folder ID invalid or not accessible", None
        else:
            query = f"name='{GOOGLE_DRIVE_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, webViewLink)'
            ).execute()
            
            folders = results.get('files', [])
            if not folders:
                return "❌ Folder not found or not shared", None
            
            folder = folders[0]
            folder_id = folder['id']
            folder_link = folder.get('webViewLink')
        
        # Try to create a test file to verify write access
        try:
            test_metadata = {
                'name': f'_test_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id]
            }
            
            test_folder = drive_service.files().create(
                body=test_metadata,
                fields='id'
            ).execute()
            
            # Clean up
            drive_service.files().delete(fileId=test_folder['id']).execute()
            
            return "✅ Fully configured and working", folder_link
            
        except Exception as e:
            if "permission" in str(e).lower() or "quota" in str(e).lower():
                return "⚠️ Folder found but no write permission", folder_link
            else:
                return f"⚠️ Write test failed: {str(e)}", folder_link
            
    except Exception as e:
        return f"❌ Error: {str(e)}", None

def append_to_csv(data):
    """Append to CSV"""
    with open(SUBMISSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            data['submission_id'], data['timestamp'], data['title'],
            data['authors'], data['corresponding_email'],
            data['research_area'], data['submission_type'],
            data.get('pdf_path', ''), data.get('image_path', ''),
            data.get('drive_doc_link', ''), data.get('drive_folder_link', '')
        ])

def append_to_google_sheets(data):
    """Append basic info to Google Sheets"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1

        row = [
            data['submission_id'],
            data['timestamp'],
            data['title'],
            data['authors'],
            data['corresponding_email'],
            data['research_area'],
            data['submission_type'],
            data.get('drive_doc_link', 'Not available'),
            data.get('drive_folder_link', 'Not available')
        ]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Sheets error: {str(e)}")
        return False

def extract_affiliations_from_tei(tei_xml: str) -> list:
    """Extract affiliations from TEI XML"""
    from xml.etree import ElementTree as ET
    root = ET.fromstring(tei_xml)
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    affiliations = []
    for affil in root.findall('.//tei:affiliation', ns):
        org_name = affil.find('.//tei:orgName', ns)
        if org_name is not None and org_name.text:
            affiliations.append(org_name.text)
    return list(set(affiliations))

def count_submissions():
    """Count submissions"""
    if not os.path.exists(SUBMISSIONS_FILE):
        return 0
    with open(SUBMISSIONS_FILE, 'r', encoding='utf-8') as f:
        return sum(1 for line in f) - 1

# ==================== INITIALIZE ====================
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

init_csv()
init_storage()

# ==================== ADMIN PANEL ====================
with st.sidebar:
    st.header("🔐 Admin Access")
    
    if not st.session_state.admin_authenticated:
        with st.form("admin_login"):
            pin_input = st.text_input("Enter PIN", type="password", max_chars=6)
            if st.form_submit_button("🔓 Unlock"):
                if pin_input == ADMIN_PIN:
                    st.session_state.admin_authenticated = True
                    st.success("✅ Authenticated!")
                    st.rerun()
                else:
                    st.error("❌ Wrong PIN")
    else:
        st.success("✅ Admin Mode")
        
        if st.button("🔒 Lock"):
            st.session_state.admin_authenticated = False
            st.rerun()
        
        # Google Drive Status
        st.markdown("---")
        st.subheader("☁️ Google Drive")
        
        with st.spinner("Checking Drive..."):
            status, folder_link = check_drive_setup_status()
            
        if "✅" in status:
            st.success(status)
            st.caption(f"Uploads to: {SUBMISSIONS_DRIVE_EMAIL}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📁 Open", use_container_width=True):
                    if folder_link:
                        st.markdown(f"[Open Folder]({folder_link})")
            with col2:
                if st.button("🔄 Retest", use_container_width=True):
                    test_drive_setup()
        else:
            st.error(status)
            
            if st.button("🔧 Setup Guide", use_container_width=True, type="primary"):
                show_drive_setup_guide()
        
        # Dashboard
        st.markdown("---")
        st.subheader("📊 Dashboard")
        st.metric("Total Submissions", count_submissions())
        
        if st.button("👁️ View All Submissions", use_container_width=True):
            if os.path.exists(SUBMISSIONS_FILE):
                import pandas as pd
                df = pd.read_csv(SUBMISSIONS_FILE)
                st.dataframe(df, use_container_width=True, height=400)
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download CSV",
                    csv_data,
                    f"submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.info("No submissions yet")
        
        if st.button("🔍 View Latest", use_container_width=True):
            if os.path.exists(SUBMISSIONS_FILE):
                import pandas as pd
                df = pd.read_csv(SUBMISSIONS_FILE)
                if len(df) > 0:
                    latest = df.iloc[-1]
                    st.json(latest.to_dict())
                else:
                    st.info("No submissions yet")
        
        # Storage Info
        st.markdown("---")
        st.info("💾 **Storage:** Local + Google Drive")
        st.caption("✓ Files saved locally")
        st.caption("✓ Details in Google Sheets")
        st.caption("✓ Full backup in Drive")
        
        # GROBID Configuration
        st.markdown("---")
        st.subheader("⚙️ Configuration")
        st.session_state.grobid_server = st.text_input(
            "GROBID Server URL",
            value=st.session_state.grobid_server,
            help="PDF parsing service"
        )
        
        # Service Account Info
        with st.expander("🔍 Service Account Info"):
            try:
                service_account_email = st.secrets["gcp_service_account"]["client_email"]
                st.code(service_account_email)
                st.caption("Share your Drive folder with this email")
                st.caption(f"Submissions Drive: {SUBMISSIONS_DRIVE_EMAIL}")
            except:
                st.error("Service account not configured in secrets.toml")

# ==================== MAIN FORM ====================
st.title("📝 Research Paper Submission")
st.markdown("Upload your paper and transaction proof")

if st.session_state.show_success:
    st.success("🎉 Submission successful!")
    st.info("✅ All details saved to Google Drive. Admin will review and contact you.")
    
    if st.button("➕ Submit Another"):
        st.session_state.show_success = False
        st.session_state.metadata = None
        st.session_state.extracted = False
        st.rerun()
    st.stop()

st.markdown("---")
st.subheader("📤 Step 1: Upload Files")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📄 Research Paper")
    uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'], key="pdf")
    if uploaded_pdf:
        st.success(f"✅ {uploaded_pdf.name}")

with col2:
    st.markdown("#### 💳 Transaction Proof")
    uploaded_image = st.file_uploader("Upload receipt", type=['jpg', 'jpeg', 'png', 'pdf'], key="img")
    if uploaded_image:
        st.success(f"✅ {uploaded_image.name}")
        if uploaded_image.type.startswith('image'):
            st.image(uploaded_image, width=200)

if uploaded_pdf and uploaded_image:
    if st.button("🤖 Auto-Fill Form", type="primary", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_pdf.getvalue())
            tmp_path = tmp.name
        
        try:
            with st.spinner("🔄 Extracting..."):
                tei_xml = parse_pdf_with_grobid(tmp_path, st.session_state.grobid_server)
                metadata = extract_metadata_from_tei(tei_xml)
                metadata['affiliations'] = extract_affiliations_from_tei(tei_xml)
                metadata['emails'] = find_emails(extract_full_text(tmp_path))
                
                st.session_state.metadata = metadata
                st.session_state.extracted = True
                st.success("✅ Auto-filled!")
        except Exception as e:
            st.error(f"❌ Auto-fill failed: {str(e)}")
            st.info("💡 Fill manually below")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

if uploaded_pdf and uploaded_image:
    st.markdown("---")
    st.subheader("📋 Step 2: Complete Form")
    
    if st.session_state.extracted:
        st.info("✨ Auto-filled! Please review.")
    
    metadata = st.session_state.metadata or {}
    
    with st.form("submission"):
        st.markdown("### 📄 Paper Details")
        
        title = st.text_input("Title *", value=metadata.get('title', ''))
        authors = st.text_area("Authors (semicolon separated) *", 
                              value="; ".join(metadata.get('authors', [])),
                              height=80)
        
        st.markdown("### 📧 Contact")
        
        col1, col2 = st.columns(2)
        with col1:
            emails_list = metadata.get('emails', [])
            if emails_list:
                email = st.selectbox("Corresponding Email *", ['Select...'] + emails_list)
                if email == 'Select...':
                    email = st.text_input("Or enter manually *")
            else:
                email = st.text_input("Corresponding Email *")
        
        with col2:
            all_emails = st.text_area("All Emails (optional)",
                                     value="; ".join(emails_list),
                                     height=80)
        
        affiliations = st.text_area("Affiliations *",
                                   value="; ".join(metadata.get('affiliations', [])),
                                   height=80)
        
        st.markdown("### 📝 Abstract & Keywords")
        abstract = st.text_area("Abstract *", value=metadata.get('abstract', ''), height=150)
        keywords = st.text_input("Keywords *", value=", ".join(metadata.get('keywords', [])))
        
        st.markdown("### 🔬 Classification")
        col1, col2 = st.columns(2)
        with col1:
            area = st.selectbox("Research Area *", [
                "Select...", "Computer Science", "AI", "Machine Learning",
                "Data Science", "Physics", "Chemistry", "Biology",
                "Mathematics", "Engineering", "Medicine", "Other"
            ])
        with col2:
            sub_type = st.selectbox("Type *", [
                "Select...", "Full Paper", "Short Paper", "Poster",
                "Extended Abstract", "Review", "Case Study"
            ])
        
        comments = st.text_area("Comments (optional)", height=80)
        
        st.markdown("---")
        consent = st.checkbox("I confirm all information is accurate *")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("✅ Submit", type="primary", use_container_width=True)
        
        if submitted:
            errors = []
            if not title.strip(): errors.append("Title")
            if not authors.strip(): errors.append("Authors")
            if not email.strip() or email == 'Select...': errors.append("Email")
            if not affiliations.strip(): errors.append("Affiliations")
            if not abstract.strip(): errors.append("Abstract")
            if not keywords.strip(): errors.append("Keywords")
            if area == "Select...": errors.append("Research Area")
            if sub_type == "Select...": errors.append("Type")
            if not consent: errors.append("Consent")
            
            if errors:
                st.error(f"❌ Required: {', '.join(errors)}")
            else:
                submission_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Prepare data
                submission_data = {
                    'submission_id': submission_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': title.strip(),
                    'authors': authors.strip(),
                    'corresponding_email': email.strip(),
                    'all_emails': all_emails.strip(),
                    'affiliations': affiliations.strip(),
                    'abstract': abstract.strip(),
                    'keywords': keywords.strip(),
                    'research_area': area,
                    'submission_type': sub_type,
                    'comments': comments.strip(),
                    'pdf_filename': uploaded_pdf.name,
                    'image_filename': uploaded_image.name
                }
                
                # Save locally
                with st.spinner("💾 Saving files locally..."):
                    local_data = save_files_locally(uploaded_pdf, uploaded_image, 
                                                   submission_id, authors.strip())
                
                if local_data:
                    submission_data.update({
                        'pdf_path': local_data['pdf_path'],
                        'image_path': local_data['image_path']
                    })
                    
                    # Upload to Drive
                    if GOOGLE_DRIVE_ENABLED:
                        with st.spinner("☁️ Uploading to Google Drive..."):
                            drive_data = upload_complete_submission_to_drive(
                                uploaded_pdf, uploaded_image, submission_data
                            )
                            
                            if drive_data:
                                submission_data.update({
                                    'drive_doc_link': drive_data.get('doc_link'),
                                    'drive_folder_link': drive_data.get('folder_link')
                                })
                                st.success("✅ Uploaded to Drive!")
                            else:
                                st.warning("⚠️ Drive upload failed, but files are saved locally")
                    
                    # Save to CSV
                    try:
                        append_to_csv(submission_data)
                    except Exception as e:
                        st.error(f"CSV error: {str(e)}")
                    
                    # Save to Sheets
                    if GOOGLE_SHEETS_ENABLED:
                        with st.spinner("📊 Updating Google Sheets..."):
                            append_to_google_sheets(submission_data)
                    
                    st.session_state.show_success = True
                    st.rerun()

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "🔒 Secure System • Full details stored in Google Drive<br>"
    "Powered by AI & GROBID"
    "</div>",
    unsafe_allow_html=True
)