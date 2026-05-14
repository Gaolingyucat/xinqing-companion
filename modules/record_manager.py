"""功能模块：封装具体业务能力，供路由层调用。"""

import csv
from datetime import datetime
from pathlib import Path


RECORD_FIELDS = [
    "time",
    "input_type",
    "emotion",
    "emotion_cn",
    "confidence",
    "risk_score",
    "risk_level",
    "suggestion",
    "file_path",
]


def ensure_record_file(csv_path):
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
            writer.writeheader()
        return

    with path.open("r", newline="", encoding="utf-8") as file:
        first_line = file.readline().strip()
    expected_header = ",".join(RECORD_FIELDS)
    if first_line != expected_header:
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
            writer.writeheader()


def add_record(
    csv_path,
    input_type,
    emotion,
    emotion_cn,
    confidence,
    risk_score,
    risk_level,
    suggestion,
    file_path="",
):
    ensure_record_file(csv_path)
    row = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_type": input_type,
        "emotion": emotion,
        "emotion_cn": emotion_cn,
        "confidence": f"{float(confidence):.4f}",
        "risk_score": int(risk_score),
        "risk_level": risk_level,
        "suggestion": suggestion,
        "file_path": file_path,
    }
    with Path(csv_path).open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writerow(row)


def read_records(csv_path):
    path = Path(csv_path)
    if not path.exists():
        return []

    records = []
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for raw_row in reader:
            if not raw_row:
                continue
            row = {field: (raw_row.get(field, "") or "").strip() for field in RECORD_FIELDS}
            if not any(row.values()):
                continue
            records.append(row)

    def _sort_key(item):
        value = item.get("time", "")
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.min

    records.sort(key=_sort_key, reverse=True)
    return records


def clear_records(csv_path):
    ensure_record_file(csv_path)
    path = Path(csv_path)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writeheader()
