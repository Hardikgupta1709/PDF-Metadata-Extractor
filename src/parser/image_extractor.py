
import re
import requests
from PIL import Image
import io
import pytesseract
from typing import Dict, Optional, List



# OCR utilities
def extract_text_from_image_tesseract(image_file) -> str:

    try:
        image = Image.open(image_file)

        if image.mode != 'RGB':
            image = image.convert('RGB')

        return pytesseract.image_to_string(image)

    except Exception as e:
        print(f"Tesseract extraction error: {str(e)}")
        return ""


def extract_text_from_image_grobid(image_path: str, grobid_server: str) -> str:

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



# Transaction extraction


def is_false_positive(text: str) -> bool:
    """Reject non-ID tokens"""
    if not text:
        return True

    false_words = [
        "PHONE", "EMAIL", "ADDRESS", "CUSTOMER", "MERCHANT", "BANK",
        "ACCOUNT", "IFSC", "DETAILS", "PAYMENT", "DATE", "TIME",
        "STATUS", "METHOD", "COMPLETED", "SUCCESS", "FAILED"
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


def extract_all_transaction_ids(text: str) -> Dict[str, Optional[str]]:

    if not text:
        return {
            "upi_transaction_id": None,
            "google_transaction_id": None,
            "app_transaction_id": None,
            "utr_number": None,
            "reference_number": None
        }

    text_upper = text.upper()
    result = {
        "upi_transaction_id": None,
        "google_transaction_id": None,
        "app_transaction_id": None,
        "utr_number": None,
        "reference_number": None
    }


    upi_patterns = [
        r'UPI\s+TRANSACTION\s+ID[\s:]*(\d{12})',
        r'UPI\s+TXN\s+ID[\s:]*(\d{12})',
        r'UPI\s+ID[\s:]*(\d{12})',
        r'UPI\s+REF(?:ERENCE)?\s+(?:NO|NUMBER)[\s:]*(\d{12})',
        r'UPI\s+REF[\s:]*(\d{12})',
    ]
    
    for pattern in upi_patterns:
        match = re.search(pattern, text_upper)
        if match:
            result["upi_transaction_id"] = match.group(1)
            break
    

    if not result["upi_transaction_id"]:

        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'UPI' in line.upper() and 'TRANSACTION' in line.upper() and 'ID' in line.upper():

                for j in range(i+1, min(i+4, len(lines))):
                    match = re.search(r'\b(\d{12})\b', lines[j])
                    if match:
                        result["upi_transaction_id"] = match.group(1)
                        break
                if result["upi_transaction_id"]:
                    break


    google_patterns = [
        r'GOOGLE\s+TRANSACTION\s+ID[\s:]*([A-Za-z0-9]{10,})',
        r'GOOGLE\s+TXN\s+ID[\s:]*([A-Za-z0-9]{10,})',
        r'G(?:OOG|oog)le\s+(?:transaction|txn)\s+ID[\s:]*([A-Za-z0-9]{10,})',
    ]
    
    for pattern in google_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["google_transaction_id"] = match.group(1)
            break
    

    if not result["google_transaction_id"]:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'GOOGLE' in line.upper() and 'TRANSACTION' in line.upper() and 'ID' in line.upper():
                for j in range(i+1, min(i+4, len(lines))):
                    # Google IDs often have mixed case and special chars
                    match = re.search(r'\b([A-Za-z][A-Za-z0-9]{9,30})\b', lines[j])
                    if match and not is_false_positive(match.group(1)):
                        result["google_transaction_id"] = match.group(1)
                        break
                if result["google_transaction_id"]:
                    break


    
    # PhonePe OLEX format
    match = re.search(r'\b(OLEX[A-Z0-9]{20,})\b', text_upper)
    if match:
        result["app_transaction_id"] = match.group(1)
    
    # Generic T-prefix IDs (PhonePe, Paytm)
    if not result["app_transaction_id"]:
        match = re.search(r'\bT([A-Z0-9]{18,})\b', text_upper)
        if match:
            full_id = 'T' + match.group(1)
            if not is_false_positive(full_id):
                result["app_transaction_id"] = full_id
    
    # Explicit app transaction ID labels
    if not result["app_transaction_id"]:
        app_patterns = [
            r'(?:PHONEPE|PAYTM|BHIM)\s+(?:TRANSACTION|TXN)\s+ID[\s:]*([A-Z0-9]{15,})',
            r'TRANSACTION\s+ID[\s:]*([A-Z0-9]{15,})',
            r'TXN\s+ID[\s:]*([A-Z0-9]{15,})',
        ]
        
        for pattern in app_patterns:
            match = re.search(pattern, text_upper)
            if match:
                tid = match.group(1)
                # Skip if it's the UPI ID we already found
                if tid != result["upi_transaction_id"] and not is_false_positive(tid):
                    result["app_transaction_id"] = tid
                    break


    match = re.search(r'UTR[\s:]*[#]?\s*(\d{12})', text_upper)
    if match:
        result["utr_number"] = match.group(1)


    ref_patterns = [
        r'(?:REF|REFERENCE)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        r'(?:ORDER|PAYMENT)[\s:]*[#]?\s*([A-Z0-9]{12,})',
        r'(?:RECEIPT|RCPT)[\s:]*[#]?\s*([A-Z0-9]{12,})',
    ]
    
    for pattern in ref_patterns:
        match = re.search(pattern, text_upper)
        if match:
            ref_id = match.group(1)
            # Don't duplicate IDs we already have
            if (ref_id not in [result["upi_transaction_id"], 
                              result["google_transaction_id"],
                              result["app_transaction_id"],
                              result["utr_number"]] 
                and not is_false_positive(ref_id)):
                result["reference_number"] = ref_id
                break

    return result


def extract_transaction_id(text: str) -> Optional[str]:
    """
    Extract the PRIMARY transaction ID.
    For UPI payments, prioritize UPI transaction ID.
    """
    all_ids = extract_all_transaction_ids(text)
    
    # Priority order for primary ID
    if all_ids["upi_transaction_id"]:
        return all_ids["upi_transaction_id"]
    
    if all_ids["app_transaction_id"]:
        return all_ids["app_transaction_id"]
    
    if all_ids["google_transaction_id"]:
        return all_ids["google_transaction_id"]
    
    if all_ids["utr_number"]:
        return all_ids["utr_number"]
    
    if all_ids["reference_number"]:
        return all_ids["reference_number"]
    
    return None




def extract_payment_details(text: str) -> Dict[str, Optional[str]]:
    res = {
        "transaction_id": None,  # Primary transaction ID
        "upi_transaction_id": None,
        "google_transaction_id": None,
        "app_transaction_id": None,
        "utr_number": None,
        "reference_number": None,
        "amount": None,
        "date": None,
        "time": None,
        "payment_method": None,
        "status": None,
        "upi_id": None,
        "bank_name": None,
        "merchant_name": None,
        "payer_name": None,
    }

    if not text:
        return res

    text_upper = text.upper()

    # Extract all transaction IDs
    all_ids = extract_all_transaction_ids(text)
    res.update(all_ids)
    
    # Set primary transaction ID (UPI ID takes priority)
    res["transaction_id"] = extract_transaction_id(text)

    # Amount - improved patterns
    amount_patterns = [
        r'₹\s*([0-9,]+\.?[0-9]*)',  # ₹220
        r'RS\.?\s*([0-9,]+\.?[0-9]*)',  # Rs. 220
        r'INR\s*([0-9,]+\.?[0-9]*)',  # INR 220
        r'(?:AMOUNT|AMT|TOTAL|PAID)[\s:]*[₹$]?\s*([0-9,]+\.?[0-9]*)',
    ]

    for p in amount_patterns:
        m = re.search(p, text_upper)
        if m:
            amt = m.group(1).replace(",", "")
            try:

                float_amt = float(amt)
                if 0 < float_amt < 1000000:  
                    res["amount"] = amt
                    break
            except:
                continue


    date_patterns = [
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # 7 Dec 2025
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
    ]
    for p in date_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            res["date"] = m.group(1)
            break


    time_patterns = [
        r'\b(\d{1,2}:\d{2}\s*(?:am|pm))\b',  # 1:46 pm
        r'\b(\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?)\b',
    ]
    for p in time_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            res["time"] = m.group(1)
            break


    m = re.search(r'([a-zA-Z0-9._-]+@[a-zA-Z]+)', text)
    if m:
        res["upi_id"] = m.group(1)


    methods = [
        "GOOGLE PAY", "GPAY", "PHONEPE", "PAYTM", "BHIM",
        "UPI", "CREDIT CARD", "DEBIT CARD", "NET BANKING", 
        "WALLET", "AUTOPAY"
    ]
    for m in methods:
        if m in text_upper:
            res["payment_method"] = m
            break


    if "COMPLETED" in text_upper or "COMPLETE" in text_upper:
        res["status"] = "COMPLETED"
    elif "SUCCESS" in text_upper or "SUCCESSFUL" in text_upper:
        res["status"] = "SUCCESS"
    elif "PAID" in text_upper:
        res["status"] = "PAID"
    elif "FAILED" in text_upper or "FAIL" in text_upper:
        res["status"] = "FAILED"
    elif "PENDING" in text_upper:
        res["status"] = "PENDING"
    elif "DECLINED" in text_upper:
        res["status"] = "DECLINED"

    # Bank name
    banks = [
        "HDFC BANK", "HDFC", "SBI", "STATE BANK", 
        "ICICI", "AXIS", "KOTAK", "PNB", "PUNJAB NATIONAL",
        "BOB", "BANK OF BARODA", "CANARA", "UNION", 
        "IDBI", "YES BANK", "FEDERAL", "IDFC"
    ]
    for b in banks:
        if b in text_upper:
            res["bank_name"] = b
            break


    merchant_patterns = [
        r'(?:TO|Pay\s+to)[\s:]+([A-Z][A-Z\s]+?)(?:\n|$|₹)',
        r'PAY\s+TO\s+(.+?)(?:MERCHANT|$)',
    ]
    for p in merchant_patterns:
        m = re.search(p, text_upper)
        if m:
            merchant = m.group(1).strip()
            if len(merchant) > 2 and len(merchant) < 50:
                res["merchant_name"] = merchant
                break


    from_patterns = [
        r'FROM[\s:]+([A-Z][A-Z\s]+?)(?:\(|$|\n)',
    ]
    for p in from_patterns:
        m = re.search(p, text_upper)
        if m:
            payer = m.group(1).strip()
            if len(payer) > 2 and len(payer) < 50:
                res["payer_name"] = payer
                break

    return res



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
            "upi_transaction_id": None,
            "google_transaction_id": None,
            "app_transaction_id": None,
            "utr_number": None,
            "reference_number": None,
            "amount": None,
            "date": None,
            "time": None,
            "payment_method": None,
            "status": None,
            "upi_id": None,
            "bank_name": None,
            "merchant_name": None,
            "payer_name": None,
            "raw_text": "",
        }

    details = extract_payment_details(text)
    details["raw_text"] = text[:500]
    return details


def format_payment_details(details: Dict) -> str:
    lines = []

    if details.get("transaction_id"):
        lines.append(f"Primary Transaction ID: {details['transaction_id']}")

    if details.get("upi_transaction_id"):
        lines.append(f"UPI Transaction ID: {details['upi_transaction_id']}")

    if details.get("google_transaction_id"):
        lines.append(f"Google Transaction ID: {details['google_transaction_id']}")

    if details.get("app_transaction_id"):
        lines.append(f"App Transaction ID: {details['app_transaction_id']}")

    if details.get("utr_number"):
        lines.append(f"UTR Number: {details['utr_number']}")

    if details.get("reference_number"):
        lines.append(f"Reference Number: {details['reference_number']}")

    if details.get("amount"):
        lines.append(f"Amount: ₹{details['amount']}")

    if details.get("status"):
        lines.append(f"Status: {details['status']}")

    if details.get("merchant_name"):
        lines.append(f"Merchant: {details['merchant_name']}")

    if details.get("payer_name"):
        lines.append(f"From: {details['payer_name']}")

    if details.get("date"):
        lines.append(f"Date: {details['date']}")

    if details.get("time"):
        lines.append(f"Time: {details['time']}")

    if details.get("payment_method"):
        lines.append(f"Method: {details['payment_method']}")

    if details.get("upi_id"):
        lines.append(f"UPI ID: {details['upi_id']}")

    if details.get("bank_name"):
        lines.append(f"Bank: {details['bank_name']}")

    return "\n".join(lines) if lines else "No payment details extracted"




def streamlit_example():
    import streamlit as st

    st.title(" Receipt Scanner with Auto-Fill")
    st.caption("Enhanced support for Google Pay, PhonePe, Paytm & more")

    if "form_data" not in st.session_state:
        st.session_state.form_data = {
            "transaction_id": "",
            "upi_transaction_id": "",
            "google_transaction_id": "",
            "app_transaction_id": "",
            "amount": "",
            "payment_date": "",
            "payment_time": "",
            "payment_method": "",
            "payment_status": "",
            "upi_id": "",
            "bank_name": "",
            "merchant_name": "",
            "payer_name": "",
        }

    uploaded_file = st.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Receipt", use_column_width=True)

        col1, col2 = st.columns(2)
        
        with col1:
            use_tesseract = st.checkbox("Use Tesseract OCR", value=True)
        with col2:
            use_easyocr = st.checkbox("Use EasyOCR", value=False)

        if st.button("🔍 Extract Details", type="primary", use_container_width=True):
            with st.spinner("Extracting payment details..."):
                details = extract_payment_info_from_image(
                    uploaded_file, 
                    use_tesseract=use_tesseract,
                    use_easyocr=use_easyocr
                )
                st.success(" Extraction complete!")
                

                st.info(format_payment_details(details))
                

                with st.expander("🔍 View Raw OCR Text"):
                    st.text(details.get("raw_text", ""))
                

                st.session_state.form_data["transaction_id"] = details.get("transaction_id") or ""
                st.session_state.form_data["upi_transaction_id"] = details.get("upi_transaction_id") or ""
                st.session_state.form_data["google_transaction_id"] = details.get("google_transaction_id") or ""
                st.session_state.form_data["app_transaction_id"] = details.get("app_transaction_id") or ""
                st.session_state.form_data["amount"] = details.get("amount") or ""
                st.session_state.form_data["payment_date"] = details.get("date") or ""
                st.session_state.form_data["payment_time"] = details.get("time") or ""
                st.session_state.form_data["payment_method"] = details.get("payment_method") or ""
                st.session_state.form_data["payment_status"] = details.get("status") or ""
                st.session_state.form_data["upi_id"] = details.get("upi_id") or ""
                st.session_state.form_data["bank_name"] = details.get("bank_name") or ""
                st.session_state.form_data["merchant_name"] = details.get("merchant_name") or ""
                st.session_state.form_data["payer_name"] = details.get("payer_name") or ""
                
                st.rerun()

    st.divider()
    st.subheader(" Payment Form")

    with st.form("payment_form"):
        f = st.session_state.form_data


        st.markdown("**Transaction IDs**")
        col1, col2 = st.columns(2)
        
        with col1:
            upi_transaction_id = st.text_input("UPI Transaction ID (Primary)", value=f["upi_transaction_id"])
            google_transaction_id = st.text_input("Google Transaction ID", value=f["google_transaction_id"])
        
        with col2:
            app_transaction_id = st.text_input("App Transaction ID", value=f["app_transaction_id"])
            transaction_id = st.text_input("Other Transaction ID", value=f["transaction_id"])

        st.divider()
        
        # Payment details section
        st.markdown("**Payment Details**")
        col3, col4 = st.columns(2)
        
        with col3:
            amount = st.text_input("Amount (₹)", value=f["amount"])
            payment_date = st.text_input("Payment Date", value=f["payment_date"])
            payment_time = st.text_input("Payment Time", value=f["payment_time"])
            payment_status = st.text_input("Status", value=f["payment_status"])
        
        with col4:
            payment_method = st.text_input("Payment Method", value=f["payment_method"])
            merchant_name = st.text_input("Merchant Name", value=f["merchant_name"])
            payer_name = st.text_input("Payer Name", value=f["payer_name"])
            bank_name = st.text_input("Bank Name", value=f["bank_name"])
        
        upi_id = st.text_input("UPI ID", value=f["upi_id"])

        submitted = st.form_submit_button(" Submit Payment Details", type="primary", use_container_width=True)

        if submitted:
            st.success(" Payment details submitted successfully!")
            st.json({
                "upi_transaction_id": upi_transaction_id,
                "google_transaction_id": google_transaction_id,
                "app_transaction_id": app_transaction_id,
                "transaction_id": transaction_id,
                "amount": amount,
                "payment_date": payment_date,
                "payment_time": payment_time,
                "payment_method": payment_method,
                "payment_status": payment_status,
                "merchant_name": merchant_name,
                "payer_name": payer_name,
                "upi_id": upi_id,
                "bank_name": bank_name,
            })


if __name__ == "__main__":
    print(" Module loaded successfully")
