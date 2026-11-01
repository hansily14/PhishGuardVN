# Thiết kế tuần 5–8

## Điều chỉnh phạm vi nghiên cứu

1. Thay nguồn PhishVN bằng PhiUSIIL; không dùng cấu trúc PhishVN để suy ra cột vắng mặt trong PhiUSIIL.
2. Nhãn URL gốc 0=phishing, 1=legitimate; nhãn nội bộ đảo lại 1=phishing. Đây là điểm bắt buộc, nếu đảo sai thì mọi cảnh báo/Recall phishing đều sai nghĩa.
3. Bộ 700 SMS tuần 3 là nhãn luật, không phải dữ liệu chuyên gia. Phiên bản v2 bỏ bớt luật quá rộng, thêm hỗ trợ không dấu và lưu trạng thái weak_rules_v2_unreviewed. Số mẫu vẫn 700, được lấy lại sau chuẩn hóa chặt hơn; không coi đây là cùng 700 ID của bản cũ.
4. Không có checkpoint XLM-R tuần 4 trong đầu vào hiện tại. Bản chạy thật dùng baseline TF-IDF + LR nhị phân từ nguồn SMS để tích hợp pipeline. Spam/scam gộp không thể thay thế nhãn phishing riêng hoặc suy thành 3 lớp.
5. Risk Fusion được cài đặt đầy đủ, nhưng tuning hiện tại chỉ là proxy. Có module riêng nhận paired validation đã rà soát để chọn lại alpha/ngưỡng sau khi hoàn tất nhãn và tích hợp mô hình văn bản chính thức.
6. Social Engineering nhận diện **dấu hiệu tự nhận danh tính**, không chứng minh danh tính đó bị giả mạo. Giao diện không kết luận ai lừa đảo chỉ vì có cụm từ thương hiệu/ngân hàng.

## Luồng dữ liệu

Tin nhắn/URL → trích URL → chuẩn hóa → 31 đặc trưng lexical → mô hình URL → max(P_url).

Tin nhắn → chuẩn hóa văn bản → TF-IDF/LR nhị phân + 6 classifier dấu hiệu → điểm văn bản và danh sách dấu hiệu.

Có hai nhánh → Risk Fusion; chỉ văn bản/URL → dùng nhánh tương ứng. Giải thích từng URL bằng SHAP, hiển thị chứng cứ câu chữ của luật và xác suất nhận diện đa nhãn riêng.

Kết quả AI → checks thuộc chủ tài khoản. Người dùng tự gửi reports → pending → admin approved/rejected → chỉ approved xuất hiện khi lookup. Không tự gửi báo cáo vì điểm AI cao; không cộng số báo cáo vào điểm mô hình.

## Cơ sở dữ liệu

- users: username duy nhất, mật khẩu PBKDF2, role, active.
- sessions: hash token, CSRF, user_id, hạn dùng.
- checks: nội dung nhập, kết quả JSON, thời gian, owner.
- reports: phone/url, mô tả, trạng thái, version, deleted, owner và thời gian.
- audit: ai thực hiện, hành động, đối tượng, nhận xét, thời gian.

Một báo cáo đang hoạt động cho mỗi (user_id,target_type,target). Sửa báo cáo đã duyệt làm status trở về pending. Thu hồi/xóa mềm loại khỏi count công khai nhưng giữ dấu vết xử lý. Không xóa tài khoản vật lý để tránh mất quan hệ audit; khóa/mở tài khoản đáp ứng quản lý người dùng.

## Hạ tầng và ánh xạ đặc trưng

| Nhóm yêu cầu | Triển khai | Trong mô hình đã học? |
|---|---|---|
| Độ dài URL/domain/TLD, ký tự chữ/số, dấu đặc biệt | Tính lại trong features.py | Có |
| HTTPS, IP host, subdomain, phần trăm mã hóa | Tính trực tiếp từ URL | Có |
| Entropy, path/query, punycode, cổng, từ khóa | Tính trực tiếp từ URL | Có |
| DNS tồn tại/số câu trả lời | Nhập snapshot thực đo | Chưa |
| Tuổi domain/ngày đến hết hạn | Parser RDAP snapshot | Chưa |
| TLS hợp lệ | Giá trị thực đo trong snapshot | Chưa |
| FILENAME, Title, HTML, URLSimilarityIndex, TLDLegitimateProb | Không đưa vào vector lexical | Không |

Cột giữ tên gần PhiUSIIL nhưng định nghĩa tính lại được ghi trong mã; không trộn đặc trưng tiền tính sẵn với extractor khác khi serving. HTTPS chỉ phản ánh scheme; không thay thế kiểm tra chứng thư TLS. Dữ liệu hạ tầng vắng là NaN + missing indicator, không điền 0 để giả lập kết quả đo.

## Kiểm soát rò rỉ

- Chuẩn hóa URL bảo toàn chữ hoa/thường của path/query; khác với cách casefold toàn URL ở notebook cũ.
- Loại URL trùng, xung đột nhãn; chia theo registered domain với PSL private suffix.
- Loại URL có domain trong corpus SMS khỏi toàn corpus URL trước chia, để giảm chồng lấn khi tuning fusion.
- SMS thay chuỗi số dài trong đầu vào, loại trùng/xung đột; gom nhóm cosine char n-gram ≥0.88 trước chia.
- SE và mô hình text kế thừa cùng split/group; không huấn luyện nhánh SE trên SMS thuộc validation/test của nhánh text.
- TF-IDF của mô hình văn bản/SE, scaler LR chỉ fit Train. TF-IDF riêng dùng phát hiện trùng trên toàn corpus chỉ phục vụ phân nhóm, không tái dùng làm predictor.
- Ngưỡng, C, độ sâu cây, alpha chỉ chọn trên Validation. Chỉ số này có thể lạc quan do chọn cấu hình trên cùng Validation; Test giữ cho tuần 9.

## Cải tiến tiếp theo

Ưu tiên hoàn tất nhãn người rà soát cho 3 lớp văn bản và 6 nhãn SE; đo agreement giữa hai người, giải quyết bất đồng. Sau đó nạp checkpoint XLM-R tuần 4, tạo dự đoán cùng paired Validation và tuning lại. Thu thập DNS/RDAP/TLS theo thời điểm, giữ lịch sử và thêm thử nghiệm lexical-only vs lexical+infrastructure. Trước triển khai công khai, thêm xác minh email, cơ chế phản hồi/khiếu nại, chính sách lưu/xóa dữ liệu, HTTPS, backup, PostgreSQL và limiter dùng Redis. Tệp minh chứng cần kiểm tra định dạng/kích thước và quét trước khi mở; bản này dùng mô tả văn bản, chưa nhận file upload.
