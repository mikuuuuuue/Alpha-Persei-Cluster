#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gen_voice_treadmill.py — 语音零差异跑步机模板再生成工具

背景（M1 Task 6 / U16 路径②，2026-09-28 根因确诊）：
321 客户端语音更新链存在两处死锁——①diff 非空时 WaitConfirm 确认弹窗在
启动环屏阶段无法渲染；②完全无工作时 DownloadHaseNode/VoiceDiffNode 空转
永不完成。对策 = 服务端(cdn_proxy.py 语音跑步机)恒定下发"与客户端本地磁盘
100% 一致的修剪清单"，让客户端走"版本差→下载清单→diff=空→跳过确认→完成"
的官方稳态路径。

本工具把"官方清单 ∩ 客户端本地磁盘真值"固化为模板：
    v5_server/cdn_cache/pc/voice_hash_zh_30701000.bytes
（cdn_proxy 惰性加载该模板并按请求改写 version 字段合成任意跑步机版本。）

何时需要重跑：cdn_cache 被清空 / 客户端语音文件集发生变化（如日后补齐了
缺失的 story_v_side_new_* 文件）。

用法: python tools/gen_voice_treadmill.py
"""
import json
import os
import sys

CLIENT_VOICE_ZH = (r"C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili"
                   r"\AetherGazer_Bili_Data\StreamingAssets\Voice\zh")
BASE_MANIFEST = "voice_hash_zh_30700321.bytes"   # 官方 321 zh 清单（客户端已装）
TREADMILL_BASE_VERSION = 30701000
OUTPUT = None  # 默认写入仓库 v5_server/cdn_cache/pc/


def main():
    src = os.path.join(CLIENT_VOICE_ZH, BASE_MANIFEST)
    if not os.path.isfile(src):
        sys.exit(f"[ERR] 找不到官方基准清单: {src}")
    with open(src, "r", encoding="utf-8") as f:
        m = json.load(f)

    total, keep = len(m["assetHashList"]), []
    dropped = []
    for e in m["assetHashList"]:
        name, h, _sz = e.split("|")
        if os.path.isfile(os.path.join(CLIENT_VOICE_ZH, h[0], h[1], h + ".ys")):
            keep.append(e)
        else:
            dropped.append(name)

    out_path = OUTPUT or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "v5_server", "cdn_cache", "pc",
        "voice_hash_zh_%d.bytes" % TREADMILL_BASE_VERSION)
    manifest = {"versionName": "zh", "version": TREADMILL_BASE_VERSION,
                "size": m["size"], "assetHashList": keep}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))

    # 终检：模板条目必须全部对得上盘（零差异的前提）
    bad = sum(1 for e in keep
              if not os.path.isfile(os.path.join(
                  CLIENT_VOICE_ZH, *(p := e.split("|"))[1][0], p[1][1], p[1] + ".ys")))
    print(f"官方条目 {total} → 保留 {len(keep)}（剔除本地缺失 {len(dropped)} 个）")
    print(f"剔除示例: {dropped[:3]}")
    print(f"模板已写入: {out_path} ({os.path.getsize(out_path)} bytes)")
    print(f"对盘复检缺失数(必须=0): {bad}")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
