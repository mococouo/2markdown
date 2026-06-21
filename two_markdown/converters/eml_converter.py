from __future__ import annotations

import email
from email import policy
from email.parser import BytesParser
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument


class EmlConverter:
    name = "eml"
    extensions = {".eml"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        data = path.read_bytes()
        message = BytesParser(policy=policy.default).parsebytes(data)
        warnings: list[str] = []
        metadata = _headers_to_metadata(message, context)
        subject = metadata.get("title") or path.stem

        body_md, attachments_md = _walk_message(message, context, warnings)
        parts = [f"# {subject}"]
        parts.append(body_md)
        if attachments_md:
            parts.append("**Attachments:**\n")
            parts.extend(attachments_md)

        return ConvertedDocument(
            title=subject,
            markdown="\n\n".join(part for part in parts if part),
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
            metadata=metadata,
        )


def _headers_to_metadata(message: object, context: ConversionContext) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if not context.options.include_metadata:
        return metadata
    fields = {
        "subject": "title",
        "from": "from",
        "to": "to",
        "cc": "cc",
        "date": "date",
        "message-id": "message_id",
    }
    for raw, key in fields.items():
        value = message.get(raw)  # type: ignore[attr-defined]
        if value and str(value).strip():
            metadata[key] = str(value).strip()
    return metadata


def _walk_message(message: object, context: ConversionContext, warnings: list[str]) -> tuple[str, list[str]]:
    if message.is_multipart():  # type: ignore[attr-defined]
        text_parts: list[str] = []
        attachment_links: list[str] = []
        for part in message.iter_parts():  # type: ignore[attr-defined]
            if part.is_multipart():
                sub_md, sub_links = _walk_message(part, context, warnings)
                if sub_md:
                    text_parts.append(sub_md)
                attachment_links.extend(sub_links)
                continue
            content = _part_content(part, context, warnings, attachment_links)
            if content:
                text_parts.append(content)
        return "\n\n".join(text_parts), attachment_links
    return _part_content(message, context, warnings, []), []


def _part_content(
    part: object,
    context: ConversionContext,
    warnings: list[str],
    attachment_links: list[str],
) -> str:
    content_type = part.get_content_type()  # type: ignore[attr-defined]
    disposition = (part.get_content_disposition() or "").lower()  # type: ignore[attr-defined]
    filename = part.get_filename()  # type: ignore[attr-defined]

    if disposition == "attachment" or (filename and content_type not in {"text/plain", "text/html"}):
        if filename and context.options.extract_attachments:
            try:
                payload = part.get_payload(decode=True) or b""  # type: ignore[attr-defined]
                token = context.add_attachment(filename, payload, alt_text=filename)
                attachment_links.append(f"- {token}")
            except Exception as exc:
                warnings.append(f"Could not extract email attachment {filename}: {exc}")
        return ""

    if content_type == "text/plain":
        try:
            return _text_body(part)
        except Exception as exc:
            warnings.append(f"Could not read email text body: {exc}")
            return ""
    if content_type == "text/html":
        try:
            html = _text_body(part)
            from two_markdown.converters.html_converter import _to_markdown

            return _to_markdown(html).strip()
        except Exception as exc:
            warnings.append(f"Could not read email HTML body: {exc}")
            return ""
    return ""


def _text_body(part: object) -> str:
    payload = part.get_content()  # type: ignore[attr-defined]
    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="replace")
    return str(payload)
