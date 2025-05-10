# nuvom/serialize.py

# Handles serialization and deserialization
# Starts with msgpack, swappable to protobuf, etc.

from nuvom.serialization.msgpack_serializer import MsgpackSerializer
from nuvom.config import get_settings

_serializer = None

def get_serializer():
    global _serializer
    if _serializer is not None:
        return _serializer

    backend = get_settings().serialization_backend.lower()
    if backend == "msgpack":
        _serializer = MsgpackSerializer()
    else:
        raise ValueError(f"Unsupported serialization backend: {backend}")
    return _serializer


def serialize(obj: object) -> bytes:
    return get_serializer().serialize(obj=obj)

def deserialize(data: bytes) -> object:
    return get_serializer().deserialize(data)

