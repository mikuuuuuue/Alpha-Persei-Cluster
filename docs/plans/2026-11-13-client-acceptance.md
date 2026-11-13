# 客户端验收记录

本记录分开标记源码、自动检查和游戏客户端结果。自动检查不代替自然游玩、退出重登或客户端截图。

## 当前结论

- M2 数值走查：12 项都阻塞，未运行游戏客户端。
- B2 三关和 B3 三预设：客户端均阻塞。B3 只有全新内存存档的自动遍历结果。
- F：15 个入口都没有客户端验收。现有 15 份专项日志共运行 291 项，6 份全通过；9 份各有 1 个依赖错误，断言失败为 0。
- 爬塔、换装池：本轮没有客户端结果；内存 Core 与冷读专项见文末，不能替代客户端。
- A1 已按本轮授权完成根替换、叶续签、分发同步和两处 Windows 根信任安装；文件、Windows 链与本机 HTTPS 探针通过。游戏客户端未运行，按用户要求等待每项完成后的确认。

## M2：12 项数值走查

计划来源：[M2 数值走查清单](../../M2-数值走查清单.md)。每项都要求操作前、操作后和重登后三个状态。

自动检查只提供共同背景：本轮 `selftest_tmp/priority-repair/m2-defect.log` 记录 `ALL PASSED`；`smoke.log` 记录 423 个操作、52 个有效参数命令、0 个未捕获异常。12046 有 1 项定时体力资格差异，依据运行时间核对，未更新基线。下表不把共享结果折算成单项客户端通过。

| 序号 | 客户端核对 | 源码／自动检查 | 客户端状态 |
| --- | --- | --- | --- |
| 1 | 抽卡十连扣费与产出 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 2 | 商城购买扣费 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 3 | 体力购买与消耗 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 4 | 角色升级消耗与经验 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 5 | 刻印分解返还 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 6 | 任务领奖入包 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 7 | 周常／活跃奖励领取 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 8 | 邮件附件领取 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 9 | 好感度礼物消耗 | 共享自动结果见上；未映射为本项客户端结果。 | 阻塞：未运行客户端。 |
| 10 | 第 1～9 项重登后数值 | 自动回归不能证明客户端缓存和重登表现。 | 阻塞：未运行客户端。 |
| 11 | 多维变量通关、任务与成就提示 | 多维自动回归存在；不能代替一次完整客户端通关。 | 阻塞：未运行客户端。 |
| 12 | 1032018、1032019 终局卡死观察 | 当前无这两关的本轮客户端日志或转储。 | 阻塞：未运行客户端。 |

证据位置：`selftest_tmp/priority-repair/m2-defect.log`、`selftest_tmp/priority-repair/smoke.log`。没有操作前／后／重登截图，也没有可登记的新客户端异常实例。

## B2：M-5 三关复核

计划要求先打 1032018、1032019，再复验 1032020，并依据同场日志或转储决定单关还是整条弧线规避。

| 关卡 | 源码／自动检查 | 客户端状态 |
| --- | --- | --- |
| 1032018 | 本轮没有该关的单独自然路线结果。 | 阻塞：未运行客户端，未取得终局日志或转储。 |
| 1032019 | 本轮没有该关的单独自然路线结果。 | 阻塞：未运行客户端，未取得终局日志或转储。 |
| 1032020 | 旧诊断材料只作历史线索；不作为本轮复验。 | 阻塞：未运行客户端，未取得终局日志或转储。 |

当前不判定 M-5 的规避范围。下次获得客户端运行授权后，按计划依次打完三关，并保存每场客户端转储与同一时间窗的服务端日志。

## B3：新档预设遍历

证据来自 [b3-presets.json](../../selftest_tmp/priority-repair/b3-presets.json)。脚本在全新内存配置上遍历前驱解锁，并检查数据库完整性；这些数字不代表客户端进度或完整通关。

| 预设 | Owner | 已清关 | 可用 | 锁定前驱案例 | DB 完整性 | 客户端状态 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 普通新档 `fresh` | 42 | 0 | 24 | 1085 | `ok` | 阻塞：未运行客户端。 |
| 跳序章 `skip_prologue` | 43 | 7 | 30 | 1079 | `ok` | 阻塞：未运行客户端。 |
| 快速体验 `quick_start` | 44 | 48 | 91 | 1043 | `ok` | 阻塞：未运行客户端。 |

## F：15 个入口

计划范围来自[入口名单](../../v5_server/docs/minigame_user_roster_20261104.md)。源码阶段状态只引用名单中的既有记录。本轮自动日志详情如下；这不是游戏内进入、游玩、领奖或重登结果。

| # | 入口 | 自动日志结果 | 游戏客户端 |
| ---: | --- | --- | --- |
| 1 | 极限机装 | `verify_vehicle_ball.log`：Ran 21，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/mergeballstagecfg.lua`。 | 阻塞：未运行。 |
| 2 | 诡谈夜话 | `verify_rogue_card_lifecycle.log`：Ran 17，errors 0，failures 0。 | 阻塞：未运行。 |
| 3 | 岁醒夺魁 | `verify_offline_minigame_rewards.log`：Ran 7，errors 0，failures 0。多人封锁和常驻奖励自动检查不证明客户端领取体验。 | 阻塞：未运行。 |
| 4 | 谧光叙录 | `verify_hodur_challenge.log`：Ran 20，errors 0，failures 0。 | 阻塞：未运行。 |
| 5 | 远村异闻 | `verify_pinball.log`：Ran 19，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/pinballstagecfg.lua`。 | 阻塞：未运行。 |
| 6 | 浮光绎曲 | `verify_resident_music.log`：Ran 16，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/activitymusiccfg.lua`。 | 阻塞：未运行。 |
| 7 | 人机对战 | `verify_autochess_finish.log`：Ran 19，errors 0，failures 0。 | 阻塞：未运行。 |
| 8 | 列车大劫案 | `verify_ash_shoot.log`：Ran 24，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/ashshootstagecfg.lua`。 | 阻塞：未运行。 |
| 9 | 食与异世界 | `verify_summer_pub.log`：Ran 24，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/summerpublevelcfg.lua`。 | 阻塞：未运行。 |
| 10 | 战术研习记录 | `verify_osiris_study.log`：Ran 24，errors 1，failures 0。native 导出检查导入 `extract_autochess_cfg` 时失败。 | 阻塞：未运行。 |
| 11 | 刺桐巷 | `verify_quanzhou_runtime.log`：Ran 15，errors 0，failures 0。冲刺路线仍需客户端观察。 | 阻塞：未运行。 |
| 12 | 溯梦之隙 | `verify_skuld.log`：Ran 23，errors 1，failures 0。native 导出检查导入 `extract_autochess_cfg` 时失败。 | 阻塞：未运行。 |
| 13 | 夏日竞技 | `verify_summer_board_finish.log`：Ran 20，errors 0，failures 0。 | 阻塞：未运行。 |
| 14 | 薇儿丹蒂常驻活动 | `verify_sphero_leisure.log`：Ran 20，errors 1，failures 0。native 导出检查导入 `extract_autochess_cfg` 时失败。原两项头像目录断言已修；当前日志只剩此依赖错误。 | 阻塞：未运行。 |
| 15 | 卡达斯假日赛 | `verify_kadas_race.log`：Ran 22，errors 1，failures 0。缺 `decompiled_v2/x64/game/config/activitytankcfg.lua`。 | 阻塞：未运行。 |

上述 F 日志合计 Ran 291、errors 9、failures 0。9 个 error 都发生在 native 导出／配置核对路径；其中 6 个明确缺 Lua 文件，3 个因 native 导出工具导入失败。`Test-Path decompiled_v2` 实测为 `False`，不能把这些 error 写成玩法断言通过。

## 名单外玩法

| 玩法 | 源码 | 自动检查 | 游戏客户端 |
| --- | --- | --- | --- |
| 爬塔 | 复用既有实现，未改玩法。 | `f-tower.json`：真实内存 Core 入场和注入胜利战报结算，进度为 area 4010101／stage 4010001；41001 回读一致。重复结算只回 54033，资产不变；测试副本冷读一致。命令：`python -B -X utf8 selftest_tmp/priority-repair/f-tower-probe.py`，退出 `0`。 | 阻塞：未实际游玩或登录游戏；注入胜利战报不能作为客户端完成证据。 |
| 换装池 | 复用 `skin_draw_service` 与 68152 Operation，未改玩法。 | `f-skin-draw.json`：池 1001，凭证 53030，单次成本 1；单抽 20→19，十连 19→9，累计 11 次，68151 状态与测试副本冷读一致。 | 阻塞：查询、单抽、十连动画／展示及游戏重登未验。 |

## 其他浏览器与启动证据

| 项目 | 源码／自动检查 | 客户端或宿主 |
| --- | --- | --- |
| C：Inventory 清理和套装 | `c-after.log`：Ran 10，errors 0，failures 0。 | IAB 临时双存档回读：3 星套装 6 件；清理 1 行材料；同 UID 的 `other.db` 数量仍为 7；货币为 777。详情见 [c-browser-readback.json](../../selftest_tmp/priority-repair/c-browser-readback.json)。这是控制台浏览器证据，不是游戏客户端验收。 |
| A1：证书 | [修复后文件检查](../../selftest_tmp/priority-repair/a1-cert-check-repaired.json) 退出 0；两库信任、Windows 链、实际 HTTPS 200 和根／叶指纹核对通过。 | 证书级探针完成；游戏客户端未验。严格 CRL curl 失败仍保留，详见进度台账 A1 续作。 |
| D：启动与周期浏览器 | `d-browser-readback.json`：HTTPS 11443、CDN relay 持久化；介质攫取 0／0、领取列表清空，货币 2=777、材料 41201=7 保持。 | IAB 已实测非法端口反馈、保存／重新读取、重置取消／确认、列表滚动及刷新；临时服务已停止。[启动画面](../../selftest_tmp/priority-repair/d-launch-browser.jpg)、[周期画面](../../selftest_tmp/priority-repair/d-cycle-browser.jpg)。 |
| Windows 宿主 | A1 续作以 SDK 10.0.404 构建通过，0 警告、0 错误。前轮 `dotnet-build.log` 保留缺 SDK 的历史失败。 | 已构建；D 的托管重启未实测，等待逐项确认。 |

## 共享路径与复杂度复核

- C 材料清理曾把官方 type 6 材料排除；已改为 `classify_item()` 判定。Inventory 同 UID 切档的旧请求覆盖问题已用存档／UID 身份和请求序号保护。两项修复已分别通过 m4 API 与前端类型检查；本轮没有游戏客户端证据。
- G 注册表删除曾在物理回收后才提交映射；现先提交映射，提交失败时原文件不动，回收失败时尝试恢复旧映射。隔离故障注入已确认失败返回、原档和旧映射保留。
- H1 五个问候模板与旧 AST 逐字匹配；新增三个上下文键只作用于内存 system prompt。10 个 persona 文件仍标记 `reviewed=false`，当前无运行时加载者。
- 登录读取已从 `seq <= 192` 改为按 `seq` 读取并在首个 `10201` 处停止，且包含该终止帧。现有主库有 192 行，终止帧在 seq 192，未发现旧流程依赖跳过 192 之后的帧。`replay.py` 两处过时注释已同步修正。`python -B -X utf8 v5_server/tools/verify_rogueteam_tutorial_skip.py` 5/5 通过；`python -B -X utf8 v5_server/tools/verify_minigame_empty_login.py` 4/4 通过。`tests/m3_import_check.py` 已加入大于 192 帧、包含结束帧并排除结束后增量的检查，最终结果见进度台账。
- 静态目录普通集合为 41 张、导入子集为 34 张。导入器当前已显式调用 `IMPORT_STATIC_CATALOG_TABLES`，没有复制 `login_push`、API 配置或供体账号。
- 独立复杂度审查与删除清单见[交付复核](2026-11-13-repair-delivery.md)。已删除重复 AST 助手、生成器探测、批量 UID 改写和重复隔离登录；未增加新操作或 CLI 选项。

跨进程注册表复核命令：`python -B -X utf8 selftest_tmp/priority-repair/registry-race-probe.py`。隔离结果保存在 [registry-race-result.json](../../selftest_tmp/priority-repair/registry-race-result.json)。

岁醒夺魁的内存资产读回另存为 `selftest_tmp/priority-repair/f-offline-rewards.json`：60533～60536 一键领取后，41302 为 50、40603 为 100、40104 为 80、货币 1 为 300。恢复任务再重复请求后四项均不增加；响应顺序为 17023→28015。客户端领取体验仍未验。
