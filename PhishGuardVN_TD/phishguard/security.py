import hashlib
import secrets
import hmac
import re

def password_hash(password):
    salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'

def password_matches(password,stored):
    try:
        _,iterations,salt,digest=stored.split('$')
        result=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(iterations)).hex()
        return hmac.compare_digest(result,digest)
    except (ValueError,TypeError):return False

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

def normalize_phone(value):
    s=re.sub(r'[\s().-]','',value)
    if s.startswith('+84'):s='0'+s[3:]
    elif s.startswith('84') and len(s) in (11,12):s='0'+s[2:]
    if not re.fullmatch(r'0\d{9,10}',s):raise ValueError('Số điện thoại Việt Nam cần 10–11 chữ số, bắt đầu bằng 0 hoặc +84.')
    return s
