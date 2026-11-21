# PhishGuardVN — Bàn giao cơ sở dữ liệu và tài khoản kiểm thử

## 1. Có gì trong gói này?

- `export_database.py`: mã Python **chỉ đọc** SQLite hiện có và xuất **đúng cấu trúc CSDL** từ `sqlite_master`.
- `schema.sql`: được **tạo ra khi bạn chạy script**; là cấu trúc bảng/index/trigger/view, **không có mật khẩu hay dữ liệu cá nhân**.
- `schema_catalog.json` và `SCHEMA_OVERVIEW.md`: danh sách tên bảng, cột, kiểu dữ liệu và quan hệ khóa ngoại.
- `sample_data_illustrative.json`: dữ liệu **minh họa giả lập theo cấu trúc thật**, không phải dữ liệu thật và không dùng làm tài khoản đăng nhập.
- `TAI_KHOAN_KIEM_THU_MAU.md`: mẫu bàn giao tài khoản User và Admin hiện có.

## 2. Cách dùng (Windows, PowerShell)

Chép **riêng file** `export_database.py` vào thư mục gốc **`PhishGuardVN_TD`**, nơi có thư mục `instance` và `phishguard`.

```powershell
cd "C:\Users\ASUS\OneDrive - sad\Documents\Han\DATN\PhishGuardVN\PhishGuardVN_TD"
py -3.12 export_database.py --db "instance\phishguard.db" --out "database"
```

Nếu thư mục gốc khác, thay `cd` cho đúng. Script chỉ đọc file SQLite, không sửa bảng hay tài khoản. Nếu ứng dụng dùng biến `PHISHGUARD_DB` trỏ sang nơi khác thì chỉ định đường dẫn thật trong `--db`.

Sau khi chạy, trong `database/` sẽ có 4 file kể trên. Đưa `database/schema.sql`, `database/schema_catalog.json`, `database/sample_data_illustrative.json`, `database/SCHEMA_OVERVIEW.md` lên GitHub. Nên giữ `export_database.py` trong `scripts/` để hội đồng có thể chạy lại.

**Không đưa** `instance/phishguard.db`, `.env`, access token, cookie, mật khẩu, hoặc file SQLite sao chép từ máy đang dùng lên GitHub công khai. Nếu giảng viên cần CSDL có bản ghi để demo, hãy tạo database demo riêng từ ứng dụng và dùng tài khoản thử nghiệm riêng, không sao chép dữ liệu thật.

## 3. Tài khoản User/Admin hiện có

Vì bạn đã tạo cả hai tài khoản, **không cần tạo lại**. Điền **chỉ tên đăng nhập thử nghiệm** vào mẫu `TAI_KHOAN_KIEM_THU_MAU.md`, kiểm tra đăng nhập được và trao mật khẩu **riêng cho giảng viên** (tin nhắn riêng, email riêng, hoặc tài liệu trong kênh riêng được kiểm soát). Không commit mật khẩu vào repository public.

> Nếu dùng SQLite cục bộ, tài khoản trong database trên máy bạn **không tự tồn tại trên máy giảng viên** chỉ nhờ đăng mã nguồn lên GitHub. Giảng viên phải chạy hệ thống có database demo đã khởi tạo tài khoản, hoặc bạn cần tạo tài khoản trên bản demo mà họ truy cập được.

## 4. Đối chiếu yêu cầu của Khoa

| Yêu cầu | Tệp bàn giao |
|---|---|
| Cấu trúc CSDL | `database/schema.sql`, `database/SCHEMA_OVERVIEW.md` |
| Dữ liệu mẫu | `database/sample_data_illustrative.json` (chỉ minh họa cấu trúc, **không phải dữ liệu chức năng chạy được**) |
| Tài khoản kiểm thử | `TAI_KHOAN_KIEM_THU_MAU.md` + mật khẩu gửi riêng + CSDL demo có tài khoản tương ứng |
| Hướng dẫn cài đặt | README của dự án + hướng dẫn chạy tại đây |

Để đáp ứng mạnh hơn yêu cầu **dữ liệu mẫu chạy được**, nên thêm quy trình `seed_demo` sử dụng đúng hàm API của ứng dụng để tạo tài khoản và báo cáo giả lập, sau khi kiểm thử trên máy. Không nên tự tạo lệnh INSERT khi chưa chắc schema và cách hash mật khẩu.
