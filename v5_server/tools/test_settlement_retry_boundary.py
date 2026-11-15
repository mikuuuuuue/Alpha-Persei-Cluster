"""A105: real memory Core/AccountDB/codec receipt replay with regular-settlement slice.

The _settle_frames boundary applies actual weekly challenge SQL and codec updates.
It excludes full drop rewards, notifications, UDP registration, and the native client.
"""
import ast
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

from verify_report_small_fixes import MemoryTests, UID
import core
import middleware as mw
import codec
import enemy_kill_service
import weekly_challenge_service as ws
import generator


class SettlementRetryTests(MemoryTests):
    def setUp(self):
        super().setUp()
        self.ws = ws
        self.ns = vars(mw)
        self.env = {"clock": [7], "calls": []}
        cycle = patch.object(ws, "get_core_verification_cycle", side_effect=lambda now_ts=None: self.env["clock"][0])
        cycle.start(); self.addCleanup(cycle.stop)
        counters = patch.object(enemy_kill_service, "record_battle", return_value=[])
        counters.start(); self.addCleanup(counters.stop)
        def settle(ctx, uid, bid, result, dest, *, heroes=None, battle_info=None, **kwargs):
            self.env["calls"].append(bid)
            if result == 1:
                stages = ws.get_core_verification_stages(self.env["clock"][0])
                stage = next(s for s in stages[0] + stages[1] if int(s["id"]) == int(dest))
                ctx.db.record_core_verification_stage_clear(
                    uid, self.env["clock"][0], dest, stage["boss_type"], stage["difficult"],
                    int((battle_info or {}).get("battle_time") or 0), heroes=heroes)
                payload = ctx.codec_encode("sc_75009", ws.get_core_verification_data(uid, ctx.db))
                frames = [mw.DownFrame(75009, payload)]
            else:
                frames = []
            br = mw.build_battle_result(bid, result, dest, clear_times=1, heroes=heroes,
                                       use_seconds=max(0, int((battle_info or {}).get("battle_time") or 0)) // 1000)
            return br, frames
        settle_patch = patch.object(mw, "_settle_frames", side_effect=settle)
        settle_patch.start(); self.addCleanup(settle_patch.stop)
        sessions = patch.dict(mw._BATTLE_SESSIONS, {}, clear=True)
        sessions.start(); self.addCleanup(sessions.stop)
        self.db.record_core_verification_stage_clear(UID, 7, 7101, 1, 1, 30000, score=0, heroes=[1011])
        self.core = core.Core(db=self.db, generator=generator, codec_encode=codec.encode,
                              codec_decode=codec.decode, log=lambda *a, **k: None)
        self.bid = 105001
        self.ctx = self.new_context()
        self.register(self.bid)

    def new_context(self):
        return core.Connection(uid=UID, db=self.db, generator=generator,
                               codec_encode=codec.encode, codec_decode=codec.decode,
                               log=lambda *a, **k: None)

    def register(self, bid, result=1):
        mw.register_battle_session(bid, UID, dest=7102, stage_type=67, heroes=[1011])
        mw.get_battle_session(bid)["result_data"] = dict(result=result, info=dict(battle_time=30000))

    def finish(self, bid=None, ctx=None):
        req = core.CoreRequest(54032, codec.encode("cs_54032", dict(battle_id=bid or self.bid)), uid=UID)
        return self.core.dispatch(req, ctx or self.ctx)

    def decoded(self, response, cmd):
        return [codec.decode(f["payload"], "sc_" + str(cmd)) for f in response.frames if f["sc"] == cmd]

    def snapshot(self):
        return list(self.db._conn().iterdump())

    def test_first_settlement_preserves_frames_and_repeat_preserves_receipt_only(self):
        first = self.finish()
        self.assertEqual(first.scs, [75009, 54033])
        self.assertEqual(self.decoded(first, 75009)[0]["now_cycle"], 7)
        receipt = self.decoded(first, 54033)[0]
        self.assertEqual(receipt["result"], 0)
        self.assertEqual(receipt["battle_result"]["battle_id"], self.bid)
        self.assertEqual(receipt["battle_result"]["dest"], 7102)
        self.assertEqual(receipt["battle_result"]["result"], 1)
        self.assertEqual([s["id"] for s in self.ws.get_core_verification_data(42, self.db)["stage_info"]], [7101, 7102])
        before = self.snapshot()
        for _ in range(3):
            retry = self.finish()
            self.assertEqual(retry.scs, [54033])
            self.assertEqual(retry.frames[0]["payload"], first.frames[-1]["payload"])
        self.assertEqual(self.env["calls"], [self.bid])
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("extra", mw.get_battle_session(self.bid))

    def test_cross_cycle_retry_cannot_restore_cycle7_state(self):
        first = self.finish()
        self.env["clock"][0] += 1
        current = self.ws.get_core_verification_data(42, self.db)
        self.assertEqual(current["now_cycle"], 8)
        self.assertEqual(current["stage_info"], [])
        before = self.snapshot()
        retry = self.finish()
        self.assertEqual(retry.scs, [54033])
        self.assertEqual(retry.frames[0]["payload"], first.frames[-1]["payload"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.ws.get_core_verification_data(42, self.db), current)
        self.assertEqual(self.env["calls"], [self.bid])

    def test_same_cycle_reset_is_not_undone_by_cached_progress(self):
        self.finish()
        reset = core.CoreRequest(75010, codec.encode("cs_75010", {"type": 0}), uid=UID)
        response = self.core.dispatch(reset, self.ctx)
        self.assertEqual(codec.decode(response.frames[0]["payload"], "sc_75011")["result"], 0)
        current = self.ws.get_core_verification_data(42, self.db)
        self.assertEqual(current["stage_info"], [])
        before = self.snapshot()
        self.assertEqual(self.finish().scs, [54033])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.ws.get_core_verification_data(42, self.db), current)

    def test_legacy_extra_does_not_overwrite_newer_inventory_or_illustrated(self):
        self.finish()
        # Finite cache/SQL fixtures: these do not claim full inventory grants
        # or monster-classification behavior. The encoded absolute frames are real.
        self.db.set_currency(UID, 1, 125)
        old = [mw.DownFrame(17023, codec.encode("sc_17023", {
                   "normal_items": [{"id": 1, "num": 100}]})),
               mw.DownFrame(52009, codec.encode("sc_52009", {
                   "enemy_info": [{"id": 2017, "times": 1, "is_view": 0}]}))]
        mw.get_battle_session(self.bid)["extra"] = old
        projected = {"inventory": 125, "enemy_times": 2}
        before = self.snapshot()
        retry = self.finish()
        for f in retry.frames:
            if f["sc"] == 17023:
                projected["inventory"] = self.decoded(retry, 17023)[0]["normal_items"][0]["num"]
            if f["sc"] == 52009:
                projected["enemy_times"] = self.decoded(retry, 52009)[0]["enemy_info"][0]["times"]
        self.assertEqual(projected, {"inventory": 125, "enemy_times": 2})
        self.assertEqual(retry.scs, [54033])
        self.assertEqual(self.snapshot(), before)
        self.assertIs(mw.get_battle_session(self.bid)["extra"], old)

    def test_same_uid_new_context_recovers_receipt_without_settling_again(self):
        first = self.finish()
        ctx = self.new_context()
        before = self.snapshot()
        retry = self.finish(ctx=ctx)
        self.assertEqual(retry.scs, [54033])
        self.assertEqual(retry.frames[0]["payload"], first.frames[-1]["payload"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.env["calls"], [self.bid])

    def test_retry_does_not_drain_unrelated_pending_notifications(self):
        self.finish()
        pending = [mw.DownFrame(17023, b"fixture", flag=1, srv=88)]
        handler_ctx = self.ctx.to_handler_ctx()
        handler_ctx.pending_frames = pending
        request = core.CoreRequest(54032, codec.encode("cs_54032", {"battle_id": self.bid}), uid=UID)
        response = mw.h_54032(request.to_cs_request(), handler_ctx)
        self.assertEqual([frame.cmd for frame in response.frames], [54033])
        self.assertIs(handler_ctx.pending_frames, pending)
        self.assertEqual([(frame.payload, frame.flag, frame.srv) for frame in pending], [(b"fixture", 1, 88)])

    def test_other_battle_still_settles_and_old_receipt_does_not_revert_it(self):
        first = self.finish()
        self.register(self.bid + 1)
        second = self.finish(self.bid + 1)
        self.assertEqual(second.scs, [75009, 54033])
        before = self.snapshot()
        retry = self.finish()
        self.assertEqual(retry.scs, [54033])
        self.assertEqual(retry.frames[0]["payload"], first.frames[-1]["payload"])
        self.assertEqual(self.env["calls"], [self.bid, self.bid + 1])
        self.assertEqual(self.snapshot(), before)

    def test_failure_and_quit_keep_result_and_wire_request_correlation(self):
        for result in (2, 3):
            with self.subTest(result=result):
                bid = self.bid + result
                self.register(bid, result=result)
                first = self.finish(bid)
                retry = self.finish(bid)
                self.assertEqual(first.scs, [54033])
                self.assertEqual(retry.scs, [54033])
                payload = retry.frames[0]["payload"]
                receipt = codec.decode(payload, "sc_54033")
                self.assertEqual(receipt["battle_result"]["result"], result)
                self.assertEqual(receipt["battle_result"].get("all_drop_list", []), [])
                raw = mw.CSResponse([mw.DownFrame(54033, payload)]).to_bytes(index=17, server_idx=28)
                self.assertEqual(struct.unpack(">H", raw[:2])[0], len(raw) - 2)
                self.assertEqual(struct.unpack(">HHH", raw[5:11]), (54033, 17, 29))
                self.assertEqual(raw[11:], payload)
                self.assertEqual(payload, first.frames[-1]["payload"])


def negative_control(path):
    test = SettlementRetryTests()
    test.setUp()
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8-sig"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "h_54032")
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), test.ns)
        original_handler = mw.CORE_HANDLERS[54032]
        mw.CORE_HANDLERS[54032] = test.ns["h_54032"]
        test.addCleanup(lambda: mw.CORE_HANDLERS.__setitem__(54032, original_handler))
        first = test.finish()
        test.env["clock"][0] += 1
        current = test.ws.get_core_verification_data(42, test.db)
        before = test.snapshot()
        retry = test.finish()
        replay = test.decoded(retry, 75009)[0]
        assert current["now_cycle"] == 8 and current["stage_info"] == []
        assert replay["now_cycle"] == 7 and [s["id"] for s in replay["stage_info"]] == [7101, 7102]
        assert before == test.snapshot() and test.env["calls"] == [test.bid]
        assert test.decoded(first, 54033) == test.decoded(retry, 54033)
        return dict(source=str(path), current_state=current, stale_replayed_state=replay,
                    retry_cmds=retry.scs, settlement_calls=test.env["calls"],
                    sql_unchanged=True, receipt_unchanged=True,
                    boundary="actual regular-Core fragments/SQL/service/handler/codec; no full reward engine or native client")
    finally:
        test.doCleanups()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--negative-control":
        print(json.dumps(negative_control(sys.argv[2]), ensure_ascii=False))
    else:
        unittest.main(verbosity=2)
