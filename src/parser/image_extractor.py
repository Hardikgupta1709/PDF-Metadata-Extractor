# """
# Extract transaction IDs and payment details from receipt images
# """
# import re
# import requests
# from PIL import Image
# import io
# import pytesseract
# from typing import Dict, Optional, List

# def extract_text_from_image_tesseract(image_file) -> str:
#     """
#     Extract text from image using Tesseract OCR (local)
#     """
#     try:
#         # Open image
#         image = Image.open(image_file)
        
#         # Convert to RGB if necessary
#         if image.mode != 'RGB':
#             image = image.convert('RGB')
        
#         # Extract text
#         text = pytesseract.image_to_string(image)
#         return text
#     except Exception as e:
#         print(f"Tesseract extraction error: {str(e)}")
#         return ""

# def extract_text_from_image_grobid(image_path: str, grobid_server: str) -> str:
#     """
#     Extract text from image/PDF using GROBID service
#     Note: GROBID is primarily for PDFs, may not work well for images
#     """
#     try:
#         url = f"{grobid_server}/api/processFulltextDocument"
        
#         with open(image_path, 'rb') as f:
#             files = {'input': f}
#             response = requests.post(url, files=files, timeout=60)
        
#         if response.status_code == 200:
#             # GROBID returns TEI XML, extract text
#             import xml.etree.ElementTree as ET
#             root = ET.fromstring(response.text)
            
#             # Extract all text nodes
#             text_parts = []
#             for elem in root.iter():
#                 if elem.text:
#                     text_parts.append(elem.text.strip())
            
#             return ' '.join(text_parts)
#         else:
#             return ""
#     except Exception as e:
#         print(f"GROBID extraction error: {str(e)}")
#         return ""

# def extract_text_from_image_easyocr(image_file) -> str:
#     """
#     Extract text using EasyOCR (better for non-English text)
#     """
#     try:
#         import easyocr
        
#         # Initialize reader (downloads model on first use)
#         reader = easyocr.Reader(['en'])  # Add more languages as needed
        
#         # Read image
#         image = Image.open(image_file)
        
#         # Convert to bytes
#         img_byte_arr = io.BytesIO()
#         image.save(img_byte_arr, format='PNG')
#         img_byte_arr = img_byte_arr.getvalue()
        
#         # Extract text
#         results = reader.readtext(img_byte_arr)
        
#         # Combine all detected text
#         text = ' '.join([result[1] for result in results])
#         return text
#     except Exception as e:
#         print(f"EasyOCR extraction error: {str(e)}")
#         return ""

# def extract_transaction_id(text: str) -> Optional[str]:
#     """
#     Extract transaction ID using common patterns
#     """
#     if not text:
#         return None
    
#     # Common transaction ID patterns
#     patterns = [
#         # Standard formats
#         r'(?:transaction|txn|trans|trx)[\s:]*[#]?\s*([A-Z0-9]{10,})',
#         r'(?:ref|reference)[\s:]*[#]?\s*([A-Z0-9]{10,})',
#         r'(?:order|payment)[\s:]*[#]?\s*([A-Z0-9]{10,})',
#         r'(?:receipt|rcpt)[\s:]*[#]?\s*([A-Z0-9]{10,})',
        
#         # UTR Number (Indian banking)
#         r'(?:utr|UTR)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        
#         # UPI patterns
#         r'(?:upi|UPI)[\s:]*[#]?\s*([0-9]{12,})',
        
#         # Generic alphanumeric IDs (12+ chars)
#         r'\b([A-Z0-9]{12,})\b',
        
#         # ID with special characters
#         r'ID[\s:]*[#]?\s*([A-Z0-9-_]{10,})',
#     ]
    
#     text_upper = text.upper()
    
#     for pattern in patterns:
#         matches = re.finditer(pattern, text_upper, re.IGNORECASE)
#         for match in matches:
#             txn_id = match.group(1)
#             # Filter out common false positives
#             if not is_false_positive(txn_id):
#                 return txn_id
    
#     return None

# def is_false_positive(text: str) -> bool:
#     """
#     Filter out common false positives
#     """
#     false_positives = [
#         'PHONE', 'EMAIL', 'ADDRESS', 'CUSTOMER',
#         'MERCHANT', 'BANK', 'ACCOUNT', 'IFSC',
#         'DETAILS', 'PAYMENT', 'AMOUNT', 'DATE'
#     ]
    
#     text_upper = text.upper()
    
#     # Too short or too long
#     if len(text) < 8 or len(text) > 50:
#         return True
    
#     # Contains common words
#     for fp in false_positives:
#         if fp in text_upper:
#             return True
    
#     # All same character
#     if len(set(text)) < 3:
#         return True
    
#     return False

# def extract_payment_details(text: str) -> Dict[str, Optional[str]]:
#     """
#     Extract comprehensive payment information
#     """
#     details = {
#         'transaction_id': None,
#         'amount': None,
#         'date': None,
#         'time': None,
#         'payment_method': None,
#         'status': None,
#         'upi_id': None,
#         'bank_name': None
#     }
    
#     if not text:
#         return details
    
#     text_upper = text.upper()
    
#     # Extract transaction ID
#     details['transaction_id'] = extract_transaction_id(text)
    
#     # Extract amount (₹, Rs, INR, $, etc.)
#     amount_patterns = [
#         r'(?:amount|amt|total|paid)[\s:]*[₹$]?\s*([0-9,]+\.?[0-9]*)',
#         r'[₹$]\s*([0-9,]+\.?[0-9]*)',
#         r'(?:rs|inr)[\s.]*([0-9,]+\.?[0-9]*)'
#     ]
    
#     for pattern in amount_patterns:
#         match = re.search(pattern, text_upper, re.IGNORECASE)
#         if match:
#             details['amount'] = match.group(1).replace(',', '')
#             break
    
#     # Extract date (DD-MM-YYYY, DD/MM/YYYY, etc.)
#     date_patterns = [
#         r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
#         r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
#         r'\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b'
#     ]
    
#     for pattern in date_patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             details['date'] = match.group(1)
#             break
    
#     # Extract time
#     time_pattern = r'\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?)\b'
#     match = re.search(time_pattern, text, re.IGNORECASE)
#     if match:
#         details['time'] = match.group(1)
    
#     # Extract UPI ID
#     upi_pattern = r'([a-zA-Z0-9._-]+@[a-zA-Z]+)'
#     match = re.search(upi_pattern, text)
#     if match:
#         details['upi_id'] = match.group(1)
    
#     # Extract payment method
#     payment_methods = ['UPI', 'CREDIT CARD', 'DEBIT CARD', 'NET BANKING', 
#                       'WALLET', 'PAYTM', 'PHONEPE', 'GPAY', 'GOOGLE PAY']
#     for method in payment_methods:
#         if method in text_upper:
#             details['payment_method'] = method
#             break
    
#     # Extract status
#     statuses = ['SUCCESS', 'SUCCESSFUL', 'COMPLETED', 'PAID', 
#                 'FAILED', 'PENDING', 'DECLINED']
#     for status in statuses:
#         if status in text_upper:
#             details['status'] = status
#             break
    
#     # Extract bank name
#     banks = ['SBI', 'HDFC', 'ICICI', 'AXIS', 'KOTAK', 'PNB', 
#              'BOB', 'CANARA', 'UNION', 'IDBI', 'YES BANK']
#     for bank in banks:
#         if bank in text_upper:
#             details['bank_name'] = bank
#             break
    
#     return details

# def extract_payment_info_from_image(image_file, grobid_server: str = None, 
#                                    use_tesseract: bool = True,
#                                    use_easyocr: bool = False) -> Dict[str, Optional[str]]:
#     """
#     Main function to extract payment information from receipt image
    
#     Args:
#         image_file: Uploaded image file (Streamlit UploadedFile or file path)
#         grobid_server: GROBID server URL (optional)
#         use_tesseract: Use Tesseract OCR (default: True)
#         use_easyocr: Use EasyOCR (default: False, better accuracy but slower)
    
#     Returns:
#         Dictionary with extracted payment details
#     """
#     extracted_text = ""
    
#     # Try different OCR methods
#     if use_easyocr:
#         try:
#             extracted_text = extract_text_from_image_easyocr(image_file)
#             if extracted_text:
#                 print("✓ Text extracted using EasyOCR")
#         except Exception as e:
#             print(f"EasyOCR failed: {str(e)}")
    
#     if not extracted_text and use_tesseract:
#         try:
#             # Reset file pointer if it's a file object
#             if hasattr(image_file, 'seek'):
#                 image_file.seek(0)
            
#             extracted_text = extract_text_from_image_tesseract(image_file)
#             if extracted_text:
#                 print("✓ Text extracted using Tesseract")
#         except Exception as e:
#             print(f"Tesseract failed: {str(e)}")
    
#     if not extracted_text:
#         print("⚠️ No text could be extracted from image")
#         return {
#             'transaction_id': None,
#             'amount': None,
#             'date': None,
#             'time': None,
#             'payment_method': None,
#             'status': None,
#             'upi_id': None,
#             'bank_name': None,
#             'raw_text': ""
#         }
    
#     # Extract payment details
#     details = extract_payment_details(extracted_text)
#     details['raw_text'] = extracted_text[:500]  # Store first 500 chars
    
#     return details

# def format_payment_details(details: Dict) -> str:
#     """
#     Format payment details for display
#     """
#     lines = []
    
#     if details.get('transaction_id'):
#         lines.append(f"🆔 Transaction ID: {details['transaction_id']}")
    
#     if details.get('amount'):
#         lines.append(f"💰 Amount: ₹{details['amount']}")
    
#     if details.get('date'):
#         lines.append(f"📅 Date: {details['date']}")
    
#     if details.get('time'):
#         lines.append(f"⏰ Time: {details['time']}")
    
#     if details.get('payment_method'):
#         lines.append(f"💳 Method: {details['payment_method']}")
    
#     if details.get('status'):
#         lines.append(f"✅ Status: {details['status']}")
    
#     if details.get('upi_id'):
#         lines.append(f"🔗 UPI ID: {details['upi_id']}")
    
#     if details.get('bank_name'):
#         lines.append(f"🏦 Bank: {details['bank_name']}")
    
#     return '\n'.join(lines) if lines else "No payment details extracted"



"""
Extract transaction IDs and payment details from receipt images
"""
import re
import requests
from PIL import Image
import io
import pytesseract
from typing import Dict, Optional, List

def extract_text_from_image_tesseract(image_file) -> str:
    """
    Extract text from image using Tesseract OCR (local)
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Tesseract extraction error: {str(e)}")
        return ""

def extract_text_from_image_grobid(image_path: str, grobid_server: str) -> str:
    """
    Extract text from image/PDF using GROBID service
    Note: GROBID is primarily for PDFs, may not work well for images
    """
    try:
        url = f"{grobid_server}/api/processFulltextDocument"
        
        with open(image_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(url, files=files, timeout=60)
        
        if response.status_code == 200:
            # GROBID returns TEI XML, extract text
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            # Extract all text nodes
            text_parts = []
            for elem in root.iter():
                if elem.text:
                    text_parts.append(elem.text.strip())
            
            return ' '.join(text_parts)
        else:
            return ""
    except Exception as e:
        print(f"GROBID extraction error: {str(e)}")
        return ""

def extract_text_from_image_easyocr(image_file) -> str:
    """
    Extract text using EasyOCR (better for non-English text)
    """
    try:
        import easyocr
        
        # Initialize reader (downloads model on first use)
        reader = easyocr.Reader(['en'])  # Add more languages as needed
        
        # Read image
        image = Image.open(image_file)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Extract text
        results = reader.readtext(img_byte_arr)
        
        # Combine all detected text
        text = ' '.join([result[1] for result in results])
        return text
    except Exception as e:
        print(f"EasyOCR extraction error: {str(e)}")
        return ""

def extract_transaction_id(text: str) -> Optional[str]:
    """
    Extract transaction ID with improved pattern matching
    """
    if not text:
        return None
    
    text_upper = text.upper()
    
    # Priority 1: Look for explicit "Transaction ID" label
    explicit_patterns = [
        r'TRANSACTION\s*ID[:\s]*([A-Z0-9]{12,})',
        r'TXN\s*ID[:\s]*([A-Z0-9]{12,})',
        r'TRANS\s*ID[:\s]*([A-Z0-9]{12,})',
        r'REF(?:ERENCE)?\s*(?:NO|NUMBER)?[:\s]*([A-Z0-9]{12,})',
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, text_upper)
        if match:
            txn_id = match.group(1).strip()
            if not is_false_positive(txn_id):
                return txn_id
    
    # Priority 2: Look for UTR numbers
    utr_pattern = r'UTR[:\s]*([0-9]{12,})'
    match = re.search(utr_pattern, text_upper)
    if match:
        return match.group(1)
    
    # Priority 3: Look for IDs starting with 'T' followed by digits (PhonePe pattern)
    phonepe_pattern = r'\b(T[0-9]{20,})\b'
    match = re.search(phonepe_pattern, text_upper)
    if match:
        return match.group(1)
    
    # Priority 4: Look for long alphanumeric IDs (16+ chars, avoiding common words)
    generic_pattern = r'\b([A-Z0-9]{16,})\b'
    matches = re.finditer(generic_pattern, text_upper)
    
    for match in matches:
        txn_id = match.group(1)
        if not is_false_positive(txn_id):
            # Additional check: must have both letters and numbers
            if re.search(r'[A-Z]', txn_id) and re.search(r'[0-9]', txn_id):
                return txn_id
            # Or be purely numeric with 12+ digits
            elif txn_id.isdigit() and len(txn_id) >= 12:
                return txn_id
    
    return None

def is_false_positive(text: str) -> bool:
    """
    Improved false positive detection
    """
    if not text:
        return True
    
    # List of words that are NOT transaction IDs
    false_positives = [
        'SUCCESSFUL', 'SUCCESS', 'FAILED', 'PENDING', 'COMPLETED',
        'TRANSACTION', 'PAYMENT', 'DETAILS', 'SUMMARY',
        'PHONE', 'EMAIL', 'ADDRESS', 'CUSTOMER', 'MERCHANT',
        'BANK', 'ACCOUNT', 'IFSC', 'AMOUNT', 'DATE', 'TIME',
        'BALANCE', 'AVAILABLE', 'CREDITED', 'DEBITED',
        'XXXXXXX',  # Masked account numbers
    ]
    
    text_upper = text.upper()
    
    # Check if it's a known false positive
    if text_upper in false_positives:
        return True
    
    # Check if it contains false positive substrings
    for fp in false_positives:
        if text_upper == fp or text_upper.startswith(fp) or text_upper.endswith(fp):
            return True
    
    # Too short or too long
    if len(text) < 10 or len(text) > 30:
        return True
    
    # All same character (like XXXXXX)
    if len(set(text)) < 4:
        return True
    
    # Check if it's a masked number (contains X)
    if 'X' in text_upper and text_upper.count('X') > len(text) / 2:
        return True
    
    return False

def extract_payment_details(text: str) -> Dict[str, Optional[str]]:
    """
    Extract comprehensive payment information with better parsing
    """
    details = {
        'transaction_id': None,
        'amount': None,
        'date': None,
        'time': None,
        'payment_method': None,
        'status': None,
        'upi_id': None,
        'bank_name': None
    }
    
    if not text:
        return details
    
    text_upper = text.upper()
    
    # Extract transaction ID (improved)
    details['transaction_id'] = extract_transaction_id(text)
    
    # Extract amount - look near ₹ symbol or amount keywords
    amount_patterns = [
        r'₹\s*([0-9,]+(?:\.[0-9]{2})?)',  # ₹99 or ₹99.00
        r'RS\.?\s*([0-9,]+(?:\.[0-9]{2})?)',  # Rs. 99
        r'INR\s*([0-9,]+(?:\.[0-9]{2})?)',  # INR 99
        r'(?:AMOUNT|AMT|PAID|TOTAL)[:\s]*₹?\s*([0-9,]+(?:\.[0-9]{2})?)',
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text_upper)
        if match:
            amount = match.group(1).replace(',', '')
            # Validate amount (should be reasonable)
            try:
                amount_float = float(amount)
                if 1 <= amount_float <= 1000000:  # ₹1 to ₹10 lakh
                    details['amount'] = amount
                    break
            except ValueError:
                continue
    
    # Extract date with improved patterns
    date_patterns = [
        r'(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{4})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_upper)
        if match:
            details['date'] = match.group(1)
            break
    
    # Extract time
    time_patterns = [
        r'(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)',
        r'(?:TIME|AT)[:\s]*(\d{1,2}:\d{2}(?::\d{2})?)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text_upper)
        if match:
            details['time'] = match.group(1)
            break
    
    # Extract UPI ID (more specific pattern)
    upi_pattern = r'\b([a-zA-Z0-9._-]+@[a-zA-Z]{3,})\b'
    match = re.search(upi_pattern, text)
    if match:
        upi_candidate = match.group(1)
        # Validate it's actually a UPI ID (not email)
        if not any(domain in upi_candidate.lower() for domain in ['gmail', 'yahoo', 'outlook', 'hotmail']):
            details['upi_id'] = upi_candidate
    
    # Extract payment method
    payment_methods = {
        'PAYTM': 'Paytm',
        'PHONEPE': 'PhonePe',
        'GPAY': 'Google Pay',
        'GOOGLE PAY': 'Google Pay',
        'UPI': 'UPI',
        'CREDIT CARD': 'Credit Card',
        'DEBIT CARD': 'Debit Card',
        'NET BANKING': 'Net Banking',
        'WALLET': 'Wallet',
    }
    
    for method, display_name in payment_methods.items():
        if method in text_upper:
            details['payment_method'] = display_name
            break
    
    # Extract status
    status_patterns = {
        'SUCCESS': 'Success',
        'SUCCESSFUL': 'Success',
        'COMPLETED': 'Completed',
        'PAID': 'Paid',
        'FAILED': 'Failed',
        'PENDING': 'Pending',
        'DECLINED': 'Declined',
    }
    
    for status_key, status_value in status_patterns.items():
        if status_key in text_upper:
            details['status'] = status_value
            break
    
    # Extract bank name
    banks = {
        'AXIS': 'Axis Bank',
        'SBI': 'State Bank of India',
        'HDFC': 'HDFC Bank',
        'ICICI': 'ICICI Bank',
        'KOTAK': 'Kotak Mahindra Bank',
        'PNB': 'Punjab National Bank',
        'BOB': 'Bank of Baroda',
        'CANARA': 'Canara Bank',
        'UNION': 'Union Bank',
        'IDBI': 'IDBI Bank',
        'YES BANK': 'Yes Bank',
    }
    
    for bank_key, bank_name in banks.items():
        if bank_key in text_upper:
            details['bank_name'] = bank_name
            break
    
    return details

def extract_payment_info_from_image(image_file, grobid_server: str = None, 
                                   use_tesseract: bool = True,
                                   use_easyocr: bool = False) -> Dict[str, Optional[str]]:
    """
    Main function to extract payment information from receipt image
    
    Args:
        image_file: Uploaded image file (Streamlit UploadedFile or file path)
        grobid_server: GROBID server URL (optional)
        use_tesseract: Use Tesseract OCR (default: True)
        use_easyocr: Use EasyOCR (default: False, better accuracy but slower)
    
    Returns:
        Dictionary with extracted payment details
    """
    extracted_text = ""
    
    # Try different OCR methods
    if use_easyocr:
        try:
            extracted_text = extract_text_from_image_easyocr(image_file)
            if extracted_text:
                print("✓ Text extracted using EasyOCR")
        except Exception as e:
            print(f"EasyOCR failed: {str(e)}")
    
    if not extracted_text and use_tesseract:
        try:
            # Reset file pointer if it's a file object
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            extracted_text = extract_text_from_image_tesseract(image_file)
            if extracted_text:
                print("✓ Text extracted using Tesseract")
        except Exception as e:
            print(f"Tesseract failed: {str(e)}")
    
    if not extracted_text:
        print("⚠️ No text could be extracted from image")
        return {
            'transaction_id': None,
            'amount': None,
            'date': None,
            'time': None,
            'payment_method': None,
            'status': None,
            'upi_id': None,
            'bank_name': None,
            'raw_text': ""
        }
    
    # Extract payment details
    details = extract_payment_details(extracted_text)
    details['raw_text'] = extracted_text[:500]  # Store first 500 chars
    
    return details

def format_payment_details(details: Dict) -> str:
    """
    Format payment details for display with emojis
    """
    lines = []
    
    if details.get('transaction_id'):
        lines.append(f" Transaction ID: {details['transaction_id']}\n")
    
    if details.get('amount'):
        lines.append(f" Amount: ₹{details['amount']}")
    
    if details.get('date'):
        lines.append(f"date: {details['date']}")
    
    if details.get('time'):
        lines.append(f"Time: {details['time']}\n")
    
    if details.get('payment_method'):
        lines.append(f" Method: {details['payment_method']}\n")
    
    if details.get('status'):
        emoji = "✅" if details['status'].lower() in ['success', 'completed', 'paid'] else "⚠️"
        lines.append(f"{emoji} Status: {details['status']}\n")
    
    if details.get('upi_id'):
        lines.append(f" UPI ID: {details['upi_id']}\n")
    
    if details.get('bank_name'):
        lines.append(f"Bank: {details['bank_name']}\n")
    
    return '\n'.join(lines) if lines else "❌ No payment details extracted"