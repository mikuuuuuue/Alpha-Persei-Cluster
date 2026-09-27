#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/extract_proto_schema.py — 反编译 *_pb.lua → lua_proto_messages.json（M1.1 产物生成器）

用法：
  python tools/extract_proto_schema.py <protocol目录> -o <输出.json>
  python tools/extract_proto_schema.py --selftest   # 黄金样例断言（内置 cs_16010/sc_16011）
"""

import argparse
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


def parse_file_raw(filepath):
    """解析单个 *_pb.lua 文件的 raw AST/token 结构（第一遍扫描）。

    返回：
      mod_name: 模块文件名（无后缀，如 p16_pb）
      requires: {slotN: module_name}
      var_to_msg_name: {MSG_VAR: msg_name_normalized}
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

    var_to_msg_name = {}
    for mm in MSG_NAME_PAT.finditer(text):
        var_name, raw_name = mm.group(1), mm.group(2)
        norm_name = raw_name.strip().lstrip(".").lower()
        var_to_msg_name[var_name] = norm_name

    msg_fields = {mvar: {} for mvar in var_to_msg_name}
    for fm in FIELD_ATTR_PAT.finditer(text):
        mvar, fvar, attr, val = fm.group(1), fm.group(2), fm.group(3), fm.group(4).strip()
        if mvar not in msg_fields:
            msg_fields[mvar] = {}
        if fvar not in msg_fields[mvar]:
            msg_fields[mvar][fvar] = {}
        msg_fields[mvar][fvar][attr] = val

    return mod_name, requires, var_to_msg_name, msg_fields


def resolve_message_ref(val, requires, current_var_to_name, module_registry, global_msg_registry):
    """解析 message_type 赋值表达式右侧的目标消息名。"""
    val = val.strip()

    # 形态 1: slot1.ITEM_NET_REC
    m1 = re.match(r"^(slot\d+)\.([A-Za-z0-9_]+)$", val)
    if m1:
        slot, var = m1.group(1), m1.group(2)
        target_mod = requires.get(slot)
        if target_mod and target_mod in module_registry:
            target_name = module_registry[target_mod].get(var)
            if target_name:
                return target_name

    # 形态 2: require("protocol/xxx_pb").VAR_NAME
    m2 = re.match(r"^require\([\"']protocol/([^\"']+)[\"']\)\.([A-Za-z0-9_]+)$", val)
    if m2:
        req_mod = m2.group(1).split("/")[-1]
        var = m2.group(2)
        if req_mod in module_registry:
            target_name = module_registry[req_mod].get(var)
            if target_name:
                return target_name

    # 形态 3: VAR_NAME（同文件裸名或全局名）
    m3 = re.match(r"^([A-Za-z0-9_]+)$", val)
    if m3:
        var = m3.group(1)
        if var in current_var_to_name:
            return current_var_to_name[var]
        if var in global_msg_registry:
            return global_msg_registry[var]

    return None


def extract_proto_schema(proto_dir_or_files):
    """两遍扫描提取 protocol 目录下所有消息定义。

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

    # 第一遍：收集所有文件定义并构建注册表
    file_records = []
    module_registry = {}      # {mod_name: {var_name: msg_name}}
    global_msg_registry = {}  # {var_name: msg_name}

    for fpath in file_paths:
        mod_name, requires, var_to_name, msg_fields = parse_file_raw(fpath)
        module_registry[mod_name] = var_to_name
        for v, n in var_to_name.items():
            global_msg_registry[v] = n
        file_records.append((fpath, mod_name, requires, var_to_name, msg_fields))

    # 若为单文件或部分文件提取，自动加载依赖模块以支持跨文件解引用
    loaded_mods = set(module_registry.keys())
    for fpath, mod_name, requires, var_to_name, msg_fields in file_records:
        proto_dir = os.path.dirname(os.path.abspath(fpath))
        for slot, req_mod in requires.items():
            if req_mod not in loaded_mods and req_mod != "protobuf":
                candidate = os.path.join(proto_dir, f"{req_mod}.lua")
                if os.path.exists(candidate):
                    dep_mod, _, dep_var_to_name, _ = parse_file_raw(candidate)
                    module_registry[dep_mod] = dep_var_to_name
                    for v, n in dep_var_to_name.items():
                        global_msg_registry.setdefault(v, n)
                    loaded_mods.add(dep_mod)

    # 第二遍：跨文件解引用并格式化字段
    messages = []
    group_field_count = 0
    total_fields_count = 0
    unresolved_ref_count = 0

    for fpath, mod_name, requires, var_to_name, msg_fields in file_records:
        for mvar, norm_msg_name in var_to_name.items():
            raw_fields = msg_fields.get(mvar, {})
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
                        mt_raw, requires, var_to_name, module_registry, global_msg_registry
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

            # fields 按 number 升序
            fields_list.sort(key=lambda f: f["number"])

            messages.append({
                "name": norm_msg_name,
                "fields": fields_list,
            })

    # messages 按名字排序（产物确定性，便于 diff 复跑）
    messages.sort(key=lambda m: (m["name"], tuple(f["number"] for f in m["fields"])))

    stats = {
        "total_messages": len(messages),
        "total_fields": total_fields_count,
        "group_field_count": group_field_count,
        "unresolved_ref_count": unresolved_ref_count,
        "cs_count": sum(1 for m in messages if m["name"].startswith("cs_")),
        "sc_count": sum(1 for m in messages if m["name"].startswith("sc_")),
    }
    return messages, stats


def run_selftest(proto_dir=None):
    """黄金样例自测：对 p16_pb.lua 单文件运行提取，断言 cs_16010 与 sc_16011 逐字段一致。"""
    if proto_dir is None:
        proto_dir = find_default_proto_dir()
    if not proto_dir or not os.path.isdir(proto_dir):
        raise FileNotFoundError(f"未找到 protocol 目录，请指定路径。搜索候选路径均无效。")

    p16_path = os.path.join(proto_dir, "p16_pb.lua")
    if not os.path.exists(p16_path):
        raise FileNotFoundError(f"自测文件不存在: {p16_path}")

    # 对 p16_pb.lua 单文件运行提取（依赖模块如 item_hrl_pb 自动跨文件解引用）
    messages, stats = extract_proto_schema([p16_path])
    msg_map = {m["name"]: m for m in messages}

    assert "cs_16010" in msg_map, "缺少黄金样例 cs_16010"
    assert "sc_16011" in msg_map, "缺少黄金样例 sc_16011"

    # 黄金样例 1: cs_16010
    # f1: type uint32 required ref=None
    # f2: pool uint32 required ref=None
    # f3: cost message required ref=item_net_rec
    expected_cs_16010 = [
        {"name": "type", "number": 1, "type": "uint32", "label": "required", "ref": None},
        {"name": "pool", "number": 2, "type": "uint32", "label": "required", "ref": None},
        {"name": "cost", "number": 3, "type": "message", "label": "required", "ref": "item_net_rec"},
    ]
    actual_cs_16010 = msg_map["cs_16010"]["fields"]
    assert actual_cs_16010 == expected_cs_16010, f"cs_16010 字段不匹配: 期望 {expected_cs_16010}, 实际 {actual_cs_16010}"

    # 黄金样例 2: sc_16011
    # f1: result uint32 required ref=None
    # f2: item message repeated ref=item_net_rec
    # f3: first_ssr_draw_flag bool optional ref=None
    # f4: newbie_choose_draw_flag bool optional ref=None
    # f5: ssr_draw_times uint32 optional ref=None
    expected_sc_16011 = [
        {"name": "result", "number": 1, "type": "uint32", "label": "required", "ref": None},
        {"name": "item", "number": 2, "type": "message", "label": "repeated", "ref": "item_net_rec"},
        {"name": "first_ssr_draw_flag", "number": 3, "type": "bool", "label": "optional", "ref": None},
        {"name": "newbie_choose_draw_flag", "number": 4, "type": "bool", "label": "optional", "ref": None},
        {"name": "ssr_draw_times", "number": 5, "type": "uint32", "label": "optional", "ref": None},
    ]
    actual_sc_16011 = msg_map["sc_16011"]["fields"]
    assert actual_sc_16011 == expected_sc_16011, f"sc_16011 字段不匹配: 期望 {expected_sc_16011}, 实际 {actual_sc_16011}"

    print("[PASS] 黄金样例自测全部通过:")
    print("  - cs_16010: 3 字段逐项吻合 (type/pool/cost ref=item_net_rec)")
    print("  - sc_16011: 5 字段逐项吻合 (result/item ref=item_net_rec/first_ssr_draw_flag/newbie_choose_draw_flag/ssr_draw_times)")
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
        help="运行黄金样例 (cs_16010, sc_16011) 自测断言",
    )

    args = parser.parse_args()

    if args.selftest:
        proto_dir = args.protocol_dir or find_default_proto_dir()
        try:
            run_selftest(proto_dir)
            sys.exit(0)
        except Exception as e:
            print(f"[FAIL] 自测失败: {e}", file=sys.stderr)
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

    if stats["group_field_count"] > 0:
        print(f"[!] 警告: 发现 {stats['group_field_count']} 个 group 字段，decode_schema 不支持 group", file=sys.stderr)

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"messages": messages}, fh, ensure_ascii=False, indent=2)

    print(f"[+] 产物已写入: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
