import requests
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET


def parse_pdf_with_grobid(pdf_path: str, grobid_server: str = "https://kermitt2-grobid.hf.space") -> Optional[str]:
    """
    Parse PDF using GROBID server and return TEI XML
    
    Args:
        pdf_path: Path to the PDF file
        grobid_server: GROBID server URL (default: public HuggingFace instance)
    
    Returns:
        TEI XML string or None if parsing fails
    """
    try:
        endpoint = f"{grobid_server}/api/processFulltextDocument"
        
        with open(pdf_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(
                endpoint,
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            return response.text
        else:
            print(f"GROBID error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("GROBID server timeout")
        return None
    except requests.exceptions.ConnectionError:
        print("Cannot connect to GROBID server")
        return None
    except Exception as e:
        print(f"GROBID parsing error: {e}")
        return None


def extract_metadata_from_tei(tei_xml: str) -> dict:
    """
    Extract metadata from GROBID TEI XML
    
    Args:
        tei_xml: TEI XML string from GROBID
    
    Returns:
        Dictionary with extracted metadata
    """
    metadata = {
        'title': '',
        'authors': [],
        'abstract': '',
        'keywords': [],
        'affiliations': [],
        'emails': []
    }
    
    try:
        root = ET.fromstring(tei_xml)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        # Extract title
        title_elem = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
        if title_elem is not None and title_elem.text:
            metadata['title'] = title_elem.text.strip()
        
        # Extract authors
        for author in root.findall('.//tei:sourceDesc//tei:author', ns):
            persName = author.find('.//tei:persName', ns)
            if persName is not None:
                forename = persName.find('.//tei:forename', ns)
                surname = persName.find('.//tei:surname', ns)
                
                author_name = ""
                if forename is not None and forename.text:
                    author_name += forename.text.strip()
                if surname is not None and surname.text:
                    if author_name:
                        author_name += " "
                    author_name += surname.text.strip()
                
                if author_name:
                    metadata['authors'].append(author_name)
            
            # Extract email
            email_elem = author.find('.//tei:email', ns)
            if email_elem is not None and email_elem.text:
                metadata['emails'].append(email_elem.text.strip())
        
        # Extract abstract
        abstract_elem = root.find('.//tei:abstract/tei:div/tei:p', ns)
        if abstract_elem is not None and abstract_elem.text:
            metadata['abstract'] = abstract_elem.text.strip()
        elif abstract_elem is not None:
            # Sometimes abstract has multiple elements
            abstract_text = ''.join(abstract_elem.itertext()).strip()
            if abstract_text:
                metadata['abstract'] = abstract_text
        
        # Extract keywords
        for keyword in root.findall('.//tei:keywords/tei:term', ns):
            if keyword.text:
                metadata['keywords'].append(keyword.text.strip())
        
        # Extract affiliations
        for affiliation in root.findall('.//tei:affiliation', ns):
            org_name = affiliation.find('.//tei:orgName', ns)
            if org_name is not None and org_name.text:
                metadata['affiliations'].append(org_name.text.strip())
        
    except Exception as e:
        print(f"Error parsing TEI XML: {e}")
    
    return metadata


def extract_affiliations_from_tei(tei_xml: str) -> list:
    """
    Extract affiliations from TEI XML
    
    Args:
        tei_xml: TEI XML string from GROBID
    
    Returns:
        List of affiliation strings
    """
    try:
        root = ET.fromstring(tei_xml)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        affiliations = []
        
        for affil in root.findall('.//tei:affiliation', ns):
            org_name = affil.find('.//tei:orgName', ns)
            if org_name is not None and org_name.text:
                affiliations.append(org_name.text.strip())
        
        return list(set(affiliations))  # Remove duplicates
    except Exception as e:
        print(f"Error extracting affiliations: {e}")
        return []
