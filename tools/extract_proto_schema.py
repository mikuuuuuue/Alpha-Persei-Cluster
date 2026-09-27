#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/extract_proto_schema.py — 反编译 *_pb.lua → lua_proto_messages.json（M1.1 产物生成器）

用法：
  python tools/extract_proto_schema.py <protocol目录> -o <输出.json>
  python tools/extract_proto_schema.py --selftest   # 黄金样例断言（内置 cs_16010/sc_16011 与 p38/p49 作用域消歧）
"""

import argparse
from collections import Counter, defaultdict
import glob
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# 枚举映射表
# ---------------------------------------------------------------------------
LABEL_MAP = {
    1: "optional",
    2: "required",
    3: "repeated",
}

# 标准 protobuf wire / field type 映射
TYPE_MAP = {
    1: "double",
    2: "float",
    3: "int64",
    4: "uint64",
    5: "int32",
    6: "fixed64",
    7: "fixed32",
    8: "bool",
    9: "string",
    10: "group",
    11: "message",
    12: "bytes",
    13: "uint32",
    14: "enum",
    15: "sfixed32",
    16: "sfixed64",
    17: "sint32",
    18: "sint64",
}

# ---------------------------------------------------------------------------
# 正则表达式
# ---------------------------------------------------------------------------
# require 映射：slot1 = require("protocol/item_hrl_pb")
REQ_PAT = re.compile(r"^slot(\d+)\s*=\s*require\([\"']([^\"']+)[\"']\)", re.MULTILINE)

# 消息全局描述符：CS_16010 = slot0.Descriptor()
DESC_PAT = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*slot0\.Descriptor\(\)", re.MULTILINE)

# 消息命名：CS_16010.name = "cs_16010"
MSG_NAME_PAT = re.compile(r"^([A-Za-z0-9_]+)\.name\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)

# 消息完整命名（含 package 作用域）：LOG_NET_REC.full_name = ".p38.log_net_rec"
MSG_FULL_NAME_PAT = re.compile(r"^([A-Za-z0-9_]+)\.full_name\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)

# 字段属性赋值：slot2.CS_16010_FIELD_LIST.CS_16010_TYPE_FIELD.name = "type"
FIELD_ATTR_PAT = re.compile(
    r"slot\d+\.([A-Za-z0-9_]+)_FIELD_LIST\.([A-Za-z0-9_]+_FIELD)\.(name|number|label|type|message_type)\s*=\s*(.+)$",
    re.MULTILINE,
)

# 默认搜索候选路径
DEFAULT_PROTO_CANDIDATES = [
    os.environ.get("UNPACK") and os.path.join(os.environ["UNPACK"], "protocol"),
    os.environ.get("UNPACK") and os.path.join(os.environ["UNPACK"], "Lua源码", "protocol"),
    os.environ.get("UNPACK") and os.path.join(os.environ["UNPACK"], "Lua源码库", "Lua源码", "protocol"),
    r"C:\Users\<user>\Desktop\解包\Lua源码库\Lua源码\protocol",
    "/c/Users/<user>/Desktop/解包/Lua源码库/Lua源码/protocol",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "解包", "Lua源码库", "Lua源码", "protocol"),
]


def find_default_proto_dir():
    """查找默认的 protocol 目录。"""
    for p in DEFAULT_PROTO_CANDIDATES:
        if p and os.path.isdir(p):
            return os.path.abspath(p)
    return None


def extract_scope(full_name, bare_name):
    """从 full_name 中剥离前导点与末尾消息名，返回作用域包名前缀（小写）。"""
    clean_fn = (full_name or "").strip().lstrip(".")
    bn_lower = bare_name.lower()
    if clean_fn.lower().endswith("." + bn_lower):
        return clean_fn[:-len(bn_lower) - 1].lower()
    elif clean_fn.lower().endswith(bn_lower):
        return clean_fn[:-len(bn_lower)].rstrip(".").lower()
    elif "." in clean_fn:
        return clean_fn.split(".")[0].lower()
    return ""


def parse_file_raw(filepath):
    """解析单个 *_pb.lua 文件的 raw 结构（第一遍扫描）。

    返回：
      mod_name: 模块文件名（无后缀，如 p16_pb）
      requires: {slotN: module_name}
      raw_messages: list of dict {var, bare_name, full_name, scope}
      msg_fields: {MSG_VAR: {FIELD_VAR: {attr: raw_val}}}
    """
    mod_name = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, "r", encoding="utf-8") as fh:
        text = fh.read()

    requires = {}
    for sm in REQ_PAT.finditer(text):
        slot_num, req_path = sm.group(1), sm.group(2)
        req_mod = req_path.split("/")[-1]
        requires[f"slot{slot_num}"] = req_mod

    names = dict(MSG_NAME_PAT.findall(text))
    full_names = dict(MSG_FULL_NAME_PAT.findall(text))

    raw_messages = []
    for var, raw_name in names.items():
        norm_name = raw_name.strip().lstrip(".").lower()
        raw_fn = full_names.get(var, "").strip()
        scope = extract_scope(raw_fn, norm_name)
        raw_messages.append({
            "var": var,
            "bare_name": norm_name,
            "full_name": raw_fn,
            "scope": scope,
            "mod_name": mod_name,
            "file": os.path.basename(filepath),
        })

    msg_fields = {m["var"]: {} for m in raw_messages}
    for fm in FIELD_ATTR_PAT.finditer(text):
        mvar, fvar, attr, val = fm.group(1), fm.group(2), fm.group(3), fm.group(4).strip()
        if mvar in msg_fields:
            if fvar not in msg_fields[mvar]:
                msg_fields[mvar][fvar] = {}
            msg_fields[mvar][fvar][attr] = val

    return mod_name, requires, raw_messages, msg_fields


def resolve_message_ref(val, requires, current_mod, module_var_to_reg, global_var_to_reg):
    """解析 message_type 赋值表达式右侧的目标消息注册名。"""
    val = val.strip()

    # 形态 1: slot1.ITEM_NET_REC
    m1 = re.match(r"^(slot\d+)\.([A-Za-z0-9_]+)$", val)
    if m1:
        slot, var = m1.group(1), m1.group(2)
        target_mod = requires.get(slot)
        if target_mod and target_mod in module_var_to_reg:
            target_reg_name = module_var_to_reg[target_mod].get(var)
            if target_reg_name:
                return target_reg_name

    # 形态 2: require("protocol/xxx_pb").VAR_NAME
    m2 = re.match(r"^require\([\"']protocol/([^\"']+)[\"']\)\.([A-Za-z0-9_]+)$", val)
    if m2:
        req_mod = m2.group(1).split("/")[-1]
        var = m2.group(2)
        if req_mod in module_var_to_reg:
            target_reg_name = module_var_to_reg[req_mod].get(var)
            if target_reg_name:
                return target_reg_name

    # 形态 3: VAR_NAME（优先当前文件局部注册名，其次全局回退）
    m3 = re.match(r"^([A-Za-z0-9_]+)$", val)
    if m3:
        var = m3.group(1)
        if current_mod in module_var_to_reg and var in module_var_to_reg[current_mod]:
            return module_var_to_reg[current_mod][var]
        if var in global_var_to_reg:
            return global_var_to_reg[var]

    return None


def extract_proto_schema(proto_dir_or_files):
    """两遍扫描提取 protocol 目录下所有消息定义，执行作用域消歧。

    返回：
      messages: 消息定义列表 [{"name": ..., "fields": [...]}]
      stats: 统计指标字典
    """
    if isinstance(proto_dir_or_files, str):
        if os.path.isdir(proto_dir_or_files):
            file_paths = sorted(glob.glob(os.path.join(proto_dir_or_files, "*.lua")))
        elif os.path.isfile(proto_dir_or_files):
            file_paths = [proto_dir_or_files]
        else:
            raise FileNotFoundError(f"路径不存在: {proto_dir_or_files}")
    else:
        file_paths = list(proto_dir_or_files)

    file_paths = sorted(os.path.abspath(p) for p in file_paths)
    target_files_set = set(file_paths)

    # 第一遍：收集所有目标文件及依赖模块
    file_records = []
    loaded_mods = set()

    for fpath in file_paths:
        mod_name, requires, raw_messages, msg_fields = parse_file_raw(fpath)
        loaded_mods.add(mod_name)
        file_records.append((fpath, mod_name, requires, raw_messages, msg_fields, True))

    # 若为单文件或部分文件提取，自动加载依赖模块以支持跨文件解引用
    for fpath, mod_name, requires, raw_messages, msg_fields, is_target in list(file_records):
        proto_dir = os.path.dirname(fpath)
        for slot, req_mod in requires.items():
            if req_mod not in loaded_mods and req_mod != "protobuf":
                candidate = os.path.join(proto_dir, f"{req_mod}.lua")
                if os.path.exists(candidate):
                    dep_mod, dep_req, dep_raw_msgs, dep_msg_fields = parse_file_raw(candidate)
                    loaded_mods.add(dep_mod)
                    file_records.append((candidate, dep_mod, dep_req, dep_raw_msgs, dep_msg_fields, False))

    # 按文件名稳定排序文件记录
    file_records.sort(key=lambda rec: os.path.basename(rec[0]))

    # 汇集所有消息对象
    all_messages_raw = []
    for fpath, mod_name, requires, raw_messages, msg_fields, is_target in file_records:
        for m in raw_messages:
            m["_fields_dict"] = msg_fields.get(m["var"], {})
            m["_requires"] = requires
            m["_is_target"] = is_target
            all_messages_raw.append(m)

    # -----------------------------------------------------------------------
    # 消歧与注册名仲裁规则：
    # 1. 消息注册时若 name（小写）已被占用 → 改用作用域名：取 full_name 去掉前导点和消息名本身后的前缀，
    #    如 .p38.log_net_rec → 注册名 p38.log_net_rec；
    #    .common.log_net_rec 这类 common 作用域者保留裸名 log_net_rec。
    #    作用域相同仍冲突 → 文件名排序先者保留，后者追加 _2 后缀并在 stderr 告警。
    # -----------------------------------------------------------------------
    by_bare_name = defaultdict(list)
    for m in all_messages_raw:
        by_bare_name[m["bare_name"]].append(m)

    conflicts_summary = []
    for bare_name, msg_list in sorted(by_bare_name.items()):
        if len(msg_list) == 1:
            msg_list[0]["registered_name"] = bare_name
        else:
            conflict_info = {
                "bare_name": bare_name,
                "count": len(msg_list),
                "mapping": [],
            }
            common_msgs = [m for m in msg_list if m["scope"] in ("common", "")]
            non_common_msgs = [m for m in msg_list if m["scope"] not in ("common", "")]

            # 非 common 作用域：改用作用域名 f"{scope}.{bare_name}"
            non_common_by_scope = defaultdict(list)
            for m in non_common_msgs:
                non_common_by_scope[m["scope"]].append(m)

            for sc, ms in sorted(non_common_by_scope.items()):
                for idx, m in enumerate(ms):
                    suffix = "" if idx == 0 else f"_{idx + 1}"
                    reg_name = f"{sc}.{bare_name}{suffix}"
                    m["registered_name"] = reg_name
                    conflict_info["mapping"].append(f"{m['file']} -> {reg_name}")
                    if idx > 0:
                        sys.stderr.write(
                            f"[WARN] 作用域相同仍冲突: {m['file']} {m['var']} -> {reg_name}\n"
                        )

            # common 作用域：先者保留裸名，后者追加 _2, _3
            for idx, m in enumerate(common_msgs):
                suffix = "" if idx == 0 else f"_{idx + 1}"
                reg_name = f"{bare_name}{suffix}"
                m["registered_name"] = reg_name
                conflict_info["mapping"].append(f"{m['file']} -> {reg_name}")
                if idx > 0:
                    sys.stderr.write(
                        f"[WARN] common作用域相同冲突: {m['file']} {m['var']} -> {reg_name}\n"
                    )

            conflicts_summary.append(conflict_info)

    # 注册表构建：{mod_name: {var: registered_name}}
    module_var_to_reg = defaultdict(dict)
    global_var_to_reg = {}
    registered_name_to_msg = {}

    for m in all_messages_raw:
        reg_name = m["registered_name"]
        module_var_to_reg[m["mod_name"]][m["var"]] = reg_name
        global_var_to_reg[m["var"]] = reg_name
        registered_name_to_msg[reg_name] = m

    # -----------------------------------------------------------------------
    # 第二遍：跨文件解引用并格式化字段
    # -----------------------------------------------------------------------
    messages_out = []
    group_field_count = 0
    total_fields_count = 0
    unresolved_ref_count = 0

    for m in all_messages_raw:
        if not m["_is_target"]:
            continue

        raw_fields = m["_fields_dict"]
        requires = m["_requires"]
        mod_name = m["mod_name"]
        fields_list = []

        for fvar, fattrs in raw_fields.items():
            if "number" not in fattrs or "name" not in fattrs:
                continue

            raw_num = fattrs["number"]
            try:
                field_num = int(raw_num)
            except ValueError:
                continue

            field_name = fattrs["name"].strip().strip('"').strip("'")
            raw_type = int(fattrs.get("type", 0))
            type_str = TYPE_MAP.get(raw_type, f"type_{raw_type}")

            if raw_type == 10:
                group_field_count += 1

            raw_label = int(fattrs.get("label", 1))
            label_str = LABEL_MAP.get(raw_label, "optional")

            ref_val = None
            if type_str == "message":
                mt_raw = fattrs.get("message_type", "")
                resolved = resolve_message_ref(
                    mt_raw, requires, mod_name, module_var_to_reg, global_var_to_reg
                )
                if resolved:
                    ref_val = resolved
                else:
                    unresolved_ref_count += 1
                    ref_val = mt_raw.strip().split(".")[-1].lower()

            field_obj = {
                "name": field_name,
                "number": field_num,
                "type": type_str,
                "label": label_str,
                "ref": ref_val,
            }
            fields_list.append(field_obj)
            total_fields_count += 1

        fields_list.sort(key=lambda f: f["number"])

        messages_out.append({
            "name": m["registered_name"],
            "fields": fields_list,
        })

    # messages 按注册名与字段编号排序（保证确定性）
    messages_out.sort(key=lambda item: (item["name"], tuple(f["number"] for f in item["fields"])))

    stats = {
        "total_messages": len(messages_out),
        "total_fields": total_fields_count,
        "group_field_count": group_field_count,
        "unresolved_ref_count": unresolved_ref_count,
        "cs_count": sum(1 for item in messages_out if item["name"].startswith("cs_")),
        "sc_count": sum(1 for item in messages_out if item["name"].startswith("sc_")),
        "conflicts": conflicts_summary,
    }
    return messages_out, stats


def run_selftest(proto_dir=None):
    """黄金样例与回归断言自测：

    1. p16_pb.lua 单文件黄金样例 (cs_16010 / sc_16011 逐字段吻合，item_net_rec 为 common 裸名不受影响)
    2. p38_pb.lua + p49_pb.lua 作用域消歧回归 (cs_38014.log_list ref=p38.log_net_rec，log_net_rec 为 3 字段战棋版)
    """
    if proto_dir is None:
        proto_dir = find_default_proto_dir()
    if not proto_dir or not os.path.isdir(proto_dir):
        raise FileNotFoundError(f"未找到 protocol 目录，请指定路径。搜索候选路径均无效。")

    p16_path = os.path.join(proto_dir, "p16_pb.lua")
    p38_path = os.path.join(proto_dir, "p38_pb.lua")
    p49_path = os.path.join(proto_dir, "p49_pb.lua")

    for p in (p16_path, p38_path, p49_path):
        if not os.path.exists(p):
            raise FileNotFoundError(f"自测文件不存在: {p}")

    # -----------------------------------------------------------------------
    # 测试断言 1: p16_pb 黄金样例
    # -----------------------------------------------------------------------
    messages_p16, _ = extract_proto_schema([p16_path])
    msg_map_p16 = {m["name"]: m for m in messages_p16}

    assert "cs_16010" in msg_map_p16, "缺少黄金样例 cs_16010"
    assert "sc_16011" in msg_map_p16, "缺少黄金样例 sc_16011"

    expected_cs_16010 = [
        {"name": "type", "number": 1, "type": "uint32", "label": "required", "ref": None},
        {"name": "pool", "number": 2, "type": "uint32", "label": "required", "ref": None},
        {"name": "cost", "number": 3, "type": "message", "label": "required", "ref": "item_net_rec"},
    ]
    actual_cs_16010 = msg_map_p16["cs_16010"]["fields"]
    assert actual_cs_16010 == expected_cs_16010, f"cs_16010 字段不匹配: 期望 {expected_cs_16010}, 实际 {actual_cs_16010}"

    expected_sc_16011 = [
        {"name": "result", "number": 1, "type": "uint32", "label": "required", "ref": None},
        {"name": "item", "number": 2, "type": "message", "label": "repeated", "ref": "item_net_rec"},
        {"name": "first_ssr_draw_flag", "number": 3, "type": "bool", "label": "optional", "ref": None},
        {"name": "newbie_choose_draw_flag", "number": 4, "type": "bool", "label": "optional", "ref": None},
        {"name": "ssr_draw_times", "number": 5, "type": "uint32", "label": "optional", "ref": None},
    ]
    actual_sc_16011 = msg_map_p16["sc_16011"]["fields"]
    assert actual_sc_16011 == expected_sc_16011, f"sc_16011 字段不匹配: 期望 {expected_sc_16011}, 实际 {actual_sc_16011}"

    # -----------------------------------------------------------------------
    # 测试断言 2: p38_pb + p49_pb 作用域消歧回归
    # -----------------------------------------------------------------------
    messages_conflict, _ = extract_proto_schema([p38_path, p49_path])
    msg_map_conflict = {m["name"]: m for m in messages_conflict}

    assert "cs_38014" in msg_map_conflict, "缺少 cs_38014 定义"
    cs_38014_fields = {f["name"]: f for f in msg_map_conflict["cs_38014"]["fields"]}
    assert "log_list" in cs_38014_fields, "cs_38014 缺少 log_list 字段"
    assert cs_38014_fields["log_list"]["ref"] == "p38.log_net_rec", (
        f"cs_38014.log_list ref 错误: 期望 p38.log_net_rec, 实际 {cs_38014_fields['log_list']['ref']}"
    )

    assert "p38.log_net_rec" in msg_map_conflict, "缺少作用域消息 p38.log_net_rec"
    p38_log_fields = [f["name"] for f in msg_map_conflict["p38.log_net_rec"]["fields"]]
    assert p38_log_fields == ["event_name", "attribute_json"], (
        f"p38.log_net_rec 字段错误: 期望 ['event_name', 'attribute_json'], 实际 {p38_log_fields}"
    )

    assert "log_net_rec" in msg_map_conflict, "缺少 common 裸名 log_net_rec"
    common_log_fields = [f["name"] for f in msg_map_conflict["log_net_rec"]["fields"]]
    assert common_log_fields == ["pos", "tag", "log"], (
        f"log_net_rec 字段错误: 期望 ['pos', 'tag', 'log'], 实际 {common_log_fields}"
    )

    print("[PASS] 黄金样例与作用域消歧自测全部通过:")
    print("  - cs_16010: 3 字段逐项吻合 (cost ref=item_net_rec 保持 common 裸名)")
    print("  - sc_16011: 5 字段逐项吻合 (item ref=item_net_rec)")
    print("  - cs_38014: log_list ref 为 p38.log_net_rec (作用域化引用)")
    print("  - p38.log_net_rec: 2 字段埋点版 (event_name, attribute_json) 独立存在")
    print("  - log_net_rec: 3 字段战棋版 (pos, tag, log) 保留 common 裸名")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="提取 protocol/*.lua 反编译代码中的 protobuf schema 生成 JSON 字典"
    )
    parser.add_argument(
        "protocol_dir",
        nargs="?",
        default=None,
        help="包含 *_pb.lua 文件的 protocol 目录路径",
    )
    parser.add_argument(
        "-o",
        "--out",
        default="v5_server/lua_proto_messages.json",
        help="输出 JSON 文件路径 (默认: v5_server/lua_proto_messages.json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行黄金样例与消歧自测断言",
    )

    args = parser.parse_args()

    if args.selftest:
        proto_dir = args.protocol_dir or find_default_proto_dir()
        try:
            run_selftest(proto_dir)
            sys.exit(0)
        except Exception as e:
            print(f"[FAIL] 自测失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

    proto_dir = args.protocol_dir or find_default_proto_dir()
    if not proto_dir:
        print("错误: 请提供 protocol 目录路径", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    print(f"[*] 扫描目录: {proto_dir}")
    messages, stats = extract_proto_schema(proto_dir)

    print(f"[*] 提取完成:")
    print(f"    消息总数: {stats['total_messages']}")
    print(f"    字段总数: {stats['total_fields']}")
    print(f"    cs_ 消息数: {stats['cs_count']}")
    print(f"    sc_ 消息数: {stats['sc_count']}")
    print(f"    group 字段数 (type=10): {stats['group_field_count']}")
    print(f"    未解析 ref 数: {stats['unresolved_ref_count']}")
    print(f"    同名冲突组数: {len(stats['conflicts'])}")

    if stats["conflicts"]:
        print(f"\n[*] 同名消息冲突消歧清单 (共 {len(stats['conflicts'])} 组):")
        for c in stats["conflicts"]:
            print(f"    - {c['bare_name']} ({c['count']} 处): {', '.join(c['mapping'])}")
        print()

    if stats["group_field_count"] > 0:
        print(f"[!] 警告: 发现 {stats['group_field_count']} 个 group 字段，decode_schema 不支持 group", file=sys.stderr)

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"messages": messages}, fh, ensure_ascii=False, indent=2)

    print(f"[+] 产物已写入: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
