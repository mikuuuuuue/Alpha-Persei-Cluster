# -*- coding: utf-8 -*-
"""tests/m2_defect_checks.py — M2 既有缺陷修复的单测集合（Task 2/3/5）

共享助手 _setup_temp_db()：account.db 临时副本 + 副表，模式复制自
tests/m1_dispatch_check.py（测试隔离口径，不污染真实库）。
"""
import glob
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_DIR not in sys.path:
    sys.path.insert(0, V5_DIR)


def _setup_temp_db():
    workdir = tempfile.mkdtemp(prefix="m2_defect_")
    src = os.path.join(V5_DIR, "account.db")
    dst = os.path.join(workdir, "account.db")
    shutil.copy2(src, dst)
    for side in ("-wal", "-shm"):
        for f in glob.glob(src + side):
            shutil.copy2(f, dst + side)
    from account_db import get_db
    return get_db(dst), workdir


def test_gen_13057_payload():
    import generator as gen
    from codec import decode as dec
    db, _wd = _setup_temp_db()
    try:
        # 基线库 uid=999999 仅有 sign=0 行，空 enabled 编码为 b""（falsy）会误报；
        # 先种一行 sign=1，同时验证 ops_common 驱动组装 → return 全链路
        # （模式复制 equip_service.save_auto_decompose_cfg，INSERT 略偏离 brief 逐字稿）
        db.execute(
            "INSERT INTO ops_common (uid, kind, item_id, name, value_json) VALUES (?, 'auto_decompose', ?, '', ?) "
            "ON CONFLICT(uid, kind, item_id) DO UPDATE SET value_json=excluded.value_json",
            (999999, "1", '{"sign": 1}')
        )
        out = gen.gen_payload(13057, uid=999999, db=db)
        assert out, "gen_payload(13057) 现状返回 None（构造 enabled 后缺 return）"
        dec_out = dec(out, "sc_13057")
        assert "type_list" in dec_out, "sc_13057 应含 type_list 字段，实际 %r" % dec_out
        print("[+] gen_13057: %dB, type_list=%r" % (len(out), dec_out.get("type_list")))
    finally:
        shutil.rmtree(_wd, ignore_errors=True)


if __name__ == "__main__":
    test_gen_13057_payload()
    print("ALL PASSED")
