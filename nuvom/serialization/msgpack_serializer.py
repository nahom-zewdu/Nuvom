# nuvom/serialization/msgpack_serializer.py

"""
MsgPack-based implementation of the Serializer interface.

This serializer uses the `msgpack` format for compact, fast binary serialization.
It supports complex Python data structures and is more efficient than JSON
for many use cases.
"""

import msgpack
from nuvom.serialization.base import Serializer


class MsgpackSerializer(Serializer):
    """
    Serializer implementation using the MessagePack format.

    MessagePack offers compact binary representation of data, making it suitable
    for queue-based systems where performance and storage efficiency matter.

    Methods:
        serialize(obj): Serializes an object into MessagePack bytes.
        deserialize(data): Deserializes MessagePack bytes back into a Python object.
    """

    def serialize(self, obj: object) -> bytes:
        """
        Serialize a Python object into MessagePack-formatted bytes.

        Args:
            obj (object): The Python object to serialize.

        Returns:
            bytes: MessagePack-encoded byte representation of the object.
        """
        return msgpack.packb(obj, use_bin_type=True)

    def deserialize(self, data: bytes) -> object:
        """
        Deserialize MessagePack-encoded bytes back into a Python object.

        Args:
            data (bytes): The byte data to deserialize.

        Returns:
            object: The original Python object reconstructed from the bytes.
        """
        return msgpack.unpackb(data, raw=False, strict_map_key=False)
