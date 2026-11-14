# 修复计划交接提示词

2026-11-14：用户确认礼物“验证通过”。实际领取 5 本、连续送出 4 本，剩 1 本，档案经验 0→20；文件冷读保持。赠礼后第二次登录的独立证据仍缺。服务已停、hosts 原字节恢复；B1 仍为 partial，其余正常项目不重做。

此前取证已从可信 332 包提取消费代码、候选组配置及协议定义，共 9 个文件；新档选组与计数规则仍缺。取证结束不等于整张 B1 停止；当前状态如下。

**当前隔离服务和临时 hosts 已清理。** PID18388 已停止，exec35371 exit 1；Ctrl+C 未生效后只精确停止本 PID，不算优雅退出通过。hosts Restore exit 0，与原始 65,492 字节相同，35 TCP＋UDP6105 可独占绑定；源 9 个保护文件、运行副本 8 个证书／私钥和客户端主清单未变。独立 DNS 当前返回 198.18.0.4／198.18.0.5，未沿用历史解析值。最新 `running-service.json` 已为 active=false。4 份文档改动保留，未提交、未推送。

最近会话只用已有 CLI `--gw-port 18102` 避开外部占用；旧 launch_config 已恢复原字节。实际 HTTPS／SDK 曾回读 UID 261113200139／B1隔离验收／slot 3端口18104／332／CDN off／capture false。隔离叶证书自动更新，8 个旧证书／私钥备份保留，原根和 Windows 信任未改。最近证据目录为 `b1-client-20261114/resume-20261114T070645Z/`，含快照、原始日志、清理回执和 `gift-diagnosis/diagnosis.json`。

礼物收尾：1023 已领，用户实际向 1045「赤音／亚莉莎」连续赠送 4 本 50001，均走 14100，一本 +5，档案经验 0→20、gift_list 记 4、库存剩 1。30012×10 和所有角色交心值未变。用户确认通过，显示／领取／赠礼及入库已验；停服后文件冷读保持。日志只有赠礼前一次登录，赠礼后重登独立证据 filed，不把冷读替代重登，也不把本项通过写成 M2 全过。

本轮证据为 `b1-client-20261114/gift-recheck-20261114T111341Z/`，含准备及验收／停服快照、`after-client-acceptance.json`、332 赠礼页源码、完整命令、复核和清理回执。`server.log:210` 是 30004 领取；:229／235／238／241 是赠礼，:253 是退出。原始 SDK 日志含凭据，不原样输出。根 Codex／Luna 已复核，复杂度删除清单无；本轮生产代码及测试未变。B1 剩余仍是 N-2 规则、完整多维和其他逐项数值缺证。

先核对仓库与本机证据，在已确认的 B1 范围内继续。B1 收尾后才等待下一票确认，不自动进入 B2。

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

## B1 剩余工作

- **N-2 联合特勤：filed，未修复。** 这是 chapter 203／stage_type 8 的普通刻印材料入口。新档 SC42001 空列表与可信 332 视图固定读取 3 组冲突；当前客户端 Lua 栈仍缺。332 客户端发送 42002；服务端未见 42002／42004 专用业务处理器，42004 只有空 42005 模板。本轮证据包为 `selftest_tmp/priority-repair/b1-n2-evidence-20261114/`：9 个文件均有字节码／Lua 哈希、LJD 实际命令及 exit 0；`p42_pb` 的 4 个消息、6 个字段与仓库 schema 相符，StageGroupCfg 有 30 个 type 8 候选组。索引与冻结 332 主清单相同，scripts64 与安装源相同。仍缺新档三组的选择、顺序、去重、权重、计数初值及周期迁移规则；协议默认值及 GameSetting 的阈值／费用不能替代业务规则。旧 master `[9,27,17]` 和其他 owner 计数继续仅作历史线索。公开检索未取得可用解法，GitHub 代码搜索不可读，范围不完整。下票先补可信成功初始化样本或服务端规则，不猜组，不扩完整刷新玩法或解除 R18 封锁。详见进度台账“N-2 取证接续”，含根 Codex／Luna 的功能与复杂度复核。

  **2026-11-14 补证（只读取证，未实施修复）：** 对 332 `scripts64.ys` 全部 TextAsset（排除 config／laterconfig／qworld）做内存级常量扫描，命中 70 个对象，确认 42001～42005 仅出现在 `p42_pb.lua`、`ignoreMod` 的 LazyLoad 名表、`BattleEnchantAction.lua` 与大量 story 脚本；`BattleEnchantmentData` 由 `DataInclude.lua:293` 全局注入，`RedPointMgr` 无 `DAILY_EQUIP_ENCHANT` 逻辑（仅 `ChapterEquipEnchantmentItemView.lua` 与 `redpointMgr` 常量表命中）。`ChapterConst.DAILY_EQUIP_ENCHANT = 203`、`RedPointConst.DAILY_EQUIP_ENCHANT` 与 `SystemLinkCfg[318]`（system_id 309、link `/enchantment`）构成入口链路。`StageGroupCfg` type 8 分布为 level1＝15／level2＝10／level3＝5 共 30 组，203 系列 90 关在 `stage_meta.json` 中齐全且全部 `max_star=3`；`daily_stage_drop_cfg.json` 的 203 键与 90 关一一对应，掉落库仅 210001／210002／210003 三档。真实 9/26 登录与 9/27 补抓的 42001 帧均为 `08021000180b18081805`，解码为 `{free=2, buy=0, list=[11,8,5]}`，9/26 另见 `[11,6,5]`——证明同一账号跨日组集会变，但这是已有账号刷新结果，仍不能作为新档初值。`GameTimer.GetNextDayFreshTime` 与 `PlayerAction.RequestNewDayData`（cs_10500→sc_10501）说明跨日刷新走通用 NEW_DAY 通道，43200 秒级倒计时由 `GameSetting.fm_*` 驱动；`TipsCfg[60227]` 明确「每日刷新次数重置」，`TipsCfg[71452]`（EQUIP_STAGE_REFRESH）为「当前已存在高价值任务，是否确认刷新？」——这仅为确认弹窗，不是服务端权重规则。结论不变：仍缺新档选择／顺序／去重／权重与刷新计数初值的权威来源，不猜值、不实施。
- **完整多维与其余逐项数值：已归档完成。** 2026-11-14 用户决定：M2 第 2～7、10 项与赠礼后重登不再逐项补三阶段截图，按“已完成”归档。第 1 项抽卡三阶段快照保留；第 8 项 1020／1022／1023 均 `attach_flag=2`；第 9 项隔离库回读 `material 50001 num=1`、`hero_archive 1045 exp=20`、`gift_list=[{"id":50001,"num":4}]`；第 11 项场景 3035111→3035401、`battle_count=1`、HP 9250/10000。今后不再以缺截图重复开票。
- **M2 第 12 项仅为可选观察。** 1032018／1032019 缺本轮同场证据；不自动展开 B2 的 1032020、转储分析或三关修复。
- **B1-C01 已 fixed。** `v5_server/server_net.py:1758` 的 Mix SDK 登录 `data.id` 由裸数字改为字符串。原存档主人 `2174928301` 已超 `Int32`（`2^31-1=2147483647`），12 位 UID 超得更多；区服列表 `save_slot_manager.py:880-882` 本就下发字符串，两端现已一致。`42`／`2174928301`／`261113200139` 三种 UID 验证可无损回读。
- **B1-R01 已 fixed。** 332 冻结缓存 `selftest_tmp/priority-repair/b0-local-client/asset-cache`（1846 个 `.ys`、6,266,198,823 字节）此前不在 `cdn_proxy.cache_roots('pc')`，`find_cached_file` 必然 MISS（实测 `0017fcd338ae9791400e0726ca569b04.ys` 返回 `None`）。已通过既有配置项 `storage.cdn_read_roots` 登记为只读历史根（`../selftest_tmp/priority-repair/b0-local-client/asset-cache`），未改 `cdn_cache_dir`、未复制缓存、未改代码。登记后 200 个随机样本全部 HIT 且 MD5 校验通过。
- **本轮回归：** `verify_resource_storage.py` 16 项 exit 0；`test_cdn_foundation.py` 30 项 exit 0；`verify_client_version.py` 13 项 exit 0；`verify_gateway_handoff.py` 7 项 exit 0。新增／删除模块、类、顶层函数、参数、配置键均为 0；`cdn_read_roots` 为既有键。

## 本机隔离环境与清理

运行副本为 `selftest_tmp/priority-repair/b1-client-20261114/runtime/v5_server`，昵称 `B1隔离验收`、UID `261113200139`，区服第 3 项 `【当前】account`。只使用本票账号库；旧 B0、旧 B1、真实主库和备份保留。ACCOUNT_DB_PATH、AETHERGAZER_SERVER_CONFIG、聊天根与 CLI `--db` 应显式绑定本副本，启动前回读挂载路径和主人。不要依赖旧 flat launch_config 的字段覆盖。

冻结资源缓存有意复用 `selftest_tmp/priority-repair/b0-local-client/asset-cache`。CDN off、capture false；不因目录名不同复制整套缓存或引入新配置。

游戏本体是 `C:\Program Files\AetherGazerStarter_Bili\AetherGazer_Bili\AetherGazer_Bili.exe`，由用户直接启动。安装文件只读。本机目标 app 307／resource build 332／v5.3.6；SDK gateway version 308、渠道 10 分开记录，不能强行写为同一版本。

上轮服务 PID 24768／exec 35738 已退出，游戏进程数为 0。Ctrl+C 退出码 1 不算优雅退出通过。hosts Restore 退出 0，原始 65492 字节及 SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54` 完全一致；当时 35 个 TCP 端口及 UDP 6105 可独占绑定，9 个保护文件与客户端主清单未变。

本轮 N-2 取证未启动服务或改 hosts。`evidence.json.environment_readback` 保存新回读：hosts 原字节、9 个保护文件及当前安装主清单均不变，13 个指定本机证据文件／目录均在。独占绑定为 TCP 33/35、UDP 6105 通过；8110、8111 返回 WinError 10013，环境检查 exit 1。随后 `netstat` 观察到对应 Codex／verge-mihomo 出站连接，未显示监听；未证明绑定失败的完整原因，也未停止这些进程。CIM 查询拒绝访问 exit 1；`Get-Process` exit 0，未见游戏、LocalServer 或 Python 进程。下次起服前重检，不沿用旧 35/35。指定周期 before 归档仍缺，旧 2 error 不改为 skip。

上轮 Restore 回执的即时 10 域解析仍为 127.0.0.1，原回执保留；后续新进程 Windows getaddrinfo 与 .NET 均确认两个关键域为 203.107.63.115，仅声明两域回读。上轮证据是 `b1-client-20261114/` 下的 `running-service.json`、`cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`、`dns-system-after-restore.json`。不要把历史活动 PID 或旧回执当作当前状态，也不要原样输出含凭据的 SDK 日志。

## 保留的其他阶段结果

- A1 证书部署、两处 Windows 根信任和本机 HTTPS 已验。严格 CRL 限制仍登记，不写成全过，不再次替根或安装信任。
- A2 的 10 个必需脚本均退出 0；156 次执行含继承重复，含 1 项历史归档缺失的既有 skip。原生缺证、严格 CRL 限制和 A2-W01 资源关闭告警保留。
- B0 的 332 完整资源及联网主界面／角色／背包／重登已通过。71,275 个唯一对象、63,325,313,135 字节，缺失／坏对象均为 0。存储 16／探测 5／分发 21／连接版本 13 均 exit 0。断网冷启动仍弹 B 站认证，B0-S01 按用户指示后置，整票 partial；联网成功不能覆盖离线失败。
- .NET SDK 10.0.404 已安装，启动壳构建通过；D 的托管重启未验。C 的 API／浏览器通过，游戏内完整验收未完；B3 只有内存预设证据。
- E 已交付契约与取证；F 完整自然游玩未完。G 真实样本仍缺 10 封同会话普通邮件和 144 个协议审核，不发布真实恢复档。H1 的 10 份 reviewed=false 稿待用户审校；H2 实际拆分仍受 M2 门禁约束。
