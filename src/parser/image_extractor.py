"""
Extract transaction IDs and payment details from receipt images
"""
import re
from PIL import Image, ImageEnhance
import io
import pytesseract
from typing import Dict, Optional

def extract_text_from_image_tesseract(image_file) -> str:
    """
    Extract text from image using Tesseract OCR with enhanced preprocessing
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhance image for better OCR
        # 1. Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 2. Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        # Try multiple PSM modes for better results
        texts = []
        for psm in [6, 3, 11, 4]:  # Different page segmentation modes
            try:
                custom_config = f'--oem 3 --psm {psm}'
                extracted = pytesseract.image_to_string(image, config=custom_config)
                texts.append(extracted)
            except:
                continue
        
        # Return the longest extracted text (usually most accurate)
        return max(texts, key=len) if texts else ""
        
    except Exception as e:
        print(f"❌ Tesseract extraction error: {str(e)}")
        return ""

def extract_text_from_image_easyocr(image_file) -> str:
    """
    Extract text using EasyOCR (better for non-English text)
    """
    try:
        import easyocr
        
        # Initialize reader
        reader = easyocr.Reader(['en'], gpu=False)
        
        # Read image
        image = Image.open(image_file)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Extract text
        results = reader.readtext(img_byte_arr, detail=0)
        
        # Combine all detected text
        text = ' '.join(results)
        return text
        
    except Exception as e:
        print(f"❌ EasyOCR extraction error: {str(e)}")
        return ""

def extract_payment_info_from_image(image_file, grobid_server: str = None, 
                                   use_tesseract: bool = True,
                                   use_easyocr: bool = False) -> Dict[str, Optional[str]]:
    """
    Main function to extract payment information from receipt image with improved accuracy
    """
    extracted_text = ""
    
    # Try EasyOCR first (better accuracy but slower)
    if use_easyocr:
        try:
            extracted_text = extract_text_from_image_easyocr(image_file)
            if extracted_text:
                print("✅ Text extracted using EasyOCR")
        except Exception as e:
            print(f"⚠️ EasyOCR failed: {str(e)}")
    
    # Fallback to Tesseract
    if not extracted_text and use_tesseract:
        try:
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            
            extracted_text = extract_text_from_image_tesseract(image_file)
            if extracted_text:
                print("✅ Text extracted using Tesseract")
        except Exception as e:
            print(f"⚠️ Tesseract failed: {str(e)}")
    
    if not extracted_text:
        print("❌ No text could be extracted from image")
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
    
    # Extract payment details with enhanced patterns
    details = extract_payment_details_enhanced(extracted_text)
    details['raw_text'] = extracted_text[:1000]  # Store first 1000 chars
    
    # Debug output
    print(f"📝 Extracted text length: {len(extracted_text)} chars")
    print(f"💳 Transaction ID: {details['transaction_id']}")
    print(f"💰 Amount: {details['amount']}")
    
    return details

def extract_payment_details_enhanced(text: str) -> Dict[str, Optional[str]]:
    """
    Enhanced extraction with better pattern matching
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
    
    # ============ TRANSACTION ID (Most Important) ============
    txn_patterns = [
        # Explicit labels
        r'(?:TRANSACTION\s*(?:ID|NO|NUMBER)|TXN\s*(?:ID|NO)|TRANS\s*ID)[:\s]*([A-Z0-9]{10,30})',
        r'(?:UTR\s*(?:NO|NUMBER|REF)?)[:\s]*([0-9]{12,22})',
        r'(?:REFERENCE\s*(?:NO|NUMBER|ID)?)[:\s]*([A-Z0-9]{12,30})',
        r'(?:ORDER\s*(?:ID|NO))[:\s]*([A-Z0-9]{10,30})',
        r'(?:PAYMENT\s*(?:ID|REF))[:\s]*([A-Z0-9]{10,30})',
        
        # PhonePe pattern: T followed by 20+ digits
        r'\b(T[0-9]{20,})\b',
        
        # PayTM pattern: Usually starts with numbers
        r'\b([0-9]{16,20})\b',
        
        # Google Pay / Other UPI: Mixed alphanumeric
        r'\b([A-Z0-9]{16,25})\b',
    ]
    
    for pattern in txn_patterns:
        match = re.search(pattern, text_upper)
        if match:
            candidate = match.group(1).strip()
            
            # Validation: Not a false positive
            if not is_false_positive(candidate):
                # Must have variety of characters
                if len(set(candidate)) >= 6:
                    details['transaction_id'] = candidate
                    print(f"✅ Found Transaction ID with pattern: {pattern[:30]}...")
                    break
    
    # ============ AMOUNT ============
    amount_patterns = [
        r'(?:PAID|AMOUNT|AMT|TOTAL|PAID\s*AMOUNT)[:\s]*[₹RS\.\s]*([0-9,]+\.?[0-9]{0,2})',
        r'[₹₨]\s*([0-9,]+\.?[0-9]{0,2})',
        r'RS\.?\s*([0-9,]+\.?[0-9]{0,2})',
        r'INR\s*([0-9,]+\.?[0-9]{0,2})',
        r'\b([0-9]{1,6}\.[0-9]{2})\b',  # Decimal amounts like 99.00
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text_upper)
        if match:
            amount = match.group(1).replace(',', '').strip()
            try:
                amount_float = float(amount)
                # Reasonable amount range: ₹1 to ₹1 crore
                if 1 <= amount_float <= 10000000:
                    details['amount'] = amount
                    print(f"✅ Found Amount: ₹{amount}")
                    break
            except ValueError:
                continue
    
    # ============ DATE ============
    date_patterns = [
        r'(\d{1,2}\s+(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:TEMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)\s*,?\s*\d{2,4})',
        r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
        r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
        r'(?:DATE|ON)[:\s]*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_upper)
        if match:
            details['date'] = match.group(1).strip()
            print(f"✅ Found Date: {details['date']}")
            break
    
    # ============ TIME ============
    time_patterns = [
        r'(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)',
        r'(?:TIME|AT)[:\s]*(\d{1,2}:\d{2}(?::\d{2})?)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text_upper)
        if match:
            details['time'] = match.group(1).strip()
            break
    
    # ============ UPI ID ============
    upi_pattern = r'\b([a-zA-Z0-9._-]{3,}@[a-zA-Z]{3,})\b'
    match = re.search(upi_pattern, text)
    if match:
        upi_candidate = match.group(1).lower()
        # Exclude common email domains
        if not any(domain in upi_candidate for domain in ['gmail', 'yahoo', 'outlook', 'hotmail', 'email']):
            details['upi_id'] = upi_candidate
            print(f"✅ Found UPI ID: {upi_candidate}")
    
    # ============ PAYMENT METHOD ============
    payment_methods = {
        'PHONEPE': 'PhonePe',
        'PHONE PE': 'PhonePe',
        'PAYTM': 'Paytm',
        'GPAY': 'Google Pay',
        'GOOGLE PAY': 'Google Pay',
        'AMAZON PAY': 'Amazon Pay',
        'BHIM': 'BHIM UPI',
        'UPI': 'UPI',
        'CREDIT CARD': 'Credit Card',
        'DEBIT CARD': 'Debit Card',
        'NET BANKING': 'Net Banking',
        'NETBANKING': 'Net Banking',
        'WALLET': 'Wallet',
    }
    
    for method, display_name in payment_methods.items():
        if method in text_upper:
            details['payment_method'] = display_name
            break
    
    # ============ STATUS ============
    status_keywords = {
        'SUCCESS': 'Success',
        'SUCCESSFUL': 'Success',
        'COMPLETED': 'Completed',
        'PAID': 'Paid',
        'DONE': 'Success',
        'FAILED': 'Failed',
        'PENDING': 'Pending',
        'DECLINED': 'Declined',
        'REJECTED': 'Rejected',
    }
    
    for keyword, status in status_keywords.items():
        if keyword in text_upper:
            details['status'] = status
            break
    
    # ============ BANK NAME ============
    banks = {
        'AXIS': 'Axis Bank',
        'SBI': 'State Bank of India',
        'STATE BANK': 'State Bank of India',
        'HDFC': 'HDFC Bank',
        'ICICI': 'ICICI Bank',
        'KOTAK': 'Kotak Mahindra Bank',
        'PNB': 'Punjab National Bank',
        'BOB': 'Bank of Baroda',
        'BARODA': 'Bank of Baroda',
        'CANARA': 'Canara Bank',
        'UNION BANK': 'Union Bank',
        'IDBI': 'IDBI Bank',
        'YES BANK': 'Yes Bank',
        'INDUSIND': 'IndusInd Bank',
    }
    
    for bank_key, bank_name in banks.items():
        if bank_key in text_upper:
            details['bank_name'] = bank_name
            break
    
    return details

def is_false_positive(text: str) -> bool:
    """
    Enhanced false positive detection
    """
    if not text or len(text) < 8:
        return True
    
    # Known false positives
    false_positives = {
        'SUCCESSFUL', 'SUCCESS', 'FAILED', 'PENDING', 'COMPLETED',
        'TRANSACTION', 'PAYMENT', 'DETAILS', 'SUMMARY', 'RECEIPT',
        'PHONE', 'EMAIL', 'ADDRESS', 'CUSTOMER', 'MERCHANT',
        'BANK', 'ACCOUNT', 'IFSC', 'AMOUNT', 'DATE', 'TIME',
        'BALANCE', 'AVAILABLE', 'CREDITED', 'DEBITED',
        'DESCRIPTION', 'REFERENCE', 'STATEMENT',
    }
    
    text_upper = text.upper()
    
    # Exact match with false positives
    if text_upper in false_positives:
        return True
    
    # Contains mostly same character (like XXXXXX or 000000)
    if len(set(text)) < 5:
        return True
    
    # Masked account number
    if text_upper.count('X') > len(text) * 0.5:
        return True
    
    # Too long or contains spaces
    if len(text) > 30 or ' ' in text:
        return True
    
    return False

def format_payment_details(details: Dict) -> str:
    """
    Format payment details for beautiful display
    """
    lines = []
    
    if details.get('transaction_id'):
        lines.append(f"💳 Transaction ID: {details['transaction_id']}")
    
    if details.get('amount'):
        lines.append(f"💰 Amount: ₹{details['amount']}")
    
    if details.get('payment_method'):
        lines.append(f"📱 Method: {details['payment_method']}")
    
    if details.get('date'):
        lines.append(f"📅 Date: {details['date']}")
    
    if details.get('time'):
        lines.append(f"⏰ Time: {details['time']}")
    
    if details.get('status'):
        emoji = "✅" if details['status'].lower() in ['success', 'completed', 'paid'] else "⚠️"
        lines.append(f"{emoji} Status: {details['status']}")
    
    if details.get('upi_id'):
        lines.append(f"🆔 UPI ID: {details['upi_id']}")
    
    if details.get('bank_name'):
        lines.append(f"🏦 Bank: {details['bank_name']}")
    
    return '\n'.join(lines) if lines else "❌ No payment details extracted"
