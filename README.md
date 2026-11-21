# PhishGuardVN — Hướng dẫn tái lập dự án

> Đây là README hướng dẫn được biên soạn từ cấu trúc tệp và báo cáo đã có. **Chưa xác nhận chạy lại toàn bộ mã nguồn trong bản ZIP cung cấp** do bản ZIP có các entry trùng/lỗi cấu trúc. Để đưa lên GitHub, dùng thư mục nguồn gốc trên máy đã được kiểm tra, KHÔNG upload ZIP hiện tại nguyên trạng.

## Công nghệ
Python 3.12, FastAPI, SQLite, scikit-learn, XGBoost, SHAP; giao diện HTML/CSS/JS. Phiên bản thư viện được khóa trong `requirements.txt`.

## Cấu trúc thư mục
````
PhishGuardVN_TD/
  phishguard/        # api.py, engine.py, database.py, features.py, signals.py, security.py, training.py
  web/               # index.html, app.js, style.css
  models/            # các artifact mô hình được phép phân phối và manifest
  notebooks/         # notebook tuần 5-10
  scripts/           # tiện ích huấn luyện/sửa mô hình
  reports/           # số liệu Test/Validation, kiểm thử chức năng, SHAP
  docs/              # API, kiến trúc và mô tả dữ liệu
  requirements.txt
  start.bat
````

## Cài đặt trên Windows (PowerShell)
````powershell
cd PhishGuardVN_TD
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv312\Scripts\python.exe -m uvicorn phishguard.api:app --host 127.0.0.1 --port 8000
````
Mở `http://127.0.0.1:8000` sau khi kiểm tra ứng dụng đã khởi động thành công.

## Tạo tài khoản Admin
````powershell
.\.venv312\Scripts\python.exe -m phishguard.create_admin
````
Nhập tài khoản và mật khẩu riêng (ít nhất 10 ký tự). **Không có mật khẩu quản trị mặc định được công bố.** Tạo tài khoản User kiểm thử qua giao diện đăng ký.

## Kiểm thử
````powershell
.\.venv312\Scripts\python.exe -m pytest -q
````
Bản báo cáo được cung cấp có log `9 passed, 1 warning`; đây là kết quả đã lưu, **không phải kết quả kiểm thử vừa chạy lại**.

## Dữ liệu, mô hình và kết quả
- `notebooks/Tuan_5_URL_LR_XGBoost.ipynb`: huấn luyện URL
- `notebooks/Tuan_6_SE_Risk_Fusion.ipynb`: nhãn yếu SE và thử nghiệm fusion proxy
- `notebooks/Tuan_9_Danh_gia_thuc_nghiem.ipynb`, `Tuan_10_Danh_gia_thuc_nghiem.ipynb`: đánh giá, kiểm thử và báo cáo
- `reports/week9_url_test_metrics.json`: Test URL độc lập, 34.017 mẫu; XGBoost F1 = 0.9734258507
- `reports/week9_execution_status.json`: trạng thái các nhánh chưa đánh giá
- `reports/tests.txt`: ghi nhận kiểm thử đã lưu
- `models/`: chỉ đưa mô hình được phép công khai và đã xác minh tính tương thích với môi trường

**Cảnh báo học thuật:** Text là nhị phân Legitimate/Spam–Scam; SE dùng nhãn quy tắc; fusion alpha=1.0 trong đánh giá proxy; không có checkpoint XLM-RoBERTa ba lớp và không có gold-validation cho fusion phishing.

## CSDL SQLite
Tệp dữ liệu thật dưới `instance/` phải được giữ riêng và KHÔNG commit. Hãy cung cấp tệp schema `.sql` hoặc mã khởi tạo từ `phishguard/database.py` sau khi xác nhận nguồn đầy đủ; tài khoản demo tự tạo trên máy của người chấm.
