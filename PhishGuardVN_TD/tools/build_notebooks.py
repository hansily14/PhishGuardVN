from pathlib import Path
import nbformat as nb
ROOT=Path(__file__).resolve().parents[1]
def markdown(s):return nb.v4.new_markdown_cell(s)
def code(s):return nb.v4.new_code_cell(s)
COMMON='''import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from IPython.display import display

PROJECT_DIR = Path.cwd()
if not (PROJECT_DIR / "phishguard").is_dir():
    PROJECT_DIR = PROJECT_DIR.parent
if not (PROJECT_DIR / "phishguard").is_dir():
    raise FileNotFoundError("Mở notebook trong thư mục notebooks của gói dự án.")
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
'''
def save(name,cells):
 n=nb.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
 nb.write(n,ROOT/'notebooks'/name)
save('Tuan_5_URL_LR_XGBoost.ipynb',[
markdown('# Tuần 5 — Trích xuất URL, Logistic Regression và XGBoost\n\n**Nguồn đã đổi sang PhiUSIIL**, không gọi các cột của PhiUSIIL là PhishVN. Import tập trung trong cell đầu. Gói đã có mô hình huấn luyện thật và kết quả Validation; đổi RUN_TRAINING=True để chạy lại pipeline từ 2 ZIP gốc.\n\nPhiUSIIL gốc: **0=Phishing, 1=Legitimate**. Nội bộ: **1=Phishing**. Chia theo registered domain bằng PSL offline, gồm private suffix. URL thuộc domain trong SMS được loại khỏi toàn bộ corpus URL để giảm chồng lấn giữa hai nhánh. Dữ liệu Test chỉ lưu manifest, chưa tính chỉ số.\n\nNguồn quy ước nhãn: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset'),
code(COMMON+'''from phishguard.features import extract_urls, feature_frame, infrastructure_features, LEXICAL
from phishguard.training import train_all
'''),
code('''DATA_DIR = Path(r"C:\\Users\\ASUS\\OneDrive - sad\\Documents\\Han\\DATN")
RUN_TRAINING = False
if RUN_TRAINING:
    train_all(DATA_DIR, PROJECT_DIR)
results = json.loads((PROJECT_DIR / "reports/validation_results.json").read_text(encoding="utf-8"))
manifest = json.loads((PROJECT_DIR / "models/manifest.json").read_text(encoding="utf-8"))
print("Mô hình URL được chọn:", results["selected_url"])
print("Chia tập URL:", manifest["url_splits"])
print("Đã đánh giá Test:", results["test_evaluated"])
'''),
markdown('## Module trích xuất dùng chung với FastAPI\nNhận http/https, www, URL trần và hxxp/[.]. Chuẩn hóa hostname, giữ hoa/thường của path/query; không tải trang web. Loại FILENAME, Title, URLSimilarityIndex, TLDLegitimateProb và các cột cần HTML/nguồn ngoài khỏi mô hình lexical. 31 đặc trưng được tính lại từ URL để bảo đảm training/serving dùng cùng định nghĩa.'),
code('''urls = extract_urls("Vui lòng kiểm tra hxxps://example[.]com/login?ref=1 và www.example.org.")
print(urls)
display(feature_frame(urls))
print("Hạ tầng chưa có quan sát:", infrastructure_features(urls[0]))'''),
markdown('## So sánh trên cùng Validation\nChuẩn hóa StandardScaler chỉ fit Train cho Logistic Regression. XGBoost dùng histogram. Lưới cố định: LR C∈{0.1,1}; XGB max_depth∈{4,6}, 240 trees. Chọn threshold theo F1; hòa thì Recall cao hơn và FPR thấp hơn. Không dùng Test chọn mô hình/ngưỡng. PR-AUC trong báo cáo được tính bằng average precision.'),
code('''comparison = pd.DataFrame(results["url_validation"])
display(comparison[["model","precision","recall","f1","fpr","pr_auc","brier","threshold"]])
print("Kiểm soát dữ liệu:")
print(json.dumps({k: manifest[k] for k in ["source_label_mapping","sms_domain_rows_excluded_from_URL_corpus","url_conflicting_keys_removed","sms_audit"]}, ensure_ascii=False, indent=2))'''),
markdown('## Đặc trưng hạ tầng\n`phishguard/infrastructure.py` chuyển snapshot RDAP/DNS/TLS đã đo thành domain_age_days, registration_remaining_days, dns_resolves, dns_answer_count, tls_valid. Thời điểm đo sau as_of bị loại; dữ liệu thiếu là NaN và có missing indicator. PhiUSIIL đính kèm không có snapshot tương ứng, nên mô hình đóng gói **chỉ dùng lexical**. Cần thu thập snapshot và huấn luyện lại cùng schema trước khi tuyên bố đã thử nghiệm lexical + infrastructure.\n\nToàn bộ mã fit nằm trong `phishguard/training.py`, mã đặc trưng trong `phishguard/features.py`. Không tự tải hoặc truy cập URL người dùng gửi.')])
save('Tuan_6_SE_Risk_Fusion.ipynb',[
markdown('# Tuần 6 — Social Engineering đa nhãn và Risk Fusion\n\nSáu bộ phân loại nhị phân TF-IDF + Logistic Regression (Binary Relevance). Nhãn 700 tin được gán bằng rules v2, chưa có chuyên gia rà soát. Điểm trên Validation là mức khớp nhãn tự động; không được trình bày như độ chính xác phát hiện Social Engineering thực tế.\n\nSửa các luật quá rộng tuần 3: không gán giả mạo chỉ vì có “quý khách”; không gán yêu cầu OTP chỉ vì tin thông báo chứa OTP; yêu cầu thông tin có cụm hành động và loại trừ phủ định gần. Đây vẫn là weak labels, chưa giải quyết đầy đủ ngữ nghĩa.'),
code(COMMON+'''from phishguard.signals import LABELS, rule_evidence
from phishguard.engine import Engine
from phishguard.fusion import tune_reviewed_validation
'''),
code('''report = json.loads((PROJECT_DIR / "reports/validation_results.json").read_text(encoding="utf-8"))
se = pd.read_csv(PROJECT_DIR / "data/social_engineering_700_v2.csv")
print("Số mẫu:", len(se))
display(se.groupby("split")[LABELS].sum())
display(pd.DataFrame(report["social_engineering_validation_weak_labels"]).T)
'''),
markdown('## Kết hợp điểm\nTin không có URL: dùng điểm văn bản. Chỉ có URL: dùng mô hình URL và ngưỡng URL. Nhiều URL: dùng max(P_url). Có cả hai: α×P_text + (1−α)×max(P_url).\n\nChưa có checkpoint XLM-R tuần 4 trong đầu vào: bản chạy dùng TF-IDF + LR nhị phân từ nhãn SMS nguồn. Nhãn nguồn 1 gộp spam/scam, nên phép kết hợp hiện tại là **thử nghiệm proxy**, không phải xác suất phishing đúng nghĩa. Tối ưu alpha và ngưỡng trên Validation SMS có URL thật; không ghép SMS với URL ngẫu nhiên. Dữ liệu dùng chọn alpha chưa có gold labels.'),
code('''fusion = report["fusion_validation_proxy"]
print(json.dumps(fusion, ensure_ascii=False, indent=2))
grid = pd.read_csv(PROJECT_DIR / "reports/fusion_validation_grid.csv")
display(grid.sort_values(["f1","recall"], ascending=False).head(8))
if fusion["alpha"] == 1.0:
    print("Kết quả chọn alpha=1.0: nhánh URL chưa cải thiện F1 trong thử nghiệm proxy này. Không ép alpha khác để tạo kết quả đẹp.")'''),
code('''engine = Engine(PROJECT_DIR / "models")
result = engine.analyze("Vui lòng đăng nhập để nhận quà tại https://example.com/login")
print({key: result[key] for key in ["mode","risk_score","threshold","alpha","p_text_spam_scam","p_url_phishing"]})
display(pd.DataFrame(result["signals"])[["key","probability","predicted","evidence"]])'''),
markdown('## Tối ưu lại khi có nhãn người rà soát\nĐiền CSV theo mẫu `docs/paired_validation_template.csv`, dùng xác suất từ mô hình văn bản tuần 4 và URL model không học các nhóm validation đó. `split` phải là validation, `label_status` phải là human_reviewed, `y_phishing` 0/1 riêng với spam. Hàm chặn Test và weak labels; người nghiên cứu vẫn phải xác minh nguồn dữ liệu/prediction. Kết quả không tự động thay mô hình phục vụ khi mục tiêu nhãn đã thay đổi.'),
code('''REVIEWED_VALIDATION_CSV = None  # ví dụ PROJECT_DIR / "data/paired_validation_reviewed.csv"
if REVIEWED_VALIDATION_CSV is not None:
    gold_result = tune_reviewed_validation(REVIEWED_VALIDATION_CSV, PROJECT_DIR / "reports/fusion_gold_validation.json")
    display(gold_result["selected"])
else:
    print("Chưa có nhãn phishing đã rà soát: giữ nguyên trạng thái proxy của thử nghiệm hiện tại.")''')])
save('Tuan_7_SHAP_FastAPI.ipynb',[
markdown('# Tuần 7 — Giải thích URL bằng SHAP và AI Service\n\nTree SHAP dùng thuật toán exact trong XGBoost (`pred_contribs=True`). Đây là đóng góp log-odds; dấu dương tăng điểm phishing, dấu âm giảm điểm. Tổng base + mọi đóng góp bằng output margin, sigmoid(margin) bằng xác suất mô hình. Khi LR được chọn thì engine dùng SHAP LinearExplainer.'),
code(COMMON+'''import matplotlib.pyplot as plt
from phishguard.engine import Engine
from phishguard.features import feature_frame
'''),
code('''engine = Engine(PROJECT_DIR / "models")
result = engine.analyze("", ["https://example.com/login?verify=1"])
explanation = result["urls"][0]["shap"]
display(pd.DataFrame(explanation["top_features"]))
margin = explanation["base_value"] + sum(explanation["all_contributions"].values())
assert abs(margin - explanation["model_margin"]) < 1e-4
assert abs(1 / (1 + np.exp(-margin)) - result["urls"][0]["p_phishing"]) < 1e-5
print("SHAP additivity residual:", explanation["additivity_residual"])
fig, ax = plt.subplots(figsize=(9, 4.5))
rows = list(reversed(explanation["top_features"]))
ax.barh([r["feature"] for r in rows], [r["contribution"] for r in rows], color=["#ba593c" if r["contribution"]>0 else "#287d63" for r in rows])
ax.axvline(0, color="#53645d", linewidth=.8)
ax.set_xlabel("SHAP contribution (phishing log-odds)")
ax.set_title("URL explanation — example.com/login?verify=1")
fig.tight_layout()
fig.savefig(PROJECT_DIR / "reports/shap_example.png", dpi=150)
plt.show()'''),
markdown('## FastAPI\nTừ terminal ở thư mục dự án: `python -m phishguard.create_admin`, sau đó `python -m uvicorn phishguard.api:app --host 127.0.0.1 --port 8000`. Truy cập http://127.0.0.1:8000.\n\nPOST /api/checks nhận text và urls; cần đăng nhập, cookie phiên HttpOnly và X-CSRF-Token. API không dùng heuristic để thay mô hình khi thiếu checkpoint: trả 503 yêu cầu huấn luyện. Xem `docs/API.md` và mã `phishguard/api.py`.\n\nService chỉ xử lý chuỗi URL, không tải nội dung từ địa chỉ nghi ngờ. Số báo cáo cộng đồng không được tự cộng vào xác suất AI.')])
save('Tuan_8_Web_RBAC_Tests.ipynb',[
markdown('# Tuần 8 — Web User/Admin và kiểm thử toàn bộ luồng\n\nUser: kiểm tra, tra cứu cộng đồng, gửi/sửa/rút báo cáo, lịch sử kiểm tra riêng, thống kê, đổi mật khẩu. Admin: duyệt/từ chối/xóa báo cáo, khóa/mở tài khoản, đổi vai trò, thống kê toàn hệ thống, nhật ký thao tác.\n\nChỉ báo cáo đã duyệt xuất hiện trong tra cứu; đếm số người gửi khác nhau; sửa báo cáo đưa về pending; owner kiểm tra ở server, không dựa vào ẩn nút trên giao diện. Tuần dùng thứ Hai và có tuần 00 đầu năm theo SQLite %W, được ghi rõ trong API.'),
code(COMMON+'''import subprocess
'''),
code('''process = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--junitxml=reports/tests.xml"], cwd=PROJECT_DIR, capture_output=True, text=True)
print(process.stdout)
if process.stderr:
    print(process.stderr)
assert process.returncode == 0, "Có kiểm thử chưa đạt, cần sửa trước khi demo."
(PROJECT_DIR / "reports/tests.txt").write_text(process.stdout + process.stderr, encoding="utf-8")'''),
markdown('## Chạy web trên Windows\nGiải nén toàn bộ dự án, mở terminal tại thư mục có requirements.txt. Dùng Python 3.12 tương ứng môi trường đã kiểm thử; nếu thư viện không khớp thì cài requirements.txt. Chạy create_admin.bat một lần để tự đặt tài khoản admin, sau đó start.bat. User tự đăng ký ở màn hình đăng nhập. Không có mật khẩu admin mặc định.\n\nNotebook không mở server chặn kernel; start.bat chạy server trong cửa sổ terminal riêng. Cơ sở dữ liệu được tạo ở instance/phishguard.db trên máy bạn. Đọc README.md để xem thứ tự notebook, giới hạn mô hình và các đề xuất phát triển.')])
print('Created four notebooks')
