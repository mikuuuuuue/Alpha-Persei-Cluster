# 客户端验收记录

本记录分开标记源码、自动检查和游戏客户端结果。自动检查不代替自然游玩、退出重登或客户端截图。

## 当前结论

- B0 已保存为本地提交 ce761b7。本机 `307/332/v5.3.6` 资源、联网主界面、角色／背包和重登已有证据；仅 B0-S01 断网渠道认证按用户指示后置，整票 partial。用户随后已授权恢复 B1。
- B1 整批反馈中的多维首战后推进失败已登记为 N-1，并完成修复与实机复验；联合特勤黑屏 N-2 仍缺初始化契约，未修复。其余“正常”为用户汇总，不替代逐项数值／截图。B1 保持 partial，修复及验收文档随本轮本地快照保存，未进入 B2。
- M2 数值走查：第 1 项数值与重登已核对，用户已整批回报其余正常并指出 N-1／N-2。N-1 修复后推进复验通过；各项缺少的数值、截图或执行证据在下表单列。当前 B1 修复版服务已停、临时 hosts 已恢复，以本轮清理回执为准。
- B2 三关和 B3 三预设：客户端均阻塞。B3 只有全新内存存档的自动遍历结果。
- F：15 个入口都没有客户端验收。现有 15 份专项日志共运行 291 项，6 份全通过；9 份各有 1 个依赖错误，断言失败为 0。
- 爬塔、换装池：本轮没有客户端结果；内存 Core 与冷读专项见文末，不能替代客户端。
- A1 已按本轮授权完成根替换、叶续签、分发同步和两处 Windows 根信任安装；文件、Windows 链与本机 HTTPS 探针通过。本轮游戏初始化及更新阶段结果见下文；不将其算作 M2 数值验收。

当前B1复验：2026-11-14 B1：N-1 多维首战后推进失败已完成源码修复、自动检查及客户端复验；实际场景由 3035111 推进到 3035401，本轮完整通关与任务／成就仍缺证。N-2 联合特勤缺 332 权威初始化契约，已登记、未修复。第 1 项数值／重登已有证据，其余按用户汇总正常与逐项缺证记录，M2 未全过。临时服务已停、hosts 已恢复。B0 本地提交 ce761b7 未推送，B0-S01 后置；不进入 B2。

**本轮已清理。** PID `24768` 和游戏进程均已退出，exec `35738` 经 Ctrl+C 退出 `1`；Restore 退出 `0`，hosts 与原始 65492 字节完全一致。35 TCP＋UDP 6105 可独占绑定，保护 9 文件与客户端主清单未变；两关键域独立 DNS 回读为 `203.107.63.115`。证据为 `b1-client-20261114/cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`。

## B0：本机版本适配前置

2026-11-14 B0 核对结束：本机 `307/332/v5.3.6` 的版本／资源适配、联网状态下的主界面、角色／背包和退出重登均有证据；除用户后置的 `B0-S01` 外，未发现其他未完成的必需项。断网冷启动仍被 B 站渠道登录阻断，因此整票保持 **partial**，不能写成全部离线通过。临时服务已停、hosts 已恢复；本轮停止，等待用户确认后才恢复 B1。

| B0 条件 | 结果与证据 |
| --- | --- |
| 目标与连接身份 | done；本机 307／332、v5.3.6，官方渠道 10；gateway 308 分列，实际两次 slot 3／UID 261113211627／332 与库一致。 |
| 完整主／双语音资源 | done；71,275 个唯一对象，63,325,313,135 字节；准备窗口逐项大小／MD5，缺失／坏对象 0。 |
| 实际联网客户端流程 | done；用户确认主界面、昵称／UID、角色／背包及退出重登全部正常；两次登录完成 207/218。 |
| 完全断网冷启动 | partial，B0-S01 后置；B 站登录窗口因无网无法认证，未进游戏，不算离线通过。 |
| 失败路径与必需检查 | done（自动范围）；4 个专项 16／5／21／13 均 exit 0，本次无生产变化未重跑；不代表全玩法。 |
| 复核与恢复 | done；根 Codex＋Luna high 复核，复杂度删除清单无；hosts 原字节恢复、端口释放、保护 9 个文件＋客户端主清单未变。 |

用户确认昵称 `B0版本适配`、UID `261113211627`、主界面、角色列表、背包和退出重登全部正常。实际日志有两次 slot 3 登录及两次版本 `332` 的登录推送完成，均为 `207/218` 帧、动态 `207`；11 帧进度合并为一次全量，再按既有版本策略略过 `89013`。207 是实际发送数，218 是合并／过滤前候选数，不相加为独立覆盖。库内唯一用户、等级 `70` 与身份回读一致，quick_check=`ok`；此处没有替代 B1 的资产数值验收。

`B0-S01`，confirmed／filed／用户后置：用户完全退出游戏后断开 Wi-Fi／网线，冷启动弹出 B 站登录窗口，因无网无法登录，未进入游戏。当前 Mix SDK 本地接口不等于原生 PCGameSDK 离线认证，仓库没有现成实现；未伪造响应、扩展 10 域名预览、改真实账号或客户端安装文件。断网失败独立保留，联网成功不能覆盖它。

服务 PID `9484` 已不存在，exec `66583` 经 Ctrl+C 退出 `1`，不冒充优雅退出通过。`hosts-transaction.ps1 -Action Apply`／`Restore` 均退出 `0`；恢复后 hosts 与原件逐字节一致，长度 `65492`、SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54`。即时解析回执保留，独立 DNS 两关键域随后均为 `203.107.63.115`。35 个 TCP 端口及 UDP `6105` 可独占绑定，9 个保护文件及客户端主清单哈希未变。

证据目录 `selftest_tmp/priority-repair/b0-local-client/`：`client-online-acceptance-20261114.json`、`client-offline-blocker-20261114.json`、`cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`、`review-resume-20261114.json`。新备份 `hosts.before-resume-20261114-073937.bin` 与原件一致，旧运行和回滚回执另存 before-resume 副本。原始 SDK 日志含凭据，仅留忽略目录，不原样输出。最后额度回读为 5 小时剩余 `86%`、周 `68%`，未重置。

## M2：12 项数值走查

计划来源：[M2 数值走查清单](../../M2-数值走查清单.md)。每项都要求操作前、操作后和重登后三个状态。

自动检查只提供共同背景：本轮 `selftest_tmp/priority-repair/m2-defect.log` 记录 `ALL PASSED`；`smoke.log` 记录 423 个操作、52 个有效参数命令、0 个未捕获异常。12046 有 1 项定时体力资格差异，依据运行时间核对，未更新基线。下表不把共享结果折算成单项客户端通过。

| 序号 | 客户端核对 | 源码／自动检查 | 客户端状态 |
| --- | --- | --- | --- |
| 1 | 抽卡十连扣费与产出 | 共享自动结果见上；实际取证使用332隔离档。 | 数值／重登已核对；票20→10、10记录、新角色1056＋重复碎片＋8钥从＋辉芒110，三阶段快照一致；截图待回传。 |
| 2 | 商城购买扣费 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺逐项扣费数值与截图，未记数值验收通过。 |
| 3 | 体力购买与消耗 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺逐项消耗数值与截图，未记数值验收通过。 |
| 4 | 角色升级消耗与经验 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺消耗／经验前后数值与截图，未记数值验收通过。 |
| 5 | 刻印分解返还 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺分解前后数值与截图。额外报告的联合特勤黑屏另列 N-2。 |
| 6 | 任务领奖入包 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺逐项奖励数值与截图，未记数值验收通过。 |
| 7 | 周常／活跃奖励领取 | 共享自动结果见上；未映射为本项客户端结果。 | 用户整批回报正常；缺逐项奖励数值与截图，未记数值验收通过。 |
| 8 | 邮件附件领取 | `02-12-after-batch.db` 回读邮件 1020 的 `attach_flag=2`。 | 用户整批回报正常，库证已领取；缺本项独立资产差额与截图，未记完整数值验收通过。 |
| 9 | 好感度礼物消耗 | 批次后快照中礼物 30012 仍为 5；未取得对应赠礼请求证据。 | 用户整批回报正常，但无法证明本项实际消耗；保留缺证，不记通过。 |
| 10 | 第 1～9 项重登后数值 | 第 1 项已有重登快照；其余仅有批次后快照，不能代替逐项三阶段证据。 | 用户整批回报正常；其余项重登数值未逐项留证，不记全通过。 |
| 11 | 多维变量通关、任务与成就提示 | N-1 真实 battle-info 回归保存 8502/10000 并推进；多维 35／Hodur 20／战棋定向 1 通过。 | N-1 推进实机通过：用户报正常，场景 3035111→3035401、battle_count 0→1、实际 HP 9250/10000；未完成整局，任务／成就仍缺证，整项 partial。 |
| 12 | 1032018、1032019 终局卡死观察 | 当前无这两关的本轮同场日志或转储。 | 用户汇总未单列这两关，无法确认实际执行；作为可选观察项保留缺证，不展开 B2。 |

历史基础回归日志为 `m2-defect.log`／`smoke.log`。本轮各项状态以上表为准；下面是 B0 之前的初始化与资源更新历史：

- 首次隔离 UID `42` 导致 SDK `Int32→Int64` 异常，登记 B1-C01；换用既有分配器生成的 UID `261113200139` 后，用户确认已越过初始化。生产 SDK 未修改，小 UID 兼容缺口仍为 filed。
- 用户随后看到更新提示且下载失败。实际安装资源为 `307/332`，服务端所选 PC 原生为 `307/321`；日志中 2928 条 `.ys` 访问均为 `404`，对应 82 个不同文件名。82 个均存在于所选 321 清单，清单尺寸合计 `244992009` 字节；这些数字只覆盖本轮请求及重试，不表示全量缺口。
- 本机安装目录、仓库已有缓存及已知 legacy 根均没有这 82 个文件；登记 B1-R01。只配置目录不能解决缺件，未联网下载、猜改清单或改写客户端安装文件。初始化通过不等于主界面登录成功，M2 12 项仍未执行。
- 两轮均由用户手工操作。结束后已停止隔离服务并精确恢复 hosts；9 个保护文件和客户端原资源清单 SHA256 不变。独立 DNS 查询的两个关键域名已恢复为 `203.107.63.115`。

历史证据目录：`selftest_tmp/priority-repair/b1-client-20261113/`。初始化证据为 `sdk-initialization-blocker.json`／`client-initialization.png`／`large-uid-readback.json`；资源证据为 `resource-update-blocker.json`／`resource-missing-specs.json`／`resource-presence.json`；当轮清理见 `cleanup-readback.json`／`hosts-restore-receipt.json`／`dns-after-restore.json`。匹配资源现已由 B0 补齐；最新批次反馈及 N-1 修复证据在 `b1-client-20261114/`，不宣称 M2 全过或 `0` 个客户端缺陷。

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
| 11 | 多维变量通关、任务与成就提示 | N-1 真实 battle-info 回归保存 8502/10000 并推进；多维 35／Hodur 20／战棋定向 1 通过。 | N-1 原推进故障实机复验通过；完整一局及任务／成就仍缺证，F 项整体验收未完成。 |
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

B1 整批自查准备：用户不再逐项回报。第8项指定邮件 `B1-08 附件验收`（mail_id 1020），附件精确探测凭证5、艾因索菲币1000、普通的礼物5，尚未领取。礼物供第9项使用；仅在游戏入口可用时执行，前置未解锁须记未执行原因。第5项当前有1件未装备未锁定刻印。代理已保存余项会话基线，等待用户数值／截图及实际操作后统一回读，不能把准备状态算通过。

当前诊断状态：**当前诊断服务和临时 hosts 活动，结束后必须恢复。** PID `11224`、exec `60503`，目录 `selftest_tmp/priority-repair/b1-client-20261114/`，日志 `server-diagnostic.log`，昵称B1隔离验收／UID `261113200139`／版本332。旧PID8068已停止并Restore exit0，原字节、35 TCP+UDP6105、保护9及客户端清单均已回读；旧回执另存before-diagnostic后缀，不代表当前已恢复。当前已重新备份并Apply同10域。

N-2：新档login.py的schema默认路径下发空SC42001，登录日志三次可证；本地BattleEnchantAction绑定42001，EnchantmentStageView固定读取3个组。43001是另一装备状态帧，25009是关卡进度，不能替代42001。42002无真实handler，42004仅空42005模板；旧Lua/master样本没有332版本与初始分组规则，不能复制其他owner计数或猜组。已filed待332初始化契约，不扩多人解封或完整刷新玩法。
