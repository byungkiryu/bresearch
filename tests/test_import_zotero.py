"""Behavior checks for Zotero imports; all fixtures live in temporary folders."""

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_zotero.py"
FIELDS = [
    "Key", "Item Type", "Publication Year", "Author", "Title", "Date",
    "Publication Title", "DOI", "Meeting Name", "Place", "Type", "Url",
    "Volume", "Issue", "Pages", "Manual Tags", "Automatic Tags", "Notes",
    "Extra", "File Attachments", "Link Attachments",
]


def paper(key="PAPER001", title="Transport in a test material", doi="10.1234/test.1", **extra):
    row = dict.fromkeys(FIELDS, "")
    row.update({
        "Key": key, "Item Type": "journalArticle", "Publication Year": "2025",
        "Author": "Ryu, Byungki; Kim, Test", "Title": title, "Date": "2025-03-21",
        "Publication Title": "Test Journal", "DOI": doi,
        "Volume": "12", "Pages": "100-110", "Manual Tags": "BR:corresponding",
    })
    row.update(extra)
    return row


def talk(key="TALK0001", title="Transport at a conference", presentation_type="Oral", **extra):
    row = dict.fromkeys(FIELDS, "")
    row.update({
        "Key": key, "Item Type": "presentation", "Publication Year": "2026",
        "Author": "Ryu, Byungki; Kim, Test", "Title": title, "Date": "2026-09-16",
        "Meeting Name": "ECT 2026", "Place": "Test City", "Type": presentation_type,
    })
    row.update(extra)
    return row


class ImportIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zotero-import-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.papers_path = self.root / "papers.csv"
        self.talks_path = self.root / "presentations.csv"

    def write_csv(self, path, records):
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(records)

    def import_rows(self, papers=(), talks=(), resolutions=None, expected=0):
        self.write_csv(self.papers_path, papers)
        self.write_csv(self.talks_path, talks)
        args = [
            sys.executable, str(SCRIPT), "--papers", str(self.papers_path),
            "--presentations", str(self.talks_path), "--data-dir", str(self.data),
        ]
        if resolutions is not None:
            resolution_path = self.root / "resolutions.json"
            resolution_path.write_text(json.dumps(resolutions), encoding="utf-8")
            args.extend(["--resolutions", str(resolution_path)])
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        report = self.load("import_report.json")
        self.assertEqual(report["applied"], expected == 0)
        return report

    def load(self, name):
        return json.loads((self.data / name).read_text(encoding="utf-8"))

    def records(self, kind="publications"):
        return self.load(kind + ".json")

    def snapshots(self):
        return {
            name: (self.data / name).read_bytes()
            for name in ("registry.json", "publications.json", "presentations.json")
        }

    def assert_snapshots_unchanged(self, before):
        self.assertEqual(self.snapshots(), before)

    def test_reexport_and_reordering_preserve_ids(self):
        first = paper()
        second = paper("PAPER002", "Another paper", "10.1234/test.2", Date="2024-01-01", **{"Publication Year": "2024"})
        self.import_rows([first, second], [talk()])
        before = {item["zotero_key"]: item["id"] for item in self.records()}
        self.import_rows([second, dict(first, Title="Corrected paper title")], [talk()])
        after = {item["zotero_key"]: item["id"] for item in self.records()}
        self.assertEqual(before, after)
        self.assertEqual(len(after), 2)
        self.assertIn("Corrected paper title", {x["title"] for x in self.records()})

    def test_unique_doi_reconnects_new_key_and_retains_alias(self):
        self.import_rows([paper()])
        stable_id = self.records()[0]["id"]
        report = self.import_rows([paper("NEWKEY01", title="Updated title", doi="https://doi.org/10.1234/test.1")])
        self.assertEqual(self.records()[0]["id"], stable_id)
        self.assertEqual(report["counts"]["reconnected"], 1)
        source_refs = self.load("registry.json")["records"][0]["source_refs"]
        self.assertEqual({ref["key"] for ref in source_refs}, {"PAPER001", "NEWKEY01"})

    def test_ambiguous_duplicate_doi_blocks_without_changes(self):
        self.import_rows([paper()])
        before = self.snapshots()
        report = self.import_rows(
            [paper("NEWKEY01"), paper("NEWKEY02", title="Another copy")], expected=2
        )
        self.assertFalse(report["applied"])
        self.assertTrue(report["pending"] or report["errors"])
        self.assert_snapshots_unchanged(before)

    def test_presentation_new_key_requires_resolution(self):
        self.import_rows(talks=[talk()])
        stable_id = self.records("presentations")[0]["id"]
        before = self.snapshots()
        report = self.import_rows(talks=[talk("NEWTALK1")], expected=2)
        self.assertIn(stable_id, [candidate for item in report["pending"] for candidate in item["candidates"]])
        self.assert_snapshots_unchanged(before)
        self.import_rows(talks=[talk("NEWTALK1")], resolutions={"NEWTALK1": stable_id})
        self.assertEqual(self.records("presentations")[0]["id"], stable_id)

    def test_same_title_oral_and_poster_remain_distinct(self):
        self.import_rows(talks=[talk(), talk("TALK0002", presentation_type="Poster")])
        presentations = self.records("presentations")
        self.assertEqual(len(presentations), 2)
        self.assertEqual(len({item["id"] for item in presentations}), 2)
        self.assertEqual({item["presentation_type"] for item in presentations}, {"Oral", "Poster"})

    def test_omission_retains_record_and_marks_missing(self):
        self.import_rows([paper()], [talk()])
        stable_id = self.records()[0]["id"]
        report = self.import_rows(talks=[talk()])
        retained = self.records()
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]["id"], stable_id)
        self.assertTrue(retained[0]["source_missing"])
        self.assertEqual(report["counts"]["missing"], 1)

    def test_duplicate_key_rejects_input_without_changes(self):
        self.import_rows([paper()])
        before = self.snapshots()
        report = self.import_rows([paper(), paper(title="Conflicting duplicate")], expected=2)
        self.assertEqual(report["status"], "invalid_input")
        self.assertTrue(report["errors"])
        self.assert_snapshots_unchanged(before)

    def test_sidecar_content_is_never_rewritten(self):
        self.import_rows([paper()])
        sidecar = self.root / "content" / "items.json"
        sidecar.parent.mkdir()
        original = '{"schema_version":1,"items":{"pub-0001":{"summary":"직접 작성한 해설","image":"figures/result.png"}}}\n'
        sidecar.write_text(original, encoding="utf-8")
        self.import_rows([paper("NEWKEY01")])
        self.assertEqual(sidecar.read_text(encoding="utf-8"), original)

    def test_previous_key_can_reappear_after_reconnection(self):
        self.import_rows([paper()])
        stable_id = self.records()[0]["id"]
        self.import_rows([paper("NEWKEY01")])
        self.import_rows([paper(title="Updated using previous alias")])
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.records()[0]["id"], stable_id)
        self.assertEqual(self.records()[0]["title"], "Updated using previous alias")

    def test_changed_doi_on_existing_key_requires_review(self):
        self.import_rows([paper()])
        before = self.snapshots()
        report = self.import_rows([paper(doi="10.1234/different")], expected=2)
        self.assertTrue(report["pending"])
        self.assert_snapshots_unchanged(before)

    def test_confirmed_doi_correction_retains_id_and_logs_change(self):
        self.import_rows([paper()])
        stable_id = self.records()[0]["id"]
        report = self.import_rows(
            [paper(doi="10.1234/corrected")], resolutions={"PAPER001": stable_id}
        )
        self.assertEqual(self.records()[0]["id"], stable_id)
        self.assertEqual(self.records()[0]["doi"], "10.1234/corrected")
        self.assertEqual(report["counts"]["doi_corrected"], 1)
        self.assertEqual(report["changes"]["doi_corrected"], [{
            "id": stable_id, "key": "PAPER001",
            "previous_doi": "10.1234/test.1", "doi": "10.1234/corrected",
        }])

    def test_confirmed_new_presentation_does_not_replace_candidate(self):
        self.import_rows(talks=[talk()])
        original_id = self.records("presentations")[0]["id"]
        self.import_rows(talks=[talk("NEWTALK1")], expected=2)
        self.import_rows(talks=[talk("NEWTALK1")], resolutions={"NEWTALK1": "new"})
        records = self.records("presentations")
        self.assertEqual(len(records), 2)
        original = next(item for item in records if item["id"] == original_id)
        added = next(item for item in records if item["zotero_key"] == "NEWTALK1")
        self.assertTrue(original["source_missing"])
        self.assertFalse(added["source_missing"])
        self.assertNotEqual(added["id"], original_id)

    def test_missing_registry_does_not_regenerate_existing_data(self):
        self.import_rows([paper()], [talk()])
        before = {
            name: (self.data / name).read_bytes()
            for name in ("publications.json", "presentations.json")
        }
        (self.data / "registry.json").unlink()
        report = self.import_rows([paper()], [talk()], expected=2)
        self.assertTrue(report["errors"] or report["pending"])
        self.assertFalse((self.data / "registry.json").exists())
        for name, content in before.items():
            self.assertEqual((self.data / name).read_bytes(), content)

    def test_private_columns_never_enter_generated_data(self):
        secret = "PRIVATE_SENTINEL_SHOULD_NOT_APPEAR"
        self.import_rows([paper(**{
            "Notes": secret,
            "Extra": secret,
            "File Attachments": "/private/" + secret + ".pdf",
            "Link Attachments": "file:///private/" + secret,
        })])
        for path in self.data.glob("*.json"):
            self.assertNotIn(secret, path.read_text(encoding="utf-8"), path.name)

    def test_partial_date_and_missing_pages_are_not_invented(self):
        self.import_rows([paper(Pages="null-null")], [talk(Date="2026-07")])
        self.assertIsNone(self.records()[0]["pages"])
        self.assertEqual(self.records("presentations")[0]["date"], "2026-07")


if __name__ == "__main__":
    unittest.main()
