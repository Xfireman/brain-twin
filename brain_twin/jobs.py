"""Bounded, in-memory jobs. Questions/results are not persisted or exported."""
import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from .twin import new_id


class Jobs:
    def __init__(self, workers=2, capacity=4, retained=64, ttl=900):
        self.executor=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='twin')
        self.slots=threading.BoundedSemaphore(capacity)
        self.lock=threading.Lock()
        self.entries={}
        self.retained,self.ttl=retained,ttl

    def _prune(self):
        now=time.monotonic()
        for key in list(self.entries):
            entry=self.entries[key]
            if entry['status'] in ('succeeded','failed') and now-entry['_time']>self.ttl:
                del self.entries[key]
        while len(self.entries)>=self.retained:
            done=next((key for key,item in self.entries.items() if item['status'] in ('succeeded','failed')),None)
            if done is None:
                raise RuntimeError('Task queue is full; wait for a running task')
            del self.entries[done]

    def submit(self, fn):
        if not self.slots.acquire(blocking=False):
            raise RuntimeError('Task queue is full; wait for a running task')
        try:
            with self.lock:
                self._prune()
                key=new_id()
                self.entries[key]={'task_id':key,'status':'queued','_time':time.monotonic()}
            self.executor.submit(self._run,key,fn)
            return key
        except Exception:
            self.slots.release()
            raise

    def _run(self,key,fn):
        with self.lock:
            self.entries[key]['status']='running'
        try:
            result=fn()
            with self.lock:
                self.entries[key].update(status='succeeded',result=result,_time=time.monotonic())
        except (ValueError,RuntimeError) as exc:
            with self.lock:
                self.entries[key].update(status='failed',error=str(exc),_time=time.monotonic())
        except Exception:
            with self.lock:
                self.entries[key].update(status='failed',error='Task failed unexpectedly; retry after checking local data',_time=time.monotonic())
        finally:
            self.slots.release()

    def get(self,key):
        with self.lock:
            entry=self.entries.get(key)
            if entry is None or (entry['status'] in ('succeeded','failed') and time.monotonic()-entry['_time']>self.ttl):
                self.entries.pop(key,None)
                raise KeyError(key)
            return copy.deepcopy({k:v for k,v in entry.items() if not k.startswith('_')})
