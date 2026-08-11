import os
import time
import json
import io
import sys
import shutil
import requests

# Force UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response, BackgroundTasks, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.engines.cloud_vision import extract_with_gemini_vision

try:
    from backend.engines.local_ocr import extract_with_local_ocr
except Exception:
    def extract_with_local_ocr(*args, **kwargs):
        return {"error": "Local OCR (OpenCV/Tesseract) không khả dụng trên Cloud Vercel. Vui lòng dùng AI Vision."}

from backend.utils.dip_processor import crop_by_custom_points
from backend.utils.exporter import generate_vcard, generate_excel, generate_csv, send_to_google_sheet

load_dotenv(override=True)

app = FastAPI(
    title="Business Card OCR & AI Extractor",
    description="Dual Engine OCR Application: Cloud AI Vision & Local DIP OpenCV",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# ANTI-SPAM RATE LIMITER MIDDLEWARE (Chống spam request liên tục)
# --------------------------------------------------------------------------
from collections import defaultdict
from fastapi import Request

RATE_LIMIT_STORE = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 10
WINDOW_SECONDS = 60

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only limit sensitive heavy API endpoints
    path = request.url.path
    if path in ["/api/extract", "/api/auth/login", "/api/save-database", "/api/save-google-sheet"]:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Clean timestamps older than 60 seconds
        RATE_LIMIT_STORE[client_ip] = [
            t for t in RATE_LIMIT_STORE[client_ip] if now - t < WINDOW_SECONDS
        ]
        
        if len(RATE_LIMIT_STORE[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            return Response(
                content=json.dumps({"detail": "Cảnh báo bảo mật (429): Bạn đang gửi request quá nhanh! Vui lòng chờ 60 giây trước khi thử lại."}, ensure_ascii=False),
                status_code=429,
                media_type="application/json"
            )
            
        RATE_LIMIT_STORE[client_ip].append(now)

    response = await call_next(request)
    return response

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
CARD_TEST_DIR = os.path.join(BASE_DIR, "Card_test")

app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "src")), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Business Card OCR Application</h1>")

@app.get("/sw.js")
async def serve_sw():
    sw_path = os.path.join(FRONTEND_DIR, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service worker not found")


@app.get("/manifest.json")
async def serve_manifest():
    manifest_path = os.path.join(FRONTEND_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest not found")

@app.get("/api/sample-cards")
async def get_sample_cards():
    if not os.path.exists(CARD_TEST_DIR):
        return {"samples": []}
    files = [f for f in os.listdir(CARD_TEST_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    return {"samples": sorted(files)}

@app.get("/api/sample-cards/{filename}")
async def get_sample_card_file(filename: str):
    file_path = os.path.join(CARD_TEST_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File không tồn tại")

@app.post("/api/extract")
async def extract_card_info(
    file: UploadFile = File(None),
    sample_filename: str = Form(None),
    engine: str = Form("v1"),
    api_key: str = Form(None),
    crop_points_json: str = Form(None)
):
    image_bytes = None

    if file:
        image_bytes = await file.read()
    elif sample_filename:
        sample_path = os.path.join(CARD_TEST_DIR, sample_filename)
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                image_bytes = f.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Vui lòng tải lên ảnh card hoặc chọn ảnh mẫu.")

    if crop_points_json:
        try:
            points_list = json.loads(crop_points_json)
            if len(points_list) == 4:
                image_bytes = crop_by_custom_points(image_bytes, points_list)
        except Exception:
            pass

    response_payload = {}

    if engine in ["v1", "compare"]:
        t0 = time.time()
        try:
            res_v1 = extract_with_gemini_vision(image_bytes, api_key=api_key)
        except Exception as e:
            res_v1 = {
                "error": f"Lỗi V1 Cloud Vision: {str(e)}",
                "company_name": "", "full_name": "", "job_title": "",
                "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": ""
            }
        t1 = time.time()
        res_v1["latency_ms"] = round((t1 - t0) * 1000, 2)
        response_payload["v1"] = res_v1

    if engine in ["v2", "compare"]:
        t0 = time.time()
        try:
            res_v2 = extract_with_local_ocr(image_bytes)
        except Exception as e:
            res_v2 = {
                "error": f"Lỗi V2 Local OCR: {str(e)}",
                "company_name": "", "full_name": "", "job_title": "",
                "phone": "", "phone_2": "", "email": "", "website": "", "address": "", "tax_code": ""
            }
        t1 = time.time()
        res_v2["latency_ms"] = round((t1 - t0) * 1000, 2)
        response_payload["v2"] = res_v2

    if engine == "v1":
        response_payload["result"] = response_payload.get("v1", {})
    elif engine == "v2":
        response_payload["result"] = response_payload.get("v2", {})
    else:
        response_payload["result"] = response_payload.get("v1", {})

    # Auto-save extracted card record to Neon Postgres / Database
    try:
        from backend.database.db_manager import save_card_to_database, extract_token_from_request, decode_jwt_token
        token = extract_token_from_request(request)
        scanned_by = "Guest"
        if token:
            user_info = decode_jwt_token(token)
            if user_info:
                scanned_by = user_info.get("full_name") or user_info.get("username") or "Admin"
        
        final_res = response_payload.get("result", {})
        if "error" not in final_res and (final_res.get("full_name") or final_res.get("company_name") or final_res.get("phone")):
            save_card_to_database(final_res, owner_token=token or "anon", scanned_by=scanned_by)
    except Exception as err_dbsave:
        print(f"[DB Auto Save Error]: {err_dbsave}")

    return response_payload

@app.post("/api/export/vcard")
async def export_vcard_endpoint(card_data: dict):
    vcard_str = generate_vcard(card_data)
    name = card_data.get("full_name", "contact").replace(" ", "_")
    filename = f"{name}.vcf"
    
    return Response(
        content=vcard_str.encode("utf-8"),
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/export/excel")
async def export_excel_endpoint(card_list: list):
    excel_bytes = generate_excel(card_list)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=scanned_cards.xlsx"}
    )

@app.post("/api/export/csv")
async def export_csv_endpoint(card_list: list):
    csv_bytes = generate_csv(card_list)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=scanned_cards.csv"}
    )

@app.post("/api/save-google-sheet")
async def save_google_sheet_endpoint(request: Request, payload: dict):
    from backend.database.db_manager import decode_jwt_token
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return {"success": False, "error": "Chưa cài đặt GOOGLE_SHEET_WEBHOOK_URL trên Vercel Environment Variables."}
    
    # Extract scanned_by user
    token = extract_token_from_request(request)
    scanned_by = "Guest"
    if token:
        user_info = decode_jwt_token(token)
        if user_info:
            scanned_by = user_info.get("full_name") or user_info.get("username") or "Admin"
    
    # Also save/ensure card record is saved to Neon Database
    try:
        from backend.database.db_manager import save_card_to_database
        if isinstance(payload, dict):
            save_card_to_database(payload, owner_token=token or "anon", scanned_by=scanned_by)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    save_card_to_database(item, owner_token=token or "anon", scanned_by=scanned_by)
    except Exception as err_dbsave2:
        print(f"[DB Save Sheet Endpoint Error]: {err_dbsave2}")

    return send_to_google_sheet(payload, webhook_url)

# --------------------------------------------------------------------------
# INTERNATIONAL STANDARD AUTHENTICATION ENDPOINTS (JWT Cookie + Bearer Token)
# --------------------------------------------------------------------------
def extract_token_from_request(request: Request, access_token_cookie: str = None) -> str | None:
    from backend.database.db_manager import decode_jwt_token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        tok = auth_header.split(" ", 1)[1].strip()
        if decode_jwt_token(tok):
            return tok
    if access_token_cookie and decode_jwt_token(access_token_cookie):
        return access_token_cookie
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return access_token_cookie

@app.post("/api/auth/login")
async def login_endpoint(payload: dict, response: Response, request: Request):
    try:
        username = payload.get("username", "").strip() if payload else ""
        password = payload.get("password", "").strip() if payload else ""

        if not username or not password:
            raise HTTPException(status_code=400, detail="Vui lòng nhập đầy đủ Username và Mật khẩu.")

        from backend.database.db_manager import SessionLocal, hash_username, verify_password, create_jwt_token, seed_default_user
        from backend.database.models import UserCredential, UserProfile

        # Ensure CITARES seed user exists on fresh Neon DB
        try:
            seed_default_user()
        except Exception as seed_err:
            print(f"[Seed Error]: {seed_err}")

        db = SessionLocal()
        try:
            u_hash = hash_username(username)
            cred = db.query(UserCredential).filter(UserCredential.username_hash == u_hash).first()
            if not cred or not verify_password(password, cred.password_hash):
                raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không chính xác.")

            profile = db.query(UserProfile).filter(UserProfile.account_token == cred.account_token).first()
            token = create_jwt_token(cred.account_token)

            is_https = request.headers.get("x-forwarded-proto") == "https" or bool(os.getenv("VERCEL")) or request.url.scheme == "https"

            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                samesite="lax",
                max_age=86400 * 7,
                secure=is_https
            )

            return {
                "success": True,
                "message": "Đăng nhập thành công!",
                "token": token,
                "user": {
                    "account_token": cred.account_token,
                    "full_name": profile.full_name if profile else username,
                    "email": profile.email if profile else "",
                    "role": profile.role if profile else "user"
                }
            }
        finally:
            db.close()
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Server (500): {str(e)}")

@app.post("/api/auth/register")
async def register_endpoint(payload: dict, response: Response, request: Request, access_token: str = Cookie(None)):
    from backend.database.db_manager import decode_jwt_token, SessionLocal, hash_username, hash_password, create_jwt_token
    from backend.database.models import UserCredential, UserProfile

    token_str = extract_token_from_request(request, access_token)
    if not token_str:
        raise HTTPException(status_code=403, detail="Chưa đăng nhập! Chỉ có tài khoản Admin mới có quyền cấp tài khoản người dùng mới.")

    account_token = decode_jwt_token(token_str)
    if not account_token:
        raise HTTPException(status_code=403, detail="Token không hợp lệ.")

    db = SessionLocal()
    try:
        current_profile = db.query(UserProfile).filter(UserProfile.account_token == account_token).first()
        if not current_profile or current_profile.role != "admin":
            raise HTTPException(status_code=403, detail="Bảo mật: Chỉ có tài khoản Admin mới có quyền tạo tài khoản người dùng mới!")

        username = payload.get("username", "").strip()
        password = payload.get("password", "").strip()
        full_name = payload.get("full_name", username).strip()
        email = payload.get("email", "").strip()
        role = payload.get("role", "user").strip()

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username và Mật khẩu không được để trống.")

        u_hash = hash_username(username)
        existing = db.query(UserCredential).filter(UserCredential.username_hash == u_hash).first()
        if existing:
            raise HTTPException(status_code=400, detail="Tên đăng nhập này đã tồn tại.")

        p_hash = hash_password(password)
        cred = UserCredential(username_hash=u_hash, password_hash=p_hash)
        db.add(cred)
        db.commit()
        db.refresh(cred)

        profile = UserProfile(
            account_token=cred.account_token,
            full_name=full_name,
            email=email,
            role=role
        )
        db.add(profile)
        db.commit()

        return {
            "success": True,
            "message": f"Admin đã cấp thành công tài khoản mới cho {username}!",
            "user": {
                "account_token": cred.account_token,
                "full_name": full_name,
                "email": email,
                "role": role
            }
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

@app.get("/api/auth/me")
async def get_current_user_endpoint(request: Request, access_token: str = Cookie(None)):
    token_str = extract_token_from_request(request, access_token)
    if not token_str:
        return {"authenticated": False}

    from backend.database.db_manager import decode_jwt_token, SessionLocal
    from backend.database.models import UserProfile

    account_token = decode_jwt_token(token_str)
    if not account_token:
        return {"authenticated": False}

    db = SessionLocal()
    try:
        profile = db.query(UserProfile).filter(UserProfile.account_token == account_token).first()
        if not profile:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "user": {
                "account_token": profile.account_token,
                "full_name": profile.full_name,
                "email": profile.email,
                "role": profile.role
            }
        }
    finally:
        db.close()

@app.post("/api/auth/logout")
async def logout_endpoint(response: Response):
    response.delete_cookie("access_token")
    return {"success": True, "message": "Đã đăng xuất an toàn!"}

@app.post("/api/save-database")
async def save_database_endpoint(payload: dict, access_token: str = Cookie(None)):
    card_data = payload.get("card_data") or payload
    from backend.database.db_manager import decode_jwt_token, save_card_to_database, SessionLocal
    from backend.database.models import UserProfile

    owner_token = "anon_user"
    scanned_by = card_data.get("scanned_by", "")

    if access_token:
        acc_tok = decode_jwt_token(access_token)
        if acc_tok:
            owner_token = acc_tok
            db = SessionLocal()
            try:
                prof = db.query(UserProfile).filter(UserProfile.account_token == acc_tok).first()
                if prof:
                    scanned_by = prof.full_name or prof.email
            finally:
                db.close()

    card_data["scanned_by"] = scanned_by
    success = save_card_to_database(card_data, owner_token=owner_token, scanned_by=scanned_by)
    if success:
        return {"success": True, "message": "Đã lưu thành công vĩnh viễn vào CSDL (Database)!"}
    raise HTTPException(status_code=500, detail="Không thể lưu vào Cơ sở dữ liệu.")

@app.post("/api/save-google-sheet")
async def save_google_sheet_endpoint(payload: dict, access_token: str = Cookie(None)):
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
    card_data = payload.get("card_data") or payload

    from backend.database.db_manager import decode_jwt_token, save_card_to_database, SessionLocal
    from backend.database.models import UserProfile

    owner_token = "anon_user"
    scanned_by = card_data.get("scanned_by", "")

    if access_token:
        acc_tok = decode_jwt_token(access_token)
        if acc_tok:
            owner_token = acc_tok
            db = SessionLocal()
            try:
                prof = db.query(UserProfile).filter(UserProfile.account_token == acc_tok).first()
                if prof:
                    scanned_by = prof.full_name or prof.email
            finally:
                db.close()

    card_data["scanned_by"] = scanned_by

    # 1. Parallel Auto Backup to Database (Table 3: card_records)
    save_card_to_database(card_data, owner_token=owner_token, scanned_by=scanned_by)

    if not webhook_url:
        return {"success": True, "message": "Đã lưu bản sao vĩnh viễn vào CSDL! (Cần cấu hình thêm GOOGLE_SHEET_WEBHOOK_URL để đồng bộ sang Google Sheet)"}

@app.get("/api/cards/history")
async def get_card_history_endpoint(access_token: str = Cookie(None)):
    from backend.database.db_manager import decode_jwt_token, SessionLocal
    from backend.database.models import CardRecord, UserProfile

    if not access_token:
        return {"history": []}

    account_token = decode_jwt_token(access_token)
    if not account_token:
        return {"history": []}

    db = SessionLocal()
    try:
        prof = db.query(UserProfile).filter(UserProfile.account_token == account_token).first()
        if prof and prof.role == "admin":
            # Admin sees all card records
            records = db.query(CardRecord).order_by(CardRecord.card_id.desc()).limit(50).all()
        else:
            # Regular user sees their own scanned cards
            records = db.query(CardRecord).filter(CardRecord.owner_token == account_token).order_by(CardRecord.card_id.desc()).limit(50).all()

        history_list = []
        for r in records:
            history_list.append({
                "id": r.card_id,
                "company_name": r.company_name,
                "full_name": r.full_name,
                "job_title": r.job_title,
                "phone": r.phone,
                "phone_2": r.phone_2,
                "email": r.email,
                "website": r.website,
                "address": r.address,
                "scanned_by": r.scanned_by,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            })
        return {"history": history_list}
    finally:
        db.close()

# --------------------------------------------------------------------------
# RESILIENT BACKGROUND WORKER TASK (Dù thoát app giữa chừng vẫn lưu DB 100%)
# --------------------------------------------------------------------------
def run_background_card_processing(image_bytes: bytes, owner_token: str, scanned_by: str, api_key: str = None):
    try:
        print(f"[BACKGROUND WORKER]: Starting background AI vision extraction for {scanned_by}...")
        res = extract_with_gemini_vision(image_bytes, api_key=api_key)
        if res and "error" not in res:
            res["scanned_by"] = scanned_by
            from backend.database.db_manager import save_card_to_database
            save_card_to_database(res, owner_token=owner_token, scanned_by=scanned_by)
            print(f"[BACKGROUND WORKER SUCCESS]: Card for {res.get('full_name')} saved to DB automatically!")
        else:
            print(f"[BACKGROUND WORKER ERROR]: {res.get('error')}")
    except Exception as e:
        print(f"[BACKGROUND WORKER EXCEPTION]: {e}")

@app.post("/api/extract-background")
async def extract_card_background_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    access_token: str = Cookie(None)
):
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Vui lòng gửi file ảnh card hợp lệ.")

    from backend.database.db_manager import decode_jwt_token, SessionLocal
    from backend.database.models import UserProfile

    owner_token = "anon_user"
    scanned_by = "Người dùng vô danh"

    if access_token:
        acc_tok = decode_jwt_token(access_token)
        if acc_tok:
            owner_token = acc_tok
            db = SessionLocal()
            try:
                prof = db.query(UserProfile).filter(UserProfile.account_token == acc_tok).first()
                if prof:
                    scanned_by = prof.full_name or prof.email
            finally:
                db.close()

    # Enqueue background task (Runs asynchronously on server EVEN IF USER CLOSES APP)
    background_tasks.add_task(run_background_card_processing, image_bytes, owner_token, scanned_by)

    return {
        "status": "processing",
        "message": f"Server đã nhận ảnh thành công! Dù bạn tắt app hay thoát trình duyệt, hệ thống vẫn đang trích xuất ngầm và sẽ tự động lưu vào CSDL cho {scanned_by}."
    }

@app.post("/api/export/google-sheet")
async def export_google_sheet_endpoint(payload: dict):
    card_list = payload.get("cards", [])
    webhook_url = payload.get("webhook_url") or os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Chưa cấu hình Google Sheet Webhook URL. Vui lòng nhập URL Webhook trên giao diện hoặc trong file .env")
    
    try:
        res = send_to_google_sheet(card_list, webhook_url)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

