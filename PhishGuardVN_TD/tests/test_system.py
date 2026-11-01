import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from phishguard.api import create_app
from phishguard.database import connection
from phishguard.security import password_hash
from phishguard.features import extract_urls,normalize_url,domain_group,feature_frame,infrastructure_features
from phishguard.engine import Engine
from phishguard.infrastructure import snapshot_from_rdap
from phishguard.fusion import tune_reviewed_validation

@pytest.fixture(scope='session')
def engine():return Engine(Path(__file__).resolve().parents[1]/'models')

@pytest.fixture()
def clients(tmp_path,engine):
    path=tmp_path/'test.db';app=create_app(path,engine)
    with connection(path) as db:
        hashed=password_hash('TestingOnly!2026')
        for name,role in [('member1','user'),('member2','user'),('admin1','admin')]:db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,hashed,role))
    result=[]
    for name in ['member1','member2','admin1']:
        c=TestClient(app);r=c.post('/api/auth/login',json={'username':name,'password':'TestingOnly!2026'});assert r.status_code==200
        c.headers['X-CSRF-Token']=r.json()['csrf'];result.append(c)
    return (*result,path,app)

def payload():return {'target_type':'phone','target':'0901234567','description':'Báo cáo kiểm thử về cuộc gọi yêu cầu chuyển tiền.'}

def test_extract_and_canonicalization():
    urls=extract_urls('Xem hxxps://example[.]com/A?Q=Yes và www.example.org, hoặc https://example.com/A?Q=Yes.')
    assert len(urls)==2
    assert normalize_url('HTTPS://EXAMPLE.COM/A?Q=Yes')=='https://example.com/A?Q=Yes'
    assert normalize_url('https://example.com/A')!=normalize_url('https://example.com/a')
    assert domain_group('https://a.bank.com.vn')==domain_group('https://b.bank.com.vn')=='bank.com.vn'
    assert domain_group('https://one.blogspot.com')!=domain_group('https://two.blogspot.com')
    with pytest.raises(ValueError):normalize_url('javascript://alert.com')
    assert np.isfinite(feature_frame(['https://example.com']).values).all()

def test_infrastructure_missing_and_time():
    assert infrastructure_features('https://example.com')['domain_age_days_missing']==1
    snap=snapshot_from_rdap('https://example.com',{'events':[{'eventAction':'registration','eventDate':'2020-01-01T00:00:00Z'}]},['93.184.215.14'],None,'2026-01-01T00:00:00Z')
    assert infrastructure_features('https://example.com',snap,'2025-01-01T00:00:00Z')['domain_age_days_missing']==1
    assert infrastructure_features('https://example.com',snap,'2026-01-02T00:00:00Z')['domain_age_days']>2000
    assert infrastructure_features('https://example.com',snap)['tls_valid_missing']==1

def test_real_pipeline_and_shap(engine):
    text=engine.analyze('Xin chào, hẹn bạn ngày mai.');assert text['mode']=='text_only_proxy' and text['p_url_phishing'] is None
    url=engine.analyze('', ['https://example.com','https://example.org/login']);assert url['mode']=='url_only'
    assert url['p_url_phishing']==max(x['p_phishing'] for x in url['urls'])
    for r in url['urls']:
        assert r['shap']['additivity_residual']<1e-4
        shap=r['shap'];p=1/(1+np.exp(-(shap['base_value']+sum(shap['all_contributions'].values()))))
        assert abs(p-r['p_phishing'])<1e-5
    mixed=engine.analyze('Vui lòng đăng nhập: https://example.com/login');assert mixed['mode']=='fusion_proxy'
    assert abs(mixed['risk_score']-(mixed['alpha']*mixed['p_text_spam_scam']+(1-mixed['alpha'])*mixed['p_url_phishing']))<1e-8
    assert engine.analyze('https://example.com')['mode']=='url_only'
    with pytest.raises(ValueError):engine.analyze('')
    with pytest.raises(ValueError):engine.analyze('',[f'https://example.com/{x}' for x in range(21)])

def test_ownership_moderation_lookup(clients):
    a,b,admin,path,app=clients
    rid=a.post('/api/reports',json=payload()).json()['id']
    assert b.put(f'/api/reports/{rid}',json={**payload(),'version':1}).status_code==404
    assert b.delete(f'/api/reports/{rid}').status_code==404
    lookup='/api/lookup?target_type=phone&q=%2B84901234567'
    assert b.get(lookup).json()['approved_reports']==0
    assert a.post('/api/reports',json=payload()).status_code==409
    assert a.post(f'/api/admin/reports/{rid}/moderate',json={'status':'approved','note':'checked','version':1}).status_code==403
    assert admin.post(f'/api/admin/reports/{rid}/moderate',json={'status':'approved','note':'Đã rà soát','version':1}).status_code==200
    assert b.get(lookup).json()['unique_reporters']==1
    assert a.put(f'/api/reports/{rid}',json={**payload(),'version':1}).status_code==409
    assert a.put(f'/api/reports/{rid}',json={**payload(),'description':'Nội dung đã cập nhật để rà soát lại.','version':2}).status_code==200
    assert b.get(lookup).json()['approved_reports']==0
    assert admin.post(f'/api/admin/reports/{rid}/moderate',json={'status':'approved','note':'reviewed','version':2}).status_code==409
    assert admin.post(f'/api/admin/reports/{rid}/moderate',json={'status':'approved','note':'reviewed','version':3}).status_code==200
    r2=b.post('/api/reports',json=payload()).json()['id']
    admin.post(f'/api/admin/reports/{r2}/moderate',json={'status':'approved','note':'reviewed','version':1})
    assert a.get(lookup).json()['unique_reporters']==2
    assert admin.delete(f'/api/admin/reports/{rid}').status_code==200
    assert a.get(lookup).json()['approved_reports']==1
    assert b.delete(f'/api/reports/{r2}').status_code==200
    assert a.get(lookup).json()['approved_reports']==0

def test_csrf_rbac_sessions_and_schema(clients):
    a,b,admin,path,app=clients
    anon=TestClient(app)
    assert anon.get('/api/reports').status_code==401
    token=a.headers.pop('X-CSRF-Token');assert a.post('/api/reports',json=payload()).status_code==403;a.headers['X-CSRF-Token']=token
    assert a.get('/api/admin/users').status_code==403
    assert anon.post('/api/auth/register',json={'username':'injected','password':'TestingOnly!2026','role':'admin'}).status_code==422
    assert admin.patch('/api/admin/users/3',json={'active':False,'role':'user'}).status_code==400
    assert admin.patch('/api/admin/users/2',json={'active':False,'role':'user'}).status_code==200
    assert b.get('/api/auth/me').status_code==401
    assert b.post('/api/auth/login',json={'username':'member2','password':'TestingOnly!2026'}).status_code==401
    assert a.post('/api/auth/logout',json={}).status_code==200
    assert a.get('/api/auth/me').status_code==401

def test_history_stats_privacy_and_validation(clients):
    a,b,admin,path,app=clients
    r=a.post('/api/checks',json={'text':'Xin chào bạn.','urls':[]});assert r.status_code==200;cid=r.json()['id']
    assert b.get(f'/api/checks/{cid}').status_code==404
    assert b.delete(f'/api/checks/{cid}').status_code==404
    assert a.get('/api/stats').json()['totals']['checks']==1
    assert b.get('/api/stats').json()['totals']['checks']==0
    for period in ['day','week','month']:assert admin.get('/api/admin/stats?period='+period).json()['totals']['checks']==1
    assert a.post('/api/checks',json={'text':''}).status_code==422
    assert a.post('/api/checks',json={'urls':['file:///etc/passwd']}).status_code==422
    assert a.post('/api/checks',json={'text':'a'*6001}).status_code==422
    assert a.delete(f'/api/checks/{cid}').status_code==200
    assert a.get('/api/checks').json()['total']==0
    assert a.get('/').headers['x-content-type-options']=='nosniff'

def test_password_change_revokes_session(clients):
    a,b,admin,path,app=clients
    assert a.post('/api/auth/password',json={'current_password':'WrongPassword','new_password':'NewTestingOnly!2026'}).status_code==400
    assert a.post('/api/auth/password',json={'current_password':'TestingOnly!2026','new_password':'NewTestingOnly!2026'}).status_code==200
    assert a.get('/api/auth/me').status_code==401
    assert a.post('/api/auth/login',json={'username':'member1','password':'NewTestingOnly!2026'}).status_code==200

def test_fusion_rejects_test_and_unreviewed(tmp_path):
    df=pd.DataFrame({'sample_id':['a','b'],'split':['test','test'],'y_phishing':[0,1],'p_text':[.2,.8],'p_url':[.3,.9],'has_url':[1,1],'label_status':['human_reviewed']*2});p=tmp_path/'v.csv';df.to_csv(p,index=False)
    with pytest.raises(ValueError):tune_reviewed_validation(p,tmp_path/'x.json')
    df['split']='validation';df['label_status']='weak';df.to_csv(p,index=False)
    with pytest.raises(ValueError):tune_reviewed_validation(p,tmp_path/'x.json')
    df['label_status']='human_reviewed';df.to_csv(p,index=False)
    assert tune_reviewed_validation(p,tmp_path/'x.json')['test_used'] is False

def test_training_metadata_and_leakage():
    root=Path(__file__).resolve().parents[1];m=json.loads((root/'models/manifest.json').read_text())
    assert m['source_label_mapping']['PhiUSIIL_0']=='Phishing' and m['test_evaluated'] is False
    df=pd.read_csv(root/'data/url_split_manifest.csv.gz');groups=[set(df.loc[df.split==s,'domain_group']) for s in ['train','validation','test']]
    assert not(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])
    assert (df.y_phishing==1-df.label).all()
    s=pd.read_csv(root/'data/social_engineering_700_v2.csv');assert len(s)==700
    for a,b in [('train','validation'),('train','test'),('validation','test')]:assert not set(s.loc[s.split==a,'group'])&set(s.loc[s.split==b,'group'])
