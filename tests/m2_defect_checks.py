# -*- coding: utf-8 -*-
"""tests/m2_defect_checks.py — M2 既有缺陷修复的单测集合（Task 2/3/5）

使用临时数据库副本或空测试库；证书测试使用临时目录，不修改真实存档和证书。
"""
import glob
import os
import shutil
import sys
import tempfile

os.environ['ACCOUNT_DB_PATH'] = ':memory:'

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_DIR not in sys.path:
    sys.path.insert(0, V5_DIR)


def _setup_temp_db():
    workdir = tempfile.mkdtemp(prefix="m2_defect_")
    src = os.path.join(V5_DIR, "account.db")
    dst = os.path.join(workdir, "account.db")
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        for side in ("-wal", "-shm"):
            for f in glob.glob(src + side):
                shutil.copy2(f, dst + side)
    from account_db import AccountDB
    return AccountDB(dst), workdir


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
    import core
    import operations
    import generator
    from codec import encode, decode
    from polyhedron_service import PolyhedronRunManager
    for command, acknowledgement, payload in ((18018, 18019, b'{}'),
                                              (18012, 18013, b'{"index":0}')):
        db, workdir = _setup_temp_db()
        try:
            uid = 888001
            db.execute("INSERT OR REPLACE INTO task_cfg (task_id, condition, need, task_type, additional_parameter) VALUES (100007, 423, 1, 3, '[]')")
            db.execute("INSERT OR REPLACE INTO task (uid, task_id, progress) VALUES (888001, 100007, 0)")
            db.upsert('polyhedron_hero', uid, {'hero_id': 1084}, keys=('uid', 'hero_id'))
            run = PolyhedronRunManager.start_run(uid, db, [1084], [], 1)
            if command == 18012:
                run.update(tier_id=3010, cleared_tiers=[3010])
                run['current_stage'].update(
                    save_point=2,
                    reward={'round': 0, 'item_list': [{'class': 6, 'params': [101701]}]},
                )
                PolyhedronRunManager.save_run(uid, db, run)
            server = core.Core(db=db, generator=generator, codec_encode=encode,
                               codec_decode=decode, log=lambda *a, **k: None)
            response = server.dispatch(core.CoreRequest(command, payload, uid=uid))
            rows = db.query('SELECT progress FROM task WHERE uid=? AND task_id=100007', (uid,))
            assert rows and int(rows[0]['progress']) >= 1, (command, rows)
            frames = {frame['sc']: frame['payload'] for frame in response.frames}
            assert decode(frames[acknowledgement], 'sc_%d' % acknowledgement).get('result', 0) == 0
            assert 28007 in frames, '多维变量结算必须将任务通知放入实际响应'
            progress = decode(frames[28007], 'sc_28007')['progress_list']
            assert any(item['id'] == 100007 and item['progress'] >= 1 for item in progress)
        finally:
            db.close()
            shutil.rmtree(workdir, ignore_errors=True)



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
        ca_path = os.path.join(td, 'sdk_ca.crt')
        with open(ca_path, 'rb') as source:
            original_root = source.read()
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
        assert gen_cert.generate_dual_layer_certs(output_dir=td, force=True, log=lambda *a, **k: None)
        with open(ca_path, 'rb') as source:
            assert source.read() == original_root, '强制续签叶子证书必须保留现有根证书'
    print("[+] 叶子验签检查通过")


def test_gen_cert_concurrent_atomicity():
    import threading
    import tempfile
    import gen_cert
    from unittest.mock import patch
    errs = []
    first_write = threading.Event()
    release = threading.Event()
    second_done = threading.Event()
    original_write = gen_cert._write_with_backup

    def paused_write(path, data):
        if threading.current_thread().name == 'first-cert' and os.path.basename(path) == 'sdk_ca.key':
            first_write.set()
            assert release.wait(10), '首个证书发布未获释放'
        return original_write(path, data)

    def worker(td, i):
        try:
            assert gen_cert.generate_dual_layer_certs(
                output_dir=td, log=lambda *a, **k: None)
        except Exception as e:
            errs.append("worker%d: %r" % (i, e))
        finally:
            if i == 1:
                second_done.set()

    with tempfile.TemporaryDirectory(prefix="m2_certc_") as td:
        ts = [threading.Thread(target=worker, args=(td, i), name=name)
              for i, name in enumerate(('first-cert', 'second-cert'))]
        with patch.object(gen_cert, '_write_with_backup', side_effect=paused_write):
            try:
                ts[0].start()
                assert first_write.wait(10), '首个生成过程未到达发布阶段'
                ts[1].start()
                overlapped = second_done.wait(2)
            finally:
                release.set()
                for thread in ts:
                    if thread.ident is not None:
                        thread.join(15)
        assert not any(thread.is_alive() for thread in ts), '生成线程未结束'
        assert not errs, "并发生成异常: %r" % errs
        assert not overlapped, '第二个生成过程越过了尚未完成的证书发布'
        assert gen_cert.inspect_certificate_files(td)['ready'], '并发生成后证书体系不配套'
        leftovers = [f for f in os.listdir(td) if f.endswith(".tmp")]
        assert not leftovers, "残留临时文件: %r" % leftovers
    print("[+] 并发原子性通过")


def test_gen_cert_failed_publish_preserves_existing():
    import gen_cert
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='m2_cert_failure_') as td:
        assert gen_cert.generate_dual_layer_certs(output_dir=td, log=lambda *a, **k: None)
        key_path = os.path.join(td, 'sdk_key.pem')
        with open(key_path, 'rb') as source:
            original_key = source.read()
        original_replace = os.replace

        def failed_replace(source, destination):
            if os.path.abspath(destination) == os.path.abspath(key_path):
                raise OSError('injected publication failure')
            return original_replace(source, destination)

        failed = False
        with patch.object(gen_cert.os, 'replace', side_effect=failed_replace):
            try:
                gen_cert.generate_dual_layer_certs(output_dir=td, force=True, log=lambda *a, **k: None)
            except OSError:
                failed = True
        assert failed, '证书发布失败必须返回给调用方'
        with open(key_path, 'rb') as source:
            assert source.read() == original_key, '发布失败不应覆盖原服务私钥'
        assert gen_cert.inspect_certificate_files(td)['ready']
        assert not [name for name in os.listdir(td) if name.endswith('.tmp')]


def test_gen_cert_process_atomicity():
    import json
    import subprocess
    import gen_cert
    with tempfile.TemporaryDirectory(prefix='m2_cert_process_') as td:
        command = [sys.executable, os.path.join(V5_DIR, 'gen_cert.py'), '--out', td]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        try:
            for process in processes:
                stdout, stderr = process.communicate(timeout=30)
                assert process.returncode == 0, (stdout, stderr)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        check = subprocess.run(command + ['--check', '--json'], capture_output=True, check=True)
        assert json.loads(check.stdout)['ready']
        assert gen_cert.inspect_certificate_files(td)['ready']


def test_chapter_move_ack_survives_merge():
    from codec import encode
    assert encode('sc_24065', {'result': 0}) == b'\x08\x00'


def test_defect_check_without_local_master():
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='m2_no_master_') as empty:
        with patch.dict(globals(), {'V5_DIR': empty}):
            try:
                db, workdir = _setup_temp_db()
            except FileNotFoundError as error:
                raise AssertionError('缺少本地存档时仍应创建临时测试数据库') from error
        try:
            assert db.query('PRAGMA integrity_check')[0]['integrity_check'] == 'ok'
            assert os.path.isfile(os.path.join(workdir, 'account.db'))
        finally:
            db.close()
            shutil.rmtree(workdir)


def test_smoke_without_local_master():
    import smoke_dispatch
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='m2_smoke_no_master_') as directory:
        with patch.dict(smoke_dispatch.__dict__, {'V5_DIR': os.path.join(directory, 'missing-master')}):
            try:
                server = smoke_dispatch.make_core(directory)
            except FileNotFoundError as error:
                raise AssertionError('缺少本地存档时冒烟检查仍应创建临时数据库') from error
        try:
            assert server.db.query('PRAGMA integrity_check')[0]['integrity_check'] == 'ok'
            assert os.path.isfile(os.path.join(directory, 'account.db'))
        finally:
            server.db.close()


if __name__ == "__main__":
    test_gen_13057_payload()
    test_on_polyhedron_pass_ctx_none()
    test_on_polyhedron_pass_advances_cond423()
    test_gen_cert_existing_check_verifies_leaf()
    test_gen_cert_concurrent_atomicity()
    test_gen_cert_failed_publish_preserves_existing()
    test_gen_cert_process_atomicity()
    test_chapter_move_ack_survives_merge()
    test_defect_check_without_local_master()
    test_smoke_without_local_master()
    print("ALL PASSED")
