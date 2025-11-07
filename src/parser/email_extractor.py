"""
Email extractor for PDF research papers
Uses PyMuPDF (fitz) for better text extraction
"""
import re
from typing import List

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    try:
        from PyPDF2 import PdfReader
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False


def extract_full_text(pdf_path: str) -> str:
    """
    Extracts all text content from a PDF file.
    Tries PyMuPDF first (better), falls back to PyPDF2.
    
    Args:
        pdf_path: The file path to the PDF document.
    
    Returns:
        A single string containing all text from the PDF.
    """
    # Try PyMuPDF first (better extraction)
    if PYMUPDF_AVAILABLE:
        try:
            full_text = ""
            doc = fitz.open(pdf_path)
            for page in doc:
                full_text += page.get_text()
            doc.close()
            return full_text
        except Exception as e:
            print(f"⚠️ Error extracting text with PyMuPDF: {e}")
    
    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            full_text = ""
            with open(pdf_path, 'rb') as file:
                pdf = PdfReader(file)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            return full_text
        except Exception as e:
            print(f"⚠️ Error extracting text with PyPDF2: {e}")
    
    print("❌ No PDF library available (install PyMuPDF or PyPDF2)")
    return ""


def find_emails(text: str) -> List[str]:
    """
    Finds all unique email addresses in a block of text using regex.
    
    Args:
        text: The string to search for emails.
    
    Returns:
        A list of unique email addresses found in the text.
    """
    if not text:
        return []
    
    # Robust email regex pattern
    # Matches: username@domain.tld
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    found_emails = re.findall(email_regex, text)
    
    # Return unique emails (preserve order)
    seen = set()
    unique_emails = []
    for email in found_emails:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            unique_emails.append(email)
    
    return unique_emails
