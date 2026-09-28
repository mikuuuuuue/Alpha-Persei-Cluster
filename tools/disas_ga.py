#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/disas_ga.py — GameAssembly.dll RVA 反汇编器(调用点以 Il2CppDumper script.json 注名)

用法: python disas_ga.py <rva> [-n 字节数] [--json script.json] [--dll GameAssembly.dll]
"""
import sys
import json
import bisect
import argparse
import struct

import capstone


def load_sections(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = pe + 24
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    sopt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    for i in range(nsec):
        s = opt + sopt + i * 40
        vsz, va, rsz, ro = struct.unpack_from("<IIII", data, s + 8)
        secs.append((va, max(vsz, rsz), ro, rsz))
    return secs


def rva_to_off(secs, rva):
    for va, sz, ro, rsz in secs:
        if va <= rva < va + sz:
            return ro + (rva - va)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rva")
    ap.add_argument("-n", "--bytes", type=int, default=0x300)
    ap.add_argument("--dll", default=r"C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili\GameAssembly.dll")
    ap.add_argument("--json", default=r"C:\Users\<user>\Desktop\解包\tools\Il2CppDumper\script.json")
    ap.add_argument("--until-ret", action="store_true")
    args = ap.parse_args()

    rva = int(args.rva, 16)
    data = open(args.dll, "rb").read()
    secs = load_sections(data)
    off = rva_to_off(secs, rva)

    names = {}
    if args.json:
        sj = json.load(open(args.json, encoding="utf-8"))
        for m in sj.get("ScriptMethod", []):
            names[m["Address"]] = m["Name"]
    keys = sorted(names)

    def nm(a):
        i = bisect.bisect_right(keys, a) - 1
        if i >= 0 and a - keys[i] < 0x80 and keys[i] in names:
            return f"{names[keys[i]]}+{hex(a - keys[i])}"
        return None

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    code = data[off:off + (0x20000 if args.until_ret else args.bytes)]
    count = 0
    for ins in md.disasm(code, rva):
        line = f"{ins.address:#x}  {ins.mnemonic} {ins.op_str}".rstrip()
        ann = ""
        # call/jmp 直接目标
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            n2 = nm(t)
            if n2:
                ann = f"   ; -> {n2}"
        # rip 相对寻址 → 数据地址
        elif "rip" in ins.op_str:
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                    t = ins.address + ins.size + op.mem.disp
                    n2 = nm(t)
                    ann = f"   ; [{t:#x}]" + (f" {n2}" if n2 else "")
        print(line + ann)
        count += 1
        if args.until_ret and ins.mnemonic == "ret":
            break
        if count > 4000:
            print("...(截断)")
            break


if __name__ == "__main__":
    main()
