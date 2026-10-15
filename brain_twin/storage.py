"""Single-process JSON storage: validate before replacing, never overwrite corruption."""
import copy
import json
import os
import tempfile
import threading
from pathlib import Path
from .twin import validate_profile


class Store:
    def __init__(self, directory):
        self.path = Path(directory).expanduser() / 'profiles.json'
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data,list) or len(data)>30:
                    raise ValueError('invalid profile list')
                self.profiles = [validate_profile(p) for p in data]
                if len({p['id'] for p in self.profiles}) != len(self.profiles):
                    raise ValueError('duplicate profile IDs')
            except (ValueError, OSError) as exc:
                raise RuntimeError('Cannot read profiles.json; restore or repair it before starting. Existing data was not replaced.') from exc
        else:
            example = json.loads(Path(__file__).with_name('example.json').read_text(encoding='utf-8'))
            self.profiles = [validate_profile(example)]
            self._write(self.profiles)

    def _write(self, profiles):
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.profiles-', suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:
                json.dump(profiles,handle,ensure_ascii=False,indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def all(self):
        with self.lock:
            return copy.deepcopy(self.profiles)

    def get(self, profile_id):
        with self.lock:
            for profile in self.profiles:
                if profile['id']==profile_id:
                    return copy.deepcopy(profile)
        raise KeyError(profile_id)

    def save(self, profile, create=False):
        profile = validate_profile(profile)
        with self.lock:
            exists = any(p['id']==profile['id'] for p in self.profiles)
            if create and exists:
                raise ValueError('profile ID already exists')
            if not create and not exists:
                raise KeyError(profile['id'])
            if create and len(self.profiles)>=30:
                raise ValueError('maximum 30 profiles; delete one before adding another')
            updated = [p for p in self.profiles if p['id']!=profile['id']] + [profile]
            self._write(updated)
            self.profiles = updated
            return copy.deepcopy(profile)

    def delete(self, profile_id):
        with self.lock:
            self.get(profile_id)
            updated = [p for p in self.profiles if p['id']!=profile_id]
            self._write(updated)
            self.profiles = updated
