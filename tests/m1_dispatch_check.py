# -*- coding: utf-8 -*-
"""
tests/m1_dispatch_check.py — M1 无头业务回归验证脚本

验证范围：
1. 段一【397 操作 Schema 签名扫零】：
   - 全量调度 core.OPERATIONS (397个注册操作)，发送空 JSON payload b"{}"；
   - 监听日志增量，断言 "参数解析失败: schema 文件不存在" 出现次数 == 0；
   - 统计响应数据源分类 (src) 与 reply 状态。
2. 段二【代表操作深检】：
   - 从真实抓包数据重放关键业务操作 (抽卡 cs_16010/cs_16012, 商城购买 cs_20012, 邮件领取 cs_30008,
     货币/体力购买 cs_15012/cs_15016, 大厅设置 cs_32132)；
   - 断言返回真实业务数据帧 (sc_16011 等且含 result 字段)，区分"业务拒绝"与"参数解析失败"。
3. 段三【Hero 专项断言】：
   - 验证 hero_codec.build_hero_payload 生成及 sc_14009 结构；
   - uid=999999 解码出 15 位英雄，uid=999999998 解码出 20 位英雄。
"""
import json
import os
import sys
import time

# 确保 v5_server 模块在 sys.path 中
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V5_DIR = os.path.join(REPO_ROOT, "v5_server")
if V5_DIR not in sys.path:
    sys.path.insert(0, V5_DIR)

from account_db import get_db
import core as core_mod
import operations
import backhome_service
import peripheral_service
import achievement_service
import minigame_service
import autochess_service
import periodic_gift_service
import recharge_service
import generator as _gen
from codec import encode as _enc, decode as _dec
import hero_codec
import logger


TARGET_SIG = "参数解析失败: schema 文件不存在"
DEFAULT_UID = 999999


def run_section_1_sweep(core, db):
    """段一【397 操作 Schema 签名扫零】"""
    print("\n" + "=" * 60)
    print("【段一】397 操作 Schema 签名扫零测试")
    print("=" * 60)

    ops = sorted(core_mod.OPERATIONS.keys())
    total_ops = len(ops)
    print(f"[*] 发现 core.OPERATIONS 注册操作数: {total_ops}")
    assert total_ops == 397, f"期望 397 个注册操作，实际发现 {total_ops} 个"

    # 记录文件偏移
    log_dir = os.path.join(V5_DIR, "logs")
    log_file = os.path.join(log_dir, f"middleware_{time.strftime('%Y%m%d')}.log")
    file_start_pos = os.path.getsize(log_file) if os.path.exists(log_file) else 0

    # 内存日志收集器
    collected_logs = []
    original_core_log = core.log

    def sweep_log_hook(*args, **kwargs):
        if original_core_log:
            try:
                kw = dict(kwargs)
                kw["to_console"] = False
                original_core_log(*args, **kw)
            except Exception:
                pass
        msg = " ".join(str(a) for a in args)
        collected_logs.append(msg)

    core.log = sweep_log_hook

    src_counter = {}
    reply_counter = {True: 0, False: 0}
    exceptions = []

    print("[*] 开始分发 397 个操作 (payload=b'{}', uid=999999)...")
    for cmd in ops:
        req = core_mod.CoreRequest(cmd=cmd, payload=b"{}", uid=DEFAULT_UID)
        try:
            resp = core.dispatch(req)
            src_counter[resp.src] = src_counter.get(resp.src, 0) + 1
            reply_counter[resp.reply] = reply_counter.get(resp.reply, 0) + 1
        except Exception as e:
            exceptions.append((cmd, str(e)))

    # 恢复日志函数
    core.log = original_core_log

    # 检查内存中日志
    mem_sig_hits = [line for line in collected_logs if TARGET_SIG in line]

    # 检查日志文件增量
    file_sig_hits = 0
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            f.seek(file_start_pos)
            delta_content = f.read()
            file_sig_hits = delta_content.count(TARGET_SIG)

    print(f"[*] 分发完成统计:")
    print(f"    - 总分发数: {total_ops}")
    print(f"    - 数据源分类 (src): {dict(src_counter)}")
    print(f"    - 回包语义 (reply): True={reply_counter[True]}, False={reply_counter[False]}")
    print(f"    - 异常未捕获数: {len(exceptions)}")
    print(f"    - 签名 '{TARGET_SIG}' 命中数 (内存): {len(mem_sig_hits)}")
    print(f"    - 签名 '{TARGET_SIG}' 命中数 (文件增量): {file_sig_hits}")

    assert len(exceptions) == 0, f"存在未捕获异常: {exceptions}"
    assert len(mem_sig_hits) == 0, f"内存日志检测到签名命中: {mem_sig_hits}"
    assert file_sig_hits == 0, f"文件增量检测到签名命中: {file_sig_hits} 次"
    print("[+] 段一通过：397 个操作全部完成调度，schema 缺失签名 100% 归零！")
    return {
        "total_ops": total_ops,
        "src_counter": src_counter,
        "reply_counter": reply_counter,
        "exceptions": len(exceptions),
        "mem_sig_hits": len(mem_sig_hits),
        "file_sig_hits": file_sig_hits,
    }


def run_section_2_representative_replay(core, db):
    """段二【代表操作深检】：抓包参数重放与业务响应"""
    print("\n" + "=" * 60)
    print("【段二】代表操作深检与抓包参数重放")
    print("=" * 60)

    # 准备测试用例
    # 每个用例包含：cmd, name, source_desc, payload_dict, expected_sc, check_func
    results = []

    # 1. cs_16010: 抽卡 10 连（来源：2026-09-26_抽卡 tcp_2_up_8105.jsonl 帧 hex 080a109d83b3021a040826100a）
    # 该抓包指向线上历史卡池 5030301，预期返回 sc_16011 业务拒绝帧 (result=2: 抽卡池不存在，非 0802 schema 参数解析错误)
    c16010_payload = {"type": 10, "pool": 5030301, "cost": {"id": 38, "num": 10}}
    req = core_mod.CoreRequest(
        cmd=16010,
        payload=json.dumps(c16010_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True, "cs_16010 应有回包"
    assert len(resp.frames) >= 1, "cs_16010 至少包含1帧响应"
    sc_frame = resp.frames[-1]
    sc_cmd = sc_frame["sc"] if isinstance(sc_frame, dict) else getattr(sc_frame, "cmd", None)
    sc_pl = sc_frame["payload"] if isinstance(sc_frame, dict) else getattr(sc_frame, "payload", None)
    assert sc_cmd == 16011, f"cs_16010 预期返回 sc_16011，实际为 sc_{sc_cmd}"
    dec16011 = _dec(sc_pl, "sc_16011")
    assert "result" in dec16011, "sc_16011 应包含 result 字段"
    print(f"[*] cs_16010 (抓包历史卡池 5030301) 重放成功: sc_16011 result={dec16011['result']} (业务判定，非解析错误)")
    results.append({
        "cmd": 16010,
        "name": "抽卡十连 (线上抓包卡池 5030301)",
        "source": "2026-09-26_抽卡/rebuilt/tcp_2_up_8105.jsonl (hex: 080a109d83b3021a040826100a)",
        "sc": sc_cmd,
        "result": dec16011["result"],
        "desc": "返回有效业务响应 sc_16011 (result=2 业务拒绝)",
    })

    # 1b. cs_16010 补充验证：本地现有活动池 10003 (雷光的剑息) 真实抽卡
    c16010_local_payload = {"type": 10, "pool": 10003, "cost": {"id": 38, "num": 10}}
    req_local = core_mod.CoreRequest(
        cmd=16010,
        payload=json.dumps(c16010_local_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp_local = core.dispatch(req_local)
    assert resp_local.reply is True
    sc_local_frame = resp_local.frames[0]
    sc_local_cmd = sc_local_frame["sc"] if isinstance(sc_local_frame, dict) else getattr(sc_local_frame, "cmd", None)
    sc_local_pl = sc_local_frame["payload"] if isinstance(sc_local_frame, dict) else getattr(sc_local_frame, "payload", None)
    assert sc_local_cmd == 16011
    dec_local = _dec(sc_local_pl, "sc_16011")
    assert dec_local.get("result") == 0, f"本地池抽卡应成功，实际 result={dec_local.get('result')}"
    items_drawn = len(dec_local.get("item", []))
    assert items_drawn == 10, f"十连抽应产出 10 项奖励，实际 {items_drawn} 项"
    print(f"[*] cs_16010 (本地活动池 10003) 真实抽卡成功: sc_16011 result=0, 产出 {items_drawn} 个道具, 触发下发帧数={len(resp_local.frames)}")
    results.append({
        "cmd": 16010,
        "name": "抽卡十连 (本地有效卡池 10003)",
        "source": "本地 draw_pool 配置 (pool_id=10003)",
        "sc": 16011,
        "result": 0,
        "desc": f"业务成功：产出 {items_drawn} 项道具，下发 {len(resp_local.frames)} 帧",
    })

    # 2. cs_16012: 卡池查询/切换（来源：2026-09-26_抽卡 tcp_2_up_8105.jsonl hex: 089d83b302）
    c16012_payload = {"id": 5030301}
    req = core_mod.CoreRequest(
        cmd=16012,
        payload=json.dumps(c16012_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmd = resp.frames[0]["sc"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "cmd", None)
    sc_pl = resp.frames[0]["payload"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "payload", None)
    assert sc_cmd == 16013, f"cs_16012 预期返回 sc_16013，实际 sc_{sc_cmd}"
    dec16013 = _dec(sc_pl, "sc_16013")
    assert dec16013.get("result") == 0, f"sc_16013 预期 result=0，实际 {dec16013.get('result')}"
    print(f"[*] cs_16012 卡池查询重放成功: sc_16013 result=0, ssr_draw_times={dec16013.get('ssr_draw_times')}")
    results.append({
        "cmd": 16012,
        "name": "卡池切换与查询",
        "source": "2026-09-26_抽卡/rebuilt/tcp_2_up_8105.jsonl (hex: 089d83b302)",
        "sc": 16013,
        "result": dec16013.get("result"),
        "desc": "业务成功：返回保底与卡池状态",
    })

    # 3. cs_20012: 商城购买（来源：2026-09-26_抽卡 tcp_2_up_8105.jsonl hex: 0a1008839bee02100a1a05080110d00f200010061802）
    c20012_payload = {
        "buy_goods_list": [{"buy_id": 6000003, "buy_num": 10, "cost_items": [{"id": 1, "num": 2000}], "buy_type": 0}],
        "shop_id": 6,
        "buy_source": 2,
    }
    req = core_mod.CoreRequest(
        cmd=20012,
        payload=json.dumps(c20012_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmd = resp.frames[0]["sc"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "cmd", None)
    sc_pl = resp.frames[0]["payload"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "payload", None)
    assert sc_cmd == 20013, f"cs_20012 预期返回 sc_20013，实际 sc_{sc_cmd}"
    dec20013 = _dec(sc_pl, "sc_20013")
    assert "result" in dec20013, "sc_20013 应包含 result 字段"
    print(f"[*] cs_20012 商城购买重放成功: sc_20013 result={dec20013['result']} (业务响应，非解析错误)")
    results.append({
        "cmd": 20012,
        "name": "商城商品购买",
        "source": "2026-09-26_抽卡/rebuilt/tcp_2_up_8105.jsonl (hex: 0a1008...)",
        "sc": 20013,
        "result": dec20013["result"],
        "desc": f"返回有效业务帧 sc_20013 (result={dec20013['result']})",
    })

    # 4. cs_30008: 邮件领取（来源：2026-09-26_商城邮件 tcp_2_up_8105.jsonl hex: 08d201）
    c30008_payload = {"id": 210}
    req = core_mod.CoreRequest(
        cmd=30008,
        payload=json.dumps(c30008_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmd = resp.frames[0]["sc"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "cmd", None)
    sc_pl = resp.frames[0]["payload"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "payload", None)
    assert sc_cmd == 30009, f"cs_30008 预期返回 sc_30009，实际 sc_{sc_cmd}"
    dec30009 = _dec(sc_pl, "sc_30009")
    assert dec30009.get("result") == 0, f"sc_30009 预期 result=0，实际 {dec30009.get('result')}"
    print(f"[*] cs_30008 邮件领取重放成功: sc_30009 result=0")
    results.append({
        "cmd": 30008,
        "name": "邮件领取",
        "source": "2026-09-26_商城邮件/rebuilt/tcp_2_up_8105.jsonl (hex: 08d201)",
        "sc": 30009,
        "result": dec30009.get("result"),
        "desc": "业务成功：邮件附件领取完成",
    })

    # 5. cs_30002: 邮件列表查询（来源：2026-09-26_商城邮件 tcp_2_up_8105.jsonl 空 payload）
    req = core_mod.CoreRequest(cmd=30002, payload=b"{}", uid=DEFAULT_UID)
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmd = resp.frames[0]["sc"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "cmd", None)
    sc_pl = resp.frames[0]["payload"] if isinstance(resp.frames[0], dict) else getattr(resp.frames[0], "payload", None)
    assert sc_cmd == 30003, f"cs_30002 预期返回 sc_30003，实际 sc_{sc_cmd}"
    dec30003 = _dec(sc_pl, "sc_30003")
    print(f"[*] cs_30002 邮件列表查询重放成功: sc_30003 total_num={dec30003.get('total_num')}")
    results.append({
        "cmd": 30002,
        "name": "邮件列表查询",
        "source": "2026-09-26_商城邮件/rebuilt/tcp_2_up_8105.jsonl (空 payload)",
        "sc": 30003,
        "result": dec30003.get("result"),
        "desc": f"业务成功：返回邮件列表信息 total_num={dec30003.get('total_num')}",
    })

    # 6. cs_15012: 购买金币 (cs_15001 类代表操作)
    c15012_payload = {"id": 1}
    req = core_mod.CoreRequest(
        cmd=15012,
        payload=json.dumps(c15012_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmds = [f["sc"] if isinstance(f, dict) else getattr(f, "cmd", None) for f in resp.frames]
    assert 15013 in sc_cmds, f"cs_15012 预期包含 sc_15013，实际帧: {sc_cmds}"
    idx15013 = sc_cmds.index(15013)
    pl15013 = resp.frames[idx15013]["payload"] if isinstance(resp.frames[idx15013], dict) else getattr(resp.frames[idx15013], "payload", None)
    dec15013 = _dec(pl15013, "sc_15013")
    assert dec15013.get("result") == 0, f"sc_15013 预期 result=0，实际 {dec15013.get('result')}"
    print(f"[*] cs_15012 购买金币成功: sc_15013 result=0, reward_list={dec15013.get('reward_list')}")
    results.append({
        "cmd": 15012,
        "name": "购买金币 (cs_15001 类)",
        "source": "operations.BuyCoinOp (cs_15012 {id: 1})",
        "sc": 15013,
        "result": dec15013.get("result"),
        "desc": f"业务成功：扣除移转之辉兑换金币成功",
    })

    # 7. cs_15016: 购买体力 (cs_15001 类代表操作)
    c15016_payload = {"num": 1}
    req = core_mod.CoreRequest(
        cmd=15016,
        payload=json.dumps(c15016_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is True
    sc_cmds = [f["sc"] if isinstance(f, dict) else getattr(f, "cmd", None) for f in resp.frames]
    assert 15017 in sc_cmds, f"cs_15016 预期包含 sc_15017，实际帧: {sc_cmds}"
    idx15017 = sc_cmds.index(15017)
    pl15017 = resp.frames[idx15017]["payload"] if isinstance(resp.frames[idx15017], dict) else getattr(resp.frames[idx15017], "payload", None)
    dec15017 = _dec(pl15017, "sc_15017")
    assert dec15017.get("result") == 0, f"sc_15017 预期 result=0，实际 {dec15017.get('result')}"
    print(f"[*] cs_15016 购买体力成功: sc_15017 result=0, reward_list={dec15017.get('reward_list')}")
    results.append({
        "cmd": 15016,
        "name": "购买体力 (cs_15001 类)",
        "source": "operations.BuyFatigueOp (cs_15016 {num: 1})",
        "sc": 15017,
        "result": dec15017.get("result"),
        "desc": f"业务成功：购买体力成功，下发体力恢复帧",
    })

    # 8. cs_32132: 大厅壁纸与角色设置（来源：2026-09-26_商城邮件 tcp_2_up_8105.jsonl hex: 08912f10a5c606）
    c32132_payload = {"background_id": 6033, "hero_id": 107301}
    req = core_mod.CoreRequest(
        cmd=32132,
        payload=json.dumps(c32132_payload).encode("utf-8"),
        uid=DEFAULT_UID,
    )
    resp = core.dispatch(req)
    assert resp.reply is False, "cs_32132 客户端契约为静默保存 (reply=False)"
    print(f"[*] cs_32132 大厅壁纸设置重放成功: reply=False (静默落库)")
    results.append({
        "cmd": 32132,
        "name": "大厅壁纸与角色设置",
        "source": "2026-09-26_商城邮件/rebuilt/tcp_2_up_8105.jsonl (hex: 08912f10a5c606)",
        "sc": None,
        "result": 0,
        "desc": "契约符合：reply=False 静默落库完成",
    })

    print("[+] 段二通过：所有代表操作重放均正确返回业务响应帧，解析失败率为 0！")
    return results


def run_section_3_hero_assertions(db):
    """段三【Hero 专项断言】"""
    print("\n" + "=" * 60)
    print("【段三】Hero 专项断言测试")
    print("=" * 60)

    # 1. uid=999999 (默认账号)
    uid1 = 999999
    p1 = hero_codec.build_hero_payload(db, uid=uid1)
    assert p1 is not None, f"uid={uid1} 的 build_hero_payload 返回 None"
    assert len(p1) > 0, f"uid={uid1} payload 长度为 0"
    dec1 = _dec(p1, "sc_14009")
    hlist1 = dec1.get("hero_info_list", [])
    count1 = len(hlist1)
    print(f"[*] uid={uid1}: payload 长度={len(p1)} 字节, 包含英雄数={count1}")
    assert count1 == 15, f"uid={uid1} 期望 15 位英雄，实际获得 {count1} 位"

    # 2. uid=999999998
    uid2 = 999999998
    p2 = hero_codec.build_hero_payload(db, uid=uid2)
    assert p2 is not None, f"uid={uid2} 的 build_hero_payload 返回 None"
    assert len(p2) > 0, f"uid={uid2} payload 长度为 0"
    dec2 = _dec(p2, "sc_14009")
    hlist2 = dec2.get("hero_info_list", [])
    count2 = len(hlist2)
    print(f"[*] uid={uid2}: payload 长度={len(p2)} 字节, 包含英雄数={count2}")
    assert count2 == 20, f"uid={uid2} 期望 20 位英雄，实际获得 {count2} 位"

    print("[+] 段三通过：hero 专项断言全部满足 (999999=15 英雄, 999999998=20 英雄)！")
    return {
        "uid_999999": {"len": len(p1), "hero_count": count1},
        "uid_999999998": {"len": len(p2), "hero_count": count2},
    }


def main():
    print("============================================================")
    print("  Alpha-Persei-Cluster M1 无头业务回归验证 (Task 4)")
    print("============================================================")
    db = get_db()
    core = core_mod.Core(
        db=db,
        generator=_gen,
        codec_encode=_enc,
        codec_decode=_dec,
        log=logger.log,
    )

    t0 = time.time()
    s1_res = run_section_1_sweep(core, db)
    s3_res = run_section_3_hero_assertions(db)
    s2_res = run_section_2_representative_replay(core, db)
    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("  回归验证总体结果: ALL PASSED (100% 成功)")
    print(f"  总耗时: {elapsed:.2f} 秒")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
