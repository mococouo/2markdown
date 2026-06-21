from __future__ import annotations

from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.errors import MissingDependencyError
from two_markdown.models import ConvertedDocument


class AudioVideoConverter:
    name = "audio-video"
    extensions = {
        ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga",
        ".mp4", ".mkv", ".mov", ".webm", ".avi",
    }

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:
            raise MissingDependencyError("faster-whisper", "Audio/video transcription") from exc

        warnings: list[str] = []
        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            language = context.options.audio_lang or None
            segments, _info = model.transcribe(str(path), language=language, vad_filter=True)
            parts = [f"# {path.stem}\n"]
            for segment in segments:
                start = _format_timestamp(segment.start)
                end = _format_timestamp(segment.end)
                text = segment.text.strip()
                if text:
                    parts.append(f"[{start} - {end}] {text}")
            body = "\n\n".join(parts)
            if len(parts) <= 1:
                body += "_No speech was transcribed._"
                warnings.append("No speech detected in the media file.")
        except Exception as exc:
            warnings.append(f"Transcription failed: {exc}")
            body = "_Transcription failed._"

        return ConvertedDocument(
            title=path.stem,
            markdown=body,
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
        )


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
