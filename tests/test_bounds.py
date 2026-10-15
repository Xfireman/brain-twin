import json
import threading
import time
import pytest
from brain_twin.jobs import Jobs
from brain_twin.storage import Store
from brain_twin.twin import validate_profile
from test_app import bootstrap


def test_queue_rejects_excess_work_and_retention_is_bounded():
    jobs=Jobs(workers=1,capacity=1,retained=2)
    release=threading.Event()
    task=jobs.submit(lambda:release.wait(2))
    with pytest.raises(RuntimeError,match='full'):
        jobs.submit(lambda:None)
    release.set()
    for _ in range(100):
        if jobs.get(task)['status']=='succeeded':break
        time.sleep(.01)
    else:pytest.fail('first task did not finish')
    for _ in range(4):
        next_task=jobs.submit(lambda:'ok')
        for _ in range(100):
            if jobs.get(next_task)['status']=='succeeded':break
            time.sleep(.01)
    with pytest.raises(KeyError):jobs.get(task)
    assert len(jobs.entries)<=2
    jobs.executor.shutdown()


def test_expired_task_not_returned():
    jobs=Jobs(ttl=0)
    task=jobs.submit(lambda:'answer')
    jobs.executor.shutdown()
    with pytest.raises(KeyError):jobs.get(task)


def test_corrupt_storage_is_never_replaced(tmp_path):
    path=tmp_path/'profiles.json';path.write_text('broken json')
    with pytest.raises(RuntimeError,match='not replaced'):Store(tmp_path)
    assert path.read_text()=='broken json'


def test_unknown_fields_and_duplicate_sources_rejected():
    profile={'schema_version':1,'id':'p','name':'Name','sources':[{'id':'same','title':'A','text':'A'},{'id':'same','title':'B','text':'B'}]}
    with pytest.raises(ValueError,match='duplicate'):validate_profile(profile)
    profile['sources']=[];profile['api_key']='synthetic-not-a-real-key'
    with pytest.raises(ValueError,match='unexpected'):validate_profile(profile)


def test_atomic_store_persists_only_valid_profiles(tmp_path):
    store=Store(tmp_path);before=(tmp_path/'profiles.json').read_bytes()
    profile=store.all()[0];profile['sources'][0]['text']=''
    with pytest.raises(ValueError):store.save(profile)
    assert (tmp_path/'profiles.json').read_bytes()==before
    assert not list(tmp_path.glob('*.tmp'))
