"""Isolated Flask and parser checks for launch settings and cycle resets."""
from contextlib import ExitStack, closing, redirect_stdout
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['ACCOUNT_DB_PATH'] = ':memory:'

from flask import Flask
from account_db import AccountDB
import account_db
import admin_access
import admin_session_auth as auth
import gm_api
import gm_save_scope
import launch_settings
import linux_manager
import main
import server_net
import save_slot_manager
import weekly_challenge_service as weekly

UID = 42
ORIGIN = 'https://launch.example.test'
PASSWORD = 'isolated-launch-password'


class LaunchCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = auth.hash_password(PASSWORD)

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='launch_cycles_')))
        self.save_path = self.folder / 'selected.db'
        workspace = AccountDB.new_save_workspace()
        try:
            workspace.execute('INSERT INTO users(uid,nick) VALUES(?,?)', (UID, 'launch probe'))
            workspace.set_currency(UID, 2, 777)
            workspace.execute('INSERT INTO material(uid,id,num) VALUES(?,?,?)', (UID, 41201, 9))
            workspace.get_equip_seizure_progress(UID, 1_792_771_200)
            workspace.execute(
                "UPDATE equip_seizure_progress SET today_max_score=9000,sum_score=15000,"
                "got_reward_id_list='[1]',team_heroes='[1075]' WHERE uid=?", (UID,))
            with closing(sqlite3.connect(self.save_path)) as target:
                workspace._conn().backup(target)
        finally:
            workspace.close()
        self.db = AccountDB.open_existing(self.save_path)
        self.addCleanup(self.db.close)

        self.stack.enter_context(patch.object(account_db, '_db', self.db))
        self.stack.enter_context(patch.object(gm_api, '_global_get_db', return_value=self.db))
        self.stack.enter_context(patch.object(gm_save_scope, 'catalog', return_value=[
            dict(filename=self.save_path.name, uid=UID)]))
        self.stack.enter_context(patch.object(
            save_slot_manager, 'get_slot_manager',
            return_value=save_slot_manager.SaveSlotManager(self.folder)))
        self.stack.enter_context(patch.object(server_net, '_online_game_conns', {}))
        self.backups = self.stack.enter_context(
            patch.object(AccountDB, 'backup_save_file', return_value='isolated-backup'))

        self.config_path = self.folder / 'data' / 'launch_overrides.json'
        self.stack.enter_context(patch.object(launch_settings, 'ROOT', self.folder))
        self.stack.enter_context(patch.object(launch_settings, 'CONFIG', self.config_path))
        self.stack.enter_context(patch.object(launch_settings, '_current', dict(
            https_port=19443, http_port=0, gw_port=9000, game_port=9105, battle_port=0,
            host_ip='127.0.0.1', web_bind='127.0.0.1', dns=False, dns_upstream=[],
            cdn_mode='off', db_path=self.save_path.name, client_assets_dir='', log_level='INFO',
            replay_enabled=False, replay_path='',
        )))
        self.stack.enter_context(patch.object(launch_settings, '_restart', None))
        self.stack.enter_context(patch.object(launch_settings, '_pending', False))
        self.stack.enter_context(patch.object(gm_api, '_scan_available_replays', return_value=[]))

        password_file = self.folder / 'admin.json'
        password_file.write_text(json.dumps({
            'schema': 1,
            'password_hash': self.password_hash,
            'origin': ORIGIN,
            'session_seconds': 3600,
            'trusted_proxies': [],
        }), encoding='utf-8')
        self.stack.enter_context(patch.dict(os.environ))
        os.environ.pop(admin_access.AUTH_FILE_ENV, None)
        os.environ[auth.PASSWORD_FILE_ENV] = str(password_file)
        with auth._STATES_LOCK:
            auth._STATES.clear()
        app = Flask(__name__)
        app.testing = True
        admin_access.install_admin_guard(app)
        app.register_blueprint(gm_api.gm_bp, url_prefix='/api/gm')
        self.client = app.test_client()

    def request(self, method, path, *, json_body=None, headers=None):
        return self.client.open(path, method=method, base_url=ORIGIN,
                                json=json_body, headers=headers or {})

    def login(self):
        response = self.request('POST', '/api/gm/auth/login', json_body={'password': PASSWORD},
                                headers={'Origin': ORIGIN})
        self.assertEqual(response.status_code, 200)
        return {'Origin': ORIGIN, auth.CSRF_HEADER: response.json['csrf_token']}

    def post_launch(self, body, headers):
        return self.request('POST', '/api/gm/system/launch_config',
                            json_body=body, headers=headers)

    def cycle_headers(self, csrf):
        return {'Origin': ORIGIN, auth.CSRF_HEADER: csrf[auth.CSRF_HEADER],
                'X-Save-Name': self.save_path.name}

    def cycle_card(self, headers):
        response = self.request('GET', f'/api/gm/cycles?uid={UID}&kind=seizure', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0, response.json)
        return response.json['data'][0]

    def asset_state(self):
        tables = ('currency', 'material', 'hero_piece', 'equip', 'servant', 'hero', 'backhome_hero')
        return {table: self.db.query(f'SELECT * FROM {table} ORDER BY rowid') for table in tables}

    def parse_through_main(self, raw, launcher_arg_count):
        captured = []
        original = launch_settings.parse_args

        class ParsedArgs(Exception):
            pass

        def capture(parser, argv=None, **kwargs):
            captured.append(original(parser, argv, **kwargs))
            raise ParsedArgs()

        with patch.object(launch_settings, 'parse_args', side_effect=capture):
            with self.assertRaises(ParsedArgs):
                main.main(argv=raw, launcher_arg_count=launcher_arg_count)
        self.assertEqual(len(captured), 1)
        return captured[0]

    def test_launch_config_rejects_bad_ports_unknown_fields_and_preserves_file_on_write_error(self):
        headers = self.login()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        original = b'{"overrides":{"cdn_mode":"off"}}\n'
        self.config_path.write_bytes(original)
        invalid = [{key: value} for key in launch_settings.PORTS for value in (-1, 65536, True, '8105')]
        for body in [*invalid, {'unknown_field': True}]:
            response = self.post_launch(body, headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['code'], gm_api.GMErrorCode.PARAM_INVALID)
            self.assertEqual(self.config_path.read_bytes(), original)

        with patch.object(linux_manager, 'backup_write', side_effect=OSError('disk full')):
            response = self.post_launch({'cdn_mode': 'relay'}, headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], gm_api.GMErrorCode.SERVICE_ERROR)
        self.assertEqual(self.config_path.read_bytes(), original)

    def test_launch_api_requires_login_and_valid_csrf(self):
        unauthenticated = self.post_launch({'cdn_mode': 'relay'}, {'Origin': ORIGIN})
        self.assertEqual(unauthenticated.status_code, 401)
        cycle = self.request('POST', '/api/gm/cycles/seizure/reset',
                             json_body={'uid': UID, 'token': 'fixture'}, headers={'Origin': ORIGIN})
        self.assertEqual(cycle.status_code, 401)
        authenticated = self.login()
        invalid_csrf = dict(authenticated, **{auth.CSRF_HEADER: 'x' * 43})
        response = self.post_launch({'cdn_mode': 'relay'}, invalid_csrf)
        self.assertEqual(response.status_code, 403)
        cycle = self.request('POST', '/api/gm/cycles/seizure/reset',
                             json_body={'uid': UID, 'token': 'fixture'}, headers=invalid_csrf)
        self.assertEqual(cycle.status_code, 403)
        self.assertFalse(self.config_path.exists())
        self.backups.assert_not_called()

    def test_saved_launch_values_reach_real_main_parser_and_cli_values_override_them(self):
        headers = self.login()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with patch.object(linux_manager, 'probe_endpoints', return_value=[]) as probe:
            response = self.post_launch({
                'https_port': 19444,
                'cdn_mode': 'cache',
                'db_path': self.save_path.name,
                'client_assets_dir': 'saved-assets',
            }, headers)
        self.assertEqual(response.json['code'], 0, response.json)
        self.assertEqual(probe.call_count, 1)
        saved = json.loads(self.config_path.read_text('utf-8'))['overrides']
        self.assertEqual((saved['https_port'], saved['cdn_mode'], saved['db_path'],
                          saved['client_assets_dir']),
                         (19444, 'cache', self.save_path.name, 'saved-assets'))

        base = ['--https-port', '19443', '--db', 'base.db', '--cdn-mode', 'off',
                '--client-assets-dir', 'base-assets']
        parsed = self.parse_through_main(base, len(base))
        self.assertEqual((parsed.https_port, parsed.cdn_mode, parsed.db, parsed.client_assets_dir),
                         (19444, 'cache', self.save_path.name, 'saved-assets'))

        explicit = ['--https-port', '19445', '--cdn-mode', 'relay', '--db', 'cli.db',
                    '--client-assets-dir', 'cli-assets']
        parsed = self.parse_through_main(base + explicit, len(base))
        self.assertEqual((parsed.https_port, parsed.cdn_mode, parsed.db, parsed.client_assets_dir),
                         (19445, 'relay', 'cli.db', 'cli-assets'))

    def test_managed_restart_schedules_owned_callback_and_direct_run_rejects_it(self):
        callback = Mock()
        with (patch.object(launch_settings, '_pending', False),
              patch.object(launch_settings, '_restart', callback),
              patch.object(launch_settings, 'supervisor', return_value='cli'),
              patch.object(launch_settings.threading, 'Timer') as timer):
            launch_settings.save({}, [], restart=True)
            self.assertTrue(launch_settings._pending)
        timer.assert_called_once_with(0.75, callback)
        timer.return_value.start.assert_called_once_with()

        with (patch.object(launch_settings, '_pending', False),
              patch.object(launch_settings, '_restart', callback),
              patch.object(launch_settings, 'supervisor', return_value=''),
              patch.object(launch_settings.threading, 'Timer') as timer):
            with self.assertRaisesRegex(ValueError, '命令行直接运行'):
                launch_settings.save({}, [], restart=True)
        timer.assert_not_called()

    def test_supervised_runner_relaunches_only_after_restart_exit_code(self):
        first, second = Mock(), Mock()
        first.wait.return_value = launch_settings.RESTART_EXIT_CODE
        second.wait.return_value = 0
        with patch.object(launch_settings.subprocess, 'Popen', side_effect=[first, second]) as popen, \
             patch.object(launch_settings.signal, 'signal', return_value=object()) as signal, \
             redirect_stdout(io.StringIO()):
            result = launch_settings.run_supervised(['--db', self.save_path.name])
        self.assertEqual(result, 0)
        self.assertEqual(popen.call_count, 2)
        command, options = popen.call_args_list[0].args[0], popen.call_args_list[0].kwargs
        self.assertEqual(command[:4], [sys.executable, '-B', '-X', 'utf8'])
        self.assertEqual(command[-2:], ['--db', self.save_path.name])
        self.assertEqual(options['env']['AG_LAUNCH_SUPERVISOR'], 'cli')
        self.assertEqual(options['env']['AG_LAUNCH_PARENT_PID'], str(os.getpid()))
        self.assertEqual(signal.call_count, 2)

    def test_cycle_reset_is_offline_rejects_old_token_and_does_not_grant_or_repeat_assets(self):
        headers = self.cycle_headers(self.login())
        before = self.asset_state()
        card = self.cycle_card(headers)
        response = self.request('POST', '/api/gm/cycles/seizure/reset',
                                json_body={'uid': UID, 'token': card['token']}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['code'], 0, response.json)
        progress = self.db.query('SELECT today_max_score,sum_score,got_reward_id_list FROM equip_seizure_progress WHERE uid=?', (UID,))[0]
        self.assertEqual((progress['today_max_score'], progress['sum_score'],
                          json.loads(progress['got_reward_id_list'])), (0, 0, []))
        self.assertEqual(self.asset_state(), before)

        snapshot = list(self.db._conn().iterdump())
        stale = self.request('POST', '/api/gm/cycles/seizure/reset',
                             json_body={'uid': UID, 'token': card['token']}, headers=headers)
        self.assertEqual(stale.json['code'], gm_api.GMErrorCode.PARAM_INVALID)
        self.assertEqual(list(self.db._conn().iterdump()), snapshot)

        refreshed = self.cycle_card(headers)
        repeated = self.request('POST', '/api/gm/cycles/seizure/reset',
                                json_body={'uid': UID, 'token': refreshed['token']}, headers=headers)
        self.assertEqual(repeated.json['code'], 0, repeated.json)
        self.assertEqual(self.asset_state(), before)

    def test_online_selected_save_rejects_cycle_reset_without_mutation(self):
        headers = self.cycle_headers(self.login())
        card = self.cycle_card(headers)
        before = list(self.db._conn().iterdump())
        class OnlineConnection(SimpleNamespace):
            __hash__ = object.__hash__

        connection = OnlineConnection(db=SimpleNamespace(path=str(self.save_path)))
        with patch.object(server_net, '_online_game_conns', {UID: {connection}}):
            response = self.request('POST', '/api/gm/cycles/seizure/reset',
                                    json_body={'uid': UID, 'token': card['token']}, headers=headers)
        self.assertEqual(response.json['code'], gm_api.GMErrorCode.PARAM_INVALID)
        self.assertEqual(list(self.db._conn().iterdump()), before)

    def test_iteration_card_and_reset_use_saved_rotation_through_readonly_api(self):
        now = int(time.time())
        cycle = weekly.get_core_verification_cycle(now) % 16 + 1
        period = dict(now_cycle=cycle, next_cycle=cycle % 16 + 1,
                      refresh_timestamp=weekly.get_next_thursday_5am(now))
        self.db.execute(
            'INSERT INTO ops_common(uid,kind,item_id,value_json) VALUES(?,?,?,?)',
            (UID, 'core_verification_rotation', 'current', json.dumps(period)))
        stage = weekly.get_core_verification_stages(cycle)[0][0]
        self.db.execute(
            'INSERT INTO core_verification_stage_record '
            '(uid,cycle,info_id,boss_type,difficult,sign) VALUES(?,?,?,?,?,1)',
            (UID, cycle, stage['id'], stage['boss_type'], stage['difficult']))
        headers = self.cycle_headers(self.login())
        assets = self.asset_state()
        response = self.request('GET', f'/api/gm/cycles?uid={UID}&kind=iteration', headers=headers)
        self.assertEqual(response.status_code, 200)
        card = response.json['data'][0]
        self.assertNotIn('error', card)
        self.assertTrue(card['token'])
        self.assertTrue(any(row['id'] == f"stage-{stage['id']}" and row['current'] == 1
                            for row in card['rows']))
        reset = self.request('POST', '/api/gm/cycles/iteration/reset',
                             json_body={'uid': UID, 'token': card['token']}, headers=headers)
        self.assertEqual(reset.json['code'], 0, reset.json)
        self.assertFalse(self.db.query(
            'SELECT 1 FROM core_verification_stage_record WHERE uid=? AND cycle=?', (UID, cycle)))
        self.assertEqual(self.asset_state(), assets)
        saved = self.db.query(
            "SELECT value_json FROM ops_common WHERE uid=? "
            "AND kind='core_verification_rotation' AND item_id='current'", (UID,))[0]
        self.assertEqual(json.loads(saved['value_json']), period)


if __name__ == '__main__':
    unittest.main(verbosity=2)
