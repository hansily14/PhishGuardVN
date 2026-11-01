# UI smoke test

`tools/ui_smoke.cjs` kiểm thử DOM bằng jsdom với API ở 127.0.0.1:8765. Đây là kiểm thử script/DOM, chưa xác minh bố cục render trình duyệt. Kết quả chạy đã lưu ở reports/ui_smoke.json.

Chỉ chạy với DB thử nghiệm trống và tài khoản admin thử nghiệm `ui_admin` có mật khẩu `TemporaryUITest!2026`; script tự đăng ký `ui_member`. Các credential này chỉ dành cho test, không tồn tại trong gói DB của ứng dụng (gói không có DB). Không dùng cho tài khoản thật.

Đặt PHISHGUARD_DB trỏ tới DB test, tạo admin đó bằng CLI, chạy uvicorn cổng 8765. Trong thư mục dự án cài `npm install --no-save jsdom`, chạy `node tools/ui_smoke.cjs`. Xóa DB test sau khi xong.
