#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/extract_hero_templates.py — sc_14009 → 展开模板提取器（M1.2 产物生成器）

核心算法：
  wire 直解，保字节无损，不依赖 schema。
  wire 0 → "v" (varint)
  wire 2 → 尝试嵌套解析，递归 encode_expanded 字节相等且 depth < 12 则 "m"，否则整段降级 "b" (hex)
  wire 1/5（fixed32/64）无法用 encode_expanded 表达：嵌套尝试自然降级父级 "b"；顶层直现 wire 1/5 则记录异常。

用法：
  python tools/extract_hero_templates.py <capture_path_or_dir> -o <output_dir>
  python tools/extract_hero_templates.py --cross-validate [--captures-root <captures_root>]
"""

import argparse
import copy
import json
import os
import sys
import zlib

# 引入 v5_server 模块
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_V5_SERVER = os.path.join(_REPO_ROOT, "v5_server")
if _V5_SERVER not in sys.path:
    sys.path.insert(0, _V5_SERVER)

import hero_codec


EXPECTED_HERO_IDS = [
    1011, 1012, 1013, 1015, 1016, 1017, 1019, 1020, 1021, 1022,
    1024, 1026, 1027, 1028, 1033, 1034, 1035, 1037, 1038, 1039,
    1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1052,
    1053, 1054, 1055, 1056, 1058, 1059, 1060, 1061, 1066, 1067,
    1068, 1070, 1071, 1073, 1074, 1075, 1076, 1077, 1080, 1083,
    1084, 1085, 1089, 1093, 1094, 1095, 1096, 1097, 1099, 1111,
    1119, 1133, 1137, 1138, 1139, 1148, 1150, 1156, 1158, 1166,
    1170, 1184, 1197, 1199, 1211, 1248, 1284
]


def parse_varint(data: bytes, pos: int):
    """从 data[pos] 读取 varint，返回 (value, new_pos)。"""
    res = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        res |= (b & 0x7F) << shift
        if not (b & 0x80):
            return res, pos
        shift += 7
    raise ValueError(f"Varint truncated at pos {pos}")


def extract_top_f1_chunks(data: bytes):
    """解析 sc_14009 解压字节流，收集所有 f1 (hero_net_rec) 原始字节块。"""
    pos = 0
    f1_list = []
    top_wire_types = {}
    while pos < len(data):
        tag, pos = parse_varint(data, pos)
        fn = tag >> 3
        wt = tag & 0x7
        if fn not in top_wire_types:
            top_wire_types[fn] = set()
        top_wire_types[fn].add(wt)

        if wt == 0:
            val, pos = parse_varint(data, pos)
        elif wt == 2:
            length, pos = parse_varint(data, pos)
            chunk = data[pos:pos + length]
            pos += length
            if fn == 1:
                f1_list.append(chunk)
        elif wt == 5:
            pos += 4
        elif wt == 1:
            pos += 8
        else:
            raise ValueError(f"Unknown wire type {wt} for top field {fn} at {pos}")

    return f1_list, top_wire_types


def wire_to_exp(chunk: bytes, depth: int = 0):
    """protobuf 字节 → 展开结构。

    wire 0 → "v"
    wire 2 → 先试嵌套解析，嵌套重编码字节相等且 depth < 12 则 "m"，否则整段降级 "b"(hex)。
    wire 1/5（fixed32/64）无法用 encode_expanded 表达——嵌套尝试会自然降级到父级 "b"；
    顶层直现 wire 1/5 则该英雄记入报告人工核查。
    """
    pos = 0
    items = []
    has_wire15 = False

    while pos < len(chunk):
        try:
            tag, new_pos = parse_varint(chunk, pos)
        except Exception:
            return None, False, False
        pos = new_pos
        fn = tag >> 3
        wt = tag & 0x7

        if fn == 0:
            return None, False, False

        if wt == 0:
            try:
                val, pos = parse_varint(chunk, pos)
            except Exception:
                return None, False, False
            items.append([fn, "v", val])
        elif wt == 2:
            try:
                length, pos = parse_varint(chunk, pos)
            except Exception:
                return None, False, False
            if pos + length > len(chunk):
                return None, False, False
            subchunk = chunk[pos:pos + length]
            pos += length

            # 尝试嵌套解析
            if depth < 12 and len(subchunk) > 0:
                sub_exp, sub_ok, _ = wire_to_exp(subchunk, depth + 1)
                if sub_ok:
                    try:
                        re_encoded = hero_codec.encode_expanded(sub_exp)
                        if re_encoded == subchunk:
                            items.append([fn, "m", sub_exp])
                            continue
                    except Exception:
                        pass

            # 降级到 "b" (hex)
            items.append([fn, "b", subchunk.hex()])
        elif wt in (1, 5):
            # wire 1/5 无法在展开结构中直接作为叶子表达
            has_wire15 = True
            if depth > 0:
                # 递归嵌套遇到 wire 1/5，整段退出让父级降级 "b"
                return None, False, True
            else:
                # 顶层遇到 wire 1/5
                pos += 8 if wt == 1 else 4
        else:
            return None, False, False

    if pos != len(chunk):
        return None, False, has_wire15

    return items, True, has_wire15


def extract_hero_id_from_exp(exp):
    """从展开结构获取 hero_id：hbi (f1) 内的 f1。"""
    for it in exp:
        if it[0] == 1 and it[1] == "m":
            hbi = it[2]
            for hit in hbi:
                if hit[0] == 1 and hit[1] == "v":
                    return hit[2]
    return None


def find_capture_file(path_str: str) -> str:
    """定位抓包文件，支持目录或文件路径，自动兼容 tcp_2/tcp_1 命名。"""
    if os.path.isfile(path_str):
        return path_str

    if os.path.isdir(path_str):
        rebuilt = os.path.join(path_str, "rebuilt")
        search_dirs = [rebuilt, path_str] if os.path.isdir(rebuilt) else [path_str]
        for sdir in search_dirs:
            for fname in ["tcp_2_down_8105.jsonl", "tcp_1_down_8105.jsonl"]:
                candidate = os.path.join(sdir, fname)
                if os.path.isfile(candidate):
                    return candidate
            for fname in os.listdir(sdir):
                if "down_8105" in fname and fname.endswith(".jsonl"):
                    return os.path.join(sdir, fname)

    # 路径不存在时检查同目录下其他候选
    dirname, _ = os.path.split(path_str)
    if os.path.isdir(dirname):
        for candidate in ["tcp_2_down_8105.jsonl", "tcp_1_down_8105.jsonl"]:
            p = os.path.join(dirname, candidate)
            if os.path.isfile(p):
                return p

    raise FileNotFoundError(f"找不到抓包文件: {path_str}")


def load_sc_14009_payload(file_path: str) -> bytes:
    """从 jsonl 文件读取 14009 帧 payload 并完成解压。"""
    actual_path = find_capture_file(file_path)
    with open(actual_path, "r", encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            cmd = obj.get("frame_cmd") or obj.get("cmd")
            if cmd == 14009:
                hex_data = obj.get("payload_hex") or obj.get("payload") or obj.get("data")
                raw = bytes.fromhex(hex_data)
                if raw.startswith(b"\x78\x9c") or raw.startswith(b"\x78\x01") or raw.startswith(b"\x78\xda"):
                    return zlib.decompress(raw)
                return raw
    raise RuntimeError(f"在 {actual_path} 中未找到 14009 帧")


def extract_hero_templates(capture_path: str, output_dir: str):
    """提取 77 角色模板并执行字节断言写入 output_dir。"""
    os.makedirs(output_dir, exist_ok=True)
    payload = load_sc_14009_payload(capture_path)
    f1_chunks, _ = extract_top_f1_chunks(payload)

    print(f"解析到 sc_14009 顶层 f1 条目数: {len(f1_chunks)}")
    if len(f1_chunks) != 77:
        raise RuntimeError(f"预期 77 个 f1 条目，实际提取到 {len(f1_chunks)} 个")

    passed = 0
    hero_records = []
    top_wire15_heroes = []

    for idx, chunk in enumerate(f1_chunks):
        exp, ok, has_wire15 = wire_to_exp(chunk, depth=0)
        if not ok:
            raise RuntimeError(f"条目 #{idx} wire_to_exp 解析失败")
        if has_wire15:
            top_wire15_heroes.append(idx)

        # 逐英雄字节级严格断言：hero_codec.encode_expanded(exp) == 原条目字节段
        encoded = hero_codec.encode_expanded(exp)
        if encoded != chunk:
            raise AssertionError(f"条目 #{idx} 编码字节与原条目不一致: len {len(encoded)} != {len(chunk)}")

        hid = extract_hero_id_from_exp(exp)
        if hid is None:
            raise RuntimeError(f"条目 #{idx} 无法提取 hero_id")

        filename = f"hero_{hid}.json"
        hero_records.append((hid, filename, exp, len(chunk)))
        passed += 1

    # 排序并校验 ID 列表
    extracted_ids = sorted([r[0] for r in hero_records])
    if extracted_ids != EXPECTED_HERO_IDS:
        raise RuntimeError(f"提取的英雄 ID 集合与预期 77 ID 不一致!\n实际: {extracted_ids}\n预期: {EXPECTED_HERO_IDS}")

    # 写入模板文件
    for hid, filename, exp, _ in hero_records:
        out_path = os.path.join(output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(exp, fh, indent=2, ensure_ascii=False)

    print(f"{passed}/{len(f1_chunks)} 字节级断言通过")
    print(f"模板文件已保存至: {output_dir} (共 {len(hero_records)} 个)")
    if top_wire15_heroes:
        print(f"警告：以下条目顶层包含 wire 1/5: {top_wire15_heroes}")

    return hero_records


DEFAULT_CAPTURES_ROOT = r"C:\Users\<user>\Desktop\Alpha-Persei-Captures"


def cross_validate(capture_paths=None, captures_root: str = DEFAULT_CAPTURES_ROOT):
    """三处 sc_14009 抓包交叉验证。"""
    if capture_paths is None:
        base = captures_root or DEFAULT_CAPTURES_ROOT
        capture_paths = [
            os.path.join(base, "2026-09-26_登录"),
            os.path.join(base, "2026-09-26_批量"),
            os.path.join(base, "2026-09-27_补抓2"),
        ]

    results = {}
    for p in capture_paths:
        label = os.path.basename(os.path.normpath(p))
        try:
            payload = load_sc_14009_payload(p)
            chunks, _ = extract_top_f1_chunks(payload)
            ids = []
            for c in chunks:
                exp, ok, _ = wire_to_exp(c, depth=0)
                if ok:
                    hid = extract_hero_id_from_exp(exp)
                    ids.append(hid)
            sorted_ids = sorted(ids)
            results[label] = {
                "payload_len": len(payload),
                "chunks_count": len(chunks),
                "ids": sorted_ids,
                "matches_expected": sorted_ids == EXPECTED_HERO_IDS,
            }
        except Exception as e:
            results[label] = {"error": str(e)}

    print("=== 三帧交叉验证结果 ===")
    all_match = True
    for label, res in results.items():
        if "error" in res:
            print(f"[{label}] 失败: {res['error']}")
            all_match = False
        else:
            match_str = "一致" if res["matches_expected"] else "不一致"
            print(f"[{label}] 载荷长度: {res['payload_len']}B, 英雄数: {len(res['ids'])}, 预期 77 ID 匹配: {match_str}")
            if not res["matches_expected"]:
                all_match = False

    if all_match:
        print("三帧 ID 集合完全一致（77 英雄，同一账号快照）。")
    else:
        print("警告：三帧 ID 集合存在差异！")

    return results


def main():
    parser = argparse.ArgumentParser(description="sc_14009 英雄模板提取器")
    parser.add_argument(
        "capture_path",
        nargs="?",
        default="",
        help="抓包目录或 rebuilt jsonl 文件路径（可为登录场景目录，或包含各场景的抓包根目录）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join(_V5_SERVER, "角色挖掘"),
        help="模板输出目录（默认: v5_server/角色挖掘）",
    )
    parser.add_argument(
        "--captures-root",
        default=DEFAULT_CAPTURES_ROOT,
        help=f"抓包根目录（默认: %(default)s），用于交叉验证与默认主提取使用",
    )
    parser.add_argument(
        "--cross-validate",
        action="store_true",
        help="对三处抓包（登录、批量、补抓2）执行交叉验证",
    )

    args = parser.parse_args()

    captures_root = args.captures_root
    target_capture = args.capture_path

    # 若传入的 capture_path 是包含子场景的根目录，则自动共用为 captures_root 并定位登录场景
    if target_capture and os.path.isdir(target_capture):
        login_subdir = os.path.join(target_capture, "2026-09-26_登录")
        if os.path.isdir(login_subdir):
            if args.captures_root == DEFAULT_CAPTURES_ROOT:
                captures_root = target_capture
            target_capture = login_subdir
    elif target_capture:
        # 若指定了具体子场景路径，尝试推断其上级目录是否为抓包根目录（供交叉验证使用）
        curr = os.path.abspath(target_capture)
        for _ in range(3):
            curr = os.path.dirname(curr)
            if os.path.isdir(os.path.join(curr, "2026-09-26_批量")):
                if args.captures_root == DEFAULT_CAPTURES_ROOT:
                    captures_root = curr
                break

    if args.cross_validate or not args.capture_path:
        cross_validate(captures_root=captures_root)
        if not args.capture_path:
            return

    extract_hero_templates(target_capture, args.output)


if __name__ == "__main__":
    main()
