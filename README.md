# Business Card Reader & Extractor (Đa Nền Tảng: Desktop Web, Mobile Web & Android App)

Hệ thống trích xuất thông tin Card Visit song ngữ Tiếng Việt & Tiếng Anh đa nền tảng, tích hợp 2 Engine xử lý (Cloud AI Vision & Local Offline DIP OCR) kèm chế độ so sánh song song Side-by-Side.

---

## 🌟 Tính Năng Nổi Bật

1. **Đa Nền Tảng (Cross-Platform)**:
   - **Desktop Web**: Kéo thả ảnh, căn góc 4 điểm trực quan trên Canvas, giao diện Dashboard hiện đại.
   - **Mobile Web**: Mở máy ảnh chụp card visit trực tiếp từ điện thoại (`Camera Snap`).
   - **Android App (PWA)**: Bấm "Thêm vào Màn hình chính" trên Android để dùng như App Android bản địa.

2. **2 Engine Xử Lý Độc Lập & So Sánh Song Song**:
   - **Version 1 (Cloud AI Vision)**: Sử dụng Gemini 2.0 Flash Vision API (Miễn phí 1,500 card/ngày), nhận diện chính xác >95% Tiếng Việt & Tiếng Anh.
   - **Version 2 (Local Offline Engine)**: Sử dụng OpenCV DIP (Corner Detection & Perspective Warp) + Tesseract OCR + Spatial Regex Parser (100% Offline).
   - **Chế độ Compare Both**: Cho phép so sánh kết quả và tốc độ (latency ms) của 2 engine trên cùng 1 card.

3. **Xuất Dữ Liệu Tức Thì (Instant Export)**:
   - 📱 **Tải file vCard (`.vcf`)**: Lưu danh bạ thẳng vào điện thoại iPhone/Android.
   - 📊 **Xuất File CSV / Excel**: Lưu danh sách danh thiếp đã quét.
   - 📋 **Copy 1-Click**: Sao chép nhanh từng trường dữ liệu.

---

## 🔑 Cấu Hình API Key trong `.env`

Mở file **[.env](file:///d:/CARD_VISIT/.env)** tại thư mục gốc và dán API Key của bạn (NVIDIA hoặc Gemini):

```env
# NVIDIA API Key (Khuyên dùng - Lấy miễn phí tại build.nvidia.com)
NVIDIA_API_KEY=nvapi-your_nvidia_api_key_here

# Hoặc Gemini API Key (aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here
```

Sau khi lưu file `.env`, ứng dụng sẽ tự động nhận diện và sử dụng API Key mà bạn không cần phải nhập thủ công trên giao diện Web!

---

## 🚀 Hướng Dẫn Khởi Chạy

### Cách 1: Chạy 1-Click trên Windows (Đơn giản nhất)
Nhấp kép vào file `run.bat` trong thư mục gốc `d:\CARD_VISIT`. Script sẽ tự khởi động server và mở trình duyệt tại địa chỉ `http://localhost:8000`.

### Cách 2: Chạy bằng câu lệnh Terminal (Dùng môi trường ảo venv)
```bash
# 1. Tạo và kích hoạt môi trường ảo venv
python -m venv venv
venv\Scripts\activate.bat        # Trên Windows
# source venv/bin/activate        # Trên Linux/macOS

# 2. Cài đặt thư viện vào venv
pip install -r backend/requirements.txt

# 3. Khởi chạy server FastAPI từ venv
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

Sau khi chạy server, mở trình duyệt truy cập:
- **Địa chỉ máy tính**: `http://localhost:8000`
- **Địa chỉ điện thoại (cùng mạng Wi-Fi)**: `http://<IP_MAY_TINH>:8000`

---

## 🧪 Thử Nghiệm Với Bộ Card Mẫu (`Card_test`)
Trình duyệt sẽ hiển thị sẵn 4 card mẫu có sẵn trong thư mục `Card_test`:
- `card1.jpg`: Card màu vàng, bị ngón tay cầm, thông tin Tiếng Việt (`PHẠM XUÂN TÌNH`).
- `card2.jpg`: Card xanh `HUGTECH`, có ảnh chân dung (`PHẠM CAO HÙNG`).
- `card3.jpg`: Card `Kamogawa`, song ngữ Nhật-Anh-Việt.
- `card4.jpg`: Card `CITARES`, dạng chuẩn.
