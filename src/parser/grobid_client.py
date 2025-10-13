# import requests
# from xml.etree import ElementTree as ET


# def parse_pdf_with_grobid(pdf_path: str, grobid_server: str) -> str:
#     """
#     Send PDF to GROBID server and get TEI XML response.
#     """
#     url = f"{grobid_server}/api/processFulltextDocument"
    
#     with open(pdf_path, 'rb') as pdf_file:
#         files = {'input': pdf_file}
#         response = requests.post(url, files=files)
#         response.raise_for_status()
        
#     return response.text


# def extract_metadata_from_tei(tei_xml: str) -> dict:
#     """
#     Extract metadata from GROBID's TEI XML output.
#     """
#     namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
#     root = ET.fromstring(tei_xml)
    
#     metadata = {
#         'title': '',
#         'authors': [],
#         'abstract': '',
#         'keywords': [],
#         'publication_date': '',
#         'body_text': ''
#     }
    
#     # Extract title from titleStmt
#     title_elem = root.find('.//tei:titleStmt/tei:title', namespaces)
#     if title_elem is not None and title_elem.text:
#         metadata['title'] = title_elem.text.strip()
    
#     # If title is empty, try to get from first heading in body
#     if not metadata['title']:
#         first_head = root.find('.//tei:body//tei:head', namespaces)
#         if first_head is not None and first_head.text:
#             metadata['title'] = first_head.text.strip()
    
#     # Extract authors
#     authors = root.findall('.//tei:sourceDesc//tei:author', namespaces)
#     for author in authors:
#         forename = author.find('.//tei:forename', namespaces)
#         surname = author.find('.//tei:surname', namespaces)
        
#         name_parts = []
#         if forename is not None and forename.text:
#             name_parts.append(forename.text.strip())
#         if surname is not None and surname.text:
#             name_parts.append(surname.text.strip())
        
#         if name_parts:
#             metadata['authors'].append(' '.join(name_parts))
    
#     # Extract abstract
#     abstract_elem = root.find('.//tei:abstract', namespaces)
#     if abstract_elem is not None:
#         abstract_texts = []
#         for elem in abstract_elem.iter():
#             if elem.text:
#                 abstract_texts.append(elem.text.strip())
#         metadata['abstract'] = ' '.join(abstract_texts)
    
#     # Extract keywords
#     keywords = root.findall('.//tei:keywords//tei:term', namespaces)
#     metadata['keywords'] = [kw.text.strip() for kw in keywords if kw.text]
    
#     # Extract publication date
#     date_elem = root.find('.//tei:publicationStmt/tei:date', namespaces)
#     if date_elem is not None:
#         metadata['publication_date'] = date_elem.get('when', '')
    
#     # Extract body text (first 1000 characters for preview)
#     body_paragraphs = root.findall('.//tei:body//tei:p', namespaces)
#     body_texts = []
#     for p in body_paragraphs:
#         if p.text:
#             body_texts.append(p.text.strip())
#         for elem in p.iter():
#             if elem.text and elem != p:
#                 body_texts.append(elem.text.strip())
    
#     full_body = ' '.join(body_texts)
#     metadata['body_text'] = full_body[:1000] + '...' if len(full_body) > 1000 else full_body
    
#     return metadata



"""
GROBID client for parsing PDF files
"""
import requests
import time
from typing import Dict, List
from xml.etree import ElementTree as ET


def parse_pdf_with_grobid(pdf_path: str, grobid_server: str, max_retries: int = 3) -> str:
    """
    Send PDF to GROBID server and get TEI XML response.
    
    Args:
        pdf_path: Path to PDF file
        grobid_server: GROBID server URL
        max_retries: Number of retry attempts for timeout/503 errors
    
    Returns:
        TEI XML string
    
    Raises:
        requests.exceptions.HTTPError: If request fails after all retries
    """
    url = f"{grobid_server}/api/processFulltextDocument"
    
    for attempt in range(max_retries):
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                
                # Extended timeout for cold start (free tier wakes up slowly)
                timeout = 120 if attempt == 0 else 60
                
                response = requests.post(
                    url, 
                    files=files,
                    timeout=timeout
                )
                response.raise_for_status()
                
                return response.text
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 30  # 30s, 60s
                print(f"Timeout on attempt {attempt + 1}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(
                    f"Request timed out after {max_retries} attempts. "
                    "The GROBID service may be sleeping or overloaded. "
                    "Please wait a minute and try again."
                )
        
        except requests.exceptions.HTTPError as e:
            # Retry on 503 (service unavailable - waking up)
            if e.response.status_code == 503 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 20  # 20s, 40s
                print(f"Service unavailable (503). Waiting {wait_time}s for service to wake up...")
                time.sleep(wait_time)
            else:
                raise
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to GROBID server: {str(e)}")


def extract_metadata_from_tei(tei_xml: str) -> Dict:
    """
    Extract metadata from TEI XML returned by GROBID.
    
    Args:
        tei_xml: TEI XML string from GROBID
    
    Returns:
        Dictionary containing extracted metadata
    """
    # Parse XML
    root = ET.fromstring(tei_xml)
    
    # Define namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    metadata = {
        'title': None,
        'authors': [],
        'abstract': None,
        'keywords': [],
        'publication_date': None,
        'body_text': None,
        'emails': []
    }
    
    # Extract title
    title_elem = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
    if title_elem is not None:
        metadata['title'] = title_elem.text
    
    # Extract authors
    authors = root.findall('.//tei:sourceDesc//tei:author', ns)
    for author in authors:
        forename = author.find('.//tei:forename', ns)
        surname = author.find('.//tei:surname', ns)
        
        if forename is not None and surname is not None:
            full_name = f"{forename.text} {surname.text}"
            metadata['authors'].append(full_name)
        elif surname is not None:
            metadata['authors'].append(surname.text)
    
    # Extract abstract
    abstract_elem = root.find('.//tei:profileDesc/tei:abstract/tei:div/tei:p', ns)
    if abstract_elem is not None:
        abstract_text = ''.join(abstract_elem.itertext())
        metadata['abstract'] = abstract_text.strip()
    
    # Extract keywords
    keywords = root.findall('.//tei:keywords/tei:term', ns)
    metadata['keywords'] = [kw.text for kw in keywords if kw.text]
    
    # Extract publication date
    date_elem = root.find('.//tei:publicationStmt/tei:date', ns)
    if date_elem is not None:
        metadata['publication_date'] = date_elem.get('when') or date_elem.text
    
    # Extract body text (first 1000 chars)
    body_elem = root.find('.//tei:text/tei:body', ns)
    if body_elem is not None:
        body_text = ''.join(body_elem.itertext())
        metadata['body_text'] = body_text.strip()[:1000]
    
    return metadata