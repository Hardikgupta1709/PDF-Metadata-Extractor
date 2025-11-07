"""
GROBID client for parsing PDF research papers
"""
import requests
import time
from xml.etree import ElementTree as ET
from typing import Dict


def parse_pdf_with_grobid(pdf_path: str, grobid_server: str, max_retries: int = 3) -> str:
    """
    Send PDF to GROBID server and get TEI XML response with retry logic
    """
    url = f"{grobid_server}/api/processFulltextDocument"
    
    for attempt in range(max_retries):
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                
                # Extended timeout for free tier (may need to wake up)
                timeout = 120 if attempt == 0 else 60
                
                print(f"🔄 Attempt {attempt + 1}/{max_retries} - Sending PDF to GROBID...")
                
                response = requests.post(
                    url, 
                    files=files,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    print("✅ GROBID processing successful")
                    return response.text
                else:
                    print(f"⚠️ GROBID returned status {response.status_code}")
                    response.raise_for_status()
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 20
                print(f"⏳ Timeout. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(
                    "GROBID service timed out. The free service may be sleeping. "
                    "Please wait a minute and try again, or fill the form manually."
                )
        
        except requests.exceptions.HTTPError as e:
            # Retry on 503 (service waking up)
            if e.response.status_code == 503 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 15
                print(f"⏳ Service unavailable (waking up). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"GROBID error: {str(e)}")
        
        except Exception as e:
            raise Exception(f"Failed to connect to GROBID: {str(e)}")
    
    raise Exception("Failed to process PDF after all retries")


def extract_metadata_from_tei(tei_xml: str) -> Dict:
    """
    Enhanced metadata extraction from GROBID TEI XML
    """
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as e:
        print(f"❌ Failed to parse TEI XML: {e}")
        return get_empty_metadata()
    
    metadata = get_empty_metadata()
    
    # ============ TITLE ============
    # Priority 1: Main title from titleStmt
    title_elem = root.find('.//tei:titleStmt/tei:title[@type="main"]', namespaces)
    if title_elem is not None and title_elem.text:
        metadata['title'] = clean_text(title_elem.text)
        print(f"✅ Found title (main): {metadata['title'][:50]}...")
    
    # Priority 2: Any title in titleStmt
    if not metadata['title']:
        title_elem = root.find('.//tei:titleStmt/tei:title', namespaces)
        if title_elem is not None and title_elem.text:
            metadata['title'] = clean_text(title_elem.text)
            print(f"✅ Found title (alt): {metadata['title'][:50]}...")
    
    # Priority 3: First heading in body
    if not metadata['title']:
        first_head = root.find('.//tei:body//tei:head', namespaces)
        if first_head is not None and first_head.text:
            metadata['title'] = clean_text(first_head.text)
            print(f"✅ Found title (heading): {metadata['title'][:50]}...")
    
    # ============ AUTHORS ============
    authors = root.findall('.//tei:sourceDesc//tei:author', namespaces)
    
    for author in authors:
        name_parts = []
        
        # Try to get full name structure
        forename = author.find('.//tei:forename[@type="first"]', namespaces)
        if forename is None:
            forename = author.find('.//tei:forename', namespaces)
        
        middle = author.find('.//tei:forename[@type="middle"]', namespaces)
        surname = author.find('.//tei:surname', namespaces)
        
        if forename is not None and forename.text:
            name_parts.append(forename.text.strip())
        if middle is not None and middle.text:
            name_parts.append(middle.text.strip())
        if surname is not None and surname.text:
            name_parts.append(surname.text.strip())
        
        if name_parts:
            full_name = ' '.join(name_parts)
            metadata['authors'].append(full_name)
    
    print(f"✅ Found {len(metadata['authors'])} authors")
    
    # ============ ABSTRACT ============
    # Try multiple locations for abstract
    abstract_locations = [
        './/tei:profileDesc/tei:abstract/tei:div/tei:p',
        './/tei:profileDesc/tei:abstract/tei:p',
        './/tei:abstract/tei:div/tei:p',
        './/tei:abstract/tei:p',
        './/tei:abstract',
    ]
    
    for location in abstract_locations:
        abstract_elem = root.find(location, namespaces)
        if abstract_elem is not None:
            # Get all text including nested elements
            abstract_text = ''.join(abstract_elem.itertext())
            metadata['abstract'] = clean_text(abstract_text)
            if metadata['abstract']:
                print(f"✅ Found abstract ({len(metadata['abstract'])} chars)")
                break
    
    # ============ KEYWORDS ============
    # Try multiple locations for keywords
    keyword_locations = [
        './/tei:keywords//tei:term',
        './/tei:profileDesc//tei:keywords//tei:term',
    ]
    
    for location in keyword_locations:
        keywords = root.findall(location, namespaces)
        if keywords:
            metadata['keywords'] = [
                clean_text(kw.text) for kw in keywords 
                if kw.text and len(kw.text.strip()) > 1
            ]
            if metadata['keywords']:
                print(f"✅ Found {len(metadata['keywords'])} keywords")
                break
    
    # ============ PUBLICATION DATE ============
    date_elem = root.find('.//tei:publicationStmt/tei:date', namespaces)
    if date_elem is not None:
        metadata['publication_date'] = date_elem.get('when', '') or clean_text(date_elem.text or '')
    
    # ============ BODY TEXT (Preview) ============
    body_paragraphs = root.findall('.//tei:body//tei:p', namespaces)
    body_texts = []
    
    for p in body_paragraphs[:10]:  # First 10 paragraphs
        paragraph_text = ''.join(p.itertext())
        cleaned = clean_text(paragraph_text)
        if cleaned and len(cleaned) > 20:  # Skip very short paragraphs
            body_texts.append(cleaned)
    
    if body_texts:
        full_body = ' '.join(body_texts)
        metadata['body_text'] = full_body[:1500] + '...' if len(full_body) > 1500 else full_body
    
    return metadata


def get_empty_metadata() -> Dict:
    """Return empty metadata structure"""
    return {
        'title': '',
        'authors': [],
        'abstract': '',
        'keywords': [],
        'publication_date': '',
        'body_text': ''
    }


def clean_text(text: str) -> str:
    """Clean and normalize extracted text"""
    if not text:
        return ''
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common artifacts
    text = text.replace('\n', ' ').replace('\r', '')
    
    return text.strip()
