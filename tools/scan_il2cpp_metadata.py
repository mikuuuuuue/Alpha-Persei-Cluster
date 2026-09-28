# -*- coding: utf-8 -*-
"""
scan_il2cpp_metadata.py — 在文件/进程转储中搜索 il2cpp 元数据魔数

用途（M1 Task 6 L2）：当 global-metadata.dat 被加密/魔改（魔数非 0xFAB11BAF）导致
AssetRipper/Cpp2IL 无法符号化时，运行时内存中通常仍存在"已解密"的元数据副本。
本脚本在内存转储中搜索魔数 0xFAB11BAF，定位解密后的元数据起始位置。

用法：
  python scan_il2cpp_metadata.py <file> [--magic fab11baf] [--context 64]
  python scan_il2cpp_metadata.py <file> --extract <out.dat> --at <hexoffset>

依赖：无（纯标准库）
"""
import argparse
import sys

MAGIC_LE = bytes.fromhex("af1bb1fa")  # 0xFAB11BAF little-endian
MAGIC_BE = bytes.fromhex("fab11baf")


def scan_file(path, magic, ctx=48, limit=50):
    hits = []
    with open(path, "rb") as f:
        prev_tail = b""
        off = 0
        CHUNK = 1 << 22
        while True:
            buf = f.read(CHUNK)
            if not buf:
                break
            data = prev_tail + buf
            base = off - len(prev_tail)
            i = 0
            while True:
                j = data.find(magic, i)
                if j < 0:
                    break
                abs_off = base + j
                s = max(0, j - ctx)
                e = min(len(data), j + ctx)
                hits.append((abs_off, data[s:e]))
                i = j + 1
                if len(hits) >= limit:
                    return hits
            prev_tail = data[-4:]
            off += len(buf)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--magic", default="fab11baf", help="魔数 hex（默认 fab11baf）")
    ap.add_argument("--context", type=int, default=48)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--extract", default=None, help="从首个命中处导出 N 字节")
    ap.add_argument("--at", default=None, help="导出起始绝对偏移 hex")
    ap.add_argument("--extract-size", type=int, default=26000000)
    args = ap.parse_args()

    magic = bytes.fromhex(args.magic)
    print(f"文件: {args.file}")
    print(f"搜索魔数: {args.magic} (LE) / {bytes.fromhex(args.magic)[::-1].hex()} (BE)")
    hits = scan_file(args.file, magic, args.context, args.limit)
    print(f"命中 {len(hits)} 处")
    for off, ctxb in hits[:args.limit]:
        print(f"  offset={hex(off)}  ctx={ctxb.hex()}")

    if args.extract and hits:
        start = int(args.at, 16) if args.at else hits[0][0]
        with open(args.file, "rb") as f:
            f.seek(start)
            data = f.read(args.extract_size)
        with open(args.extract, "wb") as g:
            g.write(data)
        print(f"已导出 {len(data)} 字节: {args.extract} (from {hex(start)})")


if __name__ == "__main__":
    main()
