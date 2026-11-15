# 修复计划交接提示词

B2、B3 的本机 PC 332 实机核对均已完成。B3 同场初始化、三档前驱对照及方案 A 分支通过，旧票已回填 `client_verified`。服务和游戏已退出，hosts 与启动器配置已恢复；接续 20 项保护基线一致。午后误挂前的主库 WAL 基线缺证独立保留。[本场结果](2026-11-13-client-acceptance.md#b3-同场实机2026-11-15)

## B3 收尾位置

连续进度在 `selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/session-progress.json`。快速体验和普通新档结束快照位于该目录；最终跳序章、分支快照及恢复回执位于 `resume-01/`。四份起始档未变，已有通过项不重做。

跳序章原始 1 级门槛已记录，前驱对照使用补经验至 5 级的运行副本；分支仍使用方案 A 的 `branch_pending`。开发版启动器午后曾误挂工作区主库，接续改为从隔离核心直接启动并回读数据库绝对路径。此前 WAL 缺证见验收表，保留现有审计副本，不以旧文件覆盖主库。当前无须继续 B3；其他批次等待用户指定。

## B2 历史交接提示词（已执行）

在同一项目、同一工作目录打开新会话，把下面这段作为第一条消息发送。本机未提交的计划修订和被 Git 忽略的隔离证据都在这个目录。

> 请在 `C:\Users\<user>\Desktop\Alpha-Persei-Cluster` 接手。我确认本次只执行 B2（M-5 三关复验）。先读 `AGENTS.md` 和 `docs/plans/2026-11-13-repair-handoff.md`。按总计划准备 PC 332 隔离档，确认首关 1032018 可进入后，一次性给我三关操作清单。游戏由我操作。请逐关核对同场日志，回填结果并恢复临时环境。B2 结束后停下，B3 等我另行确认。

## B2 历史接手步骤

1. 在仓库根目录运行 `git status --short --branch` 和 `git log -3 --oneline`，保留已有改动。代码基线为 B1 收尾提交 `0112cd0`。
2. 读仓库 `AGENTS.md`、[B2 计划](2026-11-12-repair-plan.md#b2-复验-m-5)、[进度台账](2026-11-12-repair-progress.md)和[三关验收表](2026-11-13-client-acceptance.md#b2m-5-三关复核)。历史 M-5 日志只作对照。
3. 准备 B2 专用隔离档。总计划中的“快速体验＋预通章节 10120”已通过内存档验证，实机档仍待准备。B1 的 `selftest_tmp/priority-repair/b1-client-20261114/gift-recheck-20261114T111341Z/04-after-stop.db` 为 70 级，三关均锁定。起服前回读本票数据库路径、UID、三关的通关次数和首关可进入状态。
4. 环境就绪后交给用户操作。将证据放在 `selftest_tmp/priority-repair/` 的本票目录，在验收表和台账回填结果。票结束时核对进程和临时 hosts 恢复情况。

本机证据由 Git 忽略，原始 SDK 日志含凭据。换机器时先核对必要资料是否在场，交接时只提供所需的脱敏结果。

## 执行与停止规则

1. 每次只执行用户已确认的票。B3 已收尾，后续按用户本次指示执行。
2. 使用子代理驱动执行，默认 `gpt-6-luna`、`high`。根代理串行修改共享文件。共享执行路径和权限边界由不同模型复核。
3. 读取可用的 5 小时和周额度。任一剩余不超过 10% 时停止，清理临时环境并保存交接。无法读取时如实说明，不自动重置。用户回报通过后的回读为 92%／48%，未使用重置；接续时重新读取。
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

## B1 归档与遗留

- **N-2 联合特勤保留登记。** 332 客户端需要 3 个初始组，仍缺可信的新档成功样本或服务端选择规则。用户已决定本轮不修复。此前取证和来源见[进度台账](2026-11-12-repair-progress.md)。
- **完整多维与其余逐项数值：已归档完成。** 2026-11-14 用户决定：M2 第 2～7、10 项与赠礼后重登不再逐项补三阶段截图，按“已完成”归档。第 1 项抽卡三阶段快照保留；第 8 项 1020／1022／1023 均 `attach_flag=2`；第 9 项隔离库回读 `material 50001 num=1`、`hero_archive 1045 exp=20`、`gift_list=[{"id":50001,"num":4}]`；第 11 项场景 3035111→3035401、`battle_count=1`、HP 9250/10000。今后不再以缺截图重复开票。
- **M2 第 12 项在 B1 为可选观察。** 后续 B2 已完成 `1032018/1032019/1032020` 三关实机复验，均正常结算并返回主城，本轮未复现卡死。
- **B1-C01 历史处置。** `0112cd0` 将 Mix 登录 ID 改为字符串，通过了服务端数值回读，未验证客户端反序列化。B3 的新证据见下节。
- **B1-R01 已 fixed。** 332 冻结缓存 `selftest_tmp/priority-repair/b0-local-client/asset-cache`（1846 个 `.ys`、6,266,198,823 字节）此前不在 `cdn_proxy.cache_roots('pc')`，`find_cached_file` 必然 MISS（实测 `0017fcd338ae9791400e0726ca569b04.ys` 返回 `None`）。已通过既有配置项 `storage.cdn_read_roots` 登记为只读历史根（`../selftest_tmp/priority-repair/b0-local-client/asset-cache`），未改 `cdn_cache_dir`、未复制缓存、未改代码。登记后 200 个随机样本全部 HIT 且 MD5 校验通过。
- **本轮回归：** `verify_resource_storage.py` 16 项 exit 0；`test_cdn_foundation.py` 30 项 exit 0；`verify_client_version.py` 13 项 exit 0；`verify_gateway_handoff.py` 7 项 exit 0。新增／删除模块、类、顶层函数、参数、配置键均为 0；`cdn_read_roots` 为既有键。

## B2 与 B3 历史状态（2026-11-14 夜间）

- **B2 已完成。** PC 332 实机：`1032018`／`1032019`／`1032020` 三关均自然进场、`cs_54032` 结算并回主城，`clear_times` 全为 1，未卡死未采转储。M-5 记「332 本轮未复现」。证据 `selftest_tmp/priority-repair/b2-run-20261114/server.log`。
- **B3 当时未完成。** 四份隔离档已装配并通过内存回读（`fresh` 0／`skip_prologue` 7／`quick_start` 48 预通，外加 70 级分支变体 39 预通），但客户端停在「客户端初始化」，当时三档与分支对照均无实机结果，旧票未回填。11 月 15 日已接续完成，当前结果见[验收表 B3 节](2026-11-13-client-acceptance.md#b3-同场实机2026-11-15)。
- **B3 接续操作（11 月 15 日）。** 四份独立档的 UID 均为 `261113200139`。快速体验档的运行副本为 `launcher-check/v5_server/account.db`，同目录的 `data/slot_registry.json` 已登记槽位 3。便携版 `AetherGazer_Server_v5.0_Portable/LocalServer.exe` 优先加载包内核心。[本轮启动与区服记录](2026-11-13-client-acceptance.md#b3-修复后核对)
- **一项独立观察（未修）。** 新建 UID 的隔离档冷启动时，客户端会请求 `/game-website-server/pass/sdk/*`（`get_index_config`／`get_menu_info`／`get_news`／`get_slide_image`／`get_update_version`），仓库内无任何实现，落 `server_net.py` 末尾兜底空 `data:{}`，客户端重试后停在初始化。超出 B2／B3 范围，未改代码，待单独决定是否开票。

## B1 隔离环境与历史清理记录

B1 使用的运行副本为 `selftest_tmp/priority-repair/b1-client-20261114/runtime/v5_server`，账号 UID 为 `261113200139`。B2 起服时将 `ACCOUNT_DB_PATH`、`AETHERGAZER_SERVER_CONFIG`、聊天根和 CLI `--db` 绑定本票副本，回读挂载路径和主人。保留 B0、B1 原件和真实存档。

冻结资源缓存有意复用 `selftest_tmp/priority-repair/b0-local-client/asset-cache`。CDN off、capture false；不因目录名不同复制整套缓存或引入新配置。

游戏本体是 `C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili\AetherGazer_Bili.exe`，由用户直接启动。安装文件只读。本机目标 app 307／resource build 332／v5.3.6；SDK gateway version 308、渠道 10 分开记录，不能强行写为同一版本。

上轮服务 PID 24768／exec 35738 已退出，游戏进程数为 0。Ctrl+C 退出码 1 不算优雅退出通过。hosts Restore 退出 0，原始 65492 字节及 SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54` 完全一致；当时 35 个 TCP 端口及 UDP 6105 可独占绑定，9 个保护文件与客户端主清单未变。

本轮 N-2 取证未启动服务或改 hosts。`evidence.json.environment_readback` 保存新回读：hosts 原字节、9 个保护文件及当前安装主清单均不变，13 个指定本机证据文件／目录均在。独占绑定为 TCP 33/35、UDP 6105 通过；8110、8111 返回 WinError 10013，环境检查 exit 1。随后 `netstat` 观察到对应 Codex／verge-mihomo 出站连接，未显示监听；未证明绑定失败的完整原因，也未停止这些进程。CIM 查询拒绝访问 exit 1；`Get-Process` exit 0，未见游戏、LocalServer 或 Python 进程。下次起服前重检，不沿用旧 35/35。指定周期 before 归档仍缺，旧 2 error 不改为 skip。

上轮 Restore 回执的即时 10 域解析仍为 127.0.0.1，原回执保留；后续新进程 Windows getaddrinfo 与 .NET 均确认两个关键域为 203.107.63.115，仅声明两域回读。上轮证据是 `b1-client-20261114/` 下的 `running-service.json`、`cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`、`dns-system-after-restore.json`。不要把历史活动 PID 或旧回执当作当前状态，也不要原样输出含凭据的 SDK 日志。

## 保留的其他阶段结果

- A1 证书部署、两处 Windows 根信任和本机 HTTPS 已验。严格 CRL 限制仍登记，不写成全过，不再次替根或安装信任。
- A2 的 10 个必需脚本均退出 0；156 次执行含继承重复，含 1 项历史归档缺失的既有 skip。原生缺证、严格 CRL 限制和 A2-W01 资源关闭告警保留。
- B0 的 332 完整资源及联网主界面／角色／背包／重登已通过。71,275 个唯一对象、63,325,313,135 字节，缺失／坏对象均为 0。存储 16／探测 5／分发 21／连接版本 13 均 exit 0。断网冷启动仍弹 B 站认证，B0-S01 按用户指示后置，整票 partial；联网成功不能覆盖离线失败。
- .NET SDK 10.0.404 已安装，启动壳构建通过。D 的托管重启未验。C 的 API／浏览器通过，游戏内完整验收未完。
- E 已交付契约与取证；F 完整自然游玩未完。G 真实样本仍缺 10 封同会话普通邮件和 144 个协议审核，不发布真实恢复档。H1 的 10 份 reviewed=false 稿待用户审校；H2 实际拆分仍受 M2 门禁约束。
