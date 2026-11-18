# 从 Wireshark 抓包恢复账号

## 概览

本流程从一次完整登录建立独立恢复档。邮件正文可由同账号的其他已验证抓包补充；每封邮件都要核对身份并保留来源证明。资产和玩法进度使用主快照。原始抓包和已发布存档保持不动。

先完成抓包，再运行预览。只有预览报告的 `ready` 为 `true` 时，才应用存档。

## 快速开始

1. 完全退出游戏客户端。
2. 打开 Wireshark。
3. 在接口列表中选择连接游戏服务器所用的以太网或 Wi-Fi 网卡。
4. 在“捕获”栏输入 `tcp port 8105`。
5. 点击开始捕获。
6. 启动游戏并完成账号登录，直到大厅加载完成。
7. 如报告缺邮件正文，打开目标邮件并等待正文显示。
8. 停止捕获并保存为 `.pcapng`。

抓包文件建议使用日期和用途命名，例如 `1116.pcapng`。保存后不要覆盖原文件。

需要恢复购买、任务领奖或活动状态时，在登录完成后进入对应页面，并完成一次只读查询。不要先领奖或购买，否则抓包只能证明变化后的状态。

## 选择网卡

查看“接口”列的数据量。选择数据量随游戏登录变化的真实网卡。

常见有效接口名称包含 `以太网`、`Ethernet`、`Wi-Fi` 或无线适配器型号。不要选择以下接口：

- Cisco AnyConnect、VPN 或隧道接口。
- SSH、Loopback、Npcap Loopback 或仅本机通信接口。
- 没有地址、状态为断开或只有零星数据包的接口。

开始前先运行一次 `tcp port 8105` 过滤。登录时若包列表持续增加，说明网卡和过滤器正确。

## 捕获规则

从游戏启动前开始抓包。客户端建立连接、登录、收到 `10201` 和完成大厅加载都必须出现在同一捕获文件中。

一次抓包只保留一个完整 TCP 8105 双向连接。登录前先退出游戏，避免旧连接和新连接混在同一文件。

捕获期间不要切换 VPN、代理或网络接口。不要启用仅记录帧头的“限制每个数据包捕获的字节数”。重建会拒绝截断、缺包、重叠字节冲突和连接重置。

邮件正文有独立查询。摘要已到但正文缺失时，保持抓包运行，回到原账号打开每封需要恢复的邮件。停止抓包前确认正文查询和响应已经出现。

邮件的标题、附件和已读状态不能替代正文。需要完整恢复时，所有非空正文都必须取得；无法补齐时只使用 `available` 范围，并接受该邮件正文保持未抓取状态。

## 补抓当前缺项

`1117-补.pcapng` 已补齐以下 3 封收藏邮件详情。结合 `1117.pcapng` 中两封身份匹配的普通邮件正文，当前 6 封普通邮件和 3 封收藏邮件均有正文。现阶段没有已确认、必须再次抓取的邮件。

| 收藏邮件 | 邮件 ID |
| --- | --- |
| 陪伴服更新福利 | `281475045128448` |
| 致一路同行的你 | `281475044913635` |
| 给你的礼物 | `281475043617282` |

只有后续报告出现缺失正文或发现页面状态不一致时，再按以下步骤补抓：

1. 完全退出游戏。
2. 在 Wireshark 选择真实以太网或 Wi-Fi 网卡，输入 `tcp port 8105` 并开始捕获。
3. 登录账号并进入大厅。
4. 打开普通收件箱，等待邮件列表加载完成。
5. 切换到收藏邮件列表。
6. 打开报告点名的邮件，等待正文显示。
7. 停止捕获并另存为新的 `.pcapng`。

补抓时不领取奖励、不购买商品。补抓文件使用新的重建目录，保留原始抓包和已有恢复档。

补抓能补齐可观察的邮件正文和页面查询。`pending` 协议仍需增加字段映射和逐值验证，重新抓包不会自动闭合这些协议。

### 抽卡记录

用户已明确后置各卡池抽卡记录。当前不要求查询记录、实际抽卡或验证隐藏保底。已有卡池载荷继续保存为证据。

### 有未结束挑战时

若自走棋、虚构推演或多维变量显示“继续挑战”，打开现有局的队伍、地图和当前状态页。保留这局，不新开、不重置、不放弃，也不要求完成战斗。

`1117` 的自走棋状态为 `state=0`，没有明确的进行中棋局需要补抓。虚构推演已取得第二层地图、队伍和属性；只有实际页面与恢复档不一致，或需要恢复未下发的局内详情时，再补对应页面查询。

### 由恢复器继续处理的项目

已取得的角色、资产、任务、商店购买、普通邮箱和玩法登录状态，无需仅为重复取得同一载荷而重新抓包。周期轮换、客户端目录差异和已有载荷尚未映射的字段，由恢复器继续处理。

如果当前关卡进度确实为 0，保留该状态即可。无需为了取证通关迭代校验、打 Boss 或制造小游戏记录。当前已关闭的活动也不要求重开。PC 332 的本地恢复档仍需在游戏中查看并退出重登，这一步属于实机验收。

## 补充邮件详情

若主抓包只包含邮件摘要，而较早抓包已取得正文，先分别重建两个文件。导入时用 `--mail-details-from` 指定正文来源目录。该参数可重复使用，各目录都必须来自原始抓包。

普通邮件须匹配来源账号、客户端版本、邮件 ID、标题、发信时间、过期时间、模板和附件。收藏邮件须匹配账号、版本、ID、标题、模板、发信时间和收藏时间。正文或发件人冲突时拒绝补入；资产、已读状态和领取标记继续采用主快照。

被补入的正文、发件人、邮件身份、来源会话和哈希写入 `ops_common.capture_mail_details`。报告的 `mail_detail_sources` 列出所用来源。这样可以复现补入结果，无需反复打开已取得正文的邮件。

## 重建证据

在仓库根目录运行：

```powershell
python -B -X utf8 tools/rebuild_capture_archive.py "1117-补.pcapng" selftest_tmp/capture-1117-supplement
python -B -X utf8 tools/rebuild_capture_archive.py 1117.pcapng selftest_tmp/capture-1117-mail-source
```

把输出目录换成新的空路径。工具会完成以下检查：

- 读取前后 SHA256 一致。
- 只有一个 TCP 8105 双向连接。
- 两个方向都包含 SYN，序号和帧边界完整。
- 重组缺口、残留和冲突均为零。
- `10042 → 10043 → 10200 → 10201` 登录顺序有效。
- 每个应用帧都能交给协议解码器；未知字段仍保留在原始证据中。

成功时生成 `summary.md`、两个方向的 `.jsonl` 流和 `reconstruction.json`。失败时退出码为 `1`，错误写入 JSON；此时重新抓包。

检查 `reconstruction.json` 的以下值：

1. `stream` 是本次唯一连接的编号。
2. `directions.up` 和 `directions.down` 都存在。
3. 两个方向的 `gaps`、`residual`、`conflicting_bytes` 均为 `0`。
4. `end_command` 为 `10201`。
5. `source_sha256` 与原始抓包的 SHA256 相同。

## 预览恢复档

运行账号状态预览：

```powershell
python -B -X utf8 tools/import_capture_archive.py selftest_tmp/capture-1117-supplement --name 账号恢复_新导入 --scope available --mail-details-from selftest_tmp/capture-1117-mail-source
```

预览不写入存档。检查以下字段：

- `ready` 为 `true`。
- `issues` 为空。
- `recovery_manifest` 列出每个协议的 `core`、`restored`、`partial`、`evidence-only`、`excluded` 或 `pending`。
- `verified_commands` 只包含可以逐值核验的协议。
- `unrestored_mail_ids` 只包含无法从抓包恢复正文的邮件。
- `unrestored_collect_mail_ids` 列出仍缺正文的收藏邮件。

`partial` 表示只恢复了有直接消费者的字段。`evidence-only` 表示原始帧已保存，但没有安全的持久表。`excluded` 表示联机或账号隔离策略阻止恢复。这些状态不会进入 `verified_commands`。

预览不执行挂载。`isolated_login` 在发布时出现；其值为 `true` 时，新档已通过正常挂载和实际登录验证。

## 应用恢复档

预览通过后运行：

```powershell
python -B -X utf8 tools/import_capture_archive.py selftest_tmp/capture-1117-supplement --name 账号恢复_新导入 --scope available --mail-details-from selftest_tmp/capture-1117-mail-source --apply
```

导入器在创建锁内重新读取 UID 和文件名。它拒绝覆盖同名文件，也拒绝使用已有 UID。成功后新文件位于 `v5_server/<存档名>.db`，槽位登记由现有存档管理器完成。

报告中的 `target_uid` 是本次实际发布 UID。`slot_registration.registered` 必须为 `true`；记录槽位号，启动游戏时选择该槽。

检查发布报告的以下值：

1. `published_integrity` 为 `true`。
2. `isolated_login` 为 `true`。
3. `isolated_login_frames` 与 `decoded_login_frames` 相等。
4. `compared_protocols` 与 `verified_commands` 的数量相同。
5. `normal_login_added_mail_ids` 和 `normal_login_added_task_ids` 只表示当前客户端新增内容，不属于来源。

## 客户端验收

1. 启动本地服，确认客户端通过既有本地路由连接该服务。
2. 在存档列表选择发布报告登记的槽位。
3. 登录后核对 UID、等级、角色数和昵称。
4. 打开角色、背包、邮箱、任务、活动、猫咪探索、虚构推演和自走棋。
5. 退出游戏并重新登录。
6. 再次核对第 3、4 步的状态。

当前建议使用 `账号恢复_1117_补充`，槽位 8，UID `261117212902`。该档包含 6 封普通邮件和 3 封收藏邮件，正文齐全。槽位 4 至 7 的旧恢复档保留。

若使用桌面启动器，先注入 hosts 解析规则，再启动服务。进入游戏后按存档名称选择槽位 8。

若使用控制台启动，在仓库根目录运行：

```powershell
Set-Location v5_server
python -B -X utf8 main.py --db "账号恢复_1117_补充.db"
```

该命令指定恢复档，但仍需按客户端既有方式完成本地域名路由和证书信任。

## 核验

运行重建回归测试：

```powershell
python -B -X utf8 tests/capture_rebuild_check.py
```

运行真实抓包导入检查：

```powershell
python -B -X utf8 tests/m3_import_check.py selftest_tmp/capture-1117-supplement
```

对发布文件执行以下只读检查：

1. 运行 SQLite `PRAGMA integrity_check`，结果必须为 `ok`。
2. 核对 `save.owner_uid` 与报告中的目标 UID。
3. 核对角色、刻印、钥从、邮件和活动状态的持久计数。
4. 重新挂载新档，确认登录只发送一次 `10201`。
5. 解码全部登录帧，确认没有空载荷或无法识别的账号协议。
6. 再次计算原始 `.pcapng` 和已有恢复档的 SHA256。
7. 确认活动数据库和当前活动槽位没有变化。

如发布报告包含未闭合协议，运行以下 SQLite 查询：

```sql
SELECT
  json_extract(value_json, '$.status') AS status,
  COUNT(*) AS rows
FROM ops_common
WHERE kind = 'capture_evidence'
GROUP BY status;
```

把结果与发布报告中的 `partial`、`evidence-only` 和 `pending` 数量比较。三者之和应等于证据行数。任何未闭合协议缺证据行时，停止发布并修复恢复器。

## 未闭合状态

当前客户端目录与抓包版本不同时，来源记录可能包含客户端已删除的关卡、商品或活动。导入器保留这些来源值，并在报告中记录 `current_client_catalog` 差异。

无持久表的协议保留完整帧、来源哈希和会话 ID。需要重新抓包时，按报告中的 `recapture` 操作，并新建输出目录。不要修改旧证据目录。

`pending` 表示尚未确认消费入口。`partial` 表示缺少完整状态或核验证据。`local` 表示按本地时钟、目录或策略生成，并记录来源差异。`excluded` 表示按归属排除的全服、运营或联机数据。

用本版导入器重建 `1117-补` 后，隔离候选通过 195 帧和 147 个协议的核验。用户在 PC 332 确认槽位 3 验收档的导入数据正常。抽卡保底 `16015` 后置，`40031` 已登记。槽位 8 仍使用 11 月 17 日的发布档。[逐项清单](plans/2026-11-17-g-protocol-gaps.md) · [客户端验收记录](plans/2026-11-13-client-acceptance.md#11-月-18-日导入验收)

猫咪探索和虚构推演的周状态需要保留捕获周期。验证时核对 `admin_cat_explore_data.last_weekly_reset_ts` 和 `ops_common` 中 `capture_rogueteam_fetters` 的记录。普通存档仍按当前周生成，不读取其他恢复档的来源周。
