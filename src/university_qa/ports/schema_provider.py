from abc import ABC, abstractmethod

from university_qa.domain.types import SchemaDescription


class SchemaProvider(ABC):
    @abstractmethod
    def describe(self) -> SchemaDescription: ...
