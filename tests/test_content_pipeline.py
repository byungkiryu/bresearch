"""Content input validation and all-or-nothing update behavior."""
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from openpyxl import Workbook, load_workbook

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from content_schema import SHEETS, sheet_help
from import_content import convert_workbook
from import_zotero import run_import
from update import run_update


class ContentPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="content-pipeline-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        for name in ("input", "content", "data", "src", "assets", "scripts", "dist"):
            (self.root / name).mkdir()
        for script in (REPO / "scripts").glob("*.py"):
            shutil.copy2(script, self.root / "scripts" / script.name)
        self.original = {"profile": {"name": "Old name", "education": [], "career": [], "awards": [], "links": [], "about_sections": []},
                         "people": [], "research": {"intro": "Old intro", "topics": []}, "news": [], "links": [],
                         "maps": {"collaborations": [], "visits": []}, "provenance": {"source_commit": "retained"}}
        self.write_json("content/site.json", self.original)
        self.write_json("content/items.json", {"schema_version": 1, "items": {}})
        (self.root / "dist/index.html").write_text("old deployed output")
        self.fields = ["Key", "Item Type", "Publication Year", "Author", "Title", "Date", "Publication Title", "DOI", "Meeting Name", "Place", "Type", "Notes", "File Attachments"]
        self.paper = {"Key": "PAPER001", "Item Type": "journalArticle", "Publication Year": "2026", "Author": "Ryu, Byungki", "Title": "Original paper", "Date": "2026-01-01", "Publication Title": "Journal", "DOI": "10.1234/example", "Notes": "PRIVATE VALUE"}
        self.talk = {"Key": "TALK0001", "Item Type": "presentation", "Publication Year": "2026", "Author": "Ryu, Byungki", "Title": "Original talk", "Date": "2026-01-02", "Meeting Name": "Meeting", "Place": "City", "Type": "Oral"}
        self.write_csvs()
        report = run_import(self.root / "input/zotero-publications.csv", self.root / "input/zotero-presentations.csv", self.root / "data")
        self.assertTrue(report["applied"])
        self.rows = {"사람": [{"id": "person-0001", "name": "Researcher", "category": "Members", "public": False}],
                     "행사": [{"id": "event-0001", "title": "A conference", "start_date": "2026-01-01", "end_date": "2026-01-03"}],
                     "홈": [{"key": "research_description", "value": "New intro"}],
                     "프로필": [{"id": "profile-name", "kind": "scalar", "key": "name", "value": "New name"}],
                     "연구": [{"id": "transport", "title": "Transport", "details": "First\nSecond", "keywords": "A; B"}],
                     "논문해설": [{"id": "pub-0001", "title_reference": "Ignored title", "summary": "Authored summary", "person_ids": "person-0001"}],
                     "발표해설": [{"id": "talk-0001", "event_id": "event-0001"}]}
        self.write_workbook()
        self.good_build()

    def write_json(self, path, data):
        (self.root / path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def write_csvs(self):
        for filename, records in (("zotero-publications.csv", [self.paper]), ("zotero-presentations.csv", [self.talk])):
            with (self.root / "input" / filename).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(records)

    def write_workbook(self, omit=()):
        book = Workbook()
        book.remove(book.active)
        for name, columns in SHEETS.items():
            if name in omit:
                continue
            sheet = book.create_sheet(name)
            sheet.append(columns)
            sheet.append(sheet_help(name))
            for row in self.rows.get(name, []):
                sheet.append([row.get(column) for column in columns])
        book.save(self.root / "input/content.xlsx")
        book.close()

    def good_build(self):
        # Small executable build fixture makes failure/commit boundaries explicit.
        (self.root / "scripts/build_site.py").write_text("from pathlib import Path\nimport json\nr=Path(__file__).resolve().parents[1]\np=json.loads((r/'data/publications.json').read_text())\n(r/'dist').mkdir(exist_ok=True)\n(r/'dist/index.html').write_text(p[0]['title'])\n", encoding="utf-8")

    def snapshots(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for directory in ("data", "content", "dist") for path in (self.root / directory).rglob("*") if path.is_file()}

    def test_import_keeps_authority_and_explicit_visibility(self):
        site, curated, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["provenance"], self.original["provenance"])
        self.assertFalse(site["people"][0]["public"])
        self.assertEqual(site["profile"]["name"], "New name")
        self.assertEqual(site["research"]["topics"][0]["details"], ["First", "Second"])
        self.assertEqual(curated["items"]["talk-0001"]["event_id"], "event-0001")
        self.assertNotIn("title_reference", curated["items"]["pub-0001"])
        self.assertTrue(curated["items"]["pub-0001"]["public"])
        self.assertEqual(json.loads((self.root / "data/presentations.json").read_text())[0]["date"], "2026-01-02")

    def test_legacy_workbook_preserves_optional_research_lists(self):
        projects = [{"id": "existing-project", "title": "Existing project", "public": False}]
        facilities = [{"id": "existing-facility", "title": "Existing facility"}]
        self.original["research"].update(projects=projects, facilities=facilities)
        self.write_json("content/site.json", self.original)
        self.write_workbook(omit=("프로젝트", "시설"))
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["research"]["projects"], projects)
        self.assertEqual(site["research"]["facilities"], facilities)

        # Explicitly present empty sheets are an editor's instruction to clear
        # those lists; omission in an older workbook must not do that.
        self.write_workbook()
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["research"]["projects"], [])
        self.assertEqual(site["research"]["facilities"], [])

    def test_legacy_workbook_without_optional_baseline_defaults_to_empty(self):
        self.write_workbook(omit=("프로젝트", "시설"))
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["research"]["projects"], [])
        self.assertEqual(site["research"]["facilities"], [])

    def test_projects_and_facilities_import_bilingual_content_and_assets(self):
        (self.root / "assets/facility.png").write_bytes(b"png fixture")
        project = {"id": "project-0001", "title": "Strengthening by stable heterogeneous phases in metal",
                   "title_ko": "안정한 이질상을 이용한 금속의 강화",
                   "start_date": datetime(2022, 9, 1), "end_date": "2027-12-31",
                   "description": "Project description", "reference_numbers": "26A02008 (2022M3C1C8093916)",
                   "order": 2, "public": False}
        facility = {"id": "facility-0001", "title": "Measurement facility", "title_ko": "측정 시설",
                    "description": "Facility description", "url": "https://example.test/facility",
                    "image": "assets/facility.png", "image_alt": "Facility image", "order": 1}
        self.rows.update({"프로젝트": [project], "시설": [facility]})
        self.write_workbook()
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["research"]["projects"], [{**project, "start_date": "2022-09-01"}])
        self.assertEqual(site["research"]["facilities"], [{**facility, "public": True}])

    def test_project_invalid_dates_titles_and_duplicate_ids_are_rejected(self):
        valid = {"id": "project-0001", "title": "Project", "start_date": "2026-01-01", "end_date": "2026-12-31"}
        for changes, code in (({"end_date": "2025-12-31"}, "invalid_date_range"),
                              ({"start_date": ""}, "invalid_date_range"),
                              ({"start_date": "2026-02-30"}, "invalid_date"),
                              ({"title": ""}, "missing_title")):
            with self.subTest(changes=changes):
                self.rows["프로젝트"] = [{**valid, **changes}]
                self.write_workbook()
                _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
                self.assertEqual(report["status"], "invalid_input", report)
                self.assertIn(code, {issue["code"] for issue in report["errors"]})
        self.rows["프로젝트"] = [valid, {**valid, "title": "Another project"}]
        self.write_workbook()
        _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertIn("duplicate_id", {issue["code"] for issue in report["errors"]})

    def test_facility_missing_title_and_unsafe_assets_are_rejected(self):
        for changes, code in (({"title": ""}, "missing_title"),
                              ({"image": "assets/../private.png"}, "invalid_image"),
                              ({"url": "javascript:alert(1)"}, "invalid_url")):
            with self.subTest(changes=changes):
                self.rows["시설"] = [{"id": "facility-0001", "title": "Facility", **changes}]
                self.write_workbook()
                _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
                self.assertEqual(report["status"], "invalid_input", report)
                self.assertIn(code, {issue["code"] for issue in report["errors"]})

    def test_formula_bad_reference_duplicate_and_traversal_fail(self):
        self.rows["사람"].append({"id": "person-0001", "name": "Duplicate"})
        self.rows["사람"][0]["description"] = "=1+1"
        self.write_workbook()
        _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        codes = {x["code"] for x in report["errors"]}
        self.assertIn("formula_not_allowed", codes)
        self.assertIn("duplicate_id", codes)
        self.rows["사람"] = [{"id": "person-0001", "name": "Person", "image": "assets/../private.jpg"}]
        self.rows["발표해설"][0]["event_id"] = "event-missing"
        self.rows["논문해설"][0]["person_ids"] = "person-missing"
        self.write_workbook()
        _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        codes = {x["code"] for x in report["errors"]}
        self.assertTrue({"invalid_image", "unknown_event_id", "unknown_person_id"}.issubset(codes))

    def test_missing_id_and_header_rows_rejected(self):
        self.rows["사람"][0]["id"] = ""
        self.write_workbook()
        _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertIn("invalid_id", {x["code"] for x in report["errors"]})
        book = load_workbook(self.root / "input/content.xlsx")
        book["사람"]["A1"] = "wrong_header"
        book.save(self.root / "input/content.xlsx")
        book.close()
        _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertIn("header_mismatch", {x["code"] for x in report["errors"]})

    def test_local_attachment_links_accept_files_and_reject_escape(self):
        (self.root / "assets/files").mkdir()
        (self.root / "assets/files/slides.pdf").write_bytes(b"%PDF-1.7\n")
        self.rows["자료"] = [{"id": "slides", "title": "Slides", "url": "assets/files/slides.pdf"}]
        self.rows["연구"][0]["links"] = "Slides|assets/files/slides.pdf"
        self.rows["홈"].append({"key": "primary_url", "value": "assets/files/slides.pdf"})
        self.write_workbook()
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(site["links"][0]["url"], "assets/files/slides.pdf")
        self.assertEqual(site["research"]["topics"][0]["links"][0]["url"], "assets/files/slides.pdf")
        self.assertEqual(site["home"]["primary_url"], "assets/files/slides.pdf")
        (self.root / "private.pdf").write_bytes(b"private")
        for invalid in ("assets/../private.pdf", "assets/%2e%2e/private.pdf", "assets/files/missing.pdf"):
            with self.subTest(invalid=invalid):
                self.rows["자료"][0]["url"] = invalid
                self.write_workbook()
                _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
                self.assertIn("invalid_url", {x["code"] for x in report["errors"]})

    def test_check_build_failure_and_success_are_transactional(self):
        self.paper["Title"] = "Updated paper"
        self.write_csvs()
        before = self.snapshots()
        report = run_update(self.root, check=True)
        self.assertEqual(report["status"], "ok", report)
        self.assertFalse(report["applied"])
        self.assertEqual(before, self.snapshots())
        (self.root / "scripts/build_site.py").write_text("raise RuntimeError('intentional build failure')")
        report = run_update(self.root)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(before, self.snapshots())
        self.good_build()
        report = run_update(self.root)
        self.assertTrue(report["applied"], report)
        self.assertEqual((self.root / "dist/index.html").read_text(), "Updated paper")
        records = json.loads((self.root / "data/publications.json").read_text())
        self.assertEqual(records[0]["id"], "pub-0001")
        self.assertNotIn("PRIVATE VALUE", (self.root / "data/registry.json").read_text())

    def test_visit_without_coordinates_keeps_record_and_warns(self):
        self.rows["위치"] = [{"id": "visit-0001", "group": "visits", "name": "Chiba",
                              "description": "2026-03 · Vacation"},
                             {"id": "visit-0002", "group": "visits", "name": "Equator",
                              "lat": 0, "lon": 0}]
        self.write_workbook()
        site, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(len(site["maps"]["visits"]), 2)
        self.assertIsNone(site["maps"]["visits"][0]["lat"])
        self.assertIsNone(site["maps"]["visits"][0]["lon"])
        self.assertEqual(site["maps"]["visits"][0]["description"], "2026-03 · Vacation")
        self.assertEqual((site["maps"]["visits"][1]["lat"], site["maps"]["visits"][1]["lon"]), (0, 0))
        self.assertEqual([x["code"] for x in report["warnings"]], ["unconfirmed_coordinates"])

    def test_partial_or_invalid_visit_coordinates_fail(self):
        for coordinates in ({"lat": 35}, {"lon": 140}, {"lat": 91, "lon": 140},
                            {"lat": 35, "lon": -181}, {"lat": "unknown", "lon": "unknown"}):
            with self.subTest(coordinates=coordinates):
                self.rows["위치"] = [{"id": "visit-0001", "group": "visits", "name": "Visit", **coordinates}]
                self.write_workbook()
                _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
                self.assertNotEqual(report["status"], "ok", report)
                self.assertIn("missing_location", {x["code"] for x in report["errors"]})
                self.assertNotIn("unconfirmed_coordinates", {x["code"] for x in report["warnings"]})

    def test_collaborations_need_coordinates_and_visits_need_names(self):
        for location in ({"id": "collaboration-0001", "group": "collaborations", "name": "Institute"},
                         {"id": "visit-0001", "group": "visits", "lat": 35, "lon": 140}):
            with self.subTest(location=location):
                self.rows["위치"] = [location]
                self.write_workbook()
                _, _, report = convert_workbook(self.root / "input/content.xlsx", self.root)
                self.assertIn("missing_location", {x["code"] for x in report["errors"]})

    def test_invalid_workbook_preserves_every_output(self):
        self.rows["논문해설"][0]["id"] = "pub-9999"
        self.write_workbook()
        before = self.snapshots()
        report = run_update(self.root)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(before, self.snapshots())
        self.assertTrue((self.root / "reports/content-import-report.json").exists())


if __name__ == "__main__":
    unittest.main()
