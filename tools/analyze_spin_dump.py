#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/analyze_spin_dump.py — 用户态 minidump 自旋线程定位器(M1 Task 6 / Ruling 5)

纯标准库 + minidump-py。对转储提取:
  1. 模块表(GameAssembly.dll 基址)
  2. 每线程 RIP/RSP → 所属模块 + RVA(x64 CONTEXT: Rsp=0x98, Rip=0xF8)
  3. 栈内存扫描: [Rsp, stack_end) 内落入可执行模块地址 → 疑似返回地址链

多转储交叉: 同一线程 RIP/栈顶 RVA 稳定 → 忙循环; RIP 落在 ntdll 等待例程 → 锁等待。
用法: python analyze_spin_dump.py dump1.dmp [dump2.dmp ...] [--top N]
"""
import sys
import argparse
from collections import namedtuple

try:
    from minidump.minidumpfile import MinidumpFile
except ImportError:
    sys.exit("需要 minidump 包: pip install minidump")

CTX_RSP, CTX_RIP = 0x98, 0xF8
ModRange = namedtuple("ModRange", "name base end")


def load_modules(mf):
    mods = []
    for m in mf.modules.modules:
        base = m.baseaddress
        mods.append(ModRange(m.name or "?", base, base + m.size))
    return mods


def find_module(mods, addr):
    for m in mods:
        if m.base <= addr < m.end:
            return m
    return None


def qword(buf, off):
    return int.from_bytes(buf[off:off + 8], "little")


def read_ctx(mf, t):
    # ThreadContext: DataSize + rva → 从文件原始字节解
    f = mf.file_handle
    f.seek(t.ThreadContext.Rva)
    return f.read(t.ThreadContext.DataSize)


def thread_rows(mf, mods, top):
    rows = []
    reader = mf.get_reader()
    for t in mf.threads.threads:
        try:
            ctx = read_ctx(mf, t)
            rip, rsp = qword(ctx, CTX_RIP), qword(ctx, CTX_RSP)
        except Exception as e:
            rows.append({"tid": t.ThreadId, "err": f"ctx:{e}"})
            continue
        m = find_module(mods, rip)
        row = {
            "tid": t.ThreadId,
            "rip": rip,
            "rip_mod": m.name if m else "?",
            "rip_rva": hex(rip - m.base) if m else "",
            "rsp": rsp,
            "stack_hits": [],
        }
        # 栈范围: 线程 Stack 描述符(StartOfMemoryRange=RSP 附近, 内存段到 End)
        try:
            seg_end = None
            for seg in mf.memory_segments_64.memory_segments:
                if seg.start_virtual_address <= rsp < seg.start_virtual_address + seg.size:
                    seg_end = seg.start_virtual_address + seg.size
                    break
            end = min(seg_end, rsp + 0x8000) if seg_end else rsp + 0x8000
            buf = reader.read(rsp, end - rsp)
            for off in range(0, len(buf) - 8, 8):
                v = int.from_bytes(buf[off:off + 8], "little")
                if 0x10000 < v < 0x800000000000:  # 用户态地址范围
                    hm = find_module(mods, v)
                    if hm and hm.name != "?":
                        row["stack_hits"].append((hm.name, hex(v - hm.base)))
                        if len(row["stack_hits"]) >= top:
                            break
        except Exception as e:
            row["stack_err"] = str(e)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    for path in args.dumps:
        mf = MinidumpFile.parse(path)
        mods = load_modules(mf)
        ga = next((m for m in mods if "GameAssembly" in m.name), None)
        print(f"\n===== {path} =====")
        print(f"线程数: {len(mf.threads.threads)} | GameAssembly: "
              f"{hex(ga.base)}-{hex(ga.end)}" if ga else "GameAssembly 未找到")
        hot = []
        for row in thread_rows(mf, mods, args.top):
            if "err" in row:
                continue
            ga_stack = sum(1 for n, _ in row["stack_hits"] if "GameAssembly" in n)
            # 候选热点: RIP 在 GameAssembly,或栈上 GameAssembly 帧密集
            if "GameAssembly" in row["rip_mod"] or ga_stack >= 3:
                hot.append((row, ga_stack))
        hot.sort(key=lambda x: x[1], reverse=True)
        for row, ga_stack in hot[:8]:
            print(f"\nTID {row['tid']}  RIP {row['rip_mod']}+{row['rip_rva']}  GA栈帧~{ga_stack}")
            print("  栈上模块链:", " > ".join(f"{n}+{r}" for n, r in row["stack_hits"][:args.top]))
        if not hot:
            print("(无 RIP 在 GameAssembly 的线程;全部线程概览略)")


if __name__ == "__main__":
    main()
