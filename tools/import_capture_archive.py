"""Preview or apply one evidence-bound capture import."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "v5_server"))

from capture_import import (ImportReport, _report, build_imported_save,
                            build_imported_hero_save, publish_imported_save, read_snapshot,
                            supplement_mail_details)
import save_generator


def main(argv=None):
    parser = argparse.ArgumentParser(description="从单次 8105 登录抓包导入新存档")
    parser.add_argument("rebuilt_dir", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--uid", type=int)
    parser.add_argument('--scope', choices=('full', 'heroes', 'available'), default='full',
                        help='full 完整恢复；heroes 角色恢复；available 恢复已核实字段并报告缺项')
    parser.add_argument('--mail-details-from', type=Path, action='append', default=[],
                        help='从同账号的已验证重建目录补充匹配邮件正文；不复制账号状态')
    parser.add_argument("--apply", action="store_true", help="尝试构建；证据不完整时零写入退出")
    args = parser.parse_args(argv)
    try:
        snapshot = read_snapshot(args.rebuilt_dir)
        for source in args.mail_details_from:
            supplement_mail_details(snapshot, read_snapshot(source))
        save_generator.save_filename(args.name)
        target_uid = args.uid
        if target_uid is None:
            target_uid = save_generator.allocate_uid(save_generator.used_uids(save_generator.SLOTS))
        report = _report(snapshot, target_uid, scope=args.scope)
        if args.scope == 'available':
            from capture_account_state import recovery_manifest, verified_commands
            report.validation['recovery_manifest'] = recovery_manifest(snapshot)
            report.validation['verified_commands'] = verified_commands(snapshot)
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
        builder = build_imported_hero_save if args.scope == 'heroes' else build_imported_save
        build_options = {} if args.scope == 'heroes' else dict(scope=args.scope)
        db, built_report = builder(snapshot, target_uid, **build_options)
        built_report.validation['uid_generated'] = args.uid is None
        try:
            published = publish_imported_save(db, built_report, args.name)
        finally:
            db.close()
        print(json.dumps({"ready": True, "report": published.public_data()},
                         ensure_ascii=False, indent=2))
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())
