# -*- coding: utf-8 -*-
"""
live_rip_sampler.py — 对运行中进程做高频只读线程 RIP 采样（零安装、零注入）

用途（M1 Task 6 L1）：当进程"自旋"（CPU 持续爬升）而用户态转储恰好在 syscall 等待点
采样不到热点代码时，用 GetThreadContext 对全部线程做高频（~1ms 级）RIP 采样，
按 (模块, RVA 页/精确 RVA) 聚合，定位真正在被执行的函数 RVA。

只读边界：仅 OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION) + GetThreadContext，
不挂起、不修改、不注入、不改变任何行为。

用法：
  python live_rip_sampler.py --pid 6956 --seconds 4 [--module GameAssembly.dll] [--top 30]
  python live_rip_sampler.py --pid 6956 --seconds 4 --thread 18972   # 只采某线程

依赖：无（纯标准库 ctypes）
"""
import argparse
import ctypes
import struct
import sys
import time
from collections import Counter

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040
TH32CS_SNAPTHREAD = 0x00000004
CONTEXT_AMD64 = 0x00100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x00000001
CONTEXT_FULL = CONTEXT_AMD64 | 0x00000001 | 0x00000002 | 0x00000004


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ThreadID", ctypes.c_ulong),
        ("th32OwnerProcessID", ctypes.c_ulong),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
    ]


class M128A(ctypes.Structure):
    _fields_ = [("Low", ctypes.c_uint64), ("High", ctypes.c_int64)]


class CONTEXT64(ctypes.Structure):
    _fields_ = [
        ("P1Home", ctypes.c_uint64), ("P2Home", ctypes.c_uint64),
        ("P3Home", ctypes.c_uint64), ("P4Home", ctypes.c_uint64),
        ("P5Home", ctypes.c_uint64), ("P6Home", ctypes.c_uint64),
        ("ContextFlags", ctypes.c_uint32), ("MxCsr", ctypes.c_uint32),
        ("SegCs", ctypes.c_uint16), ("SegDs", ctypes.c_uint16),
        ("SegEs", ctypes.c_uint16), ("SegFs", ctypes.c_uint16),
        ("SegGs", ctypes.c_uint16), ("SegSs", ctypes.c_uint16),
        ("EFlags", ctypes.c_uint32),
        ("Dr0", ctypes.c_uint64), ("Dr1", ctypes.c_uint64),
        ("Dr2", ctypes.c_uint64), ("Dr3", ctypes.c_uint64),
        ("Dr6", ctypes.c_uint64), ("Dr7", ctypes.c_uint64),
        ("Rax", ctypes.c_uint64), ("Rcx", ctypes.c_uint64),
        ("Rdx", ctypes.c_uint64), ("Rbx", ctypes.c_uint64),
        ("Rsp", ctypes.c_uint64), ("Rbp", ctypes.c_uint64),
        ("Rsi", ctypes.c_uint64), ("Rdi", ctypes.c_uint64),
        ("R8", ctypes.c_uint64), ("R9", ctypes.c_uint64),
        ("R10", ctypes.c_uint64), ("R11", ctypes.c_uint64),
        ("R12", ctypes.c_uint64), ("R13", ctypes.c_uint64),
        ("R14", ctypes.c_uint64), ("R15", ctypes.c_uint64),
        ("Rip", ctypes.c_uint64),
        ("FltSave", ctypes.c_byte * 512),
        ("VectorRegister", M128A * 26),
        ("VectorControl", ctypes.c_uint64),
        ("DebugControl", ctypes.c_uint64),
        ("LastBranchToRip", ctypes.c_uint64),
        ("LastBranchFromRip", ctypes.c_uint64),
        ("LastExceptionToRip", ctypes.c_uint64),
        ("LastExceptionFromRip", ctypes.c_uint64),
    ]


def enum_threads(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == -1:
        raise ctypes.WinError(ctypes.get_last_error())
    te = THREADENTRY32()
    te.dwSize = ctypes.sizeof(THREADENTRY32)
    out = []
    ok = k32.Thread32First(snap, ctypes.byref(te))
    while ok:
        if te.th32OwnerProcessID == pid:
            out.append(te.th32ThreadID)
        ok = k32.Thread32Next(snap, ctypes.byref(te))
    k32.CloseHandle(snap)
    return out


def sample_rip(tid):
    h = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
    if not h:
        return None
    try:
        ctx = CONTEXT64()
        ctx.ContextFlags = CONTEXT_CONTROL
        if not k32.GetThreadContext(h, ctypes.byref(ctx)):
            return None
        return ctx.Rip
    finally:
        k32.CloseHandle(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--thread", type=int, default=None)
    ap.add_argument("--module", default=None)
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    tids = [args.thread] if args.thread else enum_threads(args.pid)
    print(f"PID {args.pid}: {len(tids)} 线程；采样 {args.seconds}s")

    exact = Counter()     # (tid, rip)
    per_tid = Counter()   # tid -> samples
    deadline = time.time() + args.seconds
    nsamples = 0
    while time.time() < deadline:
        for tid in tids:
            rip = sample_rip(tid)
            if rip:
                exact[(tid, rip)] += 1
                per_tid[tid] += 1
                nsamples += 1
    print(f"总采样 {nsamples} 次")

    # 按 tid 汇总最热 RIP
    hot = {}
    for (tid, rip), n in exact.items():
        hot.setdefault(tid, []).append((n, rip))
    ranked = []
    for tid, lst in hot.items():
        lst.sort(reverse=True)
        top_n, top_rip = lst[0]
        ranked.append((per_tid[tid], tid, top_n, top_rip, len(lst)))
    ranked.sort(reverse=True)

    print("\n--- 每线程采样数 / 最热 RIP ---")
    for total, tid, top_n, top_rip, distinct in ranked[:args.top]:
        print(f"  TID {tid:>7}  采样={total:5d}  最热RIP={hex(top_rip)} (x{top_n})  不同RIP={distinct}")
        for n, rip in sorted(hot[tid], reverse=True)[:4]:
            print(f"        {hex(rip)}  x{n}")


if __name__ == "__main__":
    main()
