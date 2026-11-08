"""The upload preparer preserves bibliography while excluding unused columns."""
import csv
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_zotero import FIELDS, main, prepare_csv_text


def source_csv(**overrides):
    row = dict.fromkeys(FIELDS, "")
    row.update({"Key": "ABCD1234", "Item Type": "journalArticle", "Publication Year": "2026", "Author": "Ryu, Byungki; 테스트, 이름", "Title": 'A "quoted", multiline\n제목', "Date": "2026-11", "Publication Title": "Journal", "DOI": "10.1234/test", "Manual Tags": "BR:first; thermoelectric", "Url": "https://example.org/paper"})
    row.update({"Notes": "private note", "Extra": "private extra", "File Attachments": "C:\\Users\\researcher\\paper.pdf", **overrides})
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(row))
    writer.writeheader(); writer.writerow(row)
    return "\ufeff" + buffer.getvalue()


class PrepareTests(unittest.TestCase):
    def test_preserves_exact_bibliography_and_excludes_private_columns(self):
        original = source_csv()
        output, report = prepare_csv_text(original, "publication")
        self.assertTrue(output.startswith("\ufeff"))
        result = list(csv.DictReader(io.StringIO(output.removeprefix("\ufeff"))))
        source = next(csv.DictReader(io.StringIO(original.removeprefix("\ufeff"))))
        self.assertEqual(list(result[0]), FIELDS)
        for field in FIELDS:
            self.assertEqual(result[0][field], source[field])
        self.assertNotIn("private note", output)
        self.assertNotIn("C:\\Users", output)
        self.assertEqual(report["records"], 1)

    def test_local_url_not_published(self):
        output, report = prepare_csv_text(source_csv(Url="file:///private/paper.pdf"), "publication")
        self.assertNotIn("file:///", output)
        self.assertEqual(report["omitted_non_web_urls"], 1)

    def test_header_shape_and_kind_fail_without_output(self):
        with self.assertRaisesRegex(ValueError, "필수"):
            prepare_csv_text("Title,Author\r\nX,Y\r\n", "publication")
        with self.assertRaisesRegex(ValueError, "중복"):
            prepare_csv_text("Key,Key\r\nX,Y\r\n", "publication")
        with self.assertRaisesRegex(ValueError, "종류"):
            prepare_csv_text(source_csv(), "presentation")

    def test_failed_second_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / "output"; output.mkdir()
            previous = output / "zotero-publications.csv"; previous.write_text("previous")
            papers = base / "papers.csv"; papers.write_text(source_csv(), encoding="utf-8")
            talks = base / "talks.csv"; talks.write_text("wrong", encoding="utf-8")
            code = main(["--papers", str(papers), "--presentations", str(talks), "--output-dir", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(previous.read_text(), "previous")

    @unittest.skipUnless(shutil.which("node"), "Node is needed for browser-helper parity")
    def test_browser_and_python_match_for_quoted_unicode_multiline_csv(self):
        html = (Path(__file__).resolve().parents[1] / "tools" / "prepare-zotero.html").read_text(encoding="utf-8")
        script = re.search(r"<script>([\s\S]*?)</script>", html).group(1)
        script += '\nconst input = JSON.parse(require("fs").readFileSync(0, "utf8")); process.stdout.write(JSON.stringify(prepareCsv(input.text, input.kind)));'
        for url in ("https://example.org/paper", "file:///C:/private/paper.pdf", "https://@example.org/paper"):
            original = source_csv(Title='Quoted "research", 한글\r\nsecond line', Url=url)
            expected, _ = prepare_csv_text(original, "publication")
            with tempfile.TemporaryDirectory() as directory:
                js = Path(directory) / "helper.cjs"
                js.write_text(script, encoding="utf-8")
                result = subprocess.run(["node", str(js)], input=json.dumps({"text": original, "kind": "publication"}), text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["csv"], expected)


if __name__ == "__main__":
    unittest.main()
