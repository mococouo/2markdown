from __future__ import annotations

import json
from pathlib import Path


MANIFEST_FILENAME = "_2markdown_manifest.json"


def load_manifest(output_dir: Path) -> dict[str, dict[str, str]]:
    path = output_dir / MANIFEST_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(key): value
        for key, value in data.items()
        if isinstance(value, dict) and isinstance(value.get("hash"), str)
    }


def save_manifest(output_dir: Path, entries: dict[str, dict[str, str]]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MANIFEST_FILENAME
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
