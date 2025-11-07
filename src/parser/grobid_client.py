"""
GROBID client for parsing PDF files - Improved version
"""
import requests
import time
from typing import Dict, List, Optional
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


def extract_text_from_element(element) -> str:
    """Helper to extract all text from an XML element, handling nested tags"""
    if element is None:
        return ""
    return ''.join(element.itertext()).strip()


def extract_title_from_tei(root, ns: dict) -> Optional[str]:
    """
    Extract title using multiple fallback strategies.
    GROBID can place titles in different locations depending on PDF structure.
    """
    # Strategy 1: Main title in titleStmt (most common)
    title_elem = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
    if title_elem is not None:
        title = extract_text_from_element(title_elem)
        if title:
            return title
    
    # Strategy 2: Any title in titleStmt (without type attribute)
    title_elem = root.find('.//tei:titleStmt/tei:title', ns)
    if title_elem is not None:
        title = extract_text_from_element(title_elem)
        if title:
            return title
    
    # Strategy 3: Title in analytic section (for journal articles)
    title_elem = root.find('.//tei:analytic/tei:title[@type="main"]', ns)
    if title_elem is not None:
        title = extract_text_from_element(title_elem)
        if title:
            return title
    
    # Strategy 4: Any title in analytic
    title_elem = root.find('.//tei:analytic/tei:title', ns)
    if title_elem is not None:
        title = extract_text_from_element(title_elem)
        if title:
            return title
    
    # Strategy 5: Title in biblStruct
    title_elem = root.find('.//tei:biblStruct//tei:title[@type="main"]', ns)
    if title_elem is not None:
        title = extract_text_from_element(title_elem)
        if title:
            return title
    
    # Strategy 6: Any title element in the document (last resort)
    all_titles = root.findall('.//tei:title', ns)
    for title_elem in all_titles:
        title = extract_text_from_element(title_elem)
        # Filter out very short titles (likely section headers)
        if title and len(title) > 10:
            return title
    
    return None


def extract_metadata_from_tei(tei_xml: str, debug: bool = False) -> Dict:
    """
    Extract metadata from TEI XML returned by GROBID.
    
    Args:
        tei_xml: TEI XML string from GROBID
        debug: If True, print debug information
    
    Returns:
        Dictionary containing extracted metadata
    """
    # Parse XML
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as e:
        print(f"⚠️ XML Parse Error: {e}")
        return {
            'title': None,
            'authors': [],
            'abstract': None,
            'keywords': [],
            'publication_date': None,
            'body_text': None,
            'emails': []
        }
    
    # Define namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    metadata = {
        'title': None,
        'authors': [],
        'abstract': None,
        'keywords': [],
        'publication_date': None,
        'body_text': None,
        'emails': [],
        'affiliations': []
    }
    
    # Extract title using improved method
    metadata['title'] = extract_title_from_tei(root, ns)
    
    if debug and metadata['title']:
        print(f"✅ Title extracted: {metadata['title'][:100]}...")
    elif debug:
        print("⚠️ No title found in TEI XML")
    
    # Extract authors - try multiple locations
    # Location 1: sourceDesc (most common)
    authors = root.findall('.//tei:sourceDesc//tei:author', ns)
    if not authors:
        # Location 2: analytic section
        authors = root.findall('.//tei:analytic//tei:author', ns)
    if not authors:
        # Location 3: biblStruct
        authors = root.findall('.//tei:biblStruct//tei:author', ns)
    
    for author in authors:
        # Try persName structure
        pers_name = author.find('.//tei:persName', ns)
        if pers_name is not None:
            forename = pers_name.find('.//tei:forename', ns)
            surname = pers_name.find('.//tei:surname', ns)
            
            if forename is not None and surname is not None:
                full_name = f"{forename.text} {surname.text}".strip()
                if full_name:
                    metadata['authors'].append(full_name)
            elif surname is not None and surname.text:
                metadata['authors'].append(surname.text.strip())
        else:
            # Try direct forename/surname
            forename = author.find('.//tei:forename', ns)
            surname = author.find('.//tei:surname', ns)
            
            if forename is not None and surname is not None:
                full_name = f"{forename.text} {surname.text}".strip()
                if full_name:
                    metadata['authors'].append(full_name)
            elif surname is not None and surname.text:
                metadata['authors'].append(surname.text.strip())
    
    if debug:
        print(f"✅ Authors extracted: {len(metadata['authors'])}")
    
    # Extract abstract - try multiple locations
    abstract_elem = root.find('.//tei:profileDesc/tei:abstract/tei:div/tei:p', ns)
    if abstract_elem is None:
        # Try without div
        abstract_elem = root.find('.//tei:profileDesc/tei:abstract/tei:p', ns)
    if abstract_elem is None:
        # Try in body
        abstract_elem = root.find('.//tei:abstract/tei:p', ns)
    
    if abstract_elem is not None:
        metadata['abstract'] = extract_text_from_element(abstract_elem)
    
    if debug:
        if metadata['abstract']:
            print(f"✅ Abstract extracted: {len(metadata['abstract'])} chars")
        else:
            print("⚠️ No abstract found")
    
    # Extract keywords
    keywords = root.findall('.//tei:keywords/tei:term', ns)
    metadata['keywords'] = [kw.text.strip() for kw in keywords if kw.text]
    
    # Also try keywords[@scheme="author"]
    if not metadata['keywords']:
        keywords = root.findall('.//tei:keywords[@scheme="author"]/tei:term', ns)
        metadata['keywords'] = [kw.text.strip() for kw in keywords if kw.text]
    
    if debug:
        print(f"✅ Keywords extracted: {len(metadata['keywords'])}")
    
    # Extract affiliations
    affiliations = root.findall('.//tei:affiliation', ns)
    for affil in affiliations:
        org_name = affil.find('.//tei:orgName', ns)
        if org_name is not None and org_name.text:
            metadata['affiliations'].append(org_name.text.strip())
        else:
            # Get all text if no orgName
            affil_text = extract_text_from_element(affil)
            if affil_text and len(affil_text) > 3:
                metadata['affiliations'].append(affil_text)
    
    # Remove duplicates
    metadata['affiliations'] = list(set(metadata['affiliations']))
    
    if debug:
        print(f"✅ Affiliations extracted: {len(metadata['affiliations'])}")
    
    # Extract publication date
    date_elem = root.find('.//tei:publicationStmt/tei:date', ns)
    if date_elem is not None:
        metadata['publication_date'] = date_elem.get('when') or date_elem.text
    
    # Extract body text (first 2000 chars for better context)
    body_elem = root.find('.//tei:text/tei:body', ns)
    if body_elem is not None:
        body_text = extract_text_from_element(body_elem)
        metadata['body_text'] = body_text[:2000] if body_text else None
    
    if debug:
        print("\n=== Extraction Summary ===")
        print(f"Title: {'✅' if metadata['title'] else '❌'}")
        print(f"Authors: {len(metadata['authors'])}")
        print(f"Abstract: {'✅' if metadata['abstract'] else '❌'}")
        print(f"Keywords: {len(metadata['keywords'])}")
        print(f"Affiliations: {len(metadata['affiliations'])}")
        print("=" * 25)
    
    return metadata


def debug_tei_structure(tei_xml: str, output_file: str = None):
    """
    Debug helper to inspect TEI XML structure.
    Useful when extraction fails.
    """
    try:
        root = ET.fromstring(tei_xml)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        print("\n=== TEI XML Structure Debug ===")
        
        # Find all title elements
        print("\n📄 All <title> elements found:")
        all_titles = root.findall('.//tei:title', ns)
        for i, title in enumerate(all_titles, 1):
            title_type = title.get('type', 'no-type')
            title_text = extract_text_from_element(title)
            parent = title.find('..')
            parent_tag = parent.tag.split('}')[-1] if parent is not None else 'unknown'
            print(f"  {i}. Type: {title_type}, Parent: {parent_tag}")
            print(f"     Text: {title_text[:100]}...")
        
        # Find all author elements
        print("\n👥 All <author> elements found:")
        all_authors = root.findall('.//tei:author', ns)
        print(f"  Total: {len(all_authors)}")
        
        # Find abstract
        print("\n📝 Abstract locations:")
        abstract_paths = [
            './/tei:profileDesc/tei:abstract',
            './/tei:abstract',
        ]
        for path in abstract_paths:
            elem = root.find(path, ns)
            if elem is not None:
                print(f"  ✅ Found at: {path}")
        
        print("=" * 35)
        
        # Optionally save to file
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(tei_xml)
            print(f"\n💾 TEI XML saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
