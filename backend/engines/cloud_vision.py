import os
import json
import base64
import requests
import re
from dotenv import load_dotenv

def clean_value(val: str) -> str:
    if not val:
        return ""
    v = str(val).strip()
    v = re.sub(r"^[\*\"\'\`\#\-\:\s]+", "", v)
    v = re.sub(r"[\*\"\'\`\#\s]+$", "", v)
    v = v.strip()
    if v.lower() in ["none", "null", "n/a", "undefined"]:
        return ""
    return v

def clean_extracted_dict(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    cleaned = {}
    for k, v in data.items():
        if isinstance(v, str) and k != "engine" and k != "error":
            cleaned[k] = clean_value(v)
        else:
            cleaned[k] = v
    return cleaned

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
    return res

def clean_extracted_dict(res: dict) -> dict:
    """Strip markdown formatting (like **bold**) and clean values in extracted dictionary."""
    cleaned = {}
    for k, v in res.items():
        if isinstance(v, str):
            # Strip markdown ** and *
            val = v.replace("**", "").replace("*", "").strip()
            cleaned[k] = val
        else:
            cleaned[k] = v
    
    if cleaned.get("phone"):
        cleaned["phone"] = clean_phone_number(cleaned["phone"])
    if cleaned.get("phone_2"):
        cleaned["phone_2"] = clean_phone_number(cleaned["phone_2"])

    return cleaned

def auto_fill_phone_2_hybrid(res: dict, image_bytes: bytes = None) -> dict:
    """General cross-referencing fallback if AI Vision missed a 2nd phone line."""
    if image_bytes and res.get("phone") and not res.get("phone_2"):
        try:
            from backend.engines.local_ocr import extract_with_local_ocr
            loc_res = extract_with_local_ocr(image_bytes) or {}
            p1_digits = re.sub(r'\D', '', str(res.get("phone", "")))

            for loc_p in [loc_res.get("phone_2", "") if isinstance(loc_res, dict) else "", loc_res.get("phone", "") if isinstance(loc_res, dict) else ""]:
                loc_digits = re.sub(r'\D', '', str(loc_p))
                if len(loc_digits) >= 8 and loc_digits not in p1_digits and p1_digits not in loc_digits:
                    res["phone_2"] = loc_p
                    break
        except Exception as e:
            print(f"[Hybrid Fallback Notice]: {e}")

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
        parsed = parse_robust_json(text_content) or {}

        res_dict = {
            "engine": "NVIDIA NIM - Llama 3.2 11B Vision",
            "company_name": parsed.get("company_name", "") if isinstance(parsed, dict) else "",
            "full_name": parsed.get("full_name", "") if isinstance(parsed, dict) else "",
            "job_title": parsed.get("job_title", "") if isinstance(parsed, dict) else "",
            "phone": parsed.get("phone", "") if isinstance(parsed, dict) else "",
            "phone_2": parsed.get("phone_2", "") if isinstance(parsed, dict) else "",
            "email": parsed.get("email", "") if isinstance(parsed, dict) else "",
            "website": parsed.get("website", "") if isinstance(parsed, dict) else "",
            "address": parsed.get("address", "") if isinstance(parsed, dict) else "",
            "tax_code": parsed.get("tax_code", "") if isinstance(parsed, dict) else ""
        }

        if not res_dict.get("company_name") and not res_dict.get("full_name") and not res_dict.get("phone"):
            return {"error": "NVIDIA Llama Vision returned empty extraction result"}

        res_dict = clean_extracted_dict(res_dict)
        res_dict = split_multiple_phones(res_dict)
        return auto_fill_phone_2_hybrid(res_dict, image_bytes)
    except Exception as e:
        return {"error": f"Ngoại lệ NVIDIA Llama Vision: {str(e)}"}

def extract_with_gemini_vision_direct(image_bytes: bytes, api_key: str) -> dict:
    """
    Uses Gemini Vision REST API with high performance models.
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

    models_to_try = ["gemini-3.6-flash", "gemini-flash-latest"]
    last_error_text = ""

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                res_data = resp.json()
                candidates = res_data.get("candidates", [])
                if not candidates:
                    return {"error": "Không nhận được phản hồi từ Gemini AI Vision"}

                text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = parse_robust_json(text_content) or {}

                res_dict = {
                    "engine": f"Cloud AI Vision - Gemini ({model_name})",
                    "company_name": parsed.get("company_name", "") if isinstance(parsed, dict) else "",
                    "full_name": parsed.get("full_name", "") if isinstance(parsed, dict) else "",
                    "job_title": parsed.get("job_title", "") if isinstance(parsed, dict) else "",
                    "phone": parsed.get("phone", "") if isinstance(parsed, dict) else "",
                    "phone_2": parsed.get("phone_2", "") if isinstance(parsed, dict) else "",
                    "email": parsed.get("email", "") if isinstance(parsed, dict) else "",
                    "website": parsed.get("website", "") if isinstance(parsed, dict) else "",
                    "address": parsed.get("address", "") if isinstance(parsed, dict) else "",
                    "tax_code": parsed.get("tax_code", "") if isinstance(parsed, dict) else ""
                }
                res_dict = clean_extracted_dict(res_dict)
                res_dict = split_multiple_phones(res_dict)
                return auto_fill_phone_2_hybrid(res_dict, image_bytes)

            last_error_text = f"Gemini API ({resp.status_code}): {resp.text}"
        except Exception as err_rest:
            last_error_text = f"Ngoại lệ Gemini Vision: {str(err_rest)}"

    return {"error": last_error_text}

def extract_with_gemini_vision(image_bytes: bytes, api_key: str = None) -> dict:
    """
    MAIN ENTRY POINT:
    Priority 1: NVIDIA Llama 3.2 Vision (using NVIDIA_API_KEY)
    Priority 2 (Fallback): Gemini Vision (using GEMINI_API_KEY)
    """
    load_dotenv(override=True)
    last_error = ""

    # 1. Check NVIDIA API Key (Priority 1)
    nvidia_key = api_key if (api_key and api_key.startswith("nvapi-")) else os.getenv("NVIDIA_API_KEY", "").strip().strip('"').strip("'")
    if nvidia_key and nvidia_key != "your_nvidia_api_key_here":
        res_nvidia = extract_with_nvidia_llama_vision(image_bytes, api_key=nvidia_key)
        if "error" not in res_nvidia:
            return res_nvidia
        last_error = str(res_nvidia.get("error"))
        print(f"[WARNING] NVIDIA Llama Vision error: {last_error}. Fallback to Gemini...")

    # 2. Check Gemini API Key (Priority 2 Fallback)
    gemini_key = api_key if (api_key and not api_key.startswith("nvapi-")) else os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        res_gemini = extract_with_gemini_vision_direct(image_bytes, api_key=gemini_key)
        if "error" not in res_gemini:
            return res_gemini
        last_error = str(res_gemini.get("error"))
        print(f"[WARNING] Gemini Vision error: {last_error}")

    err_msg = last_error if last_error else "Chưa tìm thấy API Key hợp lệ. Vui lòng cài đặt NVIDIA_API_KEY hoặc GEMINI_API_KEY trên Vercel Environment Variables."

    return {
        "error": err_msg,
        "company_name": "", "full_name": "", "job_title": "",
        "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": ""
    }
