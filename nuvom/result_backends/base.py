# nuvom/result_backends/base.py
# Define an interface (i.e., base class) that all backends must follow.

from abc import ABC, abstractmethod

class BaseResultBackend(ABC):
    @abstractmethod
    def set_result(self, job_id: str, result: object):
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> object:
        pass

    @abstractmethod
    def set_error(self, job_id: str, error: str):
        pass

    @abstractmethod
    def get_error(self, job_id: str) -> str:
        pass
