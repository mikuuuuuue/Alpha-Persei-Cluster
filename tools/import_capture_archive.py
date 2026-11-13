"""Preview or apply one evidence-bound capture import."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "v5_server"))

from capture_import import (ImportReport, _report, build_imported_save,
                            publish_imported_save, read_snapshot)
import save_generator


def main(argv=None):
    parser = argparse.ArgumentParser(description="从单次 8105 登录抓包导入新存档")
    parser.add_argument("rebuilt_dir", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--uid", type=int)
    parser.add_argument("--apply", action="store_true", help="尝试构建；证据不完整时零写入退出")
    args = parser.parse_args(argv)
    try:
        snapshot = read_snapshot(args.rebuilt_dir)
        save_generator.save_filename(args.name)
        target_uid = args.uid
        if target_uid is None:
            target_uid = save_generator.allocate_uid(save_generator.used_uids(save_generator.SLOTS))
        report = _report(snapshot, target_uid)
        report.validation["uid_generated"] = args.uid is None
        report.validation["protocol_counts"] = {
            str(cmd): len(rows) for cmd, rows in sorted(snapshot.protocol_data.items())
        }
        print(json.dumps({
            "mode": "apply" if args.apply else "preview",
            "name": args.name,
            "ready": not report.issues and not report.missing_data,
            "report": report.public_data(),
        }, ensure_ascii=False, indent=2))
        if not args.apply:
            return 0
        if report.issues or report.missing_data:
            return 2
        db, built_report = build_imported_save(snapshot, target_uid)
        built_report.validation['uid_generated'] = args.uid is None
        try:
            published = publish_imported_save(db, built_report, args.name)
        finally:
            db.close()
        print(json.dumps({"ready": True, "report": published.public_data()},
                         ensure_ascii=False, indent=2))
    except ValueError as exc:
        if exc.args and isinstance(exc.args[0], ImportReport):
            print(json.dumps({"ready": False, "report": exc.args[0].public_data()},
                             ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"ready": False, "issues": [str(exc)]}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"ready": False, "issues": [str(exc)]}, ensure_ascii=False))
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
