import sqlite3
import pytest


def test_cache_closes_connections_after_each_operation(tmp_path,monkeypatch):
    from src.llm.cache import Cache
    original=sqlite3.connect;connections=[]
    def connect(*args,**kwargs):
        db=original(*args,**kwargs);connections.append(db);return db
    monkeypatch.setattr('src.llm.cache.sqlite3.connect',connect)
    cache=Cache(tmp_path/'cache.sqlite3');cache.put('key',{'value':1})
    assert cache.get('key')=={'value':1}
    for db in connections:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):db.execute('SELECT 1')
