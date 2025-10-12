import requests
from xml.etree import ElementTree as ET


def parse_pdf_with_grobid(pdf_path: str, grobid_server: str) -> str:
    """
    Send PDF to GROBID server and get TEI XML response.
    """
    url = f"{grobid_server}/api/processFulltextDocument"
    
    with open(pdf_path, 'rb') as pdf_file:
        files = {'input': pdf_file}
        response = requests.post(url, files=files)
        response.raise_for_status()
        
    return response.text


def extract_metadata_from_tei(tei_xml: str) -> dict:
    """
    Extract metadata from GROBID's TEI XML output.
    """
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = ET.fromstring(tei_xml)
    
    metadata = {
        'title': '',
        'authors': [],
        'abstract': '',
        'keywords': [],
        'publication_date': '',
        'body_text': ''
    }
    
    # Extract title from titleStmt
    title_elem = root.find('.//tei:titleStmt/tei:title', namespaces)
    if title_elem is not None and title_elem.text:
        metadata['title'] = title_elem.text.strip()
    
    # If title is empty, try to get from first heading in body
    if not metadata['title']:
        first_head = root.find('.//tei:body//tei:head', namespaces)
        if first_head is not None and first_head.text:
            metadata['title'] = first_head.text.strip()
    
    # Extract authors
    authors = root.findall('.//tei:sourceDesc//tei:author', namespaces)
    for author in authors:
        forename = author.find('.//tei:forename', namespaces)
        surname = author.find('.//tei:surname', namespaces)
        
        name_parts = []
        if forename is not None and forename.text:
            name_parts.append(forename.text.strip())
        if surname is not None and surname.text:
            name_parts.append(surname.text.strip())
        
        if name_parts:
            metadata['authors'].append(' '.join(name_parts))
    
    # Extract abstract
    abstract_elem = root.find('.//tei:abstract', namespaces)
    if abstract_elem is not None:
        abstract_texts = []
        for elem in abstract_elem.iter():
            if elem.text:
                abstract_texts.append(elem.text.strip())
        metadata['abstract'] = ' '.join(abstract_texts)
    
    # Extract keywords
    keywords = root.findall('.//tei:keywords//tei:term', namespaces)
    metadata['keywords'] = [kw.text.strip() for kw in keywords if kw.text]
    
    # Extract publication date
    date_elem = root.find('.//tei:publicationStmt/tei:date', namespaces)
    if date_elem is not None:
        metadata['publication_date'] = date_elem.get('when', '')
    
    # Extract body text (first 1000 characters for preview)
    body_paragraphs = root.findall('.//tei:body//tei:p', namespaces)
    body_texts = []
    for p in body_paragraphs:
        if p.text:
            body_texts.append(p.text.strip())
        for elem in p.iter():
            if elem.text and elem != p:
                body_texts.append(elem.text.strip())
    
    full_body = ' '.join(body_texts)
    metadata['body_text'] = full_body[:1000] + '...' if len(full_body) > 1000 else full_body
    
    return metadata