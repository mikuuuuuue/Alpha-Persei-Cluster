# -*- coding: utf-8 -*-
"""client_itemcfg — 客户端物品 id 白名单（M1 整改 P1-2，2026-09-29）

背景（《M1-修复真实性排查报告.md》§六）：
  旧防护 CLIENT_FATAL_ITEM_IDS = {20, 21} 是 2 元素黑名单，同类崩溃路径仍然活着
  （DB item_catalog 9565 条中 1604 个 id 客户端不存在；充值奖励 2046、未领取邮件
  128403/6059、currency 表 20/21 均可走同一崩溃链：sc_17023 → ItemAction.AddItemData
  → 'attempt to index a nil value' → Lua 网络泵炸断）。

权威口径：
  data/client_itemcfg_ids.json = 客户端 ItemCfg.lua (4141) ∪ ItemCfg2.lua (3819) ∪ {0}
  共 7961 键（2026-09-29 独立复核两侧缺口为 0）。
  货币侧佐证：官方抓包 sc_15009 全部 41 个下发 id 100% 落在该集合内。

用法：
  from client_itemcfg import is_client_known_item
  if not is_client_known_item(iid): 拒发/跳过 + 告警

降级语义：数据文件缺失/损坏时退化为旧 2 元素黑名单（不阻断全部发货），并告警一次。
"""
import json
import os
import threading

_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "client_itemcfg_ids.json")
# 退化兜底（数据文件缺失时）：仅拦 2026-09-29 真机确诊的两个致命 id
_LEGACY_FATAL_IDS = frozenset({20, 21})
# 不在 ItemCfg 但允许下发的例外：
#   101 —— generator.gen_15009 的 _ZERO_SHOW 零值展示位（客户端货币栏清零显示用，
#           官方抓包从未携带，服务端以 num=0 下发）
_CURRENCY_EXTRA_IDS = frozenset({101})

_IDS = None            # None = 未加载；set = 已加载（空集表示文件存在但为空，视为异常）
_warned_fallback = False
_lock = threading.Lock()


def _load():
    global _IDS, _warned_fallback
    with _lock:
        if _IDS is not None:
            return
        try:
            with open(_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = {int(x) for x in data.get("ids") or []}
            if not ids:
                raise ValueError("ids 为空")
            _IDS = ids
        except Exception as e:
            _IDS = set()
            import logger
            logger.warning(
                f"[M-1防护] 客户端物品白名单加载失败({e})，退化为旧黑名单 "
                f"{sorted(_LEGACY_FATAL_IDS)}——请检查 {_DATA_PATH}")


def is_client_known_item(iid):
    """该物品 id 是否存在于客户端 ItemCfg（或登记过的展示位例外）。

    True  → 可安全入库/下发；
    False → 客户端不存在此 id，下发 sc_17023 会炸断 Lua 网络泵，必须拒发。
    """
    _load()
    if _IDS:
        return int(iid) in _IDS or int(iid) in _CURRENCY_EXTRA_IDS
    return int(iid) not in _LEGACY_FATAL_IDS


def dropped_unknown_ids(id_list):
    """从 iterable[int] 中筛出客户端不存在的 id（用于调用方告警/统计）。"""
    return [int(x) for x in id_list if not is_client_known_item(x)]
