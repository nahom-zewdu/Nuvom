# nuvom/serialization/msgpack_serializer.py

import msgpack
from nuvom.serialization.base import Serializer

class MsgpackSerializer(Serializer):
    def serialize(self, obj: object) -> bytes:
        return msgpack.packb(obj, use_bin_type=True)

    def deserialize(self, data: bytes) -> object:
        return msgpack.unpackb(data, raw=False, strict_map_key=False)
