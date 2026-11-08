#!/usr/bin/env python3
"""Validate Excel and Zotero CSVs, build in isolation, then replace outputs.

No existing data/content/dist output is replaced until all three stages pass.
On failure, consult reports/update-report.json; fix input and run again.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from import_content import run_import as import_content
from import_zotero import run_import as import_zotero, _atomic_outputs

ROOT = Path(__file__).resolve().parents[1]


def _promote(stage, root):
    """Commit directories together, restoring all originals on a rename error."""
    backup = stage / ".backup"
    backup.mkdir()
    previous, promoted = [], []
    try:
        for name in ("data", "content", "dist"):
            destination = root / name
            if destination.exists():
                destination.replace(backup / name)
                previous.append(name)
            (stage / name).replace(destination)
            promoted.append(name)
    except BaseException:
        for name in reversed(promoted):
            destination = root / name
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists():
                destination.unlink()
        for name in reversed(previous):
            (backup / name).replace(root / name)
        raise


def _input_path(path, root, default):
    return Path(path).resolve() if path is not None else root / default


def run_update(root=ROOT, papers=None, presentations=None, workbook=None,
               check=False, namespace="bk-zotero", resolutions=None):
    root = Path(root).resolve()
    papers = _input_path(papers, root, "input/zotero-publications.csv")
    presentations = _input_path(presentations, root, "input/zotero-presentations.csv")
    workbook = _input_path(workbook, root, "input/content.xlsx")
    report = {"schema_version": 1, "status": "failed", "applied": False,
              "check_only": bool(check), "started_at": datetime.now(timezone.utc).isoformat(),
              "stages": {}, "errors": [], "help": "reports/의 상세 보고서에서 시트·행·열 또는 Zotero 충돌을 수정한 뒤 다시 실행하세요. 기존 data/content/dist는 실패 시 유지됩니다."}
    detailed = {}
    lock = root / ".update.lock"
    locked = False
    try:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
            locked = True
        except FileExistsError:
            report["errors"].append({"code": "update_already_running", "message": "다른 갱신이 실행 중입니다. 종료 후 다시 실행하세요. 비정상 종료된 경우 실행 중인 갱신이 없는지 확인한 뒤 .update.lock을 제거하세요."})
            return report
        missing = [path.name for path in (papers, presentations, workbook) if not path.is_file()]
        if missing:
            report["errors"].append({"code": "missing_input", "files": missing,
                                     "message": "input/에 Excel 1개와 Zotero CSV 2개를 준비하세요."})
            return report
        with tempfile.TemporaryDirectory(prefix=".bresearch-update-", dir=root.parent) as temporary:
            stage = Path(temporary)
            for name in ("scripts", "src", "content", "data", "assets"):
                source = root / name
                if source.is_dir():
                    shutil.copytree(source, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (stage / "data").mkdir(exist_ok=True)
            (stage / "content").mkdir(exist_ok=True)
            zotero = import_zotero(papers, presentations, stage / "data", namespace, resolutions)
            detailed["zotero-import-report.json"] = zotero
            report["stages"]["zotero"] = {"status": zotero["status"], "counts": zotero["counts"]}
            if not zotero["applied"]:
                report["errors"].append({"code": "zotero_import_failed", "message": "Zotero 입력 또는 ID 연결을 확인하세요. reports/zotero-import-report.json 참조."})
                return report
            content = import_content(workbook, stage)
            detailed["content-import-report.json"] = content
            report["stages"]["content"] = {"status": content["status"], "counts": content["counts"]}
            if not content["applied"]:
                report["errors"].append({"code": "content_import_failed", "message": "Excel 입력을 확인하세요. reports/content-import-report.json 참조."})
                return report
            built = subprocess.run([sys.executable, str(stage / "scripts/build_site.py")], cwd=stage,
                                   text=True, encoding="utf-8", capture_output=True, timeout=120, check=False)
            report["stages"]["build"] = {"status": "ok" if built.returncode == 0 else "failed",
                                           "returncode": built.returncode,
                                           "stdout": built.stdout[-12000:], "stderr": built.stderr[-12000:]}
            if built.returncode != 0 or not (stage / "dist/index.html").is_file():
                report["errors"].append({"code": "build_failed", "message": "화면 생성 검증에 실패했습니다. 기존 출력은 유지됩니다."})
                return report
            if not check:
                _promote(stage, root)
                report["applied"] = True
            report["status"] = "ok"
            report["help"] = "검증 완료. --check 실행은 기존 출력을 바꾸지 않습니다." if check else "갱신 완료. dist/index.html이 최신 결과입니다. data/registry.json을 함께 버전 관리하세요."
    except Exception as exc:
        # Avoid exposing absolute local paths from raw CSV or workbook errors.
        message = str(exc)
        for path in (papers, presentations, workbook, root):
            message = message.replace(str(path), path.name)
        report["errors"].append({"code": "update_exception", "message": f"{type(exc).__name__}: {message}"})
    finally:
        if locked:
            lock.unlink(missing_ok=True)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_outputs(root / "reports", {**detailed, "update-report.json": report})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--papers", type=Path)
    parser.add_argument("--presentations", type=Path)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--namespace", default="bk-zotero")
    parser.add_argument("--resolutions", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = run_update(**vars(args))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
