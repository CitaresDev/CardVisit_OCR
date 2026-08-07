import os
import io
import csv
import pandas as pd
import vobject

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

def generate_excel(card_data_list: list) -> bytes:
    """Generates Excel file bytes for export."""
    df = pd.DataFrame(card_data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def generate_csv(card_data_list: list) -> bytes:
    """Generates CSV file bytes for export."""
    df = pd.DataFrame(card_data_list)
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    return output.getvalue().encode("utf-8-sig")

def export_to_excel(card_data_list: list, filepath: str):
    """Exports card data list to Excel file path."""
    df = pd.DataFrame(card_data_list)
    df.to_excel(filepath, index=False)
    return filepath

def export_to_csv(card_data_list: list, filepath: str):
    """Exports card data list to CSV file path."""
    df = pd.DataFrame(card_data_list)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    return filepath

def send_to_google_sheet(card_data_list: list, webhook_url: str) -> dict:
    """Sends card data list to Google Apps Script Webhook URL."""
    import requests
    if not webhook_url or not webhook_url.startswith("http"):
        raise ValueError("Google Sheet Webhook URL không hợp lệ hoặc bị trống.")
    
    headers = {"Content-Type": "application/json"}
    resp = requests.post(webhook_url, json=card_data_list, headers=headers, timeout=15)
    
    if resp.status_code >= 400:
        raise Exception(f"Lỗi kết nối Google Sheet ({resp.status_code}): {resp.text}")
    
    try:
        return resp.json()
    except Exception:
        return {"status": "success", "message": "Đã gửi dữ liệu sang Google Sheet"}

