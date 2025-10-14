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


import streamlit as st
import sys
import os
import json
import tempfile
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from parser.grobid_client import parse_pdf_with_grobid, extract_metadata_from_tei
from parser.email_extractor import extract_full_text, find_emails

# Page configuration
st.set_page_config(
    page_title="PDF Metadata Extractor",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Sidebar configuration
st.sidebar.title(" Configuration")
grobid_server = st.sidebar.text_input(
    "GROBID Server URL",
    value="https://kermitt2-grobid.hf.space",
    help="GROBID service on Render.com..."
)

st.sidebar.markdown("---")
st.sidebar.markdown(" Display Options")
show_body_text = st.sidebar.checkbox("Show Body Text Preview", value=True)
show_raw_json = st.sidebar.checkbox("Show Raw JSON", value=False)


# Main content
st.title("📄 PDF Metadata Extractor")
st.markdown("Upload a PDF to extract metadata, authors, emails, and more using GROBID.")

# File uploader
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=['pdf'],
    help="Upload a research paper or document in PDF format (max 5MB recommended)"
)

if uploaded_file is not None:
    # Display file info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(" Filename", uploaded_file.name)
    with col2:
        file_size_kb = uploaded_file.size / 1024
        st.metric("File Size", f"{file_size_kb:.2f} KB")
    with col3:
        st.metric(" Type", uploaded_file.type)
    
    # Check file size warning
    if uploaded_file.size > 5 * 1024 * 1024:  # 5MB
        st.warning("File is larger than 5MB. Processing may be slow or fail.")
    
    # Process button
    if st.button(" Extract Metadata", type="primary", use_container_width=True):
        st.session_state.processing = True
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Step 1: Parse with GROBID
            progress_bar = st.progress(0, text="Starting PDF processing...")
            
            with st.spinner("Connecting to GROBID service..."):
                tei_xml = parse_pdf_with_grobid(tmp_path, grobid_server)
            
            progress_bar.progress(33, text="Extracting metadata...")
            
            metadata = extract_metadata_from_tei(tei_xml)
  
            
            # Step 2: Extract text and emails
            full_text = extract_full_text(tmp_path)
            emails = find_emails(full_text)
            metadata['emails'] = emails
            
            progress_bar.progress(100, text="Complete!")
            st.session_state.metadata = metadata
            st.success(" Extraction complete!")
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"Error during processing: {error_msg}")
            
            # Provide helpful hints based on error type
            if "404" in error_msg:
                st.error(
                    " **GROBID Service Not Found (404)**\n\n"
                    "The GROBID service is not responding. Possible causes:\n"
                    "- Service failed to deploy\n"
                    "- Service URL is incorrect\n"
                    "- Service is still starting up\n\n"
                    "Please check the Render.com dashboard and deployment logs."
                )
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                st.error(
                    "⏱ **Request Timeout**\n\n"
                    "The request took too long. This can happen when:\n"
                    "- Service is waking up from sleep (free tier)\n"
                    "- PDF is too large\n"
                    "- Service is overloaded\n\n"
                    "Try again in a moment or use a smaller PDF."
                )
            elif "503" in error_msg:
                st.error(
                    " **Service Unavailable (503)**\n\n"
                    "The GROBID service is sleeping or starting up. "
                    "Please wait 60 seconds and try again."
                )
            
            # Show full traceback in expander for debugging
            with st.expander("View Full Error Details"):
                st.exception(e)
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            st.session_state.processing = False

# Display results
if st.session_state.metadata is not None:
    st.markdown("---")
    st.header(" Extraction Results")
    
    metadata = st.session_state.metadata
    
    # Title
    st.subheader(" Title")
    if metadata.get('title'):
        st.markdown(f"**{metadata['title']}**")
    else:
        st.warning("No title found")
    
    # Authors
    st.subheader(" Authors")
    if metadata.get('authors'):
        cols = st.columns(min(len(metadata['authors']), 3))
        for idx, author in enumerate(metadata['authors']):
            with cols[idx % 3]:
                st.info(f" {author}")
    else:
        st.warning("No authors found")
    
    # Emails
    st.subheader(" Email Addresses")
    if metadata.get('emails'):
        cols = st.columns(min(len(metadata['emails']), 2))
        for idx, email in enumerate(metadata['emails']):
            with cols[idx % 2]:
                st.success(f"{email}")
    else:
        st.warning("No email addresses found")
    
    # Abstract
    st.subheader(" Abstract")
    if metadata.get('abstract'):
        with st.expander("View Abstract", expanded=True):
            st.write(metadata['abstract'])
    else:
        st.warning("No abstract found")
    
    # Keywords
    if metadata.get('keywords'):
        st.subheader(" Keywords")
        keyword_str = " • ".join(metadata['keywords'])
        st.markdown(f"`{keyword_str}`")
    
    # Body Text Preview
    if show_body_text and metadata.get('body_text'):
        st.subheader(" Body Text Preview")
        with st.expander("View Body Text", expanded=False):
            st.text_area(
                "First 2000 characters",
                metadata['body_text'][:2000],
                height=200,
                disabled=True
            )
    
    # Publication Date
    if metadata.get('publication_date'):
        st.subheader(" Publication Date")
        st.info(metadata['publication_date'])
    
    # Download options
    st.markdown("---")
    st.subheader(" Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON download
        json_str = json.dumps(metadata, indent=2, ensure_ascii=False)
        st.download_button(
            label=" Download JSON",
            data=json_str,
            file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # CSV download
        csv_lines = ["Field,Value"]
        for key, value in metadata.items():
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            csv_lines.append(f'"{key}","{value}"')
        csv_str = "\n".join(csv_lines)
        
        st.download_button(
            label=" Download CSV",
            data=csv_str,
            file_name=f"{uploaded_file.name.replace('.pdf', '')}_metadata.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # Raw JSON view
    if show_raw_json:
        st.markdown("---")
        st.subheader(" Raw JSON Data")
        with st.expander("View Raw JSON", expanded=False):
            st.json(metadata)


# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "• Built with Streamlit •" 
    "</div>",
    unsafe_allow_html=True
)