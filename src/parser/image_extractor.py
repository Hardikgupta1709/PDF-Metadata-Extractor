"""
Extract transaction IDs and payment details from receipt images with auto-fill
"""
import re
import requests
from PIL import Image
import io
import pytesseract
from typing import Dict, Optional


# --------------------------------------------------------
# OCR utilities
# --------------------------------------------------------

def extract_text_from_image_tesseract(image_file) -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        image = Image.open(image_file)

        if image.mode != 'RGB':
            image = image.convert('RGB')

        return pytesseract.image_to_string(image)

    except Exception as e:
        print(f"Tesseract extraction error: {str(e)}")
        return ""


def extract_text_from_image_grobid(image_path: str, grobid_server: str) -> str:
    """Extract text from image/PDF using GROBID (mostly PDF)"""
    try:
        url = f"{grobid_server}/api/processFulltextDocument"

        with open(image_path, 'rb') as f:
            files = {'input': f}
            response = requests.post(url, files=files, timeout=60)

        if response.status_code != 200:
            return ""

        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)

        text_parts = []
        for elem in root.iter():
            if elem.text:
                text_parts.append(elem.text.strip())

        return " ".join(text_parts)

    except Exception as e:
        print(f"GROBID extraction error: {str(e)}")
        return ""


def extract_text_from_image_easyocr(image_file) -> str:
    """Extract text from image using EasyOCR"""
    try:
        import easyocr

        reader = easyocr.Reader(['en'])
        image = Image.open(image_file)

        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")

        results = reader.readtext(img_byte_arr.getvalue())

        return " ".join([r[1] for r in results])

    except Exception as e:
        print(f"EasyOCR extraction error: {str(e)}")
        return ""


# --------------------------------------------------------
# Transaction extraction
# --------------------------------------------------------

def is_false_positive(text: str) -> bool:
    """Reject non-ID tokens"""
    if not text:
        return True

    false_words = [
        "PHONE", "EMAIL", "ADDRESS", "CUSTOMER", "MERCHANT", "BANK",
        "ACCOUNT", "IFSC", "DETAILS", "PAYMENT", "AMOUNT", "DATE"
    ]

    t = text.upper()

    if len(text) < 8 or len(text) > 50:
        return True

    if len(set(text)) < 3:   # repeated characters
        return True

    for w in false_words:
        if w in t:
            return True

    return False


def extract_transaction_id(text: str) -> Optional[str]:
    """Extract Transaction ID, prioritizing common app formats"""
    if not text:
        return None

    text_upper = text.upper()

    # Priority 1: Explicit labels
    patterns = [
        r'TRANSACTION\s*ID[\s:]*([A-Z0-9]{15,})',
        r'TXN\s*ID[\s:]*([A-Z0-9]{15,})',
        r'TRANS(?:ACTION)?\s*ID[\s:]*([A-Z0-9]{15,})',
    ]

    for p in patterns:
        for m in re.finditer(p, text_upper):
            v = m.group(1)
            if not is_false_positive(v):
                return v

    # Priority 2
    patterns_2 = [
        r'(?:REF|REFERENCE)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        r'(?:ORDER|PAYMENT)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        r'(?:RECEIPT|RCPT)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        r'TXN[\s:]*[#]?\s*([A-Z0-9]{12,})',
    ]

    for p in patterns_2:
        for m in re.finditer(p, text_upper):
            v = m.group(1)
            if not is_false_positive(v):
                return v

    # Priority 3: PhonePe style IDs
    match = re.search(r'\bT[A-Z0-9]{18,}\b', text_upper)
    if match:
        v = match.group(0)
        if not is_false_positive(v):
            return v

    # Priority 4: Generic fallback
    for m in re.finditer(r'\b([A-Z0-9]{15,})\b', text_upper):
        v = m.group(1)
        # Skip pure 12-digit UTR
        if re.match(r'^\d{12}$', v):
            continue
        if not is_false_positive(v):
            return v

    # Priority 5: UTR fallback
    match = re.search(r'UTR[\s:]*[#]?\s*([0-9]{12})', text_upper)
    if match:
        return match.group(1)

    return None


# --------------------------------------------------------
# Payment detail extraction
# --------------------------------------------------------

def extract_payment_details(text: str) -> Dict[str, Optional[str]]:
    res = {
        "transaction_id": None,
        "utr_number": None,
        "amount": None,
        "date": None,
        "time": None,
        "payment_method": None,
        "status": None,
        "upi_id": None,
        "bank_name": None,
    }

    if not text:
        return res

    text_upper = text.upper()

    res["transaction_id"] = extract_transaction_id(text)

    # UTR
    utr = re.search(r'UTR[\s:]*([0-9]{12})', text_upper)
    if utr:
        res["utr_number"] = utr.group(1)

    # Amount
    amount_patterns = [
        r'(?:AMOUNT|AMT|TOTAL|PAID)[\s:]*[₹$]?\s*([0-9,]+\.?[0-9]*)',
        r'[₹$]\s*([0-9,]+\.?[0-9]*)',
        r'(?:RS|INR)[\s.]*([0-9,]+\.?[0-9]*)',
    ]

    for p in amount_patterns:
        m = re.search(p, text_upper)
        if m:
            amt = m.group(1).replace(",", "")
            res["amount"] = amt
            break

    # Date
    date_patterns = [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
        r'\b(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{2,4})\b',
    ]
    for p in date_patterns:
        m = re.search(p, text_upper)
        if m:
            res["date"] = m.group(1)
            break

    # Time
    m = re.search(r'\b(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\b', text_upper)
    if m:
        res["time"] = m.group(1)

    # UPI ID
    m = re.search(r'([a-zA-Z0-9._-]+@[a-zA-Z]+)', text)
    if m:
        res["upi_id"] = m.group(1)

    # Payment method
    methods = [
        "UPI", "CREDIT CARD", "DEBIT CARD", "NET BANKING", "WALLET",
        "PAYTM", "PHONEPE", "GPAY", "GOOGLE PAY"
    ]
    for m in methods:
        if m in text_upper:
            res["payment_method"] = m
            break

    # Status
    statuses = [
        "SUCCESS", "SUCCESSFUL", "COMPLETED", "PAID",
        "FAILED", "PENDING", "DECLINED"
    ]
    for s in statuses:
        if s in text_upper:
            res["status"] = s
            break

    # Bank name
    banks = [
        "SBI", "HDFC", "ICICI", "AXIS", "KOTAK", "PNB",
        "BOB", "CANARA", "UNION", "IDBI", "YES BANK"
    ]
    for b in banks:
        if b in text_upper:
            res["bank_name"] = b
            break

    return res


# --------------------------------------------------------
# Main extraction wrapper
# --------------------------------------------------------

def extract_payment_info_from_image(
    image_file,
    grobid_server: str = None,
    use_tesseract: bool = True,
    use_easyocr: bool = False
) -> Dict[str, Optional[str]]:
    text = ""

    if use_easyocr:
        try:
            text = extract_text_from_image_easyocr(image_file)
        except:
            pass

    if not text and use_tesseract:
        if hasattr(image_file, "seek"):
            image_file.seek(0)
        text = extract_text_from_image_tesseract(image_file)

    if not text:
        return {
            "transaction_id": None,
            "amount": None,
            "date": None,
            "time": None,
            "payment_method": None,
            "status": None,
            "upi_id": None,
            "bank_name": None,
            "raw_text": "",
        }

    details = extract_payment_details(text)
    details["raw_text"] = text[:500]
    return details


# --------------------------------------------------------
# Formatting
# --------------------------------------------------------

def format_payment_details(details: Dict) -> str:
    lines = []

    if details.get("transaction_id"):
        lines.append(f"🔖 Transaction ID: {details['transaction_id']}")

    if details.get("utr_number"):
        lines.append(f"🏦 UTR Number: {details['utr_number']}")

    if details.get("amount"):
        lines.append(f"💰 Amount: ₹{details['amount']}")

    if details.get("status"):
        lines.append(f"✅ Status: {details['status']}")

    if details.get("date"):
        lines.append(f"📅 Date: {details['date']}")

    if details.get("time"):
        lines.append(f"🕐 Time: {details['time']}")

    if details.get("payment_method"):
        lines.append(f"💳 Method: {details['payment_method']}")

    if details.get("upi_id"):
        lines.append(f"📱 UPI ID: {details['upi_id']}")

    if details.get("bank_name"):
        lines.append(f"🏦 Bank: {details['bank_name']}")

    return "\n".join(lines) if lines else "No payment details extracted"


# --------------------------------------------------------
# Streamlit example
# --------------------------------------------------------

def streamlit_example():
    import streamlit as st

    st.title("Receipt Scanner with Auto-Fill")

    if "form_data" not in st.session_state:
        st.session_state.form_data = {
            "transaction_id": "",
            "amount": "",
            "payment_date": "",
            "payment_time": "",
            "payment_method": "",
            "payment_status": "",
            "upi_id": "",
            "bank_name": "",
        }

    uploaded_file = st.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        st.image(uploaded_file)

        if st.button("Extract Details"):
            with st.spinner("Extracting..."):
                details = extract_payment_info_from_image(uploaded_file)
                st.success("Done!")
                st.info(format_payment_details(details))

    st.write("Form below:")

    with st.form("payment_form"):
        f = st.session_state.form_data

        transaction_id = st.text_input("Transaction ID", value=f["transaction_id"])
        amount = st.text_input("Amount", value=f["amount"])
        payment_date = st.text_input("Payment Date", value=f["payment_date"])
        payment_time = st.text_input("Payment Time", value=f["payment_time"])
        payment_method = st.text_input("Payment Method", value=f["payment_method"])
        payment_status = st.text_input("Status", value=f["payment_status"])
        upi_id = st.text_input("UPI ID", value=f["upi_id"])
        bank_name = st.text_input("Bank Name", value=f["bank_name"])

        submitted = st.form_submit_button("Submit")

        if submitted:
            st.json({
                "transaction_id": transaction_id,
                "amount": amount,
                "payment_date": payment_date,
                "payment_time": payment_time,
                "payment_method": payment_method,
                "payment_status": payment_status,
                "upi_id": upi_id,
                "bank_name": bank_name,
            })


if __name__ == "__main__":
    print("Module loaded OK — Streamlit mode available")


