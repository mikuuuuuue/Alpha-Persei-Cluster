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
import re
import sys
from collections import OrderedDict


def sort_key(fp):
    base = os.path.basename(fp)
    m = re.search(r"tcp_(\d+)", base)
    if m:
        return (0, int(m.group(1)), base)
    return (1, 0, base)


def main():
    if len(sys.argv) < 2:
        sys.exit("用法：python tools/make_scene_table.py <场景目录>")
    scene_dir = sys.argv[1]
    files = sorted(glob.glob(os.path.join(scene_dir, "rebuilt", "*.jsonl")), key=sort_key)
    if not files:
        sys.exit(f"未找到 {scene_dir}/rebuilt/*.jsonl — 先运行 tools/rebuild_frames.py")
    stats = OrderedDict()   # (type, dir, cmd) -> [帧数, payload字节]
    all_records = []        # 收集所有记录用于全局时序排序
    for file_idx, fp in enumerate(files):
        with open(fp, encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
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
                ts = r.get("ts")
                all_records.append({
                    "ts": float(ts) if ts is not None else None,
                    "file_idx": file_idx,
                    "line_idx": line_idx,
                    "key": key,
                })
    sorted_records = sorted(
        all_records,
        key=lambda item: (
            0 if item["ts"] is not None else 1,
            item["ts"] if item["ts"] is not None else 0.0,
            item["file_idx"],
            item["line_idx"],
        )
    )
    order = []              # 跨文件全局按 ts 排序后的首次出现顺序
    seen = set()
    for item in sorted_records:
        k = item["key"]
        if k not in seen:
            seen.add(k)
            order.append(k)
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
