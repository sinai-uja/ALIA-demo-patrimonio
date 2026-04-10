"""Asset ID value object helpers (pure domain, no infrastructure)."""
import re

_PREFIX_RE = re.compile(r"^ficha-\w+-")


def extract_asset_id(document_id: str) -> str:
    """Extract the numeric heritage asset ID from a chunk document_id.

    Chunk document_ids use the format 'ficha-{type}-{number}' while
    heritage_assets.id stores just the numeric part.
    """
    return _PREFIX_RE.sub("", document_id)
