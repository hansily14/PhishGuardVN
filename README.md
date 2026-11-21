# PhishGuardVN — Hướng dẫn cài đặt, chạy thử và tái lập thực nghiệm

**Đề tài:** Hệ thống kiểm tra và báo cáo nội dung nghi ngờ lừa đảo qua tin nhắn và URL, kết hợp phân tích các dấu hiệu Social Engineering.

> **Phạm vi xác minh:** README này được cập nhật theo cấu trúc mã nguồn, các notebook và kết quả thực nghiệm được cung cấp. Chưa xác nhận cài đặt và chạy lại toàn bộ dự án trên một máy mới. Bản ZIP mã nguồn cũ có lỗi entry chồng lấn; **không dùng nguyên trạng để nộp hoặc đưa lên GitHub**. Hãy lấy mã nguồn từ thư mục dự án đã chạy được trên máy, kiểm tra lại file cần nộp rồi tạo bản ZIP mới.

## 1. Công nghệ

- Python 3.12; FastAPI và Uvicorn cho API/backend.
- SQLite cho dữ liệu nghiệp vụ; HTML, CSS và JavaScript cho giao diện.
- scikit-learn (TF-IDF + Logistic Regression), XGBoost (URL), SHAP (giải thích dự đoán).
- PyTorch, Hugging Face Transformers, Accelerate và SentencePiece cho **thử nghiệm fine-tune XLM-RoBERTa nhị phân**.
- Cài các gói theo `requirements.txt`; nhánh XLM-RoBERTa có thể cần thêm `requirements_xlmr.txt` và cấu hình PyTorch phù hợp máy tính.

## 2. Cấu trúc dự án

```text
PhishGuardVN_TD/
├── phishguard/                 # api.py, engine.py, database.py, security.py, training.py...
├── web/                        # index.html, app.js, style.css
├── models/                     # Mô hình phục vụ ứng dụng và manifest.json
│   └── text_comparison/        # Artifact thực nghiệm (nếu đã sao chép từ máy huấn luyện)
│       ├── tfidf_lr_candidate.joblib
│       └── xlmr_binary/        # Checkpoint/tokenizer XLM-RoBERTa nhị phân
├── notebooks/
│   ├── Tuan_5_Huan_luyen_va_Danh_gia_Nhanh_Van_Ban_TFIDF_XLMR.ipynb
│   ├── Tuan_5_URL_LR_XGBoost.ipynb
│   ├── Tuan_6_SE_Risk_Fusion.ipynb
│   ├── Tuan_9_Danh_gia_thuc_nghiem.ipynb
│   └── Tuan_10_Danh_gia_thuc_nghiem.ipynb
├── data/                       # Manifest chia tập và dữ liệu được phép chia sẻ
├── reports/                    # Chỉ số, báo cáo kiểm thử, hình minh chứng
│   └── text_comparison/        # Kết quả nhánh văn bản nếu đã xuất từ notebook
├── docs/                       # API, kiến trúc, nguồn dữ liệu
├── scripts/                    # Script hỗ trợ, nếu có
├── database/                   # Schema và mẫu dữ liệu đã xuất (tạo khi bàn giao)
├── requirements.txt
├── requirements_xlmr.txt       # Nếu dùng để tái lập nhánh XLM-RoBERTa
├── start.bat
└── README.md
```

*Các đường dẫn `models/text_comparison/`, `reports/text_comparison/` và `database/` là đầu ra của quá trình huấn luyện/xuất dữ liệu; chỉ đưa vào gói bàn giao sau khi xác nhận chúng thực sự có trên máy.*

## 3. Cài đặt và chạy Web trên Windows

Mở PowerShell tại thư mục `PhishGuardVN_TD`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv312\Scripts\python.exe -m uvicorn phishguard.api:app --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000** khi terminal xác nhận server đã chạy. Có thể sử dụng `start.bat` nếu đã kiểm thử script này trong bản bàn giao.

> **Lưu ý:** `127.0.0.1` chỉ truy cập được trên máy đang chạy server. Link này không phải đường dẫn demo công khai cho giảng viên.

### Tài khoản và phân quyền

Tạo Admin bằng:

```powershell
.\.venv312\Scripts\python.exe -m phishguard.create_admin
```

Làm theo hướng dẫn nhập tên đăng nhập và mật khẩu. Tạo User thử nghiệm qua giao diện đăng ký nếu chức năng này được bật. **Không công bố mật khẩu mặc định hoặc mật khẩu sử dụng thật.** Với bản bàn giao cho giảng viên, cung cấp tài khoản demo riêng và chuyển mật khẩu qua kênh riêng.

> SQLite lưu tại máy cục bộ: nếu giảng viên chạy trên máy khác, chỉ gửi mã nguồn **không tự động mang theo các tài khoản đã tạo**. Cần có CSDL demo không chứa dữ liệu thật hoặc hướng dẫn tạo tài khoản thử trên máy chấm.

## 4. Tái lập thực nghiệm nhánh văn bản

Notebook hợp nhất:

`notebooks/Tuan_5_Huan_luyen_va_Danh_gia_Nhanh_Van_Ban_TFIDF_XLMR.ipynb`

Quy trình: sử dụng cùng Train/Validation/Test và nhãn nhị phân; huấn luyện **TF-IDF + Logistic Regression** và **XLM-RoBERTa-base**; chọn mô hình/ngưỡng theo Validation; sau đó đánh giá Test độc lập. Không lựa chọn lại mô hình dựa trên Test.

Nếu cần cài môi trường thực nghiệm:

```powershell
.\.venv312\Scripts\python.exe -m pip install -r requirements_xlmr.txt
```

Nếu tệp requirements bổ sung không bao gồm đủ các gói học sâu, cài đúng Kernel notebook:

```powershell
.\.venv312\Scripts\python.exe -m pip install torch "transformers==4.57.1" accelerate sentencepiece ipykernel
```

Lần chạy đầu có thể cần kết nối Internet để tải pretrained model `FacebookAI/xlm-roberta-base`. Trên CPU, thời gian huấn luyện có thể dài hơn đáng kể.

**Kết quả thực nghiệm được ghi nhận từ notebook hoàn tất:**

| Chỉ số | TF-IDF + LR | XLM-RoBERTa |
|---|---:|---:|
| F1 trên Validation | **94,74%** | 93,72% |
| Precision trên Test | 89,52% | 94,12% |
| Recall trên Test | 94,00% | 96,00% |
| F1 trên Test | 91,71% | **95,05%** |
| FPR trên Test | 4,51% | 2,46% |
| PR-AUC trên Test | 96,97% | 98,14% |

- Test nhánh văn bản: **344 mẫu**; ngưỡng đánh giá được lựa chọn từ Validation: TF-IDF + LR **0,52**, XLM-RoBERTa **0,32**.
- **Mô hình được chọn theo Validation là TF-IDF + Logistic Regression.** XLM-RoBERTa có F1 cao hơn trên Test, nhưng không dùng kết quả Test để thay đổi quyết định lựa chọn.
- Bài toán văn bản là **phân loại nhị phân Legitimate / Spam–Scam theo nhãn nguồn**, không phải mô hình phishing ba lớp.
- Để người khác kiểm chứng, kèm notebook đã lưu output cùng các tệp xuất ra nếu có: `reports/text_comparison/text_validation_selection.json`, `text_validation_comparison.csv`, `text_test_comparison.csv`, `text_final_results.json`. Kiểm tra tên và nội dung thực tế trước khi commit.

**Artifact thực nghiệm:** `models/text_comparison/tfidf_lr_candidate.joblib`, `models/text_comparison/xlmr_binary/` nếu còn trên máy; checkpoint XLM-RoBERTa có thể lớn, nên sử dụng Git LFS hoặc liên kết tải riêng khi cần. Việc checkpoint tồn tại không đồng nghĩa Web đã tích hợp XLM-RoBERTa.

## 5. Thực nghiệm URL, Social Engineering và Risk Fusion

- `notebooks/Tuan_5_URL_LR_XGBoost.ipynb`: trích xuất đặc trưng và so sánh Logistic Regression/XGBoost cho URL. Kết quả URL Test đã ghi nhận: **34.017 mẫu**, XGBoost **F1 ≈ 97,34%** (`reports/week9_url_test_metrics.json`).
- `notebooks/Tuan_6_SE_Risk_Fusion.ipynb`: phân tích sáu nhóm tín hiệu Social Engineering bằng nhãn quy tắc/nhãn yếu và thử nghiệm Risk Fusion **proxy**.
- `notebooks/Tuan_9_Danh_gia_thuc_nghiem.ipynb`, `Tuan_10_Danh_gia_thuc_nghiem.ipynb`: đối chiếu train/predict, robustness, đánh giá, các kết quả bổ sung (tùy phiên bản đã chạy).
- Trường hợp `α = 1,0` trong thử nghiệm proxy có nghĩa nhánh URL không đóng góp vào điểm hợp nhất tại cấu hình đó. **Chưa có tập nhãn cặp SMS–URL độc lập đủ để kết luận Risk Fusion cải thiện khả năng phát hiện phishing.**
- Không khẳng định đã huấn luyện XLM-RoBERTa **ba lớp** hay tích hợp nhánh XLM-RoBERTa mới vào Web khi chưa có minh chứng tương ứng.

## 6. Kiểm thử hệ thống

Nếu đã cài `pytest` và dự án có bài kiểm thử tương ứng:

```powershell
.\.venv312\Scripts\python.exe -m pytest -q
```

`reports/tests.txt` của bản cung cấp có log lịch sử **`9 passed, 1 warning`**. Đây là kết quả đã ghi nhận, **không phải xác nhận hệ thống đã được kiểm thử lại trên máy người nhận**. Kiểm tra đăng nhập User/Admin, phân quyền, gửi báo cáo, kiểm tra tin nhắn/URL, xử lý đầu vào và các API trước buổi bảo vệ.

## 7. Cơ sở dữ liệu và dữ liệu demo

Hệ thống sử dụng SQLite, gồm các bảng nghiệp vụ đã đối chiếu: `users`, `checks`, `reports`, `sessions`, `audit`.

Để nộp hồ sơ:

- **Cấu trúc CSDL:** `database/schema.sql` và tùy chọn `database/SCHEMA_OVERVIEW.md`, được xuất trực tiếp từ SQLite/schema thật; không dùng cấu trúc tự suy đoán.
- **Dữ liệu mẫu:** `database/sample_data_illustrative.json` là dữ liệu giả lập để minh họa, **không phải tệp seed dùng được ngay**. Nếu hội đồng yêu cầu đăng nhập và thao tác dữ liệu sẵn có, cần chuẩn bị một CSDL demo riêng (đã kiểm tra), hoặc script seed thực sự tương thích.
- **Tài khoản kiểm thử:** ghi tên đăng nhập demo trong tài liệu bàn giao riêng; gửi mật khẩu qua kênh riêng. Không đăng công khai mật khẩu.
- **Không commit:** `instance/phishguard.db` từ máy đang dùng, session/token, `.env`, mật khẩu, dữ liệu cá nhân hoặc dữ liệu nguồn bị hạn chế cấp phép.

Nếu dùng `export_database.py` của bộ bàn giao CSDL đã chuẩn bị, chạy tại thư mục gốc sau khi chép script vào đó:

```powershell
.\.venv312\Scripts\python.exe export_database.py --db "instance\phishguard.db" --out "database"
```

Script xuất cấu trúc và dữ liệu minh họa; cần kiểm tra đường dẫn cơ sở dữ liệu và các tệp xuất trước khi phát hành.

## 8. Danh sách tệp minh chứng cần kèm khi nộp

- **Mã nguồn chạy được:** `phishguard/`, `web/`, các tệp dependency, script chạy và `README.md`.
- **Notebook/nguồn dữ liệu:** notebook Text TF-IDF/XLM-RoBERTa bản cuối; URL, SE/Fusion và notebook đánh giá; manifest chia tập và hướng dẫn nguồn dữ liệu.
- **Kết quả:** các JSON/CSV Test–Validation, báo cáo kiểm thử, hình SHAP/Confusion Matrix nếu đã có; checkpoint mô hình cần để demo.
- **CSDL:** cấu trúc SQL và dữ liệu mẫu an toàn; hướng dẫn dựng CSDL/tạo tài khoản demo.
- **Tài liệu bảo vệ (nộp riêng nếu Khoa yêu cầu):** đề cương được duyệt, báo cáo Word/PDF, slide PowerPoint/PDF, video thuyết trình và demo, link GitHub.




