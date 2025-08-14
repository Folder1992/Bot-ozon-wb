import time, secrets

class EphemeralStore:
    def __init__(self, ttl=3600):
        self.ttl = ttl
        self._data = {}
    def put(self, payload):
        key = secrets.token_urlsafe(8)
        self._data[key] = (time.time()+self.ttl, payload)
        return key
    def get(self, key):
        row = self._data.get(key)
        if not row: return None
        exp, payload = row
        if exp < time.time():
            self._data.pop(key, None)
            return None
        return payload
STORE = EphemeralStore(ttl=3600)
