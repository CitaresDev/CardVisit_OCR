import os
import io
import csv
try:
    import pandas as pd
except Exception:
    pd = None
try:
    import vobject
except Exception:
    vobject = None

def generate_vcard(card_data: dict) -> str:
    """Creates a standard vCard (.vcf) string representation."""
    j = vobject.vCard()
    
    # Full Name
    full_name = card_data.get("full_name", "").strip()
    if full_name:
        j.add('fn').value = full_name
        name_parts = full_name.split()
        if len(name_parts) > 1:
            j.add('n').value = vobject.vcard.Name(family=name_parts[-1], given=" ".join(name_parts[:-1]))
        else:
            j.add('n').value = vobject.vcard.Name(given=full_name)

    # Organization / Company
    company = card_data.get("company_name", "").strip()
    if company:
        j.add('org').value = [company]

    # Title / Job Role
    title = card_data.get("job_title", "").strip()
    if title:
        j.add('title').value = title

    # Phone 1 (CELL)
    phone = card_data.get("phone", "").strip()
    if phone:
        tel = j.add('tel')
        tel.value = phone
        tel.type_param = 'CELL'

    # Phone 2 (WORK / Hotline)
    phone_2 = card_data.get("phone_2", "").strip()
    if phone_2:
        tel2 = j.add('tel')
        tel2.value = phone_2
        tel2.type_param = 'WORK'

    # Email
    email = card_data.get("email", "").strip()
    if email:
        em = j.add('email')
        em.value = email
        em.type_param = 'INTERNET'

    # Website
    website = card_data.get("website", "").strip()
    if website:
        j.add('url').value = website

    # Address
    address = card_data.get("address", "").strip()
    if address:
        adr = j.add('adr')
        adr.value = vobject.vcard.Address(street=address)

    return j.serialize()

def clean_phone_for_sheets(val):
    if not val:
        return ""
    val_str = str(val).strip()
    # Add single quote prefix to leading '+' so Google Sheets stores any international phone number (+84, +65, +1, +44...) as raw Text without formula error
    if val_str.startswith("+"):
        val_str = "'" + val_str
    return val_str

def sanitize_card_data(card_data: dict | list):
    """Sanitizes card data dictionary or list to ensure safe serialization."""
    def clean_item(item):
        if not isinstance(item, dict):
            return item
        cleaned = {}
        for k, v in item.items():
            val = v if v is not None else ""
            if k in ["phone", "phone_2"]:
                val = clean_phone_for_sheets(val)
            cleaned[k] = val
        return cleaned

    if isinstance(card_data, dict):
        return clean_item(card_data)
    elif isinstance(card_data, list):
        return [clean_item(i) for i in card_data]
    return card_data

COLUMN_MAPPING = {
    "company_name": "Tên công ty / Tổ chức",
    "full_name": "Họ và tên chủ thẻ",
    "job_title": "Chức danh / Chuyên môn",
    "phone": "Số điện thoại 1",
    "phone_2": "Số điện thoại 2",
    "email": "Email",
    "website": "Website",
    "address": "Địa chỉ văn phòng",
    "scanned_by": "Người quét",
    "created_at": "Thời gian quét"
}

def generate_excel(card_data_list: list) -> bytes:
    """Generates Excel file bytes for export."""
    sanitized = sanitize_card_data(card_data_list)
    df = pd.DataFrame(sanitized)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def generate_csv(card_data_list: list) -> bytes:
    """Generates CSV file bytes for export."""
    sanitized = sanitize_card_data(card_data_list)
    df = pd.DataFrame(sanitized)
    df.rename(columns=COLUMN_MAPPING, inplace=True)
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    return output.getvalue().encode("utf-8-sig")

def export_to_excel(card_data_list: list, filepath: str):
    """Exports card data list to Excel file path."""
    sanitized = sanitize_card_data(card_data_list)
    df = pd.DataFrame(sanitized)
    df.to_excel(filepath, index=False)
    return filepath

def export_to_csv(card_data_list: list, filepath: str):
    """Exports card data list to CSV file path."""
    sanitized = sanitize_card_data(card_data_list)
    df = pd.DataFrame(sanitized)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    return filepath

def send_to_google_sheet(card_data: dict | list, webhook_url: str) -> dict:
    """Sends card data or card list to Google Apps Script Webhook URL safely."""
    import requests
    if not webhook_url or not webhook_url.startswith("http"):
        return {"success": False, "error": "Google Sheet Webhook URL chưa được cấu hình hoặc không hợp lệ."}
    
    headers = {"Content-Type": "application/json"}
    payload = sanitize_card_data(card_data)
    
    try:
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=15)
        if resp.status_code >= 400:
            return {"success": False, "error": f"Lỗi Google Sheet API ({resp.status_code}): {resp.text}"}
        return {"success": True, "message": "Đã lưu thông tin vào Google Sheet thành công!"}
    except Exception as e:
        return {"success": False, "error": f"Lỗi gửi dữ liệu Google Sheet: {str(e)}"}
