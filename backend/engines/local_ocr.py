import re
import os
import shutil
import cv2
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from backend.utils.dip_processor import preprocess_card_image

load_dotenv(override=True)

# 1. Flexible Pytesseract Path setup
pytesseract_available = False
try:
    import pytesseract
    env_tess_path = os.getenv("TESSERACT_PATH", "").strip().strip('"').strip("'")
    possible_paths = [
        env_tess_path,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\CARD_VISIT\Tesseract-OCR\tesseract.exe",
        r"D:\Tesseract-OCR\tesseract.exe",
        r"D:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Tesseract-OCR\tesseract.exe"
    ]

    for p in possible_paths:
        if p and os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            pytesseract_available = True
            break
except ImportError:
    pytesseract = None

# 2. EasyOCR setup (Pure Python Fallback - No .exe needed!)
_easyocr_reader = None
def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)
        except Exception as e:
            print(f"[EasyOCR Init Error]: {e}")
            _easyocr_reader = None
    return _easyocr_reader

JOB_KEYWORDS = [
    "chuyên viên", "lập trình viên", "giám đốc", "trưởng phòng", "quản lý", "nhân viên",
    "consultant", "developer", "engineer", "director", "executive", "manager", "officer",
    "president", "vice president", "deputy", "leader", "designer", "architect", "analyst"
]

COMPANY_KEYWORDS = [
    "công ty", "tnhh", "cổ phần", "co., ltd", "ltd", "corp", "corporation", "inc", "group", "jsc", "branch"
]

def parse_extracted_text(text: str) -> dict:
    """Regex & Heuristic Spatial Parser for OCR text lines."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    result = {
        "company_name": "",
        "full_name": "",
        "job_title": "",
        "phone": "",
        "phone_2": "",
        "email": "",
        "website": "",
        "address": "",
        "tax_code": ""
    }

    if not lines:
        return result

    # 1. Robust Email Parsing (Handles OCR missing dots like 'khoa dt@citares edu.vn')
    for line in lines:
        if "@" in line:
            line_clean = line.replace(" ", "")
            match = re.search(r'[a-zA-Z0-9._%+\-\t]+@[a-zA-Z0-9.\-\t]+\.[a-zA-Z]{2,}', line_clean)
            if match:
                result["email"] = match.group(0)
                break
            else:
                parts = line.split("@")
                if len(parts) == 2:
                    u_part = re.sub(r'[^\w.]', '', parts[0])
                    d_part = parts[1].strip().replace(" ", ".")
                    result["email"] = f"{u_part}@{d_part}"
                    break

    # 2. Extract Phone 1 and Phone 2 (Support both landline (028) and mobile 098)
    phone_pattern = r'(?:\(?0\d{1,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}'
    raw_phones = re.findall(phone_pattern, text)
    valid_phones = []
    for p in raw_phones:
        digits = re.sub(r'\D', '', p)
        if len(digits) >= 8:
            clean_p = p.replace(".", "").strip()
            if clean_p not in valid_phones:
                valid_phones.append(clean_p)

    if len(valid_phones) >= 1:
        result["phone"] = valid_phones[0]
    if len(valid_phones) >= 2:
        result["phone_2"] = valid_phones[1]

    # 3. Extract Website
    web_pattern = r'(?:https?://|www\.)\s*[a-zA-Z0-9.\-\t ]+\.[a-zA-Z]{2,}'
    websites = re.findall(web_pattern, text, re.IGNORECASE)
    if not websites:
        web_pattern2 = r'[a-zA-Z0-9.\-\t ]+\.(?:edu\.vn|com\.vn|vn|com|net|org)'
        websites = re.findall(web_pattern2, text, re.IGNORECASE)

    if websites:
        clean_web = websites[0].replace(" ", "").replace("\n", "").replace("\r", "").strip()
        if result["email"] and clean_web in result["email"]:
            parts = result["email"].split("@")
            if len(parts) > 1:
                clean_web = "www." + parts[1]
        result["website"] = clean_web

    # 4. Extract Tax Code
    tax_pattern = r'(?:tax code|mã số thuế|mst)?\s*[:.-]?\s*(\d{10}(?:-\d{3})?)'
    tax_match = re.search(tax_pattern, text, re.IGNORECASE)
    if tax_match and tax_match.group(1):
        result["tax_code"] = tax_match.group(1)

    # 5. Classify remaining text lines for Name, Job Title, Company Name, Address
    unused_lines = []
    for line in lines:
        l_lower = line.lower()

        if any(ck in l_lower for ck in COMPANY_KEYWORDS):
            if not result["company_name"]:
                result["company_name"] = line
                continue

        if any(jk in l_lower for jk in JOB_KEYWORDS):
            if not result["job_title"]:
                result["job_title"] = line
                continue

        # Multi-line Address Stitching
        if any(ak in l_lower for ak in ["địa chỉ", "address", "phường", "quận", "tp", "street", "ward", "city", "hcm", "hà nội", "park", "lot", "vietnam", "việt nam", "tăng nhơn phú", "ho chi minh"]):
            if result["address"]:
                if line not in result["address"]:
                    result["address"] += ", " + line
            else:
                result["address"] = line
            continue

        if result["email"] and result["email"] in line:
            continue
        if re.search(r'\d{7,}', line):
            continue

        unused_lines.append(line)

    for line in unused_lines:
        if line.isupper() and len(line.split()) >= 2 and len(line) < 35:
            result["full_name"] = line
            break

    if not result["full_name"] and unused_lines:
        for line in unused_lines:
            if len(line.split()) >= 2 and len(line) < 35 and not any(char.isdigit() for char in line):
                result["full_name"] = line
                break

    return result

def extract_with_local_ocr(image_bytes: bytes) -> dict:
    """
    Engine V2: Local Offline OpenCV DIP + Tesseract / EasyOCR (Pure Python).
    """
    processed_bytes, raw_img = preprocess_card_image(image_bytes, auto_warp=True)
    nparr = np.frombuffer(processed_bytes, np.uint8)
    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

    raw_text = ""
    engine_used = "Local DIP + EasyOCR (Pure Python)"

    # Attempt 1: Tesseract OCR if executable exists
    if pytesseract and pytesseract_available:
        try:
            raw_text = pytesseract.image_to_string(pil_img, lang='vie+eng')
            engine_used = "Local DIP + Tesseract OCR (vie+eng)"
        except Exception:
            try:
                raw_text = pytesseract.image_to_string(pil_img, lang='eng')
                engine_used = "Local DIP + Tesseract OCR (eng)"
            except Exception:
                raw_text = ""

    # Attempt 2: Pure Python EasyOCR Fallback (No Windows .exe needed!)
    if not raw_text.strip():
        reader = get_easyocr_reader()
        if reader is not None:
            try:
                ocr_results = reader.readtext(cv_img)
                raw_text = "\n".join([item[1] for item in ocr_results])
                engine_used = "Local DIP + EasyOCR (Pure Python)"
            except Exception as e:
                print(f"[EasyOCR Run Error]: {e}")
                raw_text = ""

    if not raw_text.strip():
        return {
            "error": "Không thể trích xuất chữ offline. Vui lòng kiểm tra lại ảnh card.",
            "company_name": "", "full_name": "", "job_title": "",
            "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": "",
            "raw_text": ""
        }

    parsed = parse_extracted_text(raw_text)
    parsed["engine"] = engine_used
    parsed["raw_text"] = raw_text.strip()
    return parsed
