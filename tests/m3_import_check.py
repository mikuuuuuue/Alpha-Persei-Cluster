"""M3 checks for evidence gaps and the no-write apply gate."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import pickle
import struct
import time
import zlib
from contextlib import redirect_stdout
from contextlib import closing
import importlib.util
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DEFAULT = (ROOT / "Alpha-Persei-Captures" /
                   "2026-09-26_登录" / "rebuilt")
sys.path.insert(0, str(ROOT / "v5_server"))

from capture_import import read_snapshot
import save_generator
import capture_import
from save_slot_manager import SaveSlotManager
from account_db import AccountDB
import login
import codec
import generator
from core import Connection
from inventory_service import InventoryService
from mail_service import MailService

_CLI_SPEC = importlib.util.spec_from_file_location(
    "import_capture_archive", ROOT / "tools/import_capture_archive.py")
_CLI = importlib.util.module_from_spec(_CLI_SPEC)
_CLI_SPEC.loader.exec_module(_CLI)


_PUBLISH_WORKER = r"""import json,pickle,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import save_generator,capture_import
save_generator.SLOTS=Path(sys.argv[2])
uid=int(sys.argv[4]); name=sys.argv[5]; db=None
try:
    if sys.argv[6]=='ordinary':
        save_generator.create_save(name,save_generator.SaveOptions(uid=uid,nick='Concurrent',support_mail=False))
    else:
        snapshot=pickle.loads(Path(sys.argv[3]).read_bytes())
        db,report=capture_import.build_imported_save(snapshot,uid)
        capture_import.publish_imported_save(db,report,name)
    print(json.dumps({'result':'published'}))
except Exception as exc:
    print(json.dumps({'result':'failed','reason':str(exc)},ensure_ascii=False))
finally:
    if db is not None: db.close()
"""

class CaptureImportTests(unittest.TestCase):
    capture_dir = CAPTURE_DEFAULT

    @classmethod
    def setUpClass(cls):
        cls.snapshot = cls._runtime_snapshot()

    @classmethod
    def _runtime_snapshot(cls):
        class Sock:
            def __init__(self): self.frames = []
            def settimeout(self, value): pass
            def sendall(self, frame): self.frames.append(bytes(frame))
        uid = 880000009999
        source, _ = save_generator.build_save_workspace(save_generator.SaveOptions(uid=uid, nick='Import fixture', level=93, support_mail=False, skip_intro=True, clear_through=5), uid)
        try:
            source.set_system_config('save.profile', 'capture_import_v1')
            source.set_currency(uid, 2, 777)
            source.set_material(uid, 41201, 3)
            source.execute('INSERT INTO servant(uid,id,prefab_id,stage,is_locked,owned) VALUES(?,701,2310001,1,0,1)', (uid,))
            context = Connection(uid=uid, db=source, generator=generator, codec_encode=codec.encode, codec_decode=codec.decode).to_handler_ctx()
            InventoryService.grant_items(context, uid, [(prefab, 1) for prefab in
                (310001, 320001, 330001, 340001, 350001, 360001)], source='gm')
            source.execute('DELETE FROM mail WHERE uid=?', (uid,))
            sock = Sock()
            with patch('ai_translator.AITranslator.trigger_login_greeting'):
                login.send_login_flood(sock, source, uid, generator, frame_delay=0, log=lambda *a, **k: None)
            frames = []
            protocols = {}
            end = None
            for i, frame in enumerate(sock.frames, 1):
                cmd = struct.unpack('>H', frame[5:7])[0] | (65536 if frame[4] & 1 else 0)
                raw = zlib.decompress(frame[11:]) if frame[2] & 1 else frame[11:]
                if cmd in capture_import.REQUIRED_COMMANDS and cmd not in (12009, 60201):
                    raw = generator.gen_payload(cmd, uid=uid, db=source, res_version='321') or b''
                value = codec.decode(raw, 'sc_' + str(cmd)) if raw else {}
                if cmd == 60201:
                    activity_id = value['activity_id']
                    state = source.query('SELECT point FROM activity_point WHERE uid=? AND activity_id=?', (uid, activity_id))
                    rewards = source.query('SELECT reward_id FROM activity_point_reward WHERE uid=? AND activity_id=? ORDER BY reward_id', (uid, activity_id))
                    value = {'activity_id': activity_id, 'point': state[0]['point'] if state else 0, 'reward_list': [row['reward_id'] for row in rewards]}
                    raw = codec.encode('sc_60201', value)
                    value = codec.decode(raw, 'sc_60201')
                f = capture_import.CapturedFrame(cmd, raw, 'synthetic-current-login', i, struct.unpack('>H', frame[9:11])[0], bool(frame[2] & 1), value, time.time(), struct.unpack('>H', frame[7:9])[0], frame[4])
                if cmd == 10201:
                    end = f
                elif cmd in capture_import.MAPPED_COMMANDS:
                    frames.append(f)
                    if cmd != 10043:
                        protocols.setdefault(cmd, []).append(value)
            from mail_service import MailService
            mailer = MailService(source)
            mails = mailer.get_inbox_list(uid)
            for row in mails:
                row['content_list'] = mailer.get_mail_detail(uid, row['id'])['content_list']
            supplement = [capture_import.CapturedFrame(30003, b'', 'synthetic-mail', 1, 1, False, {'mail_list': mails}, time.time())] if mails else []
            snap = capture_import.CaptureSnapshot(uid, '307', '321', 'synthetic-current-login', frames, supplement, {}, protocols, end_frame=end)
            return snap
        finally:
            source.close()

    def _build_candidate(self, uid):
        return capture_import.build_imported_save(deepcopy(self.snapshot), uid)

    def test_real_capture_exposes_missing_mail_details(self):
        self.assertTrue(self.capture_dir.is_dir(), f"抓包目录不存在：{self.capture_dir}")
        snapshot = read_snapshot(self.capture_dir)
        summary = snapshot.protocol_data.get(30001, [{}])[0]
        self.assertEqual(summary.get("total_number"), 10)
        self.assertFalse(snapshot.supplement_frames)
        self.assertTrue(any("普通邮箱明细 10 封" in row["data"]
                            for row in snapshot.missing_data))

    def test_preview_and_blocked_apply_preserve_existing_files_registry_and_keys(self):
        self.assertTrue(self.capture_dir.is_dir(), f"抓包目录不存在：{self.capture_dir}")
        with tempfile.TemporaryDirectory(prefix="m3-import-") as temporary:
            slots = Path(temporary)
            registry = slots / "data" / "slot_registry.json"
            registry.parent.mkdir()
            registry.write_text('{"3":"Existing.db"}', encoding='utf-8')
            with closing(sqlite3.connect(slots / 'Existing.db')) as existing:
                existing.execute('CREATE TABLE users(uid INTEGER)')
                existing.execute('INSERT INTO users VALUES(99)')
                existing.commit()
            (slots / 'test-only.key').write_bytes(b'synthetic test key')
            before_contents = {str(path.relative_to(slots)): path.read_bytes()
                               for path in slots.rglob('*') if path.is_file()}
            before_files = sorted(path.name for path in slots.glob("*.db"))
            before_registry = registry.read_bytes() if registry.exists() else None
            output = io.StringIO()
            with patch.object(save_generator, "SLOTS", slots), redirect_stdout(output):
                result = _CLI.main([
                    str(self.capture_dir), "--name", "M3-Blocked-Check", "--apply",
                ])
            after_files = sorted(path.name for path in slots.glob("*.db"))
            after_registry = registry.read_bytes() if registry.exists() else None
            self.assertEqual(result, 2, output.getvalue())
            self.assertEqual(before_files, after_files)
            self.assertEqual(before_registry, after_registry)
            with patch.object(save_generator, 'SLOTS', slots), redirect_stdout(output):
                self.assertEqual(_CLI.main([str(self.capture_dir), '--name', 'Preview']), 0)
            self.assertEqual({str(path.relative_to(slots)): path.read_bytes()
                              for path in slots.rglob('*') if path.is_file()}, before_contents)

    def test_login_push_reads_past_192_and_stops_at_marker(self):
        db = AccountDB.new_save_workspace()
        try:
            for seq in range(1, 206):
                cmd = 10201 if seq == 201 else 10043 if seq == 1 else 12009
                db.execute("INSERT INTO login_push(seq,cmd,header,payload,dynamic,payload_json) "
                           "VALUES(?,?,?,?,?,?)", (seq, cmd, b"\0" * 11, b"", 0, None))
            frames = login.load_login_push(db)
            self.assertEqual(len(frames), 201)
            self.assertEqual(frames[-1][1], 10201)
        finally:
            db.close()

    def test_reader_rejects_missing_end_marker_and_other_session_mail(self):
        def frame(cmd, direction, data, ts, index):
            schema = ("cs_" if direction == "up" else "sc_") + str(cmd)
            payload = codec.encode(schema, data) or b""
            return dict(cmd=cmd, frame_cmd=cmd, dir=direction, type="tcp",
                        payload_hex=payload.hex(), payload_len=len(payload),
                        compressed=False, flag=0, index=index, server_idx=index,
                        ts=ts)

        with tempfile.TemporaryDirectory(prefix="m3-capture-") as temporary:
            root = Path(temporary)
            rows = {
                "tcp_1_up_8105.jsonl": [
                    frame(10042, "up", dict(user_id=9, client_vs="307", resource_vs="321"), 1, 1),
                    frame(10200, "up", {}, 2, 2),
                ],
                "tcp_2_down_8105.jsonl": [
                    frame(10043, "down", {}, 3, 1),
                ],
            }
            for name, content in rows.items():
                (root / name).write_text("".join(json.dumps(row) + "\n" for row in content), "utf-8")
            (root / "summary.md").write_text(
                "| tcp_1_up_8105.jsonl | up | 127.0.0.1:12345 → 47.117.173.152:8105 | 0 |\n"
                "| tcp_2_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:12345 | 0 |\n",
                "utf-8")
            with self.assertRaisesRegex(ValueError, "10201"):
                read_snapshot(root)

            rows["tcp_2_down_8105.jsonl"].append(frame(10201, "down", {}, 4, 2))
            rows["tcp_3_up_8105.jsonl"] = [frame(30002, "up", {}, 5, 1)]
            rows["tcp_4_down_8105.jsonl"] = [frame(30003, "down", {}, 6, 1)]
            for name in ("tcp_2_down_8105.jsonl", "tcp_3_up_8105.jsonl", "tcp_4_down_8105.jsonl"):
                (root / name).write_text("".join(json.dumps(row) + "\n" for row in rows[name]), "utf-8")
            with (root / "summary.md").open("a", encoding="utf-8") as summary:
                summary.write("| tcp_3_up_8105.jsonl | up | 127.0.0.1:23456 → 47.117.173.152:8105 | 0 |\n")
                summary.write("| tcp_4_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:23456 | 0 |\n")
            with self.assertRaisesRegex(ValueError, "唯一绑定"):
                read_snapshot(root)
            (root / 'tcp_4_down_8105.jsonl').unlink()
            with self.assertRaisesRegex(ValueError, '唯一绑定'):
                read_snapshot(root)

    def test_runtime_snapshot_builds_and_registers_with_actual_values(self):
        with tempfile.TemporaryDirectory(prefix="m3-publish-") as temporary:
            slots = Path(temporary)
            db, report = self._build_candidate(880000000001)
            self.addCleanup(db.close)
            original = list(db._conn().iterdump())
            header = db.query('SELECT header FROM login_push WHERE cmd=10201')[0]['header']
            self.assertEqual(struct.unpack('>HHH', header[5:11]),
                             (10201, self.snapshot.end_frame.frame_index, self.snapshot.end_frame.server_idx))
            self.assertEqual(bool(header[2]), self.snapshot.end_frame.compressed)
            self.assertFalse(report.validation['isolated_login'])
            with patch.object(save_generator, "SLOTS", slots):
                published = capture_import.publish_imported_save(db, report, "Synthetic-Runtime")
            path = slots / "Synthetic-Runtime.db"
            self.assertTrue(path.is_file())
            self.assertTrue(published.slot_registration["registered"])
            self.assertTrue(published.validation['isolated_login'])
            self.assertEqual(published.validation['compared_protocols'], len(capture_import.REQUIRED_COMMANDS))
            self.assertGreater(published.validation['decoded_login_frames'], 0)
            self.assertIn(path.name, SaveSlotManager(str(slots))._load_registry().values())
            self.assertEqual(list(db._conn().iterdump()), original)
            with closing(sqlite3.connect(path)) as check:
                self.assertEqual(check.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                owner = check.execute("SELECT value FROM server_global_config WHERE key='save.owner_uid'").fetchone()
                self.assertEqual(int(owner[0]), published.target_uid)
                self.assertEqual(check.execute('SELECT num FROM currency WHERE uid=? AND id=2', (published.target_uid,)).fetchone()[0], 777)
                self.assertEqual(check.execute('SELECT num FROM material WHERE uid=? AND id=41201', (published.target_uid,)).fetchone()[0], 3)
                self.assertEqual(check.execute('SELECT prefab_id FROM servant WHERE uid=? AND id=701', (published.target_uid,)).fetchone()[0], 2310001)
                self.assertEqual(check.execute('SELECT COUNT(*) FROM equip WHERE uid=?', (published.target_uid,)).fetchone()[0], report.row_counts['equip'])
            self.assertFalse((slots / ".import-staging").exists())

    def test_filtered_real_capture_rejects_projection_loss(self):
        snapshot = read_snapshot(self.capture_dir)
        snapshot.protocol_data[30001] = [dict(total_number=0, unread_number=0)]
        snapshot.login_frames = [frame for frame in snapshot.login_frames
                                 if frame.cmd in capture_import.MAPPED_COMMANDS]
        snapshot.missing_data, snapshot.issues = capture_import._assess(snapshot)
        db, report = capture_import.build_imported_save(snapshot, 880000000003)
        self.addCleanup(db.close)
        with tempfile.TemporaryDirectory(prefix='m3-reject-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            with self.assertRaises(ValueError) as error:
                capture_import.publish_imported_save(db, report, 'Must-Reject')
            self.assertFalse(list(Path(temporary).glob('*.db')))
        self.assertIsInstance(error.exception.args[0], capture_import.ImportReport)
        self.assertFalse(error.exception.args[0].validation.get('isolated_login'))
        self.assertTrue(error.exception.args[0].missing_data)

    def test_process_competition_never_publishes_duplicate_name_or_uid(self):
        script = _PUBLISH_WORKER
        for mode, names in (('import', ['Same', 'Same']), ('import', ['Alpha', 'Beta']),
                            ('ordinary', ['Imported', 'Ordinary'])):
            with self.subTest(mode=mode, names=names), tempfile.TemporaryDirectory(prefix='m3-race-') as temporary:
                root = Path(temporary)
                slots = root / 'slots'
                slots.mkdir()
                fixture = root / 'snapshot.pickle'
                fixture.write_bytes(pickle.dumps(self.snapshot))
                processes = [subprocess.Popen([
                    sys.executable, '-B', '-X', 'utf8', '-c', script, str(ROOT / 'v5_server'),
                    str(slots), str(fixture), '880000000004', name,
                    mode if index else 'import'], cwd=root,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                    for index, name in enumerate(names)]
                results = []
                for process in processes:
                    stdout, stderr = process.communicate(timeout=180)
                    self.assertEqual(process.returncode, 0, stderr)
                    results.append(json.loads(stdout.splitlines()[-1]))
                self.assertEqual([row['result'] for row in results].count('published'), 1, results)
                self.assertEqual([row['result'] for row in results].count('failed'), 1, results)
                failure = next(row['reason'] for row in results if row['result'] == 'failed')
                if '另一个进程正在建档' in failure:
                    loser = next(index for index, row in enumerate(results) if row['result'] == 'failed')
                    retry = subprocess.run([
                        sys.executable, '-B', '-X', 'utf8', '-c', script, str(ROOT / 'v5_server'),
                        str(slots), str(fixture), '880000000004', names[loser],
                        mode if loser else 'import'], cwd=root, capture_output=True,
                        text=True, encoding='utf-8', timeout=180)
                    self.assertEqual(retry.returncode, 0, retry.stderr)
                    rejected = json.loads(retry.stdout.splitlines()[-1])
                    self.assertEqual(rejected['result'], 'failed', rejected)
                    failure = rejected['reason']
                self.assertTrue('UID' in failure or '已存在' in failure, results)
                self.assertEqual(len(list(slots.glob('*.db'))), 1)
                self.assertEqual(save_generator.used_uids(slots), {880000000004})
                registry = SaveSlotManager(str(slots)).sync_slot_registry()
                self.assertEqual(len(registry), 1)
                self.assertFalse((slots / '.import-staging').exists())

    def test_publication_with_registry_sync_and_delete_preserves_existing_slot(self):
        registry_worker = r"""import json,sqlite3,sys,time
from contextlib import closing
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import save_slot_manager as slots
from account_db import AccountDB
root=Path(sys.argv[2]).resolve()
manager=slots.SaveSlotManager(str(root)); manager.configure_host('127.0.0.1')
def backup(path):
    target=root/'backups'/'deleted.stage';target.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as source:
        with closing(sqlite3.connect(target)) as copy: source.backup(copy)
    return str(target)
def recycle(paths):
    for path in paths:
        source=Path(path).resolve()
        if source.parent != root/'Trash' or not source.is_dir():
            raise RuntimeError('测试回收路径越界')
        for child in source.iterdir():
            if child.is_symlink() or not child.is_file() or child.resolve().parent != source:
                raise RuntimeError('测试回收文件越界')
            child.replace(root/'Trash'/(child.name+'.stage'))
        source.rmdir()
AccountDB.backup_save_file=staticmethod(backup)
slots._recycle_save_files=recycle
with manager._registry_lock():
    (root/'registry-held').write_text('ready')
    manager.toggle_delete_mode('127.0.0.1')
    ok,reason=manager.delete_slot_save(3,'127.0.0.1')
    if not ok: raise RuntimeError(reason)
    deadline=time.monotonic()+30
    while not (root/'Incoming.db').is_file():
        if time.monotonic()>deadline: raise RuntimeError('导入未发布文件')
        time.sleep(.01)
    registry=manager.sync_slot_registry()
print(json.dumps({'registry':registry}))
"""
        with tempfile.TemporaryDirectory(prefix='m3-registry-race-') as temporary:
            root = Path(temporary)
            slots = root / 'slots'
            slots.mkdir()
            for name, uid in (('Delete.db', 8001), ('Keep.db', 8002)):
                with closing(sqlite3.connect(slots / name)) as existing:
                    existing.execute('CREATE TABLE users(uid INTEGER)')
                    existing.execute('INSERT INTO users VALUES(?)', (uid,))
                    existing.commit()
            manager = SaveSlotManager(str(slots))
            before = manager.sync_slot_registry()
            self.assertEqual(before, {3: 'Delete.db', 4: 'Keep.db'})
            keep_bytes = (slots / 'Keep.db').read_bytes()
            fixture = root / 'snapshot.pickle'
            fixture.write_bytes(pickle.dumps(self.snapshot))
            mutator = subprocess.Popen([
                sys.executable, '-B', '-X', 'utf8', '-c', registry_worker,
                str(ROOT / 'v5_server'), str(slots)], cwd=root,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            importer = None
            try:
                deadline = time.monotonic() + 10
                while not (slots / 'registry-held').exists():
                    self.assertIsNone(mutator.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(.01)
                importer = subprocess.Popen([
                    sys.executable, '-B', '-X', 'utf8', '-c', _PUBLISH_WORKER,
                    str(ROOT / 'v5_server'), str(slots), str(fixture),
                    '880000000009', 'Incoming', 'import'], cwd=root,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                stdout, stderr = importer.communicate(timeout=180)
                self.assertEqual(importer.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout.splitlines()[-1])['result'], 'published', stdout)
                _, stderr = mutator.communicate(timeout=180)
                self.assertEqual(mutator.returncode, 0, stderr)
            finally:
                for process in (mutator, importer):
                    if process is not None and process.poll() is None:
                        process.terminate()
                        process.communicate(timeout=10)
            registry = manager._load_registry()
            self.assertEqual(registry, {3: 'Incoming.db', 4: 'Keep.db'})
            self.assertEqual((slots / 'Keep.db').read_bytes(), keep_bytes)
            self.assertFalse((slots / 'Delete.db').exists())
            self.assertTrue((slots / 'Trash' / 'Delete.db.stage').is_file())
            self.assertTrue((slots / 'backups' / 'deleted.stage').is_file())
            self.assertFalse((slots / '.import-staging').exists())

    def test_registry_failure_preserves_complete_file_and_refresh_can_register(self):
        with tempfile.TemporaryDirectory(prefix='m3-registry-') as temporary:
            slots = Path(temporary)
            db, report = self._build_candidate(880000000005)
            self.addCleanup(db.close)
            with patch.object(save_generator, 'SLOTS', slots), patch.object(
                    SaveSlotManager, 'register_new_save', side_effect=OSError('isolated registry failure')):
                published = capture_import.publish_imported_save(db, report, 'Retry')
            self.assertFalse(published.slot_registration['registered'])
            path = slots / 'Retry.db'
            with closing(sqlite3.connect(path)) as check:
                self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertIn(path.name, SaveSlotManager(str(slots)).sync_slot_registry().values())

    def test_literal_mail_template_resolves_body_and_parameterized_template_blocks(self):
        from mail_service import TEMPLATES_PATH
        templates = json.loads(Path(TEMPLATES_PATH).read_text('utf-8'))
        literal = next(row for row in templates if row.get('desc') and '%' not in row['desc']
                       and '{' not in row['desc'])
        snapshot = deepcopy(self.snapshot)
        mail = snapshot.supplement_frames[0].decoded['mail_list'][0]
        mail.pop('content_list')
        mail['mail_template_id'] = literal['id']
        snapshot = replace(snapshot)
        db, _ = capture_import.build_imported_save(snapshot, 880000000010)
        self.addCleanup(db.close)
        content = json.loads(db.query('SELECT content_json FROM mail')[0]['content_json'])
        self.assertEqual(content, [dict(text=literal['desc'], content_type=2)])
        self.assertNotEqual(content[0]['text'], mail['title'])
        parameterized = next(row for row in templates if '%' in row.get('desc', ''))
        mail = snapshot.supplement_frames[0].decoded['mail_list'][0]
        mail['mail_template_id'] = parameterized['id']
        snapshot = replace(snapshot)
        with self.assertRaises(ValueError) as error:
            capture_import.build_imported_save(snapshot, 880000000011)
        self.assertTrue(any(row['data'] == '模板正文解析' for row in error.exception.args[0].missing_data))

    def test_preview_and_build_use_the_same_frozen_mail_template_bytes(self):
        with tempfile.TemporaryDirectory(prefix='m3-templates-') as temporary:
            archive = Path(temporary) / 'templates.json'
            original = json.dumps([dict(id=701, title='Template', desc='Frozen template body')]).encode()
            archive.write_bytes(original)
            snapshot = deepcopy(self.snapshot)
            mail = snapshot.supplement_frames[0].decoded['mail_list'][0]
            mail.pop('content_list')
            mail['mail_template_id'] = 701
            with patch('mail_service.TEMPLATES_PATH', str(archive)):
                snapshot = replace(snapshot)
                preview = capture_import._report(snapshot)
                archive.write_text(json.dumps([dict(id=701, title='Changed', desc='Changed body')]), 'utf-8')
                db, built = capture_import.build_imported_save(snapshot, 880000000012)
            self.addCleanup(db.close)
            key = 'catalog:mail_archive/mail_templates.json'
            self.assertEqual(preview.source_sha256[key], hashlib.sha256(original).hexdigest())
            self.assertEqual(built.source_sha256[key], preview.source_sha256[key])
            self.assertEqual(json.loads(db.query('SELECT content_json FROM mail')[0]['content_json']),
                             [dict(text='Frozen template body', content_type=2)])

    def test_existing_staging_directory_is_never_claimed_or_deleted(self):
        with tempfile.TemporaryDirectory(prefix='m3-stage-collision-') as temporary:
            slots = Path(temporary)
            foreign = slots / '.import-staging' / 'collision'
            foreign.mkdir(parents=True)
            marker = foreign / 'keep.txt'
            marker.write_text('existing data', encoding='utf-8')
            db, report = self._build_candidate(880000000008)
            self.addCleanup(db.close)
            with patch.object(save_generator, 'SLOTS', slots), patch.object(
                    capture_import.uuid, 'uuid4', return_value=SimpleNamespace(hex='collision')):
                with self.assertRaises(FileExistsError):
                    capture_import.publish_imported_save(db, report, 'Stage-Collision')
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text('utf-8'), 'existing data')
            self.assertFalse((slots / 'Stage-Collision.db').exists())

    def test_full_slots_keep_original_mappings_and_complete_unassigned_file(self):
        with tempfile.TemporaryDirectory(prefix='m3-full-') as temporary:
            slots = Path(temporary)
            for index in range(30):
                with closing(sqlite3.connect(slots / f'Old-{index:02}.db')) as existing:
                    existing.execute('CREATE TABLE users(uid INTEGER)')
                    existing.execute('INSERT INTO users VALUES(?)', (9000 + index,))
                    existing.commit()
            manager = SaveSlotManager(str(slots))
            before = manager.sync_slot_registry()
            db, report = self._build_candidate(880000000006)
            self.addCleanup(db.close)
            with patch.object(save_generator, 'SLOTS', slots):
                published = capture_import.publish_imported_save(db, report, 'Unassigned')
            self.assertFalse(published.slot_registration['registered'])
            self.assertTrue((slots / 'Unassigned.db').is_file())
            self.assertEqual(manager._load_registry(), before)

    def test_automatic_uid_is_allocated_and_rebuilt_inside_lock(self):
        with tempfile.TemporaryDirectory(prefix='m3-uid-') as temporary:
            slots = Path(temporary)
            uid = 880000000007
            with closing(sqlite3.connect(slots / 'Existing.db')) as existing:
                existing.execute('CREATE TABLE users(uid INTEGER)')
                existing.execute('INSERT INTO users VALUES(?)', (uid,))
                existing.commit()
            db, report = self._build_candidate(uid)
            self.addCleanup(db.close)
            report.validation['uid_generated'] = True
            with patch.object(save_generator, 'SLOTS', slots):
                published = capture_import.publish_imported_save(db, report, 'Generated')
            self.assertNotEqual(published.target_uid, uid)
            self.assertEqual(save_generator.used_uids(slots), {uid, published.target_uid})
            with closing(sqlite3.connect(published.output_path)) as check:
                self.assertEqual(check.execute('SELECT uid FROM users').fetchall(), [(published.target_uid,)])
                self.assertEqual(check.execute('SELECT account FROM users').fetchone()[0], f'capture_{published.target_uid}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_dir", nargs="?", type=Path, default=CAPTURE_DEFAULT)
    CaptureImportTests.capture_dir = parser.parse_args().capture_dir
    unittest.main(verbosity=2)
