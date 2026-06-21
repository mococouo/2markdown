from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import Attachment, ConversionOptions
from .utils import short_hash, slug_attachment_name

if TYPE_CHECKING:
    from .converters import ConverterRegistry


class ConversionContext:
    def __init__(
        self,
        source_path: Path,
        options: ConversionOptions,
        registry: "ConverterRegistry | None" = None,
    ) -> None:
        self.source_path = source_path
        self.options = options
        self.registry = registry
        self.attachments: list[Attachment] = []
        self._used_names: set[str] = set()

    def add_attachment(self, filename: str, data: bytes, alt_text: str = "attachment") -> str:
        safe_name = slug_attachment_name(filename)
        if safe_name in self._used_names:
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            safe_name = f"{stem}-{short_hash(data)}{suffix}"
        self._used_names.add(safe_name)
        self.attachments.append(Attachment(filename=safe_name, data=data))
        escaped_alt = alt_text.replace("[", "\\[").replace("]", "\\]")
        return f"![{escaped_alt}]({{{{attachment:{safe_name}}}}})"
