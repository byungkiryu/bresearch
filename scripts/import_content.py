#!/usr/bin/env python3
"""Validate the editable workbook and import public website content.

Bibliographic fields are never sourced from this workbook. The ID registry and
Zotero imports remain authoritative for publication/presentation identity.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from datetime import date, datetime
from itertools import islice
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from openpyxl import load_workbook

from content_schema import HELP, HOME_DEFAULTS, PROFILE_KINDS, PROFILE_SCALARS, SHEETS

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _split(value, delimiter="\n"):
    return [part.strip() for part in _text(value).split(delimiter) if part.strip()]


def _json(path, fallback=None):
    if not Path(path).exists():
        return copy.deepcopy(fallback)
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.errors, self.warnings = [], []

    def issue(self, context, column, message, code="invalid_value", warning=False):
        target = self.warnings if warning else self.errors
        target.append({"sheet": context[0], "row": context[1], "column": column,
                       "code": code, "message": message})

    def boolean(self, value, default, context, column):
        if _text(value) == "":
            return default
        text = _text(value).casefold()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
        self.issue(context, column, "TRUE 또는 FALSE를 입력해 주세요.")
        return default

    def number(self, value, default, context, column, lower=None, upper=None):
        if _text(value) == "":
            return default
        try:
            result = float(value)
            if isinstance(value, bool) or not math.isfinite(result):
                raise ValueError
            if lower is not None and result < lower or upper is not None and result > upper:
                raise ValueError
            return int(result) if result.is_integer() else result
        except (TypeError, ValueError):
            self.issue(context, column, "허용 범위의 숫자를 입력해 주세요.")
            return default

    def identifier(self, value, context, column="id"):
        text = _text(value)
        if not text or not ID_PATTERN.fullmatch(text):
            self.issue(context, column, "고유 ID가 필요합니다. 영문·숫자·-·_·.·:만 사용하세요.", "invalid_id")
        return text

    def url(self, value, context, column="url", local=False):
        text = _text(value)
        if not text:
            return ""
        if local and re.fullmatch(r"#[A-Za-z0-9_-]+", text):
            return text
        if text.startswith("assets/"):
            path = PurePosixPath(text)
            asset_root = (self.root / "assets").resolve()
            resolved = (self.root / text).resolve()
            valid = ("\\" not in text and ".." not in path.parts
                     and not path.is_absolute() and not any(c in text for c in "?#%")
                     and not any(ord(c) < 32 for c in text)
                     and resolved.is_relative_to(asset_root) and resolved.is_file())
            if not valid:
                self.issue(context, column, "assets/ 아래 실제 파일의 상대경로가 필요합니다.", "invalid_url")
            return text
        try:
            parsed = urlsplit(text)
            valid = parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password
            valid = valid and not any(ord(ch) < 32 for ch in text)
        except ValueError:
            valid = False
        if not valid:
            self.issue(context, column, "http(s) 주소 또는 assets/ 아래 실제 파일의 상대경로를 입력해 주세요.", "invalid_url")
        return text

    def image(self, value, context, column="image"):
        text = _text(value)
        if not text:
            return ""
        path = PurePosixPath(text)
        asset_root = (self.root / "assets").resolve()
        resolved = (self.root / text).resolve()
        valid = (text.startswith("assets/") and "\\" not in text and ".." not in path.parts
                 and not path.is_absolute() and not any(c in text for c in "?#%")
                 and path.suffix.lower() in IMAGE_EXTENSIONS and resolved.is_relative_to(asset_root)
                 and resolved.is_file())
        if not valid:
            self.issue(context, column, "assets/ 아래 실제 PNG·JPG·WEBP 파일의 상대경로가 필요합니다.", "invalid_image")
        return text

    def date(self, value, context, column):
        text = _text(value)
        if not text:
            return ""
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                raise ValueError
            date.fromisoformat(text)
        except ValueError:
            self.issue(context, column, "YYYY-MM-DD 형식의 실제 날짜를 입력하거나 비워 주세요.", "invalid_date")
        return text

    def links(self, value, context):
        result = []
        for line in _split(value):
            if "|" not in line:
                self.issue(context, "links", "링크는 한 줄에 표시명|https://주소 형식으로 입력하세요.", "invalid_link_list")
                continue
            label, url = (part.strip() for part in line.split("|", 1))
            if not label or not url:
                self.issue(context, "links", "링크의 표시명과 주소가 모두 필요합니다.", "invalid_link_list")
            result.append({"label": label, "url": self.url(url, context, "links")})
        return result

    def rows(self, workbook):
        rows = {}
        try:
            if Path(workbook).suffix.lower() != ".xlsx":
                raise ValueError(".xlsx 파일만 사용할 수 있습니다.")
            book = load_workbook(workbook, read_only=True, data_only=False, keep_links=False)
        except Exception as exc:
            self.issue(("", 0), "", f"Excel 파일을 읽지 못했습니다: {type(exc).__name__}", "workbook_read_error")
            return rows
        try:
            missing = set(SHEETS) - set(book.sheetnames)
            for name in sorted(missing):
                self.issue((name, 1), "", "필수 시트가 없습니다. 기본 Excel의 시트 이름을 유지해 주세요.", "missing_sheet")
            for name in book.sheetnames:
                if name not in SHEETS:
                    self.issue((name, 1), "", "지원하지 않는 시트입니다. 정의된 10개 시트만 사용하세요.", "unknown_sheet")
                    continue
                sheet = book[name]
                if (sheet.max_row or 0) > 50000 or (sheet.max_column or 0) > 200:
                    self.issue((name, 1), "", "시트 크기가 허용 범위를 초과했습니다.", "sheet_too_large")
                    continue
                expected = SHEETS[name]
                values = list(islice(sheet.iter_rows(), 50001))
                if len(values) > 50000 or any(len(row) > 200 for row in values):
                    self.issue((name, 1), "", "시트 크기가 허용 범위를 초과했습니다.", "sheet_too_large")
                    continue
                headers = [_text(cell.value) for cell in values[0]] if values else []
                while headers and not headers[-1]:
                    headers.pop()
                if headers != expected:
                    self.issue((name, 1), "", "1행 열 이름과 순서를 유지해 주세요. 필요 열: " + ", ".join(expected), "header_mismatch")
                    continue
                if len(values) < 2 or [_text(c.value) for c in values[1][:len(expected)]] != [HELP.get(key, key) for key in expected]:
                    self.issue((name, 2), "", "2행은 한국어 도움말 행입니다. 삭제하지 마세요.", "missing_help_row")
                out, seen = [], set()
                for row_number, cells in enumerate(values, start=1):
                    for index, cell in enumerate(cells):
                        if cell.data_type == "f" or _text(cell.value).startswith("="):
                            self.issue((name, row_number), expected[index] if index < len(expected) else "", "수식은 허용되지 않습니다. 계산 결과를 값으로 붙여넣으세요.", "formula_not_allowed")
                    if row_number < 3 or not any(_text(c.value) for c in cells):
                        continue
                    if any(_text(c.value) for c in cells[len(expected):]):
                        self.issue((name, row_number), "", "정의되지 않은 추가 열에 값이 있습니다.", "unexpected_cell")
                    row = {key: cells[index].value if index < len(cells) else None for index, key in enumerate(expected)}
                    context = (name, row_number)
                    key_name = "key" if name == "홈" else "id"
                    identity = self.identifier(row[key_name], context, key_name)
                    if identity in seen:
                        self.issue(context, key_name, "이 시트에서 ID 또는 설정 키가 중복됩니다.", "duplicate_id")
                    seen.add(identity)
                    out.append((row, context))
                rows[name] = out
        finally:
            book.close()
        return rows

    def record(self, row, context, base=None):
        result = copy.deepcopy(base or {})
        for key, value in row.items():
            if key == "title_reference":
                continue
            if key in {"public", "featured"}:
                result[key] = self.boolean(value, key == "public", context, key)
            elif key == "order":
                result[key] = self.number(value, context[1] - 2, context, key)
            elif key in {"image", "hero_image"}:
                result[key] = self.image(value, context, key)
            elif key == "url":
                result[key] = self.url(value, context, key)
            elif key in {"date", "start_date", "end_date"}:
                result[key] = self.date(value, context, key)
            elif key in {"details", "entries"}:
                result[key] = _split(value)
            elif key in {"keywords", "tags", "person_ids"}:
                result[key] = _split(value, ";")
            elif key == "links":
                result[key] = self.links(value, context)
            elif key == "lat":
                result[key] = self.number(value, None, context, key, -90, 90)
            elif key == "lon":
                result[key] = self.number(value, None, context, key, -180, 180)
            else:
                result[key] = _text(value)
        if result.get("image") and not result.get("image_alt"):
            self.issue(context, "image_alt", "이미지 설명을 추가하면 접근성에 도움이 됩니다.", "missing_image_alt", warning=True)
        return result


def convert_workbook(workbook, root=ROOT, data_dir=None):
    root = Path(root).resolve()
    data_dir = Path(data_dir or root / "data")
    reader = Reader(root)
    report = {"schema_version": 1, "status": "invalid_input", "applied": False,
              "source": Path(workbook).name, "counts": {}, "errors": reader.errors, "warnings": reader.warnings}
    try:
        site = _json(root / "content/site.json", {})
        curated = _json(root / "content/items.json", {"schema_version": 1, "items": {}})
        publications = _json(data_dir / "publications.json", [])
        presentations = _json(data_dir / "presentations.json", [])
    except (OSError, ValueError, TypeError) as exc:
        reader.issue(("", 0), "", f"기존 JSON을 읽지 못했습니다: {type(exc).__name__}", "baseline_read_error")
        return {}, {}, report
    sheets = reader.rows(workbook)
    if reader.errors:
        return site, curated, report
    for name, target in (("사람", "people"), ("행사", "events"), ("뉴스", "news"), ("자료", "links")):
        old = {x["id"]: x for x in site.get(target, [])}
        site[target] = [reader.record(row, ctx, old.get(_text(row["id"]))) for row, ctx in sheets[name]]
        for record, (_, ctx) in zip(site[target], sheets[name]):
            label = "name" if name == "사람" else "title"
            if not record.get(label):
                reader.issue(ctx, label, "이름 또는 제목이 필요합니다.", "missing_title")
            if name == "행사" and record["end_date"] and (not record["start_date"] or record["end_date"] < record["start_date"]):
                reader.issue(ctx, "end_date", "종료일은 시작일과 같거나 이후여야 합니다.", "invalid_date_range")
    topics = {x["id"]: x for x in site.get("research", {}).get("topics", [])}
    site.setdefault("research", {})["topics"] = [reader.record(row, ctx, topics.get(_text(row["id"]))) for row, ctx in sheets["연구"]]
    for row, ctx in sheets["연구"]:
        if not _text(row["title"]):
            reader.issue(ctx, "title", "연구 제목이 필요합니다.", "missing_title")
    home = dict(HOME_DEFAULTS)
    home.update(site.get("home", {}))
    for row, ctx in sheets["홈"]:
        key, value = _text(row["key"]), _text(row["value"])
        if key.endswith("_image"):
            value = reader.image(value, ctx, "value")
        if key.endswith("_url"):
            value = reader.url(value, ctx, "value", local=True)
        home[key] = value
    site["home"] = home
    if "research_description" in home:
        site["research"]["intro"] = home["research_description"]
    profile = site.setdefault("profile", {})
    old_profile = copy.deepcopy(profile)
    for key in PROFILE_SCALARS:
        profile.pop(key, None)
    mapping = {"education": "education", "career": "career", "award": "awards", "about": "about_sections", "link": "links"}
    for target in mapping.values():
        profile[target] = []
    profile["scalar_metadata"] = {}
    for row, ctx in sheets["프로필"]:
        kind = _text(row["kind"])
        if kind not in PROFILE_KINDS:
            reader.issue(ctx, "kind", "scalar/education/career/award/about/link 중 하나를 입력하세요.", "invalid_profile_kind")
            continue
        converted = reader.record(row, ctx)
        meta = {key: converted[key] for key in ("id", "order", "public")}
        if kind == "scalar":
            key = converted["key"]
            if key not in PROFILE_SCALARS:
                reader.issue(ctx, "key", "프로필 설정 키를 확인하세요: " + ", ".join(PROFILE_SCALARS), "invalid_profile_key")
            if key in profile["scalar_metadata"]:
                reader.issue(ctx, "key", "프로필 설정 키가 중복됩니다.", "duplicate_profile_key")
            profile[key] = reader.image(converted["value"], ctx, "value") if key == "image" else converted["value"]
            profile["scalar_metadata"][key] = meta
        else:
            target = mapping[kind]
            existing = {x.get("id", f"profile-{kind}-{index:04d}"): x for index, x in enumerate(old_profile.get(target, []), start=1)}
            result = copy.deepcopy(existing.get(converted["id"], {}))
            result.update(meta)
            keys = ("period", "title", "organization") if kind in {"education", "career", "award"} else ("title", "entries") if kind == "about" else ("url",)
            result.update({key: converted[key] for key in keys})
            if kind == "link":
                result["label"] = converted["title"]
            profile[target].append(result)
    old_points = {x["id"]: x for group in site.get("maps", {}).values() if isinstance(group, list) for x in group}
    site["maps"] = {**site.get("maps", {}), "collaborations": [], "visits": []}
    for row, ctx in sheets["위치"]:
        record = reader.record(row, ctx, old_points.get(_text(row["id"])))
        group = record.pop("group")
        if group not in {"collaborations", "visits"}:
            reader.issue(ctx, "group", "collaborations 또는 visits를 입력하세요.", "invalid_location_group")
            continue
        if not record["name"]:
            reader.issue(ctx, "name", "위치 이름이 필요합니다.", "missing_location")
        if group == "visits" and not _text(row["lat"]) and not _text(row["lon"]):
            reader.issue(ctx, "lat/lon", "좌표 미확인: 방문 목록에는 표시하고 지도에는 표시하지 않습니다.",
                         "unconfirmed_coordinates", warning=True)
        elif record["lat"] is None or record["lon"] is None:
            reader.issue(ctx, "lat/lon", "위도와 경도를 함께 입력하세요. 방문 기록은 둘 다 비울 수 있습니다.",
                         "missing_location")
        site["maps"][group].append(record)
    people = {x["id"] for x in site["people"]}
    events = {x["id"] for x in site["events"]}
    bibliography = {"논문해설": {x["id"] for x in publications}, "발표해설": {x["id"] for x in presentations}}
    old_items = curated.get("items", {})
    new_items = {}
    for name in ("논문해설", "발표해설"):
        for row, ctx in sheets[name]:
            record = reader.record(row, ctx, old_items.get(_text(row["id"])))
            record_id = record.pop("id")
            if record_id not in bibliography[name]:
                reader.issue(ctx, "id", "해당 Zotero 데이터에 없는 ID입니다. data/identity-map.csv에서 확인하세요.", "unknown_bibliographic_id")
            for person_id in record["person_ids"]:
                if person_id not in people:
                    reader.issue(ctx, "person_ids", f"사람 시트에 없는 ID: {person_id}", "unknown_person_id")
            if record.get("event_id") and record["event_id"] not in events:
                reader.issue(ctx, "event_id", "행사 시트에 없는 ID입니다.", "unknown_event_id")
            record["hidden"] = not record["public"]
            new_items[record_id] = record
    featured = _split(home.get("featured_publication_ids"), ";")
    for record_id in featured:
        if record_id not in bibliography["논문해설"]:
            reader.issue(("홈", 0), "featured_publication_ids", "선택 논문 ID가 Zotero 데이터에 없습니다: " + record_id, "unknown_featured_id")
    curated = {**curated, "schema_version": 1, "items": new_items}
    report["counts"] = {name: len(rows) for name, rows in sheets.items()}
    if not reader.errors:
        report["status"] = "ok"
    return site, curated, report


def run_import(workbook, root=ROOT, check=False, data_dir=None):
    root = Path(root).resolve()
    site, curated, report = convert_workbook(workbook, root, data_dir)
    if report["status"] == "ok" and not check:
        from import_zotero import _atomic_outputs
        _atomic_outputs(root / "content", {"site.json": site, "items.json": curated})
        report["applied"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = run_import(args.workbook or args.root / "input/content.xlsx", args.root, args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
