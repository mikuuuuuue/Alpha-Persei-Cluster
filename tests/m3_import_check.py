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
import logger
import codec
import generator
import capture_account_state
import gm_save_scope
from core import Connection, Core, CoreRequest
from inventory_service import InventoryService
from mail_service import MailService

_CLI_SPEC = importlib.util.spec_from_file_location(
    "import_capture_archive", ROOT / "tools/import_capture_archive.py")
_CLI = importlib.util.module_from_spec(_CLI_SPEC)
_CLI_SPEC.loader.exec_module(_CLI)


_PUBLISH_WORKER = r"""import json,pickle,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import account_db,logger,save_generator,capture_import
save_generator.SLOTS=Path(sys.argv[2])
logger._LOG_DIR=str(Path.cwd()/'logs')
uid=int(sys.argv[4]); name=sys.argv[5]; db=None
try:
    if sys.argv[6]=='ordinary':
        schema=Path(account_db.__file__).with_name('db_schema.sql').read_bytes()
        isolated=Path.cwd()/'v5_server'/'account_db.py'
        isolated.parent.mkdir(exist_ok=True)
        isolated.with_name('db_schema.sql').write_bytes(schema)
        account_db.__file__=str(isolated)
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
        isolation = tempfile.TemporaryDirectory(prefix='m3-logs-')
        cls.addClassCleanup(isolation.cleanup)
        log_patch = patch.multiple(logger, _LOG_DIR=str(Path(isolation.name) / 'logs'),
                                   _fh=None, _fh_path=None)
        log_patch.start()
        cls.addClassCleanup(log_patch.stop)
        cls.addClassCleanup(lambda: logger._fh.close() if logger._fh is not None else None)
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

    def _write_capture(self, root, snapshot=None):
        snapshot = deepcopy(snapshot or self.snapshot)
        end_time = snapshot.end_frame.timestamp

        def row(cmd, direction, data, timestamp, index):
            if cmd == 30003:
                from mail_service import TEMPLATES_PATH
                templates = json.loads(Path(TEMPLATES_PATH).read_text('utf-8'))
                literal = next(item for item in templates if item.get('desc')
                    and '%' not in item['desc'] and '{' not in item['desc'])
                data = deepcopy(data)
                for message in data['mail_list']:
                    message.pop('content_list', None)
                    message['mail_template_id'] = literal['id']
            payload = codec.encode(('cs_' if direction == 'up' else 'sc_') + str(cmd), data)
            return dict(cmd=cmd, frame_cmd=cmd, dir=direction, type='tcp',
                payload_hex=payload.hex(), payload_len=len(payload), compressed=False,
                flag=0, index=index, server_idx=index, ts=timestamp)

        upstream = [row(10042, 'up', dict(user_id=snapshot.source_uid,
            client_vs=snapshot.client_build, resource_vs=snapshot.resource_version), end_time - 4, 1),
            row(10200, 'up', {}, end_time - 2, 2)]
        downstream = [row(frame.cmd, 'down', frame.decoded,
            end_time - 3 if frame.cmd == 10043 else end_time - 1 + index / (len(snapshot.login_frames) + 1),
            index + 1) for index, frame in enumerate(snapshot.login_frames)]
        downstream.append(row(10201, 'down', snapshot.end_frame.decoded,
                              end_time, len(downstream) + 1))
        for query, response in ((30002, 30003), (30020, 30021)):
            if any(frame.cmd == response for frame in snapshot.supplement_frames):
                upstream.append(row(query, 'up', {}, end_time + 1, len(upstream) + 1))
        for index, frame in enumerate(snapshot.supplement_frames):
            timestamp = end_time + 2
            if frame.cmd in (30009, 30023):
                timestamp = end_time + 3 + index
                mail_id = frame.decoded['detail_info']['id']
                command, data = (30008, dict(id=mail_id)) if frame.cmd == 30009 else (30022, dict(mail_id=mail_id))
                upstream.append(row(command, 'up', data, timestamp - 0.5, len(upstream) + 1))
            downstream.append(row(frame.cmd, 'down', frame.decoded, timestamp, len(downstream) + 1))
        for name, rows in (('tcp_1_up_8105.jsonl', upstream), ('tcp_2_down_8105.jsonl', downstream)):
            (root / name).write_text(''.join(json.dumps(item) + '\n' for item in rows), 'utf-8')
        (root / 'summary.md').write_text(
            f'| tcp_1_up_8105.jsonl | up | 127.0.0.1:12345 → 47.117.173.152:8105 | {len(upstream)} | 0 |\n'
            f'| tcp_2_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:12345 | {len(downstream)} | 0 |\n', 'utf-8')

    def _login_packets(self, db, uid, version='321'):
        import timer_listeners
        timer_listeners.register_timer_listeners()
        sock = SimpleNamespace(frames=[], settimeout=lambda value: None)
        sock.sendall = sock.frames.append
        import res_version_manager
        with res_version_manager.connection_version(version), patch(
                'ai_translator.AITranslator.trigger_login_greeting'):
            login.send_login_flood(sock, db, uid, generator, frame_delay=0, log=lambda *a, **k: None)
        packets = {}
        for frame in sock.frames:
            self.assertEqual(struct.unpack('>H', frame[:2])[0], len(frame) - 2)
            command = struct.unpack('>H', frame[5:7])[0] | (65536 if frame[4] & 1 else 0)
            payload = zlib.decompress(frame[11:]) if frame[2] & 1 else frame[11:]
            packets.setdefault(command, []).append(codec.decode(payload, 'sc_' + str(command)) if payload else {})
        return packets

    def _cli_process(self, root, capture, *arguments):
        script = """import runpy,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import logger,save_generator
logger._LOG_DIR=str(Path.cwd()/'logs')
save_generator.SLOTS=Path(sys.argv[2])
sys.argv=sys.argv[3:]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', script,
            str(ROOT / 'v5_server'), str(root / 'slots'), str(ROOT / 'tools/import_capture_archive.py'),
            str(capture), *arguments], cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=180)

    def test_reader_rejects_missing_stream_residual_count_and_failed_login_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='m3-source-') as temporary:
            root = Path(temporary)
            capture = root / 'capture'
            capture.mkdir()
            self._write_capture(capture)
            self.assertFalse(read_snapshot(capture).missing_data)
            self.assertFalse(read_snapshot(capture).issues)
            original = {path.name: path.read_bytes() for path in capture.iterdir()}
            for defect in ('missing-pair', 'residual', 'count', 'failed', 'missing-result', 'order'):
                with self.subTest(defect=defect):
                    for name, data in original.items():
                        (capture / name).write_bytes(data)
                    summary = capture / 'summary.md'
                    if defect == 'missing-pair':
                        with summary.open('a', encoding='utf-8') as stream:
                            stream.write('| tcp_3_up_8105.jsonl | up | 127.0.0.1:23456 → 47.117.173.152:8105 | 1 | 0 |\n')
                            stream.write('| tcp_4_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:23456 | 1 | 0 |\n')
                    elif defect == 'residual':
                        summary.write_text(summary.read_text('utf-8').replace('| 0 |', '| 4 |', 1), 'utf-8')
                    elif defect == 'count':
                        summary.write_text(summary.read_text('utf-8').replace('| 3 | 0 |', '| 999 | 0 |'), 'utf-8')
                    else:
                        path = capture / 'tcp_2_down_8105.jsonl'
                        rows = [json.loads(line) for line in path.read_text('utf-8').splitlines()]
                        confirmation = next(item for item in rows if item['cmd'] == 10043)
                        if defect == 'order':
                            confirmation['ts'] = self.snapshot.end_frame.timestamp - 1.5
                        else:
                            payload = codec.encode('sc_10043', {'result': 1} if defect == 'failed' else {})
                            confirmation.update(payload_hex=payload.hex(), payload_len=len(payload))
                        path.write_text(''.join(json.dumps(item) + '\n' for item in rows), 'utf-8')
                    before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}
                    for apply in (False, True):
                        output = io.StringIO()
                        with patch.object(save_generator, 'SLOTS', root / 'slots'), redirect_stdout(output):
                            code = _CLI.main([str(capture), '--name', 'Rejected', *(['--apply'] if apply else [])])
                        self.assertNotEqual(code, 0, output.getvalue())
                        self.assertFalse(json.loads(output.getvalue())['ready'])
                    self.assertEqual(before, {str(path.relative_to(root)): path.read_bytes()
                        for path in root.rglob('*') if path.is_file()})

    def test_mail_normalization_rejects_empty_conflicts_and_publishes_identical_duplicates(self):
        snapshot = deepcopy(self.snapshot)
        mails = snapshot.supplement_frames[0].decoded['mail_list']
        mails.append(deepcopy(mails[0]))
        self.assertEqual(mails[-1]['star_state'], 0)
        mails[-1].pop('star_state')
        db, report = capture_import.build_imported_save(snapshot, 880000000021)
        self.addCleanup(db.close)
        self.assertEqual(report.row_counts['mail'], len({row['id'] for row in mails}))
        with tempfile.TemporaryDirectory(prefix='m3-mail-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            published = capture_import.publish_imported_save(db, report, 'Deduplicated')
            self.assertTrue(published.validation['isolated_login'])
        for defect in ('empty-summary', 'conflict'):
            with self.subTest(defect=defect):
                broken = deepcopy(snapshot)
                if defect == 'empty-summary':
                    broken.protocol_data[30001] = [dict(total_number=0, unread_number=0)]
                else:
                    broken.supplement_frames[0].decoded['mail_list'][-1]['title'] += ' conflict'
                self.assertTrue(capture_import._report(broken).issues)
                with self.assertRaises(ValueError):
                    capture_import.build_imported_save(broken, 880000000022)

    def test_ordered_mail_summary_updates_and_identical_query_replies_publish_once(self):
        snapshot = deepcopy(self.snapshot)
        original = next(frame for frame in snapshot.login_frames if frame.cmd == 30001)
        index = snapshot.login_frames.index(original)
        snapshot.login_frames[index] = replace(original,
            decoded=dict(total_number=0, unread_number=0), payload=codec.encode('sc_30001',
                dict(total_number=0, unread_number=0)))
        snapshot.login_frames.append(original)
        snapshot.supplement_frames.append(deepcopy(snapshot.supplement_frames[0]))
        with tempfile.TemporaryDirectory(prefix='m3-mail-sequence-') as temporary:
            root = Path(temporary)
            capture = root / 'capture'
            capture.mkdir()
            self._write_capture(capture, snapshot)
            restored = read_snapshot(capture)
            self.assertFalse(restored.issues)
            self.assertFalse(restored.missing_data)
            self.assertEqual(restored.protocol_data[30001], [original.decoded])
            self.assertEqual(len([frame for frame in restored.login_frames if frame.cmd == 30001]), 2)
            self.assertEqual(len(restored.supplement_frames), 2)
            db, report = capture_import.build_imported_save(restored, 880000000029)
            self.addCleanup(db.close)
            self.assertEqual(len(report.validation['mail_summary_frames']), 2)
            self.assertEqual(db.query('SELECT COUNT(*) n FROM login_push WHERE cmd=30001')[0]['n'], 1)
            with patch.object(save_generator, 'SLOTS', root / 'slots'):
                published = capture_import.publish_imported_save(db, report, 'Mail-Sequence')
            self.assertTrue(published.validation['isolated_login'])
            path = capture / 'tcp_2_down_8105.jsonl'
            rows = [json.loads(line) for line in path.read_text('utf-8').splitlines()]
            response = next(row for row in reversed(rows) if row['cmd'] == 30003)
            value = codec.decode(bytes.fromhex(response['payload_hex']), 'sc_30003')
            value['mail_list'][0]['title'] += ' conflict'
            payload = codec.encode('sc_30003', value)
            response.update(payload_hex=payload.hex(), payload_len=len(payload))
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows), 'utf-8')
            rejected = read_snapshot(capture)
            self.assertTrue(any('应答内容冲突' in issue for issue in rejected.issues))
            with self.assertRaises(ValueError):
                capture_import.build_imported_save(rejected, 880000000030)

    def test_hero_scope_restores_assets_relations_and_archive_without_other_progress(self):
        snapshot = deepcopy(self.snapshot)
        snapshot.client_build, snapshot.resource_version = '308', '332'
        snapshot.end_frame = replace(snapshot.end_frame, timestamp=time.time() - 7 * 86400)
        packet = snapshot.protocol_data[14009][0]
        hero = packet['hero_info_list'][0]
        hero['hero_base_info']['weapon']['servant_uid'] = 701
        hero['hero_base_info'].pop('servant', None)
        hero['trust']['relation'] = dict(tier_list=[dict(tier=1, upgrade_complete_list=[1])])
        archive = dict(archive_id=hero['hero_base_info']['id'], exp=1000,
            selected_picture=dict(type=1, id=hero['hero_base_info']['id']),
            super_heart_link_list=[dict(index=1, is_viewed=True)])
        packet['archives'] = [codec.decode(codec.encode('sc_14009', dict(archives=[archive])), 'sc_14009')['archives'][0]]
        snapshot.protocol_data[30001] = [dict(total_number=99, unread_number=0)]
        self.assertTrue(capture_import._report(snapshot).missing_data)
        self.assertFalse(capture_import._report(snapshot, scope='heroes').missing_data)
        uid = 880000000031
        db, report = capture_import.build_imported_hero_save(snapshot, uid)
        self.addCleanup(db.close)
        self.assertEqual(db.get_system_config('save.profile'), 'new_player_v1')
        self.assertEqual(db.get('users', uid)['hero_num'], len(packet['hero_info_list']))
        self.assertEqual(db.get('currency', uid, 'AND id=2')['num'], 0)
        self.assertFalse(db.get('material', uid, 'AND id=41201'))
        self.assertFalse(db.query('SELECT 1 FROM mail WHERE uid=?', (uid,)))
        self.assertFalse(db.query('SELECT 1 FROM store_purchase WHERE uid=?', (uid,)))
        self.assertEqual(json.loads(db.query('SELECT relation_net FROM hero WHERE uid=? AND id=?',
            (uid, hero['hero_base_info']['id']))[0]['relation_net']), hero['trust']['relation']['tier_list'])
        self.assertEqual(json.loads(db.query('SELECT super_heart_link_list FROM hero_archive WHERE uid=?',
            (uid,))[0]['super_heart_link_list']), archive['super_heart_link_list'])
        with tempfile.TemporaryDirectory(prefix='m3-hero-publish-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            before_login = int(time.time())
            published = capture_import.publish_imported_save(db, report, 'Hero-Scope')
            self.assertEqual(published.validation['import_scope'], 'heroes')
            self.assertEqual(published.validation['compared_protocols'], len(capture_import.HERO_COMMANDS))
            self.assertTrue(published.validation['isolated_login'])
            self.assertGreaterEqual(published.validation['validation_clock'], before_login)
            self.assertLessEqual(published.validation['validation_clock'], int(time.time()))
            self.assertNotEqual(published.validation['validation_clock'], int(snapshot.end_frame.timestamp))
            self.assertTrue(published.slot_registration['registered'])

    def test_mail_supplements_restore_senders_and_collected_summaries(self):
        snapshot = deepcopy(self.snapshot)
        sample = snapshot.supplement_frames[0]
        mail_id = sample.decoded['mail_list'][0]['id']
        body = [dict(content_type=2, text='捕获的邮件正文')]
        collection = dict(id=880000000099, collect_date=1700000100,
                          title='收藏摘要', mail_timestamp=1700000000, mail_template_id=0)
        snapshot.supplement_frames.extend([
            replace(sample, cmd=30021, decoded=dict(collect_mail_list=[collection], collect_total_num=1)),
            replace(sample, cmd=30009, decoded=dict(result=0, detail_info=dict(
                id=mail_id, content_list=body, sender='来源运营团队'))),
        ])
        with tempfile.TemporaryDirectory(prefix='m3-mail-supplements-') as temporary:
            root = Path(temporary)
            capture = root / 'capture'
            capture.mkdir()
            self._write_capture(capture, snapshot)
            restored = read_snapshot(capture)
            self.assertFalse(restored.issues)
            db, report = capture_import.build_imported_save(restored, 880000000037, scope='available')
            self.addCleanup(db.close)
            saved = db.get('mail', report.target_uid, 'AND mail_id=?', (mail_id,))
            self.assertEqual(json.loads(saved['content_json']), body)
            self.assertEqual(saved['sender'], '来源运营团队')
            mailer = MailService(db)
            self.assertEqual(mailer.get_login_summary(report.target_uid)['total_number'], len(restored._mail_records))
            collected = mailer.get_collect_list(report.target_uid)
            self.assertEqual([(row['id'], row['title'], row['collect_date'], row['mail_timestamp']) for row in collected],
                             [(collection['id'], collection['title'], collection['collect_date'], collection['mail_timestamp'])])
            self.assertEqual(report.validation['unrestored_mail_ids'], [])
            self.assertEqual(report.validation['unrestored_collect_mail_ids'], [collection['id']])
            with patch.object(save_generator, 'SLOTS', root / 'slots'):
                published = capture_import.publish_imported_save(db, report, 'Mailbox-Supplements')
            self.assertTrue(published.validation['isolated_login'])

    def test_collected_detail_pairing_and_conflicts_reject_import(self):
        snapshot = deepcopy(self.snapshot)
        sample = snapshot.supplement_frames[0]
        collection = dict(id=880000000098, collect_date=1700000100,
                          title='已抓收藏', mail_timestamp=1700000000, mail_template_id=0)
        detail = dict(id=collection['id'], content_list=[dict(content_type=2, text='收藏正文')], sender='来源')
        snapshot.supplement_frames.extend([
            replace(sample, cmd=30021, decoded=dict(collect_mail_list=[collection], collect_total_num=1)),
            replace(sample, cmd=30023, decoded=dict(result=0, detail_info=detail)),
        ])
        with tempfile.TemporaryDirectory(prefix='m3-collect-details-') as temporary:
            capture = Path(temporary)
            self._write_capture(capture, snapshot)
            valid = read_snapshot(capture)
            self.assertFalse(valid.issues)
            self.assertEqual(valid._collected_mail_records[0]['content_list'], detail['content_list'])
            original = {path.name: path.read_bytes() for path in capture.iterdir()}
            for defect in ('wrong-id', 'failed-response', 'conflicting-summary'):
                with self.subTest(defect=defect):
                    for name, raw in original.items():
                        (capture / name).write_bytes(raw)
                    path = capture / ('tcp_1_up_8105.jsonl' if defect == 'wrong-id' else 'tcp_2_down_8105.jsonl')
                    rows = [json.loads(line) for line in path.read_text('utf-8').splitlines()]
                    command = 30022 if defect == 'wrong-id' else 30023 if defect == 'failed-response' else 30021
                    packet = next(row for row in rows if row['cmd'] == command)
                    schema = ('cs_' if defect == 'wrong-id' else 'sc_') + str(command)
                    value = codec.decode(bytes.fromhex(packet['payload_hex']), schema)
                    if defect == 'wrong-id':
                        value['mail_id'] += 1
                    elif defect == 'failed-response':
                        value['result'] = 1
                    else:
                        value['collect_mail_list'].append(dict(value['collect_mail_list'][0], title='冲突标题'))
                        value['collect_total_num'] = 2
                    payload = codec.encode(schema, value)
                    packet.update(payload_hex=payload.hex(), payload_len=len(payload))
                    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), 'utf-8')
                    rejected = read_snapshot(capture)
                    self.assertTrue(rejected.issues)
                    with self.assertRaises(ValueError):
                        capture_import.build_imported_save(rejected, 880000000038, scope='available')

    def test_collect_date_survives_reading_and_changes_only_on_collect(self):
        uid = 880000000039
        db, _ = self._build_candidate(uid)
        self.addCleanup(db.close)
        mail_id = db.query('SELECT mail_id FROM mail WHERE uid=? LIMIT 1', (uid,))[0]['mail_id']
        mailer = MailService(db)
        with patch('time.time', return_value=1700000100):
            mailer.toggle_collect(uid, mail_id, 1)
        with patch('time.time', return_value=1700000200):
            mailer.get_mail_detail(uid, mail_id)
        self.assertEqual(mailer.get_collect_list(uid)[0]['collect_date'], 1700000100)
        mailer.toggle_collect(uid, mail_id, 2)
        self.assertEqual(mailer.get_collect_list(uid), [])
        with patch('time.time', return_value=1700000300):
            mailer.toggle_collect(uid, mail_id, 1)
        self.assertEqual(mailer.get_collect_list(uid)[0]['collect_date'], 1700000300)

    def test_mail_detail_supplement_preserves_current_assets_and_source_proof(self):
        source = deepcopy(self.snapshot)
        source.source_sha256 = {'source.jsonl': 'a' * 64}
        current = deepcopy(self.snapshot)
        for frame in current.supplement_frames:
            for mail in frame.decoded.get('mail_list', []):
                mail.pop('content_list', None)
        currency = next(row for row in current.protocol_data[15009][0]['currency_list'] if row['id'] == 2)
        currency['num'] = 12345
        first = source.supplement_frames[0].decoded['mail_list'][0]
        first['sender'] = '已验证来源'
        capture_import.supplement_mail_details(current, source)
        db, report = capture_import.build_imported_save(current, 880000000040, scope='available')
        self.addCleanup(db.close)
        self.assertEqual(db.get('currency', report.target_uid, 'AND id=2')['num'], 12345)
        self.assertEqual(report.validation['unrestored_mail_ids'], [])
        proof = db.get('ops_common', report.target_uid,
                       "AND kind='capture_mail_details' AND item_id=?", (str(first['id']),))
        self.assertEqual(json.loads(proof['value_json'])['source_sha256'], source.source_sha256)
        saved = db.get('mail', report.target_uid, 'AND mail_id=?', (first['id'],))
        self.assertEqual(saved['sender'], first['sender'])
        self.assertEqual(json.loads(saved['content_json']), first['content_list'])
        with tempfile.TemporaryDirectory(prefix='m3-mail-proof-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            published = capture_import.publish_imported_save(db, report, 'With-Mail-Proof')
            self.assertTrue(published.validation['isolated_login'])
            with closing(sqlite3.connect(published.output_path)) as stored:
                self.assertEqual(stored.execute('SELECT num FROM currency WHERE uid=? AND id=2',
                                 (published.target_uid,)).fetchone()[0], 12345)
                self.assertEqual(stored.execute("SELECT COUNT(*) FROM ops_common WHERE kind='capture_mail_details'").fetchone()[0],
                                 len(current._mail_detail_supplements))

    def test_mail_detail_supplement_rejects_other_owner_identity_and_content_conflicts(self):
        for defect in ('owner', 'version', 'title', 'date', 'attachments', 'content', 'sender', 'indirect-source'):
            with self.subTest(defect=defect):
                current = deepcopy(self.snapshot)
                source = deepcopy(self.snapshot)
                record = source.supplement_frames[0].decoded['mail_list'][0]
                if defect == 'owner':
                    source.source_uid += 1
                elif defect == 'version':
                    source.resource_version = '332'
                elif defect == 'title':
                    record['title'] += '不同'
                elif defect == 'date':
                    record['date'] += 1
                elif defect == 'attachments':
                    record['attachment_list'].append(dict(id=2, number=1))
                elif defect == 'content':
                    record['content_list'] = [dict(content_type=2, text='冲突正文')]
                elif defect == 'sender':
                    record['sender'] = '来源 A'
                    current.supplement_frames[0].decoded['mail_list'][0]['sender'] = '来源 B'
                else:
                    source._mail_detail_supplements[record['id']] = {}
                with self.assertRaises(ValueError):
                    capture_import.supplement_mail_details(current, source)
                self.assertEqual(current._mail_detail_supplements, {})

    def test_reviewed_archive_redpoints_compensation_and_daily_records_round_trip(self):
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        uid = 880000000041
        db.upsert('users', uid, dict(nick='新增映射', extra='{}'))
        captured_at = 1794920258
        packets = {
            24043: [dict(plot_list=[1002, 1001, 42010101])],
            56001: [dict(nothing=0, red_dot=[14], client_finished_red_dot=[302, 301])],
            12023: [dict(reward=[dict(id=1, stage=1001)])],
            73005: [dict(limit_list=[dict(item_id=30012, use=3)])],
            83026: [dict(reward_record=13, ticket_record=2)],
        }
        with patch('time.time', return_value=captured_at):
            capture_account_state._restore_collections(db, packets, uid, captured_at)
            capture_account_state._restore_exploration(db, packets, uid, captured_at)
            capture_account_state._restore_communications(db, packets, uid, captured_at)
            capture_account_state._restore_games(db, packets, uid, captured_at)
            for command in (24043, 56001, 12023, 83026):
                received = codec.decode(generator.gen_payload(command, uid=uid, db=db), 'sc_' + str(command))
                self.assertEqual(capture_account_state.account_protocol_state(command, [received]),
                                 capture_account_state.account_protocol_state(command, packets[command]))
            from trust_service import TrustService
            service = TrustService.get_instance()
            day = service._displace_day_key(captured_at)
            self.assertEqual(service._get_displace_used(db, uid, day), {30012: 3})
            self.assertEqual(service._get_displace_used(db, uid, service._displace_day_key(captured_at + 86400)), {})

    def test_captured_equip_state_queries_rotates_and_settles_across_groups(self):
        uid = 880000000042
        captured_at = 1794920258
        refresh_at = captured_at + 86400
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='保底测试'))
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        connection = Connection(uid=uid, db=db, generator=generator,
                                codec_encode=codec.encode, codec_decode=codec.decode)

        def send(command, data):
            request = CoreRequest(command, codec.encode('cs_' + str(command), data), uid=uid)
            return server.dispatch(request, connection)

        def query_state():
            response = send(43002, {})
            frame = next(frame for frame in response.frames if frame['sc'] == 43001)
            return codec.decode(frame['payload'], 'sc_43001')

        send(43004, dict(equip_suit_id=47))
        empty_state = query_state()
        self.assertEqual(empty_state['equip_suit_id'], 47)
        self.assertEqual(empty_state['stage_base_id'], 30001)
        self.assertEqual([row['insure_times'] for row in empty_state['insure_list']], [0] * 5)
        db.execute('DELETE FROM battle_equip WHERE uid=?', (uid,))

        insure_counts = [6, 8, 4, 3, 1]
        packets = {43001: [dict(
            stage_base_id=30007,
            equip_suit_id=46,
            next_refresh_time=refresh_at,
            insure_list=[dict(difficulty=difficulty, insure_times=count)
                         for difficulty, count in enumerate(insure_counts, 1)],
        )]}
        capture_account_state._restore_progress(db, packets, uid, captured_at)

        with patch('stage_service.time.time', return_value=captured_at + 1):
            initial = query_state()
            self.assertEqual(initial['stage_base_id'], 30007)
            self.assertEqual(initial['equip_suit_id'], 46)
            self.assertEqual([row['insure_times'] for row in initial['insure_list']], insure_counts)

            send(43004, dict(equip_suit_id=47))
            changed = query_state()
            self.assertEqual(changed['equip_suit_id'], 47)
            self.assertEqual(changed['stage_base_id'], 30007)
            self.assertEqual([row['insure_times'] for row in changed['insure_list']], insure_counts)

        with patch('stage_service.time.time', return_value=refresh_at + 1):
            expired = query_state()
        self.assertEqual(expired['stage_base_id'], 30001)
        self.assertEqual([row['insure_times'] for row in expired['insure_list']], insure_counts)

        import middleware
        ctx = connection.to_handler_ctx()
        other_group_same_difficulty = 2020064
        with patch('stage_service.time.time', return_value=captured_at + 1), \
                patch.object(middleware, 'stage_drop', return_value=[[35102, 1]]):
            middleware._settle_frames(ctx, uid, 9920001, 1, other_group_same_difficulty,
                                      times=1, heroes=[], sweep=True)
        with patch('stage_service.time.time', return_value=captured_at + 1):
            after_no_five_star = query_state()
        self.assertEqual(after_no_five_star['stage_base_id'], 30007)
        self.assertEqual(after_no_five_star['insure_list'][3]['insure_times'], 4,
                         db.query('SELECT stage_id, insure_times, suit_id, next_refresh_time '
                                  'FROM battle_equip WHERE uid=? ORDER BY stage_id', (uid,)))

        with patch('stage_service.time.time', return_value=captured_at + 1), \
                patch.object(middleware, 'stage_drop', side_effect=(
                    [[35102, 1]], [[35105, 1]])):
            middleware._settle_frames(ctx, uid, 9920002, 1, other_group_same_difficulty,
                                      times=2, heroes=[], sweep=True)
        with patch('stage_service.time.time', return_value=captured_at + 1):
            after_multi_five_star = query_state()
        self.assertEqual(after_multi_five_star['insure_list'][3]['insure_times'], 0)
        prefabs = [row['prefab_id'] for row in db.query('SELECT prefab_id FROM equip WHERE uid=?', (uid,))]
        self.assertTrue(any(prefab // 100000 == 5 for prefab in prefabs), prefabs)

    def test_equip_settlement_counter_write_failure_rolls_back_reward_and_retries_once(self):
        import middleware

        uid = 880000000043
        captured_at = 1794920258
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='结算回滚'))
        db.set_currency(uid, 2, 1000, ts=captured_at)
        packets = {43001: [dict(
            stage_base_id=30007,
            equip_suit_id=46,
            next_refresh_time=captured_at + 86400,
            insure_list=[dict(difficulty=difficulty, insure_times=count)
                         for difficulty, count in enumerate([6, 8, 4, 3, 1], 1)],
        )]}
        capture_account_state._restore_progress(db, packets, uid, captured_at)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        connection = Connection(uid=uid, db=db, generator=generator,
                                codec_encode=codec.encode, codec_decode=codec.decode)
        battle_id = 9920003
        stage_id = 2020064
        with patch.dict(middleware._BATTLE_SESSIONS, {}, clear=True):
            middleware.register_battle_session(battle_id, uid, dest=stage_id)
            session = middleware.get_battle_session(battle_id)
            session['result_data'] = dict(result=1, info=dict(battle_time=10000))
            db.execute(
                "CREATE TRIGGER fail_equip_counter BEFORE UPDATE OF insure_times ON battle_equip "
                f"WHEN NEW.uid={uid} AND NEW.insure_times=4 BEGIN "
                "SELECT RAISE(ABORT,'injected battle_equip write failure'); END")
            before_balance = db.get_item_num(uid, 2)
            before_equipment = db.query('SELECT * FROM equip WHERE uid=? ORDER BY id', (uid,))
            before_counter = db.get('battle_equip', uid, 'AND stage_id=?', (2020074,))['insure_times']
            request = CoreRequest(54032, codec.encode('cs_54032', dict(battle_id=battle_id)), uid=uid)
            with patch('stage_service.time.time', return_value=captured_at + 1), \
                    patch.object(middleware, 'stage_drop', return_value=[[2, 100]]) as drop:
                failed = server.dispatch(request, connection)
                self.assertEqual([frame['sc'] for frame in failed.frames], [54033])
                failure_packet = codec.decode(failed.frames[0]['payload'], 'sc_54033')
                self.assertNotEqual(failure_packet['result'], 0)
                self.assertEqual(db.get_item_num(uid, 2), before_balance)
                self.assertEqual(db.query('SELECT * FROM equip WHERE uid=? ORDER BY id', (uid,)), before_equipment)
                self.assertEqual(db.get('battle_equip', uid, 'AND stage_id=?', (2020074,))['insure_times'], before_counter)
                self.assertNotIn('br', session)

                db.execute('DROP TRIGGER fail_equip_counter')
                succeeded = server.dispatch(request, connection)
                self.assertIn(54033, [frame['sc'] for frame in succeeded.frames])
                receipt = next(frame for frame in succeeded.frames if frame['sc'] == 54033)
                result = codec.decode(receipt['payload'], 'sc_54033')
                self.assertEqual(result['result'], 0)
                self.assertEqual(db.get_item_num(uid, 2), before_balance + 100)
                self.assertEqual(db.get('battle_equip', uid, 'AND stage_id=?', (2020074,))['insure_times'], 4)
                self.assertEqual(drop.call_count, 2)

                settled_balance = db.get_item_num(uid, 2)
                settled_equipment = db.query('SELECT * FROM equip WHERE uid=? ORDER BY id', (uid,))
                repeat = server.dispatch(request, connection)
                self.assertEqual([frame['sc'] for frame in repeat.frames], [54033])
                self.assertEqual(codec.decode(repeat.frames[0]['payload'], 'sc_54033'), result)
                self.assertEqual(db.get_item_num(uid, 2), settled_balance)
                self.assertEqual(db.query('SELECT * FROM equip WHERE uid=? ORDER BY id', (uid,)), settled_equipment)
                self.assertEqual(drop.call_count, 2)

    def test_hero_scope_rejects_duplicate_heroes_and_missing_equipment_references(self):
        for defect in ('duplicate', 'equipment', 'servant'):
            with self.subTest(defect=defect):
                snapshot = deepcopy(self.snapshot)
                hero = snapshot.protocol_data[14009][0]['hero_info_list'][0]
                if defect == 'duplicate':
                    snapshot.protocol_data[14009][0]['hero_info_list'].append(deepcopy(hero))
                elif defect == 'equipment':
                    hero['equip'] = [dict(pos=1, equip_id=99999999)]
                else:
                    hero['hero_base_info']['weapon']['servant_uid'] = 99999999
                with self.assertRaises(ValueError):
                    capture_import.build_imported_hero_save(snapshot, 880000000032)

    def test_hero_scope_cli_publishes_while_full_scope_remains_blocked(self):
        snapshot = deepcopy(self.snapshot)
        snapshot.client_build, snapshot.resource_version = '308', '332'
        with tempfile.TemporaryDirectory(prefix='m3-hero-cli-') as temporary:
            root = Path(temporary)
            capture = root / 'capture'
            capture.mkdir()
            self._write_capture(capture, snapshot)
            preview = self._cli_process(root, capture, '--name', 'Hero-CLI', '--scope', 'heroes')
            self.assertEqual(preview.returncode, 0, preview.stderr + preview.stdout)
            self.assertTrue(json.loads(preview.stdout)['ready'])
            self.assertFalse((root / 'slots').exists())
            blocked = self._cli_process(root, capture, '--name', 'Full-CLI', '--apply')
            self.assertEqual(blocked.returncode, 2, blocked.stderr + blocked.stdout)
            self.assertFalse((root / 'slots').exists())
            applied = self._cli_process(root, capture, '--name', 'Hero-CLI', '--scope', 'heroes', '--apply')
            self.assertEqual(applied.returncode, 0, applied.stderr + applied.stdout)
            with closing(sqlite3.connect(root / 'slots' / 'Hero-CLI.db')) as check:
                self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(check.execute('SELECT COUNT(*) FROM hero').fetchone()[0],
                                 len(snapshot.protocol_data[14009][0]['hero_info_list']))

    def test_dynamic_relogin_reads_changed_level_points_and_current_clock(self):
        uid = 880000000023
        snapshot = deepcopy(self.snapshot)
        activity = next(row for row in snapshot.protocol_data[60201] if row['activity_id'] != 323801)
        previous_id = activity['activity_id']
        activity_id = 323841
        activity['activity_id'] = activity_id
        for index, frame in enumerate(snapshot.login_frames):
            if frame.cmd == 60201 and frame.decoded['activity_id'] == previous_id:
                snapshot.login_frames[index] = replace(frame, decoded=deepcopy(activity),
                    payload=codec.encode('sc_60201', activity))
        db, _ = capture_import.build_imported_save(snapshot, uid)
        self.addCleanup(db.close)
        self.assertEqual(db.get('users', uid)['level'], 93)
        self.assertEqual(db.get('activity_point', uid, 'AND activity_id=?', (activity_id,))['point'], activity['point'])
        db.execute('UPDATE users SET level=94 WHERE uid=?', (uid,))
        db.execute('UPDATE activity_point SET point=99 WHERE uid=? AND activity_id=?', (uid, activity_id))
        db.execute('INSERT OR IGNORE INTO activity_point_reward(uid,activity_id,reward_id) VALUES(?,?,?)', (uid, activity_id, 9001))
        for version in ('321', '332'):
            import res_version_manager
            with res_version_manager.connection_version(version):
                self.assertTrue(any(row['activity_id'] == activity_id and row['state'] == 1
                    and row['start_time'] <= time.time() < row['stop_time']
                    for row in generator.get_activity_list(db, uid)))
            before = int(time.time())
            packets = self._login_packets(db, uid, version)
            after = int(time.time())
            self.assertEqual(packets[12009], [dict(user_level=94)])
            changed = next(row for row in packets[60201] if row['activity_id'] == activity_id)
            self.assertEqual(changed['point'], 99)
            self.assertIn(9001, changed['reward_list'])
            self.assertEqual(len(packets[10201]), 1)
            self.assertLessEqual(before, packets[10201][0]['timestamp'])
            self.assertLessEqual(packets[10201][0]['timestamp'], after)
            self.assertEqual(db.get_system_config('save.profile'), 'capture_import_v1')
        original_payload = generator.gen_payload
        with patch.object(generator, 'gen_payload', side_effect=lambda cmd, **kwargs:
                None if cmd == 10201 else original_payload(cmd, **kwargs)):
            with self.assertRaisesRegex(RuntimeError, '10201'):
                self._login_packets(db, uid)

    def test_imported_claims_block_single_batch_and_relogin_then_reset_only_recurring(self):
        uid = 880000000024
        snapshot = deepcopy(self.snapshot)
        from lazy_timer import get_daily_5am_ts
        expiry = get_daily_5am_ts(snapshot.end_frame.timestamp) + 86400
        task_ids = (6001, 6002, 30601, 30602)
        assignments = snapshot.protocol_data[28001][0]['assignment_list']
        assignments[:] = [row for row in assignments if row['id'] not in task_ids]
        assignments.extend(dict(id=tid, progress=1, complete_flag=int(tid in (6001, 30601)),
            expired_timestamp=expiry if tid < 10000 else 0) for tid in task_ids)
        db, _ = capture_import.build_imported_save(snapshot, uid)
        self.addCleanup(db.close)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)

        def submit(command, data):
            response = server.dispatch(CoreRequest(command, codec.encode('cs_' + str(command), data), uid=uid))
            acknowledgement = next(frame for frame in response.frames if frame['sc'] == command + 1)
            value = codec.decode(acknowledgement['payload'], 'sc_' + str(command + 1))
            self.assertEqual(value.get('result', 0), 0, value)
            return value

        def assets():
            return {table: db.query('SELECT * FROM ' + table + ' WHERE uid=? ORDER BY rowid', (uid,))
                    for table in ('currency', 'material', 'hero_piece', 'equip', 'servant')}

        for tid in (6001, 30601):
            self.assertTrue(db.is_task_claimed(uid, tid))
        self.assertFalse(db.is_claimed(uid, 'task', 6001))
        self.assertTrue(db.is_claimed(uid, 'task', 30601))
        before = assets()
        submit(28010, dict(id=6001))
        submit(28010, dict(id=30601))
        submit(28014, dict(id_list=[6001, 30601]))
        self.assertEqual(assets(), before)
        self._login_packets(db, uid)
        before = assets()
        submit(28014, dict(id_list=[6001, 30601]))
        self.assertEqual(assets(), before)
        cash = db.get('currency', uid, 'AND id=2')['num']
        submit(28010, dict(id=30602))
        self.assertEqual(db.get('currency', uid, 'AND id=2')['num'] - cash, 1600)
        self.assertTrue(submit(28014, dict(id_list=[6002]))['reward_list'])
        before = assets()
        submit(28014, dict(id_list=list(task_ids)))
        self.assertEqual(assets(), before)
        with patch('time.time', return_value=expiry + 1):
            packets = self._login_packets(db, uid)
            self.assertFalse(db.is_task_claimed(uid, 6001))
            self.assertTrue(db.is_task_claimed(uid, 30601))
            self.assertTrue(submit(28010, dict(id=6001))['reward_list'])
            before = assets()
            submit(28010, dict(id=30601))
            self.assertEqual(assets(), before)

    def test_cli_preview_apply_and_duplicate_use_real_process_and_preserve_active_save(self):
        with tempfile.TemporaryDirectory(prefix='m3-cli-') as temporary:
            root = Path(temporary)
            capture = root / 'capture'
            capture.mkdir()
            self._write_capture(capture)
            slots = root / 'slots'
            slots.mkdir()
            existing = slots / 'Existing.db'
            with closing(sqlite3.connect(existing)) as conn:
                conn.execute('CREATE TABLE users(uid INTEGER)')
                conn.execute('INSERT INTO users VALUES(77)')
                conn.commit()
            manager = SaveSlotManager(str(slots))
            manager.set_active_db(str(existing))
            manager.sync_slot_registry()
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            preview = self._cli_process(root, capture, '--name', '旅途#1', '--uid', '880000000025')
            self.assertEqual(preview.returncode, 0, preview.stderr + preview.stdout)
            self.assertTrue(json.loads(preview.stdout)['ready'], preview.stdout)
            self.assertEqual(before, {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()})
            applied = self._cli_process(root, capture, '--name', '旅途#1', '--uid', '880000000025', '--apply')
            self.assertEqual(applied.returncode, 0, applied.stderr + applied.stdout)
            decoder = json.JSONDecoder()
            _, offset = decoder.raw_decode(applied.stdout)
            published = json.loads(applied.stdout[offset:].strip())['report']
            self.assertTrue(published['slot_registration']['registered'])
            output = slots / '旅途#1.db'
            with closing(sqlite3.connect(output)) as check:
                self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(check.execute('SELECT uid FROM users').fetchall(), [(880000000025,)])
            import save_slot_manager
            self.assertEqual(save_slot_manager.extract_save_metadata(str(output))[0], 880000000025)
            self.assertFalse((slots / '旅途').exists())
            self.assertEqual(manager._load_registry()[3], 'Existing.db')
            self.assertEqual(manager.get_active_db(), str(existing))
            self.assertEqual(existing.read_bytes(), before[str(Path('slots') / 'Existing.db')])
            published_bytes = output.read_bytes()
            duplicate = self._cli_process(root, capture, '--name', '旅途#1', '--uid', '880000000025', '--apply')
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(output.read_bytes(), published_bytes)
            for path in capture.iterdir():
                self.assertEqual(path.read_bytes(), before[str(Path('capture') / path.name)])

    def test_locked_registered_save_keeps_slot_while_another_is_discovered(self):
        with tempfile.TemporaryDirectory(prefix='m3-locked-') as temporary:
            root = Path(temporary)
            path = root / 'A.db'
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE users(uid INTEGER)')
                conn.execute('INSERT INTO users VALUES(1)')
                conn.commit()
            manager = SaveSlotManager(str(root))
            self.assertEqual(manager.sync_slot_registry(), {3: 'A.db'})
            with closing(sqlite3.connect(path)) as locked:
                locked.execute('BEGIN EXCLUSIVE')
                with closing(sqlite3.connect(root / 'B.db')) as added:
                    added.execute('CREATE TABLE users(uid INTEGER)')
                    added.execute('INSERT INTO users VALUES(2)')
                    added.commit()
                self.assertEqual(
                    [(row['filename'], row['uid']) for row in gm_save_scope.catalog(manager)],
                    [('B.db', 2)],
                )
                self.assertEqual(manager.sync_slot_registry(), {3: 'A.db', 4: 'B.db'})
                locked.rollback()
            self.assertEqual(manager.sync_slot_registry(), {3: 'A.db', 4: 'B.db'})
            path.write_bytes(b'confirmed invalid SQLite database')
            self.assertEqual(manager.sync_slot_registry(), {4: 'B.db'})
            (root / 'B.db').unlink()
            self.assertEqual(manager.sync_slot_registry(), {})

    def test_excluded_names_reject_before_import_or_ordinary_creation(self):
        with tempfile.TemporaryDirectory(prefix='m3-names-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            db, report = self._build_candidate(880000000026)
            self.addCleanup(db.close)
            for name in ('_hidden', '.hidden', 'test_account', 'travel_bak_old', 'travel_backup_old'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        capture_import.publish_imported_save(db, report, name)
                    with self.assertRaises(ValueError):
                        save_generator.create_save(name)
                    self.assertFalse(list(Path(temporary).iterdir()))

    def test_existing_empty_staging_root_is_preserved_after_success(self):
        with tempfile.TemporaryDirectory(prefix='m3-stage-root-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            root = Path(temporary) / '.import-staging'
            root.mkdir()
            db, report = self._build_candidate(880000000027)
            self.addCleanup(db.close)
            capture_import.publish_imported_save(db, report, 'Keep-Root')
            self.assertTrue(root.is_dir())
            self.assertFalse(list(root.iterdir()))

    def test_real_capture_mail_details_match_observed_responses(self):
        self.assertTrue(self.capture_dir.is_dir(), f"抓包目录不存在：{self.capture_dir}")
        snapshot = read_snapshot(self.capture_dir)
        summary = snapshot.protocol_data.get(30001, [{}])[0]
        total = summary.get("total_number")
        self.assertIsInstance(total, int)
        self.assertGreater(total, 0)
        supplements = [frame for frame in snapshot.supplement_frames
                       if frame.cmd == 30003]
        self.assertTrue(supplements)
        self.assertEqual(len(snapshot._mail_records), total)
        custom_ids = {mail['id'] for frame in supplements for mail in frame.decoded['mail_list']
                      if not mail.get('mail_template_id') and not mail.get('content_list')}
        details = {frame.decoded['detail_info']['id']: frame.decoded['detail_info']
                   for frame in snapshot.supplement_frames
                   if frame.cmd == 30009 and frame.decoded['detail_info'].get('content_list')}
        actual_missing = {mail['id'] for mail in snapshot._mail_records if not mail['content_list']}
        self.assertEqual(actual_missing, custom_ids - set(details))
        self.assertEqual(bool(actual_missing), any('模板正文解析' in item['data'] for item in snapshot.missing_data))
        for mail in snapshot._mail_records:
            if mail['id'] in details:
                self.assertEqual(mail['content_list'], details[mail['id']]['content_list'])
                self.assertEqual(mail['sender'], details[mail['id']]['sender'])

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
                    frame(10200, "up", {}, 3, 2),
                ],
                "tcp_2_down_8105.jsonl": [
                    frame(10043, "down", {'result': 0}, 2, 1),
                ],
            }
            for name, content in rows.items():
                (root / name).write_text("".join(json.dumps(row) + "\n" for row in content), "utf-8")
            (root / "summary.md").write_text(
                "| tcp_1_up_8105.jsonl | up | 127.0.0.1:12345 → 47.117.173.152:8105 | 2 | 0 |\n"
                "| tcp_2_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:12345 | 1 | 0 |\n",
                "utf-8")
            with self.assertRaisesRegex(ValueError, "10201"):
                read_snapshot(root)

            rows["tcp_2_down_8105.jsonl"].append(frame(10201, "down", {}, 4, 2))
            summary = root / 'summary.md'
            summary.write_text(summary.read_text('utf-8').replace('| 1 | 0 |', '| 2 | 0 |'), 'utf-8')
            rows["tcp_3_up_8105.jsonl"] = [frame(30002, "up", {}, 5, 1)]
            rows["tcp_4_down_8105.jsonl"] = [frame(30003, "down", {}, 6, 1)]
            for name in ("tcp_2_down_8105.jsonl", "tcp_3_up_8105.jsonl", "tcp_4_down_8105.jsonl"):
                (root / name).write_text("".join(json.dumps(row) + "\n" for row in rows[name]), "utf-8")
            with (root / "summary.md").open("a", encoding="utf-8") as summary:
                summary.write("| tcp_3_up_8105.jsonl | up | 127.0.0.1:23456 → 47.117.173.152:8105 | 1 | 0 |\n")
                summary.write("| tcp_4_down_8105.jsonl | down | 47.117.173.152:8105 → 127.0.0.1:23456 | 1 | 0 |\n")
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
        with tempfile.TemporaryDirectory(prefix='m3-reject-') as temporary, patch.object(
                save_generator, 'SLOTS', Path(temporary)):
            with self.assertRaises(ValueError) as error:
                db, report = capture_import.build_imported_save(snapshot, 880000000003)
                self.addCleanup(db.close)
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
import logger
from account_db import AccountDB
root=Path(sys.argv[2]).resolve()
logger._LOG_DIR=str(root/'logs')
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
            (slots / 'Old-00.db').unlink()
            refreshed = manager.sync_slot_registry()
            self.assertEqual(refreshed[3], 'Unassigned.db')
            self.assertEqual({key: value for key, value in refreshed.items() if key != 3},
                             {key: value for key, value in before.items() if key != 3})

    def test_publication_and_cleanup_failures_report_actual_file_state(self):
        for failure in ('link', 'cleanup'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(prefix='m3-failure-') as temporary:
                slots = Path(temporary)
                db, report = self._build_candidate(880000000028)
                self.addCleanup(db.close)
                with patch.object(save_generator, 'SLOTS', slots):
                    if failure == 'link':
                        with patch.object(capture_import.os, 'link', side_effect=OSError('link unavailable')):
                            with self.assertRaises(OSError):
                                capture_import.publish_imported_save(db, report, 'Failure')
                        self.assertFalse(list(slots.glob('*.db')))
                        self.assertFalse((slots / '.import-staging').exists())
                    else:
                        original_remove = capture_import.shutil.rmtree
                        def fail_stage_cleanup(path, *args, **kwargs):
                            if Path(path).parent == slots / '.import-staging':
                                raise OSError('cleanup unavailable')
                            return original_remove(path, *args, **kwargs)
                        with patch.object(capture_import.shutil, 'rmtree', side_effect=fail_stage_cleanup):
                            published = capture_import.publish_imported_save(db, report, 'Failure')
                        self.assertEqual(published.output_path, str(slots / 'Failure.db'))
                        self.assertTrue(published.slot_registration['registered'])
                        self.assertTrue(published.issues)
                        with closing(sqlite3.connect(published.output_path)) as check:
                            self.assertEqual(check.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

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

    def test_available_recovery_preserves_weekly_and_fetters_state(self):
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        uid = 880000000029
        captured_at = 1794833895
        packets = {
            67001: [dict(
                weekly_time=2, daily_time=captured_at, weekly_reward_state=1,
                weekly_scene_open=1, total_explore_c=37,
                mimir=[dict(mimir_id=10001, skill=[dict(skill_level=1)])],
                explore_queue=[])],
            88315: [dict(
                activity_id=1000, next_timestamps=1795228800, fetters_id=3)],
        }
        capture_account_state._restore_activities(db, packets, uid, captured_at)
        capture_account_state._restore_rogueteam(db, packets, uid, captured_at)
        data = db.get_admin_cat_explore_data(uid)
        self.assertEqual(
            (data['weekly_time'], data['weekly_reward_state'], data['weekly_scene_open']),
            (2, 1, 1))
        self.assertGreaterEqual(data['last_weekly_reset_ts'], 1794566400)
        from rogueteam_service import RogueTeamService
        outside = RogueTeamService.get(db=db).get_outside_data(uid)
        self.assertEqual(
            {key: outside[key] for key in ('activity_id', 'next_timestamps', 'fetters_id')},
            dict(activity_id=1000, next_timestamps=1795228800, fetters_id=3))
    def test_unclosed_protocols_are_persisted_as_evidence(self):
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        uid = 880000000030
        db.upsert(
            'users', uid,
            dict(account=f'capture_{uid}', server_id=1, nick='Evidence',
                 level=1, exp=0, extra='{}', hero_num=0, plot_progress=0,
                 is_changed_nick=0, change_nick_times=0, sign='', portrait=0,
                 icon_frame=0, likes=0, ip_location='', register_ts=0))
        snapshot = SimpleNamespace(
            protocol_data={
                88305: [dict(template_id=100001)],
                88315: [dict(
                    activity_id=1000, next_timestamps=1795228800,
                    fetters_id=3)],
            },
            login_frames=[],
            session_id='evidence-test',
            source_sha256={'source': 'frozen'},
            resource_version='332',
            end_frame=SimpleNamespace(timestamp=1794833895),
        )
        capture_account_state.restore_account_state(db, snapshot, uid)
        rows = db.query(
            "SELECT item_id,value_json FROM ops_common "
            "WHERE uid=? AND kind='capture_evidence' ORDER BY item_id", (uid,))
        self.assertEqual([row['item_id'] for row in rows], ['88305'])
        evidence = json.loads(rows[0]['value_json'])
        self.assertEqual(evidence['status'], 'partial')
        self.assertEqual(evidence['session_id'], 'evidence-test')
        self.assertEqual(evidence['payloads'], snapshot.protocol_data[88305])

    def test_partial_recovery_is_excluded_from_verified_commands(self):
        command = 88305
        snapshot = SimpleNamespace(protocol_data={
            command: [dict(template_id=100001)], 14009: []})
        records = capture_account_state.recovery_manifest(snapshot)
        record = next(item for item in records if item['command'] == command)
        self.assertEqual(record['status'], 'partial')
        self.assertNotIn(command, capture_account_state.verified_commands(snapshot))

    def test_unreviewed_equip_group_keeps_evidence_and_other_progress(self):
        snapshot = deepcopy(self.snapshot)
        snapshot.protocol_data[43001] = [dict(stage_base_id=39999, equip_suit_id=46)]
        snapshot.login_frames.append(replace(snapshot.login_frames[-1], cmd=43001,
                                             decoded=snapshot.protocol_data[43001][0]))
        uid = 880000000043
        db, report = capture_import.build_imported_save(snapshot, uid, scope='available')
        self.addCleanup(db.close)
        evidence = db.query("SELECT value_json FROM ops_common WHERE uid=? AND "
                            "kind='capture_evidence' AND item_id='43001'", (uid,))
        row = json.loads(evidence[0]['value_json'])
        self.assertEqual((row['status'], row['payloads']), ('partial', snapshot.protocol_data[43001]))
        self.assertNotIn(43001, report.validation['verified_commands'])
        self.assertEqual(db.query('SELECT 1 FROM battle_equip WHERE uid=?', (uid,)), [])
        self.assertEqual(db.query('SELECT 1 FROM login_push WHERE cmd=43001'), [])

    def test_available_preview_reports_verified_commands(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = _CLI.main([
                str(self.capture_dir), '--name', 'Preview-Available',
                '--scope', 'available'])
        self.assertEqual(result, 0)
        report = json.loads(output.getvalue())['report']
        verified = report['validation']['verified_commands']
        self.assertGreater(len(verified), 0)
        self.assertEqual(len(verified), len(set(verified)))

    def test_imported_purchases_update_real_counts_and_reset_at_game_day(self):
        from lazy_timer import get_daily_5am_ts

        uid = 880000004301
        captured_at = 1794920258
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='购买次数回归'))
        db.set_system_config('save.profile', 'capture_import_v1')
        db.set_currency(uid, 1, 500)
        expected = dict(left_time_coin=2, left_time_fatigue=3)
        capture_account_state._restore_entitlements(db, {15007: [expected]}, uid, captured_at)
        connection = Connection(uid=uid, db=db, generator=generator,
                                codec_encode=codec.encode, codec_decode=codec.decode)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        with patch('time.time', return_value=captured_at):
            first = generator.gen_payload(15007, uid=uid, db=db)
            self.assertEqual(codec.decode(first, 'sc_15007'), expected)
            for command, data, field in ((15012, dict(id=2), 'left_time_coin'),
                                          (15016, dict(num=1), 'left_time_fatigue')):
                request = CoreRequest(command, codec.encode(f'cs_{command}', data), uid=uid)
                response = server.dispatch(request, connection)
                expected[field] += 1
                frame = next(frame for frame in response.frames if frame['sc'] == 15007)
                self.assertEqual(codec.decode(frame['payload'], 'sc_15007'), expected)
            before = db.get_item_num(uid, 1)
            request = CoreRequest(15016, codec.encode('cs_15016', dict(num=100)), uid=uid)
            rejected = server.dispatch(request, connection)
            self.assertNotIn(15007, [frame['sc'] for frame in rejected.frames])
            self.assertEqual(db.get_item_num(uid, 1), before)
            self.assertEqual(codec.decode(generator.gen_payload(15007, uid=uid, db=db), 'sc_15007'), expected)
            with patch.object(connection.to_handler_ctx(), 'codec_encode', side_effect=lambda name, data:
                    b'' if name == 'sc_15007' else codec.encode(name, data)):
                request = CoreRequest(15012, codec.encode('cs_15012', dict(id=2)), uid=uid)
                failed = server.dispatch(request, connection)
                self.assertNotIn(15007, [frame['sc'] for frame in failed.frames])
            self.assertEqual(db.get_item_num(uid, 1), before)
            self.assertEqual(codec.decode(generator.gen_payload(15007, uid=uid, db=db), 'sc_15007'), expected)
        with patch('time.time', return_value=get_daily_5am_ts(captured_at) + 86400):
            payload = generator.gen_payload(15007, uid=uid, db=db)
            self.assertEqual(codec.decode(payload, 'sc_15007'), dict(left_time_coin=0, left_time_fatigue=0))

    def test_imported_seven_day_sign_continues_after_first_cycle(self):
        uid = 880000004300
        previous_sign = dict(activity_id=4400101, sign_count=54, last_sign_time=1794917614)
        now = 1794996854
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='七日签到回归'))
        db.upsert('game_user', uid, {})
        db.execute("INSERT INTO item_catalog(id,type,category) VALUES(24,1,'currency')")
        capture_account_state._restore_entitlements(db, {11015: [previous_sign]}, uid, now)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        connection = Connection(uid=uid, db=db, generator=generator,
                                codec_encode=codec.encode, codec_decode=codec.decode)
        request = CoreRequest(11010, codec.encode('cs_11010', dict(activity_id=4400101)), uid=uid)
        expected_state = dict(activity_id=4400101, sign_count=55, last_sign_time=now)
        with patch('time.time', return_value=now), patch('res_version_manager.get_current_version', return_value='321'):
            for _ in range(2):
                response = server.dispatch(request, connection)
                frames = {frame['sc']: codec.decode(frame['payload'], f"sc_{frame['sc']}")
                          for frame in response.frames}
                self.assertEqual(frames[11011], dict(result=0, item_list=[dict(id=24, num=100)]))
                self.assertEqual(frames[11015], expected_state)
                self.assertEqual(db.get_item_num(uid, 24), 100)
            self.assertEqual(codec.decode(generator.gen_payload(11015, uid=uid, db=db), 'sc_11015'),
                             expected_state)

    def test_enchantment_query_returns_the_imported_selection(self):
        uid = 880000004302
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='联合特勤回归'))
        db.set_system_config('save.profile', 'capture_import_v1')
        expected = dict(free_refreshed_times=2, all_buy_refreshed_times=0, enchantment_battle_list=[22, 9, 7])
        capture_account_state._restore_progress(db, {42001: [expected]}, uid, 1794920258)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        for owner in (uid, uid + 1):
            connection = Connection(uid=owner, db=db, generator=generator,
                                    codec_encode=codec.encode, codec_decode=codec.decode)
            response = server.dispatch(CoreRequest(42002, b'', uid=owner), connection)
            actual = [codec.decode(frame['payload'], 'sc_42001') for frame in response.frames if frame['sc'] == 42001]
            self.assertEqual(actual, [expected] if owner == uid else [])

    def test_resident_snapshot_keeps_separate_caches_and_legacy_payloads(self):
        uid = 880000004303
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='常驻积分隔离'))
        db.set_system_config('save.profile', 'capture_import_v1')
        db.upsert('activity_point', uid, dict(activity_id=999001, point=42), keys=('uid', 'activity_id'))
        db.upsert('activity_point_reward', uid, dict(activity_id=999001, reward_id=99900101),
                  keys=('uid', 'activity_id', 'reward_id'))
        source = {60105: [dict(score_info_list=[dict(key=400, score=17)])],
                  60107: [dict(reward_info_list=[40001])]}
        capture_account_state._restore_activities(db, source, uid, 1794920258)
        legacy_score = codec.decode(generator.gen_payload(60105, uid=uid, db=db), 'sc_60105')
        legacy_rewards = codec.decode(generator.gen_payload(60107, uid=uid, db=db), 'sc_60107')
        self.assertIn(dict(key=999001, score=42), legacy_score['score_info_list'])
        self.assertIn(99900101, legacy_rewards['reward_info_list'])
        for sequence, command in enumerate(source, 1):
            db.execute('INSERT INTO login_push(seq,cmd,header,payload,dynamic) VALUES(?,?,?,?,1)',
                       (sequence, command, generator.build_frame(command, b'')[:11], b''))
            decoded = codec.decode(generator.gen_payload(command, uid=uid, db=db), f'sc_{command}')
            self.assertEqual([decoded], source[command])

    def test_options_and_story_triggers_preserve_imported_state_on_client_push(self):
        uid = 880000004304
        db = AccountDB.new_save_workspace()
        self.addCleanup(db.close)
        db.upsert('users', uid, dict(nick='剧情与选项回归'))
        imported = {85105: [dict(opt_list=[dict(id=1, opt=[dict(key=2, value=1)])])],
                    81001: [dict(info_list=[dict(trigger_group_id=101101, completed_trigger_list=[1011011])])]}
        capture_account_state._restore_profile(db, imported, uid, 1794920258)
        capture_account_state._restore_activities(db, imported, uid, 1794920258)
        server = Core(db=db, generator=generator, codec_encode=codec.encode,
                      codec_decode=codec.decode, log=lambda *a, **k: None)
        for command, data in ((85106, dict(id=1, opt=dict(key=3, value=4))),
                              (81002, dict(trigger_id=1011012, trigger_story=1, trigger_text=0, trigger_select=0))):
            result = server.dispatch(CoreRequest(command, codec.encode(f'cs_{command}', data), uid=uid))
            self.assertFalse(result.reply)
        options = codec.decode(generator.gen_payload(85105, uid=uid, db=db), 'sc_85105')
        triggers = codec.decode(generator.gen_payload(81001, uid=uid, db=db), 'sc_81001')
        self.assertEqual(options, dict(opt_list=[dict(id=1, opt=[dict(key=2, value=1), dict(key=3, value=4)])]))
        self.assertEqual(triggers, dict(info_list=[dict(trigger_group_id=101101, completed_trigger_list=[1011011, 1011012])]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("capture_dir", nargs="?", type=Path, default=CAPTURE_DEFAULT)
    arguments, unittest_arguments = parser.parse_known_args()
    CaptureImportTests.capture_dir = arguments.capture_dir
    unittest.main(argv=[sys.argv[0], *unittest_arguments], verbosity=2)
