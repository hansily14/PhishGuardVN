"""Local API inference benchmark for Week 11. Uses a disposable SQLite DB."""
import json
import statistics
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient
from phishguard.api import create_app
from phishguard.database import connection
from phishguard.engine import Engine
from phishguard.security import password_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='phishguard_week11_') as tmp:
        db_path = Path(tmp) / 'benchmark.db'
        engine = Engine(ROOT / 'models')
        app = create_app(db_path, engine)
        with connection(db_path) as db:
            db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',
                       ('benchmark_user', password_hash('BenchmarkOnly!2026'), 'user'))
        client = TestClient(app)
        login = client.post('/api/auth/login', json={'username':'benchmark_user','password':'BenchmarkOnly!2026'})
        login.raise_for_status()
        client.headers['X-CSRF-Token'] = login.json()['csrf']
        cases = {
            'text_only': {'text':'Thông báo: tài khoản của bạn cần được xác minh ngay. Vui lòng liên hệ tổng đài để được hỗ trợ.', 'urls':[]},
            'url_only': {'text':'', 'urls':['https://example.com/login']},
            'text_plus_url': {'text':'Vui lòng đăng nhập để xác minh tài khoản.', 'urls':['https://example.com/verify']},
        }
        result = {'benchmark':'PhishGuardVN Week 11 API end-to-end inference',
                  'environment_python':__import__('platform').python_version(),
                  'warmup_requests':1,'measured_requests_per_case':8,'cases':{}}
        for name, payload in cases.items():
            for _ in range(1):
                response = client.post('/api/checks', json=payload)
                response.raise_for_status()
            samples=[]
            for _ in range(8):
                started=time.perf_counter()
                response=client.post('/api/checks',json=payload)
                elapsed=(time.perf_counter()-started)*1000
                response.raise_for_status()
                samples.append(elapsed)
            ordered=sorted(samples)
            result['cases'][name] = {
                'n':len(samples),
                'mean_ms':round(statistics.mean(samples),3),
                'median_ms':round(statistics.median(samples),3),
                'p95_ms':round(ordered[min(len(ordered)-1, min(len(ordered)-1, int(__import__('math').ceil(0.95*len(ordered))-1)))],3),
                'min_ms':round(min(samples),3),
                'max_ms':round(max(samples),3),
            }
        out=ROOT/'reports'/'week11_benchmark.json'
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        print('Saved:',out)


if __name__ == '__main__':
    main()
