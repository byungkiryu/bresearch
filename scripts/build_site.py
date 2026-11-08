#!/usr/bin/env python3
"""Build a self-contained research homepage; no network or packages required."""
from pathlib import Path
import json
import re
import base64
import copy
import shutil
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def public_rows(rows):
    return sorted((row for row in rows if row.get("public", True) is not False),
                  key=lambda row: row.get("order", 0))


def public_site(site):
    site = copy.deepcopy(site)
    for key in ("people", "events", "news", "links"):
        site[key] = public_rows(site.get(key, []))
    site.setdefault("research", {})["topics"] = public_rows(site.get("research", {}).get("topics", []))
    for key, rows in site.get("maps", {}).items():
        site["maps"][key] = public_rows(rows)
    profile = site.get("profile", {})
    for key in ("education", "career", "awards", "about_sections", "links"):
        profile[key] = public_rows(profile.get(key, []))
    for key, meta in profile.pop("scalar_metadata", {}).items():
        if meta.get("public", True) is False:
            profile[key] = ""
    return site


def prepare_assets(payload):
    """Embed local images and copy only public, referenced attachments."""
    copies = {}
    assets_root = (ROOT / "assets").resolve()
    image_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                   ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml", ".avif": "image/avif"}
    def visit(value, key=""):
        if isinstance(value, dict):
            return {name: visit(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [visit(item, key) for item in value]
        if not isinstance(value, str) or not value.startswith("assets/"):
            return value
        relative = Path(value)
        if ".." in relative.parts or "\\" in value or "\x00" in value:
            raise ValueError(f"Invalid asset path: {value}")
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(assets_root) or not source.is_file():
            raise ValueError(f"Missing asset file: {value}")
        if key in {"image", "hero_image"}:
            mime = image_types.get(source.suffix.lower())
            if not mime:
                raise ValueError(f"Unsupported image format: {value}")
            return "data:" + mime + ";base64," + base64.b64encode(source.read_bytes()).decode("ascii")
        if key in {"url", "primary_url", "secondary_url"}:
            copies[value] = source
            return quote(value, safe="/-._~")
        return value
    return visit(payload), copies


def copy_event_pages(out):
    """Publish standalone, self-contained event pages at stable URLs."""
    destination = out / "events"
    if destination.exists():
        shutil.rmtree(destination)
    pages = []
    for source in sorted((ROOT / "src/events").glob("*/index.html")):
        target = destination / source.parent.name / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        pages.append(target.relative_to(out).as_posix())
    return pages


def build():
    site = public_site(read_json("content/site.json"))
    curated = read_json("content/items.json")
    items = curated.get("items", {})
    publications = read_json("data/publications.json")
    presentations = read_json("data/presentations.json")
    known = {record["id"] for record in publications + presentations}
    unknown = set(items) - known
    if unknown:
        raise ValueError("Unknown content IDs: " + ", ".join(sorted(unknown)))
    def visible(record):
        return not record.get("source_missing") and not items.get(record["id"], {}).get("hidden", False)
    publications = [record for record in publications if visible(record)]
    presentations = [record for record in presentations if visible(record)]
    active = {record["id"] for record in publications + presentations}
    payload = {
        "site": site,
        "publications": publications,
        "presentations": presentations,
        "content": {"schema_version": 1, "items": {key: value for key, value in items.items() if key in active}},
        "world": read_json("content/world-land.geojson"),
    }
    payload, asset_copies = prepare_assets(payload)
    html = (ROOT / "src/index.html").read_text(encoding="utf-8")
    css = (ROOT / "src/styles.css").read_text(encoding="utf-8")
    app = (ROOT / "src/app.js").read_text(encoding="utf-8")
    for svg in (ROOT / "src").glob("*.svg"):
        uri = "data:image/svg+xml;base64," + base64.b64encode(svg.read_bytes()).decode("ascii")
        html = html.replace(svg.name, uri)
        css = css.replace(svg.name, uri)
        app = app.replace(svg.name, uri)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html, css_count = re.subn(r'<link\b[^>]*href=["\'](?:\./)?styles\.css["\'][^>]*>', lambda _: "<style>\n" + css + "\n</style>", html)
    html, data_count = re.subn(r'<script\b[^>]*src=["\'](?:\./)?data\.js["\'][^>]*>\s*</script>', lambda _: "<script>window.HOMEPAGE_DATA=" + encoded + ";</script>", html)
    safe_app = re.sub(r"</script", r"<\\/script", app, flags=re.IGNORECASE)
    html, app_count = re.subn(r'<script\b[^>]*src=["\'](?:\./)?app\.js["\'][^>]*>\s*</script>', lambda _: "<script>\n" + safe_app + "\n</script>", html)
    if (css_count, data_count, app_count) != (1, 1, 1):
        raise ValueError(f"Expected stylesheet/data/app includes exactly once, got {css_count}/{data_count}/{app_count}")
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    if (out / "assets").exists():
        shutil.rmtree(out / "assets")
    for relative, source in asset_copies.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (out / "index.html").write_text(html, encoding="utf-8")
    event_pages = copy_event_pages(out)
    print(json.dumps({"output": "dist/index.html", "event_pages": event_pages, "publications": len(publications), "presentations": len(presentations), "people": len(site["people"]), "bytes": len(html.encode("utf-8"))}, ensure_ascii=False))


if __name__ == "__main__":
    build()
