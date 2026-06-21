from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DEFAULTS: dict[str, Any] = {
    "language": "en",
    "last_source": "",
    "last_output": "",
    "preserve_tree": True,
    "extract_attachments": True,
    "write_frontmatter": True,
    "include_metadata": True,
    "overwrite": False,
    "incremental": False,
    "dry_run": False,
    "resume": False,
    "download_remote": False,
    "recurse_archives": False,
    "ocr": False,
    "ocr_lang": "eng",
    "audio_lang": "",
    "concurrency": 1,
    "max_size_mb": "",
    "asked_install_all": False,
}


def config_path() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or str(Path.home())
    folder = Path(base) / "2markdown"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        return dict(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_DEFAULTS)
    if not isinstance(data, dict):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
    return merged


def save_config(values: dict[str, Any]) -> None:
    path = config_path()
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in values.items() if k in _DEFAULTS})
    try:
        path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def default_language() -> str:
    for env in ("2MARKDOWN_LANG", "LANG"):
        value = os.environ.get(env)
        if value:
            base = value.split(".")[0].replace("_", "-")
            if base in __import__("two_markdown.i18n", fromlist=["LANGUAGES"]).LANGUAGES:
                return base
            short = base.split("-")[0]
            if short in __import__("two_markdown.i18n", fromlist=["LANGUAGES"]).LANGUAGES:
                return short
    return "en"
