from __future__ import annotations

import json
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument


class IpynbConverter:
    name = "ipynb"
    extensions = {".ipynb"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise _conversion_error(exc)
        warnings: list[str] = []
        metadata = _notebook_metadata(notebook) if context.options.include_metadata else {}
        parts = [f"# {path.stem}"]

        cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
        for index, cell in enumerate(cells, start=1):
            if not isinstance(cell, dict):
                continue
            cell_md = _cell_to_markdown(cell, index, context, warnings)
            if cell_md:
                parts.append(cell_md)

        if not cells:
            warnings.append("Notebook has no cells.")

        return ConvertedDocument(
            title=metadata.get("title") or path.stem,
            markdown="\n\n".join(parts),
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
            metadata=metadata,
        )


def _cell_to_markdown(cell: dict, index: int, context: ConversionContext, warnings: list[str]) -> str:
    cell_type = cell.get("cell_type")
    source = cell.get("source", "")
    if isinstance(source, list):
        source = "".join(source)
    if cell_type == "markdown":
        return source
    if cell_type == "code":
        section = [f"```python\n{source}\n```"]
        for output in cell.get("outputs", []) or []:
            rendered = _output_to_markdown(output, context, warnings, index)
            if rendered:
                section.append(rendered)
        return "\n\n".join(section)
    if cell_type == "raw":
        return source
    return ""


def _output_to_markdown(output: dict, context: ConversionContext, warnings: list[str], cell_index: int) -> str:
    output_type = output.get("output_type")
    if output_type == "stream":
        text = output.get("text", "")
        if isinstance(text, list):
            text = "".join(text)
        return f"```\n{text}\n```"
    if output_type in {"execute_result", "display_data"}:
        data = output.get("data", {}) or {}
        if "image/png" in data:
            return _inline_png(data["image/png"], cell_index, context)
        if "text/plain" in data:
            text = data["text/plain"]
            if isinstance(text, list):
                text = "".join(text)
            return f"```\n{text}\n```"
        if "text/html" in data:
            from two_markdown.converters.html_converter import _to_markdown

            html = data["text/html"]
            if isinstance(html, list):
                html = "".join(html)
            return _to_markdown(html).strip()
    if output_type == "error":
        traceback = output.get("traceback", [])
        if isinstance(traceback, list):
            traceback = "\n".join(traceback)
        return f"```\n{traceback}\n```"
    return ""


def _inline_png(png_data, cell_index: int, context: ConversionContext) -> str:
    import base64

    if isinstance(png_data, list):
        png_data = "".join(png_data)
    try:
        raw = base64.b64decode(png_data)
    except Exception:
        return ""
    return context.add_attachment(f"cell-{cell_index}.png", raw, alt_text=f"cell {cell_index} output")


def _notebook_metadata(notebook: dict) -> dict[str, str]:
    metadata: dict[str, str] = {}
    nb_meta = notebook.get("metadata", {}) or {}
    kernel = nb_meta.get("kernelspec", {}) or {}
    language = kernel.get("language") or nb_meta.get("language_info", {}).get("name")
    if language:
        metadata["language"] = str(language)
    if kernel.get("name"):
        metadata["kernel"] = str(kernel["name"])
    title = nb_meta.get("title")
    if title:
        metadata["title"] = str(title)
    authors = nb_meta.get("authors", [])
    if isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict) and first.get("name"):
            metadata["author"] = str(first["name"])
    return metadata


def _conversion_error(exc: Exception):
    from two_markdown.errors import ConversionError

    return ConversionError(f"Could not read notebook: {exc}")
