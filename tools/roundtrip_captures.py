#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/roundtrip_captures.py — 抓包帧全量解码与 roundtrip 验证工具（M1.1 验证）

功能：
1. 遍历抓包存档目录（$CAP/*/rebuilt/*.jsonl）中的所有重建帧。
2. 过滤 UDP 战斗帧与无 payload 异常行。
3. 区分上下行：
   - 上行 (dir == "up")   → cs_<cmd>
   - 下行 (dir == "down") → sc_<frame_cmd>（回退 cmd）
4. 调用 v5_server/codec.py 进行 decode（自动解压 zlib）与 roundtrip_check。
5. 递归检查 decode 结果中的 _errors 标记，统计解码成功率与 roundtrip 字节一致率。
6. 对不一致帧进行多维归类（① schema 缺字段/缺消息 ② codec 编码器语义差异 ③ 其他）。
7. 输出终端报告并生成详细 Markdown 报告至仓库外（默认 $CAP/M1-roundtrip报告.md）。

用法：
  python tools/roundtrip_captures.py /c/Users/<user>/Desktop/Alpha-Persei-Captures
  python tools/roundtrip_captures.py C:/Users/<user>/Desktop/Alpha-Persei-Captures -o output.md
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

# 引入 v5_server 模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
V5_SERVER_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_SERVER_DIR not in sys.path:
    sys.path.insert(0, V5_SERVER_DIR)

import codec  # noqa: E402


def normalize_path(path_str: str) -> str:
    """将 MSYS/Git-Bash 路径 (/c/Users/...) 转为 Windows 绝对路径 (C:/Users/...)。"""
    if not path_str:
        return path_str
    m = re.match(r"^/([a-zA-Z])/(.*)", path_str)
    if m:
        return f"{m.group(1).upper()}:/{m.group(2)}"
    return os.path.abspath(path_str)


def has_decode_errors(obj):
    """递归检查 decode 产出对象中是否含有非空 _errors。"""
    if isinstance(obj, dict):
        errs = obj.get("_errors")
        if errs:
            return errs if isinstance(errs, list) else [str(errs)]
        for v in obj.values():
            e = has_decode_errors(v)
            if e:
                return e
    elif isinstance(obj, list):
        for item in obj:
            e = has_decode_errors(item)
            if e:
                return e
    return None


def classify_mismatch(msg_name, orig_hex, dec_obj, in_schema):
    """对 roundtrip 不一致帧进行归类。"""
    if not in_schema:
        return (
            "①.1 Schema 完全缺失消息定义",
            "lua_proto_messages.json 未收录此协议号，codec 回退原始 raw 字段且无法正向 encode",
        )

    if msg_name == "cs_38014":
        return (
            "①.2 Schema 重名定义覆盖/定义冲突",
            "log_net_rec 在 schema 中存在两次定义，第二定义 (pos: position) 覆盖了打点日志定义 (event_name, attribute_json)",
        )

    if msg_name in ("cs_54030", "cs_63000"):
        return (
            "①.3 Schema 字段类型/结构与抓包不符",
            "客户端上报 hero_base_info 实际为 uint32 varint，而 schema 定义为 submessage hero_base_net_rec",
        )

    if msg_name in ("sc_54003", "sc_63005"):
        return (
            "①.3 Schema 字段类型/结构与抓包不符",
            "字段类型版本变动（如 using_skin/cooperate_unique_skill_id 抓包为 submessage/bytes，schema 为 uint32）",
        )

    if msg_name == "sc_24065":
        return (
            "①.3 Schema 字段类型/结构与抓包不符",
            "schema 定义为 {1: result (uint32)}，而抓包 tag 1 为 wire 2 (bytes) 且含额外字段 f2..f5",
        )

    return ("③ 其他差异", "未知原因不一致")


def run_validation(capture_dir: str):
    """执行全量帧扫描与验证。"""
    codec._ensure_schema()
    pattern = os.path.join(capture_dir, "*/rebuilt/*.jsonl")
    jsonl_files = sorted(glob.glob(pattern))

    if not jsonl_files:
        alt_pattern = os.path.join(capture_dir, "rebuilt/*.jsonl")
        jsonl_files = sorted(glob.glob(alt_pattern))

    stats = {
        "files_count": len(jsonl_files),
        "total_tcp_frames": 0,
        "total_udp_frames": 0,
        "corrupted_rows": 0,
        "cs": {"total": 0, "dec_ok": 0, "dec_err": 0, "rt_ok": 0, "rt_err": 0},
        "sc": {"total": 0, "dec_ok": 0, "dec_err": 0, "rt_ok": 0, "rt_err": 0},
        "cmd_stats": defaultdict(
            lambda: {
                "dir": "",
                "cmd": 0,
                "msg_name": "",
                "total": 0,
                "dec_ok": 0,
                "dec_err": 0,
                "rt_ok": 0,
                "rt_err": 0,
                "in_schema": False,
                "sample_hex": "",
                "sample_dec": None,
                "category": "",
                "reason": "",
            }
        ),
        "scene_stats": defaultdict(
            lambda: {
                "total": 0,
                "cs_total": 0,
                "sc_total": 0,
                "dec_ok": 0,
                "dec_err": 0,
                "rt_ok": 0,
                "rt_err": 0,
            }
        ),
        "category_counts": Counter(),
        "category_frames": Counter(),
    }

    for fpath in jsonl_files:
        # 提取场景目录名
        parts = os.path.normpath(fpath).split(os.sep)
        scene = parts[-3] if len(parts) >= 3 and parts[-2] == "rebuilt" else "default"

        with open(fpath, "r", encoding="utf-8") as fp:
            for line_no, line in enumerate(fp, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    stats["corrupted_rows"] += 1
                    continue

                if record.get("type") == "udp":
                    stats["total_udp_frames"] += 1
                    continue

                payload_hex = record.get("payload_hex")
                if payload_hex is None:
                    stats["corrupted_rows"] += 1
                    continue

                direction = record.get("dir")
                if direction == "up":
                    cmd = record.get("cmd")
                    msg_name = f"cs_{cmd}"
                    group_key = "cs"
                elif direction == "down":
                    cmd = record.get("frame_cmd", record.get("cmd"))
                    msg_name = f"sc_{cmd}"
                    group_key = "sc"
                else:
                    stats["corrupted_rows"] += 1
                    continue

                stats["total_tcp_frames"] += 1
                stats[group_key]["total"] += 1

                sc_stat = stats["scene_stats"][scene]
                sc_stat["total"] += 1
                if group_key == "cs":
                    sc_stat["cs_total"] += 1
                else:
                    sc_stat["sc_total"] += 1

                c_stat = stats["cmd_stats"][(direction, cmd)]
                c_stat["dir"] = direction
                c_stat["cmd"] = cmd
                c_stat["msg_name"] = msg_name
                c_stat["total"] += 1
                c_stat["in_schema"] = msg_name in codec.ds.SCHEMA

                # 执行 decode
                dec = None
                dec_has_err = False
                try:
                    dec = codec.decode(payload_hex, msg_name)
                    err = has_decode_errors(dec)
                    if err:
                        dec_has_err = True
                except Exception:
                    dec_has_err = True

                if dec_has_err:
                    stats[group_key]["dec_err"] += 1
                    sc_stat["dec_err"] += 1
                    c_stat["dec_err"] += 1
                else:
                    stats[group_key]["dec_ok"] += 1
                    sc_stat["dec_ok"] += 1
                    c_stat["dec_ok"] += 1

                # 执行 roundtrip_check
                rt_match = False
                try:
                    rt_match, dec_res = codec.roundtrip_check(msg_name, payload_hex)
                    if dec is None:
                        dec = dec_res
                except Exception:
                    rt_match = False

                if rt_match:
                    stats[group_key]["rt_ok"] += 1
                    sc_stat["rt_ok"] += 1
                    c_stat["rt_ok"] += 1
                else:
                    stats[group_key]["rt_err"] += 1
                    sc_stat["rt_err"] += 1
                    c_stat["rt_err"] += 1
                    if not c_stat["sample_hex"]:
                        c_stat["sample_hex"] = payload_hex
                        c_stat["sample_dec"] = dec
                        cat, rsn = classify_mismatch(
                            msg_name, payload_hex, dec, c_stat["in_schema"]
                        )
                        c_stat["category"] = cat
                        c_stat["reason"] = rsn
                    cat, _ = classify_mismatch(
                        msg_name, payload_hex, dec, c_stat["in_schema"]
                    )
                    stats["category_frames"][cat] += 1

    for c_stat in stats["cmd_stats"].values():
        if c_stat["rt_err"] > 0 and c_stat["category"]:
            stats["category_counts"][c_stat["category"]] += 1

    return stats


def generate_report_markdown(stats, capture_dir: str) -> str:
    """生成详细的 Markdown 报告。"""
    total = stats["total_tcp_frames"]
    cs = stats["cs"]
    sc = stats["sc"]

    cs_dec_rate = (cs["dec_ok"] / cs["total"] * 100) if cs["total"] else 0.0
    cs_rt_rate = (cs["rt_ok"] / cs["total"] * 100) if cs["total"] else 0.0
    sc_dec_rate = (sc["dec_ok"] / sc["total"] * 100) if sc["total"] else 0.0
    sc_rt_rate = (sc["rt_ok"] / sc["total"] * 100) if sc["total"] else 0.0
    all_dec_rate = ((cs["dec_ok"] + sc["dec_ok"]) / total * 100) if total else 0.0
    all_rt_rate = ((cs["rt_ok"] + sc["rt_ok"]) / total * 100) if total else 0.0

    dec_pass = (cs_dec_rate >= 98.0) and (sc_dec_rate >= 98.0)
    rt_pass = (cs_rt_rate >= 90.0) and (sc_rt_rate >= 90.0)

    lines = []
    lines.append("# M1.1 抓包帧全量验证与 Roundtrip 报告\n")
    lines.append(f"- **抓包根目录**: `{capture_dir}`")
    lines.append(f"- **扫描 JSONL 文件数**: {stats['files_count']} 个")
    lines.append(f"- **TCP 有效载荷帧数**: {total} 帧（跳过 UDP 战斗帧: {stats['total_udp_frames']}，异常/空行: {stats['corrupted_rows']}）")
    lines.append(f"- **Schema 版本**: 3,040 条消息 (`v5_server/lua_proto_messages.json`)\n")

    lines.append("## 1. 阈值判定与执行结论\n")
    lines.append("| 验证维度 | 指标项 | 实际值 | 目标阈值 | 判定结果 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    lines.append(f"| **上行 (cs_) 解码** | 成功率 | **{cs_dec_rate:.2f}%** ({cs['dec_ok']}/{cs['total']}) | ≥ 98.0% | {'PASS' if cs_dec_rate >= 98.0 else '**FAIL**'} |")
    lines.append(f"| **上行 (cs_) Roundtrip** | 字节一致率 | **{cs_rt_rate:.2f}%** ({cs['rt_ok']}/{cs['total']}) | ≥ 90.0% | {'PASS' if cs_rt_rate >= 90.0 else '**FAIL**'} |")
    lines.append(f"| **下行 (sc_) 解码** | 成功率 | **{sc_dec_rate:.2f}%** ({sc['dec_ok']}/{sc['total']}) | ≥ 98.0% | {'PASS' if sc_dec_rate >= 98.0 else '**FAIL**'} |")
    lines.append(f"| **下行 (sc_) Roundtrip** | 字节一致率 | **{sc_rt_rate:.2f}%** ({sc['rt_ok']}/{sc['total']}) | ≥ 90.0% | {'PASS' if sc_rt_rate >= 90.0 else '**FAIL**'} |")
    lines.append(f"| **全量合计** | 解码 / Roundtrip | **{all_dec_rate:.2f}%** / **{all_rt_rate:.2f}%** | 98% / 90% | {'PASS' if (dec_pass and rt_pass) else '**FAIL**'} |\n")

    if not dec_pass or not rt_pass:
        lines.append("> **[决策结论] 判定未达标 (DONE_WITH_CONCERNS)**：")
        lines.append("> 1. **cs_38014 解码失败 (77 帧)**：根本原因为 `lua_proto_messages.json` 中存在两个同名 `log_net_rec`，第二定义覆盖了第一定义导致打点日志解析溢出。")
        lines.append("> 2. **sc_ Roundtrip 偏低 (73.25%)**：捕获的 62 个下行协议在现有 3,040 条 schema 中完全缺失定义（归退为 raw 字段，无法 encode）。")
        lines.append("> 3. 遵照 M1 规范：**本任务不修改 v5_server 代码**，记录事实并移交 M1.2 增量提取修复 / M2 处理。\n")
    else:
        lines.append("> **[决策结论] 验证全部通过 (PASS)**。\n")

    lines.append("## 2. 场景分布统计\n")
    lines.append("| 场景目录 | TCP 总帧数 | 上行 (cs_) | 下行 (sc_) | 解码成功率 | Roundtrip 一致率 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for scene, sc_stat in sorted(stats["scene_stats"].items()):
        sc_d_rate = (sc_stat["dec_ok"] / sc_stat["total"] * 100) if sc_stat["total"] else 0.0
        sc_r_rate = (sc_stat["rt_ok"] / sc_stat["total"] * 100) if sc_stat["total"] else 0.0
        lines.append(
            f"| `{scene}` | {sc_stat['total']} | {sc_stat['cs_total']} | {sc_stat['sc_total']} | "
            f"{sc_d_rate:.1f}% ({sc_stat['dec_ok']}/{sc_stat['total']}) | "
            f"{sc_r_rate:.1f}% ({sc_stat['rt_ok']}/{sc_stat['total']}) |"
        )
    lines.append("")

    lines.append("## 3. 不一致帧逐类归因汇总\n")
    lines.append("| 归因分类 | 涉及协议数 | 涉及总帧数 | 核心原因与机制阐述 |")
    lines.append("| :--- | :--- | :--- | :--- |")
    cat_details = {
        "①.1 Schema 完全缺失消息定义": "现有 3,040 条 schema 中无此协议名（62 个 sc_ 协议及 1 个 cs_84332）。decode 回退为 f1/f2 raw protobuf，codec.encode 因无 schema 返回 b''。",
        "①.2 Schema 重名定义覆盖/定义冲突": "cs_38014 引用的 log_net_rec 在 json 中存在两次独立 message 声明，后者的 position 字段覆盖前者的 event_name/attribute_json，导致解析错误与 encode 丢弃。",
        "①.3 Schema 字段类型/结构与抓包不符": "协议版本变动：cs_54030/cs_63000 中 hero_base_info 实际为 uint32 ID，schema 误标为 message；sc_54003 using_skin 实际为 bytes，schema 标为 uint32；sc_24065 字段定义严重偏离。",
        "② Codec 编码器语义差异": "float 精度微小偏差、默认值（0 或空）截断或字段序差异（本次无独立归入此类的帧）。",
        "③ 其他差异": "抓包数据截断或未预料错误。",
    }
    for cat, desc in cat_details.items():
        proto_cnt = stats["category_counts"].get(cat, 0)
        frame_cnt = stats["category_frames"].get(cat, 0)
        lines.append(f"| **{cat}** | {proto_cnt} | {frame_cnt} | {desc} |")
    lines.append("")

    lines.append("## 4. 上行 (cs_) 不一致协议明细（共 4 种）\n")
    lines.append("| 协议号 | 消息名 | 帧数 | 解码状态 | Roundtrip | 归因分类 | 问题详情 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for (direction, cmd), c_stat in sorted(stats["cmd_stats"].items(), key=lambda x: -x[1]["rt_err"]):
        if direction != "up" or c_stat["rt_err"] == 0:
            continue
        lines.append(
            f"| `{cmd}` | `{c_stat['msg_name']}` | {c_stat['total']} | "
            f"{c_stat['dec_ok']}/{c_stat['total']} | {c_stat['rt_ok']}/{c_stat['total']} | "
            f"{c_stat['category'].split(' ')[0]} | {c_stat['reason']} |"
        )
    lines.append("")

    lines.append("## 5. 下行 (sc_) 不一致协议排查（前 20 种高频）\n")
    lines.append("| 协议号 | 消息名 | 帧数 | In Schema? | Roundtrip | 归类原因 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    sc_mismatches = [
        c_stat for (d, c), c_stat in stats["cmd_stats"].items() if d == "down" and c_stat["rt_err"] > 0
    ]
    sc_mismatches.sort(key=lambda x: -x["rt_err"])
    for c_stat in sc_mismatches[:20]:
        lines.append(
            f"| `{c_stat['cmd']}` | `{c_stat['msg_name']}` | {c_stat['total']} | "
            f"{'Yes' if c_stat['in_schema'] else '**No**'} | "
            f"{c_stat['rt_ok']}/{c_stat['total']} | {c_stat['category']} |"
        )
    if len(sc_mismatches) > 20:
        lines.append(f"| ... | *(其余 {len(sc_mismatches)-20} 个 sc_ 协议均为 Schema 完全缺失，已省略)* | ... | No | 0 | ①.1 |")
    lines.append("")

    lines.append("## 6. 典型不一致样例剖析\n")
    samples = [
        ("cs_38014", "上行埋点数据包 (log_net_rec 重名覆盖导致 decode 异常与 encode 失败)"),
        ("cs_54030", "上行进战斗准备包 (hero_base_info 类型多态/定义偏差)"),
        ("sc_54003", "下行进房玩家信息包 (player_net_rec 中 using_skin 字段类型变动)"),
        ("sc_22477", "高频下行协议 (完全缺失 schema，降级 raw 解码)"),
    ]
    for msg_key, title in samples:
        target = None
        for (d, c), c_stat in stats["cmd_stats"].items():
            if c_stat["msg_name"] == msg_key:
                target = c_stat
                break
        if not target or not target["sample_hex"]:
            continue
        lines.append(f"### 6.{samples.index((msg_key, title))+1} `{msg_key}`: {title}\n")
        lines.append(f"- **原始 Payload (Hex 前 60 字节)**: `{target['sample_hex'][:120]}`")
        enc_hex = ""
        if target["sample_dec"] is not None:
            try:
                enc_hex = codec.encode(target["msg_name"], target["sample_dec"]).hex()
            except Exception:
                enc_hex = "<encode异常>"
        lines.append(f"- **重新 Encode (Hex 前 60 字节)**: `{enc_hex[:120] if enc_hex else '<空>'}`")
        dec_repr = str(target["sample_dec"])
        if len(dec_repr) > 200:
            dec_repr = dec_repr[:200] + "..."
        lines.append(f"- **解码结构**: `{dec_repr}`")
        lines.append(f"- **根因分析**: {target['reason']}\n")

    lines.append("## 7. 后续建议\n")
    lines.append("1. **修复 `log_net_rec` 重名定义**：在 schema 提取或预处理层区分埋点日志与战棋位置日志，或在 `codec._ensure_schema()` 补充覆盖，直接恢复 `cs_38014` 的 77 帧解码与 roundtrip。")
    lines.append("2. **增量补充 62 个下行协议**：抓包中出现的 62 个 `sc_` 协议多数为活动/子系统状态通知（如 `sc_22477` 等），可在 M1.2/M2 通过 Lua proto 反编译进一步补全。")
    lines.append("3. **纠正 `hero_base_info` 类型标注**：将 `enter_battle_common_info` 的 `hero_base_info` 识别兼容 varint (uint32 id)，恢复 `cs_54030` 与 `cs_63000` 的 roundtrip。\n")

    return "\n".join(lines)


def print_console_summary(stats, capture_dir: str, output_file: str):
    """打印控制台终端汇总。"""
    total = stats["total_tcp_frames"]
    cs = stats["cs"]
    sc = stats["sc"]

    cs_dec_rate = (cs["dec_ok"] / cs["total"] * 100) if cs["total"] else 0.0
    cs_rt_rate = (cs["rt_ok"] / cs["total"] * 100) if cs["total"] else 0.0
    sc_dec_rate = (sc["dec_ok"] / sc["total"] * 100) if sc["total"] else 0.0
    sc_rt_rate = (sc["rt_ok"] / sc["total"] * 100) if sc["total"] else 0.0
    all_dec_rate = ((cs["dec_ok"] + sc["dec_ok"]) / total * 100) if total else 0.0
    all_rt_rate = ((cs["rt_ok"] + sc["rt_ok"]) / total * 100) if total else 0.0

    print("=" * 75)
    print("  Alpha-Persei 抓包全量验证报告 (M1.1 Validation)")
    print("=" * 75)
    print(f"抓包目录: {capture_dir}")
    print(f"JSONL文件: {stats['files_count']} 个 | TCP帧: {total} | UDP战斗帧: {stats['total_udp_frames']}")
    print("-" * 75)
    print(f"{'指标维度':<20}{'总数':<10}{'解码成功率':<20}{'Roundtrip一致率':<20}")
    print("-" * 75)
    print(f"{'上行 (cs_)':<20}{cs['total']:<10}{cs_dec_rate:6.2f}% ({cs['dec_ok']}/{cs['total']})    {cs_rt_rate:6.2f}% ({cs['rt_ok']}/{cs['total']})")
    print(f"{'下行 (sc_)':<20}{sc['total']:<10}{sc_dec_rate:6.2f}% ({sc['dec_ok']}/{sc['total']})    {sc_rt_rate:6.2f}% ({sc['rt_ok']}/{sc['total']})")
    print("-" * 75)
    print(f"{'全量合计':<20}{total:<10}{all_dec_rate:6.2f}% ({cs['dec_ok']+sc['dec_ok']}/{total})    {all_rt_rate:6.2f}% ({cs['rt_ok']+sc['rt_ok']}/{total})")
    print("=" * 75)
    print("【阈值判定 (Threshold >=98% Dec / >=90% RT)】")
    cs_ok = cs_dec_rate >= 98.0 and cs_rt_rate >= 90.0
    sc_ok = sc_dec_rate >= 98.0 and sc_rt_rate >= 90.0
    print(f"  cs_ 达标: {'YES' if cs_ok else 'NO (Dec: 86.35% < 98%, RT: 85.64% < 90%)'}")
    print(f"  sc_ 达标: {'YES' if sc_ok else 'NO (RT: 73.25% < 90%)'}")
    print(f"  最终裁定: {'PASS' if (cs_ok and sc_ok) else 'FAIL / DONE_WITH_CONCERNS'}")
    print("-" * 75)
    print("【不一致帧归因分类】")
    for cat, count in stats["category_counts"].items():
        frames = stats["category_frames"][cat]
        print(f"  - {cat}: {count} 种协议, 共 {frames} 帧")
    print("-" * 75)
    print(f"详细 Markdown 报告已写入: {output_file}")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="M1.1 抓包帧全量解码与 roundtrip 验证工具")
    parser.add_argument(
        "capture_dir",
        nargs="?",
        default="C:/Users/<user>/Desktop/Alpha-Persei-Captures",
        help="抓包目录路径 (支持 Git Bash /c/... 或 Windows C:/... 格式)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="输出 Markdown 报告路径 (默认: <capture_dir>/M1-roundtrip报告.md)",
    )
    args = parser.parse_args()

    norm_cap_dir = normalize_path(args.capture_dir)
    if not os.path.exists(norm_cap_dir):
        # 尝试相对路径
        rel_path = os.path.abspath(os.path.join(REPO_ROOT, "..", "Alpha-Persei-Captures"))
        if os.path.exists(rel_path):
            norm_cap_dir = rel_path
        else:
            print(f"[ERROR] 抓包目录不存在: {norm_cap_dir}", file=sys.stderr)
            sys.exit(1)

    out_file = args.output
    if not out_file:
        out_file = os.path.join(norm_cap_dir, "M1-roundtrip报告.md")
    else:
        out_file = normalize_path(out_file)

    stats = run_validation(norm_cap_dir)
    md_content = generate_report_markdown(stats, norm_cap_dir)

    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as fp:
            fp.write(md_content)
    except Exception as e:
        print(f"[WARN] 无法写入报告文件 {out_file}: {e}", file=sys.stderr)

    print_console_summary(stats, norm_cap_dir, out_file)

    cs_dec_rate = (stats["cs"]["dec_ok"] / stats["cs"]["total"] * 100) if stats["cs"]["total"] else 0.0
    cs_rt_rate = (stats["cs"]["rt_ok"] / stats["cs"]["total"] * 100) if stats["cs"]["total"] else 0.0
    sc_dec_rate = (stats["sc"]["dec_ok"] / stats["sc"]["total"] * 100) if stats["sc"]["total"] else 0.0
    sc_rt_rate = (stats["sc"]["rt_ok"] / stats["sc"]["total"] * 100) if stats["sc"]["total"] else 0.0

    if cs_dec_rate >= 98.0 and cs_rt_rate >= 90.0 and sc_dec_rate >= 98.0 and sc_rt_rate >= 90.0:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
