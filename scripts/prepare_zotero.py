#!/usr/bin/env python3
"""Prepare the public columns of Zotero CSV exports before uploading to GitHub.

The original exports are never changed. This is a field allowlist, not a
redaction service: titles, authors, tags, and other retained fields remain public.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "Key", "Item Type", "Publication Year", "Author", "Title", "Date",
    "Publication Title", "DOI", "Url", "Pages", "Manual Tags", "Automatic Tags",
    "Meeting Name", "Place", "Type", "Volume", "Issue",
]
COMMON = {"Key", "Item Type", "Publication Year", "Author", "Title", "Date"}
REQUIRED = {
    "publication": COMMON | {"Publication Title", "DOI"},
    "presentation": COMMON | {"Meeting Name", "Place", "Type"},
}
PUBLICATION_TYPES = {
    "journalArticle", "conferencePaper", "thesis", "dataset", "book",
    "bookSection", "report", "preprint", "magazineArticle", "newspaperArticle",
}
OUTPUT_NAMES = {
    "publication": "zotero-publications.csv",
    "presentation": "zotero-presentations.csv",
}


def public_url(value):
    if not value.strip():
        return value
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None and parsed.password is None:
            return value
    except ValueError:
        pass
    return ""


def prepare_csv_text(text, kind):
    """Return BOM-prefixed CSV and a summary after validating the entire input."""
    if kind not in REQUIRED:
        raise ValueError("Unknown CSV kind")
    reader = csv.reader(io.StringIO(text.removeprefix("\ufeff"), newline=""), strict=True)
    try:
        fields = next(reader)
    except StopIteration:
        raise ValueError("CSV 파일이 비어 있습니다.") from None
    if len(fields) != len(set(fields)):
        raise ValueError("CSV 헤더에 중복된 열 이름이 있습니다.")
    missing = REQUIRED[kind] - set(fields)
    if missing:
        raise ValueError("필수 열이 없습니다: " + ", ".join(sorted(missing)))
    rows = []
    omitted_urls = 0
    allowed_types = PUBLICATION_TYPES if kind == "publication" else {"presentation"}
    for cells in reader:
        if not cells or not any(cells):
            continue
        if len(cells) != len(fields):
            raise ValueError(f"CSV {reader.line_num}행의 열 개수가 헤더와 다릅니다.")
        source = dict(zip(fields, cells))
        if not re.fullmatch(r"[A-Z0-9]{8}", source["Key"].strip()):
            raise ValueError(f"CSV {reader.line_num}행의 Zotero Key를 확인하세요.")
        if source["Item Type"].strip() not in allowed_types:
            raise ValueError(f"CSV {reader.line_num}행의 Item Type이 선택한 파일 종류와 다릅니다.")
        row = {key: source.get(key, "") for key in FIELDS}
        row["Url"] = public_url(row["Url"])
        omitted_urls += bool(source.get("Url", "")) and not bool(row["Url"])
        rows.append(row)
    if not rows:
        raise ValueError("CSV에 기록이 없습니다.")
    stream = io.StringIO(newline="")
    stream.write("\ufeff")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue(), {
        "records": len(rows), "columns": len(FIELDS),
        "removed_columns": [key for key in fields if key not in FIELDS],
        "omitted_non_web_urls": omitted_urls,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zotero CSV에서 홈페이지용 열만 남깁니다. 원본은 변경하지 않습니다.")
    parser.add_argument("--papers", type=Path, help="원본 논문 Zotero CSV")
    parser.add_argument("--presentations", type=Path, help="원본 발표 Zotero CSV")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "input", help="결과 폴더 (기본: 프로젝트 input/)")
    args = parser.parse_args(argv)
    if not args.papers and not args.presentations:
        parser.error("--papers 또는 --presentations를 지정하세요.")
    prepared = []
    try:
        for kind, source in [("publication", args.papers), ("presentation", args.presentations)]:
            if source is None:
                continue
            destination = args.output_dir / OUTPUT_NAMES[kind]
            if source.resolve() == destination.resolve():
                raise ValueError("원본과 결과 파일 경로가 같습니다. 원본 CSV는 다른 폴더에 두세요.")
            payload, summary = prepare_csv_text(source.read_bytes().decode("utf-8-sig"), kind)
            prepared.append((destination, payload, summary))
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for destination, payload, summary in prepared:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=args.output_dir, delete=False) as handle:
                    handle.write(payload)
                    temporary = Path(handle.name)
                temporary.replace(destination)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            print(json.dumps({"output": str(destination), **summary}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        print(f"CSV 준비 실패: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
