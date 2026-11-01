import sqlite3
from contextlib import contextmanager
from pathlib import Path
SCHEMA='''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('user','admin')), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),csrf TEXT NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),target_type TEXT NOT NULL CHECK(target_type IN ('phone','url')),target TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),admin_note TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,deleted INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')),updated_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE UNIQUE INDEX IF NOT EXISTS one_report_per_user_target ON reports(user_id,target_type,target) WHERE deleted=0;
CREATE INDEX IF NOT EXISTS report_lookup ON reports(target_type,target,status,deleted);
CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),input_text TEXT NOT NULL,result_json TEXT NOT NULL,alert INTEGER NOT NULL,created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE INDEX IF NOT EXISTS check_user ON checks(user_id,created_at);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT NOT NULL,object_id INTEGER,detail TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')));
'''
@contextmanager
def connection(path):
    db=sqlite3.connect(str(path),timeout=15);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db;db.commit()
    except BaseException:
        db.rollback();raise
    finally:db.close()

def initialize(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with connection(path) as db:db.execute('PRAGMA journal_mode=WAL');db.executescript(SCHEMA)
