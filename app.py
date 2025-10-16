# import streamlit as st
# import sys
# import os
# import json
# import tempfile
# from pathlib import Path

# # Add src to path
# project_root = Path(__file__).parent
# src_path = project_root / "src"
# if str(src_path) not in sys.path:
#     sys.path.insert(0, str(src_path))

# from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
# from parser.email_extractor import extract_full_text, find_emails

# # Page configuration
# st.set_page_config(
#     page_title="PDF Metadata Extractor",
#     page_icon="",
#     layout="wide"
# )

# # Initialize session state
# if 'metadata' not in st.session_state:
#     st.session_state.metadata = None
# if 'processing' not in st.session_state:
#     st.session_state.processing = False

# # Sidebar configuration
# st.sidebar.title("Configuration")
# grobid_server = st.sidebar.text_input(
#     "GROBID Server URL",
#     value="https://grobid-service.onrender.com",
#     help="Make sure GROBID is running"
# )



# st.sidebar.markdown("---")
# st.sidebar.markdown("### Display Options")
# show_body_text = st.sidebar.checkbox("Show Body Text Preview", value=True)
# show_raw_json = st.sidebar.checkbox("Show Raw JSON", value=False)

# # Main content
# st.title("Metadata Extractor")
# st.markdown("Upload a PDF to extract metadata, authors, emails, and more using GROBID.")

# # File uploader
# uploaded_file = st.file_uploader(
#     "Choose a PDF file",
#     type=['pdf'],
#     help="Upload a research paper or document in PDF format"
# )

# if uploaded_file is not None:
#     # Display file info
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric("Filename", uploaded_file.name)
#     with col2:
#         st.metric("File Size", f"{uploaded_file.size / 1024:.2f} KB")
#     with col3:
#         st.metric("Type", uploaded_file.type)
    
#     # Process button
#     if st.button("Extract Metadata", type="primary", use_container_width=True):
#         st.session_state.processing = True
        
#         # Save uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             tmp_file.write(uploaded_file.getvalue())
#             tmp_path = tmp_file.name
        
#         try:
#             with st.spinner("Processing PDF ..."):
#                 # Step 1: Parse with GROBID
#                 progress_bar = st.progress(0)
                
                
#                 tei_xml = parse_pdf_with_grobid(tmp_path, grobid_server)
#                 progress_bar.progress(33)
                
                
#                 metadata = extract_metadata_from_tei(tei_xml)
#                 progress_bar.progress(66)
                
#                 # Step 2: Extract text and emails
                
#                 full_text = extract_full_text(tmp_path)
#                 emails = find_emails(full_text)
#                 metadata['emails'] = emails
                
#                 progress_bar.progress(100)
#                 st.session_state.metadata = metadata
#                 st.success("Extraction complete!")
                
#         except Exception as e:
#             st.error(f" Error during processing: {str(e)}")
#             st.exception(e)
#         finally:
#             # Clean up temp file
#             if os.path.exists(tmp_path):
#                 os.unlink(tmp_path)
#             st.session_state.processing = False

# # Display results
# if st.session_state.metadata is not None:
#     st.markdown("---")
#     st.header("Extraction Results")
    
#     metadata = st.session_state.metadata
    
#     # Title
#     st.subheader(" Title")
#     if metadata.get('title'):
#         st.markdown(f"**{metadata['title']}**")
#     else:
#         st.warning("No title found")
    
#     # Authors
#     st.subheader("Authors")
#     if metadata.get('authors'):
#         cols = st.columns(min(len(metadata['authors']), 3))
#         for idx, author in enumerate(metadata['authors']):
#             with cols[idx % 3]:
#                 st.info(f"{author}")
#     else:
#         st.warning("No authors found")
    
#     # Emails
#     st.subheader("Email Addresses")
#     if metadata.get('emails'):
#         cols = st.columns(min(len(metadata['emails']), 2))
#         for idx, email in enumerate(metadata['emails']):
#             with cols[idx % 2]:
#                 st.success(f"{email}")
#     else:
#         st.warning("No email addresses found")
    
#     # Abstract
#     st.subheader("Abstract")
#     if metadata.get('abstract'):
#         with st.expander("View Abstract", expanded=True):
#             st.write(metadata['abstract'])
#     else:
#         st.warning("No abstract found")
    
#     # Keywords
#     if metadata.get('keywords'):
#         st.subheader("Keywords")
#         keyword_str = " • ".join(metadata['keywords'])
#         st.markdown(f"`{keyword_str}`")
    
#     # Body Text Preview
#     if show_body_text and metadata.get('body_text'):
#         st.subheader(" Body Text Preview")
#         with st.expander("View Body Text", expanded=False):
#             st.text_area(
#                 "First 1000 characters",
#                 metadata['body_text'],
#                 height=200,
#                 disabled=True
#             )
    
#     # Publication Date
#     if metadata.get('publication_date'):
#         st.subheader("Publication Date")
#         st.info(metadata['publication_date'])
    
#     # Download options
#     st.markdown("---")
#     st.subheader("Download Results")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         # JSON download
#         json_str = json.dumps(metadata, indent=2, ensure_ascii=False)
#         st.download_button(
#             label="Download JSON",
#             data=json_str,
#             file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.json",
#             mime="application/json",
#             use_container_width=True
#         )
    
#     with col2:
#         # CSV download
#         csv_lines = ["Field,Value"]
#         for key, value in metadata.items():
#             if isinstance(value, list):
#                 value = "; ".join(str(v) for v in value)
#             csv_lines.append(f'"{key}","{value}"')
#         csv_str = "\n".join(csv_lines)
        
#         st.download_button(
#             label=" Download CSV",
#             data=csv_str,
#             file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.csv",
#             mime="text/csv",
#             use_container_width=True
#         )
    
#     # Raw JSON view
#     if show_raw_json:
#         st.markdown("---")
#         st.subheader("🔧 Raw JSON Data")
#         with st.expander("View Raw JSON", expanded=False):
#             st.json(metadata)


# # Footer
# st.markdown("---")
# st.markdown(
#     "<div style='text-align: center; color: gray;'>"
#     "Built with Streamlit "
#     "</div>",
#     unsafe_allow_html=True
# )


# import streamlit as st
# import sys
# import os
# import json
# import tempfile
# from pathlib import Path

# # Add src to path
# project_root = Path(__file__).parent
# src_path = project_root / "src"
# if str(src_path) not in sys.path:
#     sys.path.insert(0, str(src_path))

# from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
# from parser.email_extractor import extract_full_text, find_emails

# # Page configuration
# st.set_page_config(
#     page_title="PDF Metadata Extractor",
#     page_icon="📄",
#     layout="wide"
# )

# # Initialize session state
# if 'metadata' not in st.session_state:
#     st.session_state.metadata = None
# if 'processing' not in st.session_state:
#     st.session_state.processing = False

# # Sidebar configuration
# st.sidebar.title(" Configuration")
# grobid_server = st.sidebar.text_input(
#     "GROBID Server URL",
#     value="https://kermitt2-grobid.hf.space",
#     help="GROBID service on Render.com..."
# )

# st.sidebar.markdown("---")
# st.sidebar.markdown(" Display Options")
# show_body_text = st.sidebar.checkbox("Show Body Text Preview", value=True)
# show_raw_json = st.sidebar.checkbox("Show Raw JSON", value=False)


# # Main content
# st.title("📄 PDF Metadata Extractor")
# st.markdown("Upload a PDF to extract metadata, authors, emails, and more using GROBID.")

# # File uploader
# uploaded_file = st.file_uploader(
#     "Choose a PDF file",
#     type=['pdf'],
#     help="Upload a research paper or document in PDF format (max 5MB recommended)"
# )

# if uploaded_file is not None:
#     # Display file info
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric(" Filename", uploaded_file.name)
#     with col2:
#         file_size_kb = uploaded_file.size / 1024
#         st.metric("File Size", f"{file_size_kb:.2f} KB")
#     with col3:
#         st.metric(" Type", uploaded_file.type)
    
#     # Check file size warning
#     if uploaded_file.size > 5 * 1024 * 1024:  # 5MB
#         st.warning("File is larger than 5MB. Processing may be slow or fail.")
    
#     # Process button
#     if st.button(" Extract Metadata", type="primary", use_container_width=True):
#         st.session_state.processing = True
        
#         # Save uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             tmp_file.write(uploaded_file.getvalue())
#             tmp_path = tmp_file.name
        
#         try:
#             # Step 1: Parse with GROBID
#             progress_bar = st.progress(0, text="Starting PDF processing...")
            
#             with st.spinner("Connecting to GROBID service..."):
#                 tei_xml = parse_pdf_with_grobid(tmp_path, grobid_server)
            
#             progress_bar.progress(33, text="Extracting metadata...")
            
#             metadata = extract_metadata_from_tei(tei_xml)
  
            
#             # Step 2: Extract text and emails
#             full_text = extract_full_text(tmp_path)
#             emails = find_emails(full_text)
#             metadata['emails'] = emails
            
#             progress_bar.progress(100, text="Complete!")
#             st.session_state.metadata = metadata
#             st.success(" Extraction complete!")
            
#         except Exception as e:
#             error_msg = str(e)
#             st.error(f"Error during processing: {error_msg}")
            
#             # Provide helpful hints based on error type
#             if "404" in error_msg:
#                 st.error(
#                     " **GROBID Service Not Found (404)**\n\n"
#                     "The GROBID service is not responding. Possible causes:\n"
#                     "- Service failed to deploy\n"
#                     "- Service URL is incorrect\n"
#                     "- Service is still starting up\n\n"
#                     "Please check the Render.com dashboard and deployment logs."
#                 )
#             elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
#                 st.error(
#                     "⏱ **Request Timeout**\n\n"
#                     "The request took too long. This can happen when:\n"
#                     "- Service is waking up from sleep (free tier)\n"
#                     "- PDF is too large\n"
#                     "- Service is overloaded\n\n"
#                     "Try again in a moment or use a smaller PDF."
#                 )
#             elif "503" in error_msg:
#                 st.error(
#                     " **Service Unavailable (503)**\n\n"
#                     "The GROBID service is sleeping or starting up. "
#                     "Please wait 60 seconds and try again."
#                 )
            
#             # Show full traceback in expander for debugging
#             with st.expander("View Full Error Details"):
#                 st.exception(e)
                
#         finally:
#             # Clean up temp file
#             if os.path.exists(tmp_path):
#                 os.unlink(tmp_path)
#             st.session_state.processing = False

# # Display results
# if st.session_state.metadata is not None:
#     st.markdown("---")
#     st.header(" Extraction Results")
    
#     metadata = st.session_state.metadata
    
#     # Title
#     st.subheader(" Title")
#     if metadata.get('title'):
#         st.markdown(f"**{metadata['title']}**")
#     else:
#         st.warning("No title found")
    
#     # Authors
#     st.subheader(" Authors")
#     if metadata.get('authors'):
#         cols = st.columns(min(len(metadata['authors']), 3))
#         for idx, author in enumerate(metadata['authors']):
#             with cols[idx % 3]:
#                 st.info(f" {author}")
#     else:
#         st.warning("No authors found")
    
#     # Emails
#     st.subheader(" Email Addresses")
#     if metadata.get('emails'):
#         cols = st.columns(min(len(metadata['emails']), 2))
#         for idx, email in enumerate(metadata['emails']):
#             with cols[idx % 2]:
#                 st.success(f"{email}")
#     else:
#         st.warning("No email addresses found")
    
#     # Abstract
#     st.subheader(" Abstract")
#     if metadata.get('abstract'):
#         with st.expander("View Abstract", expanded=True):
#             st.write(metadata['abstract'])
#     else:
#         st.warning("No abstract found")
    
#     # Keywords
#     if metadata.get('keywords'):
#         st.subheader(" Keywords")
#         keyword_str = " • ".join(metadata['keywords'])
#         st.markdown(f"`{keyword_str}`")
    
#     # Body Text Preview
#     if show_body_text and metadata.get('body_text'):
#         st.subheader(" Body Text Preview")
#         with st.expander("View Body Text", expanded=False):
#             st.text_area(
#                 "First 2000 characters",
#                 metadata['body_text'][:2000],
#                 height=200,
#                 disabled=True
#             )
    
#     # Publication Date
#     if metadata.get('publication_date'):
#         st.subheader(" Publication Date")
#         st.info(metadata['publication_date'])
    
#     # Download options
#     st.markdown("---")
#     st.subheader(" Download Results")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         # JSON download
#         json_str = json.dumps(metadata, indent=2, ensure_ascii=False)
#         st.download_button(
#             label=" Download JSON",
#             data=json_str,
#             file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.json",
#             mime="application/json",
#             use_container_width=True
#         )
    
#     with col2:
#         # CSV download
#         csv_lines = ["Field,Value"]
#         for key, value in metadata.items():
#             if isinstance(value, list):
#                 value = "; ".join(str(v) for v in value)
#             csv_lines.append(f'"{key}","{value}"')
#         csv_str = "\n".join(csv_lines)
        
#         st.download_button(
#             label=" Download CSV",
#             data=csv_str,
#             file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.csv",
#             mime="text/csv",
#             use_container_width=True
#         )
    
#     # Raw JSON view
#     if show_raw_json:
#         st.markdown("---")
#         st.subheader(" Raw JSON Data")
#         with st.expander("View Raw JSON", expanded=False):
#             st.json(metadata)


# # Footer
# st.markdown("---")
# st.markdown(
#     "<div style='text-align: center; color: gray;'>"
#     "• Built with Streamlit •" 
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

# CSV file to store submissions
SUBMISSIONS_FILE = "submissions.csv"

# Initialize CSV file if it doesn't exist
def init_csv():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Submission ID',
                'Timestamp',
                'Paper Title',
                'Authors',
                'Corresponding Author Email',
                'All Emails',
                'Author Affiliations',
                'Abstract',
                'Keywords',
                'Research Area',
                'Submission Type',
                'Additional Comments',
                'Filename'
            ])

def append_submission(data):
    """Append submission data to CSV"""
    with open(SUBMISSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            data['submission_id'],
            data['timestamp'],
            data['title'],
            data['authors'],
            data['corresponding_email'],
            data['all_emails'],
            data['affiliations'],
            data['abstract'],
            data['keywords'],
            data['research_area'],
            data['submission_type'],
            data['comments'],
            data['filename']
        ])

def extract_affiliations_from_tei(tei_xml: str) -> list:
    """Extract author affiliations from TEI XML"""
    from xml.etree import ElementTree as ET
    root = ET.fromstring(tei_xml)
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    affiliations = []
    affil_elems = root.findall('.//tei:affiliation', ns)
    
    for affil in affil_elems:
        org_name = affil.find('.//tei:orgName', ns)
        if org_name is not None and org_name.text:
            affiliations.append(org_name.text)
    
    return list(set(affiliations))  # Remove duplicates

# Initialize session state
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'extracted' not in st.session_state:
    st.session_state.extracted = False
if 'tei_xml' not in st.session_state:
    st.session_state.tei_xml = None

# Initialize CSV
init_csv()

# Header
st.title("📝 Research Paper Submission Form")
st.markdown("Upload your research paper PDF and the form will auto-fill with extracted metadata")

# Sidebar for admin
with st.sidebar:
    st.header("🔧 Admin Panel")
    
    if st.button("📊 View All Submissions"):
        if os.path.exists(SUBMISSIONS_FILE):
            import pandas as pd
            df = pd.read_csv(SUBMISSIONS_FILE)
            st.dataframe(df, use_container_width=True)
            
            # Download button for admin
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download All Submissions",
                csv_data,
                "all_submissions.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("No submissions yet")
    
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    grobid_server = st.text_input(
        "GROBID Server URL",
        value="https://kermitt2-grobid.hf.space",
        help="GROBID service for PDF parsing"
    )

# Main form
st.markdown("---")

# Step 1: Upload PDF
st.subheader("📤 Step 1: Upload Your Research Paper")
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=['pdf'],
    help="Upload your research paper in PDF format"
)

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📁 Filename", uploaded_file.name)
    with col2:
        st.metric("💾 Size", f"{uploaded_file.size / 1024:.2f} KB")
    
    # Extract metadata button
    if st.button("🔍 Extract Metadata from PDF", type="primary", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            with st.spinner("🔄 Extracting metadata... (may take 30-60 seconds)"):
                # Parse with GROBID
                tei_xml = parse_pdf_with_grobid(tmp_path, grobid_server)
                st.session_state.tei_xml = tei_xml
                
                # Extract metadata
                metadata = extract_metadata_from_tei(tei_xml)
                
                # Extract affiliations
                affiliations = extract_affiliations_from_tei(tei_xml)
                metadata['affiliations'] = affiliations
                
                # Extract emails
                full_text = extract_full_text(tmp_path)
                emails = find_emails(full_text)
                metadata['emails'] = emails
                
                st.session_state.metadata = metadata
                st.session_state.extracted = True
                st.success("✅ Metadata extracted successfully!")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Tip: You can still fill the form manually below")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

# Step 2: Submission Form
if uploaded_file is not None:
    st.markdown("---")
    st.subheader("📋 Step 2: Review and Complete Submission Form")
    
    metadata = st.session_state.metadata or {}
    
    with st.form("submission_form"):
        st.markdown("### 📄 Paper Information")
        
        # Paper Title (auto-filled)
        title = st.text_input(
            "Paper Title *",
            value=metadata.get('title', ''),
            placeholder="Enter paper title",
            help="Extracted from PDF or enter manually"
        )
        
        # Authors (auto-filled, can edit)
        authors_list = metadata.get('authors', [])
        authors_str = "; ".join(authors_list) if authors_list else ""
        
        authors = st.text_area(
            "Authors (separate by semicolon) *",
            value=authors_str,
            placeholder="John Doe; Jane Smith; ...",
            help="Extracted from PDF. Format: Author1; Author2; Author3",
            height=100
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Corresponding Author Email (dropdown from extracted emails)
            emails_list = metadata.get('emails', [])
            
            if emails_list:
                corresponding_email = st.selectbox(
                    "Corresponding Author Email *",
                    options=[''] + emails_list,
                    help="Select from extracted emails or enter manually below"
                )
                if not corresponding_email:
                    corresponding_email = st.text_input(
                        "Or enter email manually *",
                        placeholder="email@example.com"
                    )
            else:
                corresponding_email = st.text_input(
                    "Corresponding Author Email *",
                    placeholder="email@example.com"
                )
        
        with col2:
            # All author emails
            all_emails_str = "; ".join(emails_list) if emails_list else ""
            all_emails = st.text_area(
                "All Author Emails (optional)",
                value=all_emails_str,
                placeholder="email1@example.com; email2@example.com",
                help="Separate multiple emails with semicolons"
            )
        
        # Author Affiliations (auto-filled from extracted data)
        affiliations_list = metadata.get('affiliations', [])
        affiliations_str = "; ".join(affiliations_list) if affiliations_list else ""
        
        affiliations = st.text_area(
            "Author Affiliations / Institutes *",
            value=affiliations_str,
            placeholder="University of Example; Research Institute XYZ; ...",
            help="Enter all affiliated institutions, separated by semicolons",
            height=100
        )
        
        st.markdown("### 📝 Abstract & Keywords")
        
        # Abstract (auto-filled)
        abstract = st.text_area(
            "Abstract *",
            value=metadata.get('abstract', ''),
            placeholder="Enter paper abstract",
            help="Extracted from PDF or enter manually",
            height=150
        )
        
        # Keywords (auto-filled)
        keywords_list = metadata.get('keywords', [])
        keywords_str = ", ".join(keywords_list) if keywords_list else ""
        
        keywords = st.text_input(
            "Keywords (comma-separated) *",
            value=keywords_str,
            placeholder="machine learning, neural networks, deep learning",
            help="Extracted from PDF or enter manually"
        )
        
        st.markdown("### 🔬 Additional Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            research_area = st.selectbox(
                "Research Area *",
                options=[
                    "",
                    "Computer Science",
                    "Artificial Intelligence",
                    "Machine Learning",
                    "Data Science",
                    "Bioinformatics",
                    "Physics",
                    "Chemistry",
                    "Biology",
                    "Mathematics",
                    "Engineering",
                    "Medicine",
                    "Social Sciences",
                    "Other"
                ],
                help="Select the primary research area"
            )
        
        with col2:
            submission_type = st.selectbox(
                "Submission Type *",
                options=[
                    "",
                    "Full Paper",
                    "Short Paper",
                    "Poster",
                    "Abstract Only",
                    "Review Paper",
                    "Case Study"
                ]
            )
        
        # Additional comments
        comments = st.text_area(
            "Additional Comments (optional)",
            placeholder="Any additional information you'd like to provide",
            height=100
        )
        
        st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button(
            "✅ Submit Paper",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validate required fields
            errors = []
            if not title.strip():
                errors.append("Paper Title is required")
            if not authors.strip():
                errors.append("Authors are required")
            if not corresponding_email.strip():
                errors.append("Corresponding Author Email is required")
            if not affiliations.strip():
                errors.append("Author Affiliations are required")
            if not abstract.strip():
                errors.append("Abstract is required")
            if not keywords.strip():
                errors.append("Keywords are required")
            if not research_area:
                errors.append("Research Area is required")
            if not submission_type:
                errors.append("Submission Type is required")
            
            if errors:
                st.error("❌ Please fill in all required fields:")
                for error in errors:
                    st.error(f"  • {error}")
            else:
                # Generate submission ID
                submission_id = f"SUB{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Prepare submission data
                submission_data = {
                    'submission_id': submission_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': title.strip(),
                    'authors': authors.strip(),
                    'corresponding_email': corresponding_email.strip(),
                    'all_emails': all_emails.strip(),
                    'affiliations': affiliations.strip(),
                    'abstract': abstract.strip(),
                    'keywords': keywords.strip(),
                    'research_area': research_area,
                    'submission_type': submission_type,
                    'comments': comments.strip(),
                    'filename': uploaded_file.name
                }
                
                # Append to CSV
                try:
                    append_submission(submission_data)
                    
                    # Success message
                    st.success("🎉 Submission Successful!")
                    st.balloons()
                    
                    # Display submission details
                    st.info(f"""
                    **Submission ID:** {submission_id}
                    
                    **Submitted on:** {submission_data['timestamp']}
                    
                    Your paper has been successfully submitted. You will receive a confirmation email shortly.
                    """)
                    
                    # Show summary
                    with st.expander("📄 View Submission Summary"):
                        st.json(submission_data)
                    
                except Exception as e:
                    st.error(f"❌ Error saving submission: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Research Paper Submission System • Powered by GROBID & Streamlit 🚀"
    "</div>",
    unsafe_allow_html=True
)