# nuvom/serialization/base.py

"""
Defines the abstract base class for serialization backends.

All serializer implementations must inherit from this class and implement the
`serialize` and `deserialize` methods to handle object ↔ bytes conversion.
"""

from abc import ABC, abstractmethod


class Serializer(ABC):
    """
    Abstract base class for all serialization strategies.

    Any custom serializer (e.g., using JSON, MsgPack, or Pickle) must subclass this
    and implement the required methods.

    Methods:
        serialize(obj): Convert a Python object into bytes.
        deserialize(data): Convert bytes back into a Python object.
    """

    @abstractmethod
    def serialize(self, obj: object) -> bytes:
        """
        Serialize a Python object into bytes.

        Args:
            obj (object): The Python object to serialize.

        Returns:
            bytes: The serialized byte representation of the object.
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> object:
        """
        Deserialize bytes back into a Python object.

        Args:
            data (bytes): Byte representation of a serialized object.

        Returns:
            object: The deserialized Python object.
        """
        pass
