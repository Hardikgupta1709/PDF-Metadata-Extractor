"""
Extract payment details from receipt images using Tesseract OCR (lightweight)
"""
import re
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from typing import Dict, Optional
import numpy as np
import cv2

def preprocess_image_advanced(image):
    """
    Advanced image preprocessing for better OCR accuracy
    """
    # Convert PIL to OpenCV format
    img_array = np.array(image)
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply different preprocessing techniques
    processed_images = []
    
    # 1. Original grayscale
    processed_images.append(gray)
    
    # 2. Adaptive thresholding (best for varying lighting)
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    processed_images.append(adaptive)
    
    # 3. Otsu's thresholding (good for bimodal images)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(otsu)
    
    # 4. Increase contrast
    enhanced = cv2.equalizeHist(gray)
    processed_images.append(enhanced)
    
    # 5. Denoise + threshold
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    _, denoised_thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_images.append(denoised_thresh)
    
    return processed_images

def extract_text_tesseract_enhanced(image_file) -> str:
    """
    Extract text using Tesseract with multiple preprocessing techniques
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Convert to RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Try multiple preprocessing methods
        all_texts = []
        
        # Method 1: Simple PIL enhancement
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(2.5)
        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(2.0)
        
        text1 = pytesseract.image_to_string(enhanced, config='--oem 3 --psm 6')
        all_texts.append(text1)
        
        # Method 2: Advanced OpenCV preprocessing
        try:
            processed_images = preprocess_image_advanced(image)
            
            for idx, processed in enumerate(processed_images):
                # Convert back to PIL for pytesseract
                pil_img = Image.fromarray(processed)
                text = pytesseract.image_to_string(pil_img, config='--oem 3 --psm 6')
                all_texts.append(text)
        except Exception as e:
            print(f"⚠️ OpenCV preprocessing failed: {e}")
        
        # Method 3: Try different PSM modes on enhanced image
        for psm in [3, 4, 11]:
            try:
                text = pytesseract.image_to_string(
                    enhanced, 
                    config=f'--oem 3 --psm {psm}'
                )
                all_texts.append(text)
            except:
                continue
        
        # Combine all extracted texts
        combined_text = '\n\n'.join(all_texts)
        
        print(f"📝 Extracted {len(combined_text)} characters from {len(all_texts)} methods")
        
        return combined_text
        
    except Exception as e:
        print(f"❌ Tesseract extraction error: {str(e)}")
        return ""

def extract_payment_info_from_image(image_file, grobid_server: str = None, 
                                   use_tesseract: bool = True,
                                   use_easyocr: bool = False) -> Dict[str, Optional[str]]:
    """
    Extract payment information using Tesseract only (lightweight)
    """
    print("🔍 Starting payment extraction with Tesseract...")
    
    # Extract text using enhanced Tesseract
    extracted_text = extract_text_tesseract_enhanced(image_file)
    
    if not extracted_text or len(extracted_text) < 20:
        print("❌ Insufficient text extracted from image")
        return {
            'transaction_id': '',
            'amount': '',
            'date': '',
            'time': '',
            'payment_method': '',
            'status': '',
            'upi_id': '',
            'bank_name': '',
            'raw_text': extracted_text
        }
    
    # Extract payment details
    details = extract_payment_details_smart(extracted_text)
    details['raw_text'] = extracted_text[:1000]
    
    # Debug output
    print(f"\n{'='*50}")
    print(f"EXTRACTION RESULTS:")
    print(f"{'='*50}")
    print(f"💳 Transaction ID: {details['transaction_id'] or 'NOT FOUND'}")
    print(f"💰 Amount: {details['amount'] or 'NOT FOUND'}")
    print(f"📅 Date: {details['date'] or 'NOT FOUND'}")
    print(f"📱 Method: {details['payment_method'] or 'NOT FOUND'}")
    print(f"{'='*50}\n")
    
    return details

def extract_payment_details_smart(text: str) -> Dict[str, Optional[str]]:
    """
    Smart extraction with aggressive pattern matching
    """
    details = {
        'transaction_id': '',
        'amount': '',
        'date': '',
        'time': '',
        'payment_method': '',
        'status': '',
        'upi_id': '',
        'bank_name': ''
    }
    
    if not text:
        return details
    
    text_upper = text.upper()
    lines = text_upper.split('\n')
    
    # ============ TRANSACTION ID (MOST AGGRESSIVE) ============
    print("\n🔍 Searching for Transaction ID...")
    
    # Pattern 1: Explicit labels (highest priority)
    explicit_patterns = [
        (r'(?:TRANSACTION|TXN|TRANS)\s*(?:ID|NO|NUMBER|REF)[:\s]*([A-Z0-9]{8,30})', 'Explicit TXN label'),
        (r'(?:UTR|UPI\s*REF)[:\s]*([A-Z0-9]{10,25})', 'UTR/UPI Ref'),
        (r'(?:ORDER|PAYMENT|RECEIPT)\s*(?:ID|NO)[:\s]*([A-Z0-9]{10,30})', 'Order/Payment ID'),
        (r'(?:REF(?:ERENCE)?)\s*(?:NO|NUMBER)[:\s]*([A-Z0-9]{10,30})', 'Reference Number'),
    ]
    
    for pattern, description in explicit_patterns:
        match = re.search(pattern, text_upper)
        if match:
            candidate = match.group(1).strip()
            if is_valid_transaction_id(candidate):
                details['transaction_id'] = candidate
                print(f"✅ Found via {description}: {candidate}")
                break
    
    # Pattern 2: PhonePe style (T + 20 digits)
    if not details['transaction_id']:
        match = re.search(r'\b(T\d{20,25})\b', text_upper)
        if match:
            details['transaction_id'] = match.group(1)
            print(f"✅ Found PhonePe style: {details['transaction_id']}")
    
    # Pattern 3: Long numeric strings (12-20 digits)
    if not details['transaction_id']:
        for line in lines:
            match = re.search(r'\b(\d{12,20})\b', line)
            if match:
                candidate = match.group(1)
                if is_valid_transaction_id(candidate):
                    details['transaction_id'] = candidate
                    print(f"✅ Found numeric ID: {candidate}")
                    break
    
    # Pattern 4: Alphanumeric (16-25 chars)
    if not details['transaction_id']:
        for line in lines:
            match = re.search(r'\b([A-Z0-9]{16,25})\b', line)
            if match:
                candidate = match.group(1)
                if is_valid_transaction_id(candidate):
                    details['transaction_id'] = candidate
                    print(f"✅ Found alphanumeric ID: {candidate}")
                    break
    
    # Pattern 5: Any alphanumeric string (10-30 chars) - last resort
    if not details['transaction_id']:
        matches = re.findall(r'\b([A-Z0-9]{10,30})\b', text_upper)
        for candidate in matches:
            if is_valid_transaction_id(candidate):
                details['transaction_id'] = candidate
                print(f"✅ Found generic ID: {candidate}")
                break
    
    # ============ AMOUNT ============
    amount_patterns = [
        (r'(?:PAID|AMOUNT|AMT|TOTAL)[:\s]*[₹RS\.\s]*([0-9,]+\.?\d{0,2})', 'Labeled amount'),
        (r'[₹₨]\s*([0-9,]+\.?\d{0,2})', 'Rupee symbol'),
        (r'RS\.?\s*([0-9,]+\.?\d{0,2})', 'Rs prefix'),
        (r'INR\s*([0-9,]+\.?\d{0,2})', 'INR prefix'),
        (r'\b([0-9,]{1,6}\.\d{2})\b', 'Decimal format'),
    ]
    
    for pattern, description in amount_patterns:
        match = re.search(pattern, text_upper)
        if match:
            amount_str = match.group(1).replace(',', '').strip()
            try:
                amount_val = float(amount_str)
                if 1 <= amount_val <= 10000000:
                    details['amount'] = amount_str
                    print(f"✅ Found amount via {description}: ₹{amount_str}")
                    break
            except:
                continue
    
    # ============ DATE ============
    date_patterns = [
        r'\b(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{2,4})\b',
        r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b',
        r'\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_upper)
        if match:
            details['date'] = match.group(1)
            break
    
    # ============ TIME ============
    time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)', text_upper)
    if time_match:
        details['time'] = time_match.group(1)
    
    # ============ UPI ID ============
    upi_match = re.search(r'\b([a-z0-9._-]{3,}@[a-z]{3,})\b', text, re.IGNORECASE)
    if upi_match:
        upi = upi_match.group(1).lower()
        if 'gmail' not in upi and 'yahoo' not in upi:
            details['upi_id'] = upi
    
    # ============ PAYMENT METHOD ============
    methods = {
        'PHONEPE': 'PhonePe', 'PHONE PE': 'PhonePe',
        'PAYTM': 'Paytm', 'GPAY': 'Google Pay',
        'GOOGLE PAY': 'Google Pay', 'BHIM': 'BHIM UPI',
        'UPI': 'UPI', 'CARD': 'Card'
    }
    
    for key, value in methods.items():
        if key in text_upper:
            details['payment_method'] = value
            break
    
    return details

def is_valid_transaction_id(text: str) -> bool:
    """
    Validate if a string is likely a transaction ID
    """
    if not text or len(text) < 8:
        return False
    
    # Blacklist common false positives
    blacklist = {
        'SUCCESSFUL', 'SUCCESS', 'COMPLETED', 'PENDING', 'FAILED',
        'TRANSACTION', 'PAYMENT', 'AMOUNT', 'BALANCE', 'ACCOUNT',
        'CUSTOMER', 'MERCHANT', 'RECEIVER', 'SENDER', 'DETAILS',
        'SUMMARY', 'RECEIPT', 'STATEMENT', 'CONFIRMED'
    }
    
    if text in blacklist:
        return False
    
    # Must have variety (not all same character)
    if len(set(text)) < 5:
        return False
    
    # Check for masked numbers (XXX)
    if text.count('X') > len(text) * 0.4:
        return False
    
    # Must be alphanumeric only
    if not text.isalnum():
        return False
    
    # Good signs for transaction IDs:
    # 1. Mix of letters and numbers
    has_letters = any(c.isalpha() for c in text)
    has_numbers = any(c.isdigit() for c in text)
    
    # 2. Pure numeric with good length (12+)
    if text.isdigit() and len(text) >= 12:
        return True
    
    # 3. Alphanumeric mix
    if has_letters and has_numbers and len(text) >= 10:
        return True
    
    return False

def format_payment_details(details: Dict) -> str:
    """
    Format payment details beautifully
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
    
    if details.get('upi_id'):
        lines.append(f"🆔 UPI: {details['upi_id']}")
    
    return '\n'.join(lines) if lines else "⚠️ Could not extract payment details"
