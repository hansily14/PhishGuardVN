# PhishGuardVN — tuần 5, 6, 7, 8

Gói dự án Python/FastAPI có giao diện User/Admin, bốn notebook Jupyter, mô hình đã huấn luyện thật, báo cáo Validation và kiểm thử. Phiên bản 0.5.0, xây dựng từ hai ZIP dữ liệu bạn cung cấp. Đây là bản demo nghiên cứu chạy cục bộ; chưa triển khai website công khai.

## Chạy nhanh trên Windows

1. Giải nén **toàn bộ** gói ZIP, mở thư mục `PhishGuardVN_Weeks5_8` có file README này. Có thể đặt tại `C:\Users\ASUS\OneDrive - sad\Documents\Han\DATN\PhishGuardVN_Weeks5_8`.
2. Dùng Python 3.12. Thư viện trên máy phải tương thích với `requirements.txt`, đặc biệt scikit-learn 1.8.0 và XGBoost 3.4.1 để đọc mô hình đi kèm. Nếu môi trường đã khớp thì bỏ qua cài đặt; nếu chưa: `python -m pip install -r requirements.txt`.
3. Mở terminal tại thư mục dự án, chạy `python -m phishguard.create_admin` hoặc mở `create_admin.bat`. Tự nhập username và mật khẩu ít nhất 10 ký tự. Khi nhập mật khẩu, terminal không hiện ký tự. **Không có mật khẩu admin mặc định.**
4. Chạy `python -m uvicorn phishguard.api:app --host 127.0.0.1 --port 8000` hoặc mở `start.bat`.
5. Mở **http://127.0.0.1:8000**. Admin dùng tài khoản vừa tạo. User đăng ký từ màn hình đăng nhập.
6. Giữ cửa sổ server đang chạy. Ctrl+C để dừng. Không cần huấn luyện lại để dùng bản demo.

Nếu lệnh `python` trên máy bạn không đúng môi trường Jupyter, mở terminal từ môi trường đó hoặc thay bằng đường dẫn Python tương ứng. Không đổi các file mô hình giữa những phiên bản thư viện không tương thích.

## Notebook — import riêng ở cell đầu

| File | Nội dung |
|---|---|
| notebooks/Tuan_5_URL_LR_XGBoost.ipynb | Trích xuất đặc trưng, huấn luyện/tải kết quả, so sánh LR và XGBoost |
| notebooks/Tuan_6_SE_Risk_Fusion.ipynb | 6 nhãn đa nhãn, phân bố hỗ trợ, chọn alpha và ngưỡng Validation |
| notebooks/Tuan_7_SHAP_FastAPI.ipynb | SHAP từng URL, kiểm tra tổng đóng góp, biểu đồ giải thích |
| notebooks/Tuan_8_Web_RBAC_Tests.ipynb | Kiểm thử API/AI, hướng dẫn chạy User/Admin |

Notebook đã có đầu ra từ các cell Python được thực thi tuần tự bằng IPython trong tiến trình. Môi trường tạo gói không mở được kernel ZMQ nên không tuyên bố đã chạy kernel Jupyter riêng; định dạng notebook được nbformat kiểm tra. Trên máy bạn mở bằng Jupyter và Run All bình thường. Tuần 5 mặc định `RUN_TRAINING=False` để xem kết quả đã chạy; đổi True để huấn luyện lại.

Mọi import notebook nằm trong cell đầu, không lặp import ở các cell xử lý. Logic thực thi đặt trong các module `phishguard/` và dùng chung với API; cần giữ nguyên thư mục dự án khi chạy notebook.

Đường dẫn dữ liệu gốc đã cấu hình:
```python
DATA_DIR = Path(r"C:\Users\ASUS\OneDrive - sad\Documents\Han\DATN")
```
Hai ZIP giữ nguyên tên `vietnamese_sms_dataset.zip` và `phiusiil+phishing+url+dataset.zip`, không cần giải nén trước. Dữ liệu gốc không chép lại vào gói này. Có thể huấn luyện từ terminal:
```powershell
python -m phishguard.training --input-dir "C:\Users\ASUS\OneDrive - sad\Documents\Han\DATN" --output-dir .
```

## Những gì đã triển khai

**User:** đăng ký/đăng nhập/đăng xuất, đổi mật khẩu; kiểm tra tin nhắn, URL hoặc nhiều URL; xem điểm cảnh báo và giải thích; lịch sử kiểm tra riêng/xóa lịch sử; gửi/sửa/rút báo cáo; xem phản hồi admin; thống kê cá nhân; tra cứu số điện thoại/URL đã được cộng đồng báo cáo.

**Admin:** xem báo cáo toàn hệ thống, lọc trạng thái, phân trang; duyệt/từ chối có nhận xét; xóa mềm báo cáo; danh sách người dùng, khóa/mở, thay vai trò; thống kê ngày/tuần/tháng; nhật ký quản trị. Admin chỉ xem thống kê tổng các lượt kiểm tra; nội dung lịch sử cá nhân vẫn chỉ chủ tài khoản truy cập.

**Quy tắc cộng đồng:** chỉ tính báo cáo đã duyệt; hiển thị số người gửi khác nhau; một user không gửi lặp cho cùng đối tượng. Sửa báo cáo đưa về chờ duyệt; version kiểm soát việc admin duyệt nội dung cũ. Không có báo cáo không có nghĩa đối tượng an toàn. Phản ánh cộng đồng không phải kết luận pháp lý và không tự cộng vào điểm AI.

**Kiểm soát truy cập:** quyền được kiểm tra ở API, không dựa vào việc ẩn nút giao diện. Cookie HttpOnly/SameSite, CSRF token, PBKDF2 cho mật khẩu, thu hồi phiên khi khóa/đổi quyền/đổi mật khẩu. Không tự đổi quyền user từ dữ liệu đăng ký. SQL có tham số; nội dung người dùng hiển thị bằng textContent. Server không mở liên kết nghi ngờ.

## Các điều chỉnh cần ghi trong báo cáo tốt nghiệp

- Đổi tên nguồn chính thức từ PhishVN sang **PhiUSIIL**. Nhãn gốc **0=Phishing, 1=Legitimate**; nội bộ đảo thành **1=Phishing**. Notebook tuần 3 giữ nhãn gốc, không được mặc định coi 1 là phishing.
- Mô hình hiện tại dùng **31 đặc trưng lexical tính từ URL**. Đã có adapter snapshot DNS/RDAP/TLS, nhưng dữ liệu bạn gửi không có snapshot hạ tầng theo thời điểm. Vì vậy **chưa có thực nghiệm mô hình lexical + infrastructure**; không tạo dữ liệu WHOIS/DNS giả để lấp chỗ trống.
- Chưa có checkpoint XLM-R tuần 4 trong đầu vào. Nhánh văn bản chạy bằng **TF-IDF + Logistic Regression nhị phân**. Nguồn SMS gộp spam/scam, không đủ căn cứ tự chuyển thành ba lớp Legitimate/Spam/Phishing.
- 700 mẫu SE v2 có nhãn luật và sáu mô hình nhị phân. Một số nhóm quá ít mẫu dương, đặc biệt giả mạo chỉ có 3 mẫu Train và 2 mẫu Validation. API đánh dấu thiếu hỗ trợ, không dùng quyết định classifier cho nhóm chưa đạt ngưỡng số mẫu; vẫn hiển thị cụm từ luật tìm thấy. Cần nhãn người rà soát trước khi tuyên bố hiệu quả SE.
- **Risk Fusion hiện là proxy** trên nhãn SMS nguồn. Alpha tối ưu ra **1.0**, tức nhánh URL chưa cải thiện F1 trong thử nghiệm này. Không thay bằng alpha tùy ý để làm kết quả tốt hơn. URL vẫn được phân tích và hiển thị cảnh báo riêng.
- Chỉ số model-selection hiện là **Validation**, chưa phải Test. Test dành cho tuần 9. Xem báo cáo `reports/BAO_CAO_TUAN_5_8.md`.

## Hoàn thiện nhãn và thay mô hình văn bản

Dùng `data/social_engineering_700_v2.csv` để rà soát từng nhãn. Lưu bản được người gán nhãn kiểm tra thành `data/social_engineering_reviewed.csv` gồm `message_id`, sáu cột nhãn 0/1 và `annotation_status=human_reviewed`; chạy lại training để dùng nhãn này. Code tái dùng split từ corpus SMS, không tin split do người nhập cung cấp. Không đổi trạng thái human_reviewed khi chưa thực sự rà soát.

Với Risk Fusion, sau khi có mô hình văn bản tuần 4 và nhãn phishing riêng, xuất dự đoán paired Validation theo `docs/paired_validation_template.csv`; gọi `python -m phishguard.fusion <csv> <output.json>`. Hàm từ chối Test hoặc nhãn chưa review. Đây là công cụ tuning; cần tích hợp checkpoint văn bản đúng nhãn vào Engine và kiểm tra lại pipeline trước khi thay cấu hình phục vụ. File mẫu hiện chỉ có header, không có dữ liệu gold giả.

## Kết quả và kiểm thử

- `reports/validation_results.json`: chỉ số thực nghiệm URL, baseline text, weak-label SE và proxy fusion.
- `reports/url_validation_comparison.csv`: toàn bộ cấu hình URL trên cùng Validation.
- `reports/fusion_validation_grid.csv`: 21 giá trị alpha và ngưỡng tối ưu tương ứng.
- `data/url_split_manifest.csv.gz`: URL chuẩn hóa, domain group, nhãn gốc/nhãn phishing và split; không tính Test metrics.
- `models/manifest.json`: checksum hai nguồn, phiên bản thư viện, schema đặc trưng, ngưỡng, alpha và kiểm tra leakage.
- `reports/tests.txt`, `reports/tests.xml`: kết quả kiểm thử thật.
- `reports/ui_smoke.json`: kiểm thử thao tác DOM với API đang chạy, không phải ảnh chụp trình duyệt.

Chạy lại kiểm thử: `python -m pytest tests -q` hoặc mở `run_tests.bat`.

## Dữ liệu lưu trên máy

Lần chạy đầu tạo `instance/phishguard.db`; gói không chứa tài khoản hay phiên đăng nhập sẵn. DB lưu nội dung bạn nhập để phục vụ lịch sử; người dùng có thể xóa từng lần kiểm tra. Sao lưu DB sau khi dừng server hoặc dùng SQLite backup API. Đặt `PHISHGUARD_DB` để đổi vị trí; dùng ổ cục bộ nếu OneDrive gây khóa đồng bộ. Khi triển khai HTTPS đặt `COOKIE_SECURE=1`; bản demo mặc định chỉ lắng nghe localhost.

## Cải tiến đề xuất

Ưu tiên: gán nhãn thủ công và đánh giá độc lập; hoàn thiện checkpoint XLM-R; dữ liệu hạ tầng theo thời điểm; xác minh email, kênh bổ sung chứng cứ và phản hồi quyết định duyệt. Khi nhiều người dùng: PostgreSQL, limiter Redis, chính sách lưu/xóa, backup và giám sát. Trước khi cho upload minh chứng cần thêm kiểm tra file; bản hiện tại nhận mô tả văn bản.

## Nguồn và đối chiếu

- UCI PhiUSIIL, quy ước nhãn/giấy phép CC BY 4.0: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset — Prasad, A. & Chandra, S. (2024), DOI 10.1016/j.cose.2023.103545 (theo trang UCI).
- SMS: ZIP do người dùng cung cấp; README nguồn nêu nhóm Trần Nguyễn Thái Tuấn và cộng sự, CC BY 4.0. Thông tin xuất bản/benchmark trong README nguồn không phải kết quả của gói này.
- XGBoost Tree SHAP: https://xgboost.readthedocs.io/en/stable/python/python_api.html ; SHAP API: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html .

Chi tiết kiến trúc, giới hạn và mapping: `docs/KIEN_TRUC.md`. Hợp đồng API: `docs/API.md`.
