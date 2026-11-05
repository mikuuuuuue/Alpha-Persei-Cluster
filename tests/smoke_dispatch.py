# -*- coding: utf-8 -*-
"""tests/smoke_dispatch.py — 全量操作带参数驱动与冻结基线对比。

使用临时数据库副本，核对操作集合并记录调度返回结构和未捕获异常。
业务成功回执与关键状态变化由针对性测试验证。
基线机制：首次 `--update-baseline` 冻结每操作状态（ok/reply/frames/sc 前缀 + 失败集合）；
此后常规运行与基线 diff，**新增失败 = 退出码 1**；行为变化（非失败）打印清单供人工确认后更新基线。
"""
import glob
import json
import os
import shutil
import sys
import tempfile
import time

os.environ['ACCOUNT_DB_PATH'] = ':memory:'

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_DIR not in sys.path:
    sys.path.insert(0, V5_DIR)

from account_db import AccountDB         # noqa: E402
import core as core_mod                  # noqa: E402
import generator as _gen                 # noqa: E402
from codec import encode as _enc, decode as _dec  # noqa: E402
import logger                            # noqa: E402
# 导入领域服务以注册全部业务操作。
import backhome_service                  # noqa: E402
import peripheral_service                # noqa: E402
import achievement_service               # noqa: E402
import minigame_service                  # noqa: E402
import autochess_service                 # noqa: E402
import periodic_gift_service             # noqa: E402
import recharge_service                  # noqa: E402

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASELINE_PATH = os.path.join(TESTS_DIR, "smoke_baseline.json")
PARAMS_PATH = os.path.join(TESTS_DIR, "min_params.json")
DEFAULT_UID = 999999


def load_params():
    if os.path.exists(PARAMS_PATH):
        with open(PARAMS_PATH, encoding="utf-8") as f:
            return json.load(f)["params"]
    print("[!] tests/min_params.json 缺失（未生成或无抓包），回落空参数驱动")
    return {}


def make_core(workdir):
    src_db = os.path.join(V5_DIR, "account.db")
    tmp_db = os.path.join(workdir, "account.db")
    if os.path.isfile(src_db):
        shutil.copy2(src_db, tmp_db)
        for side in ("-wal", "-shm"):
            for f in glob.glob(src_db + side):
                shutil.copy2(f, tmp_db + side)
    db = AccountDB(tmp_db)
    return core_mod.Core(db=db, generator=_gen, codec_encode=_enc,
                         codec_decode=_dec, log=logger.log)


def sweep(core, params):
    results, fails = {}, {}
    for cmd in sorted(core_mod.OPERATIONS.keys()):
        p = params.get("cs_%d" % cmd, {})
        try:
            req = core_mod.CoreRequest(cmd=cmd,
                                       payload=json.dumps(p).encode("utf-8"),
                                       uid=DEFAULT_UID)
            resp = core.dispatch(req)
            sc_list = []
            for fr in resp.frames:
                sc_list.append(fr["sc"] if isinstance(fr, dict)
                                else getattr(fr, "cmd", None))
            results[cmd] = {"ok": True, "reply": bool(resp.reply),
                            "frames": len(resp.frames), "sc": sc_list[:6]}
        except Exception as e:
            results[cmd] = {"ok": False, "reply": False, "frames": 0, "sc": []}
            fails[cmd] = repr(e)[:200]
    return results, fails


def main():
    update = "--update-baseline" in sys.argv
    params = load_params()
    with tempfile.TemporaryDirectory(prefix="m2_smoke_") as workdir:
        core = make_core(workdir)
        t0 = time.time()
        results, fails = sweep(core, params)
        elapsed = time.time() - t0
        core.db.close()  # win32：SQLite 连接未关闭时 TemporaryDirectory 清理报 WinError 32

    covered = sum(bool(params.get("cs_%d" % cmd)) for cmd in results)
    print("[*] %d 操作驱动完成（有效参数覆盖 %d cmd），耗时 %.1fs" % (len(results), covered, elapsed))
    print("[*] 失败（未捕获异常）: %d 项" % len(fails))

    if update or not os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump({"frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "results": results, "fails": fails},
                      f, ensure_ascii=False, indent=1, sort_keys=True)
        print("[+] 基线已冻结 -> %s（失败 %d 项为已知集）" % (BASELINE_PATH, len(fails)))
        return 0

    with open(BASELINE_PATH, encoding="utf-8") as f:
        base = json.load(f)
    expected_commands = {int(cmd) for cmd in base['results']}
    actual_commands = set(results)
    assert actual_commands == expected_commands, (
        '操作集合与基线不符：新增=%s，缺失=%s' %
        (sorted(actual_commands - expected_commands), sorted(expected_commands - actual_commands)))
    base_fails = {int(k): v for k, v in base["fails"].items()}
    new_fails = sorted(set(fails) - set(base_fails))
    fixed_fails = sorted(set(base_fails) - set(fails))
    changed = [c for c in results
               if results[c] != base["results"].get(str(c)) and int(c) not in new_fails]

    for c in new_fails:
        print("[-] 新增失败 cs_%s: %s" % (c, fails[c]))
    for c in fixed_fails:
        print("[+] 已消失败 cs_%s（原: %s）" % (c, base_fails[int(c)]))
    print("[*] 行为变化（非失败）: %d 项%s" %
          (len(changed), "（人工确认后 --update-baseline 收录）" if changed else ""))

    if new_fails:
        print("[-] SMOKE FAIL：新增失败 %d 项" % len(new_fails))
        return 1
    print("[+] SMOKE PASS：零新增失败（已知失败集 %d 项不变或缩小）" % len(base_fails))
    return 0


if __name__ == "__main__":
    sys.exit(main())
