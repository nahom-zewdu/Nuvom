# nuvom/serialization/base.py
# # Define an interface (i.e., base class) that all serializers must follow.

from abc import ABC, abstractmethod

class Serializer(ABC):
    @abstractmethod
    def serialize(self, obj: object) -> bytes:
        """
        Convert an object to bytes.
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> object:
        """
        Convert bytes back to object.
        """
        pass
