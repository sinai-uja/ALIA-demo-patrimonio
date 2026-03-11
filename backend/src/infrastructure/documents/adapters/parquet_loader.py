from collections.abc import Iterator

import pandas as pd

from src.domain.documents.entities.document import Document
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.value_objects.heritage_type import HeritageType

# Columns that map directly to Document entity fields
_ENTITY_COLUMNS = {"id", "url", "title", "province", "municipality", "text"}


class ParquetDocumentLoader(DocumentLoader):
    """Loads heritage documents from parquet files using pandas + pyarrow."""

    def load_documents(
        self, source_path: str, heritage_type: HeritageType
    ) -> Iterator[Document]:
        df = pd.read_parquet(source_path, engine="pyarrow")

        for _, row in df.iterrows():
            row_dict = row.to_dict()

            # Extract entity fields
            doc_id = str(row_dict.get("id", ""))
            url = str(row_dict.get("url", ""))
            title = str(row_dict.get("title", ""))
            province = str(row_dict.get("province", ""))
            text = str(row_dict.get("text", ""))
            municipality = row_dict.get("municipality")
            if municipality is not None:
                municipality = str(municipality)

            # Remaining columns go into metadata
            metadata = {
                k: v for k, v in row_dict.items() if k not in _ENTITY_COLUMNS
            }

            yield Document(
                id=doc_id,
                url=url,
                title=title,
                province=province,
                heritage_type=heritage_type,
                text=text,
                municipality=municipality,
                metadata=metadata,
            )
