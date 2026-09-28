# -*- coding: utf-8 -*-
"""
minidump_spin_analyzer.py — 用户态转储"自旋线程"定位器（零 WinDbg 依赖）

用途（M1 Task 6 L1）：给定进程的 Windows 用户态转储（rundll32 comsvcs.dll,MiniDump），
定位"忙循环/自旋"线程并给出其 RIP 在目标模块内的 RVA，供 L2 il2cpp 符号化对照。

原理：
- 忙循环线程的 RIP 会持续落在同一小段地址（同一函数或紧密循环体内）；
- 单份转储只能给出快照；对同一进程间隔抓取多份转储，取"多份中 RIP 反复出现在同一
  模块同一小窗口"的线程 → 即为自旋线程（锁等待线程的 RIP 会停在 wait 系统调用附近，
  且常伴随栈回溯可读；两者可区分）。

用法：
  python minidump_spin_analyzer.py <dump1> [dump2 ...] [--module GameAssembly.dll]
  python minidump_spin_analyzer.py <dump> --threads        # 打印全部线程 RIP
  python minidump_spin_analyzer.py <dump> --stack <tid>    # 用转储内存扫描回溯某线程栈

依赖：pip install minidump（纯 Python）
注意：comsvcs.dll 生成的转储属 SYSTEM 所有，需先 `icacls <dump> /grant <user>:F`。
"""
import argparse
import struct
import sys
from collections import Counter, defaultdict

try:
    from minidump.minidumpfile import MinidumpFile
except ImportError:
    sys.exit("需要 minidump 包：pip install minidump")

# AMD64 CONTEXT 关键偏移（CONTEXT_AMD64）
AMD64_RIP = 0xF8
AMD64_RSP = 0x98
AMD64_RBP = 0xA0
# x86 (WOW64 场景) CONTEXT 偏移
X86_EIP = 0xB8
X86_ESP = 0xC4
X86_EBP = 0xB4


def _read_ctx(mf, thread):
    """返回 (rip, rsp, rbp, is_64)。"""
    ctx = thread.ThreadContext
    mf.file_handle.seek(ctx.Rva)
    raw = mf.file_handle.read(ctx.DataSize)
    # DataSize==0x4d0 → CONTEXT_AMD64; 0x2cc → CONTEXT_i386
    if ctx.DataSize >= 0x4D0:
        rip = struct.unpack_from("<Q", raw, AMD64_RIP)[0]
        rsp = struct.unpack_from("<Q", raw, AMD64_RSP)[0]
        rbp = struct.unpack_from("<Q", raw, AMD64_RBP)[0]
        return rip, rsp, rbp, True
    if ctx.DataSize >= 0x2CC:
        eip = struct.unpack_from("<I", raw, X86_EIP)[0]
        esp = struct.unpack_from("<I", raw, X86_ESP)[0]
        ebp = struct.unpack_from("<I", raw, X86_EBP)[0]
        return eip, esp, ebp, False
    return None, None, None, None


def _modules(mf):
    mods = []
    for m in mf.modules.modules:
        mods.append((m.baseaddress, m.size, m.name))
    mods.sort()
    return mods


def _locate(mods, addr):
    for base, size, name in mods:
        if base <= addr < base + size:
            return name, addr - base
    return None, None


def analyze(dump_paths, module_filter=None, verbose=False):
    per_dump = []
    mods_ref = None
    for p in dump_paths:
        mf = MinidumpFile.parse(p)
        mods = _modules(mf)
        if mods_ref is None:
            mods_ref = mods
        rows = []
        for t in mf.threads.threads:
            rip, rsp, rbp, is64 = _read_ctx(mf, t)
            if rip is None:
                continue
            mod, rva = _locate(mods, rip)
            rows.append({
                "tid": t.ThreadId, "rip": rip, "rsp": rsp, "rbp": rbp,
                "mod": mod, "rva": rva,
            })
        per_dump.append({"path": p, "rows": rows})
        mf.close() if hasattr(mf, "close") else None

    print("=" * 78)
    print(f"转储数: {len(per_dump)}  模块数: {len(mods_ref)}")
    for d in per_dump:
        print(f"  - {d['path']}  线程数={len(d['rows'])}")

    # 1) 每个转储内，按 (模块,RVA 4KB 页) 聚合，找出现次数最多的位置
    print("\n--- 各转储内 RIP 热点（按模块+RVA页聚合，取 top 8）---")
    for d in per_dump:
        c = Counter()
        for r in d["rows"]:
            key = (r["mod"], (r["rva"] or 0) & ~0xFFF)
            c[key] += 1
        print(f"\n[{d['path']}]")
        for (mod, page), n in c.most_common(8):
            print(f"    n={n:3d}  {mod}  page_rva={hex(page)}")

    # 2) 跨转储：同一线程 ID 的 RIP 是否稳定落在同一模块同一小窗口
    print("\n--- 跨转储稳定性（同 TID 的 RIP 模块+RVA 窗口）---")
    by_tid = defaultdict(list)
    for d in per_dump:
        for r in d["rows"]:
            by_tid[r["tid"]].append(r)

    def _filter_hit(r):
        if module_filter and (not r["mod"] or module_filter.lower() not in r["mod"].lower()):
            return False
        return True

    candidates = []
    for tid, rs in by_tid.items():
        if len(rs) < len(per_dump):
            continue  # 该 TID 未在每份转储出现
        if not all(_filter_hit(r) for r in rs):
            continue
        rvas = [r["rva"] for r in rs]
        if any(v is None for v in rvas):
            continue
        span = max(rvas) - min(rvas)
        candidates.append((span, tid, rs, rvas))
    candidates.sort(key=lambda x: x[0])
    if not candidates:
        print("  (无跨转储稳定候选；放宽 --module 或增加转储数)")
    for span, tid, rs, rvas in candidates[:12]:
        print(f"  TID={tid}  span={hex(span)}  mod={rs[0]['mod']}")
        for r in rs:
            print(f"      RIP={hex(r['rip'])}  RVA={hex(r['rva'])}  RSP={hex(r['rsp'])}")

    # 3) 全部线程明细
    if verbose:
        print("\n--- 全部线程 RIP 明细（首份转储）---")
        for r in per_dump[0]["rows"]:
            print(f"  TID={r['tid']:>7}  RIP={hex(r['rip'])}  "
                  f"{r['mod']}  RVA={hex(r['rva']) if r['rva'] is not None else 'n/a'}")
    return per_dump


def main():
    ap = argparse.ArgumentParser(description="用户态转储自旋线程定位器")
    ap.add_argument("dumps", nargs="+", help="转储文件路径（可多份）")
    ap.add_argument("--module", default=None,
                    help="只关注 RIP 落在该模块内的线程，如 GameAssembly.dll")
    ap.add_argument("--threads", action="store_true", help="打印全部线程 RIP 明细")
    args = ap.parse_args()
    analyze(args.dumps, module_filter=args.module, verbose=args.threads)


if __name__ == "__main__":
    main()
