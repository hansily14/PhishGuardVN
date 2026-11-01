# FastAPI — hợp đồng API

Base URL: `http://127.0.0.1:8000`. Toàn bộ JSON dùng UTF-8. `/openapi.json` chứa schema; giao diện Swagger mặc định có thể bị CSP chặn script CDN, dùng file OpenAPI với client cục bộ.

Đăng nhập trả `csrf` và đặt cookie `pg_session` HttpOnly, SameSite=Strict. Tất cả thao tác ghi sau đăng nhập cần header `X-CSRF-Token: <csrf>`. Cookie được kiểm tra với phiên server, quyền hiện tại và tình trạng tài khoản trong DB.

| Endpoint | Quyền | Công dụng |
|---|---|---|
| POST /api/auth/register | Chưa đăng nhập | Tạo user; từ chối trường role do client gửi |
| POST /api/auth/login | Chưa đăng nhập | Xác thực, tạo phiên 8 giờ |
| GET /api/auth/me | Đăng nhập | Tài khoản, quyền và CSRF của phiên |
| POST /api/auth/logout | Đăng nhập | Thu hồi phiên |
| POST /api/auth/password | Đăng nhập | Đổi mật khẩu, thu hồi tất cả phiên |
| POST /api/checks | Đăng nhập | Phân tích text và urls, lưu lịch sử riêng |
| GET /api/checks | Đăng nhập | Lịch sử của chính mình, offset/limit |
| GET /api/checks/{id} | Chủ sở hữu | Kết quả chi tiết |
| DELETE /api/checks/{id} | Chủ sở hữu | Xóa dữ liệu kiểm tra |
| POST /api/reports | Đăng nhập | Gửi báo cáo phone/url, pending |
| GET /api/reports | Đăng nhập | Báo cáo của chính mình, offset/limit |
| PUT /api/reports/{id} | Chủ sở hữu | Sửa với version, đưa về pending |
| DELETE /api/reports/{id} | Chủ sở hữu | Rút báo cáo, ngừng xuất hiện công khai |
| GET /api/lookup | Đăng nhập | Tra cứu đúng phone/url đã chuẩn hóa |
| GET /api/stats | Đăng nhập | Thống kê cá nhân; period=day/week/month |
| GET /api/admin/reports | Admin | Tất cả báo cáo, lọc status, phân trang |
| POST /api/admin/reports/{id}/moderate | Admin | Duyệt/từ chối kèm note và version |
| DELETE /api/admin/reports/{id} | Admin | Xóa mềm, cập nhật tra cứu cộng đồng |
| GET /api/admin/users | Admin | Danh sách người dùng, không lộ hash mật khẩu |
| PATCH /api/admin/users/{id} | Admin | Khóa/mở, thay role, thu hồi phiên |
| GET /api/admin/stats | Admin | Thống kê toàn hệ thống theo kỳ |
| GET /api/admin/audit | Admin | 100 sự kiện quản trị gần nhất |
| GET /api/model-info | Đăng nhập | Phiên bản và giới hạn của mô hình |
| GET /api/health | Công khai | Kiểm tra dịch vụ, tình trạng file mô hình |

Ví dụ POST /api/checks:
```json
{"text":"Nội dung muốn kiểm tra", "urls":["https://example.com/login"]}
```

Ví dụ POST /api/reports:
```json
{"target_type":"url","target":"https://example.com/login","description":"Mô tả sự việc cần kiểm tra..."}
```

Sửa báo cáo thêm `version` nhận từ danh sách. Duyệt cần `{"status":"approved","note":"Đã kiểm tra nội dung","version":1}`. Nếu người gửi sửa trước khi admin duyệt, version cũ bị trả 409; tải lại dữ liệu rồi xem xét lại.

Lookup trả tổng báo cáo đã duyệt, số người gửi khác nhau, thời điểm cập nhật gần nhất. Không trả tên người tố cáo hoặc mô tả có thể chứa thông tin cá nhân. URL được đối chiếu chính xác sau canonicalization; một đường dẫn bị tố cáo không khiến mọi URL trong domain tự bị gắn cờ. Số điện thoại +84/84 được chuẩn hóa về 0.

Giới hạn demo: SQLite và limiter trong bộ nhớ cho một worker; triển khai nhiều worker cần PostgreSQL, Redis limiter, HTTPS và cookie Secure. DB dùng thời gian UTC, thống kê đổi sang UTC+7. Chuỗi báo cáo/kiểm tra được hiển thị bằng textContent để tránh HTML thực thi.
