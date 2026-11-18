# 抓包导入新存档 · 独立操作手册

> 目标读者：想把一次游戏登录抓包，变成一个新的、可登录的本地存档的操作者。
> 本手册只讲"新建存档"这一件事，不涉及邮件正文补抓、历史档恢复等旁支。
> 所有命令均在**仓库根目录**（`C:\Users\<user>\Desktop\Alpha-Persei-Cluster`）执行，使用系统 Python 3.14。

---

## 0. 一图看懂流程

```
①抓包(.pcapng) → ②重建证据(rebuilt目录) → ③预览(preview) → ④应用(apply) → ⑤客户端验收
```

- **预览不做任何写入**，只告诉你"如果导入会得到什么、缺了什么"。
- **只有预览 `ready` 为 `true` 时**才可以执行"应用"。
- 应用会**新建**一个独立存档文件，**不会覆盖**任何现有存档。

---

## 1. 抓包（.pcapng）

1. **完全退出游戏客户端**（避免旧连接混进新抓包）。
2. 打开 Wireshark，选择连接游戏服务器所用的**真实以太网 / Wi-Fi 网卡**（不要选 VPN / Loopback / 隧道）。
3. 在捕获过滤器输入：`tcp port 8105`。
4. 开始捕获。
5. 启动游戏并**完成一次完整登录**，直到**进入大厅加载完成**。
6. 停止捕获，另存为 `.pcapng`（建议按日期命名，如 `1120.pcapng`）。

### 抓包硬性要求（重建会拒绝不合格的抓包）

- 一次抓包**只保留一个完整的 TCP 8105 双向连接**。
- 客户端连接、登录、收到 `10201`、大厅加载完成，必须都在**同一个文件**里。
- **不要**启用"限制每个数据包捕获的字节数"（截断会被拒绝）。
- 捕获期间**不要**切换 VPN / 代理 / 网卡。
- 保存后**不要覆盖原始文件**。

> 只需抓"登录到大厅"这一段。想多恢复某些页面状态的话，在登录后进入对应页面做一次**只读查询**再停止捕获即可；**先别领奖、别购买**。

---

## 2. 重建证据（把 pcapng 变成可解析的帧流）

```powershell
python -B -X utf8 tools/rebuild_capture_archive.py 1120.pcapng selftest_tmp/capture-1120
```

- 第二个参数是**输出目录，必须是新的空路径**。
- 成功时生成 `summary.md`、上行/下行两个 `.jsonl` 帧流、以及 `reconstruction.json`。
- 失败时退出码为 `1`，错误写入 JSON —— 这种情况一般需要**重新抓包**。

### 重建成功后，必查 `reconstruction.json`

| 检查项 | 期望值 |
|---|---|
| `stream` | 本次唯一连接编号（唯一） |
| `directions.up` / `directions.down` | 两个方向都存在 |
| 两个方向的 `gaps` / `residual` / `conflicting_bytes` | 全部为 `0` |
| `end_command` | `10201` |
| `source_sha256` | 与原始 `.pcapng` 的 SHA256 相同 |

任何一项不符，**不要继续**，重新抓包。

---

## 3. 预览新存档（不写入）

选定存档名后，先跑预览（**去掉 `--apply`**）：

```powershell
python -B -X utf8 tools/import_capture_archive.py selftest_tmp/capture-1120 --name 新档_1120 --scope available
```

### 参数说明

| 参数 | 作用 |
|---|---|
| `rebuilt_dir`（第一个位置参数） | 第 2 步重建出的目录 |
| `--name` | **必填**。新存档名，最终文件为 `v5_server/<存档名>.db`，不可与已有同名文件冲突 |
| `--uid` | 可选。指定目标 UID；**不填则自动分配**一个新 UID |
| `--scope` | `available`（推荐：恢复已核实字段并报告缺项）/ `full`（要求完整，缺项即拒）/ `heroes`（只恢复角色） |
| `--mail-details-from` | 可选、**可重复**。从同账号的另一个已验证重建目录补充邮件正文（只补正文，不复制账号状态） |
| `--apply` | 加上此参数才真正写入（第 4 步才用） |

> 推荐 `--scope available`：它只恢复有直接消费者的字段，其余（缺正文的邮件、没映射的协议）作为"缺项"报告出来，而不是伪造。想要严格全量就用 `full`。

### 预览结果必查

- `ready` 为 **`true`**。
- `issues` **为空**。
- `recovery_manifest`：每个协议都有处置标签（`core` / `restored` / `partial` / `evidence-only` / `excluded` / `pending`）。
- `verified_commands`：只含可逐值核验的协议。
- `unrestored_mail_ids` / `unrestored_collect_mail_ids`：仍缺正文的普通/收藏邮件 ID。

**标签含义**（帮你判断能不能接受这次导入）：

| 标签 | 含义 | 是否进 `verified_commands` |
|---|---|---|
| `core` / `restored` | 核心状态 / 完整恢复 | ✅ |
| `partial` | 只恢复了有直接消费者的字段 | ❌ |
| `evidence-only` | 原始帧已保存，但无安全持久表 | ❌ |
| `excluded` | 联机/账号隔离策略阻止恢复 | ❌ |
| `pending` | 尚未确认消费入口 | ❌ |

`ready=true` 且你认可缺项范围后，进入下一步。

---

## 4. 应用（真正创建新存档）

在预览命令后**追加 `--apply`**：

```powershell
python -B -X utf8 tools/import_capture_archive.py selftest_tmp/capture-1120 --name 新档_1120 --scope available --apply
```

- 导入器会在**创建锁内**重新读取 UID 和文件名。
- **拒绝覆盖同名文件**，也**拒绝复用已有 UID**。
- 成功后新文件位于 `v5_server/<存档名>.db`，并**自动完成槽位登记**。

### 应用后必查（发布报告）

| 字段 | 期望 |
|---|---|
| `target_uid` | 本次实际发布的 UID（记下它） |
| `slot_registration.registered` | **`true`**（记下**槽位号**，启动游戏时选这个槽） |
| `published_integrity` | `true` |
| `isolated_login` | `true`（新档已通过正常挂载 + 实际登录验证） |
| `isolated_login_frames` | 等于 `decoded_login_frames` |
| `compared_protocols` | 数量等于 `verified_commands` 的数量 |
| `normal_login_added_mail_ids` / `normal_login_added_task_ids` | 仅代表当前客户端新增内容，**不属于来源**，无需紧张 |

> ⚠️ 若退出码为 `2`：说明证据不完整（`issues` 或 `missing_data` 非空），本次**零写入**，修复缺项后再试。

---

## 5. 客户端验收（实机确认）

1. 启动本地服，确认客户端通过既有本地路由连上该服务。
2. 在**存档列表**里选择第 4 步报告登记的**槽位号**。
3. 登录后核对：**UID、等级、角色数、昵称**。
4. 逐个打开：角色、背包、邮箱、任务、活动、猫咪探索、虚构推演、自走棋。
5. **退出游戏并重新登录**。
6. 再次核对第 3、4 步的状态是否一致。

### 启动方式二选一

**桌面启动器**：先注入 hosts 解析规则，再启动服务，进入游戏后按存档名选槽位。

**控制台启动**（仓库根目录）：
```powershell
Set-Location v5_server
python -B -X utf8 main.py --db "新档_1120.db"
```
> 指定存档的同时，仍需按客户端既有方式完成**本地域名路由和证书信任**。

---

## 6. 核验（可选，但建议做）

```powershell
# 重建回归测试
python -B -X utf8 tests/capture_rebuild_check.py

# 真实抓包导入检查（把路径换成你的 rebuilt 目录）
python -B -X utf8 tests/m3_import_check.py selftest_tmp/capture-1120
```

对发布文件做只读检查：

1. SQLite `PRAGMA integrity_check` → 结果必须为 `ok`。
2. `save.owner_uid` 与报告中的 `target_uid` 一致。
3. 角色、刻印、钥从、邮件、活动状态的持久计数合理。
4. 重新挂载新档，确认登录**只发送一次 `10201`**。
5. 解码全部登录帧，无空载荷或无法识别的账号协议。
6. 原始 `.pcapng` 和已有存档的 SHA256 **保持不变**。
7. 活动数据库和当前活动槽位**没有变化**。

若报告含未闭合协议，核对证据行数与报告是否吻合：

```sql
SELECT
  json_extract(value_json, '$.status') AS status,
  COUNT(*) AS rows
FROM ops_common
WHERE kind = 'capture_evidence'
GROUP BY status;
```

`partial` + `evidence-only` + `pending` 三者之和应等于证据行数；任何未闭合协议缺证据行时，停止发布并排查。

---

## 7. 常见问题 / 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| 重建退出码 `1` | 抓包截断/多连接/缺包/冲突 | 重抓：单连接、不截断、登录到 `10201` 全程在同一文件 |
| 预览 `ready=false` 且有 `issues` | 缺少必需状态或来源不合规 | 看 `issues`，按提示补抓或改 `--scope` |
| 应用退出码 `2` | 证据不完整 | 零写入，修掉 `missing_data` 再重新 `--apply` |
| 提示同名/同 UID | 存档名或 UID 已存在 | 换 `--name`（或换 `--uid`） |
| `slot_registration.registered=false` | 槽位登记失败 | 检查存档管理器，勿手动改库 |
| 邮件正文缺失 | 主抓包只有摘要 | 用 `--mail-details-from` 追加同账号的正文来源目录（可重复） |

---

## 8. 合规红线（务必遵守）

- **原始抓包、重建帧、`account.db` 均不入 git**（`Alpha-Persei-Captures/` 已在 `.gitignore`）。
- 抓包衍生数据属**官方衍生内容**，按 NCR-1.0 / README §十 规范，仅本地使用，不对外分发。
- 补抓/预览/应用过程中**不领奖、不购买、不改动原始证据目录**。

---

> 更完整的背景与历史验收记录见：[从 Wireshark 抓包恢复账号](capture-recovery.md)、[抓包导入能力与门禁](../plans/2026-11-13-capture-import-contract.md)。
