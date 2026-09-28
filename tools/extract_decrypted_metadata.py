#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/extract_decrypted_metadata.py — 从全内存转储提取运行时解密的 il2cpp global-metadata

适用:磁盘上的 global-metadata.dat 被加密(魔数≠0xFAB11BAF),但进程内存中存在
Il2Cpp runtime 解密后的完整 metadata 块。扫描转储内存段,定位
{sanity=0xFAB11BAF, version∈[24,31]} 且头部字段单调合理的候选,
按连续段拼出 ~25MB blob 落盘,供 Il2CppDumper 使用。

用法: python extract_decrypted_metadata.py <dump.dmp> -o <out.dat>
"""
import sys
import argparse

MAGIC = 0xFAB11BAF


def header_plausible(b):
    """Il2CppGlobalMetadataHeader 前 12 字段: sanity,version,(offset,count)×5 应单调递增。"""
    if len(b) < 12 * 8 + 8:
        return False
    vals = [int.from_bytes(b[i:i + 4], "little") for i in range(8, 8 + 12 * 8, 4)]
    offs = vals[0::2]
    return all(x < y for x, y in zip(offs, offs[1:])) and offs[0] == 0x100 or offs[0] > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--maxsize", type=int, default=26 * 1024 * 1024)
    args = ap.parse_args()

    from minidump.minidumpfile import MinidumpFile
    mf = MinidumpFile.parse(args.dump)
    reader = mf.get_reader()
    segs = sorted(mf.memory_segments_64.memory_segments,
                  key=lambda s: s.start_virtual_address)

    print(f"段数 {len(segs)}, 逐段扫描魔数 {hex(MAGIC)} ...")
    hits = []
    for i, s in enumerate(segs):
        if s.size > 64 * 1024 * 1024:
            step = s.size // (32 * 1024 * 1024) + 1  # 超大段分块
        else:
            step = 1
        for j in range(step):
            lo = j * (s.size // step)
            hi = min(s.size, (j + 1) * (s.size // step) + 64) if step > 1 else s.size
            base = s.start_virtual_address
            try:
                buf = reader.read(base + lo, hi - lo)
            except Exception:
                continue
            off = buf.find(MAGIC.to_bytes(4, "little"))
            while off != -1:
                va = base + lo + off
                try:
                    head = reader.read(va, 104)
                except Exception:
                    head = b""
                ver = int.from_bytes(head[4:8], "little")
                if 24 <= ver <= 31 and header_plausible(head):
                    hits.append((va, ver))
                off = buf.find(MAGIC.to_bytes(4, "little"), off + 1)
    print(f"合理候选 {len(hits)} 个: {[(hex(a), v) for a, v in hits[:10]]}")
    if not hits:
        sys.exit("未找到解密 metadata 候选")

    va, ver = hits[0]
    # 从候选地址起,按连续映射内存拼接 maxsize 字节
    out = bytearray()
    addr = va
    remaining = args.maxsize
    while remaining > 0:
        seg = next((s for s in segs
                    if s.start_virtual_address <= addr < s.start_virtual_address + s.size), None)
        if not seg:
            break
        take = min(remaining, seg.start_virtual_address + seg.size - addr)
        try:
            out += reader.read(addr, take)
        except Exception:
            break
        remaining -= take
        addr += take
    with open(args.out, "wb") as f:
        f.write(out)
    print(f"已写出 {len(out)} 字节 → {args.out} (候选 VA {hex(va)}, metadata version {ver})")


if __name__ == "__main__":
    main()
