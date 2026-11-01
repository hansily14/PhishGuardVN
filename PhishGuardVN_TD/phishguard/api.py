"""FastAPI + SQLite demo, server-side authorization, ownership and CSRF checks."""
import json
import os
import re
import secrets
import sqlite3
import time
import threading
from collections import defaultdict, deque
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from .database import connection, initialize
from .security import password_hash, password_matches, token_hash, normalize_phone
from .features import normalize_url
from .engine import Engine
ROOT=Path(__file__).resolve().parents[1]

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Credentials(StrictModel):
    username:str=Field(min_length=3,max_length=40,pattern=r'^[a-zA-Z0-9_.-]+$')
    password:str=Field(min_length=10,max_length=128)
class CheckBody(StrictModel):
    text:str=Field(default='',max_length=6000)
    urls:list[str]=Field(default_factory=list,max_length=20)
class ReportBody(StrictModel):
    target_type:Literal['phone','url']
    target:str=Field(min_length=3,max_length=4096)
    description:str=Field(min_length=10,max_length=3000)
class ReportEdit(ReportBody):
    version:int=Field(ge=1)
class Moderation(StrictModel):
    status:Literal['approved','rejected']
    note:str=Field(min_length=3,max_length=500)
    version:int=Field(ge=1)
class UserUpdate(StrictModel):
    active:bool
    role:Literal['user','admin']
class PasswordChange(StrictModel):
    current_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=10,max_length=128)

def create_app(db_path=None,engine=None):
    app=FastAPI(title='PhishGuardVN AI Service',version='0.5.0')
    db_path=Path(db_path or os.getenv('PHISHGUARD_DB',str(ROOT/'instance'/'phishguard.db')));initialize(db_path)
    app.state.engine=engine;load_lock=threading.Lock();limit_lock=threading.Lock();buckets=defaultdict(deque)
    def rate(key,maximum,seconds):
        with limit_lock:
            now=time.time();q=buckets[key]
            while q and q[0]<now-seconds:q.popleft()
            if len(q)>=maximum:raise HTTPException(429,'Bạn thao tác quá nhanh. Vui lòng thử lại sau.')
            q.append(now)
            if len(buckets)>10000:
                for k in list(buckets):
                    if not buckets[k] or buckets[k][-1]<now-3600:del buckets[k]
    def ai():
        with load_lock:
            if app.state.engine is None:
                try:app.state.engine=Engine(ROOT/'models')
                except FileNotFoundError:raise HTTPException(503,'Chưa có mô hình. Chạy notebook huấn luyện trước.')
        return app.state.engine
    def audit(db,user,action,obj=None,detail=''):
        db.execute('INSERT INTO audit(user_id,action,object_id,detail) VALUES(?,?,?,?)',(user,action,obj,detail))
    def current(request:Request):
        token=request.cookies.get('pg_session','')
        with connection(db_path) as db:
            row=db.execute('SELECT u.id,u.username,u.role,u.active,s.csrf,s.token_hash FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(token_hash(token),time.time())).fetchone()
        if row is None or not row['active']:raise HTTPException(401,'Vui lòng đăng nhập.')
        if request.method not in ['GET','HEAD','OPTIONS'] and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),row['csrf']):raise HTTPException(403,'CSRF token không hợp lệ.')
        return dict(row)
    def admin(user=Depends(current)):
        if user['role']!='admin':raise HTTPException(403,'Chức năng dành cho quản trị viên.')
        return user
    def target(kind,value):
        try:return normalize_phone(value) if kind=='phone' else normalize_url(value)
        except (ValueError,UnicodeError) as e:raise HTTPException(422,str(e))
    def own_report(db,rid,user):
        row=db.execute('SELECT * FROM reports WHERE id=? AND deleted=0',(rid,)).fetchone()
        if row is None or row['user_id']!=user['id']:raise HTTPException(404,'Không tìm thấy báo cáo của bạn.')
        return row
    @app.middleware('http')
    async def security_headers(request:Request,call_next):
        length=request.headers.get('content-length')
        if length and (not length.isdigit() or int(length)>100000):return Response('Request too large',413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        return response
    @app.get('/')
    def index():return FileResponse(ROOT/'web'/'index.html')
    app.mount('/static',StaticFiles(directory=ROOT/'web'),name='static')
    @app.get('/api/health')
    def health():return {'status':'ok','model_files_ready':(ROOT/'models'/'manifest.json').exists(),'version':'0.5.0'}
    @app.post('/api/auth/register',status_code=201)
    def register(body:Credentials,request:Request):
        rate(('register',request.client.host),5,3600)
        try:
            with connection(db_path) as db:
                cur=db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(body.username.lower(),password_hash(body.password),'user'));audit(db,cur.lastrowid,'register')
        except sqlite3.IntegrityError:raise HTTPException(409,'Tên đăng nhập đã được sử dụng.')
        return {'message':'Tạo tài khoản thành công. Bạn có thể đăng nhập.'}
    @app.post('/api/auth/login')
    def login(body:Credentials,request:Request,response:Response):
        rate(('login_ip',request.client.host),30,600);rate(('login_user',body.username.lower()),10,600)
        with connection(db_path) as db:
            row=db.execute('SELECT * FROM users WHERE username=?',(body.username.lower(),)).fetchone()
            if row is None or not row['active'] or not password_matches(body.password,row['password_hash']):raise HTTPException(401,'Thông tin đăng nhập không hợp lệ hoặc tài khoản bị khóa.')
            token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires_at<?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token_hash(token),row['id'],csrf,time.time()+28800));audit(db,row['id'],'login')
        response.set_cookie('pg_session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE')=='1',max_age=28800,path='/')
        return {'id':row['id'],'username':row['username'],'role':row['role'],'csrf':csrf}
    @app.get('/api/auth/me')
    def me(user=Depends(current)):return {k:user[k] for k in ['id','username','role','csrf']}
    @app.post('/api/auth/logout')
    def logout(response:Response,user=Depends(current)):
        with connection(db_path) as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(user['token_hash'],))
        response.delete_cookie('pg_session');return {'message':'Đã đăng xuất.'}
    @app.post('/api/auth/password')
    def change_password(body:PasswordChange,user=Depends(current)):
        with connection(db_path) as db:
            row=db.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
            if not password_matches(body.current_password,row[0]):raise HTTPException(400,'Mật khẩu hiện tại chưa đúng.')
            db.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(body.new_password),user['id']))
            db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],));audit(db,user['id'],'password_changed')
        return {'message':'Đã đổi mật khẩu; vui lòng đăng nhập lại.'}
    @app.post('/api/checks')
    def check(body:CheckBody,user=Depends(current)):
        rate(('check',user['id']),30,60)
        try:
            model = ai()
            result = model.analyze(body.text, body.urls)
        except (ValueError,UnicodeError) as e:raise HTTPException(422,str(e))
        with connection(db_path) as db:
            cur=db.execute('INSERT INTO checks(user_id,input_text,result_json,alert) VALUES(?,?,?,?)',(user['id'],json.dumps(body.model_dump(),ensure_ascii=False),json.dumps(result,ensure_ascii=False),int(result['alert'])))
        return {'id':cur.lastrowid,**result}
    @app.get('/api/checks')
    def checks(offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),user=Depends(current)):
        with connection(db_path) as db:
            rows=db.execute('SELECT id,input_text,alert,created_at FROM checks WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?',(user['id'],limit,offset)).fetchall();total=db.execute('SELECT count(*) FROM checks WHERE user_id=?',(user['id'],)).fetchone()[0]
        return {'items':[dict(r) for r in rows],'total':total}
    @app.get('/api/checks/{cid}')
    def check_detail(cid:int,user=Depends(current)):
        with connection(db_path) as db:row=db.execute('SELECT * FROM checks WHERE id=? AND user_id=?',(cid,user['id'])).fetchone()
        if row is None:raise HTTPException(404,'Không tìm thấy lần kiểm tra.')
        return {'id':row['id'],'input':json.loads(row['input_text']),'result':json.loads(row['result_json'])}
    @app.delete('/api/checks/{cid}')
    def delete_check(cid:int,user=Depends(current)):
        with connection(db_path) as db:
            cur=db.execute('DELETE FROM checks WHERE id=? AND user_id=?',(cid,user['id']))
            if not cur.rowcount:raise HTTPException(404,'Không tìm thấy lần kiểm tra.')
        return {'message':'Đã xóa lịch sử kiểm tra.'}
    @app.post('/api/reports',status_code=201)
    def report(body:ReportBody,user=Depends(current)):
        rate(('report',user['id']),15,3600);normalized=target(body.target_type,body.target)
        try:
            with connection(db_path) as db:
                cur=db.execute('INSERT INTO reports(user_id,target_type,target,description) VALUES(?,?,?,?)',(user['id'],body.target_type,normalized,body.description.strip()));audit(db,user['id'],'report_created',cur.lastrowid)
        except sqlite3.IntegrityError:raise HTTPException(409,'Bạn đã báo cáo đối tượng này. Hãy chỉnh sửa báo cáo hiện có.')
        return {'id':cur.lastrowid,'status':'pending','version':1}
    @app.get('/api/reports')
    def my_reports(offset:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),user=Depends(current)):
        with connection(db_path) as db:
            rows=db.execute('SELECT * FROM reports WHERE user_id=? AND deleted=0 ORDER BY id DESC LIMIT ? OFFSET ?',(user['id'],limit,offset)).fetchall();total=db.execute('SELECT count(*) FROM reports WHERE user_id=? AND deleted=0',(user['id'],)).fetchone()[0]
        return {'items':[dict(r) for r in rows],'total':total}
    @app.put('/api/reports/{rid}')
    def edit_report(rid:int,body:ReportEdit,user=Depends(current)):
        normalized=target(body.target_type,body.target)
        try:
            with connection(db_path) as db:
                own_report(db,rid,user)
                cur=db.execute("UPDATE reports SET target_type=?,target=?,description=?,status='pending',admin_note='',version=version+1,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND version=?",(body.target_type,normalized,body.description.strip(),rid,body.version))
                if not cur.rowcount:raise HTTPException(409,'Báo cáo đã thay đổi. Tải lại trước khi sửa.')
                audit(db,user['id'],'report_edited_reset_pending',rid)
        except sqlite3.IntegrityError:raise HTTPException(409,'Đã có báo cáo của bạn cho đối tượng này.')
        return {'id':rid,'status':'pending','version':body.version+1}
    @app.delete('/api/reports/{rid}')
    def withdraw(rid:int,user=Depends(current)):
        with connection(db_path) as db:
            own_report(db,rid,user);db.execute('UPDATE reports SET deleted=1,version=version+1 WHERE id=?',(rid,));audit(db,user['id'],'report_withdrawn',rid)
        return {'message':'Đã rút báo cáo.'}
    @app.get('/api/lookup')
    def lookup(target_type:Literal['phone','url'],q:str=Query(min_length=3,max_length=4096),user=Depends(current)):
        rate(('lookup',user['id']),60,60);normalized=target(target_type,q)
        with connection(db_path) as db:
            row=db.execute("SELECT count(*) reports,count(DISTINCT user_id) reporters,max(updated_at) latest FROM reports WHERE target_type=? AND target=? AND status='approved' AND deleted=0",(target_type,normalized)).fetchone()
        return {'target':normalized,'approved_reports':row['reports'],'unique_reporters':row['reporters'],'last_approved_update':row['latest'],'notice':'Chỉ tính báo cáo đã được duyệt; đây là phản ánh cộng đồng, không phải kết luận pháp lý. Không có báo cáo không đồng nghĩa an toàn.'}
    @app.get('/api/admin/reports')
    def admin_reports(status:Literal['all','pending','approved','rejected']='all',offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),user=Depends(admin)):
        where='r.deleted=0';args=[]
        if status!='all':where+=' AND r.status=?';args.append(status)
        with connection(db_path) as db:
            rows=db.execute(f'SELECT r.*,u.username FROM reports r JOIN users u ON u.id=r.user_id WHERE {where} ORDER BY r.id DESC LIMIT ? OFFSET ?',[*args,limit,offset]).fetchall();total=db.execute(f'SELECT count(*) FROM reports r WHERE {where}',args).fetchone()[0]
        return {'items':[dict(r) for r in rows],'total':total}
    @app.post('/api/admin/reports/{rid}/moderate')
    def moderate(rid:int,body:Moderation,user=Depends(admin)):
        with connection(db_path) as db:
            cur=db.execute("UPDATE reports SET status=?,admin_note=?,version=version+1,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND deleted=0 AND version=?",(body.status,body.note,rid,body.version))
            if not cur.rowcount:raise HTTPException(409,'Báo cáo đã thay đổi hoặc bị xóa. Tải lại trước khi duyệt.')
            audit(db,user['id'],'report_'+body.status,rid,body.note)
        return {'message':'Đã cập nhật trạng thái.'}
    @app.delete('/api/admin/reports/{rid}')
    def remove_report(rid:int,user=Depends(admin)):
        with connection(db_path) as db:
            cur=db.execute('UPDATE reports SET deleted=1,version=version+1 WHERE id=? AND deleted=0',(rid,))
            if not cur.rowcount:raise HTTPException(404,'Không tìm thấy báo cáo.')
            audit(db,user['id'],'admin_report_deleted',rid)
        return {'message':'Đã xóa báo cáo khỏi danh sách và tra cứu cộng đồng.'}
    @app.get('/api/admin/users')
    def users(offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),user=Depends(admin)):
        with connection(db_path) as db:
            rows=db.execute('SELECT id,username,role,active,created_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall();total=db.execute('SELECT count(*) FROM users').fetchone()[0]
        return {'items':[dict(r) for r in rows],'total':total}
    @app.patch('/api/admin/users/{uid}')
    def update_user(uid:int,body:UserUpdate,user=Depends(admin)):
        if uid==user['id']:raise HTTPException(400,'Không tự khóa hoặc thay đổi vai trò của chính mình.')
        with connection(db_path) as db:
            cur=db.execute('UPDATE users SET active=?,role=? WHERE id=?',(int(body.active),body.role,uid))
            if not cur.rowcount:raise HTTPException(404,'Không tìm thấy tài khoản.')
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(db,user['id'],'user_updated',uid,json.dumps(body.model_dump()))
        return {'message':'Đã cập nhật tài khoản và thu hồi các phiên đăng nhập cũ.'}
    def statistics(uid,period):
        fmt={'day':'%Y-%m-%d','week':'%Y-W%W','month':'%Y-%m'}[period]
        clause='' if uid is None else ' AND user_id=?';args=[] if uid is None else [uid]
        cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).isoformat()
        with connection(db_path) as db:
            totals={'checks':db.execute('SELECT count(*) FROM checks WHERE 1=1'+clause,args).fetchone()[0],'alerts':db.execute('SELECT count(*) FROM checks WHERE alert=1'+clause,args).fetchone()[0],'reports':db.execute('SELECT count(*) FROM reports WHERE deleted=0'+clause,args).fetchone()[0],'pending':db.execute("SELECT count(*) FROM reports WHERE deleted=0 AND status='pending'"+clause,args).fetchone()[0]}
            check_series=db.execute(f"SELECT strftime('{fmt}',created_at,'+7 hours') bucket,count(*) total,sum(alert) alerts FROM checks WHERE created_at>=?{clause} GROUP BY bucket ORDER BY bucket",[cutoff,*args]).fetchall()
            report_series=db.execute(f"SELECT strftime('{fmt}',created_at,'+7 hours') bucket,count(*) total,sum(status='approved') approved FROM reports WHERE deleted=0 AND created_at>=?{clause} GROUP BY bucket ORDER BY bucket",[cutoff,*args]).fetchall()
        return {'totals':totals,'checks':[dict(x) for x in check_series],'reports':[dict(x) for x in report_series],'period':period,'timezone':'Asia/Ho_Chi_Minh','range_days':365,'week_definition':'Monday-based SQLite %W (week 00 possible)'}
    @app.get('/api/stats')
    def stats(period:Literal['day','week','month']='day',user=Depends(current)):return statistics(user['id'],period)
    @app.get('/api/admin/stats')
    def admin_stats(period:Literal['day','week','month']='day',user=Depends(admin)):return statistics(None,period)
    @app.get('/api/admin/audit')
    def audit_log(user=Depends(admin)):
        with connection(db_path) as db:rows=db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100').fetchall()
        return {'items':[dict(x) for x in rows]}
    @app.get('/api/model-info')
    def model_info(user=Depends(current)):
        model=ai();return {'url_selected':model.manifest['url_selected'],'text_model':model.manifest['text_model'],'fusion':model.manifest['fusion'],'infrastructure_model_used':False,'social_engineering_labels':'weak_rules_v2_unreviewed'}
    return app

app=create_app()
