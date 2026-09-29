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
    import account_db as _adb
    _adb._db = None  # get_db 是进程级单例（首调绑定路径）：重置后本测试绑定新临时库，
    from account_db import get_db  # 否则上一个用例 rmtree 后残留实例 → unable to open database file
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
        db.close()  # Minor 修复：win32 下先关 SQLite 连接再删目录，否则 rmtree 静默泄漏临时目录
        shutil.rmtree(_wd, ignore_errors=True)


def test_on_polyhedron_pass_ctx_none():
    # 现状红：ctx=None → AttributeError('NoneType' has no 'db')，被 emit 沙箱吞掉
    import task_listener
    task_listener.on_polyhedron_pass(None, 999999, times=1)  # 不得抛异常
    print("[+] ctx=None 容忍通过")


def test_on_polyhedron_pass_advances_cond423():
    import types
    import task_listener
    db, _wd = _setup_temp_db()
    try:
        FRESH_UID = 888001
        # 偏离 brief 逐字稿 +1 行：_trigger_task_condition 的按需激活白名单
        # (task_listener.py WHERE 子句) 不含 423，无 task 行时 cond=423 行被过滤；
        # 生产玩家经登录/章节流程持有 task 行，此处种子化复刻生产态使断言可达。
        db.execute("INSERT OR IGNORE INTO task (uid, task_id, progress) VALUES (888001, 100007, 0)")
        task_listener.on_polyhedron_pass(types.SimpleNamespace(db=db), FRESH_UID, times=1)
        rows = db.query(
            "SELECT task_id, progress FROM task WHERE uid=? AND task_id=100007", (FRESH_UID,))
        assert rows and int(rows[0]["progress"]) >= 1, \
            "cond=423 任务 100007 应推进到 ≥1，实际 %r（task_cfg 无 423 行则改断言仅返回无异常）" % rows
        print("[+] 100007 progress=%s" % rows[0]["progress"])
    finally:
        db.close()  # Minor 修复：同上，先关连接再删临时目录
        shutil.rmtree(_wd, ignore_errors=True)


def test_gen_cert_existing_check_verifies_leaf():
    import tempfile
    import gen_cert
    from cryptography import x509 as cx
    from cryptography.hazmat.primitives.asymmetric import padding as _pad

    def _leaf_ok(ca_p, leaf_p):
        ca = cx.load_pem_x509_certificate(open(ca_p, "rb").read())
        leaf = cx.load_pem_x509_certificate(open(leaf_p, "rb").read())
        ca.public_key().verify(leaf.signature, leaf.tbs_certificate_bytes,
                               _pad.PKCS1v15(), leaf.signature_hash_algorithm)
        return True

    with tempfile.TemporaryDirectory(prefix="m2_cert_") as td:
        assert gen_cert.generate_dual_layer_certs(output_dir=td, log=lambda *a, **k: None)
        assert _leaf_ok(os.path.join(td, "sdk_ca.crt"), os.path.join(td, "sdk_cert.pem"))
        # 篡改叶子（复现 09-27 交错写形态：截断重签不可能，直接破坏字节）
        leaf = os.path.join(td, "sdk_cert.pem")
        data = bytearray(open(leaf, "rb").read())
        data[len(data) // 2] ^= 0xFF
        open(leaf, "wb").write(bytes(data))
        # 无 force 复检：现状红——EXISTING 只看 CA 有效期，返回 True 保留坏叶子
        assert gen_cert.generate_dual_layer_certs(output_dir=td, log=lambda *a, **k: None)
        # 坏叶子必须被识别并重造（重造后恢复可验签）
        assert _leaf_ok(os.path.join(td, "sdk_ca.crt"), leaf), \
            "EXISTING 检查放过了与 CA 不匹配的叶子证书"
    print("[+] 叶子验签检查通过")


def test_gen_cert_concurrent_atomicity():
    import threading
    import tempfile
    import gen_cert
    errs = []

    def worker(td, i):
        try:
            assert gen_cert.generate_dual_layer_certs(
                output_dir=td, log=lambda *a, **k: None)
        except Exception as e:
            errs.append("worker%d: %r" % (i, e))

    with tempfile.TemporaryDirectory(prefix="m2_certc_") as td:
        ts = [threading.Thread(target=worker, args=(td, i)) for i in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert not errs, "并发生成异常: %r" % errs
        leftovers = [f for f in os.listdir(td) if f.endswith(".tmp")]
        assert not leftovers, "残留临时文件: %r" % leftovers
    print("[+] 并发原子性通过")


if __name__ == "__main__":
    test_gen_13057_payload()
    test_on_polyhedron_pass_ctx_none()
    test_on_polyhedron_pass_advances_cond423()
    test_gen_cert_existing_check_verifies_leaf()
    test_gen_cert_concurrent_atomicity()
    print("ALL PASSED")
