# Business Card Reader & Extractor v2.1 (Cross-Platform Web & Mobile)

Hệ thống trích xuất thông tin Danh thiếp (Business Card) Đa ngôn ngữ (Tiếng Việt & Tiếng Anh), tích hợp kiến trúc **Dual Engine AI Vision** kép (NVIDIA NIM Llama 3.2 11B Vision & Google Gemini 3.6 Flash), hệ thống phân quyền tài khoản JWT, cùng quy trình **Tự động hóa Đồng bộ & Sao lưu Google Sheets / Google Drive**.

---

## 🌟 Tính Năng Nổi Bật (Phiên Bản 2.1)

1. **Dual Engine AI Vision Kép (Tốc Độ & Độ Chính Xác Cao)**:
   - 🟢 **Primary (Ưu tiên 1)**: `NVIDIA NIM - Meta Llama 3.2 11B Vision Instruct` — Xử lý hình ảnh và văn bản đa ngôn ngữ siêu nhanh với độ chính xác cao.
   - 🟡 **Fallback (Dự phòng 2)**: `Google Gemini 3.6 Flash` — Tự động dự phòng ngầm khi NVIDIA xảy ra ngắt kết nối hoặc hết quota.

2. **Chụp Ảnh Trực Tiếp & Làm Nét Chữ (Camera HD & Mobile Native)**:
   - 📱 **Mobile Native Camera**: Kích hoạt trực tiếp Ứng dụng Camera mặc định của điện thoại (iOS / Android), chụp ảnh sắc nét với độ phân giải gốc 100% (12MP - 48MP).
   - 💻 **Webcam Live HD**: Ép khung hình 1080p, hỗ trợ tự động căn góc và bộ lọc **Làm sắc nét chữ (AI Boost)** giúp tăng độ tương phản khi chụp bằng máy tính.

3. **Tự Động Đồng Bộ Google Sheets & Sao Lưu Google Drive**:
   - 📊 **Lưu 1-Click vào Google Sheet**: Tự động lưu thông tin chủ thẻ, số điện thoại (đã định dạng chuẩn tránh lỗi công thức), email, công ty, thời gian quét và **Tên tài khoản người quét**.
   - 🔄 **Sao lưu Xoay Vòng Google Drive (Mỗi 4 ngày/lần)**: Tự động chạy ngầm sao lưu file dữ liệu mới nhất vào thư mục `new_record` và di chuyển bản lưu trước đó sang `old_backup` để chống mất mát dữ liệu.

4. **Bảo Mật & Quản Lý Tài Khoản (JWT Auth & Admin System)**:
   - Hệ thống Đăng nhập / Đăng xuất bảo mật chuẩn quốc tế (JWT Token / Bearer Headers).
   - Phân quyền **Admin**: Cho phép tài khoản Admin cấp thêm tài khoản người dùng mới trực tiếp trên giao diện Web.

5. **Xuất Dữ Liệu Đa Dạng**:
   - 📱 **Tải file vCard (`.vcf`)**: Lưu danh bạ trực tiếp vào điện thoại iPhone/Android.
   - 📊 **Xuất File Excel (`.xlsx`) & CSV (`.csv`)**: Phù hợp cho việc lưu trữ và xuất báo cáo.

---


## 🚀 Hướng Dẫn Khởi Chạy Dự Án

### Cách 1: Chạy Nhanh 1-Click trên Windows
Nhấp kép vào file `run.bat` trong thư mục gốc dự án. Script sẽ tự động kích hoạt môi trường `venv` và chạy server tại `http://localhost:8000`.

### Cách 2: Chạy Thủ Công Qua Terminal
```bash
# 1. Kích hoạt môi trường ảo venv
venv\Scripts\activate.bat        # Trên Windows
# source venv/bin/activate        # Trên Linux/macOS

# 2. Cài đặt các thư viện bổ sung (nếu chưa có)
pip install -r requirements.txt

# 3. Khởi chạy Server FastAPI Backend
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

Sau khi khởi chạy:
- **Truy cập từ Máy tính**: `http://localhost:8000`
- **Truy cập từ Điện thoại (Cùng Wi-Fi)**: `http://<IP_MAY_TINH>:8000`

---

## 🌐 Hướng Dẫn Deploy Production (Miễn Phí)

- **Frontend**: Push code lên GitHub -> Deploy lên **Vercel** -> Trỏ tên miền riêng (Custom Domain).
- **Backend**: Deploy lên **Render.com** (dùng web service Python) -> Khai báo các biến `.env` trên Render Environment Settings.
- **Database**: Sử dụng PostgreSQL Cloud (Supabase hoặc Neon) để giữ dữ liệu bền vững.
