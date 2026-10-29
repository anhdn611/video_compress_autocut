# 🎬 Video Studio Pro (Video Compress & Smart Autocut)

[![Build Desktop Executables](https://github.com/anhdn611/video_compress_autocut/actions/workflows/build-desktop.yml/badge.svg)](https://github.com/anhdn611/video_compress_autocut/actions/workflows/build-desktop.yml)
[![Platform](https://img.shields.io/badge/Platform-macOS%20(Apple%20Silicon%20%2F%20Intel)-black?logo=apple)](https://github.com/anhdn611/video_compress_autocut)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Hardware Acceleration](https://img.shields.io/badge/Hardware%20Accel-Apple%20VideoToolbox-orange)](https://developer.apple.com/)
[![AI Engine](https://img.shields.io/badge/AI%20Segmentation-Apple%20Vision-purple)](https://developer.apple.com/documentation/vision)

**Video Studio Pro** là ứng dụng Desktop mạnh mẽ, hiện đại dành cho macOS, giúp bạn xử lý video toàn diện: **Tự động lọc khoảng im lặng (Dead Air)**, **Xóa phông chân dung AI (Cinematic Bokeh Portrait)** và **Nén video siêu tốc với phần cứng Apple Silicon** chuẩn dung lượng mục tiêu để gửi qua Zalo (< 20MB), Discord, Telegram hoặc Email.

---

## ✨ Tính Năng Nổi Bật

### ✂️ 1. Cắt & Tối Ưu Thời Lượng Thông Minh (Smart Trim)
- **Lọc bỏ khoảng lặng (Jump-Cut phong cách TikTok/Reels)**:
  - Tự động dò tìm các khoảng im lặng, ngập ngừng suy nghĩ (Dead Air) khi nói và cắt bỏ chính xác.
  - Tích hợp thuật toán **đệm an toàn 280ms** (giữ trọn hơi thở đầu câu và âm vang cuối câu) cùng **micro-fade 30ms** khử triệt để tiếng lách tách âm thanh.
  - Chuẩn hóa tốc độ khung hình (30fps cố định), đảm bảo video ghép lại mượt mà, hoàn toàn không bị giật hay khựng hình.
  - 3 profile mượt mà thiết lập sẵn: *Siêu mượt (> 1.4s)*, *Cân bằng (> 1.1s)*, *Dồn dập (> 0.8s)*.
- **Tự động cắt bỏ đoạn đầu & đuôi thừa (Intro/Outro)**:
  - Tự động nhận diện mốc bắt đầu nói đầu tiên và mốc kết thúc nói cuối cùng, cắt bỏ thời gian chờ lúc bấm bật/tắt camera.
- **Cắt mốc thủ công (Manual Trim)**:
  - Tự do nhập mốc thời gian bắt đầu và kết thúc (theo giây hoặc định dạng `mm:ss`).

---

### 🎭 2. Xóa Phông Chân Dung AI (Cinematic Bokeh Portrait)
- **Nhận diện người bằng Apple Vision AI & Apple Neural Engine**:
  - Ứng dụng mô hình phân tách người sâu (`VNGeneratePersonSegmentationRequest`) của Apple để nhận diện chủ thể sắc nét theo thời gian thực.
  - Làm mờ hậu cảnh (Depth of Field) tự nhiên như ống kính máy ảnh cơ chuyên nghiệp.
  - Các mốc khẩu độ mô phỏng: *🌸 Nhẹ nhàng (f/2.8 - 15px)*, *📷 Chuẩn chân dung (f/1.8 - 25px)*, *🌟 Xóa phông sâu (f/1.2 - 42px)* hoặc tùy chỉnh tự do theo bán kính làm mờ (px).
- **Xem trước tức thì (Preview Bokeh)**:
  - Tạo ảnh xem trước 1 khung hình với hiệu ứng xóa phông chỉ trong 1-2 giây trước khi xuất toàn bộ video.
- **Bảo mật tuyệt đối (100% Offline)**:
  - Toàn bộ quá trình xử lý AI diễn ra hoàn toàn trên thiết bị của bạn, không gửi dữ liệu ra máy chủ bên ngoài.

---

### ⚡ 3. Nén Dung Lượng Chuẩn Mục Tiêu (Apple Silicon VideoToolbox)
- **Tối ưu chuẩn dung lượng chia sẻ**:
  - Cài đặt sẵn các mốc dung lượng phổ biến: **Zalo / Chuẩn (18 MB)** (đảm bảo luôn dưới giới hạn 20MB của Zalo), **Discord Free (24 MB)**, **Telegram (20 MB)**, **Siêu nhẹ (10 MB)** hoặc kéo thanh trượt từ 5 MB đến 50 MB.
- **Tăng tốc phần cứng siêu tốc**:
  - Tận dụng bộ mã hóa phần cứng **Apple Silicon VideoToolbox** (`h264_videotoolbox`), tốc độ nén video đạt từ **20x đến 35x** so với thời lượng thực tế.
  - Thuật toán tính toán bitrate thông minh và cơ chế **Auto-Retry** tự động tái nén nếu file xuất ra vượt quá ngưỡng mong muốn.

---

### 🎛️ 4. Bộ Xử Lý Đa Năng Linh Hoạt (Studio Pipeline)
- Bật/tắt độc lập hoặc kết hợp linh hoạt cả 3 module theo nhu cầu:
  - *Chỉ cắt khoảng lặng*
  - *Chỉ xóa phông AI*
  - *Chỉ nén video*
  - *Hoặc kết hợp toàn bộ: Cắt khoảng lặng ➔ Xóa phông Bokeh ➔ Nén dung lượng mục tiêu*.

---

### 🖥️ 5. Trải Nghiệm Ứng Dụng Desktop Native Cao Cấp
- Chạy dưới dạng ứng dụng độc lập trên macOS (sử dụng thư viện `pywebview`, không cần mở trình duyệt web bên ngoài).
- Giao diện **Dark Mode Glassmorphism** hiện đại, mượt mà.
- Hiển thị trực quan: Timeline khoảng lặng/tiếng nói, thông số video gốc và kết quả sau xử lý.
- Tích hợp trình phát video xem lại kết quả ngay trong app.
- Tính năng tiện lợi: **Tải video về máy** hoặc **1-click Lưu trực tiếp vào thư mục Downloads và tự động mở Finder (`open -R`)**.

---

## 🛠️ Yêu Cầu Hệ Thống

1. **Hệ điều hành**: macOS 12.0 (Monterey) trở lên (Tối ưu nhất cho các dòng chip Apple Silicon M1, M2, M3, M4).
2. **FFmpeg**: Cần có `ffmpeg` và `ffprobe` trong máy:
   ```bash
   brew install ffmpeg
   ```
3. **Python**: Phiên bản 3.9 trở lên (nếu chạy từ mã nguồn).
4. **Xcode Command Line Tools** (để biên dịch engine Swift AI nếu cần):
   ```bash
   xcode-select --install
   ```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### Cách 1: Tải Bản Cài Đặt Sẵn (.dmg) (Khuyên Dùng)

1. Truy cập mục **[Releases](https://github.com/anhdn611/video_compress_autocut/releases)** hoặc tải artifact mới nhất từ **GitHub Actions**.
2. Mở file `VideoCompressAutocut.dmg`.
3. Kéo biểu tượng **VideoCompressAutocut** vào thư mục **Applications**.
4. Khởi chạy ứng dụng từ Launchpad hoặc Applications.

> **Lưu ý**: Nếu macOS hiển thị cảnh báo ứng dụng chưa được chứng thực bởi Apple (Gatekeeper), bạn hãy vào **System Settings (Cài đặt hệ thống)** ➔ **Privacy & Security (Quyền riêng tư & Bảo mật)** ➔ cuộn xuống và nhấn **Open Anyway (Vẫn mở)**.

---

### Cách 2: Chạy Từ Mã Nguồn (Dành Cho Nhà Phát Triển)

1. **Clone repository về máy**:
   ```bash
   git clone https://github.com/anhdn611/video_compress_autocut.git
   cd video_compress_autocut
   ```

2. **Cài đặt FFmpeg**:
   ```bash
   brew install ffmpeg
   ```

3. **Tạo môi trường ảo và cài đặt thư viện**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Biên dịch engine AI Xóa phông (nếu chưa có binary `cinematic_blur`)**:
   ```bash
   swiftc -O -framework AVFoundation -framework CoreImage -framework Vision cinematic_blur.swift -o cinematic_blur
   ```

5. **Khởi chạy ứng dụng**:
   ```bash
   python3 app.py
   ```

---

## 📦 Hướng Dẫn Đóng Gói Ứng Dụng Desktop (.app & .dmg)

Dự án cung cấp sẵn quy trình tự động đóng gói ứng dụng macOS độc lập:

1. **Tạo bộ icon ứng dụng (.ico & .icns)**:
   ```bash
   python3 convert_icon.py
   ```

2. **Cài đặt công cụ tạo DMG**:
   ```bash
   brew install create-dmg
   ```

3. **Build gói ứng dụng .app bằng PyInstaller**:
   ```bash
   pyinstaller --windowed --noconfirm \
     --add-data "static:static" \
     --add-data "cinematic_blur:." \
     --icon="favicon_io/android-chrome-512x512.png" \
     --name="VideoCompressAutocut" \
     app.py
   ```

4. **Tạo file cài đặt Disk Image (.dmg)**:
   ```bash
   mkdir -p dmg_out
   create-dmg \
     --volname "Video Compress Autocut" \
     --window-pos 200 120 \
     --window-size 600 400 \
     --icon-size 100 \
     --app-drop-link 420 185 \
     "dmg_out/VideoCompressAutocut.dmg" \
     "dist/VideoCompressAutocut.app"
   ```
   File cài đặt hoàn chỉnh sẽ nằm tại: `dmg_out/VideoCompressAutocut.dmg`.

---

## 📁 Cấu Trúc Dự Án

```
video_compress_autocut/
├── app.py                      # Backend server (HTTP API), bộ điều phối FFmpeg & cửa sổ pywebview
├── cinematic_blur.swift        # Mã nguồn Swift tích hợp Apple Vision AI tách người & làm mờ Bokeh
├── cinematic_blur              # Binary thực thi của cinematic_blur đã được biên dịch tối ưu (-O)
├── convert_icon.py             # Script tự động tạo icon.ico và icon.icns từ favicon PNG
├── requirements.txt            # Danh sách thư viện Python phụ thuộc
├── favicon_io/                 # Bộ tài nguyên hình ảnh logo và favicon
├── static/                     # Giao diện người dùng Webview
│   ├── index.html              # Cấu trúc giao diện Dark Mode Glassmorphism
│   ├── style.css               # Bộ styles responsive, animation và layout hiện đại
│   └── app.js                 # Xử lý logic giao diện, gọi API, upload chunked, audio/video preview
├── .github/workflows/          # Quy trình CI/CD GitHub Actions
│   └── build-desktop.yml       # Tự động build .app và đóng gói .dmg trên môi trường macos-latest
└── README.md                   # Tài liệu hướng dẫn sử dụng dự án
```

---

## 💡 Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Sự cố | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Không tìm thấy FFmpeg** | Máy chưa cài đặt công cụ dòng lệnh `ffmpeg` | Chạy lệnh `brew install ffmpeg` trên Terminal. Ứng dụng đã tự động thêm `/opt/homebrew/bin` và `/usr/local/bin` vào đường dẫn hệ thống. |
| **Cảnh báo bảo mật khi mở app trên macOS** | macOS Gatekeeper chặn ứng dụng tải từ bên ngoài chưa ký số | Vào **Cài đặt hệ thống (System Settings)** ➔ **Quyền riêng tư & Bảo mật (Privacy & Security)** ➔ Nhấn **Open Anyway (Vẫn mở)**. |
| **Cổng 8765 đã được sử dụng** | Có tiến trình trước đó chưa giải phóng cổng | Ứng dụng tích hợp cơ chế tự động dọn tiến trình cũ hoặc tự động chuyển sang cổng kế tiếp `8766`. |
| **Xóa phông AI không chạy** | Thiếu file binary `cinematic_blur` | Chạy lệnh `swiftc -O -framework AVFoundation -framework CoreImage -framework Vision cinematic_blur.swift -o cinematic_blur`. |

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phát hành dưới giấy phép mã nguồn mở MIT License. Mọi đóng góp, báo lỗi (Issues) và Pull Requests đều được hoan nghênh!
