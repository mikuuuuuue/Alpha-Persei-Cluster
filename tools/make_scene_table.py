#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/make_scene_table.py — 从 <场景目录>/rebuilt/*.jsonl 生成《场景-协议对照表》片段

用法：
  python tools/make_scene_table.py <场景目录> >> <CAPTURES>/场景-协议对照表.md
依赖：无（纯标准库）。输入为 tools/rebuild_frames.py 产出的 JSONL。
"""
import glob
import json
import os
import sys
from collections import OrderedDict


def main():
    if len(sys.argv) < 2:
        sys.exit("用法：python tools/make_scene_table.py <场景目录>")
    scene_dir = sys.argv[1]
    files = sorted(glob.glob(os.path.join(scene_dir, "rebuilt", "*.jsonl")))
    if not files:
        sys.exit(f"未找到 {scene_dir}/rebuilt/*.jsonl — 先运行 tools/rebuild_frames.py")
    stats = OrderedDict()   # (type, dir, cmd) -> [帧数, payload字节]
    order = []              # 首次出现顺序
    for fp in files:
        for line in open(fp, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("error"):
                continue
            if r.get("type") == "udp":
                key = ("udp", r.get("dir"), r.get("port"))
            else:
                key = ("tcp", r.get("dir"), r.get("cmd"))
            st = stats.setdefault(key, [0, 0])
            st[0] += 1
            st[1] += r.get("payload_len") or r.get("len") or 0
            if key not in order:
                order.append(key)
    scene = os.path.basename(os.path.normpath(scene_dir))
    print(f"\n## {scene}\n")
    print("| 方向 | 消息 | 帧数 | payload 字节 |")
    print("|---|---|---|---|")
    for (t, d, cmd), (cnt, nb) in stats.items():
        name = "udp_6105(战斗)" if t == "udp" else f"{'cs' if d == 'up' else 'sc'}_{cmd}"
        print(f"| {'↑' if d == 'up' else '↓'} | {name} | {cnt} | {nb} |")
    seq = " → ".join(
        f"{'cs' if d == 'up' else 'sc'}_{c}" if t == "tcp" else "udp_6105"
        for t, d, c in order)
    print(f"\n帧序列：{seq}\n")


if __name__ == "__main__":
    main()
