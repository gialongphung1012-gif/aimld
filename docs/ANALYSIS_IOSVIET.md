# Báo cáo phân tích mã nguồn IOSViet.zip

Ngày kiểm tra: 2026-10-25. Phạm vi: duyệt cấu trúc toàn bộ ZIP, đọc các tệp manifest/build, header API, mã khởi chạy và overlay, mã tuỳ chọn/theme, tài nguyên bản địa hoá; đối chiếu kích thước và SHA-256 với `source-manifest.json`. Đây là phân tích tĩnh; không có môi trường iOS/Theos để chạy hoặc xác nhận hành vi trên thiết bị.

## 1. Nhận dạng dự án

- ZIP có 174 mục (gồm thư mục), khoảng 33.6 MB nén và 68.2 MB dữ liệu giải nén.
- Chủ yếu là Objective-C/Objective-C++: 106 `.h`, 17 `.mm`, thêm assembly `.S`, C/C++, tài nguyên, thư viện tĩnh `.a`, font, plist, workflow CI và makefile.
- `intex dylib/makefile` định nghĩa gói Theos `iOSViet`/`libsubsystem.dylib`, kiến trúc arm64, SDK mục tiêu iOS 16.5 và deployment target iOS 13.0. Đây là tweak/dylib, không phải project Xcode `.xcodeproj` hoàn chỉnh và không tự tạo IPA đã ký.
- `README.md` mô tả menu Free Fire; makefile có profile `th` và `max`.

## 2. Cấu trúc và vai trò

| Vùng | Vai trò quan sát được | Xử lý trong AIMLD mới |
|---|---|---|
| `.github/workflows/Build.yml` | CI macOS cài Theos, build dylib, upload artifact | Không sao chép pipeline tạo tweak; AIMLD có build/deploy riêng |
| `.github/workflows/unzip.yml` | Tự giải nén ZIP được push và commit kết quả | Không cần cho nền tảng cấp phép |
| `sources/` | Khởi tạo ứng dụng/overlay, menu controller, API client header, theme và các lớp kiểm tra môi trường | Tái tạo trải nghiệm cấu hình hợp pháp dưới dạng app SwiftUI độc lập; không giữ loader/injection/anti-hook |
| `esp/drawing_view/` | Vẽ overlay, menu, tuỳ chọn lưu, style, nút nổi có thể kéo và lưu vị trí | Chỉ mượn hướng thiết kế tối/sáng, accent mint, thẻ bo góc và mẫu tuỳ chọn; không tái tạo overlay game/ESP |
| `esp/Core/` | Các lớp liên quan game, dữ liệu nhân vật, mục tiêu, trạng thái người chơi, chuyển động và thao tác game | Loại khỏi AIMLD |
| `obfuscation/`, `oxorany/`, `mahoa.h` | Làm rối/ẩn chuỗi và mã | Không sao chép; secrets được quản lý qua biến môi trường |
| `layout/Resources/` | Font, icon, plist, chuỗi giao diện đa ngôn ngữ | Chỉ dùng tham khảo phong cách; tài nguyên cần rà soát quyền trước khi tái sử dụng |
| `libAPIClient.a` | Thư viện nhị phân liên quan API; không có source implementation đầy đủ trong ZIP | Không liên kết hoặc phụ thuộc vào binary này |
| `source-manifest.json` | Liệt kê tệp, byte count và SHA-256 kỳ vọng | Dùng làm bằng chứng kiểm tra tính nhất quán của archive |

## 3. Luồng hoạt động có thể xác nhận từ mã

1. Entry point trong `StealthDylibInit.mm` trì hoãn khởi tạo, đợi trạng thái ứng dụng/window sẵn sàng rồi yêu cầu gắn overlay vào cửa sổ ứng dụng.
2. `InjectedMenuController.mm` tạo view overlay và menu, đồng bộ các tuỳ chọn đã lưu.
3. `FloatingFeatureControl.mm` tạo nút nổi kiểu kính mờ, xử lý kéo thả, giới hạn vị trí trong superview và lưu toạ độ qua API preferences.
4. `ESPPrefs.h` khai báo API đọc/ghi boolean, float và object settings; `ESPStyle.h` đọc tuỳ chọn theme và màu.
5. `APIClient.h` khai báo các hàm set token/device/language và callback kiểm tra gói, thiết bị, đăng nhập; phần triển khai đầy đủ không hiện diện dưới dạng source trong ZIP.
6. `Localizable.strings` cho thấy một bộ HUD tiện ích có tuỳ chọn giao diện, kích thước/đơn vị, bật/tắt HUD, vị trí, hướng màn hình và hiển thị tốc độ mạng. Chuỗi dịch không chứng minh mọi mục đều hoạt động ở bản build này.

## 4. Giao diện và trải nghiệm quan sát được

- Menu overlay gắn lên cửa sổ host, có thể đóng/ẩn; có các nút phụ nổi và có thể kéo.
- Chủ đề dùng màu mint, nền tối/sáng, surface nhiều lớp, viền nhẹ và font AvenirNext khi có sẵn.
- Có hệ thống preferences để lưu tuỳ chọn và vị trí nút nổi.
- Có chuỗi bản địa hoá tiếng Anh, Tây Ban Nha và Trung giản thể.
- Có các thành phần HUD/utility. Vì iOS tiêu chuẩn hạn chế việc vẽ cửa sổ tuỳ ý lên ứng dụng khác, AIMLD mới chỉ giữ thiết kế tương đương trong phạm vi app của chính nó.

### Danh mục điều khiển nhìn thấy trong mã giao diện

Đây là kiểm kê nhãn/điều khiển tìm thấy trong `_0xMO353DA.mm`, không phải cam kết chúng đều hoạt động khi chạy:

- **Thanh điều hướng:** `Aim`, `ESP`, `Màu sắc`, `Thiết lập`; nút đóng `×`.
- **Trang Aim:** bộ chọn kiểu Aim; lựa chọn thời điểm kích hoạt; các công tắc có nhãn `Bật Silent Aim`, `Aimlag khi ngắm`, `Dây tới mục tiêu`, `Hiện vòng FOV`, `AimKill`, `Bắn nhanh (2×)`, `Không nạp đạn`; thanh trượt FOV và tỷ lệ headshot; mục mở rộng `Cài đặt nâng cao`.
- **Trang ESP:** `Bật ESP`, nút `Áp dụng ESP tối giản`, `Khung góc mảnh`, `Tên người chơi`, `Thanh máu`, `Trục XYZ`, `Khung người chơi`, `Xương người chơi`, `Điểm đánh dấu đầu`, `Khoảng cách`; chọn kiểu khung `2D/3D`; thanh trượt tầm hiển thị và ngưỡng màu máu.
- **Trang Màu sắc:** chọn đối tượng `Box/FOV`, xem swatch, thanh trượt thành phần màu `Đỏ/Lục/Lam`.
- **Trang Thiết lập:** các điều khiển được đặt nhãn `Ghost`, `FakeLag`, `Fly`, `Ẩn nút chức năng`, `Nút Speed`, `Speed`, trường số `Tốc độ (m/s)`, `Spin · chỉ mình thấy`, thanh trượt vòng/giây, `Ẩn khi chụp / quay`, `Giao diện tối`, `Tiết kiệm pin (30 FPS)`; một số điều khiển phụ chỉ hiện theo trạng thái.
- **Nút nổi:** dạng kính mờ hình tròn, nhãn truy cập, có kéo thả, giới hạn vị trí trong vùng cha và lưu tọa độ. Mã có các nhánh xử lý sự kiện cho điều khiển menu và đồng bộ preferences.

Các nhãn thuộc Aim/ESP/chỉnh chuyển động/ẩn khi quay được ghi nhận để mô tả source, nhưng không được triển khai lại như chức năng tác động game trong AIMLD. AIMLD thay bằng màn hình cấp phép, trạng thái tài khoản/thiết bị và cấu hình ứng dụng thông thường.

## 5. Nhóm chức năng không đưa vào AIMLD

Các nhóm mã về ESP/dữ liệu người chơi, nhắm mục tiêu, tự động bắn, sửa trạng thái/chuyển động game, đọc/ghi bộ nhớ, remote assembly, loader/overlay injection, hook và chống phân tích sẽ không được sao chép. Đây không phải phần của hệ thống cấp phép độc lập. Báo cáo không cung cấp offset, cấu trúc bộ nhớ hay quy trình can thiệp game.

## 6. Vấn đề bảo mật và tính nhất quán

- Có chuỗi token/API nhúng trực tiếp trong mã khởi chạy. Không sao chép token đó vào AIMLD; nếu token còn hoạt động, chủ sở hữu dịch vụ gốc nên thu hồi/đổi token.
- README ghi xác thực đã bị loại khỏi source; tuy nhiên API client header và lời gọi API vẫn còn trong source. Không nên suy ra backend gốc còn hoạt động hoặc có thể khôi phục chỉ từ ZIP.
- Đối chiếu 145 mục được liệt kê trong `source-manifest.json`: 140 mục khớp byte count và SHA-256; 5 mục không khớp là `esp/drawing_view/_0xE298S9_.mm`, `esp/drawing_view/_0xMU2872_.mm`, `makefile`, `sources/_0xMO353DA.mm`, `sources/StealthDylibInit.mm`. Đây là sai khác giữa manifest và nội dung hiện tại của archive.
- CI chỉ tạo dylib artifact; không có bằng chứng trong workflow này rằng IPA được đóng gói, ký và cài đặt thành công.
- Không có `.xcodeproj`/`.xcworkspace` đầy đủ. Cần Theos/macOS và SDK tương thích để thử build đúng target gốc.

## 7. Phạm vi tái tạo trong AIMLD

- Web admin responsive: đăng nhập, dashboard, tạo hàng loạt key, hạn dùng, tìm kiếm/lọc, khoá/mở khoá/thu hồi, gia hạn, reset thiết bị, CSV và audit.
- API độc lập: activate, validate, deactivate và status; HMAC key hash, token kích hoạt, kiểm tra hạn/trạng thái/giới hạn thiết bị ở server.
- Database SQLite, schema khởi tạo, backup/restore và test.
- App SwiftUI độc lập: nhập key, kích hoạt online, hiển thị trạng thái/hạn và kiểm tra lại bằng activation token trong Keychain.
- Không có game code, không tích hợp `libAPIClient.a`, không tái sử dụng token gốc và không tuyên bố giữ lại chức năng game.

## 8. Trạng thái kiểm thử

- Đã phân tích cấu trúc và so sánh manifest như phần trên.
- Python syntax check có thể chạy bằng thư viện chuẩn. Không thể chạy integration test tại môi trường đóng gói hiện tại vì Flask/Flask-Limiter chưa được cài và môi trường không truy cập được package index; không tuyên bố test API đã pass.
- Không chạy được app iOS/Theos trong môi trường hiện tại; chưa có IPA ký và chưa xác nhận hành vi trên iPhone thật.
