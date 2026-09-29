#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gen_min_params.py — 扫描抓包上行帧，生成 397 操作的最小合法参数集（M2.2 / U12）

用法：
  python tools/gen_min_params.py                 # 默认扫 $REPO/Alpha-Persei-Captures
  python tools/gen_min_params.py --selftest      # 黄金断言后退出（不写盘）
  python tools/gen_min_params.py -o <path.json>  # 指定输出
"""
import argparse
import glob
import json
import os
import sys
import zlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_DIR not in sys.path:
    sys.path.insert(0, V5_DIR)

from codec import decode as _dec  # noqa: E402


def up_frames(cap_root):
    for p in sorted(glob.glob(os.path.join(cap_root, "*", "rebuilt", "*_up_*.jsonl"))):
        scene = os.path.basename(os.path.dirname(os.path.dirname(p)))
        for ln in open(p, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            yield scene, os.path.basename(p), json.loads(ln)


def payload_bytes(fr):
    raw = bytes.fromhex(fr["payload_hex"])
    if fr.get("compressed"):
        raw = zlib.decompress(raw)
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", default=os.path.join(REPO_ROOT, "Alpha-Persei-Captures"))
    ap.add_argument("-o", default=os.path.join(REPO_ROOT, "tests", "min_params.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    best = {}   # cs_name -> {"param": dict, "len": int, "src": str}
    bad = 0     # 解码失败/无定义帧计数
    for scene, fname, fr in up_frames(args.cap):
        if fr.get("dir") != "up" or not fr.get("cmd"):
            continue
        name = "cs_%d" % fr["cmd"]
        try:
            raw = payload_bytes(fr)
            param = _dec(raw, name)
            if not isinstance(param, dict) or not param:
                raise ValueError("空参数")
        except Exception:
            bad += 1
            continue
        if name not in best or len(raw) < best[name]["len"]:
            best[name] = {"param": param, "len": len(raw), "src": "%s/%s" % (scene, fname)}

    print("[*] 上行 cmd 去重: %d 种；解码失败/空参数帧: %d" % (len(best), bad))
    if args.selftest:
        g = best.get("cs_16010")
        assert g and set(g["param"]) >= {"type", "pool", "cost"}, \
            "黄金样例 cs_16010 应含 type/pool/cost，实际 %r" % (g and g["param"])
        assert len(best) >= 60, "覆盖下限 60 种（2026-09-29 实测 71），实际 %d" % len(best)
        print("[+] selftest 通过（cs_16010 黄金样例 + 覆盖量 %d ≥ 60）" % len(best))
        return 0

    out = {
        "generated_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(best),
        "params": {k: v["param"] for k, v in sorted(best.items())},
        "sources": {k: v["src"] for k, v in sorted(best.items())},
    }
    with open(args.o, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("[+] 写出 %s（%d cmd）" % (args.o, len(best)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
