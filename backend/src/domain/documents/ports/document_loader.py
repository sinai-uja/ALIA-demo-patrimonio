from abc import ABC, abstractmethod
from collections.abc import Iterator

from src.domain.documents.entities.document import Document
from src.domain.documents.value_objects.heritage_type import HeritageType


class DocumentLoader(ABC):
    """Port for loading heritage documents from an external source."""

    @abstractmethod
    def load_documents(
        self, source_path: str, heritage_type: HeritageType
    ) -> Iterator[Document]: ...
