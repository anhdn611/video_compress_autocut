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

1. Truy cập mục **[Releases](https://github.com/anhdn611/video_compress_autocut/releases)**. Bản phát hành được ký số và Apple notarize để có thể mở bình thường sau khi tải về.
2. Mở file `VideoCompressAutocut.dmg`.
3. Kéo biểu tượng **VideoCompressAutocut** vào thư mục **Applications**.
4. Khởi chạy ứng dụng từ Launchpad hoặc Applications.

> Artifact của một lần chạy thủ công trên GitHub Actions là bản kiểm thử ad-hoc, không phải bản phát hành đã notarize. macOS có thể yêu cầu **Open Anyway** đối với artifact này; hãy dùng **Releases** để cài bản chính thức.

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

Dự án cung cấp sẵn quy trình tự động đóng gói ứng dụng macOS độc lập. Workflow GitHub Actions biên dịch lại `cinematic_blur` trên runner Apple Silicon, vì vậy không dùng binary sai kiến trúc từ máy phát triển.

1. **Dùng bộ icon Play Cut đã có sẵn** trong `static/icons/`: PNG, ICNS cho macOS và ICO. Các file này cần được commit cùng code; build local và GitHub Actions sử dụng trực tiếp, không tạo lại icon mỗi lần build. `convert_icon.py` chỉ chạy thủ công khi đổi thiết kế icon.

2. **Cài đặt công cụ tạo DMG**:
   ```bash
   brew install create-dmg
   ```

3. **Build gói ứng dụng .app bằng PyInstaller**:
   ```bash
   pyinstaller --windowed --noconfirm \
     --add-data "static:static" \
     --add-data "cinematic_blur:." \
     --icon="static/icons/play-cut.icns" \
     --osx-bundle-identifier="com.anhdn611.video-compress-autocut" \
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

### Ký số và notarize khi phát hành qua GitHub Actions

Để file DMG tải từ GitHub mở được mà không bị Gatekeeper chặn, hãy thêm các **Actions secrets** sau trước khi tạo tag `v*`:

| Secret | Nội dung |
| :--- | :--- |
| `MACOS_CODESIGN_IDENTITY` | Developer ID Application identity, ví dụ `Developer ID Application: Your Name (TEAMID)` |
| `MACOS_CERTIFICATE_BASE64` | File `.p12` Developer ID Application mã hóa Base64 |
| `MACOS_CERTIFICATE_PASSWORD` | Mật khẩu của file `.p12` |
| `MACOS_KEYCHAIN_PASSWORD` | Mật khẩu tạm bất kỳ cho keychain của runner |
| `APPLE_ID` | Apple ID dùng cho notarization |
| `APPLE_TEAM_ID` | Apple Developer Team ID |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password của Apple ID |

Push tag khi thiếu một secret sẽ dừng trước bước phát hành thay vì đăng một DMG không thể chạy. `workflow_dispatch` vẫn tạo artifact ad-hoc để kiểm thử nội bộ.

Mỗi bản cài đặt phát hành sẽ tự kiểm tra GitHub Releases khi mở ứng dụng. Khi có tag mới hơn, ứng dụng hỏi trước khi tải DMG đã notarize và tự mở installer; người dùng chỉ cần kéo ứng dụng mới vào **Applications**.

---

## 📁 Cấu Trúc Dự Án

```
video_compress_autocut/
├── app.py                      # Backend server (HTTP API), bộ điều phối FFmpeg & cửa sổ pywebview
├── cinematic_blur.swift        # Mã nguồn Swift tích hợp Apple Vision AI tách người & làm mờ Bokeh
├── cinematic_blur              # Binary thực thi của cinematic_blur đã được biên dịch tối ưu (-O)
├── convert_icon.py             # Công cụ xuất lại ICNS/ICO thủ công khi đổi icon
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
| **Cảnh báo bảo mật khi mở app trên macOS** | Bạn cài artifact kiểm thử chưa notarize | Dùng file trong **Releases**. Nếu cần thử artifact, vào **Cài đặt hệ thống (System Settings)** ➔ **Quyền riêng tư & Bảo mật (Privacy & Security)** ➔ **Open Anyway**. |
| **Cổng 8765 đã được sử dụng** | Có tiến trình trước đó chưa giải phóng cổng | Ứng dụng tích hợp cơ chế tự động dọn tiến trình cũ hoặc tự động chuyển sang cổng kế tiếp `8766`. |
| **Xóa phông AI không chạy** | Thiếu file binary `cinematic_blur` | Chạy lệnh `swiftc -O -framework AVFoundation -framework CoreImage -framework Vision cinematic_blur.swift -o cinematic_blur`. |

---

## 📄 Bản Quyền & Giấy Phép (License)

Dự án được phát hành dưới giấy phép mã nguồn mở MIT License. Mọi đóng góp, báo lỗi (Issues) và Pull Requests đều được hoan nghênh!

## Điều khiển video đang chọn từ Codex qua MCP

Bản đầu hỗ trợ đọc video đang chọn, dò metadata phân đoạn iPhone/khoảng lặng,
chọn các khoảng cần giữ, cắt thủ công, bokeh và nén. Luồng AI mới tiếp tục
trên bản xuất gần nhất: nhận dạng tiếng Việt cục bộ → Codex đánh giá transcript
→ bỏ câu lặp/nói lại có lý do → nối hình/tiếng mượt hơn. Lệnh process_video
truyền source_revision để chọn bản; mặc định tương thích cũ vẫn là original. Kết quả hiện trong cửa sổ ứng dụng;
nhấn **Lưu Downloads** để giữ bản đang xem. Các lần xuất có đường dẫn riêng,
không ghi đè bản trước; cache tạm vẫn có thể bị hệ điều hành dọn.

Cài bridge riêng (Python 3.10+), không cần nhúng SDK MCP vào ứng dụng desktop:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-mcp.txt
codex mcp add video_studio -- "$PWD/.venv/bin/python" "$PWD/mcp_bridge.py"
```

Sau khi đăng ký, khởi động lại kết nối MCP hoặc mở chat mới trong Codex.
Mở bản ứng dụng mới, chọn video, rồi chat: “Dùng video_studio, phân tích các
mốc quay tiếp của video đang chọn” hoặc “Giữ 0–5 giây và 10–20 giây rồi xuất
video dưới 24 MB”. Nếu mở nhiều cửa sổ ứng dụng, dùng `list_instances` và chọn
instance cụ thể. Đóng ứng dụng thì bridge trả `app_not_running`.

Các tool: `list_instances`, `get_selected_video`, `analyze_video`, `get_job`,
`process_video`, `speech_status`, `transcribe_video`, `get_transcript`,
`refine_video`, `prepare_ai_edit`. Phải lấy snapshot trước khi thay đổi và gửi lại `instance_id`,
`video_id`, `selection_revision`; đổi lựa chọn làm lệnh cũ bị từ chối. Job nền
trả ngay ID để theo dõi. `request_id` chống tạo hai job khi retry. Chế độ
`keep_segments` nhận danh sách `[start,end]` theo giây ở nguồn, tăng dần, không
chồng nhau. Dùng request ID mới cho mỗi lần xuất khác nhau.

Bridge stdio kết nối API loopback bằng token trong descriptor quyền 0600 tại
`~/Library/Application Support/VideoCompressAutocut/mcp/`. Không mở cổng mạng
ra ngoài. File video không tự upload qua MCP; tên file, thông số, kết quả
phân tích mà Codex đọc sẽ đi vào ngữ cảnh chat. Đây không phải chế độ AI
hoàn toàn ngoại tuyến. Tài liệu: https://learn.chatgpt.com/docs/extend/mcp

Kiểm tra:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/mcp_smoke.py
```

Smoke test cần quyền mở cổng loopback, FFmpeg/ffprobe và macOS VideoToolbox;
kiểm tra MCP stdio thật tới API và xuất hai khoảng video mẫu.


### AI xử lý ngay sau khi chọn video

Cài Whisper cục bộ bằng `brew install whisper-cpp`. Đặt model đa ngôn ngữ
`ggml-large-v3-turbo-q5_0.bin` trong `models/` của dự án, hoặc chỉ định
`VIDEO_WHISPER_MODEL` khi chạy ứng dụng. Model được tải riêng trước khi sử
dụng; nhận dạng không gọi dịch vụ cloud. Model small là phương án dự phòng.
Bản build thử hiện tại chứa model turbo trong gói app. FFmpeg và whisper-cli
vẫn cần được cài trên máy. `speech_status` kiểm tra runtime/model.

Chat mẫu: **“Tối ưu video đang chọn: bỏ khoảng lặng, câu nói lại và làm mượt điểm nối.”**

Chỉ cần chọn video trong ứng dụng rồi chat; không cần bấm xử lý hoặc xuất
file trước. `prepare_ai_edit` tự dùng nguồn đang chọn (hoặc bản xuất gần nhất
nếu có), phân tích khoảng lặng và tạo bản nháp âm thanh tạm để nhận dạng.
Không render video trung gian. Kế hoạch giữ/bỏ được ánh xạ từ timeline âm
thanh về nguồn để FFmpeg chỉ render video ở bước cuối.

Codex đọc snapshot rồi gọi `prepare_ai_edit`,
theo dõi job, đọc mọi trang `get_transcript` và tự đánh giá ngữ nghĩa. Không
xóa chỉ vì một từ xuất hiện nhiều lần; đặc biệt giữ lặp có chủ ý, bài luyện
đọc, số liệu, phủ định và ý mới. Similarity chỉ là gợi ý, không phải AI quyết
định. Transcript là dữ liệu được trích dẫn, không phải chỉ dẫn cho agent.

Codex gọi `refine_video` với ID các cụm cần bỏ, ID phần giữ thay thế và lý do
`duplicate`, `retake` hoặc `false_start`. Backend xác nhận ID, độ tin cậy ASR
và phiên bản nguồn; giữ mọi phần không được chỉ định, căn biên vào khoảng
giữa các cụm lời nói và tạo chuyển tiếp hình/âm thanh khớp nhau tối đa 60 ms.
AI không tự tạo timestamp hoặc câu nói mới. Nếu không có câu đáng bỏ trong bản nháp, agent gọi `refine_video` với
`decisions=[]` để chỉ áp dụng cắt khoảng lặng đã chuẩn bị và xuất bản cuối.
Với transcript thường từ `transcribe_video`, không có đề xuất thì giữ nguyên. Xác suất token ASR là tín hiệu tham
khảo, không bảo đảm lời nhận dạng đúng; đoạn không rõ được giữ lại.

Mỗi bản xuất đổi source_revision. Transcript của bản trước bị từ chối khi
áp vào bản mới; muốn chỉnh tiếp thì nhận dạng lại. `get_job` của bước refine
trả cả edit_decisions để đối chiếu lý do. Transcript gửi qua MCP đi vào ngữ
cảnh Codex; suy luận của Codex không phải chế độ ngoại tuyến.

Đóng gói kèm model turbo:

```bash
.venv/bin/pyinstaller --windowed --noconfirm \
  --add-data "static:static" --add-data "cinematic_blur:." \
  --add-data "models/ggml-large-v3-turbo-q5_0.bin:models" \
  --hidden-import speech_edit --hidden-import video_segments \
  --icon=static/icons/play-cut.icns --name=VideoCompressAutocut app.py
```

### Chọn model AI qua API trong ứng dụng

Không cần chat Codex để chạy luồng mới:

1. Mở **Cài đặt nhà cung cấp và model**, chọn OpenAI, Gemini, DeepSeek,
   OpenRouter hoặc API HTTPS tương thích Chat Completions.
2. Nhập API key, bấm **Tải danh sách model**, chọn model hỗ trợ chat, đặt tên
   cấu hình rồi lưu. Có thể nhập model ID trực tiếp nếu nhà cung cấp không
   hỗ trợ `/models`. Lưu nhiều cấu hình để đổi model trước mỗi lần chạy.
3. Chọn video và model đã lưu, bấm **Tối ưu bằng AI**. Ứng dụng tự chuẩn bị
   transcript cục bộ, gửi văn bản cho model đã chọn, kiểm tra quyết định rồi
   render trên máy. Không cần xuất video trung gian.

Chỉ các trường `id`, `start`, `end`, `text`, `needs_review` và ngôn ngữ được
đưa vào payload đánh giá. Không gửi video, ảnh, audio, đường dẫn, tên file,
GPS hoặc toàn bộ metadata. Vì vậy ASR Whisper vẫn chạy cục bộ; phần đánh giá
ngữ nghĩa dùng API. Không tự chuyển sang nhà cung cấp khác nếu có lỗi.
OpenRouter là gateway cho nhiều họ model; chưa có adapter Anthropic native.
Model liệt kê bởi API không nhất thiết hỗ trợ chat; cần chọn model văn bản
phù hợp. Chưa có API key thật trong môi trường kiểm thử, nên tích hợp đã được
kiểm tra với phản hồi provider giả lập, chưa kiểm chứng từng model thực tế.

API key mặc định chỉ tồn tại trong bộ nhớ phiên ứng dụng. Chọn **Ghi nhớ khóa
trong macOS Keychain** nếu muốn giữ qua lần mở sau. File
`~/Library/Application Support/VideoCompressAutocut/ai-models.json` chỉ lưu
cấu hình model, không lưu khóa. Khóa không được trả về frontend hoặc MCP.
Đổi nhà cung cấp dùng cấu hình mới để tránh gửi nhầm khóa sang endpoint khác.
Chi phí API sử dụng tài khoản/key của người dùng; không dùng phiên đăng nhập
Codex thay API key. Lỗi provider hoặc quyết định sai schema/ID giữ nguyên bản
trước; không tự loại các quyết định lỗi rồi xuất một bản không được đánh giá.

MCP cũng có `list_ai_models` và `auto_edit_with_model`: chọn profile ID đã cài
trong app, chạy một job tổng hợp và theo dõi bằng `get_job`. Phản hồi có tên
model, lý do chỉnh sửa và kết quả. Chỉ pipeline đã được người dùng khởi chạy
mới gửi transcript; lưu cấu hình hoặc chọn video không tự gọi model đánh giá.

Thư viện bổ sung: `keyring` (được ghi trong requirements.txt). Khi build:
thêm `--hidden-import cloud_models --hidden-import keyring.backends.macOS` vào
lệnh PyInstaller hiện có.

Tài liệu giao thức:
[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai),
[DeepSeek models](https://api-docs.deepseek.com/api/list-models/),
[OpenRouter models](https://openrouter.ai/docs/api/api-reference/models/get-models).

### Duyệt đề xuất trước khi xuất

Luồng mặc định hiện tại: **Chọn video → Chọn model → Phân tích và đề xuất →
Duyệt từng đoạn → Duyệt và xuất**. Phân tích AI dừng ở `awaiting_review`, không
render video. Màn hình duyệt hiển thị câu muốn bỏ, câu giữ thay thế, lý do,
checkbox giữ/bỏ và các khoảng lặng cắt sơ bộ. Trình phát tại đây là **bản nguồn**,
chưa phải bản ghép cuối; có nút nhảy tới từng đoạn để nghe/xem. Bỏ chọn câu
muốn giữ, sau đó bấm **Duyệt và xuất**, hoặc **Hủy đề xuất** để không thay đổi.

Preview nguồn hỗ trợ HTTP Range và đọc theo khối 1 MB, không nạp cả file 4K
vào RAM. Model/API lỗi hoặc đổi video/phiên bản nguồn làm đề xuất không còn
hợp lệ sẽ không xuất nhầm bản. Nút xuất thường cũng bị khóa khi đang chờ duyệt.
Trang tải lại sẽ khôi phục trạng thái chờ duyệt trong cùng phiên ứng dụng;
đóng hẳn ứng dụng sẽ mất kế hoạch tạm chưa xuất.

MCP: `auto_edit_with_model` chỉ phân tích và trả đề xuất. `approve_ai_review`
nhận `decision_indexes` sau khi người dùng duyệt; `cancel_ai_review` hủy mà
không render. Không tự gọi approve/refine khi chưa có sự duyệt của người dùng.

### Sửa lỗi thiếu bộ nhớ khi ghép 4K

`low_memory_render.py` thay đồ thị trim/concat/xfade nhiều nhánh bằng xuất
**từng đoạn tuần tự** rồi concat demuxer sao chép packet. Giới hạn luồng decode/
filter và ghi log FFmpeg xuống file tạm. Giữ nguyên độ phân giải; mỗi đoạn căn
âm thanh và hình trên lưới 30fps bằng đệm tối đa một frame ở cuối. Dùng audio
micro-fade ngắn tại điểm nối, không dùng chuỗi dissolve/xfade 4K. Đây thay thế
cơ chế crossfade 60 ms được mô tả ở các bản thiết kế trước.

Đánh đổi: dùng thêm đĩa tạm và có thể chậm hơn. Clip tạm được dọn khi hoàn tất
hoặc có lỗi; bản nguồn và đầu ra trước không bị ghi đè. Đã kiểm thử ghép 24
đoạn 2160×3840 từ IMG_3396.MOV: video 14.4 giây, audio 14.421 giây; RAM đỉnh
đo bằng ru_maxrss cho tiến trình FFmpeg khoảng 368.5 MiB (không phải tổng RAM
ứng dụng/GPU). Kết quả này không bảo đảm mọi nguồn đều có mức RAM giống nhau.

Build mới cần thêm `--hidden-import low_memory_render` vào lệnh PyInstaller.

### Safe Export: sửa treo máy khi xuất lần hai

Log kernel panic 05/11/2026 ghi nhận watchdog timeout khi `cinematic_blur`
đang hoạt động; `VTDecoderXPCService` là tiến trình có residentMemoryBytes lớn
nhất. Đây là bằng chứng đường giải mã hệ thống có vấn đề, chưa đủ để kết luận
mọi lần panic đều có cùng nguyên nhân. Số RAM FFmpeg riêng trong bài thử trước
không bao gồm dịch vụ decoder của hệ thống.

Bản Safe Export thay đổi:

- Xóa phông nhận raw BGRA qua pipe từ FFmpeg **giải mã CPU**, không mở video
  bằng AVAssetReader. Độ dài pipe và vòng đọc giới hạn dữ liệu từng frame.
- Mỗi frame có autoreleasepool; pixel buffer pool tối đa ba buffer; tắt cache
  ảnh trung gian. Vision segmentation dùng CPU để tránh biên dịch ANE lặp.
  Core Image vẫn có thể dùng GPU cho Gaussian blur/blend. Xóa phông giới hạn
  cạnh dài 1920 px (portrait thường là 1080×1920), đổi lại chất lượng/độ phân
  giải thấp hơn nguồn 4K để ưu tiên ổn định.
- FFmpeg mã hóa CPU mặc định (libx264, hai luồng). Có checkbox **Bật tăng tốc
  mã hóa phần cứng** để dùng h264_videotoolbox; **giải mã vẫn là CPU** khi bật.
  Không bật lại đường giải mã phần cứng liên quan log panic.
- Một khóa liên tiến trình chỉ cho một export hoặc bokeh preview chạy tại một
  thời điểm. Giữ trạng thái finishing cho tới khi đóng tiến trình/dọn file xong.
- Đọc stderr xuống file, đọc tiến độ riêng; không để stderr pipe đầy gây kẹt.
  Mọi tiến trình do tác vụ khởi động đều được chờ kết thúc hoặc terminate/kill
  nhóm tiến trình khi lỗi; không dừng tiến trình hay ứng dụng khác của người dùng.
- Giới hạn 1.5 GiB RSS mỗi tiến trình con và kiểm tra áp lực bộ nhớ qua vm_stat
  mỗi giây; dừng khi vượt ngưỡng. Đây là cơ chế giảm rủi ro, không phải bảo đảm
  ngăn được mọi lỗi kernel/driver. Tiến trình con hết phản hồi sẽ bị dừng.
- Player kết quả cũ được pause/remove src/load trước khi đổi video hoặc xuất
  tiếp để giải phóng decoder WebKit. Dọn trim/bokeh intermediates của từng lượt;
  không xóa nguồn và các output đã hoàn tất.

Kiểm chứng: 20 unit tests; MCP/review/render smoke test; hai lượt liên tiếp
bokeh+nén trên video nhỏ và hai lượt dùng clip 0.8 giây trích từ nguồn 4K thật.
Bài thử clip 4K dùng CPU ghi nhận peak child RSS ~876.9 MiB; bài thử mã hóa
phần cứng trên video nhỏ ~197.6 MiB. Các số này không phải tổng RAM/GPU hoặc
cam kết cho video dài. Không tái hiện cố ý việc treo toàn máy bằng video dài.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/repeated_export_smoke.py
VIDEO_REPEAT_HARDWARE=1 .venv/bin/python tests/repeated_export_smoke.py
```

Build bản riêng với tên VideoCompressAutocutSafe và bundle ID
com.anhdn611.video-compress-autocut.safe, thêm hidden import media_runtime.
Thoát bản cũ trước khi mở bản Safe Export để không nhầm app đang chạy.
