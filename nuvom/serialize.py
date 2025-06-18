# nuvom/serialize.py

"""
Serialization abstraction layer for Nuvom.
Delegates to the selected backend (currently msgpack).
"""

from nuvom.serialization.msgpack_serializer import MsgpackSerializer
from nuvom.config import get_settings

_serializer = None


def get_serializer():
    """
    Lazily initializes and returns the global serializer backend.
    """
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
    """
    Serializes a Python object into bytes using the active backend.
    """
    return get_serializer().serialize(obj=obj)


def deserialize(data: bytes) -> object:
    """
    Deserializes bytes back into a Python object using the active backend.
    """
    return get_serializer().deserialize(data)
