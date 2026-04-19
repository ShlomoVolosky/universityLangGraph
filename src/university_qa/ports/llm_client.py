from abc import ABC, abstractmethod


class LlmClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str: ...
