# 未完成功能与修复优先级（2026-11-12）

2026-11-13 执行更新：实际结果以[修复进度台账](plans/2026-11-12-repair-progress.md)为准。R04 首批三个 GM 写操作和四个明确未支持响应已实现，10 项隔离 API 检查及浏览器库存交互通过；游戏重登未验。R05 的 7 项自动专项通过，Windows 宿主因缺少 .NET SDK 阻塞。R02 已恢复共享战斗、Linux 和多项消费者，缺原生 Lua 的核对仍单列。R13 已交付 10 份未审校试稿，未启用或回填。R01 证书重部署与系统信任变更仍待当轮专项授权。其余票的源码、自动检查和客户端状态分别记录，以下历史结论不批量改为已修复。

## 概览

建议先恢复本机可运行和可验证的状态，再处理资产一致性、面板假成功及玩法缺口。AI 内容与大文件拆分排在后面。

本次基于本地 `main` 的 `4bec98f`。远端 main 为 `26c2769cd1d55b166892f497b18f1fecc819a436`，本地已包含该提交。v5.0.4 更新说明见 `docs/upstream-update-2026-11-12.md:21`。

默认目标是 PC 单机稳定可玩、存档数据正确。以下顺序是本次整理建议；原计划和台账保持原样。本次只更新本文，新增、删除代码模块、类和顶层函数均为 0。

## 快速接续

1. 先处理 R01，让证书检查返回通过。
2. 接续 R02，恢复受影响专项的验证入口。
3. 在隔离存档上执行 R03，登记实际失败。
4. 接续 R04 和 R05，完成管理操作与新启动流程验收。
5. 按 R06～R12 推进玩法和账号迁移工作。

R01 不阻塞无头测试。R02 与取证可并行准备。修复顺序须服从真实依赖；例如 Mode4 两项积分任务须先补队伍总分模型。

## 重要程度排序

P0 表示当前运行阻塞；P1 表示验证、资产正确性或主要管理流程；P2 表示玩法与迁移能力；P3 表示增强、治理或旧记录整理。同级按表内顺序接续。

| 顺序 | 等级 | 项目与当前状态 | 排在这里的原因 | 完成条件 |
| --- | --- | --- | --- | --- |
| R01 | P0 | 本地证书与根私钥配对：已确认不匹配。 | 阻塞本机正常启动及后续真机验收。 | 只读证书检查退出码为 0，再验证客户端连接。 |
| R02 | P1 | 六个直接脚本和 3 个 Linux 旧夹具已恢复；原生 Lua 和历史归档缺项单列。 | 原生对照仍缺材料，不能把运行夹具通过当原生通过。 | Issue #8 17 项、Linux 41 项通过；原缺项仍须补齐才能完成原生／历史对照。 |
| R03 | P1 | 核心资产、周期与 M2 数值验收：待实测和逐项复核。 | 扣费、发奖、重试及重登不一致会影响存档可信度。 | M2 12 项填写实际结果；关键操作扣发一致、重领不增益、重登保持；真实失败均有复现与处置。 |
| R04 | P1 | 三个 GM 真写入、四个未支持响应及错误码已修；API 与浏览器通过，游戏重登未验。 | 假成功已消除，受保护资产的游戏内体验仍需重登验收。 | 真实库、API、页面回读一致；游戏内回放、兑换和表情按客户端清单补验。 |
| R05 | P1 | v5.0.4 启动配置、托管重启与周期卡片：已有实现，待完整交互验收。 | 涉及进程重启、网络端口和周期写入，是新引入的主要管理流程。 | 保存值在重启后实际生效；非法端口被拒；在线玩家不能重置周期，过期状态被拒；实际浏览器与宿主链路通过。 |
| R06 | P2 | M-5：1032020 终局卡死，旧缺陷待当前版本复验。 | 阻塞特定关卡及 M2 收官，影响范围小于基础链路。 | 复现后取得转储／日志；对照 1032018、1032019；修复复验或完成有依据的规避登记。 |
| R07 | P2 | 虚构推演：HP、其余效果与科技、pool301 权重等保留边界。 | 主干与 17 项审查成就已接通，剩余规则会影响整局正确性。 | 逐角色状态有可信来源；每个补齐效果有生命周期及恢复检查；完整局和重登验收。 |
| R08 | P2 | 多维变量：完整效果／数值、复活上限、HP、试炼招募类型 1。 | 生命周期已补，但部分合法玩法与效果仍缺。 | 合法招募类型和效果可用，数值依据明确，完整局与冷恢复一致。 |
| R09 | P2 | 迭代校验 Mode4：五队总分、两项积分任务及挑战入口。 | 合法积分任务仍被拒，必须先补真实队伍成绩来源。 | A94 队伍总分及 A96 等入口依赖闭合；两项积分任务可正常达成、领取且防重。 |
| R10 | P2 | 因果观测／战棋：后续地图、高级事件、船炮、多队及新战棋链路。 | 仅首图有完整自然路线的脚本验收，后续范围较大。 | 逐图核对所需事件；已支持图可自然完成；未支持语义明确失败，不以导入配置代替完成。 |
| R11 | P2 | 已完成源码阶段的小游戏、爬塔、换装池：待客户端系统验收。 | 应验证已有成果，避免将旧未勾选项重写一遍。 | 15 个既定入口按范围验收；爬塔和换装池单独核对进度、扣费、领奖及重登。 |
| R12 | P2 | 首版导入、正常隔离挂载与原子发布已交付；真实样本缺 10 封邮件和 144 个未审核协议，整票 partial。 | 合成账号通过不能证明真实全账号恢复。 | 补齐同会话证据和映射，再完成真实恢复档与游戏客户端登录。 |
| R13 | P3 | v2 三键、五模板和 10 份未审校稿已交付；未扩展、启用、回填或在线调用。 | 51 人扩展依赖内容审校。 | 先审校 10 稿，再按原门禁完成全量、在线及游戏内验收。 |
| R14 | P3 | 主线新档树及历史主线票：先核对旧台账。 | 现有代码已有前驱和分支限制，不能按旧 queued 票直接重写。 | 区分新档预设与预通设置；验收实际解锁行为，再更新旧票状态。 |
| R15 | P3 | 三大文件拆分与接口治理。 | 变更面大，宜在基础验收和测试保护恢复后进行。 | 当前注册面与兼容接口不变；真实业务及客户端回归通过；满足重核后的原拆分门禁。 |
| R16 | P3 | 旧计划状态、说明与低影响工具整理。 | 减少误判和重复开发，但不优先于功能正确性。 | 统一已实现／待验收口径；修正旧版本和旧基线；清理经复核的低影响遗留。 |
| R17 | 不排期 | iOS 311 清单、手机 DNS、iOS 差量等上游移动端余项。 | 本地移动端已明确豁免。 | 若重新纳入目标，再按真实设备与资源证据立项。 |
| R18 | 不排期 | 多人联机、公会、PVP 解封。 | 当前为主动关闭，原单人计划没有实现它们的目标。 | 若目标改变，单独定义联机方案和验收范围。 |

如果当前任务是抢救官方账号，R12 的素材留存应前移到 P0，并与本机修复并行；导入实现本身不必等待官方在线。本次未核实官方可登录性，不将“仍在线”作为事实。

## 排序依据与确认程度

| 项目 | 来源与本次判断 |
| --- | --- |
| R01 | `v5_server/gen_cert.py:476` 的只读入口本次返回 `ready=false`，提示根证书与根私钥不匹配；`v5_server/main.py:386` 在证书准备失败时中止启动。已登记，未部署修复。 |
| R02 | `v5_server/tools/verify_report_small_fixes.py:24` 缺模块；Linux 3 个错误已重新执行，见本文“验证缺口”。已登记，未修改测试。 |
| R03 | `M2-数值走查清单.md:32`、`M2-数值bug登记簿.md:20`。12 点尚无填写结果。A03／A04／A244／A247 及大月卡历史票是复核线索，不冒充本次已复现。 |
| R04 | `v5_server/gm_api.py:733` 等 7 个函数体本次复查仍为空操作；`v5_server/gm_api.py:2479` 仍引用未定义错误码。详见下表。 |
| R05 | `v5_server/launch_settings.py:233`、`v5_server/gm_api.py:2929`、`LocalServer/ServerSupervisor.cs:477`。源码已接通；完整保存、重启和 UI 交互未实测。 |
| R06 | `M2-数值bug登记簿.md:16`、`M2-数值走查清单.md:67`。旧根因假设仍需复验，不直接当作当前已确认根因。 |
| R07 | `v5_server/docs/repair_20261105_rogueteam_effects.md:51`、`v5_server/docs/repair_20261106_rogueteam_battle_facts.md:55`。保留 HP 与效果边界；17 项审查成就已接齐。 |
| R08 | `v5_server/docs/repair_20261105_polyhedron_state.md:39`。生命周期阶段完成，整票仍为 partial。 |
| R09 | `v5_server/docs/repair_20261105_core_mode4_rewards_partial.md:25`。两项积分任务等待真实五队总分，不能以单关最高分替代。 |
| R10 | `v5_server/docs/repair_20261105_warchess_state.md:60`。只有 4040101 有整图自然路线的脚本验收；后续 39 图不能按已完成计算。 |
| R11 | `v5_server/docs/minigame_closeout_audit_20261105.md:11`、`README.md:1122`。小游戏一阶源码范围已收口；客户端移动、返回、领奖等仍需观察。 |
| R12 | `M3-执行计划.md:657`。未找到 `tools/import_capture_archive.py` 或等价全账号转库入口；新版 README 移除文字不等于实现完成。 |
| R13 | `M4-执行计划.md:66`、`M4-执行计划.md:220`、`M4-执行计划.md:388`。碎片仍为 v1，计划中的测试、人格目录和问候信外置文件未见交付。 |
| R14 | `v5_server/new_player_service.py:302` 已按等级、章节前驱、关卡前驱和分支限制解锁；`v5_server/new_player_service.py:319` 只从已通节点扩展。旧票未能证明当前仍缺实现。 |
| R15 | `M4-执行计划.md:1090`、`M4-执行计划.md:1387`。当前三大文件分别为 operations 8,803 行、account_db 7,342 行、middleware 4,254 行；行数不代表缺陷数。 |
| R16 | `README.md:28` 和 `CHANGELOG.md:3` 仍以 v5.0.3 为最新说明，而本地已合入 v5.0.4；旧计划还保留 397 操作等旧口径。 |
| R17／R18 | `M2-执行计划.md:19` 的移动端豁免及 `README.md:1115` 的联机封锁继续保留。 |

## M2 原任务对照

| 原任务 | 当前状态 | 位置与接续排序 |
| --- | --- | --- |
| Task 1：冒烟基建 | 完成代码整合，基线已升级。 | `tests/smoke_dispatch.py:86`。当前 423 个操作；52 个有抓包参数，371 个为空参数。最新合并检查记录见 `docs/upstream-update-2026-11-12.md:35`；本次未重跑。 |
| Task 2：刻印自动分解回包 | 已完成，保留回归。 | `v5_server/generator.py:1524`、`tests/m2_defect_checks.py:33`。不重复开发。 |
| Task 3：多维任务进度和通知 | 已完成代码整合，保留客户端回归。 | `v5_server/polyhedron_service.py:760`、`v5_server/task_listener.py:418`。归 R03。 |
| Task 4：章节协议漂移 | 旧覆盖未引入，真实映射待核。 | `docs/superpowers/plans/2026-11-05-m2-integration.md:48`。旧素材实际 cmd 为 89601；有现象时随 R03 取证，不直接重用旧覆盖。 |
| Task 5：证书保护 | 代码已完成，本地部署未完成。 | `v5_server/gen_cert.py:47`、`tests/m2_defect_checks.py:101`。部署归 R01。 |
| Task 6：M-5 定位 | 部分完成，待当前版本复验／规避登记。 | `M2-数值走查清单.md:67`。归 R06。 |
| Task 7：数值走查和首例修复 | 建档完成，真机验收未完成。 | `M2-数值走查清单.md:36`、`M2-数值bug登记簿.md:20`。归 R03；以实际异常为修复输入。 |
| Task 8：阶段收官 | 部分完成。 | `M2-执行计划.md:925`。R03、R06 结果齐后回填。代码合并不代替阶段验收。 |

M-1～M-4 保留为已修复回归点。M2.1 手机 DNS 已豁免，不因上游新增移动端记录而重新排入。

## M3 原任务对照

| 原任务 | 当前状态 | 位置与接续排序 |
| --- | --- | --- |
| Task 0：官方流量补抓 | 历史素材待办，按需补证。 | `M3-执行计划.md:65`。归 R12 的素材条件；不凭旧清单重开已完成单人入口。 |
| Task 1：虚构推演 | 当前阶段完成，完整玩法部分完成。 | `v5_server/docs/repair_20261106_rogueteam_battle_facts.md:55`。归 R07。 |
| Task 2：多维变量 | 生命周期阶段完成，整票部分完成。 | `v5_server/docs/repair_20261105_polyhedron_state.md:39`。归 R08。 |
| Task 3：刺桐巷、夏日竞技 | 单人入口一阶源码完成，待实机。 | `v5_server/docs/minigame_closeout_audit_20261105.md:11`。归 R11；刺桐巷即旧计划的刺桐港埠漫行纪。 |
| Task 4：决斗王 PVE | 既定一期、12 关和简化 303 路线源码完成。 | `v5_server/docs/minigame_closeout_audit_20261105.md:17`。归 R11；A133 官方管理员特殊流程保留既定边界。 |
| Task 5：爬塔 | 已有实现，待系统验收。 | `v5_server/generator.py:1775`、`v5_server/new_player_service.py:361`。归 R11。 |
| Task 6：换装池 | 已接通，待完整真机验收。 | `v5_server/skin_draw_service.py:283`、`v5_server/operations.py:2259`。归 R11。 |
| Task 7：抓包导入 | 未完成。 | `M3-执行计划.md:657`。归 R12。 |
| Task 8：小游戏与总验收 | 单人入口源码阶段完成，客户端及总验收未完成。 | `v5_server/docs/minigame_closeout_audit_20261105.md:3`；`12012` 已在 `v5_server/onboarding_operations.py:126` 实现。归 R11。 |

旧 M2 建议将导入提级，旧 M3 又将其列为 Task 7。本次按当前目标列为 R12，并保留素材有时限时的前移条件。

## M4 原任务对照

| 原任务 | 当前状态 | 位置与接续排序 |
| --- | --- | --- |
| Task 1：AI 离线测试与审计 | 未见计划产物。 | `M4-执行计划.md:66`。归 R13。 |
| Task 2：提示词碎片 v2 | 未完成。 | `v5_server/data/ai_prompt_fragments.json:2` 仍为 v1。归 R13。 |
| Task 3：问候信提示词外置 | 未完成。 | `v5_server/ai_translator.py:466` 仍为内联。归 R13。 |
| Task 4：51 角色人格 | 待审计和内容交付。 | `M4-执行计划.md:388`。名册 51 条提示词为空，真实存档另有来源；不据名册判定所有存档均无人格。归 R13。 |
| Task 5：在线模型验收 | 未见计划验收产物。 | `M4-执行计划.md:516`。归 R13。 |
| Task 6：AI 真机验收 | 未完成。 | `M4-执行计划.md:648`。归 R13；现有问候通知缺口先随 R03 核实。 |
| Task 7：GM API 业务测试基建 | 未见原计划产物；已有认证专项。 | `M4-执行计划.md:672`。业务写入检查归 R04，认证检查不能替代落库验收。 |
| Task 8：参数校验与横向修复 | 部分完成。 | UID 校验和新端口校验已有；缺失错误码仍在 `v5_server/gm_api.py:2479`。剩余归 R04。 |
| Task 9：背包写端点真实化 | 未完成。 | `v5_server/gm_api.py:865`、`v5_server/gm_api.py:904`。归 R04。 |
| Task 10：同源写防护与死接口清理 | 密码模式保护已实现；旧删除方案失效。 | `v5_server/admin_session_auth.py:351`、`v5_server/admin_session_auth.py:385`。PAY 后端存在，不能按“不存在”删除。部署验收归 R05。 |
| Task 11：Inventory 直接写入 UI | 未接线。 | `v5_server/web_src/src/panels/Inventory.tsx:28`、`v5_server/web_src/src/panels/Inventory.tsx:398`。现有编辑是邮件草稿，归 R04。 |
| Task 12：面板业务真机验收 | 未完成。 | `M4-执行计划.md:1064`。归 R04／R05。 |
| Task 13：拆分门禁与基线 | 待按现状重核。 | `M4-执行计划.md:1090`。旧 DNS 门禁已豁免，397 操作和缺失 M1 脚本不能直接照用。归 R02／R15。 |
| Task 14：数据库拆分 | 未按旧目标完成。 | `M4-执行计划.md:1184`。未见 `db_layers/`，归 R15。 |
| Task 15：共享回包助手外移 | 未按旧方案完成。 | `M4-执行计划.md:1239`。未见 `ops/item_frames.py`；先复用上游已有抽取，归 R15。 |
| Task 16～18：操作按域迁移 | 已有部分抽取，未达旧目标。 | `M4-执行计划.md:1282`。归 R15。 |
| Task 19：中间件拆分 | 未按旧目标完成。 | `M4-执行计划.md:1326`。归 R15。 |
| Task 20：拆分总验收 | 待前置完成。 | `M4-执行计划.md:1353`。归 R15。 |

原内容审校、真实库回填、在线调用和拆分开工门禁继续保留，见 `M4-执行计划.md:484`、`M4-执行计划.md:505`、`M4-执行计划.md:636`、`M4-执行计划.md:1086`。本次排序未执行这些操作。

## R04：已确认的面板问题

以下 7 个函数体仍未执行所声称的业务写入或重载，均已登记，未在本次修复。按“返回成功且仅调用参数／账号校验”的静态模式扫描当前 POST 函数，命中这 7 处，无其他同类候选。

| 端点 | 当前位置 | 影响 |
| --- | --- | --- |
| `/heroes/unlock` | `v5_server/gm_api.py:733` | 返回解锁成功，未实际解锁。 |
| `/heroes/graduate` | `v5_server/gm_api.py:765` | 返回满级结果，未修改养成。 |
| `/inventory/add_suit` | `v5_server/gm_api.py:865` | 返回已发 6 件刻印，未生成实例。 |
| `/inventory/clear` | `v5_server/gm_api.py:904` | 返回清理成功，未删除资产。 |
| `/stages/complete_achievements` | `v5_server/gm_api.py:1339` | 返回固定成就完成结果，未实际修改。 |
| `/stages/set_polyhedron` | `v5_server/gm_api.py:1357` | 返回档案注入成功，未实际写入。 |
| `/server/hot_reload` | `v5_server/gm_api.py:1945` | 返回固定模块列表，未实际重载。 |

`v5_server/gm_api.py:2479` 还引用未定义的 `GMErrorCode.ITEM_NOT_FOUND`。商品不存在的免费直发分支会访问此常量。扫描该文件全部错误码引用，仅此名称未定义，已登记。

旧“启动端口直接 int 转换”问题移出待修复清单：`v5_server/launch_settings.py:188` 已校验类型与范围，`v5_server/gm_api.py:2984` 已转为参数错误。本次 3 个端口、各 4 类非法值均被拒。保存与重启整条链仍归 R05 验收。

## R02：验证缺口

Issue #8 专项本次仍在导入阶段失败，业务用例未执行。静态扫查确认以下 8 个辅助模块未在当前工具及服务端模块目录交付。

| 引用位置 | 缺失模块 |
| --- | --- |
| `v5_server/tools/verify_report_small_fixes.py:24` | `test_battle_entry_timing` |
| `v5_server/tools/test_settlement_retry_boundary.py:17` | `audit_core_regular_old_settlement_probe` |
| `v5_server/tools/test_hero_response_boundary.py:12` | `test_cost_fallback_boundary` |
| `v5_server/tools/test_hero_response_boundary.py:13` | `test_entity_rollback_notifications` |
| `v5_server/tools/verify_battle_entry_fail_closed.py:14` | `test_issue_hero_payload` |
| `v5_server/tools/verify_battle_entry_fail_closed.py:15` | `verify_mainline_trial_entry` |
| `v5_server/tools/verify_overflow_ownership.py:145` | `verify_all_cosmetic_mail` |
| `v5_server/tools/verify_rogueteam_tutorial_skip.py:7` | `verify_save_generator` |

第 1 项本次实际失败；其他项为静态依赖证据。多维、战棋和多个 Rogue 专项共用第 1 项助手，会受到传递导入影响。恢复时补齐原助手或按当前真实行为重建夹具，不增加空桩绕过断言。

本次还重新执行 Linux 已知失败的 3 个测试：

| 位置 | 失败原因与修复方向 | 处置 |
| --- | --- | --- |
| `v5_server/tools/test_linux_setup.py:210` | 旧夹具访问已不存在的 `lm.runpy`；应隔离当前启动调用并检查真实环境变量传递。 | 已登记，未修复。 |
| `v5_server/tools/test_linux_setup.py:233` | 同类旧 `lm.runpy` 夹具；应保留旧认证变量清理及参数覆盖的行为断言。 | 已登记，未修复。 |
| `v5_server/tools/test_linux_setup.py:585` | 未隔离真实 Nginx 检查，测试机无 Nginx；复用同文件 `nginx_mocks()` 并适配 HTTPS 夹具。 | 已登记，未修复。 |

`lm.runpy` 同类引用仅上述 2 处。3 个错误是测试夹具问题，不据此宣称生产认证或 Nginx 流程必然失败。最新合并记录也登记了它们，见 `docs/upstream-update-2026-11-12.md:49`。

## 台账口径与历史复核

`v5_server/docs/repair_tracker.json` 仍标记更新于 2026-11-06，未随 v5.0.4 更新状态。

| 口径 | 总数 | 台账状态 |
| --- | ---: | --- |
| 问题编号 `findings` | 386 | 176 项 source_verified、7 项 partial、203 项 historical。 |
| 修复票 `tickets` | 149 | 134 项 source_verified、13 项 partial、1 项 queued、1 项 evidence_needed。 |

`source_verified` 仅代表原源码／脚本阶段记录，仍可能缺实机；`historical` 表示待按当前版本复核。两种口径不能相加，也不能把 203 项当作 203 个当前已确认缺陷。

| partial 问题 | 本次排序与范围 |
| --- | --- |
| A03、A04 | R03：响应准备、通知队列及失败恢复，先按现有调用路径复核。 |
| A93、A95 | R09：Mode4 部分修复已完成；其他模式和队伍模型仍留。 |
| A133 | R11：保留管理员特殊流程边界，不重开已约定的一期／303 路线。 |
| A244、A247 | R03：问候／周期邮件摘要及部分资产通知链，先验证当前实际结果。 |

A264～A266、A255／A259 是旧大月卡及奖励线索，仍标 historical。按 R03 先复现，不先套用旧修复方案。夏日竞技部分早期阶段票仍标 partial，但后续总票和入口清单已记录源码收口，应以最新范围判断。

主线树 queued 票与现有前驱逻辑存在状态差异，归 R14。其他 203 条历史记录按复现后的真实影响分流：资产问题升 P1，单玩法问题归 P2，证据不足继续保留待核状态。

## 已完成或有意保留的边界

- 虚构推演 Issue #8 和 17 项审查成就已接通；101 教学按既定方案跳过。依据 `v5_server/docs/repair_20261106_rogueteam_battle_facts.md:55`。
- 刺桐巷、夏日竞技及既定单人入口已完成源码阶段，仍保留客户端观察项。依据 `v5_server/docs/minigame_closeout_audit_20261105.md:36`。
- 面板密码模式已有 Origin、CSRF 与会话保护；配置启用不等于本机实际已部署。依据 `v5_server/admin_session_auth.py:22`、`v5_server/admin_session_auth.py:385`。
- 新启动端口校验已有实现，不重复修旧直接转换代码；新启动配置和周期卡片归 R05 做完整验收。
- 主线已有前驱与分支判断，不凭旧台账判定缺失；预通预设与普通新档应分开核对。
- 全量联机、移动端豁免、真实库内容回填及外部模型调用范围保持原边界。本次只整理与排序。

## 本次核验

| 命令／检查 | 实际结果与限制 |
| --- | --- |
| `git ls-remote --exit-code origin refs/heads/main` | 退出码 0；main 为 `26c2769cd1d55b166892f497b18f1fecc819a436`。 |
| `git merge-base --is-ancestor 26c2769 HEAD` | 退出码 0；本地已包含远端提交。 |
| `python -B -X utf8 v5_server/gen_cert.py --check --json` | 退出码 1，根证书与根私钥不匹配，`ready=false`。 |
| `python -B -X utf8 v5_server/tools/verify_issue8_merge.py` | 退出码 1，缺少 `test_battle_entry_timing`；业务用例未执行。 |
| `python -B -X utf8 v5_server/tools/test_linux_setup.py LinuxSetupTests.test_run_auto_mounts_admin_password_file LinuxSetupTests.test_run_removes_legacy_auth_and_respects_cli_override LinuxSetupTests.test_wizard_semi_auto_retry_path` | 选定的 3 项全部错误；2 项旧 `lm.runpy`，1 项真实 Nginx 依赖。本次未重跑其余用例。 |
| `python -B -X utf8 v5_server/tools/verify_panel_password_integration.py` | 3 项通过。仅专项检查，不等于浏览器与部署交互验收。 |
| 一次性端口输入探针 | 调用 `launch_settings._validate`，3 个端口分别测试字符串、负数、越界数、布尔值，12 项均拒绝；未保存真实配置。 |
| 源码与来源复查 | 核对 7 个占位函数、全部错误码引用、8 个缺失助手、提示词文件、前驱解锁逻辑、旧计划与当前行数。 |
| 其他既有检查 | 423 操作冒烟、M2 10 项及认证 17 项通过是 11 月 12 日合并记录；本次未重跑，见 `docs/upstream-update-2026-11-12.md:35`。 |

本次未运行游戏、完整服务或真实模型，也未修改证书及系统信任。原计划、原台账和本地参数文件保持原样。所有问题保留为已登记、待验收或待复核状态，未把整理称为修复。

需求覆盖复核：M2 8 项、M3 9 项、M4 20 项共 37 个原任务均有状态和排序归属。另行复杂度复核的删除清单：无；复用本文件，未新增重复计划或实现工具。
