# -*- coding: utf-8 -*-
"""
minidump_stack_scan.py — 转储线程栈回溯扫描器（零 WinDbg 依赖）

用途（M1 Task 6 L1/L2）：从 Windows 用户态转储的线程栈内存中扫描"指向目标模块的
返回地址"，重建调用链（栈回溯）。当 RIP 停在 ntdll 等待/自旋、符号栈不可用时，
这是唯一纯 Python 可行的路径。

原理：
- x64 线程栈按 8 字节对齐，返回地址以 8 字节值出现；
- 扫描线程栈区间内的每个 8 字节值，凡落在 [模块基址, 基址+大小) 即判定为候选返回地址；
- 按地址从低到高（= 由栈顶向栈底 = 由内层向外层调用）输出，即调用链。

用法：
  python minidump_stack_scan.py <dump> --module GameAssembly.dll [--tid 6208] [--top 5]
  python minidump_stack_scan.py <dump> --module GameAssembly.dll --all-threads

依赖：pip install minidump
"""
import argparse
import struct
import sys
from collections import Counter

try:
    from minidump.minidumpfile import MinidumpFile
except ImportError:
    sys.exit("需要 minidump 包：pip install minidump")


def load(mf):
    mods = sorted((m.baseaddress, m.size, m.name) for m in mf.modules.modules)
    return mods


def locate(mods, addr):
    for base, size, name in mods:
        if base <= addr < base + size:
            return name, addr - base
    return None, None


def _rsp_of(mf, thread):
    ctx = thread.ThreadContext
    mf.file_handle.seek(ctx.Rva)
    raw = mf.file_handle.read(ctx.DataSize)
    if ctx.DataSize >= 0x4D0:
        return struct.unpack_from("<Q", raw, 0x98)[0]
    return None


def iter_stack_mem(mf, thread, min_size=0x100, max_bytes=16 << 20):
    """产出该线程栈的可读内存块 (start, bytes)。

    三条来源合并：
    1. ThreadListStream 自带的 per-thread Stack 描述符（dumper 抓的栈顶片段）；
    2. MemoryListStream (32-bit) 中与 rsp 相关的段；
    3. Memory64ListStream (full dump 常见) 中与 rsp 相关的段。
    为免把整个地址空间读进内存，按 rsp 向高地址最多取 max_bytes。
    """
    regions = []
    st = getattr(thread, "Stack", None)
    if st is not None:
        size = getattr(st, "DataSize", 0)
        # Rva==0 表示该 Stack 描述符无内联数据（full dump 走 memory64 段）
        if size and size >= min_size and getattr(st, "Rva", 0):
            mf.file_handle.seek(st.Rva)
            regions.append((st.StartOfMemoryRange, mf.file_handle.read(size)))
    rsp = _rsp_of(mf, thread)
    for attr in ("memory_segments", "memory_segments_64"):
        mls = getattr(mf, attr, None)
        if mls is None:
            continue
        for seg in getattr(mls, "memory_segments", None) or []:
            sv = seg.start_virtual_address
            if rsp is not None and sv <= rsp < sv + seg.size:
                take = min(seg.size - (rsp - sv), max_bytes)
                mf.file_handle.seek(seg.start_file_address + (rsp - sv))
                regions.append((rsp, mf.file_handle.read(take)))
                break
    for r in regions:
        yield r


def scan_thread(mf, mods, thread, module_filter, max_frames=64):
    frames = []
    for start, data in iter_stack_mem(mf, thread):
        n = len(data) // 8
        vals = struct.unpack_from("<%dQ" % n, data)
        for i, v in enumerate(vals):
            if v == 0:
                continue
            name, rva = locate(mods, v)
            if name is None:
                continue
            if module_filter and module_filter.lower() not in name.lower():
                continue
            # 跳过明显的非代码（模块基址本身）与重复相邻
            if rva == 0:
                continue
            addr = start + i * 8
            if frames and frames[-1][1] == addr - 8 and frames[-1][2] == rva:
                continue
            frames.append((addr, addr, rva, name))
            if len(frames) >= max_frames:
                return frames
    return frames


def main():
    ap = argparse.ArgumentParser(description="转储线程栈回溯扫描器")
    ap.add_argument("dump")
    ap.add_argument("--module", default="GameAssembly.dll")
    ap.add_argument("--tid", type=int, default=None, help="只扫描该线程")
    ap.add_argument("--all-threads", action="store_true")
    ap.add_argument("--top", type=int, default=8, help="只显示前 N 个候选线程")
    args = ap.parse_args()

    mf = MinidumpFile.parse(args.dump)
    mods = load(mf)
    ga = [m for m in mods if args.module.lower() in m[2].lower()]
    if ga:
        print(f"目标模块 {args.module}: base={hex(ga[0][0])} size={hex(ga[0][1])}")
    else:
        print(f"[!] 未找到模块 {args.module}")

    results = []
    for t in mf.threads.threads:
        if args.tid is not None and t.ThreadId != args.tid:
            continue
        frames = scan_thread(mf, mods, t, args.module)
        if frames:
            results.append((t.ThreadId, frames))

    results.sort(key=lambda x: -len(x[1]))
    print(f"\n有 {len(results)} 个线程栈中存在指向 {args.module} 的返回地址\n")
    shown = results if args.all_threads else results[:args.top]
    for tid, frames in shown:
        print(f"=== TID {tid}  ({len(frames)} 帧) ===")
        for addr, _, rva, name in frames:
            print(f"    {hex(rva)}   (slot {hex(addr)})")
        print()

    # RVA 频次总览
    c = Counter(rva for _, frames in results for _, _, rva, _ in frames)
    print("--- 全线程 RVA 频次 top 20 ---")
    for rva, n in c.most_common(20):
        print(f"    n={n:4d}  RVA={hex(rva)}")


if __name__ == "__main__":
    main()
