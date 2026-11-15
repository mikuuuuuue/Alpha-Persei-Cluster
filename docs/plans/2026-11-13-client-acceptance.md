# 客户端验收记录

本记录分开标记源码、自动检查和游戏客户端结果。自动检查不代替自然游玩、退出重登或客户端截图。

## 当前结论

- 2026-11-14 用户决定：M2 第 2～7、10 项与赠礼后重登按“已完成”归档，不再逐项补三阶段截图；B1 剩余只做 B1-C01 与 B1-R01 两项，均已在本轮实施。
- **B1-C01 的原验收仅覆盖服务端回读。** B3 的客户端与运行副本证据重新指向 Mix 登录响应的 `data.id` 类型。详见[初始化离线排查](#b3-初始化离线排查)。
- **B1-R01 已 fixed。** 332 冻结资源缓存 `selftest_tmp/priority-repair/b0-local-client/asset-cache`（1846 个 `.ys`、6,266,198,823 字节）此前不在 `cdn_proxy.cache_roots('pc')`，`find_cached_file` 必然 MISS。已通过既有配置项 `cdn_read_roots` 登记为只读历史根，未改 `cdn_cache_dir`、未复制缓存、未改代码。
- 联合特勤 N-2 按用户决定维持 filed、不修复；其缺口已收敛为“新档初始三组抽样来源”一项，其余四项已排除。
- B0 已保存为本地提交 ce761b7。本机 `307/332/v5.3.6` 资源、联网主界面、角色／背包和重登已有证据；仅 B0-S01 断网渠道认证按用户指示后置，整票 partial。
- B1 的多维首战后推进失败 N-1 已完成修复与实机复验；M2 数值走查与赠礼后重登按用户决定归档完成。B2、B3 的后续结果见下一条。
- B2、B3 的本机 PC 332 实机核对已完成。B3 同场初始化、三档前驱对照及方案 A 分支均通过。跳序章的原始 1 级门槛已记录，前驱对照使用补经验至 5 级的运行副本。服务已停，hosts 和启动器配置已恢复；午后误挂主库时的 WAL 基线缺证独立保留。[本轮实机结果](#b3-同场实机2026-11-15)
- F：15 个入口都没有客户端验收。现有 15 份专项日志共运行 291 项，6 份全通过；9 份各有 1 个依赖错误，断言失败为 0。
- 爬塔、换装池：本轮没有客户端结果；内存 Core 与冷读专项见文末，不能替代客户端。
- A1 已按本轮授权完成根替换、叶续签、分发同步和两处 Windows 根信任安装；文件、Windows 链与本机 HTTPS 探针通过。本轮游戏初始化及更新阶段结果见下文；不将其算作 M2 数值验收。

### 11 月 14 日历史回读（B1-C01 结论已修正）

下表保留当时的服务端回读。字符串 ID 未通过客户端验收；当前 Mix 登录已恢复数字 ID，并以正常分配的 12 位 UID 完成 PC 332 实机验证。旧小 UID 的兼容仍待验证，详见下文“B3 初始化离线排查”。

| 项 | 命令 | 结果 |
| --- | --- | --- |
| B1-C01 | `python -B -X utf8 -`（JSON 形状探针，UID 42／2174928301／261113200139） | 三者均序列化为 `"id": "<uid>"` 字符串，回读无损；修前 `2174928301` 为裸数字且超 Int32 |
| B1-R01 | `python -B -X utf8 -`（`find_cached_file` 探针） | 修前 `0017fcd338ae9791400e0726ca569b04.ys` 返回 `None`；登记后 200/200 随机样本全部 HIT，MD5 校验通过 |
| 回归 | `python -B -X utf8 v5_server/tools/verify_resource_storage.py` | 16 项，exit 0 |
| 回归 | `python -B -X utf8 v5_server/tools/test_cdn_foundation.py` | 30 项，exit 0 |
| 回归 | `python -B -X utf8 v5_server/tools/verify_client_version.py` | 13 项，exit 0 |
| 回归 | `python -B -X utf8 v5_server/tools/verify_gateway_handoff.py` | 7 项，exit 0 |

改动面：`v5_server/server_net.py` 一行表达式加两行注释；`v5_server/server_config.json` 的 `storage.cdn_read_roots` 增加一条相对路径。新增／删除模块、类、顶层函数、参数、配置键均为 0，未新增配置键（`cdn_read_roots` 为既有项）。

既有 B1 复验：N-1 原推进故障已修并通过一次实机复验，场景 3035111→3035401。联合特勤 N-2 维持 filed。B0-S01 后置，不进入 B2。

**上轮清理记录。** PID `24768` 和游戏进程均已退出，exec `35738` 经 Ctrl+C 退出 `1`；Restore 退出 `0`，hosts 与原始 65492 字节完全一致。当时 35 TCP＋UDP 6105 可独占绑定，保护 9 文件与客户端主清单未变；两关键域独立 DNS 回读为 `203.107.63.115`。证据为 `b1-client-20261114/cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`。本轮最新回读见下节。

## B1：N-2 初始化取证接续

后续曾在同一 B1 中恢复独立客户端验收，PID 38872／exec 54815；slot 3 为 `【当前】account`／UID 261113200139。默认 TLS、实际 SDK 列表和监听回读通过。用户反馈后因额度 9% 停止，该服务及 hosts 现已恢复。新证据在 `b1-client-20261114/resume-20261114T070645Z/`。N-2 取证不作为整票停点；当前待办为礼物夹具修正和复验。

此前 N-2 取证阶段没有运行游戏或修复生产代码。N-2 仍为 filed，B1 仍为 partial；M2 各项客户端状态保持 M2 节记录，准备就绪不算通过。

从已校验的 307／332／v5.3.6 `scripts64.ys` 定向提取 9 个文件。索引与 B0 冻结清单相同，包与当前安装源相同。9 次 LJD 均 exit 0；证据为 `selftest_tmp/priority-repair/b1-n2-evidence-20261114/evidence.json`，包含来源、完整命令、大小和哈希。

| 已确认事实 | 证据位置（相对本轮证据包） | 仍未证明 |
| --- | --- | --- |
| 332 入口固定读取 3 个组 | `lua/game/views/equipenchantmentstage/enchantmentstageview.lua:302` | 本次黑屏的实际 Lua 栈 |
| 42001 的计数和列表直接写入客户端状态 | `lua/game/data/battleenchantmentdata.lua:25` | 服务端计数初值与周期迁移规则 |
| 30 个 type 8 候选组，各有 3 个难度关卡 | `lua/game/config/stagegroupcfg.lua:1` | 新档三组选择、顺序、去重和权重 |
| 4 个消息、6 个字段与仓库 schema 相符 | `lua/protocol/p42_pb.lua:21` | 有效 332 新档初始化响应的实际取值 |
| 客户端刷新阈值、费用和解锁等级 | `lua/game/config/gamesetting.lua:216` | 服务端初始化及刷新规则 |

协议描述符的默认 0／空列表不证明业务初值。旧 master 分组和其他账号刷新计数仍不能作为新档规则。

此前取证阶段的环境回读：hosts 原字节、保护 9 文件和安装主清单不变；33/35 个 TCP 端口及 UDP 6105 可独占绑定。8110、8111 返回 WinError 10013，并观察到外部出站连接。后续真实监听预检确认这两个端口占用，现用临时 CLI 网关池避开。当前活动状态见本节首段，不沿用当时的无进程／hosts 未应用状态。

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
| 1 | 抽卡十连扣费与产出 | 共享自动结果见上；实际取证使用332隔离档。 | 完成。票20→10、10记录、新角色1056＋重复碎片＋8钥从＋辉芒110，三阶段快照一致；截图未回传。 |
| 2 | 商城购买扣费 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。 |
| 3 | 体力购买与消耗 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。 |
| 4 | 角色升级消耗与经验 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。 |
| 5 | 刻印分解返还 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。联合特勤黑屏另列 N-2。 |
| 6 | 任务领奖入包 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。 |
| 7 | 周常／活跃奖励领取 | 共享自动结果见上。 | 完成。用户确认；本轮按决定归档，不补逐项截图。 |
| 8 | 邮件附件领取 | `02-12-after-batch.db` 回读邮件 1020 的 `attach_flag=2`；隔离库回读 1020／1022／1023 均为 `attach_flag=2`。 | 完成。库证已领取。 |
| 9 | 好感度礼物消耗 | 1023 已领；4 次 14100 各扣 50001×1，最后库存 1、1045 档案经验 20；原 30012×10 和交心值未变，停服冷读保持。 | 完成。用户确认通过；隔离库回读 `material 50001 num=1`、`hero_archive 1045 exp=20`、`gift_list=[{"id":50001,"num":4}]`。 |
| 10 | 第 1～9 项重登后数值 | 第 1 项已有重登快照。 | 完成。用户确认；本轮按决定归档，不补逐项重登截图。 |
| 11 | 多维变量通关、任务与成就提示 | N-1 真实 battle-info 回归保存 8502/10000 并推进；多维 35／Hodur 20／战棋定向 1 通过。 | 完成。N-1 推进实机通过：场景 3035111→3035401、battle_count 0→1、实际 HP 9250/10000。整局与任务／成就按用户决定归档。 |
| 12 | 1032018、1032019 终局卡死观察 | 当前无这两关的本轮同场日志或转储。 | 可选观察项，不展开 B2。 |

历史基础回归日志为 `m2-defect.log`／`smoke.log`。本轮各项状态以上表为准；下面是 B0 之前的初始化与资源更新历史：

- **B1-C01 历史处置。** 原小 UID `42` 曾触发 `Int32→Int64` 解析异常。切换为 12 位 UID 后，当时的数字响应成功越过初始化。`0112cd0` 后的字符串响应只验证了服务端回读。
- **B1-R01 历史与处置：** B0 本次后的资源更新曾因服务端选 `307/321` 而 404（2928 条访问、82 个不同文件名、清单合计 `244992009` 字节）。B0 已改为 332 并补齐资源。本轮发现真正问题在缓存根：332 缓存 `selftest_tmp/priority-repair/b0-local-client/asset-cache`（1846 个 `.ys`、6,266,198,823 字节）不在 `cdn_proxy.cache_roots('pc')` 中，`find_cached_file` 必然 MISS。已通过既有 `storage.cdn_read_roots` 登记为只读历史根，未改代码、未复制缓存、未改 `cdn_cache_dir`。登记后 200 个随机样本全部 HIT。
- 两轮均由用户手工操作。结束后已停止隔离服务并精确恢复 hosts；9 个保护文件和客户端原资源清单 SHA256 不变。独立 DNS 查询的两个关键域名已恢复为 `203.107.63.115`。

历史证据目录：`selftest_tmp/priority-repair/b1-client-20261113/`。初始化证据为 `sdk-initialization-blocker.json`／`client-initialization.png`／`large-uid-readback.json`；资源证据为 `resource-update-blocker.json`／`resource-missing-specs.json`／`resource-presence.json`；当轮清理见 `cleanup-readback.json`／`hosts-restore-receipt.json`／`dns-after-restore.json`。匹配资源现已由 B0 补齐；最新批次反馈及 N-1 修复证据在 `b1-client-20261114/`，不宣称 M2 全过或 `0` 个客户端缺陷。

## B2：M-5 三关复核

**2026-11-14 实机完成：三关全部自然进场、结算并返回主城，终局未复现卡死。**

进场环境：客户端 app `307`／resource build `332`／`v5.3.6`；隔离 UID `261113200139`（`B2M5复核`，70 级）；数据库 `selftest_tmp/priority-repair/b2-run-20261114/v5_server/account.db`；运行副本由 B1 已验证副本复制，仅替换预通至 `1032017` 的存档。CDN off、capture false、临时 hosts 10 域。日志 `b2-run-20261114/server.log`，库 `integrity ok`。

预通仅用于准备进场资格：按既有 `StageService.pass_stage` 沿 `chapter_pre` 链预通 30 章、469 关，29 轮收敛。回读 `1032017` 已通、三关 `clear_times=0`、`1032018` 可进入，进场门禁成立。

| 关卡 | 开始／结束时间 | 进场／结算／返回主城 | 同场服务端日志 | 卡死时的转储 | 本轮结果 |
| --- | --- | --- | --- | --- | --- |
| 1032018 寿命控制 | 22:17:01／22:18:17 | 是／是／是 | `cs_54030` 22:17:01；`SYN` 22:17:22；`入场Ready` 22:17:31；`BattleResult bid=17946658216350001` 22:18:16；`cs_54032` 22:18:17；`sc_52027` 解锁剧情 `103201802` | 不需要，未卡死 | **通过**，`clear_times=1`、`star_list=[1,1,1]` |
| 1032019 | 22:18:29／22:19:07 | 是／是／是 | `38014` 22:18:29；`cs_54032` 22:19:07（承接 1032018 后的连续推进） | 不需要，未卡死 | **通过**，`clear_times=1`、`star_list=[1,0,0]` |
| 1032020 高楼中 | 22:19:20／22:20:38 | 是／是／是 | `cs_54030` 22:19:20；`SYN` 22:19:27；`入场Ready` 22:19:32；`BattleResult bid=17946659606980001` 22:20:38；`cs_54032` 22:20:38；`sc_52027` 解锁剧情 `103202002`；随后 `10050`、`38014`、`12002` 回主城 | 不需要，未卡死 | **通过**，`clear_times=1`、`star_list=[1,1,1]` |

**逐关统计。** 同场观察到 3 次 `cs_54032`（22:18:17／22:19:07／22:20:38）、2 次 `cs_54030` 与 2 次 `BattleResult`、1 次网关选服、1 次 game TCP 建连、心跳持续。两次开战对应三关：`1032018` 单独一场，`1032019` 结算后接 `1032020` 一场。三关 `clear_times` 均为 `1`；`1032018` 与 `1032020` 三星，`1032019` 一星。战斗 `result` 字段为 `False` 是客户端内部字段，结算按 `cs_54032` 正常处理，不据此改判。

**剧情节点。** `103201802`、`103202002` 均以 `unlock_flag=1` 落地，与历史「高楼中·前」剧情资源缺失假设不符：本轮该剧情正常解锁。

**计数边界。** 3 次结算请求是实机执行次数，不等于 3 项独立测试覆盖。本轮只验 M-5 三关，未验完整章、任务和成就；`1032021` 无记录，符合只打三关。该结果仅覆盖本机联网 PC 332 环境，不延伸到移动端、其他渠道或断网场景（B0-S01 仍后置）。

**附带登记（非 M-5）。** 准备阶段发现：以新建 UID 重建隔离档后，客户端走 B 站渠道冷启动，`/game-website-server/pass/sdk/*`（`get_index_config`／`get_menu_info`／`get_news`／`get_slide_image`／`get_update_version`）在仓库内无任何实现，落 `server_net.py:1994` 兜底空 `data:{}`，客户端反复重试并停在「客户端初始化」。改用 B1 已验证副本及其客户端会话后正常。该项不在 B2 范围，未修改任何代码，作为独立观察保留。

## B3：新档预设遍历

本轮 PC 332 的三档前驱对照及剧情分支均通过。下表前三列保留历史内存遍历结果，后三列为本轮实机选点。完整条件及准备过程见本轮记录。[原始预设记录](../../selftest_tmp/priority-repair/b3-presets.json) · [本轮实机结果](#b3-同场实机2026-11-15)

**2026-11-14 实机未完成：三档均未取得客户端结果。** 本轮尝试以 PC 332 实机复验，四份隔离档（`fresh`／`skip_prologue`／`quick_start`／分支变体 `branch_pending`）均已按既有构建器装配并通过内存回读，但客户端始终停在「客户端初始化」，未能进入区服列表，因此**三档的实机栏全部保持「未验」**，不据此更新旧票。详见下文「B3 初始化离线排查」。

| 预设 | 内存 UID | 内存预通／可用／前驱锁定数 | 实机隔离 UID | 实机可进入关卡／前驱 | 实机锁定关卡／缺少的前驱 |
| --- | ---: | --- | --- | --- | --- |
| 普通新档 `fresh` | 42 | 0／24／1085 | 261113200139 | 自然引导后 `1030101`／序章已通 | `1030102`／`1030101` |
| 跳序章 `skip_prologue` | 43 | 7／30／1079 | 261113200139 | 5 级准备后 `1030101`／序章已通 | `1030102`／`1030101` |
| 快速体验 `quick_start` | 44 | 48／91／1043 | 261113200139 | `1010601`／无关卡前驱 | `1010602`／`1010601` |

### B3 初始化离线排查

**首个分歧在 Mix SDK 登录响应之后、资源检查之前。** 用相同的 PC 请求、隔离 UID `261113200139`、固定时间和测试令牌，分别调用 B2 副本、B3 副本和工作区的 Flask 登录路由。三次 HTTP 均为 200，`errorCode` 均为 `"0"`。完整比较 `data` 的 15 个字段，B2 与 B3 仅 `id` 不同。B2 返回 JSON 数字，B3 和工作区返回字符串。此为离线响应回放，实机原日志未保存响应正文。

| 同机 PC 332 留存的实机场次 | Mix 登录请求 | 资源遥测 `client/log/add` | 游戏登录后请求区服列表 | 进入网关 |
| --- | ---: | ---: | ---: | --- |
| B2 成功对照，22:58 | 2 | 7 | 3 | 已连接槽位 3 |
| B3 单存档最后一次，23:05 起服 | 4 | 0 | 0 | 无 |

B3 的五槽、三槽两次日志都出现了登录前的 `127.0.0.1/gateway/get` 查询。B2 成功时，游戏在登录后向业务域名请求 `/skzy-activity/gateway/get?action=server`。B3 最后两次均未出现这一步。末次 B3 和 B2 的有效登记文件 `data/slot_registry.json` 相同，槽位 3 都是 `account.db`。这两场也均无 `/game-website-server/` 请求。[B2 成功时序](../../selftest_tmp/priority-repair/b2-run-20261114/server-ab.log) · [B3 单档失败时序](../../selftest_tmp/priority-repair/b3-run-20261114/server.log)

**反复出现的类型问题。** 本地上游快照 `origin/main@26c2769` 与 B2 均下发数字。早先隔离 UID 为 `42` 时，真实客户端曾连续 4 次报告 LitJson 不能把 `System.Int32` 赋给 `System.Int64`。本机既有 SDK 类型导出也显示 `YSMixLoginResult.data` 使用 `YSMixLoginInfo`，其 `id` 为 `long`。B1 提交 `0112cd0` 把登录 ID 改为字符串，当时仅验证了服务端能把值读回。区服列表里的字符串 UID 属于另一个接口。[客户端异常摘要](../../selftest_tmp/priority-repair/b1-client-20261113/sdk-initialization-blocker.json)

B3 在 22:38 起服时绑定的隔离 UID 为 `910000002`，仍在 Int32 范围；23:05 已换回与 B2 相同的 12 位 UID。对比两份运行副本顶层的 181 个 Python 文件，只有 `server_net.py` 内容不同，代码差异就是登录 ID 的类型和注释。复制旧运行副本会继承旧登录协议，即使存档和资源版本相同。

11 月 14 日 23:07:12，B3 服务端记录了第 4 次 Mix 登录返回 HTTP 200。23:07:24，Windows 记录同场游戏进程无响应并关闭（`AppHangB1`，挂起签名 `204f`）。报告没有线程调用栈、故障模块或 SDK 异常信息。[Windows 原始报告](../../selftest_tmp/priority-repair/b3-login-control-20261115/Report.wer) · [同场应用事件](../../selftest_tmp/priority-repair/b3-login-control-20261115/windows-hang.json)

11 月 15 日，用公开发行的 LitJSON 0.9.0 和 0.19.0 解析 B3 的两份完整响应。两版都将数字 `261113200139` 读为 `Int64`，都在同值字符串上抛出 `JsonException`。用数字 `42` 作历史对照时，仅 0.9.0 复现了 11 月 13 日客户端的 `Int32 → Int64` 异常。PC 332 使用的具体解析器版本仍待确认。[6 次解析结果](../../selftest_tmp/priority-repair/b3-login-control-20261115/litjson-results.json) · [复验脚本](../../selftest_tmp/priority-repair/b3-login-control-20261115/compare-litjson.ps1)

**PC 332 已确认接受数字登录 ID。** 11 月 15 日，用户在普通启动下到达登录界面。`-logFile` 写出了两次成功的 Mix 登录响应，`data.id` 都是 17 位 JSON 数字。两次响应中，`data` 的 15 个字段类型均与 B3 数字样本一致，与字符串样本仅 `id` 类型不同。随后客户端执行了 `YSMixEvent.HandleLoginCallback` 并请求了区服列表。[脱敏实机记录](../../selftest_tmp/priority-repair/b3-login-control-20261115/pc332-login-shape.json)

### B3 修复后核对

11 月 15 日，工作区 Mix 登录路由已改为以 JSON 数字返回存档 UID。实际路由回归测试在修改前报出字符串类型错误，修改后 13 项版本检查全部通过。对四份隔离档逐个调用该路由，返回的 UID 均为数字 `261113200139`，15 个字段的 JSON 类型均与 PC 332 普通登录样本一致。小 UID 的客户端兼容仍待验证。

每档独立保存为 `selftest_tmp/priority-repair/b3-progress-20261115/<预设>/account.db`。下表来自服务端实际编码并回读的章节列表 `sc_24009`。在隔离副本中对六个节点分别走正常进场入口：三档的可进入节点均收到成功回执（`sc_54031.result=0`），锁定节点均收到拒绝回执（`result=1`）。锁定关卡缺少同一行左侧的前驱。

| 隔离预设 | 等级／已通关数 | 列表包含 | 前驱未通，列表不含 | PC 332 隔离档 |
| --- | --- | --- | --- | --- |
| `fresh` | 1／0 | `1030001` | `1030002` | 未验 |
| `skip_prologue` | 1／7 | `1010001` | `1010002` | 未验 |
| `quick_start` | 70／48 | `1010501` | `1010502` | 未验 |

在 `branch_pending`（70 级、已通 39 关）的临时副本上，通过剧情进场和结算依次完成 `1030101 → 1030102 → 1030103`。前两次结算下发的章节列表均不含 `1030104` 和 `1030108`，第三次同时下发两关。关闭并重开数据库后两关仍可进入。四份待实机使用的起始档均保持原始进度。[协议结果](../../selftest_tmp/priority-repair/b3-progress-20261115/protocol-results.json) · [复验脚本](../../selftest_tmp/priority-repair/b3-progress-20261115/verify_b3.py)

11 月 15 日，使用开发版 `LocalServer.dll` 的进程启动方法运行隔离核心自检，业务版本为 321，本机资源命中 332。随后实际启动同一 `main.py`，向本机 HTTP 区服接口发起请求。接口返回 200，槽位 1、2 为新建和删除，槽位 3 对应快速体验档（70 级、48 关已通、UID `261113200139`）。探测程序连通了槽位 3 的网关和游戏 TCP 端口。探测已结束，原始快照、工作区主库和 hosts 的哈希与启动前一致。[自检记录](../../selftest_tmp/priority-repair/b3-progress-20261115/launcher-check/startup.json) · [区服结果](../../selftest_tmp/priority-repair/b3-progress-20261115/launcher-check/gateway.json) · [真实进程结果](../../selftest_tmp/priority-repair/b3-progress-20261115/launcher-check/live-readiness.json)

同一服务核心的 TCP 登录复验使用本机测试程序。它从槽位 3 取得网关分配，以服务签发的会话进入游戏，收到成功回执 `10043`。随后共收到 204 帧，末帧为登录结束标记 `10201`。其中的章节列表 `24009` 包含 `1010501`，未包含 `1010502`。服务已停，运行用数据库已恢复为快速体验起始档并逐字节核对。[登录流记录](../../selftest_tmp/priority-repair/b3-progress-20261115/launcher-check/login-stream.json)

上表保留服务端历史取样。实机使用 PC 可见的章节节点：`stage_meta.json` 的主线入口中，序章到第五章为 `10300～10305`，第六章起为 `10106`。旧 `10100`、`10105` 不在可见主线入口中。此处修正两处实机选点，不修改原始协议证据。普通新档 `1030001/1030002` 和分支 `1030103 → 1030104/1030108` 的选点仍适用。[本轮选点回读](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/native-stage-picks.json)

### B3 同场实机：2026-11-15

本节汇总同一 B3 验收批次，各档分别登录。午后按额度停服，19:04 重启隔离服务续验；每次进场按该档日志时间和 battle_id 关联。

**B3 本机 PC 332 实机核对完成，已停服收尾。** 14:42:09，游戏向 `prod-api-activity.ys4fun.com` 请求区服列表，连接槽位 3 和 UID `261113200139`。实际连接报告资源版本 `332`，14:42:11 完成 `207/218` 帧登录推送。用户确认已进入主界面，等级为 70，UID 相符。207 为实际发送数，218 为合并和过滤前的候选数。[同场登录证据](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/quick-start-login.json)

| 预设或分支 | 实机状态 | 同场结果 |
| --- | --- | --- |
| `quick_start` | done | 用户先确认第六章“水灯节”`1010602` 锁定，再进入“五山神”`1010601`。14:49:21 记录剧情进场，14:49:27 结算，随后 `1010602` 收到进场请求。该档原已预通 PC 可见第五章的 8 关，不能用第五章重玩证明前驱锁定。 |
| `fresh` | done，自然引导后取样 | 起始为 1 级、0 关，14:52:54 以 PC 332 登录。强制流程连续完成 `1030001～1030007` 后，用户确认第一章 `1030102` 原先锁定、`1030101` 可进。15:06:55 进入剧情，15:07:02 结算。结束快照为 12 级、8 关已通。首关前的 `1030002` 锁定界面仍无证据，不作补证声明。 |
| `skip_prologue` | done，5 级准备后取样 | 原始 1 级、7 关档的第一章等级锁已实机记录。主线复通不发经验，故末关回放后仍 1 级。接续时仅在运行副本用既有经验发放路径补 26 经验到 5 级，章节进度不变。用户确认 5 级、`1030102` 原先锁定、`1030101` 可进；19:06:41 进场并完成剧情。结束快照为 6 级、8 关已通。 |
| `branch_pending` | done，方案 A | 70 级、39 关档依次完成 `1030101/1030102/1030103`。用户确认两个后继此前均锁定；19:10:58 完成 `1030103` 后均可进入。`1030108` 于 19:11:19 进场后退出，`1030104` 于 19:11:39 进场、19:11:45 结算。冷读后两关均可进入，编码章节列表仍包含两关；结束快照为 70 级、43 关已通。 |

各档同场原始日志、四份结束快照和连续进度保存在 `selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/`。四份起始档保持原样。本场游戏未启用 `-logFile`，界面状态来自用户回报；服务端请求记录与其分列。[快速体验结果](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/quick-start-stage-result.json) · [普通新档结果](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/fresh-stage-result.json) · [跳序章结果](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/resume-01/skip-stage-result.json) · [分支结果](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/resume-01/branch-stage-result.json)

跳序章原始 1 级记录保留。其主线复通不发经验的路径在 `middleware.py:1517`，等级准备复用 `InventoryService.grant_item`，同步 `users.level`、`users.exp` 和经验货币。补经验是进场准备，不计作自然升级或前驱验收。[准备回读](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/resume-01/skip-level-preparation.json)

**准备阶段的隔离偏差。** 开发版启动器通过环境变量指定隔离目录，但提权后实际挂载工作区主库。已在游戏启动前停止 PID `69240`，随后从隔离目录启动 `main.py`。主库 `.db` 文件哈希与准备前一致；原有 WAL 未纳入开工基线，不能声称逐字节恢复。审计副本中，主文件的 278 个既有表、64,704 行在共同列上与 WAL 视图一致，新增 9 个表均为空。这个比较以主文件为对照，不能证明开工前 WAL 的状态。未覆盖或删除主库及其 WAL。[隔离偏差审计](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/launcher-root-audit.json)

**停线、接续与最终恢复。** 15:13 曾因 5 小时额度剩余 4% 停线并恢复环境。用户随后要求继续，接续额度回读为 100%／58%；本代理未调用重置。19:04 继续剩余两项。接续前另保存主库 DB／WAL／SHM 基线；最终 20 项保护基线均一致，四份起始档未变。五次隔离服务均经 Ctrl+C 退出 1，不记优雅退出通过。最后 hosts Restore 退出 0，恢复为原始 65,492 字节及 SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54`。35 个 TCP 与 UDP 6105 共 36 项独占绑定通过；相关进程 0；两关键域独立解析均为 `203.107.63.115`；四份结束快照完整性均为 `ok`。接续的 WAL 基线不能证明午后误挂前的状态，上段缺证仍保留。[最终恢复回读](../../selftest_tmp/priority-repair/b3-progress-20261115/client-session-01/resume-01/cleanup-readback.json)

旧票 `MAINLINE-SAVE-TREE-20261022` 已回填为 `client_verified`，表示本机 PC 332 的 B3 实机条件通过。本轮未修改生产代码；不自动接续其他批次。[B3 完成条件](2026-11-12-repair-plan.md#b3-复核主线旧票)

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

B1 整批自查准备（历史）：邮件 1020「B1-08 附件验收」当时含票 38×5、币 2×1000、30012×5，后续已领取。当前 30012 为 10；正确的一阶礼物 50001 已完成实际赠礼复验，详见 M2 第 9 项。旧准备状态不作为当前待办。

历史诊断会话：PID `11224`、exec `60503`，日志 `b1-client-20261114/server-diagnostic.log`，UID `261113200139`／版本 332。当时使用同一组 10 域名临时 hosts；此会话已结束。最新环境状态见本文本轮 N-2 取证节，旧 PID 和回执不代表当前活动。

N-2：新档登录默认路径下发空 SC42001，历史日志已有证据。本轮新增可信 332 消费代码、协议定义及候选组配置；仍缺新档初始化业务规则，未实施。332 客户端确实发送 42002；服务端未见 42002／42004 专用业务处理器，42004 只有空 42005 模板。不复制其他 owner 计数，不猜组，不扩多人解封或完整刷新玩法。
