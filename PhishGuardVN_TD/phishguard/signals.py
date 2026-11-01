"""Auditable weak annotation; lexical indicators are not proof of impersonation."""
import re
import unicodedata
LABELS=['impersonation','urgency_fear','reward_benefit','sensitive_info_request','financial_transaction','link_login_app_action']
LABEL_NAMES=['Dấu hiệu tự nhận danh tính/tổ chức','Khẩn cấp hoặc sợ hãi','Lợi ích hoặc phần thưởng','Yêu cầu thông tin nhạy cảm','Yêu cầu giao dịch tài chính','Yêu cầu mở link / đăng nhập / cài ứng dụng']
PATTERNS=[
 r'(?:chung toi|toi|day la|thong bao tu|dai dien|nhan vien)\b.{0,35}(?:ngan hang|cong an|toa an|cuc thue|shopee|viettel)|(?:\[(?:vcb|bidv|vietcombank|cong an|shopee)\])',
 r'khan cap|ngay lap tuc|trong vong|bi khoa|khoa tai khoan|tam ngung|xu ly hinh su|vi pham|truy to|het han|truoc.{0,12}(?:gio|hom nay)',
 r'trung thuong|nhan thuong|nhan qua|qua tang|hoan tien|uu dai|khuyen mai|khuyen mai|mien phi|hoa hong|lai suat|thu nhap cao',
 r'(?:cung cap|gui|nhap|xac nhan|cap nhat|chup|dien|chia se).{0,40}(?:otp|mat khau|cccd|cmnd|ma pin|ma cvv|thong tin ca nhan|so the)',
 r'(?:hay|vui long|can|yeu cau|phai|nhanh|ban|anh|chi).{0,25}(?:chuyen tien|chuyen khoan|thanh toan|nop tien|dong phi|nap tien)|(?:chuyen tien|chuyen khoan|nop tien|dong phi).{0,30}(?:de|nhan|vao|tai)',
 r'truy cap|nhap vao|nhap link|nhap lien ket|bam vao|click|dang nhap|cai dat|tai ung dung|tai app|mo app'
]

def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold().replace('đ','d')) if not unicodedata.combining(c))

def rule_evidence(text):
    text=unicodedata.normalize('NFC',text)
    s=folded(text); outputs=[]
    for key,name,pattern in zip(LABELS,LABEL_NAMES,PATTERNS):
        matches=[]
        for m in re.finditer(pattern,s):
            # Exclude explicit negation before a request. Not a semantic gold annotator.
            before=s[max(0,m.start()-30):m.start()]
            if key=='sensitive_info_request' and re.search(r'(khong|dung|tuyet doi khong)\s*$',before): continue
            matches.append({'start':m.start(),'end':m.end(),'text':text[m.start():m.end()]})
        outputs.append({'key':key,'name':name,'evidence':matches,'present':bool(matches),'status':'weak_indicator'})
    return outputs
