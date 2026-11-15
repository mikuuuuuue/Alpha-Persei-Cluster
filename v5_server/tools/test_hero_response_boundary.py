"""A03 hero growth behavior over the real in-memory AccountDB/Core/codec.

Growth metadata uses packaged runtime exports. Native Lua comparisons remain
blocked because the decompiled Lua source and its parser are absent.
"""
import json
import sqlite3
from types import MethodType, SimpleNamespace as NS
import unittest
from pathlib import Path
from unittest.mock import patch

from test_commit_recovery import deny_once, selected
from verify_report_small_fixes import MemoryTests, UID
import codec
import core
import operations
import middleware as mw
import hero_codec
import hero_service
import generator
import achievement_service
from event_bus import EventBus, Events
import event_bus

ROOT = Path(__file__).resolve().parents[1]
CODEC = codec


class HeroResponseTests(MemoryTests):
    def ctx(self):
        return self.conn.to_handler_ctx()

    def frames(self, response, cmd):
        return [codec.decode(frame['payload'], 'sc_' + str(cmd)) for frame in response.frames if frame['sc'] == cmd]

    @classmethod
    def setUpClass(cls):
        source = sqlite3.connect('file:' + (ROOT / 'account.db').as_posix() + '?mode=ro', uri=True)
        source.row_factory = sqlite3.Row
        try:
            breaks = [dict(row) for row in source.execute('SELECT * FROM hero_break_cfg ORDER BY id')]
            levels = [dict(row) for row in source.execute(
                'SELECT level,hero_exp_need FROM game_level_setting ORDER BY level')]
        finally:
            source.close()
        for row in breaks:
            row['cost'] = json.loads(row.get('cost') or '[]')
        cls.hero_cfg = json.loads((ROOT / 'data/hero_blueprint.json').read_text('utf-8-sig'))['1084']
        cls.break_cfg = {row['id']: row for row in breaks}
        cls.level_cfg = {row['level']: dict(id=row['level'], hero_level_exp1=row['hero_exp_need']) for row in levels}

    def setUp(self):
        super().setUp()
        self.sql = self.db._conn()
        handlers_patch = patch.object(EventBus, "_handlers", {})
        handlers_patch.start()
        self.addCleanup(handlers_patch.stop)
        self.bus = EventBus()
        event_bus_patch = patch.object(event_bus, "bus", self.bus)
        event_bus_patch.start()
        self.addCleanup(event_bus_patch.stop)
        achievement_bus_patch = patch.object(achievement_service, "bus", self.bus)
        achievement_bus_patch.start()
        self.addCleanup(achievement_bus_patch.stop)
        self.pushes = []
        self.env = dict(vars(operations))
        self.env.update(vars(core))
        self.env.update(vars(mw))
        self.env.update(dict(OPERATIONS=core.OPERATIONS, Events=Events, bus=self.bus,
                             _mw=mw,
                             CoreRequest=core.CoreRequest, DownFrame=mw.DownFrame))
        self.encode = codec.encode
        self.env.update(level_to_exp=hero_service.level_to_exp,
                        exp_to_level=hero_service.exp_to_level)
        selected("hero_service.py", {"SKILL_COSTS"}, self.env)
        self.db.upsert('hero', 42, hero_codec.initial_hero_row(1084, 100), keys=('uid','id'))
        # The current Core wraps dispatch in the connection's version context.
        # This SQL fixture has no channel/version selection under test.
        race = self.hero_cfg["race"]
        self.db.execute("INSERT OR REPLACE INTO hero_cfg(hero_id,unlock_star,name,race) VALUES(1084,?,?,?)",
                        (self.hero_cfg['unlock_star'], self.hero_cfg['name'], race))
        self.db.execute('DELETE FROM hero_break_cfg')
        for item in self.break_cfg.values():
            if isinstance(item, dict) and item.get("race") == race:
                self.db.execute("INSERT INTO hero_break_cfg(id,race,break_times,user_level,max_level,cost_gold,cost) VALUES(?,?,?,?,?,?,?)",
                    (item["id"], race, item["break_times"], item["user_level"], item["max_level"],
                     item.get("cost_gold", 0), json.dumps(item.get("cost") or [])))
        self.db.execute('DELETE FROM game_level_setting')
        self.db.execute("UPDATE users SET level=?", (max(c["user_level"] for c in self.break_cfg.values() if isinstance(c, dict) and "user_level" in c),))
        self.curve = {v["id"]: v["hero_level_exp1"] for v in self.level_cfg.values()
                      if isinstance(v, dict) and "hero_level_exp1" in v}
        for level, exp in self.curve.items():
            self.db.execute("INSERT INTO game_level_setting(level,hero_exp_need) VALUES(?,?)", (level, exp))
        self.db.execute("INSERT OR REPLACE INTO task_cfg(task_id,name,task_type,condition,need,activity_id) VALUES(900008,'probe',6,8,99,0)")
        self.db.execute("INSERT OR REPLACE INTO task(uid,task_id,progress,task_type) VALUES(42,900008,0,6)")
        self.db.set_currency(42, 2, 100000)
        self.skills = json.loads((ROOT / "hero_skills_cfg.json").read_text("utf-8-sig"))["1084"]
        self.db.execute("UPDATE hero SET skill_list=?", (json.dumps([[sid, 1] for sid in self.skills]),))
        mats = {40101, 40102, 40103, 40104, 40301}
        mats.update(int(iid) for item in self.break_cfg.values() if isinstance(item, dict) and item.get("race") == race
                    for iid, _ in (item.get("cost") or []))
        static = sqlite3.connect('file:' + (ROOT / 'account.db').as_posix() + '?mode=ro', uri=True)
        try:
            catalog = {row[0]: row for row in static.execute(
                'SELECT id,name,type,rare,category FROM item_catalog WHERE id IN (%s)' %
                ','.join('?' for _ in mats), tuple(mats))}
        finally:
            static.close()
        for iid in mats:
            self.db.execute("INSERT OR IGNORE INTO material(uid,id,num) VALUES(42,?,1000)", (iid,))
            self.db.execute("UPDATE material SET num=1000 WHERE id=?", (iid,))
            if iid in catalog:
                self.db.execute("INSERT OR REPLACE INTO item_catalog(id,name,type,rare,category) VALUES(?,?,?,?,?)",
                                catalog[iid])
        selected("task_listener.py", {"_trigger_task_condition", "_push_task_diff", "on_main_interact"}, self.env)
        self.bus.register(self.env["Events"].MAIN_INTERACT, self.env["on_main_interact"])
        self.bus.register(self.env["Events"].HERO_UPGRADE, achievement_service._on_hero_upgrade)
        pulse = patch('lazy_timer.lazy_timer.pulse', side_effect=lambda ctx, uid: getattr(self, 'pulse', lambda *_: None)(ctx, uid))
        pulse.start(); self.addCleanup(pulse.stop)

    def request(self, cmd=14014, data=None):
        if data is None:
            data = {14014: {"id": 1084, "item_list": [{"id": 40101, "num": 1}]},
                    14036: {"hero_id": 1084},
                    14030: {"hero_id": 1084, "skill_id": self.skills[0], "num": 1}}[cmd]
        encoder = self.encode
        self.conn.codec_encode = encoder
        self.conn.to_handler_ctx().codec_encode = encoder
        return self.core.dispatch(self.env["CoreRequest"](cmd, CODEC.encode("cs_" + str(cmd), data), uid=42), self.conn)

    def snapshot(self):
        return {table: self.db.query("SELECT * FROM " + table + " ORDER BY rowid")
                for table in ("hero", "material", "currency", "task", "achievement", "users")}

    def prepare_break(self, cmd=14036):
        if cmd == 14036:
            cap = self.break_cfg[self.hero_cfg["race"] * 10]["max_level"]
            self.db.execute("UPDATE hero SET level=?,exp=?", (cap, self.env["level_to_exp"](cap, self.curve)))

    def ack_sc(self, cmd):
        return {14014: 14015, 14036: 14037, 14030: 14031}[cmd]

    def assert_failure(self, response, cmd, before, code=1):
        self.assertEqual(self.frames(response, self.ack_sc(cmd)), [{"result": code}])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.ctx().pending_frames, [])
        self.assertEqual(self.ctx().touched_items, set())
        self.assertFalse(self.sql.in_transaction)

    def hero_base(self, response):
        return self.frames(response, 14007)[-1]["hero"]["hero_base_info"]

    def relation_listener(self):
        selected("trust_service.py", {"evaluate_relation_conditions_for_hero"}, self.env, "TrustService")
        trust = NS(_intimate_index={1084: [(1084, 1, 1, 1, [1084])]},
                   is_hero_supported=lambda hid: True, get_trust_info=lambda *a: {"trust_level": 1},
                   check_relation_condition=lambda *a: True)
        evaluate = MethodType(self.env["evaluate_relation_conditions_for_hero"], trust)
        self.bus.register(self.env["Events"].HERO_UPGRADE,
                          lambda ctx, uid, **kw: evaluate(ctx, uid, kw["hero_id"]))

    def test_normal_three_operations_keep_existing_frames_and_sql(self):
        phases = []
        self.encode = lambda *a: (phases.append(self.sql.in_transaction), CODEC.encode(*a))[1]
        for count, cmd in enumerate((14014, 14036, 14030), 1):
            self.prepare_break(cmd)
            response = self.request(cmd)
            self.assertEqual(self.frames(response, self.ack_sc(cmd)), [{"result": 0}])
            self.assertNotIn(14009, response.scs)
            self.assertEqual(self.db.query("SELECT progress FROM task")[0]["progress"], 0)
            if cmd == 14030:
                self.assertNotIn(14007, response.scs)
                self.assertLess(response.scs.index(17023), response.scs.index(14031))
                self.assertEqual(json.loads(self.db.query("SELECT skill_list FROM hero")[0]["skill_list"])[0][1], 2)
            else:
                self.assertEqual(response.scs[0], self.ack_sc(cmd))
                self.assertLess(response.scs.index(17023), response.scs.index(14007))
                row = self.db.query("SELECT * FROM hero")[0]
                packet = self.hero_base(response)
                self.assertEqual((packet["level"], packet["exp"], packet["break_level"]),
                                 (row["level"], row["exp"], row["break_level"]))
            self.assertEqual(self.pushes, [])
            self.assertFalse(self.sql.in_transaction)
        self.assertTrue(phases and all(phases))
        self.assertEqual(self.db.query("SELECT exp FROM hero")[0]["exp"], self.env["level_to_exp"](20, self.curve))
        self.assertEqual(self.db.query("SELECT num FROM currency WHERE id=2")[0]["num"],
                         100000 - self.break_cfg[self.hero_cfg["race"] * 10]["cost_gold"])

    def test_ack_encoding_exception_or_empty_rolls_back_each_operation(self):
        for cmd in (14014, 14036, 14030):
            for empty in (False, True):
                with self.subTest(cmd=cmd, empty=empty):
                    self.prepare_break(cmd)
                    before = self.snapshot()
                    def encode(name, data):
                        if name == "sc_" + str(self.ack_sc(cmd)):
                            if empty:
                                return b""
                            raise ValueError("fixture ACK encoding failure")
                        return CODEC.encode(name, data)
                    self.encode = encode
                    self.assert_failure(self.request(cmd), cmd, before)
        self.encode = CODEC.encode

    def test_required_inventory_encoding_exception_or_empty_is_not_swallowed(self):
        for cmd in (14014, 14036, 14030):
            for empty in (False, True):
                with self.subTest(cmd=cmd, empty=empty):
                    self.prepare_break(cmd)
                    before = self.snapshot()
                    def encode(name, data):
                        if name == "sc_17023":
                            if empty:
                                return b""
                            raise ValueError("fixture asset diff encoding failure")
                        return CODEC.encode(name, data)
                    original = generator.gen_payload
                    def generate(sc, *args, **kwargs):
                        if sc == 17023:
                            if empty:
                                return b""
                            raise ValueError("fixture asset diff encoding failure")
                        return original(sc, *args, **kwargs)
                    with patch.object(generator, "gen_payload", side_effect=generate):
                        self.assert_failure(self.request(cmd), cmd, before)
        self.encode = CODEC.encode

    def test_required_hero_refresh_exception_or_missing_is_not_swallowed(self):
        for cmd in (14014, 14036):
            for empty in (False, True):
                with self.subTest(cmd=cmd, empty=empty):
                    self.prepare_break(cmd)
                    before = self.snapshot()
                    def build(*a):
                        if empty:
                            return None
                        raise ValueError("fixture hero refresh encoding failure")
                    with patch.object(hero_codec, "build_hero_14007_frame", side_effect=build):
                        self.assert_failure(self.request(cmd), cmd, before)

    def test_commit_denial_discards_prepared_frames_and_retry_applies_once(self):
        for cmd in (14014, 14036, 14030):
            with self.subTest(cmd=cmd):
                self.prepare_break(cmd)
                before = self.snapshot()
                deny_once(self.sql, "COMMIT")
                response = self.request(cmd)
                self.assert_failure(response, cmd, before, code=9)
                self.assertEqual(response.scs, [self.ack_sc(cmd)])
                self.assertEqual(self.frames(self.request(cmd), self.ack_sc(cmd)), [{"result": 0}])
        self.assertEqual(self.db.query("SELECT progress FROM task")[0]["progress"], 0)
        self.assertEqual(self.db.query("SELECT exp FROM hero")[0]["exp"], self.env["level_to_exp"](20, self.curve))

    def test_post_hero_write_failure_rolls_back_costs_and_growth(self):
        original = self.db.execute
        for cmd in (14014, 14036, 14030):
            with self.subTest(cmd=cmd):
                self.prepare_break(cmd)
                before = self.snapshot()
                def execute(sql, args=()):
                    result = original(sql, args)
                    if sql.startswith(("UPDATE hero SET exp=", "UPDATE hero SET break_level=", "UPDATE hero SET skill_list=")):
                        raise RuntimeError("fixture after hero write")
                    return result
                self.db.execute = execute
                try:
                    response = self.request(cmd)
                finally:
                    self.db.execute = original
                self.assert_failure(response, cmd, before, code=9)

    def test_relation_refresh_follows_skill_ack_and_does_not_double_increment(self):
        self.relation_listener()
        response = self.request(14030)
        self.assertLess(response.scs.index(17023), response.scs.index(14031))
        self.assertLess(response.scs.index(14031), response.scs.index(14007))
        client_level = 1
        for frame in response.frames:
            if frame["sc"] == 14031 and frame["payload"] == b"\x08\x00":
                client_level += 1
            elif frame["sc"] == 14007:
                base = CODEC.decode(frame["payload"], "sc_14007")["hero"]["hero_base_info"]
                client_level = next(s["skill_level"] for s in base["skill"] if s["skill_id"] == self.skills[0])
        self.assertEqual(client_level, 2)
        self.assertEqual(json.loads(self.db.query("SELECT skill_list FROM hero")[0]["skill_list"])[0][1], 2)

    def test_break_callback_precedes_full_refresh_and_increments_once(self):
        self.prepare_break()
        response = self.request(14036)
        client_break = 0
        self.assertLess(response.scs.index(14037), response.scs.index(14007))
        for frame in response.frames:
            if frame["sc"] == 14037 and frame["payload"] == b"\x08\x00":
                client_break += 1
            elif frame["sc"] == 14007:
                client_break = CODEC.decode(frame["payload"], "sc_14007")["hero"]["hero_base_info"]["break_level"]
        self.assertEqual(client_break, 1)

    def test_prior_timer_refresh_precedes_skill_ack_without_mutating_prefix(self):
        prior = []
        def pulse(ctx, uid):
            frame = hero_codec.build_hero_14007_frame(self.db, uid, 1084)
            frame.flag, frame.srv = 1, 77
            prior.append(frame)
            ctx.append_frame(frame)
        self.pulse = pulse
        response = self.request(14030)
        # Core now emits completed timer notifications before operation frames.
        # The old snapshot applies first, then the Lua callback adds one level.
        self.assertLess(response.scs.index(14007), response.scs.index(14031))
        result = next(f for f in response.frames if f["sc"] == 14007)
        self.assertEqual((result["flag"], result["srv"]), (1, 77))
        new = self.hero_base(response)
        old = CODEC.decode(prior[0].payload, "sc_14007")["hero"]["hero_base_info"]
        self.assertEqual(next(s["skill_level"] for s in new["skill"] if s["skill_id"] == self.skills[0]), 1)
        self.assertEqual(next(s["skill_level"] for s in old["skill"] if s["skill_id"] == self.skills[0]), 1)
        self.assertEqual(json.loads(self.db.query("SELECT skill_list FROM hero")[0]["skill_list"])[0][1], 2)

    def test_late_skeleton_failure_restores_timer_frame_and_drops_growth_notices(self):
        self.relation_listener()
        before = self.snapshot()
        prior = self.env["DownFrame"](10701, CODEC.encode("sc_10701", {"timestamp": 123}), flag=1, srv=77)
        self.pulse = lambda ctx, uid: ctx.append_frame(prior)
        with patch.object(mw, "get_skeleton", return_value={"frames": [{"sc": 18002, "hex": "invalid"}]}):
            response = self.request(14030)
        self.assert_failure(response, 14030, before)
        self.assertEqual(response.scs, [10701, 14031])
        self.assertEqual((response.frames[0]["flag"], response.frames[0]["srv"]), (1, 77))

    def test_exp_overflow_refunds_rollback_on_response_failure_then_match_success(self):
        cap = self.break_cfg[self.hero_cfg["race"] * 10]["max_level"]
        max_exp = self.env["level_to_exp"](cap, self.curve)
        old_exp = max_exp - 500
        old_level = self.env["exp_to_level"](old_exp, self.curve, cap)
        self.db.execute("UPDATE hero SET exp=?,level=?", (old_exp, old_level))
        data = {"id": 1084, "item_list": [{"id": 40102, "num": 2}]}
        before = self.snapshot()
        self.encode = lambda *a: b""
        self.assert_failure(self.request(14014, data), 14014, before)
        self.encode = CODEC.encode
        response = self.request(14014, data)
        self.assertEqual(self.frames(response, 14015), [{"result": 0}])
        self.assertEqual(self.db.query("SELECT exp FROM hero")[0]["exp"], max_exp)
        self.assertEqual(self.db.query("SELECT num FROM material WHERE id=40102")[0]["num"], 999)
        self.assertEqual(self.db.query("SELECT num FROM material WHERE id=40101")[0]["num"], 1001)

    def test_insufficient_material_after_gold_deduction_rolls_back_break(self):
        self.prepare_break()
        mat = self.break_cfg[self.hero_cfg["race"] * 10]["cost"][0][0]
        self.db.execute("UPDATE material SET num=0 WHERE id=?", (mat,))
        before = self.snapshot()
        self.assert_failure(self.request(14036), 14036, before, code=3)

    def test_two_intentional_skill_upgrades_remain_two_paid_operations(self):
        for _ in range(2):
            response = self.request(14030)
            self.assertEqual(self.frames(response, 14031), [{"result": 0}])
            self.assertNotIn(14007, response.scs)
        self.assertEqual(json.loads(self.db.query("SELECT skill_list FROM hero")[0]["skill_list"])[0][1], 3)
        cost = sum(self.env["SKILL_COSTS"][lv][1] for lv in (1, 2))
        self.assertEqual(self.db.query("SELECT num FROM material WHERE id=40301")[0]["num"], 1000 - cost)


if __name__ == "__main__":
    unittest.main(verbosity=2)
