# Thiết kế AI cắt/ghép chạy cục bộ

Trạng thái: đã triển khai MCP điều khiển video, đọc metadata phân đoạn và
xuất theo khoảng giữ; ASR whisper.cpp và vòng Codex đánh giá transcript/refine đã triển khai;
LLM Ollama độc lập, hủy job và UI hoàn tác kế hoạch vẫn ở bước thiết kế. Mục tiêu đầu tiên là
video nói tiếng Việt, giữ thứ tự nội dung và cho người dùng duyệt đề xuất.

## Luồng xử lý

Video gốc → đọc metadata phân đoạn → tách âm thanh → nhận dạng lời nói →
đề xuất chỉnh sửa → kiểm tra kế hoạch → xem trước → xuất bằng FFmpeg.

1. Đọc metadata ngay khi nhập file, trước mọi lần chuyển mã. Tìm đúng track
   `com.apple.quicktime.segment-identifier` trong cấu trúc MOV, không cố định
   số track. Đọc thời gian và mã của từng sample; chỉ tạo ranh giới khi mã đổi.
   Nếu thiếu hoặc metadata lỗi, báo không có dấu mốc và tiếp tục bằng lời nói/
   khoảng lặng, không suy diễn rằng không có pause.
2. Chọn audio AAC chính theo stream index từ bước probe; không trộn nhầm
   track Apple Positional Audio. Xuất WAV mono 16 kHz để nhận dạng; bản xuất
   cuối vẫn dùng âm thanh nguồn.
3. Dùng whisper.cpp với model đa ngôn ngữ, ngôn ngữ `vi`, timestamp từ/câu.
   Chọn backend này cho bản đầu vì ứng dụng hỗ trợ cả Mac Intel và Apple
   Silicon. MLX Whisper là adapter tùy chọn cho Apple Silicon sau này.
   Benchmark model small và medium trên video mẫu trước khi chọn mặc định.
   Timestamp từ là ước lượng, phải kiểm tra với tín hiệu âm thanh khi cắt.
4. Chia câu từ transcript và khoảng lặng; gắn mỗi câu với đoạn nguồn, thời
   gian tuyệt đối và token ID. Khi nhận dạng từng khối cần overlap, khử trùng
   phần overlap và cộng offset; luôn giữ ngữ cảnh hai phía ranh giới quay tiếp.
5. Một bộ điều phối Python gọi model ngôn ngữ cục bộ qua Ollama để so sánh
   các câu gần nhau, đề xuất câu lặp/câu nói lại/câu bỏ dở. Chỉ gửi transcript
   và ID cho model; không cần đưa toàn video 4K vào model. Không mặc định
   lần nói sau tốt hơn và không loại nội dung bổ sung chỉ vì giống câu trước.
6. Model trả JSON theo schema gồm ID câu/token, hành động đề xuất, ID đoạn
   thay thế nếu có, và lý do. Backend ánh xạ ID sang thời gian; model không
   tự tạo timestamp, đường dẫn hoặc lệnh thực thi. Transcript là dữ liệu,
   không phải chỉ dẫn cho bộ điều phối. Giới hạn số lượt và thời gian suy luận.
7. Bộ kiểm tra xác nhận ID tồn tại, thời gian hữu hạn và trong nguồn, đoạn giữ
   tăng dần/không chồng nhau, không xuất rỗng. Lỗi model/schema/thiếu model
   giữ nguyên nội dung liên quan và trả thông báo; không tự xóa để chữa lỗi.
8. Tinh chỉnh điểm cắt theo khoảng lặng gần biên câu, có đệm giọng nói và
   micro-fade âm thanh. Không áp dụng pad xuyên ranh giới nguồn một cách mù
   quáng. Đề xuất bỏ nội dung luôn cần duyệt ở bản đầu; điểm số tự nhận của
   model không được coi là xác suất đúng đã hiệu chuẩn.
9. Render proxy để xem trước; xuất cuối một lần từ nguồn theo danh sách đoạn
   đã duyệt. Thực hiện cắt trước bokeh và nén để giảm công việc thừa. Không
   cần render lại video sau mỗi sửa đổi transcript.

## Kết quả kiểm tra file mẫu

`IMG_3396.MOV`: dài 212 giây, có 23 sample với 23 UUID khác nhau trong track
segment-identifier (stream index 7 ở riêng file này), tương ứng 22 ranh giới.
Các mốc đầu: 3.635, 10.736667, 17.538333, 22.806667, 36.143333 giây.
Đây là bằng chứng phân đoạn; liên hệ với pause/resume vẫn là suy luận cần
đối chiếu thao tác quay, không coi mọi file iPhone đều có cấu trúc này.
Bản MP4 đã xử lý không còn track này. Không thể suy ra độ dài khoảng pause.

## Tích hợp vào ứng dụng

- Giữ `app.py` làm lớp HTTP/điều phối, tái sử dụng TASKS và TASKS_LOCK.
- Tách `local_ai/metadata.py`, `transcribe.py`, `planner.py`, `validate.py`,
  `render.py`; gọi công cụ bằng argv, không shell và không dùng lệnh model sinh.
- API đề xuất: POST `/api/ai/analyze` tạo job nền; GET `/api/ai/status?id=…`
  lấy tiến độ; GET `/api/ai/plan?id=…` lấy transcript/đề xuất; POST
  `/api/ai/plan` lưu lựa chọn đã duyệt; POST `/api/ai/preview` tạo proxy.
  `/api/process` nhận plan ID đã kiểm tra và phiên bản plan để xuất.
- Mỗi project lưu fingerprint nguồn, phiên bản engine/model, transcript,
  metadata và edit plan. Đổi nguồn/model/tham số liên quan phải vô hiệu cache.
- Lưu kế hoạch mới theo phiên bản để hoàn tác. Không sửa hoặc xóa file gốc.
- Chạy một job AI nặng tại một thời điểm; nạp ASR rồi giải phóng trước khi
  nạp LLM. Có hủy tác vụ, timeout, giới hạn output, báo thiếu RAM/dung lượng.
  Tốc độ và cấu hình model phải đo trên máy đích; chưa đưa cam kết thời gian.

## Giao diện

Chế độ “AI cắt thông minh · Cục bộ”: kiểm tra model → phân tích → danh sách
đề xuất với thời gian, câu gốc/câu giữ và lý do → nghe/xem điểm nối →
chọn giữ hoặc bỏ → xuất. Mặc định giữ nguyên thứ tự, không viết lại lời nói.
Lỗi hoặc câu nhận dạng không rõ được đánh dấu để duyệt thay vì tự xóa.

## Dữ liệu và hoạt động ngoại tuyến

- Tải model là bước cài đặt riêng, cần mạng và hiển thị kích thước/nguồn trước
  khi tải. Khi đã có model, luồng phân tích và xuất hoạt động không có internet.
- Chỉ cho phép runtime Ollama trên loopback, chỉ model đã cài; bật chế độ
  local-only được runtime hỗ trợ và kiểm tra không gọi model cloud. Không tự
  tải model, fallback cloud, gửi telemetry hoặc ghi transcript vào log lỗi.
- Chế độ ngoại tuyến cũng tắt kiểm tra cập nhật GitHub tự động hiện có trong
  ứng dụng. Chỉ bật lại khi người dùng chủ động chọn kiểm tra cập nhật.
- Cache transcript nằm cục bộ, có nút xóa dữ liệu phân tích và quy tắc dọn WAV/
  proxy tạm khi hủy hoặc xóa project. Các log chia sẻ không chứa GPS nguồn.

## Thứ tự triển khai và kiểm chứng

1. Metadata + danh sách ranh giới + lưu sidecar trước chuyển mã. Kiểm chứng
   23 phân đoạn của file mẫu, file không metadata và track index thay đổi.
2. ASR tiếng Việt + transcript chỉnh sửa được + xem trước. Đối chiếu thủ công
   câu/timestamp, tên riêng, số, lời nói nhỏ và nhạc nền trên tập mẫu.
3. LLM đề xuất câu lặp/nói lại + validator + duyệt từng đề xuất. Đo tỷ lệ đề
   xuất bị từ chối, bỏ nhầm nội dung và lỗi cắt mất đầu/cuối câu; không chỉ
   đánh giá số giây rút ngắn. Giữ nguyên số, phủ định và thông tin mới.
4. Nối với xuất/bokeh/nén. Kiểm tra đồng bộ hình-tiếng, biên nguồn, hoàn tác,
   hủy/khởi động lại và chạy khi ngắt mạng. So sánh với chế độ cắt im lặng cũ.

## Tài liệu kỹ thuật

- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- MLX Whisper: https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md
- Ollama structured outputs: https://ollama.com/blog/structured-outputs

## Điều khiển từ chat Codex qua MCP

Chế độ bổ sung: Codex là MCP client; ứng dụng video cung cấp MCP server.
Luồng: chat Codex → MCP bridge stdio → API loopback ứng dụng → job xử lý
→ cập nhật giao diện và kết quả cho Codex. Không cần nhúng chat vào pywebview.
Bridge stdio bản đầu đã triển khai trong `mcp_bridge.py`, kết nối backend
qua `video_mcp.py`. Đã đăng ký server `video_studio` trên máy phát triển.

Khác chế độ Ollama ngoại tuyến: FFmpeg/ASR/file nguồn vẫn ở máy, nhưng dữ
liệu MCP trả về cho Codex (transcript, tên file, trạng thái, ảnh nếu yêu cầu)
đi vào ngữ cảnh chat. Không gọi chế độ này là suy luận AI hoàn toàn cục bộ.
Chỉ trả dữ liệu cần thiết, không mặc định trả GPS, toàn bộ media hoặc đường
dẫn tuyệt đối. Có thể cung cấp chế độ chỉ metadata không transcript.

### Đồng bộ video đang chọn

Hiện `currentTask` ở frontend; backend chưa có hợp đồng selected-video cho
MCP. Frontend phải đồng bộ khi upload/chọn/reset sang backend, bao gồm
task ID và selection revision. Backend giữ trạng thái dưới lock và trả
snapshot gồm app instance ID, video ID, selection revision, plan revision,
tên hiển thị, thời lượng và trạng thái job.

Codex gọi get_selected_video trước thao tác. Các lệnh thay đổi phải gửi lại
video ID và revision đã đọc. Nếu người dùng đổi video hoặc sửa plan giữa
hai lần gọi, backend trả stale_selection/stale_plan để đọc lại; tuyệt đối
không tự áp lệnh cũ vào video mới. Nếu có nhiều app instance, phải chỉ định
instance; nếu chưa chọn video, trả no_selection thay vì chọn file gần nhất.

### Bộ công cụ MCP dự kiến

| Tool | Vai trò |
| --- | --- |
| get_selected_video | Lấy snapshot video đang chọn |
| analyze_video | Tạo job đọc metadata/khoảng lặng/ASR theo tùy chọn |
| get_job | Đọc tiến độ, lỗi và kết quả; có thể hủy qua cancel_job |
| get_transcript | Lấy từng phần transcript có ID và timestamp |
| get_edit_plan | Lấy danh sách đoạn và phiên bản kế hoạch hiện tại |
| propose_edit | Đề xuất keep/remove theo ID câu hoặc đoạn nguồn |
| preview_edit | Tạo proxy để ứng dụng phát điểm nối |
| apply_edit_plan | Áp kế hoạch đã kiểm tra vào project, có hoàn tác |
| export_video | Tạo file mới từ phiên bản kế hoạch cụ thể |

Chat “bỏ câu lặp trong video đang chọn” sẽ lấy snapshot → chạy phân tích nếu
chưa có → đọc transcript → tạo đề xuất → kiểm tra plan → xem trước. Chat
“xuất bản này dưới 24 MB” sẽ dùng plan revision cụ thể và trả job ID ngay,
không giữ một MCP call chờ toàn bộ thời gian render. Mỗi yêu cầu thay đổi có
request ID để retry không tạo hai job. Giao diện có nút hoàn tác và hiển thị
cùng job/plan với chat.

### Vận hành bridge

Ưu tiên MCP stdio do Codex khởi động, bridge tìm đúng app qua descriptor
cục bộ chứa port/instance ID/token. Không ghi token vào repository; bảo vệ
descriptor theo quyền người dùng. App hiện chọn port động nên không hardcode
port. Backend chỉ nghe loopback, xác thực bridge và kiểm tra Origin cho API
giao diện; giới hạn công cụ theo project/task đang có, không mở shell tùy ý.
Bridge không import `app.py` để tránh tạo app/server thứ hai và trạng thái
TASKS độc lập. Khi app đóng, tool trả app_not_running, không tự mở file khác.

Cài MCP vào Codex là bước sau khi có bridge chạy được và đã kiểm chứng
initialize/tools/list/tools/call, đổi selection giữa hai lần gọi, hủy job,
retry và xuất đúng video. Bản đầu đã kiểm chứng stdio và xuất video thật; đã đăng ký cấu hình Codex
cho máy phát triển. Hủy job và UI duyệt/hoàn tác plan chưa triển khai. Transcript và refine đã
triển khai qua MCP, ràng buộc với phiên bản bản cắt đang xem.
Danh sách tool thực tế và hướng dẫn sử dụng nằm trong README.md.

Tài liệu kết nối: https://learn.chatgpt.com/docs/extend/mcp


## Cập nhật trải nghiệm: chọn video rồi chat

Luồng mặc định mới: get_selected_video → prepare_ai_edit → get_job →
get_transcript → Codex đánh giá → refine_video → get_job. Không yêu cầu người
dùng chạy cắt hoặc xuất trước. prepare_ai_edit chỉ tạo audio draft tạm bằng
các khoảng giữ sau phân tích im lặng, rồi nhận dạng; chưa render video.
Transcript gắn với nguồn hiện tại, thời gian trong draft và bản đồ source
segments. Bước refine chuyển các khoảng giữ ngược về nguồn để render một lần.
Nếu không có câu đáng xóa, decisions=[] vẫn xuất với các khoảng lặng đã bỏ.
Nếu đã có output, dùng output hiện tại làm nguồn; nếu chưa có, dùng original.

## Cập nhật: chọn model cloud, chỉ gửi văn bản

Đã bổ sung `cloud_models.py`, giao diện nhiều profile và nút Tối ưu bằng AI.
Mỗi profile có base URL HTTPS/model/name, khóa session hoặc macOS Keychain.
Model IDs lấy trực tiếp từ `/models` hoặc nhập tay, không hardcode model mới.
OpenAI/Gemini/DeepSeek/OpenRouter dùng giao thức Chat Completions; endpoint
custom tương thích được hỗ trợ. Chưa có Anthropic native adapter.

`VideoControl.start_cloud` điều phối prepare → evaluate text-only → validate
→ refine/render. Profile/key chụp tại đầu lượt chạy, không đổi theo dropdown
trong lúc chạy. Không cần một agent Codex làm bước đánh giá trung gian. MCP
vẫn có thể khởi chạy qua auto_edit_with_model. Bản đồ draft/source và kiểm tra
revision tiếp tục bảo vệ việc xuất nhầm nguồn. Nhận dạng vẫn cục bộ vì không
được gửi media. Không có cloud ASR, cloud video upload hoặc cloud fallback.

Kiểm thử đã phủ key không xuất hiện trong config/listing, payload allowlist,
model trả ID sai, đổi endpoint không tái dùng key, pipeline dùng provider giả
lập, HTTP Origin cho settings và render video thật. Không có key thật để xác
nhận quota/model/account của từng nhà cung cấp. UI cấu hình đã kiểm tra trực
quan, key trống, trên dữ liệu thử riêng trong /tmp.

## Cập nhật: duyệt bắt buộc và giới hạn RAM

Cloud pipeline hiện dừng tại awaiting_review. pending_reviews giữ kế hoạch
nội bộ, get_job trả review_rows (text/reason/source_ranges), preliminary_cuts
và thời lượng. Giao diện hiển thị checkbox, preview nguồn hỗ trợ HTTP Range,
Duyệt và xuất / Hủy đề xuất. Approve kiểm tra selection/source revision và chỉ
render các decision indexes được người dùng chọn. Đường process thường bị
chặn khi có review chờ duyệt, tránh xuất bỏ qua bước kiểm tra. Reload page
khôi phục review trong cùng app process. Chưa lưu review qua lần tắt app.

Renderer hiện là low_memory_render.py: mỗi tiến trình FFmpeg xử lý một đoạn,
sau đó stream-copy concat; không tạo graph xfade nhiều nhánh ở 4K. Chuyển tiếp
hiện dùng audio fades, thay cho matched audio/video crossfade trong thiết kế
cũ. Ưu tiên RAM có giới hạn theo một đoạn, đổi lại thêm I/O đĩa và thời gian.
Thử nghiệm thực tế 24 đoạn 4K ghi nhận FFmpeg peak RSS 368.5 MiB, không phải
phép đo tổng RAM/GPU. Preview nguồn đọc streaming 1 MB mỗi khối.

## Safe Export sau log kernel panic

Không còn coi RSS FFmpeg là đủ để xác nhận sửa hết lỗi RAM: panic log chỉ ra
VTDecoderXPCService lớn bất thường khi cinematic_blur chạy. Đường app bokeh mới
là FFmpeg software decode → raw BGRA pipe → Swift rawMode, không AVAssetReader.
Swift autoreleasepool từng frame, pool threshold ba buffer, CI cache off,
Vision CPU-only, long edge <=1920. GPU vẫn hỗ trợ blur/blend. Mã hóa FFmpeg mặc
định CPU; có hardware_encode opt-in chỉ ảnh hưởng encoder, không decoder.

media_runtime.py quản lý khóa liên process, stderr file, giám sát RSS/vm_stat,
progress timeout, terminate/wait/kill và dọn process group do mình khởi tạo.
Worker chỉ trả completed sau khi cleanup xong. Frontend unload player cũ khi
đổi file/xuất tiếp. Tests/repeated_export_smoke.py bao gồm hai task khác nhau
liên tiếp (cắt + bokeh + nén), kiểm tra process reap, A/V sync và cleanup file.
20 unit tests và smoke tests qua; chưa chạy toàn bộ nguồn dài từng gây panic.
