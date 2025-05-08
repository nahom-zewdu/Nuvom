# nuvom/serialization.py

import pickle

def dumps(obj) -> bytes:
    return pickle.dumps(obj)

def loads(data: bytes):
    return pickle.loads(data)
