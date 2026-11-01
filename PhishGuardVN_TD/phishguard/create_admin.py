"""Interactive bootstrap; no embedded/default administrator password."""
import getpass
import os
import re
from pathlib import Path
from .database import initialize,connection
from .security import password_hash

def main():
    path=Path(os.getenv('PHISHGUARD_DB',str(Path(__file__).resolve().parents[1]/'instance'/'phishguard.db')));initialize(path)
    username=input('Tên đăng nhập admin: ').strip().lower();password=getpass.getpass('Mật khẩu (ít nhất 10 ký tự): ')
    if not re.fullmatch(r'[a-z0-9_.-]{3,40}',username) or not 10<=len(password)<=128:raise SystemExit('Tên đăng nhập hoặc mật khẩu không đạt yêu cầu.')
    if password!=getpass.getpass('Nhập lại mật khẩu: '):raise SystemExit('Mật khẩu không trùng khớp.')
    with connection(path) as db:
        if db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():raise SystemExit('Tài khoản đã tồn tại; không tự động đổi quyền hay mật khẩu.')
        db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(username,password_hash(password),'admin'))
    print('Đã tạo tài khoản quản trị.')
if __name__=='__main__':main()
