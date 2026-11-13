# 仓库修复执行台账

2026-11-13 开始执行。起点为 `4bec98f16ba8dc95f4c01d104bcdc5b88d77ed10`，与[总计划](2026-11-12-repair-plan.md)一致。已有未跟踪计划、`_review/` 和 `tests/min_params.json` 保留。

## 当前结果与下一步

已恢复 A2 直接调用脚本，完成 GM 首批操作、启动／周期专项、控制台浏览器验收和 H1 离线实现。导入已通过合成账号构建、实际挂载／登录及并发发布检查；真实抓包恢复仍缺证。A1 证书级验收已完成；用户确认后，本轮 A2 的 10 个必需脚本均退出 `0`。本轮完成 A2 后停止，确认后才能开始 B1。游戏客户端尚未运行。

| 任务 | 源码／材料 | 自动检查 | 客户端验收 | 下一步与门禁 |
| --- | --- | --- | --- | --- |
| A1 | 已重部署证书与分发文件，安装两处 Windows 根信任 | 文件检查退出 `0`；Windows 链、HTTPS 200、指纹及错误主机名检查通过 | 未运行，不属于本票证书级探针 | done；用户已确认接续 A2 |
| A2 | 六个消费者及相关专项复验完成，本轮未改代码 | 10 个脚本均退出 `0`，156 次执行含继承重复；Linux 41 全过 | 不适用 | done（消费者范围）；保留 1 项历史归档 skip，资源告警单独登记；等待确认 B1 |
| B1 | 已执行隔离资产与基础回归 | 结算串行 5、奖励回滚 16、首领奖励 20 通过；周期 31 项含 2 个归档错误 | 12 项阻塞 | 实际客户端未运行，不能填为通过或宣称发现 0 个客户端缺陷 |
| B2 | 保留三关复验清单 | 不适用 | 1032018／1032019／1032020 均阻塞 | 缺当前同场日志与客户端转储，不猜根因或规避范围 |
| B3 | 复用现有解锁实现，未改业务 | 三预设内存构建及前驱／分支约束通过 | 阻塞 | 预通数分别为 0／7／48，不是解锁故障 |
| C1～C3 | 已实现，保留路由与响应结构 | GM 10 项通过；前端 check/build 通过 | 浏览器隔离库存交互通过；游戏重登未验 | 真实存档离线门禁保留 |
| D | 新增专项，未重写启动／周期业务 | 7 项通过；宿主在 A1 续作中构建通过 | 浏览器保存／回读、非法输入、周期确认／取消／滚动／重置通过；托管重启未验 | SDK 已就绪；D 尚未接续，等待逐项确认 |
| E | 五域契约差距与取样步骤完成 | 24 项来源哈希已核对；原生审计仍缺素材 | 未执行 | 玩法实现票保持缺证阻塞 |
| F | 15 入口及另两项分开登记 | 运行专项部分通过；原生导出核对缺 Lua | 全部自然游玩／重登未验 | 自动检查不替代客户端 |
| G | 首版映射、独立验证和原子发布已实现；真实恢复范围仍 partial | 合成账号及失败／并发检查通过，见下文；真实预览缺 10 封普通邮箱及 144 个未审核协议 | 阻塞 | 未发布真实恢复档，不能把合成正向检查算作真实导入或游戏登录通过 |
| H1 | 三键、五模板和 10 人试稿完成 | 4 项离线检查通过；5 模板异模型逐字复核通过 | 在线／游戏内未验 | 10 稿 `reviewed=false`；未扩展、未启用或回填 |
| H2 | 符号／职责与拆分子计划完成 | 基础回归通过；M2 真机收官未通过 | 未执行 | 只交付前置材料，未迁移三大业务文件 |
| H3 | 本轮执行状态、来源、交付与停止原因已更新 | 文档与差异复核完成 | 不适用 | 历史票保持可追溯，不批量勾选 |

## 产物与执行分工

总计划清单加上 H1 登记项，公开产物保持 7 个代码模块、8 个类、5 个操作入口和 1 个模板加载函数。实际 AST 清单为新增 22 个顶层函数、删除 1 个重复私有 AST 助手，净增 21 个顶层函数；多出的 14 个导入内部助手和 2 个测试协议助手没有新增操作或配置。另有 2 个 Inventory 方法及 1 个注册表锁方法。各产物、调用方和必要的单调用内部责任见[交付复核](2026-11-13-repair-delivery.md)。没有删除公开产物或新增顶层包。

根代理串行修改共享业务代码。两个 `gpt-6-luna`、`high` 子代理分别负责 A2 的计时／Linux 夹具及其他消费者。第三个同模型子代理负责 E、H 取证文档。调用路由已接受；运行模型身份以平台元数据为限。根代理以不同模型复核共享路径。

## 每票记录

### A2 起点

- 输入：当前提交与 8 个缺失辅助模块清单。
- 命令：`python -B -X utf8 v5_server/tools/verify_report_small_fixes.py`。
- 实际结果：退出码 `1`，`ModuleNotFoundError: test_battle_entry_timing`。
- 处置：恢复真实测试，不跳过原断言。根代理最终复跑：共享 23、计时 6、结算 8、角色 13、入场 12、溢出 21、教学 5、提交恢复 10、Issue #8 17、Linux 41；全部退出 `0`。入场的 12 项含 1 项既有 repair archive 缺失 skip，未新增 skip。日志为 `final-<脚本名>.log`。
- 覆盖边界：结算测试使用真实 Core／handler／SQL／codec，但保留有限 `_settle_frames` 夹具，不代表完整奖励引擎。pending frame 身份断言直接检查真实 `h_54032`；Core 按设计清理跨请求通知，未确认生产缺陷。
- 断言保留证据：`a2-test-method-coverage.json` 核对所有原测试方法仍在；`a2-assertion-count-diff.json` 未发现断言数量减少。原生 Lua 核对仍缺源码和 parser，单独失败，未用打包配置冒充原生对照。
- 功能复核：根代理复核实际 Core／AccountDB／codec 调用与失败注入，Luna 执行、根代理异模型复核。复杂度删除清单：缺失模块导入、重复 AST 助手、伪造 Core／数据库夹具、单调用教学包装。现有 `selected()` 扩展后由原测试和角色测试共用。

### A2：本轮隔离复验

- 起点：`240ac3888b6db91ff548bf930ed1a133d90e4f43`，保留 A1 的 9 个未提交文件改动。用户明确授权“继续 A2”；本轮没有启动 B1。
- 产物：更新现有状态文档及忽略目录中的实际日志、方法／断言审计和哈希回执。没有新增、删除或修改生产模块、类、函数、测试或配置，净增为 `0`。
- 命令：从仓库根目录执行 `python -B -X utf8 v5_server/tools/<脚本>`。10 份原始日志与逐项命令保存在 `selftest_tmp/priority-repair/a2-recheck-20261113-180246/` 的 `results.json`。

| 范围 | 脚本 | unittest 执行数 | 实际结果 |
| --- | --- | --- | --- |
| 直接消费者 | `verify_report_small_fixes.py` | 23 | exit 0，OK |
| 直接消费者 | `test_settlement_retry_boundary.py` | 8 | exit 0，OK |
| 直接消费者 | `test_hero_response_boundary.py` | 13 | exit 0，OK |
| 直接消费者 | `verify_battle_entry_fail_closed.py` | 12 | exit 0，OK，含 1 项历史归档 skip |
| 直接消费者 | `verify_overflow_ownership.py` | 21 | exit 0，OK |
| 直接消费者 | `verify_rogueteam_tutorial_skip.py` | 5 | exit 0，OK |
| 计时专项 | `test_battle_entry_timing.py` | 6 | exit 0，OK |
| 提交恢复专项 | `test_commit_recovery.py` | 10 | exit 0，OK |
| Issue #8 | `verify_issue8_merge.py` | 17 | exit 0，OK |
| Linux 夹具 | `test_linux_setup.py` | 41 | exit 0，OK |

- 计数边界：总数 `156` 来自 10 份 unittest 日志的 `Ran ... tests`，含继承重复，不是独立覆盖数。唯一 skip 为指定 before 归档缺失的旧版入场复现；没有新增 skip、删除断言或更改基线。原生 Lua／parser 对照不属于本轮 10 个命令，缺证状态继续单列，不算本轮通过。
- 原断言核对：重新与 `4bec98f` 比较，132 个旧定义测试方法全部保留，未发现断言数量下降；当前共 140 个定义方法，多出的 8 个为原已交付的 6 个计时测试和 2 个溢出测试。10 个脚本的 Git 过滤后 blob 与 AST 均和 `HEAD` 一致。9 个原始字节哈希差异仅为 Windows CRLF；详见 `original-assertion-audit.json` 和 `summary.json`。静态数量核对只辅助复核，行为结论以原始日志为准。
- 关键行为：Linux 两个启动测试实际观察 `main.main` 接收的认证环境变量、旧变量清除、配置参数与 CLI 覆盖；半自动向导经 `nginx_mocks()` 隔离。战斗六项行为、真实 builder 的三个教学预设、贴纸与多目标转换均有本轮执行结果。
- 覆盖边界：结算脚本调用真实 Core／AccountDB／codec，但以 `_settle_frames` 夹具限定收据、重试、跨周期及 SQL／缓存边界，不代表完整结算引擎。计时专项直接执行 `battle_server` 的内存报文路径，不需要账号库。
- 数据保护：测试执行期间，A1 的 9 个改动文件、`account.db` 和 3 个证书／密钥／链文件共 13 个路径的 SHA256 不变；详见 `before.json` 与 `summary.json`。没有启动完整服务、修改系统信任或写入真实账号。
- 处置：已确认的资源关闭告警按计划另立本地票 `A2-W01`；Rogue schema 告警记为未验证观察项，见优先级清单 R02。未通过吞掉告警或修改 schema 使日志安静。
- 功能复核：根代理实际运行，`gpt-6-luna`／`high` 独立核对 8 个缺失依赖映射、原始日志、Linux 三项修复和断言保留。单独复杂度复核删除清单：无。A2 的消费者范围完成，按用户要求停止，等待确认 B1。

### A1：首次只读取证（历史）

- 输入／起点：本台账起点提交；现有 `sdk_ca.crt`、`sdk_ca.key`、`sdk_key.pem`、`sdk_cert.pem` 及分发副本。
- 命令：`python -B -X utf8 v5_server/gen_cert.py --check --json`。
- 输出：`a1-cert-check.json`，退出 `1`；`ready=false`、`requires_root_replacement=true`。根指纹为 `BC96E5CFBAE90A1460C3F66FC2A2EDA4951783F9`。
- 安装范围：只读查询 CurrentUser／LocalMachine Root，未找到此指纹。未改变信任、证书或私钥，日志未包含私钥内容。
- 备份：检索到的 archive 证书属于测试夹具，不能当成现有部署的可恢复备份。部署动作前须用现有启动壳备份当前文件。
- 停止原因：总计划 A1 的原文为“确认执行当轮是否已明确授权证书重部署和系统信任变更”。当前仅授权执行计划，未给这项专项授权。Windows 信任和实际 HTTPS 握手尚未通过。
- 交付前复验仍退出 `1`，指纹及不配对原因不变，见 `a1-cert-check-final.json`。
- 功能复核：确认错误状态与根因；复杂度复核删除清单：无。

### A1：获授权后的部署与验收

- 起点：`240ac3888b6db91ff548bf930ed1a133d90e4f43`。用户本轮明确授权 A1 证书修复，并要求每项完成后停止，确认后才能开始下一项。本轮只执行 A1。
- 产物：更新原有根证书、服务证书、Windows 分发副本和两份 iOS 描述文件；没有新增或删除生产模块、类、函数，净增为 `0`。私钥及全部备份保留在本机，不写入日志或 Git。
- 输入复验：`gen_cert.py --check --json` 退出 `1`；根指纹 `BC96E5CFBAE90A1460C3F66FC2A2EDA4951783F9` 与私钥不配对。本项目没有运行服务；实际 Windows 用户为 `<user>`。
- 备份：8 个文件完整复制到 `selftest_tmp/priority-repair/a1-backup-20261113-173444/`，逐一核对 SHA256；生成器另产生 8 份同目录 `.before_cert_*` 副本，也与部署前哈希一致。清单为 `a1-backup-manifest.json`，复核结果为 `a1-backup-verification.json`。回滚时先停服务，再按清单恢复同一组文件；本轮没有删除旧根信任。
- SDK／构建：检测到 .NET SDK `10.0.404`。`dotnet build LocalServer/LocalServer.csproj -p:Platform=x64 --nologo -v:minimal` 退出 `0`，0 个警告、0 个错误；没有执行 D 的托管重启验收。
- 部署路径：现有启动壳清单要求 `requireAdministrator`，Computer Use 无法读取高完整性窗口。改由 `a1-deploy.ps1` 加载刚构建的 `LocalServer.dll`，调用原有 `CertificateManager`，保留检查、备份、参数选择、生成后检查及精确指纹验证顺序；没有修改部署实现或权限清单。
- 部署结果：生成参数为 `--force-ca`，生成与本机安装退出码均为 `0`。新根指纹为 `E2808B9A40765506D3033BE32A01E8F903644481`；`InCurrentUser=true`、`InLocalMachine=true`、`ChainValid=true`、`Ready=true`，问题列表为空，见 `a1-deployment-receipt.json`。根有效至 `2036-11-10T09:39:44Z`，叶证书有效至 `2027-11-13T09:39:44Z`。
- 文件复验：`python -B -X utf8 v5_server/gen_cert.py --check --json` 退出 `0`；`requires_root_replacement=false`、`needs_leaf_renewal=false`、`needs_distribution_sync=false`，见 `a1-cert-check-repaired.json`。
- HTTPS 探针：`a1-https-probe.py` 调用真实 `build_https_app(None)` 与 `start_https`，只监听 `127.0.0.1:5278`，禁用额外 HTTP 端口。构建应用前后 `account_db._db` 均为 `None`，没有加载真实账号。`a1-native-https.ps1` 用默认 `SslStream.AuthenticateAsClient("open.ys4fun.com")`，没有自定义验证回调；TLS 1.2 握手成功，`GET /cert` 返回 `200`，对端叶指纹与本机文件一致，下载根指纹与新根一致。错误主机名触发 `AuthenticationException`／`RemoteCertificateNameMismatch`，见 `a1-native-https-receipt.json`。
- 保留限制：Schannel curl 的默认严格吊销检查退出 `35`，原因为 `CRYPT_E_NO_REVOCATION_CHECK`；错误主机名退出 `60`，原因为 `SEC_E_WRONG_PRINCIPAL`。没有将前者写为通过。通过的 .NET 默认 TLS 路径与启动壳既有 `X509RevocationMode.NoCheck` 策略一致；没有增加 CRL、修改生产策略或跳过主机名校验。此结果不代表完整 `main.py` 启动、按钮交互或游戏客户端验收。
- 收尾：启动壳 PID `20868`、探针 PID `33416`、挂起清理子进程 PID `30972` 及其父进程均已退出；`5278` 没有监听。已确认生成锁未被持有，删除本轮留下的单字节运行锁。最终实际用户回读确认两库中新根存在、所有旧根记录保留、项目进程列表为空，见 `a1-cleanup-receipt.json` 与 `a1-windows-after.json`。前期清理中止没有记为成功；以最终回读为准。
- 功能复核：根代理执行，`gpt-6-luna`／`high` 独立复核共享部署与信任边界、备份和真实回读。复核发现最终回执的 CurrentUser 原始枚举含重复新根指纹；已补充说明，保留原始输出，只按精确指纹存在性核验，不把数组长度作为安装数量。复杂度复核删除清单：无；只使用已有部署实现，操作脚本保留在忽略的证据目录。

### B：基线、资产与新档

- `python -B -X utf8 tests/m2_defect_checks.py`：退出 `0`，`ALL PASSED`，证据 `m2-defect.log`。
- `python -B -X utf8 tests/smoke_dispatch.py`：退出 `0`；423 个操作、52 个有效参数、0 个未捕获异常。保留原 `tests/min_params.json` 和基线，未更新基线。
- 冒烟有 1 个非失败差异：12046 当前只回 12047，旧基线含 4 帧。源码按东八区 11／18 点开放定时体力；本次运行时尚未到所请求档位。差异存于 `smoke-changes.json`，属于时钟资格差异，未据此改业务。
- `verify_settlement_serial.py`：5 项通过。B1 首次运行因传递导入 `extract_autochess_cfg` 失败；将 `verify_servant_awake_guard.py` 的原生 exporter 导入移入原核对测试后，运行行为可执行。根代理最终日志：`verify_grant_failure_guard.py` 16 项通过；`verify_boss_reward_guard.py` 20 项通过；`verify_boss_cycle_clock.py` 执行 31 个测试方法，同一方法的 2 个子用例缺 `archive/boss_cycle_clock_20261104/before/v5_server/weekly_challenge_service.py` 报错。后者退出 `1`，未改成 skip，也未用当前源代替 before。
- `verify_hero_unlock_delta.py`：26 项中 25 项通过，1 项原生核对缺 Lua／parser 明确失败，退出 `1`。`verify_hero_race_collect.py` 自身 9 项运行测试通过，原生核对仍失败。上述继承套件有重叠，不将各脚本数量相加视作独立覆盖。
- 本地 Git 没有缺失 archive／Lua／parser 路径的历史记录；其他日期版本没有对应 before 哈希，不能证明就是指定原件，因此未拿近似版本补齐对照。
- `b3-presets.json`：真实内存存档构建器的普通新档／跳序章／快速体验分别预通 0／7／48 关，当前可选节点 24／30／91；检查到的未满足前驱节点 1,085／1,079／1,043 均被拒绝。三个内存库 `integrity_check=ok`。这些数字是配置遍历结果，不能证明客户端完整游玩。
- 功能复核：已有解锁实现保持不动。复杂度删除清单：无。三关终局与 12 项实机结果另记客户端验收表。

### C：GM 真实写入与页面交互

- 修改：`gm_api.py` 将四个未支持接口改为 `SERVICE_ERROR`；实现角色解锁、套装与材料清理，并移除道具失败转货币的降级。不存在商品改用现有 `NOT_FOUND`。
- 复用：存档作用域／自动备份、`InventoryService`、真实角色初态、事务及 `run_while_save_offline()`。在线判断仍按路径；无路径连接按同 UID 保守拒绝。未扩充连接索引。
- 材料依据：[21 个物品 ID 的扣料清单](2026-11-13-material-clear-contract.md)。保护清单优先，未知物品保留。
- 先红后绿：`c-before.log` 记录原空操作失败。最终 `python -B -X utf8 tests/m4_gm_api_check.py`：退出 `0`，10 项通过，见 `c-after.log`。
- API／持久库覆盖：严格 JSON 布尔值、重复角色不发碎片／不改养成、同 UID 双存档、错 UID、在线连接、真实 3 星 6 槽、缺槽预校验、中途 SQL 失败整批回滚、非货币发放失败回滚、目录分类与保护优先、四个未支持接口零写库／零备份、不存在商品错误码。
- 前端：`addEquipSuit` 发送 `star`；Inventory 增加直接发放与二次确认清理、结果回读、失败反馈及切档旧响应失效处理。`npm run check` 与 `npm run build` 均退出 `0`，见 `ui-check.log`／`ui-build.log`。
- IAB 实际交互：临时 `selected.db` 发出套装 1、3 星六件（310001～360001，1～6 槽）；清理显示 1 条，刷新后 41201 无持仓。切到同 UID `other.db` 后仍显示 7 个。读回 SQLite：仅 selected 的 UID 42 材料行被删，UID 43 的 9 个保留，货币 2 仍为 777。见 `c-browser-readback.json`。夹具进程已停止。
- 异模型复核：Luna high 找出类型 4 误限和同 UID 切档竞态，根均已修，Luna 再次复核。根与子代理没有将游戏重登标为通过。
- 同类扫查：清理误限仅此处；旧响应写入涉及 load／catch／finally 及两个写 handler，已一并修。未支持假成功原 7 处均处理。复杂度删除清单：四段伪造成功正文、任意货币降级；无额外公开接口或配置。

### D：启动与周期专项

- `python -B -X utf8 v5_server/tools/verify_launch_cycles.py`：退出 `0`，7 项通过，见同名日志。
- 临时配置和真实 Flask 覆盖五端口非法值（负数、超上限、布尔、字符串）、未知字段、保存失败保旧；真实 `main.main` parser 的保存值与显式 CLI 覆盖；认证／CSRF、在线重置拒绝、旧 token、重置不发奖、不重复累计。
- 前轮仅验证托管／非托管进程的 Popen／Timer 边界，没有启动真实宿主。当时 `dotnet build LocalServer/LocalServer.csproj --no-restore` 返回 `-2147450735`，原因是没有 .NET SDK，见 `dotnet-build.log`。用户安装 SDK 后，A1 续作构建通过；D 的托管重启仍未验。
- 执行者 Luna high，根以不同模型复核。复杂度删除清单：单调用 `launch_values` 助手内联，避免一次性包装。
- IAB 浏览器实际输入 HTTPS 端口 `65536`，页面显示错误并禁用保存。改为 `11443`、CDN `relay` 后保存、重新读取均一致；配置文件实际为这两项 override。周期卡片从 9,000／15,000 开始，取消保持、滚动可见后续档位；确认后回读为 0／0，领取列表为空，下次刷新时间不变。SQLite 实读货币 `2=777`、材料 `41201=7` 保持。见 `d-browser-readback.json`、`d-launch-browser.jpg` 和 `d-cycle-browser.jpg`。临时服务已停止，未重启真实宿主。

### G：新独立存档导入

- 来源和边界：[导入契约](2026-11-13-capture-import-contract.md)。真实样本在 `10201` 前有 187 帧，`307/321` 版本，3 份输入哈希已记录。缺少 10 封普通邮箱明细，另有 144 个未审核协议号，真实恢复保持阻塞。
- 构建复用 `AccountDB.new_save_workspace()`、34 张静态目录和现有角色蓝图。唯一主人和空 API profile 随新 UID 写入。账号帧从目标状态生成，不复用供体载荷；结束帧保留原头部元数据。
- 独立子进程挂载测试副本，用正常 `switch_active_database()` 和 `send_login_flood()`，解码实际字节并比较 15 个必需协议、主人、顺序、原邮件及正文。只固定 `time.time()`，不把它当真实当前周期或游戏客户端证明；测试副本正常补发的邮件另记 ID。候选库前后 dump 一致。
- 发布在普通建档锁内重新读取 UID，并用最终 UID 重建。暂存使用 `.stage`，验证后关闭连接并硬链接发布。无槽位或登记失败保留完整文件，刷新可重试。真实输入缺项时，预览和 `--apply` 均不改变现有存档、注册表或密钥夹具。
- 最终命令：`python -B -X utf8 tests/m3_import_check.py`；退出 `0`，14 项通过，耗时 31.215 秒，见 `g-final.log`。覆盖名称／同 UID／普通建档竞争、服务端同步／删除并发、满槽、登记失败重试、自动 UID 重建、旧暂存目录保留、原结束帧、字面模板和模板来源冻结。正向账号是运行协议生成的合成夹具，不能代表真实抓包成功。
- 已修确认缺陷：生成器能力探测会污染候选；只比较协议号会漏掉状态丢失；重分配 UID 没有完整重建；普通邮箱误写为类型 0；结束帧头被重新猜测；未配对额外流被忽略；旧暂存目录可能被误删；模板正文缓存与哈希版本可能不一致。均经根代理与 Luna high 复核，缺项仍失败关闭。
- 注册表异模型复核：大小写别名复用同一槽位；6 进程登记同一文件只产生一个映射。写后复读失败先红后绿，原 JSON 字节恢复；删除 8 项、刷新 14 项最终通过。所有写后复核调用均复用 `_save_registry()`，已扫，无第二处。
- 复杂度删除清单：生成器探测、全表 UID 批量改写、伪造验证布尔值、伪造结束帧、一次性邮箱摘要包装、未使用参数、一次重复隔离登录。保留固定公共签名和锁内重建，不增加 CLI 选项。

### E、F 与 H

- E 交付[玩法契约差距](2026-11-13-gameplay-contracts.md)，缺 HP／权重／五队总分／新战棋地图时保留阻塞。
- F 公共物品夹具原从缺失的 Lua 目录得到空表，导致多项 KeyError。现复用静态目录复制助手，仅将 `item_catalog` 读入内存；保留原生导出断言。薇儿角色奖励夹具另补实际获得头像 2112841 的目录行，原两个领奖失败消除。
- H1 修改 `ai_context_builder.py`、三键片段、`ai_translator.py`；新增五模板 JSON、离线测试和 10 份未审校试稿。`python -B -X utf8 tests/m4_ai_prompt_check.py`：4 项通过，见 `h1-after.log`。
- Luna 独立从 `git show HEAD:v5_server/ai_translator.py` 提取 AST，五模板逐字匹配。新版本只增加约定三键，v1 兼容；五路真实内存邮件及异常 fallback 通过，聊天历史未写入。试稿没有运行时加载者。
- H2 只交付[符号与职责子计划](2026-11-13-ai-split-subplans.md)，M2 实机门禁未满足，不迁移三个大文件。
- 复杂度删除清单：H1 五段内联模板搬为配置；未增加新路由、凭据或模型提供方。F 不增加 parser 或空替代助手。

## 接续与停止点

源码、自动检查、浏览器和游戏客户端结果已分开登记。前轮快照已本地提交为 `240ac38`；A 阶段证书、台账和[交接提示词](2026-11-13-repair-handoff.md)一并纳入收官本地提交，未推送。证书及 Windows 信任已按 A1 授权部署；A2 只复验现有隔离脚本，没有修改真实账号。

A 阶段已完成计划内的 A1 证书级验收与 A2 消费者复验；保留上文的历史归档、原生缺证和严格 CRL 检查限制。当前停止，确认后才能开始 B1 的资产一致性与 M2 复验。G 仍需要同会话普通邮箱明细、可解析正文及 144 个协议的归属／状态证据。M2／B2／F 需要实际游戏客户端；D 宿主已构建，但托管重启未验。H1 待 10 稿审校；H2 保留 M2 真机门禁。

按你的额度规则，A2 开始时读取账号的 5 小时和周窗口，分别剩余 30% 和 89%，未触发剩余 10% 停点。没有使用额度重置或购买。当前按逐项确认要求停在 A2，等待确认后才能开始下一项。
