# -*- coding: utf-8 -*-
"""diff_battle_logs.py — middleware 日志战斗会话切分 + 帧序列差分（M-5 Task 6 沉淀）

用途：对比两场战斗（如 1030109 基准 vs 1032020 复现）的 cs_/sc_ 帧序与战斗服事件序，
定位死循环/断链场次在服务端侧"缺少/多出"的帧。差分结论为"服务端无差异"时，
问题指向客户端本地结算流（见 M2-执行计划 Task 6 brief 步骤 2 注）。

用法：
    python tools/diff_battle_logs.py <日志A> <日志B> \
        [--win-a "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS"] \
        [--win-b "YYYY-MM-DD HH:MM:SS" "YYYY-MM-DD HH:MM:SS"] \
        [--list]   # 仅打印两会话的 token 序列（不 diff）

窗口缺省：整份日志参与提取。窗口按行首 `[YYYY-MM-DD HH:MM:SS]` 时间戳过滤（闭区间）。

提取 token：
  - cs_NNNNN / sc_NNNNN（大小写不敏感；[FRAME] "CS_54030 -> SC_54031" 两端都收）
  - 战斗服事件：SYN:ACK9 / SN-ALIGN / FRAME-UP / BATTLE-RESULT / BATTLE-CONN-OPEN /
    BATTLE-CONN-CLOSE（[BattleSrv] 与 TCP:8105 行）
"""
import argparse
import difflib
import re
import sys

_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
_CMD = re.compile(r"\b([csCS][sS])_(\d{5})\b")
_FRAME_ARROW = re.compile(r"CS_(\d{5})\s*->\s*SC_(\d{5})")

_BATTLE_MARKERS = [
    ("[BattleSrv] SYN", "BATTLE:SYN:ACK9"),
    ("序号对齐", "BATTLE:SN-ALIGN"),
    ("客户端战斗帧上传", "BATTLE:FRAME-UP"),
    ("BattleResult bid=", "BATTLE:RESULT"),
    ("[TCP:8105]", None),  # 由 OPEN/CLOSE 子判
]


def _in_window(ts, win):
    if win[0] is None:
        return True
    return win[0] <= ts <= win[1]


def extract_events(path, win):
    """返回该日志（可选时间窗）内的有序 token 列表。"""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = _TS.match(ln)
            if win[0] is not None:
                if not m or not _in_window(m.group(1), win):
                    continue
            hit = False
            fa = _FRAME_ARROW.search(ln)
            if fa:
                out.append("cs_" + fa.group(1))
                out.append("sc_" + fa.group(2))
                hit = True
            if not hit:
                last = None
                for cm in _CMD.finditer(ln):
                    tok = cm.group(1).lower() + "_" + cm.group(2)
                    if tok != last:  # 同一行重复 cmd 只记一次
                        out.append(tok)
                        last = tok
                        hit = True
            for needle, tok in _BATTLE_MARKERS:
                if needle in ln:
                    if tok is None:  # TCP:8105 连接开/闭
                        tok = "BATTLE:CONN-OPEN" if "连接建立" in ln else \
                              ("BATTLE:CONN-CLOSE" if "连接关闭" in ln else None)
                    if tok:
                        out.append(tok)
                    break
    return out


def main():
    ap = argparse.ArgumentParser(description="两场战斗 middleware 帧序差分")
    ap.add_argument("log_a")
    ap.add_argument("log_b")
    ap.add_argument("--win-a", nargs=2, metavar=("START", "END"), default=[None, None])
    ap.add_argument("--win-b", nargs=2, metavar=("START", "END"), default=[None, None])
    ap.add_argument("--list", action="store_true", help="仅打印两会话 token 序列")
    args = ap.parse_args()

    a = extract_events(args.log_a, args.win_a)
    b = extract_events(args.log_b, args.win_b)

    if args.list:
        print(f"== {args.log_a} ({len(a)} tokens) ==")
        print(" ".join(a))
        print(f"== {args.log_b} ({len(b)} tokens) ==")
        print(" ".join(b))
        return 0

    print(f"# A={args.log_a} tokens={len(a)}  B={args.log_b} tokens={len(b)}")
    diff = list(difflib.unified_diff(a, b, fromfile="A", tofile="B", lineterm="", n=2))
    if not diff:
        print("# 服务端侧帧序完全一致（差分为空）——结论指向客户端本地结算流")
        return 0
    print("\n".join(diff))
    return 0


if __name__ == "__main__":
    sys.exit(main())
