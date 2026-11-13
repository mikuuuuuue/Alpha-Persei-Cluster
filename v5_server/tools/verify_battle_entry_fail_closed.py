"""A369: source-selected middleware, real dynamic payload/TeamServer and memory SQL."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from verify_report_small_fixes import MemoryTests, UID
from test_commit_recovery import selected
import battle_payload
import codec
import core
import generator
import hero_codec
import middleware as mw
from polyhedron_service import PolyhedronRunManager
import team_server

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / 'archive/battle_entry_fail_closed_20261022'
HERO_ID = 1084


def wire_fields(payload):
    return [(field, value) for field, wire, value in mw._pb_fields(payload) if wire == 2]


def entry_heroes(payload):
    player = next(value for field, value in wire_fields(payload) if field == 1)
    battle = next(value for field, value in wire_fields(player) if field == 2)
    return [codec.decode(value, 'battle_hero_net_rec')
            for field, value in wire_fields(battle) if field == 4]


class BattleEntryFailureTests(MemoryTests):
    def setUp(self):
        super().setUp()
        self.db.execute("UPDATE users SET nick='current-account',level=60 WHERE uid=?", (UID,))
        self.db.set_currency(UID, 4, 180)
        self.db.upsert('hero', UID, hero_codec.initial_hero_row(HERO_ID, 100), keys=('uid','id'))
        self.db.execute('UPDATE hero SET exp=31 WHERE uid=? AND id=?',(UID,HERO_ID))
        sessions = patch.dict(mw._BATTLE_SESSIONS, {}, clear=True)
        sessions.start(); self.addCleanup(sessions.stop)
        self.ctx = self.conn.to_handler_ctx()
        self.env = dict(vars(mw))
        self.template = Mock(return_value=(ROOT / 'sc_54003_payload.bin').read_bytes())
        self.logs = []
        self.conn.battle_seq[0] = 7; self.conn.battle_id[0] = 777; self.conn.battle_stage[0] = 1031900
        self.ctx.log = lambda *a, **kw: self.logs.append(a)
        self.ctx.hero_last_payload = [b'previous-battle']
        self.ctx.battle_03_payload = self.template
        self.skeleton = Mock(wraps=mw.get_skeleton)
        skeleton = patch.object(mw, 'get_skeleton', self.skeleton)
        skeleton.start(); self.addCleanup(skeleton.stop)
        mw.register_battle_session(777, UID, dest=1031900, heroes=[HERO_ID])
        team = team_server.TeamServer()
        self.team_patch = patch.object(team_server.TeamServer, 'get_instance', return_value=team)
        self.team_patch.start()
        self.addCleanup(self.team_patch.stop)
        team.record_stage_team(self.ctx, UID, 1, 1032302, heroes=[HERO_ID], cooperate_skill=123)

    def request(self, heroes=None, stage_type=1, dest=1032302, uid=UID):
        self.skeleton.reset_mock()
        if heroes is None:
            heroes = [{'hero_id': HERO_ID, 'hero_type': 1}, {'hero_id': 318, 'hero_type': 2}]
        raw = codec.encode('cs_54030', {'common_info': dict(hero_list=heroes, type=stage_type,
            dest=dest, activity_id=0, battle_times=1, cooperate_unique_skill_id=0,
            cooperate_unique_skill_level=0), 'is_restarted_battle': 0})
        req = core.CoreRequest(54030, raw, uid=uid)
        conn = self.conn
        if uid != self.conn.uid:
            conn = core.Connection(uid=uid, db=self.db, generator=generator,
                                   codec_encode=codec.encode, codec_decode=codec.decode,
                                   log=lambda *a, **k: None)
            conn.battle_seq = self.conn.battle_seq
            conn.battle_id = self.conn.battle_id
            conn.battle_stage = self.conn.battle_stage
            conn.to_handler_ctx().battle_03_payload = self.template
        return self.core.dispatch(req, conn)

    def snapshot(self):
        return copy.deepcopy(dict(sessions=mw._BATTLE_SESSIONS,
            runtime=[self.conn.battle_seq[0], self.conn.battle_id[0], self.conn.battle_stage[0],
                     self.ctx.hero_last_payload[0]],
            currency=self.db.query('SELECT * FROM currency'),
            teams=self.db.query('SELECT * FROM stage_team'),
            rogue=self.db.query('SELECT * FROM rogueteam_session WHERE uid=?',(UID,)),
            map_nodes=self.db.query('SELECT * FROM chapter_v2_map_node')))

    def assert_failed(self, response, before):
        self.assertEqual(response.scs, [54031])
        self.assertNotEqual(codec.decode(response.frames[0]['payload'], 'sc_54031')['result'], 0)
        self.assertEqual(self.snapshot(), before)
        self.template.assert_not_called()
        self.skeleton.assert_not_called()

    @unittest.skipUnless((EVIDENCE / 'before/v5_server/middleware.py').is_file(),
                         'Pre-fix reproduction requires this repair archive')
    def test_before_source_reproduces_stale_and_missing_hero_packet_success(self):
        before_file = EVIDENCE / 'before/v5_server/middleware.py'
        selected(before_file, {'h_54030'}, self.env)
        old_handler = patch.dict(mw.CORE_HANDLERS, {54030: self.env['h_54030']})
        old_handler.start(); self.addCleanup(old_handler.stop)
        records = []
        for cached in (True, False):
            self.template.return_value = (ROOT / 'sc_54003_payload.bin').read_bytes() if cached else None
            with patch.object(battle_payload, 'build_sc_54003_dynamic', side_effect=RuntimeError('injected builder failure')):
                response = self.request()
            self.assertEqual(codec.decode(response.frames[0]['payload'], 'sc_54031')['result'], 0)
            self.assertIn(54007, response.scs)
            if cached:
                self.assertIn(54003, response.scs)
                raw = next(f['payload'] for f in response.frames if f['sc'] == 54003)
                heroes = entry_heroes(raw)
            else:
                self.assertNotIn(54003, response.scs)
                heroes = []
            records.append(dict(cache_present=cached, cmds=response.scs,
                                heroes=heroes, session_published=self.conn.battle_id[0] in mw._BATTLE_SESSIONS))
        (EVIDENCE / 'before_reproduction.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), 'utf-8')

    def test_builder_exception_rejects_with_or_without_cache_and_preserves_previous_battle(self):
        before = self.snapshot()
        for cache in ((ROOT / 'sc_54003_payload.bin').read_bytes(), None):
            self.template.return_value = cache
            with patch.object(battle_payload, 'build_sc_54003_dynamic', side_effect=RuntimeError('injected failure')):
                self.assert_failed(self.request(), before)

    def test_missing_or_nonbytes_initialization_never_falls_back(self):
        before = self.snapshot()
        for payload in (None, b'', 'not encoded'):
            with patch.object(battle_payload, 'build_sc_54003_dynamic', return_value=payload):
                self.assert_failed(self.request(), before)

    def test_partial_missing_hero_is_rejected_instead_of_silently_omitted(self):
        before = self.snapshot()
        heroes = [{'hero_id': HERO_ID, 'hero_type': 1}, {'hero_id': 99999999, 'hero_type': 1}]
        self.assert_failed(self.request(heroes=heroes), before)

    def test_unknown_account_cannot_reuse_first_accounts_profile(self):
        before = self.snapshot()
        self.assert_failed(self.request(uid=43, heroes=[{'hero_id': 318, 'hero_type': 2}]), before)

    def test_missing_database_uid_and_empty_team_do_not_publish(self):
        before = self.snapshot()
        self.assert_failed(self.request(heroes=[]), before)
        self.assert_failed(self.request(uid=0), before)
        self.conn.db = None
        self.ctx.db = None
        self.assert_failed(self.request(), before)

    def test_start_encoding_exception_or_empty_packet_preserves_state(self):
        before = self.snapshot()
        for fail in (Mock(return_value=None), Mock(side_effect=ValueError('injected start encode failure'))):
            self.ctx.codec_encode = fail
            self.assert_failed(self.request(), before)

    def test_dynamic_sql_failure_leaves_team_session_and_fatigue_unchanged(self):
        self.db.execute('ALTER TABLE equip RENAME TO equip_fault_fixture')
        before = self.snapshot()
        self.assert_failed(self.request(), before)

    def test_session_registration_failure_does_not_replace_context_or_team(self):
        before = self.snapshot()
        with patch.object(mw, 'register_battle_session', side_effect=RuntimeError('injected registration failure')):
            self.assert_failed(self.request(), before)

    def test_retry_after_failure_succeeds_once_with_current_mixed_team(self):
        before = self.snapshot()
        with patch.object(battle_payload, 'build_sc_54003_dynamic', side_effect=RuntimeError('first attempt failed')) as build:
            self.assert_failed(self.request(), before)
            build.assert_called_once()
        response = self.request()
        self.assertEqual([f['sc'] for f in response.frames if f['sc'] in (54031, 54003, 54007)], [54031, 54003, 54007])
        heroes = entry_heroes(response.frames[-2]['payload'])
        self.assertEqual([h['hero_base_info']['id'] for h in heroes], [HERO_ID, 318])
        self.assertEqual([h['hero_type'] for h in heroes], [1, 2])
        self.assertEqual(heroes[0]['hero_base_info']['exp'], 31)
        self.assertEqual(self.conn.battle_seq[0], 8)
        self.assertEqual(len(mw._BATTLE_SESSIONS), 2)
        start = codec.decode(response.frames[-1]['payload'], 'sc_54007')['battle_start']
        self.assertEqual(start['battle_id'], self.conn.battle_id[0])
        self.assertEqual(mw._BATTLE_SESSIONS[start['battle_id']]['heroes'], [HERO_ID, 318])
        self.assertEqual(self.snapshot()['currency'], before['currency'])
        self.assertEqual(json.loads(self.snapshot()['teams'][0]['hero_json']), [HERO_ID])
        self.template.assert_not_called()

    def test_polyhedron_inferred_team_still_initializes_and_failure_does_not_publish(self):
        self.db.upsert('polyhedron_hero', UID, dict(hero_id=HERO_ID), keys=('uid','hero_id'))
        started, _ = self.call(18010, dict(hero_id_list=[HERO_ID], difficulty=1), 18011)
        self.assertEqual(started['result'], 0)
        stage = PolyhedronRunManager.load_run(UID, self.db)['current_stage']['stage_id']
        before = self.snapshot()
        with patch.object(battle_payload, 'build_sc_54003_dynamic', return_value=None):
            self.assert_failed(self.request(heroes=[], stage_type=52, dest=stage), before)
        response = self.request(heroes=[], stage_type=52, dest=stage)
        self.assertEqual([f['sc'] for f in response.frames if f['sc'] in (54031, 54003, 54007)], [54031, 54003, 54007])
        self.assertEqual(entry_heroes(response.frames[-2]['payload'])[0]['hero_base_info']['id'], 3051084)

    def test_rogue_selection_waits_for_required_packets_and_success_keeps_mapping(self):
        self.db.upsert('rogueteam_session', UID, dict(template_id=100001, floor_num=1,
            select_node_id=100, map_info_json=json.dumps([dict(node_id=100,node_type=1,state=0,param=4100001)]),
            in_game=1, flow_json=json.dumps(dict(run_id='entry-test',phase='active'))), keys=('uid','template_id'))
        before = self.snapshot()
        with patch.object(battle_payload, 'build_sc_54003_dynamic', return_value=None):
            self.assert_failed(self.request(stage_type=78, dest=100), before)
        response = self.request(stage_type=78, dest=100)
        self.assertEqual([f['sc'] for f in response.frames if f['sc'] in (54031, 54003, 54007)], [54031, 54003, 54007])
        self.assertEqual(self.conn.battle_stage[0], 4100001)
        self.assertEqual(self.db.query('SELECT select_node_id FROM rogueteam_session WHERE uid=?',(UID,)), [{'select_node_id':100}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
