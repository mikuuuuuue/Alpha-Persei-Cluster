# 修复计划交接提示词

2026-11-14：B1 本轮修复、测试和验收记录已纳入本地快照。N-1 多维首战后推进失败已修复，并通过一次真实客户端推进复验。B1 整票仍为 partial：联合特勤 N-2 缺 332 初始化契约；完整多维通关、任务／成就和其他逐项数值仍缺证。服务已停，hosts 已恢复。

先核对仓库与本机证据，再在已确认的 B1 范围内接续。下一张任务票仍须用户明确确认。本次本地提交和交接没有启动新实施或测试。

## 快速接手

1. 读取仓库 `AGENTS.md` 和用户本次最新规则。
2. 完整读取本文件。
3. 读取 `docs/plans/2026-11-12-repair-plan.md`。
4. 读取 `docs/plans/2026-11-12-repair-progress.md`。
5. 读取 `docs/plans/2026-11-13-repair-delivery.md`。
6. 读取 `docs/backlog-status-2026-11-05.md`。
7. 读取 `docs/plans/2026-11-13-client-acceptance.md`、`M2-数值走查清单.md` 和 `M2-数值bug登记簿.md`。

工作目录为 `C:\Users\<user>\Desktop\Alpha-Persei-Cluster`。先运行：

```powershell
git status --short
git branch --show-current
git log -3 --oneline
git log -1 --format=%H -- v5_server/battle_server.py
```

分支为 `main`。本轮共 8 份文档（含本文件）和 4 个 Python 文件，属于同一 B1 本地快照；上面最后一条命令可定位该修复提交。前一提交为 B0：`ce761b770b2620ffd4b53187c2f234504fcf8ada`；A 阶段收官提交为 `93bbcc2946513e3f24333b2efb1fb74314491186`。均未推送。发现新改动时保留，不重置或覆盖。

`selftest_tmp/priority-repair/` 的隔离库、备份、缓存和原始日志受 Git 忽略规则保护，留在本机。提交不包含这些证据；换机器或目录缺失时，先报告缺失项。

## 执行与停止规则

1. 当前只接续 B1。每次执行一张已确认任务票，结束后报告结果，等待下一票确认；不自动进入 B2。
2. 使用子代理驱动执行，默认 `gpt-6-luna`、`high`。根代理串行修改共享文件。共享执行路径和权限边界由不同模型复核。
3. 读取可用的 5 小时和周额度。任一剩余不超过 10% 时停止，清理临时环境并保存交接。无法读取时如实说明，不自动重置。提交前最近回读为 58%／57%，接续时重新读取。
4. 先用 `rg` 检索已有实现，再复用或扩展。遵守总计划、仓库规范和阿里开发规范，不增加无关功能、参数、配置键或抽象。
5. 非简单改动先列新增／删除产物、调用方、净数量和明确不做项。只写证明必需行为与可观察结果的测试，执行必需检查。
6. 测试使用内存库、临时库或临时配置。保留真实存档、证书私钥、备份和原始证据。禁止擅自推送、部署、修改真实账号或再次变更系统信任。
7. 原 10 域名临时 hosts 预览已获授权，可按任务需要先备份、临时应用、验收后恢复；授权不扩展域名。普通可逆选择自行处理，确需额外授权时引用约束来源及原文。
8. 游戏由用户手工操作。验收使用整批清单，最后统一回报，不逐项追问。不要绕过既有 Computer Use 未批准状态。
9. 区分源码完成、自动检查通过和客户端验收通过。明确执行计数、继承重复、跳过、告警与缺证；不削弱断言、增加跳过或改基线掩盖失败。
10. 每票做功能复核和单独复杂度复核，记录模型、问题的 fixed／filed／rejected 处置及删除清单。没有可删项就写“无”。承认一类缺陷后扫查同类位置。
11. 用简洁中文持续更新。交付给出 `path:line`、实际命令、退出码、关键值、剩余工作和下一确认点。除新变更、失败或未解决疑点外，不重跑已通过检查。

## B1 已完成的代码和证据

### 冷恢复与既有资产检查

`v5_server/tools/verify_boss_reward_guard.py` 的 `test_claim_history_and_balances_survive_database_reopen` 使用临时文件库，关闭源连接后以新 AccountDB／Core／Connection 重开。45101、余额和领取记录保持；重领码 2013，一键空领不增益，完整性为 ok。

定向 1 项与奖励全套 21 项均退出 0；既有结算串行 5 项、发奖失败 16 项通过结果沿用。周期脚本执行 32 次、退出 1，同一方法的 2 个子用例仍缺指定 `archive/boss_cycle_clock_20261104/before/v5_server/weekly_challenge_service.py`，没有改成 skip，也未拿近似文件替代。日志在 `selftest_tmp/priority-repair/b1-recheck-20261113/`。

### N-1：多维首战后无法进入下一关

真实 PC 332 的 74 字节 battle-info 含英雄 1084 和 2 个精确空队伍槽。旧解析器把空槽当非法角色，导致 characters=None，54032 拒绝结算。原始夹具 SHA256 为 `8643f2f5ef1a72f65fbef67241d17fdfa24c4d2b95ccb1a0a3bcd098765df0b2`，HP 为 8502／10000。

`v5_server/battle_server.py:245` 只跳过精确空的 field10／wire2 槽。全空槽、非空坏 HP、重复字段、错 wire 仍拒绝，总槽数最多 32；无 field10 保留既有兼容，Polyhedron／Hodur／Warchess 的编队名单校验保留。同类已扫，只有这一处共用解析器。

`v5_server/tools/verify_polyhedron_lifecycle.py:220` 新增真实 battle-info 集成用例，合成外层后走现有 parser→Core54032→保存 HP→18012→18014。`verify_hodur_challenge.py:64` 扩展既有坏包用例，保持全空战报拒绝。改前定向 2 项退出 1，新增例失败；修后定向 3 项退出 0。

受影响检查的实际命令：

| 工作目录 | 命令 | 结果 |
| --- | --- | --- |
| `v5_server` | `python -B -X utf8 tools/verify_polyhedron_lifecycle.py` | 35 项，exit 0 |
| `v5_server` | `python -B -X utf8 tools/verify_hodur_challenge.py` | 20 项，exit 0 |
| `v5_server/tools` | `python -B -X utf8 -m unittest verify_warchess_state.WarChessTests.test_battle_reentry_replaces_prior_attempt_and_health_report_rejects_bad_team` | 1 项，exit 0 |

定向与继承有重复，不相加为独立覆盖。既有 skeleton ResourceWarning 仍归 A2-W01。

实机复验：用户回报“正常了”。同一 UID `261113200139` 的 54032→18012→18014 已记录；前／后场景 `3035111→3035401`、battle_count `0→1`、hp_report_complete `false→true`，英雄 1084 当前 HP `9250/10000`，两份 quick_check 均为 ok。本场与 8502／10000 的原始夹具来自不同战斗。该证据只证明原推进故障已恢复；完整一局、任务和成就仍未验。

证据位于 `selftest_tmp/priority-repair/b1-client-20261114/`：`n1-client-fixed-acceptance.json`、`pc332-empty-slots-fix.json`、`pc332-battle-info-1.bin`、`server-fixed.log:219/225/230`、各专项日志，以及 `snapshots/11-before-fixed-client.db`、`snapshots/n1-after-fixed-client.db`。

根 Codex 与 `gpt-6-luna/high` 已完成功能、共享路径／权限边界及单独复杂度复核。本次提交包含 2 个新增类内测试：冷重开和真实战报集成；生产模块／类／顶层函数／参数／配置键净增均为 0。已删除临时原始战报诊断块及过期活动状态说明；剩余删除清单为“无”。提交前又核对了全部 4 个代码差异，未发现新问题，未重复跑测试。

## B1 剩余工作

- **N-2 联合特勤：filed，未修复。** 这是 chapter 203／stage_type 8 的普通刻印材料入口，不能仅凭名称归为多人封锁。三次登录证实新档 SC42001 下发空列表；本地原生视图固定读取 3 个组，与黑屏相符，但没有当前客户端 Lua 栈。42002 无真实 handler，42004 仅空 42005 模板。旧 master 的 `[9,27,17]` 和其他 owner 刷新计数不证明 332 新档规则。缺权威初始化／分组契约时先取证，不猜默认组，也不扩完整刷新玩法或解除 R18 封锁。入口线索在 `v5_server/login.py:300`、`schema_default.py:88`；本地 Lua 位于 `C:\Users\<user>\Desktop\解包\Lua源码库\Lua源码\game\`，未证明属于 332。
- **完整多维与逐项数值仍缺证。** 用户整批报告“其余正常”，不重做已过项目，不把汇总当作每项三阶段数值／截图。M2 第 1 项已证票 20→10、10 条抽卡记录、新角色 1056、重复转 10 碎片、8 个钥从、110 辉芒，重登保持。第 8 项邮件 1020 库内 attach_flag=2；第 9 项礼物 30012 仍为 5，缺赠礼消耗请求证据。详细状态以客户端验收表为准。
- **M2 第 12 项仅为可选观察。** 1032018／1032019 缺本轮同场证据；不自动展开 B2 的 1032020、转储分析或三关修复。
- **B1-C01 小 UID 兼容仍 filed。** SDK 的 Int32→Int64 异常由更换隔离夹具为正常分配的 12 位 UID 绕过，未修生产小 UID 接口。

## 本机隔离环境与清理

运行副本为 `selftest_tmp/priority-repair/b1-client-20261114/runtime/v5_server`，昵称 `B1隔离验收`、UID `261113200139`，区服第 3 项 `【当前】account`。只使用本票账号库；旧 B0、旧 B1、真实主库和备份保留。ACCOUNT_DB_PATH、AETHERGAZER_SERVER_CONFIG、聊天根与 CLI `--db` 应显式绑定本副本，启动前回读挂载路径和主人。不要依赖旧 flat launch_config 的字段覆盖。

冻结资源缓存有意复用 `selftest_tmp/priority-repair/b0-local-client/asset-cache`。CDN off、capture false；不因目录名不同复制整套缓存或引入新配置。

游戏本体是 `C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili\AetherGazer_Bili.exe`，由用户直接启动。安装文件只读。本机目标 app 307／resource build 332／v5.3.6；SDK gateway version 308、渠道 10 分开记录，不能强行写为同一版本。

本轮服务 PID 24768／exec 35738 已退出，游戏进程数为 0。Ctrl+C 退出码 1 不算优雅退出通过。hosts Restore 退出 0，原始 65492 字节及 SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54` 完全一致；35 个 TCP 端口及 UDP 6105 可独占绑定，9 个保护文件与客户端主清单未变。

Restore 回执的即时 10 域解析仍为 127.0.0.1，原回执保留；后续新进程 Windows getaddrinfo 与 .NET 均确认两个关键域为 203.107.63.115，仅声明两域回读。最新证据是本票目录的 `running-service.json`、`cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`、`dns-system-after-restore.json`。不要把历史活动 PID 或旧回执当作当前状态，也不要原样输出含凭据的 SDK 日志。

## 保留的其他阶段结果

- A1 证书部署、两处 Windows 根信任和本机 HTTPS 已验。严格 CRL 限制仍登记，不写成全过，不再次替根或安装信任。
- A2 的 10 个必需脚本均退出 0；156 次执行含继承重复，含 1 项历史归档缺失的既有 skip。原生缺证、严格 CRL 限制和 A2-W01 资源关闭告警保留。
- B0 的 332 完整资源及联网主界面／角色／背包／重登已通过。71,275 个唯一对象、63,325,313,135 字节，缺失／坏对象均为 0。存储 16／探测 5／分发 21／连接版本 13 均 exit 0。断网冷启动仍弹 B 站认证，B0-S01 按用户指示后置，整票 partial；联网成功不能覆盖离线失败。
- .NET SDK 10.0.404 已安装，启动壳构建通过；D 的托管重启未验。C 的 API／浏览器通过，游戏内完整验收未完；B3 只有内存预设证据。
- E 已交付契约与取证；F 完整自然游玩未完。G 真实样本仍缺 10 封同会话普通邮件和 144 个协议审核，不发布真实恢复档。H1 的 10 份 reviewed=false 稿待用户审校；H2 实际拆分仍受 M2 门禁约束。
