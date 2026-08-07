import os
import json
import base64
import requests
import re
from dotenv import load_dotenv

def parse_robust_json(text_content: str) -> dict:
    """
    Dual-mode parser: Parses JSON objects AND key-value bullet points (* key: val).
    """
    text_clean = text_content.strip()
    text_clean = re.sub(r"^```(?:json)?", "", text_clean, flags=re.IGNORECASE).strip()
    text_clean = re.sub(r"```$", "", text_clean).strip()
    
    # 1. Standard JSON Parse Attempt
    start_idx = text_clean.find("{")
    end_idx = text_clean.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_candidate = text_clean[start_idx : end_idx + 1]
        try:
            return json.loads(json_candidate)
        except Exception:
            pass
            
    try:
        return json.loads(text_clean)
    except Exception:
        pass

    # 2. Key-Value / Bullet Points Fallback Parser (* key: value or key: value)
    result = {
        "company_name": "", "full_name": "", "job_title": "",
        "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": ""
    }

    lines = text_clean.split("\n")
    for line in lines:
        line_s = line.strip().lstrip("*").lstrip("-").strip()
        if ":" in line_s:
            parts = line_s.split(":", 1)
            key = parts[0].strip().lower().replace(" ", "_")
            val = parts[1].strip()

            if val.lower() in ["none", "null", "n/a", "undefined"]:
                val = ""

            if "company" in key:
                result["company_name"] = val
            elif "full" in key or "name" in key:
                result["full_name"] = val
            elif "job" in key or "title" in key:
                result["job_title"] = val
            elif key in ["phone", "phone_1", "phone1", "telephone", "mobile"]:
                result["phone"] = val
            elif key in ["phone_2", "phone2", "secondary_phone", "mobile2"]:
                result["phone_2"] = val
            elif "email" in key:
                result["email"] = val
            elif "web" in key or "url" in key:
                result["website"] = val
            elif "addr" in key:
                result["address"] = val
            elif "tax" in key:
                result["tax_code"] = val

    return result

def clean_phone_number(p: str) -> str:
    if not p:
        return ""
    return p.replace(".", "").strip()

def split_multiple_phones(res: dict) -> dict:
    """Delimiter-first post-processor that cleanly splits combined phone strings into phone 1 and phone 2."""
    phone1 = str(res.get("phone", "")).strip()
    phone2 = str(res.get("phone_2", "")).strip()

    if phone1 and not phone2:
        # 1. Try splitting by explicit delimiters first
        delimiters = [" - ", " / ", ",", ";", "\n", " | "]
        parts = []
        for d in delimiters:
            if d in phone1:
                parts = [p.strip() for p in phone1.split(d) if p.strip()]
                break

        if len(parts) >= 2:
            res["phone"] = parts[0]
            res["phone_2"] = parts[1]
        else:
            # 2. Try matching multiple standalone phone numbers in phone1
            phone_pattern = r'(?:(?:\+84|0|\(0\d+\))[\d\s.-]{7,15})'
            found = [p.strip() for p in re.findall(phone_pattern, phone1) if len(re.sub(r'\D', '', p)) >= 8]
            if len(found) >= 2:
                res["phone"] = found[0]
                res["phone_2"] = found[1]

    if res.get("phone"):
        res["phone"] = clean_phone_number(res["phone"])
    if res.get("phone_2"):
        res["phone_2"] = clean_phone_number(res["phone_2"])

    return res

def auto_fill_phone_2_hybrid(res: dict, image_bytes: bytes = None) -> dict:
    """Format and clean phone numbers extracted by Pure Cloud AI Vision."""
    if res.get("phone"):
        res["phone"] = clean_phone_number(res["phone"])
    if res.get("phone_2"):
        res["phone_2"] = clean_phone_number(res["phone_2"])
    return res

def extract_with_nvidia_llama_vision(image_bytes: bytes, api_key: str) -> dict:
    """
    PRIORITY 1: Uses NVIDIA NIM API with Meta Llama 3.2 11B Vision Instruct.
    """
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64_image}"

    prompt = """
Hãy đọc kỹ hình ảnh danh thiếp (Business Card) này và bóc tách thông tin chính xác theo định dạng JSON duy nhất:

{
  "company_name": "Tên công ty hoặc tổ chức",
  "full_name": "Họ và tên chủ danh thiếp",
  "job_title": "Chức danh công việc",
  "phone": "Số điện thoại thứ 1 đọc được (số di động hoặc số bàn)",
  "phone_2": "Số điện thoại thứ 2 đọc được (nếu trên card có 2 số điện thoại ở 2 dòng khác nhau hoặc cách nhau dấu gạch ngang -, bắt buộc phải điền số thứ 2 vào đây)",
  "email": "Địa chỉ email liên hệ",
  "website": "Trang web công ty",
  "address": "Địa chỉ văn phòng",
  "tax_code": "Mã số thuế"
}

YÊU CẦU:
1. Đọc tất cả các dòng chữ trên card. Nếu có 2 số điện thoại khác nhau, bắt buộc số thứ 1 vào "phone" và số thứ 2 vào "phone_2".
2. Trả về duy nhất khối JSON hợp lệ.
"""

    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=25)
        if response.status_code != 200:
            err_detail = response.json().get("error", {}).get("message", response.text)
            return {"error": f"NVIDIA API ({response.status_code}): {err_detail}"}

        res_data = response.json()
        choices = res_data.get("choices", [])
        if not choices:
            return {"error": "No response from NVIDIA Llama 3.2 Vision"}

        text_content = choices[0].get("message", {}).get("content", "")
        parsed = parse_robust_json(text_content)

        res_dict = {
            "engine": "NVIDIA NIM - Llama 3.2 11B Vision",
            "company_name": parsed.get("company_name", ""),
            "full_name": parsed.get("full_name", ""),
            "job_title": parsed.get("job_title", ""),
            "phone": parsed.get("phone", ""),
            "phone_2": parsed.get("phone_2", ""),
            "email": parsed.get("email", ""),
            "website": parsed.get("website", ""),
            "address": parsed.get("address", ""),
            "tax_code": parsed.get("tax_code", "")
        }

        # If extraction is empty, return error to allow fallback
        if not res_dict.get("company_name") and not res_dict.get("full_name") and not res_dict.get("phone"):
            return {"error": "NVIDIA Llama Vision returned empty extraction result"}

        res_dict = split_multiple_phones(res_dict)
        return auto_fill_phone_2_hybrid(res_dict, image_bytes)
    except Exception as e:
        return {"error": f"Ngoại lệ NVIDIA Llama Vision: {str(e)}"}

def extract_with_gemini_vision_direct(image_bytes: bytes, api_key: str) -> dict:
    """
    PRIORITY 2 (Fallback): Uses Gemini 2.0 Flash Vision API.
    """
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    prompt = """
Hãy đọc kỹ hình ảnh danh thiếp (Business Card) này và bóc tách thông tin chính xác theo định dạng JSON duy nhất:

{
  "company_name": "Tên công ty hoặc tổ chức",
  "full_name": "Họ và tên chủ danh thiếp",
  "job_title": "Chức danh công việc",
  "phone": "Số điện thoại thứ 1 đọc được (số di động hoặc số bàn)",
  "phone_2": "Số điện thoại thứ 2 đọc được (nếu trên card có 2 số điện thoại ở 2 dòng khác nhau hoặc cách nhau dấu gạch ngang -, bắt buộc phải điền số thứ 2 vào đây)",
  "email": "Địa chỉ email liên hệ",
  "website": "Trang web công ty",
  "address": "Địa chỉ văn phòng",
  "tax_code": "Mã số thuế"
}

YÊU CẦU:
1. Đọc tất cả các dòng chữ trên card. Nếu có 2 số điện thoại khác nhau, bắt buộc số thứ 1 vào "phone" và số thứ 2 vào "phone_2".
2. Trả về duy nhất khối JSON hợp lệ.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code != 200:
            err_detail = response.json().get("error", {}).get("message", response.text)
            return {"error": f"Gemini API ({response.status_code}): {err_detail}"}

        res_data = response.json()
        candidates = res_data.get("candidates", [])
        if not candidates:
            return {"error": "Không nhận được phản hồi từ Gemini AI Vision"}

        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        parsed = parse_robust_json(text_content)

        res_dict = {
            "engine": "Gemini 2.0 Flash Vision (Cloud AI)",
            "company_name": parsed.get("company_name", ""),
            "full_name": parsed.get("full_name", ""),
            "job_title": parsed.get("job_title", ""),
            "phone": parsed.get("phone", ""),
            "phone_2": parsed.get("phone_2", ""),
            "email": parsed.get("email", ""),
            "website": parsed.get("website", ""),
            "address": parsed.get("address", ""),
            "tax_code": parsed.get("tax_code", "")
        }
        res_dict = split_multiple_phones(res_dict)
        return auto_fill_phone_2_hybrid(res_dict, image_bytes)
    except Exception as e:
        return {"error": f"Ngoại lệ Gemini Vision: {str(e)}"}

def extract_with_gemini_vision(image_bytes: bytes, api_key: str = None) -> dict:
    """
    MAIN ENTRY POINT:
    Priority 1: NVIDIA Llama 3.2 Vision (using NVIDIA_API_KEY or passed nvapi- key)
    Priority 2 (Fallback): Gemini Vision (using GEMINI_API_KEY)
    """
    load_dotenv(override=True)
    
    # Check NVIDIA API Key
    nvidia_key = api_key if (api_key and api_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY", "").strip().strip('"').strip("'")
    if nvidia_key and nvidia_key.startswith("nvapi-") and not nvidia_key.endswith("your_nvidia_api_key_here"):
        res_nvidia = extract_with_nvidia_llama_vision(image_bytes, api_key=nvidia_key)
        if "error" not in res_nvidia:
            return res_nvidia
        err_msg = str(res_nvidia.get('error')).encode("ascii", "backslashreplace").decode("ascii")
        print(f"[WARNING] NVIDIA Llama Vision error: {err_msg}. Fallback to Gemini...")

    # Fallback to Gemini API Key
    gemini_key = api_key if (api_key and not api_key.startswith("nvapi-")) else os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if gemini_key and gemini_key != "your_gemini_api_key_here" and not gemini_key.startswith("nvapi-"):
        res_gemini = extract_with_gemini_vision_direct(image_bytes, api_key=gemini_key)
        if "error" not in res_gemini:
            return res_gemini
        err_msg_g = str(res_gemini.get('error')).encode("ascii", "backslashreplace").decode("ascii")
        print(f"[WARNING] Gemini Vision error: {err_msg_g}")

    return {
        "error": "Chưa tìm thấy API Key hợp lệ. Vui lòng dán NVIDIA_API_KEY hoặc GEMINI_API_KEY vào file d:\\CARD_VISIT\\.env",
        "company_name": "", "full_name": "", "job_title": "",
        "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": ""
    }
