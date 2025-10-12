# src/parser/email_extractor.py

import fitz  # PyMuPDF
import re
from typing import List

def extract_full_text(pdf_path: str) -> str:
    """
    Extracts all text content from a PDF file using PyMuPDF.

    Args:
        pdf_path: The file path to the PDF document.

    Returns:
        A single string containing all text from the PDF.
    """
    full_text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            full_text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text with PyMuPDF: {e}")
        return ""
    return full_text


# src/parser/email_extractor.py (continued)

def find_emails(text: str) -> List[str]:
    """
    Finds all unique email addresses in a block of text using a regular expression.

    Args:
        text: The string to search for emails.

    Returns:
        A list of unique email addresses found in the text.
    """
    # This regex is a robust pattern for matching common email formats.
    # It looks for:
    # [a-zA-Z0-9._%+-]+  : One or more allowed characters for the local part.
    # @                  : The literal '@' symbol.
    # [a-zA-Z0-9.-]+     : One or more characters for the domain name.
    # \.                 : The literal '.' for the top-level domain separator.
    # [a-zA-Z]{2,}       : At least two letters for the top-level domain.
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    found_emails = re.findall(email_regex, text)
    
    # Return a list of unique emails to avoid duplicates.
    return list(set(found_emails))