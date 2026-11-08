#!/usr/bin/env python3
"""Import Zotero CSV exports while preserving independent homepage identities.

No network access or third-party packages are required. Source CSVs and separately
authored content are never modified. A review conflict writes only the report.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import html
import io
import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date as calendar_date
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
PUBLICATION_TYPES = {
    "journalArticle", "conferencePaper", "thesis", "dataset", "book",
    "bookSection", "report", "preprint", "magazineArticle", "newspaperArticle",
}
ROLE_TAGS = {
    "BR:first": "first_author",
    "BR:co-first": "co_first_author",
    "BR:corresponding": "corresponding_author",
    "BR:co-corresponding": "co_corresponding_author",
}
COMMON_COLUMNS = {"Key", "Item Type", "Publication Year", "Author", "Title", "Date"}
SPECIFIC_COLUMNS = {
    "publication": {"Publication Title", "DOI"},
    "presentation": {"Meeting Name", "Place", "Type"},
}
PREFIXES = {"publication": "pub", "presentation": "talk"}


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.suppressed += 1
        elif tag in {"br", "p", "div", "li"} and not self.suppressed:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.suppressed:
            self.suppressed -= 1
        elif tag in {"p", "div", "li"} and not self.suppressed:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)


def plain_text(value):
    """Keep formula text within sub/sup tags, without exporting executable HTML."""
    parser = _TextOnly()
    parser.feed(html.unescape(str(value or "")))
    parser.close()
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def canonical(value):
    return re.sub(r"[^\w]+", "", plain_text(value).casefold())


def normalize_doi(value):
    value = str(value or "").strip()
    while True:
        cleaned = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value,
                         flags=re.IGNORECASE).strip()
        if cleaned == value:
            break
        value = cleaned
    return value.casefold() or None


def _valid_date(value):
    if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        return False
    try:
        parts = [int(x) for x in value.split("-")]
        calendar_date(*(parts + [1] * (3 - len(parts))))
        return True
    except ValueError:
        return False


def _tags(value):
    return list(dict.fromkeys(plain_text(x) for x in (value or "").split(";")
                             if plain_text(x)))


def _issue(code, record=None, **details):
    result = {"code": code}
    if record:
        result.update({k: record[k] for k in ("kind", "zotero_key", "title")
                       if k in record})
        if "zotero_key" in result:
            result["key"] = result.pop("zotero_key")
    result.update(details)
    return result


def _load_csv(path, kind, namespace, report):
    path = Path(path)
    raw = path.read_bytes()
    report["sources"].append({"kind": kind, "filename": path.name,
                              "sha256": hashlib.sha256(raw).hexdigest()})
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    required = COMMON_COLUMNS | SPECIFIC_COLUMNS[kind]
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        report["errors"].append(_issue("duplicate_columns", filename=path.name))
        return []
    if required - set(fields):
        report["errors"].append(_issue("missing_columns", filename=path.name,
                                        columns=sorted(required - set(fields))))
        return []
    output = []
    for row_number, row in enumerate(reader, start=2):
        if not any(v for v in row.values()):
            continue
        if None in row or any(v is None for v in row.values()):
            report["errors"].append(_issue("malformed_csv_row", filename=path.name,
                                            row=row_number))
            continue
        key = row["Key"].strip()
        title = plain_text(row["Title"])
        record = {"kind": kind, "zotero_key": key, "title": title}
        item_type = row["Item Type"].strip()
        if not re.fullmatch(r"[A-Z0-9]{8}", key):
            report["errors"].append(_issue("invalid_key", record, row=row_number))
        allowed = PUBLICATION_TYPES if kind == "publication" else {"presentation"}
        if item_type not in allowed:
            report["errors"].append(_issue("unsupported_item_type", record,
                                            item_type=item_type))
        date = row["Date"].strip()
        year_text = row["Publication Year"].strip()
        if not _valid_date(date):
            report["errors"].append(_issue("invalid_date", record, value=date))
        if not re.fullmatch(r"\d{4}", year_text) or not 1 <= int(year_text) <= 9999:
            report["errors"].append(_issue("invalid_year", record, value=year_text))
            year = None
        else:
            year = int(year_text)
            if date[:4] != year_text:
                report["warnings"].append(_issue("year_date_difference", record,
                                                   year=year, date=date))
        authors = [plain_text(x) for x in row["Author"].split(";") if plain_text(x)]
        if not title or not authors:
            report["errors"].append(_issue("missing_title_or_authors", record))
        if len({canonical(x) for x in authors}) < len(authors):
            report["warnings"].append(_issue("repeated_author_name", record))
        doi = normalize_doi(row.get("DOI"))
        if doi and not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            report["errors"].append(_issue("invalid_doi", record, value=doi))
        url = row.get("Url", "").strip() or None
        if url:
            try:
                parsed = urlsplit(url)
                valid_url = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                             and parsed.username is None and parsed.password is None)
            except ValueError:
                valid_url = False
            if not valid_url:
                report["warnings"].append(_issue("unsupported_url_omitted", record))
                url = None
        pages = plain_text(row.get("Pages")) or None
        if pages and pages.casefold() in {"null", "null-null", "nan", "none", "n/a"}:
            report["warnings"].append(_issue("placeholder_pages_omitted", record))
            pages = None
        manual_tags, automatic_tags = _tags(row.get("Manual Tags")), _tags(row.get("Automatic Tags"))
        venue = plain_text(row.get("Publication Title" if kind == "publication" else "Meeting Name")) or None
        presentation_type = plain_text(row.get("Type")) or None if kind == "presentation" else None
        if kind == "presentation":
            if not presentation_type:
                report["warnings"].append(_issue("presentation_type_missing", record))
            if not venue:
                report["warnings"].append(_issue("meeting_missing", record))
            if re.fullmatch(r"\d{4}-\d{2}", date):
                report["warnings"].append(_issue("month_precision_preserved", record))
            event_years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", venue or "")
            if event_years and date[:4] not in event_years:
                report["warnings"].append(_issue("event_year_difference", record,
                                                   date=date, venue=venue))
        record.update({
            "source_namespace": namespace,
            "item_type": item_type,
            "authors": authors,
            "year": year,
            "date": date,
            "venue": venue,
            "place": plain_text(row.get("Place")) or None,
            "presentation_type": presentation_type,
            "doi": doi,
            "url": url,
            "volume": plain_text(row.get("Volume")) or None,
            "issue": plain_text(row.get("Issue")) or None,
            "pages": pages,
            "manual_tags": manual_tags,
            "automatic_tags": automatic_tags,
            "roles": [ROLE_TAGS[tag] for tag in manual_tags if tag in ROLE_TAGS],
        })
        output.append(record)
    return output


def _atomic_outputs(data_dir, outputs):
    """Stage all files first, then replace each destination atomically."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for name, value in outputs.items():
            payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                             dir=data_dir, prefix=".import-", delete=False) as handle:
                handle.write(payload)
                staged.append((Path(handle.name), data_dir / name))
        for temporary, destination in staged:
            temporary.replace(destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def _load_registry(path):
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION,
                "next_ids": {"publication": 1, "presentation": 1}, "records": []}
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != SCHEMA_VERSION or not isinstance(registry.get("records"), list):
        raise ValueError("Unsupported registry schema")
    counters = registry.get("next_ids", {})
    if not isinstance(counters, dict) or any(not isinstance(value, int) or isinstance(value, bool) or value < 1
                                              for value in counters.values()):
        raise ValueError("Invalid registry ID counters")
    ids, refs = set(), set()
    for record in registry["records"]:
        kind, site_id = record.get("kind"), record.get("id")
        if kind not in PREFIXES or not isinstance(site_id, str) or not re.fullmatch(PREFIXES[kind] + r"-\d{4,}", site_id):
            raise ValueError("Invalid registry ID or kind")
        if site_id in ids or not isinstance(record.get("metadata"), dict):
            raise ValueError("Duplicate registry ID or missing metadata")
        ids.add(site_id)
        for ref in record.get("source_refs", []):
            pair = (ref["namespace"], ref["key"])
            if pair in refs:
                raise ValueError("Duplicate source reference in registry")
            refs.add(pair)
    return registry


def _candidate_ids(incoming, registry_records, active_ids):
    candidates = []
    title = canonical(incoming["title"])
    for old in registry_records:
        if old["id"] in active_ids or old["kind"] != incoming["kind"]:
            continue
        metadata = old["metadata"]
        other_title = canonical(metadata.get("title"))
        similarity = SequenceMatcher(None, title, other_title).ratio()
        exact_title = title == other_title
        same_event = (incoming["date"] == metadata.get("date")
                      and canonical(incoming["venue"]) == canonical(metadata.get("venue")))
        # Same-title oral and poster records remain separate candidates, never merged.
        if exact_title or (similarity >= .90 and (same_event or incoming["kind"] == "publication")):
            candidates.append(old["id"])
    return sorted(candidates)


def _identity_csv(records):
    buffer = io.StringIO(newline="")
    fields = ["site_id", "kind", "namespace", "zotero_key", "prior_keys", "doi", "title", "source_missing"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for record in sorted(records, key=lambda r: r["id"]):
        metadata = record["metadata"]
        current = (metadata["source_namespace"], metadata["zotero_key"])
        previous = [f"{ref['namespace']}:{ref['key']}" for ref in record["source_refs"]
                    if (ref["namespace"], ref["key"]) != current]
        writer.writerow({"site_id": record["id"], "kind": record["kind"],
                         "namespace": current[0], "zotero_key": current[1],
                         "prior_keys": "; ".join(previous), "doi": metadata.get("doi") or "",
                         "title": metadata["title"], "source_missing": record["source_missing"]})
    return buffer.getvalue()


def run_import(papers, presentations, data_dir, namespace="bk-zotero", resolutions=None):
    """Return a report; write data only when every identity decision is resolved.

    resolutions can be a dict or JSON filename: {"NEWKEY12": "pub-0001"}.
    A namespaced key ("bk-zotero:NEWKEY12") takes precedence. This explicit
    decision approves a DOI correction only for the same existing source key.
    The value "new" confirms an unknown key is a distinct record despite a
    similar-title candidate; it cannot bypass duplicate DOI or key conflicts.
    """
    data_dir = Path(data_dir)
    report = {
        "schema_version": SCHEMA_VERSION, "status": "invalid_input", "applied": False,
        "namespace": namespace, "sources": [],
        "counts": {"publications": 0, "presentations": 0, "new": 0, "updated": 0,
                   "reconnected": 0, "missing": 0, "pending": 0, "warnings": 0,
                   "doi_corrected": 0},
        "changes": {"new": [], "updated": [], "reconnected": [], "missing": [],
                    "doi_corrected": []},
        "pending": [], "errors": [], "warnings": [],
    }

    def finish_failure(status):
        report["status"] = status
        report["counts"]["pending"] = len(report["pending"])
        report["counts"]["warnings"] = len(report["warnings"])
        _atomic_outputs(data_dir, {"import_report.json": report})
        return report

    try:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", namespace or ""):
            raise ValueError("namespace must be a nonempty source label")
        incoming = _load_csv(papers, "publication", namespace, report)
        incoming += _load_csv(presentations, "presentation", namespace, report)
        if not (data_dir / "registry.json").exists() and any(
            (data_dir / filename).exists()
            for filename in ("publications.json", "presentations.json", "identity-map.csv")
        ):
            report["errors"].append({"code": "registry_missing_with_existing_data",
                                      "message": "Restore registry.json before importing; existing IDs must not be regenerated."})
            return finish_failure("invalid_input")
        registry = _load_registry(data_dir / "registry.json")
        if isinstance(resolutions, (str, Path)):
            resolutions = json.loads(Path(resolutions).read_text(encoding="utf-8"))
        resolutions = resolutions or {}
        if not isinstance(resolutions, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                    for k, v in resolutions.items()):
            raise ValueError("resolutions must map source keys to site ID strings")
    except (OSError, UnicodeError, csv.Error, ValueError, KeyError, TypeError) as exc:
        message = str(exc)
        for private_path in (papers, presentations, data_dir, resolutions if isinstance(resolutions, (str, Path)) else ""):
            if private_path:
                message = message.replace(str(private_path), Path(private_path).name)
        report["errors"].append({"code": "input_read_error", "message": message})
        return finish_failure("invalid_input")

    for kind, counter in (("publication", "publications"), ("presentation", "presentations")):
        report["counts"][counter] = sum(row["kind"] == kind for row in incoming)
    keys = Counter(row["zotero_key"] for row in incoming)
    for key, count in keys.items():
        if count > 1:
            report["errors"].append({"code": "duplicate_input_key", "key": key, "count": count})
    if report["errors"]:
        return finish_failure("invalid_input")

    records = registry["records"]
    by_id = {record["id"]: record for record in records}
    by_ref = {(ref["namespace"], ref["key"]): record for record in records for ref in record["source_refs"]}
    by_doi = defaultdict(list)
    for record in records:
        doi = normalize_doi(record["metadata"].get("doi"))
        if doi:
            by_doi[doi].append(record)
    present_refs = {(namespace, row["zotero_key"]) for row in incoming}
    active_ids = {by_ref[ref]["id"] for ref in present_refs if ref in by_ref}
    incoming_dois = Counter(row["doi"] for row in incoming if row["doi"])
    assignments, claimed = [], set()
    new_rows = []

    def pending(code, row, candidates=(), **details):
        report["pending"].append(_issue(code, row, candidates=list(candidates), **details))

    # Resolve existing keys first, independently of CSV order.
    unknown = []
    for row in sorted(incoming, key=lambda r: (r["kind"], r["date"], r["zotero_key"])):
        old = by_ref.get((namespace, row["zotero_key"]))
        explicit = resolutions.get(f"{namespace}:{row['zotero_key']}", resolutions.get(row["zotero_key"]))
        if row["doi"] and incoming_dois[row["doi"]] > 1:
            pending("duplicate_input_doi", row, [r["id"] for r in by_doi[row["doi"]]])
            continue
        if old is None:
            unknown.append(row)
            continue
        if explicit and explicit != old["id"]:
            pending("resolution_existing_key_requires_same_id", row, [old["id"]], requested_id=explicit)
            continue
        if old["kind"] != row["kind"]:
            pending("kind_changed", row, [old["id"]])
            continue
        other_doi_ids = [record["id"] for record in by_doi.get(row["doi"], [])
                         if record["id"] != old["id"]]
        if other_doi_ids:
            pending("doi_already_linked_to_another_id", row, other_doi_ids)
            continue
        old_doi = normalize_doi(old["metadata"].get("doi"))
        if old_doi and row["doi"] and old_doi != row["doi"]:
            if explicit == old["id"]:
                report["changes"]["doi_corrected"].append({"id": old["id"], "key": row["zotero_key"],
                                                           "previous_doi": old_doi, "doi": row["doi"]})
            else:
                pending("doi_changed_for_key", row, [old["id"]], previous_doi=old_doi, doi=row["doi"])
                continue
        if old["id"] in claimed:
            pending("multiple_rows_for_site_id", row, [old["id"]])
            continue
        claimed.add(old["id"])
        assignments.append((row, old["id"], "updated"))

    for row in unknown:
        explicit = resolutions.get(f"{namespace}:{row['zotero_key']}", resolutions.get(row["zotero_key"]))
        if explicit == "new":
            if row["doi"] and by_doi.get(row["doi"]):
                pending("resolution_new_doi_conflict", row, [r["id"] for r in by_doi[row["doi"]]])
            else:
                new_rows.append(row)
            continue
        if explicit:
            old = by_id.get(explicit)
            if old is None:
                pending("resolution_unknown_id", row, [], requested_id=explicit)
                continue
            if old["kind"] != row["kind"] or old["metadata"].get("item_type") != row["item_type"]:
                pending("resolution_type_mismatch", row, [explicit])
                continue
            old_doi = normalize_doi(old["metadata"].get("doi"))
            if old_doi and row["doi"] and old_doi != row["doi"]:
                pending("resolution_doi_conflict", row, [explicit])
                continue
            if explicit in claimed or explicit in active_ids:
                pending("resolution_target_still_present", row, [explicit])
                continue
            claimed.add(explicit)
            assignments.append((row, explicit, "reconnected"))
            continue
        doi_candidates = by_doi.get(row["doi"], []) if row["doi"] else []
        if doi_candidates:
            old = doi_candidates[0]
            compatible = old["kind"] == row["kind"] and old["metadata"].get("item_type") == row["item_type"]
            if len(doi_candidates) == 1 and compatible and old["id"] not in active_ids and old["id"] not in claimed:
                claimed.add(old["id"])
                assignments.append((row, old["id"], "reconnected"))
            else:
                pending("doi_reconnection_ambiguous", row, [r["id"] for r in doi_candidates])
            continue
        candidates = _candidate_ids(row, records, active_ids)
        if candidates:
            pending("metadata_match_requires_review", row, candidates)
        else:
            new_rows.append(row)
    if report["pending"]:
        return finish_failure("needs_review")

    updated_registry = copy.deepcopy(registry)
    updated_by_id = {record["id"]: record for record in updated_registry["records"]}
    next_ids = {}
    for kind, prefix in PREFIXES.items():
        highest = max((int(record["id"].split("-")[-1]) for record in records if record["kind"] == kind), default=0)
        next_ids[kind] = max(highest + 1, registry.get("next_ids", {}).get(kind, 1))
    for row in new_rows:
        kind = row["kind"]
        site_id = f"{PREFIXES[kind]}-{next_ids[kind]:04d}"
        next_ids[kind] += 1
        record = {"id": site_id, "kind": kind, "source_refs": [], "metadata": {}, "source_missing": False}
        updated_registry["records"].append(record)
        updated_by_id[site_id] = record
        assignments.append((row, site_id, "new"))
        claimed.add(site_id)
    for row, site_id, action in assignments:
        record = updated_by_id[site_id]
        previous_keys = [ref["key"] for ref in record["source_refs"]]
        ref = {"namespace": namespace, "key": row["zotero_key"]}
        if ref not in record["source_refs"]:
            record["source_refs"].append(ref)
        record["metadata"] = {"id": site_id, **row}
        record["source_missing"] = False
        if action == "reconnected":
            report["changes"][action].append({"id": site_id, "previous_keys": previous_keys, "key": row["zotero_key"]})
        else:
            report["changes"][action].append(site_id)
    for record in updated_registry["records"]:
        if record["id"] not in claimed and record["metadata"].get("source_namespace") == namespace:
            record["source_missing"] = True
            report["changes"]["missing"].append(record["id"])
    updated_registry["next_ids"] = next_ids
    updated_registry["records"].sort(key=lambda record: record["id"])
    for action in ("new", "updated", "reconnected", "missing", "doi_corrected"):
        report["counts"][action] = len(report["changes"][action])
    report["counts"]["warnings"] = len(report["warnings"])
    report["status"], report["applied"] = "ok", True
    outputs = {"registry.json": updated_registry, "import_report.json": report,
               "identity-map.csv": _identity_csv(updated_registry["records"])}
    for kind, name in (("publication", "publications.json"), ("presentation", "presentations.json")):
        public_rows = [{**record["metadata"], "source_missing": record["source_missing"]}
                       for record in updated_registry["records"] if record["kind"] == kind]
        public_rows.sort(key=lambda row: (row["date"], row["id"]), reverse=True)
        outputs[name] = public_rows
    _atomic_outputs(data_dir, outputs)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers", required=True, type=Path)
    parser.add_argument("--presentations", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--namespace", default="bk-zotero",
                        help="Stable local label for this Zotero library, not a Zotero numeric account ID")
    parser.add_argument("--resolutions", type=Path,
                        help="JSON mapping new Zotero keys to approved existing homepage IDs")
    args = parser.parse_args(argv)
    report = run_import(args.papers, args.presentations, args.data_dir, args.namespace, args.resolutions)
    print(json.dumps({"status": report["status"], "applied": report["applied"],
                      "counts": report["counts"]}, ensure_ascii=False, indent=2))
    return 0 if report["applied"] else 2


if __name__ == "__main__":
    sys.exit(main())
