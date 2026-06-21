from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import ConversionRecord


def write_reports(output_dir: Path, records: list[ConversionRecord]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "conversion_report.csv"
    json_path = output_dir / "conversion_report.json"

    rows = [_record_to_dict(record) for record in records]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["source_path", "status", "output_path", "converter", "warnings", "error", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def read_report(output_dir: Path) -> list[dict[str, str]]:
    path = output_dir / "conversion_report.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _record_to_dict(record: ConversionRecord) -> dict[str, str]:
    return {
        "source_path": str(record.source_path),
        "status": record.status,
        "output_path": str(record.output_path) if record.output_path else "",
        "converter": record.converter or "",
        "warnings": "; ".join(record.warnings),
        "error": record.error or "",
        "reason": record.reason or "",
    }
