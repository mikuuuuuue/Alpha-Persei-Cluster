#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/extract_321_proto_increment.py — 从 321 客户端脚本包补提取协议 schema（M1.1 增量工序，2026-09-29）

背景（M1 整改 P1-1，源自《M1-修复真实性排查报告.md》§二）：
  229 基线 91 个 *_pb.lua 之外，321 客户端新增 p91_pb.lua 且 p84_pb.lua 有增量
  （sc_84331/sc_84332/sc_84333/sc_91001 等）。此前"63 协议无源可补"的裁定不成立：
  321 的 scripts64.ys 就在本机 StreamingAssets 内（UnityFS 打包，.ys 前有 10 字节填充）。

工序（全部复用既有管线）：
  1. UnityPy 读 321 scripts64.ys（TextAsset），倒出 *_pb.lua 字节（LuaJIT 2.0 rawdump）
  2. LJD 反编译为 .lua 源（同 解包/Lua源码库/Lua源码 工序）
  3. tools/extract_proto_schema.py 提取为 schema json
  4. 与 v5_server/lua_proto_messages.json 求差集，仅合入基线没有的消息（不触碰已验证的
     3040 条基线），先备份原文件

用法：
  python tools/extract_321_proto_increment.py                    # 默认 321 客户端路径
  python tools/extract_321_proto_increment.py --bundle <.ys>     # 指定脚本包
  python tools/extract_321_proto_increment.py --dry-run          # 只看差集不写盘

产物自检口径（2026-09-29 实测）：
  合入 21 条（sc_84331/sc_84333/sc_91001/cs_84332 + 嵌套 rec + 91001 家族），
  3061 条总量；抓包 1915 有载荷帧 roundtrip 1915/1915 = 100.00%（修复前 8 帧缺失定义）。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(REPO_ROOT, "v5_server", "lua_proto_messages.json")
EXTRACTOR = os.path.join(REPO_ROOT, "tools", "extract_proto_schema.py")
LJD_MAIN = r"C:\Users\<user>\Desktop\解包\tools\LJD\main.py"
DEFAULT_BUNDLE = (r"C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili"
                  r"\AetherGazer_Bili_Data\StreamingAssets\Windows\f\9"
                  r"\f9468cd00564c3c98e4f819210760be1.ys")
# task11 差分登记（reports/20260925_全量收尾/goal_run/task11_new_assets_321.json）：
# scripts64 321 档 md5 = f9468cd00564c3c98e4f819210760be1, size = 35812429


def dump_textassets(bundle_path, out_dir):
    import UnityPy
    raw = open(bundle_path, "rb").read()
    off = raw.find(b"UnityFS")
    if off < 0:
        sys.exit("[ERR] 未找到 UnityFS 头（不是脚本包?）: %s" % bundle_path)
    env = UnityPy.load(raw[off:])
    names = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if not d.m_Name.endswith("_pb.lua"):
            continue
        script = d.m_Script
        if isinstance(script, str):
            script = script.encode("utf-8", "surrogateescape")
        if not script.startswith(b"\x1bLJ"):
            continue  # 非 LuaJIT rawdump，跳过
        with open(os.path.join(out_dir, d.m_Name + ".bytes"), "wb") as f:
            f.write(script)
        names.append(d.m_Name)
    return sorted(names)


def decompile_ljd(work_dir):
    for fn in sorted(os.listdir(work_dir)):
        if not fn.endswith(".bytes"):
            continue
        src = os.path.join(work_dir, fn)
        dst = os.path.join(work_dir, fn[:-len(".bytes")])
        r = subprocess.run([sys.executable, LJD_MAIN, "-f", src, "-o", dst],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(dst):
            print("[WARN] LJD 反编译失败 %s: %s" % (fn, r.stderr.strip()[:200]))


def load_messages(path):
    data = json.load(open(path, encoding="utf-8"))
    return data, data[list(data.keys())[0]]


def main():
    global LJD_MAIN
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bundle", default=DEFAULT_BUNDLE, help="321 客户端 scripts .ys 路径")
    ap.add_argument("--ljd", default=LJD_MAIN, help="LJD main.py 路径")
    ap.add_argument("--dry-run", action="store_true", help="只报告差集，不写 schema")
    args = ap.parse_args()
    LJD_MAIN = args.ljd

    if not os.path.isfile(args.bundle):
        sys.exit("[ERR] 脚本包不存在: %s（客户端未装或路径变更，用 --bundle 指定）" % args.bundle)
    if not os.path.isfile(SCHEMA_PATH):
        sys.exit("[ERR] 基线 schema 不存在: %s" % SCHEMA_PATH)

    work = tempfile.mkdtemp(prefix="proto321_")
    try:
        pbs = dump_textassets(args.bundle, work)
        print("[1/4] 倒出 %d 个 *_pb.lua（LuaJIT rawdump）" % len(pbs))
        decompile_ljd(work)
        luas = [f for f in os.listdir(work) if f.endswith(".lua")]
        if not luas:
            sys.exit("[ERR] 反编译产物为空，检查 LJD 路径")
        print("[2/4] LJD 反编译 %d 个 .lua" % len(luas))

        part = os.path.join(work, "partial.json")
        r = subprocess.run([sys.executable, EXTRACTOR, work, "-o", part],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("[ERR] 提取器失败:\n%s" % (r.stdout + r.stderr)[-500:])
        print("[3/4] 增量提取完成")

        _, base_msgs = load_messages(SCHEMA_PATH)
        _, part_msgs = load_messages(part)
        base_names = {m["name"] for m in base_msgs}
        added = [m for m in part_msgs if m["name"] not in base_names]
        clash = {m["name"] for m in part_msgs} & base_names
        print("    增量消息 %d 条，其中基线已有（跳过不动）%d 条，新增 %d 条："
              % (len(part_msgs), len(clash), len(added)))
        for m in added:
            print("      + %s (fields=%d)" % (m["name"], len(m.get("fields") or [])))

        if args.dry_run or not added:
            print("[4/4] dry-run/无新增，未写盘")
            return
        bak = SCHEMA_PATH + ".bak"
        shutil.copy(SCHEMA_PATH, bak)
        data, _ = load_messages(SCHEMA_PATH)
        data[list(data.keys())[0]].extend(added)
        with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("[4/4] 已合入 %d 条 → %s（备份 %s；总量 %d）"
              % (len(added), SCHEMA_PATH, bak, len(data[list(data.keys())[0]])))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
