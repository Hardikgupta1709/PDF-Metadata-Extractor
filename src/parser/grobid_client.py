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
