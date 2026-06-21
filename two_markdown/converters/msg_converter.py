from __future__ import annotations

from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.errors import MissingDependencyError
from two_markdown.models import ConvertedDocument


class MsgConverter:
    name = "msg"
    extensions = {".msg"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            import extract_msg  # type: ignore
        except Exception as exc:
            raise MissingDependencyError("extract-msg", "MSG email conversion") from exc

        warnings: list[str] = []
        try:
            message = extract_msg.openMsg(str(path))
        except Exception as exc:
            raise MissingDependencyError("extract-msg", "MSG email conversion") from exc

        try:
            metadata = _msg_metadata(message, context)
            subject = metadata.get("title") or path.stem
            body_md = _msg_body(message, warnings)
            attachment_md = _msg_attachments(message, context, warnings)

            parts = [f"# {subject}", body_md]
            if attachment_md:
                parts.append("**Attachments:**\n")
                parts.extend(attachment_md)
            return ConvertedDocument(
                title=subject,
                markdown="\n\n".join(part for part in parts if part),
                converter=self.name,
                attachments=context.attachments,
                warnings=warnings,
                metadata=metadata,
            )
        finally:
            close = getattr(message, "close", None)
            if callable(close):
                close()


def _msg_metadata(message: object, context: ConversionContext) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if not context.options.include_metadata:
        return metadata
    fields = {
        "sender": "from",
        "to": "to",
        "cc": "cc",
        "subject": "title",
        "date": "date",
    }
    for attr, key in fields.items():
        value = getattr(message, attr, None)
        if value and str(value).strip():
            metadata[key] = str(value).strip()
    return metadata


def _msg_body(message: object, warnings: list[str]) -> str:
    html = getattr(message, "htmlBody", None)
    if html:
        try:
            from two_markdown.converters.html_converter import _to_markdown

            return _to_markdown(_decode(html)).strip()
        except Exception as exc:
            warnings.append(f"Could not render MSG HTML body: {exc}")
    body = getattr(message, "body", None)
    if body:
        return _decode(body)
    return "_No readable body._"


def _msg_attachments(message: object, context: ConversionContext, warnings: list[str]) -> list[str]:
    links: list[str] = []
    attachments = getattr(message, "attachments", []) or []
    if not context.options.extract_attachments:
        return links
    for attachment in attachments:
        filename = getattr(attachment, "longFilename", None) or getattr(attachment, "shortFilename", None) or "attachment"
        data = getattr(attachment, "data", None)
        if data is None:
            continue
        if isinstance(data, str):
            data = data.encode("utf-8", errors="replace")
        try:
            links.append(f"- {context.add_attachment(filename, data, alt_text=filename)}")
        except Exception as exc:
            warnings.append(f"Could not extract MSG attachment {filename}: {exc}")
    return links


def _decode(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
