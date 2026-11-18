# 修复计划交付复核

## 概览

已交付测试恢复、GM 写入、启动／周期检查、导入首版安全路径、玩法取证和 AI 离线稿件。A1 续作已完成证书部署、Windows 信任和本机 HTTPS 验证。整份计划尚未收官，游戏客户端、真实抓包缺证和 AI 内容审校仍有门禁。

B0 历史收尾（已本地提交 ce761b7）：本机 `307/332/v5.3.6` 的版本／资源适配、联网状态下的主界面、角色／背包和退出重登均有证据；除用户后置的 `B0-S01` 外，未发现其他未完成的必需项。断网冷启动仍被 B 站渠道登录阻断，因此整票保持 **partial**，不能写成全部离线通过。临时服务已停、hosts 已恢复。以下“等待恢复 B1”是 B0 当时的历史停止点；B1 后续已收尾。

当前接续状态（2026-11-15）：B0-S01 后置，B1 已收尾，N-2 维持 filed。B2、B3 本机 PC 332 实机核对通过。B3 三档前驱与方案 A 分支均有用户回报及同场日志，旧票为 `client_verified`；服务和临时 hosts 已恢复。午后主库 WAL 缺证独立保留。[本轮实机和恢复记录](2026-11-13-client-acceptance.md#b3-同场实机2026-11-15)

修复起点为 `4bec98f16ba8dc95f4c01d104bcdc5b88d77ed10`。前轮全部未提交内容已保存为本地提交 `240ac38`，包含原有 M3／M4 计划、`_review/` 和参数文件。A 阶段证书、台账及[交接提示词](2026-11-13-repair-handoff.md)一并保存为收官本地提交；仅在 A1 部署本机证书与 Windows 信任，未推送。收官提交可按交接文件的 Git 历史定位。

## 计划覆盖

| 项目 | 状态 | 交付位置与停止原因 |
| --- | --- | --- |
| A1 | done（证书级验收） | 进度台账 A1 续作：文件检查退出 0，两处 Windows 根信任及链验证通过；实际 HTTPS 200、根／叶指纹核对及错误主机名拒绝通过。严格 CRL 检查限制单列，未验游戏客户端。 |
| A2 | done（消费者范围） | 本轮 10 个必需脚本均退出 0，156 次运行含继承重复；Linux 41 全过。保留 1 项历史归档 skip，原生缺证及资源关闭告警另列，下一项待确认。 |
| B0 | partial（B0-S01 后置） | 332 资源与联网客户端流程通过；断网 B 站认证仍后置。 |
| B1 | done（提交 `0112cd0`；N-2 filed） | 本轮已按用户决定收尾；历史周期专项 2 error／exit 1 保留。 |
| B2 | done | PC 332 三关自然进场、结算并回主城，本轮未复现卡死。 |
| B3 | done（本机 PC 332） | 初始化、三档前驱及方案 A 分支实机通过；跳序章在 5 级准备后取样。四份结束库完整性 ok，接续 20 项基线一致、36 项绑定通过。午后 WAL 缺证单列。 |
| C1～C3 | done（源码、API、浏览器、PC 332 实机） | GM 12 项通过。2026-11-18 用户确认清理、重登、回放、兑换和旧档表情正常；实库删除 7 行，换装及表情持久化，服务已停、hosts 已恢复。资源 404 观察独立登记。 |
| D | partial | 7 项 API／parser 检查和浏览器保存／周期重置通过；宿主已在 A1 构建通过，尚未接续 D 的托管重启验收。 |
| E | done（契约与取证材料） | 五域差距、来源哈希、40 图矩阵和下一步样本要求已交付；缺证玩法仍阻塞。 |
| F | partial | 15 入口分别记录；291 项脚本检查仍含 9 个原生资料错误；自然游玩全部未验。爬塔和换装池另有内存 Core／冷读证据。 |
| G | partial | 合成账号正常挂载／wire 核对及原子发布通过；真实 9/26 抓包缺 10 封普通邮件和 144 个未审核协议，未发布。 |
| H1 | partial | 三键、五模板和 10 份 reviewed=false 稿件已交付；待内容审校，未扩展到 51 人、启用、回填或在线调用。 |
| H2 | done（前置材料） | 符号快照、职责映射和拆分子计划已交付；M2 真机门未过，三个大文件没有迁移。 |
| H3 | done（本轮状态） | 台账、优先级、旧计划前提和客户端状态已按实际更新，历史票没有批量标为已修。 |

## 实际验证命令

未单列工作目录的命令从仓库根目录运行。日志在 `selftest_tmp/priority-repair/`。继承测试有重叠，不把各行相加作为独立覆盖数。

A2 本轮重跑了下表中的共享、计时、结算边界、角色响应、入场、溢出、教学、提交恢复、Issue #8 与 Linux 共 10 个命令，结果均与表中一致。新日志在 `a2-recheck-20261113-180246/`，逐项命令与退出码见 `results.json`；断言与数据保护审计见同目录 `summary.json` 和进度台账 A2 复验。

| 命令 | 实际结果 |
| --- | --- |
| `python -B -X utf8 tests/m2_defect_checks.py` | exit 0，ALL PASSED。 |
| `python -B -X utf8 tests/smoke_dispatch.py` | exit 0；423 操作、52 有效参数、0 未捕获异常。12046 有 1 项时钟资格差异，未改基线。 |
| `python -B -X utf8 v5_server/tools/verify_report_small_fixes.py` | exit 0，23 项。 |
| `python -B -X utf8 v5_server/tools/test_battle_entry_timing.py` | exit 0，6 项真实报文检查。 |
| `python -B -X utf8 v5_server/tools/test_settlement_retry_boundary.py` | exit 0，8 项；有限结算边界，不是完整奖励引擎。 |
| `python -B -X utf8 v5_server/tools/test_hero_response_boundary.py` | exit 0，13 项。 |
| `python -B -X utf8 v5_server/tools/verify_battle_entry_fail_closed.py` | exit 0，12 项，含 1 项既有归档缺失 skip。 |
| `python -B -X utf8 v5_server/tools/verify_overflow_ownership.py` | exit 0，21 项，含继承用例。 |
| `python -B -X utf8 v5_server/tools/verify_rogueteam_tutorial_skip.py` | exit 0，5 项，调用真实建档器。 |
| `python -B -X utf8 v5_server/tools/test_commit_recovery.py` | exit 0，10 项。 |
| `python -B -X utf8 v5_server/tools/verify_issue8_merge.py` | exit 0，17 项。 |
| `python -B -X utf8 v5_server/tools/test_linux_setup.py` | exit 0，41 项；3 个旧夹具错误消除。 |
| `python -B -X utf8 v5_server/tools/verify_settlement_serial.py` | exit 0，5 项。 |
| `python -B -X utf8 v5_server/tools/verify_grant_failure_guard.py` | exit 0，16 项，以根日志为准。 |
| `python -B -X utf8 v5_server/tools/verify_boss_reward_guard.py` | B1 续作 exit 0，21 项，新增 1 项文件库冷重开；原记录为 20 项。 |
| `python -B -X utf8 v5_server/tools/verify_boss_cycle_clock.py` | B1 续作 exit 1；32 项，2 个 before 归档缺失 error，未跳过；原记录为 31 项。 |
| `python -B -X utf8 tools/verify_polyhedron_lifecycle.py`（cwd：`v5_server`） | N-1 修复后 exit 0，35 项；含真实 PC 332 战报解析、结算和下一场景集成用例。 |
| `python -B -X utf8 tools/verify_hodur_challenge.py`（cwd：`v5_server`） | N-1 修复后 exit 0，20 项；保留共用解析器的坏包与血量边界。 |
| `python -B -X utf8 -m unittest verify_warchess_state.WarChessTests.test_battle_reentry_replaces_prior_attempt_and_health_report_rejects_bad_team`（cwd：`v5_server/tools`） | exit 0，1 项；保留共用解析器的战棋编队边界。 |
| `python -B -X utf8 v5_server/tools/verify_hero_unlock_delta.py` | exit 1；26 项，1 个原生 Lua／parser 对照失败。 |
| `python -B -X utf8 tests/m4_gm_api_check.py` | exit 0，10 项，实际 Flask／临时 SQLite。 |
| `python -B -X utf8 tests/m4_ai_prompt_check.py` | exit 0，4 项，实际内存邮件和 provider 故障 fallback。 |
| `python -B -X utf8 v5_server/tools/verify_launch_cycles.py` | exit 0，7 项；进程边界受控，未实测 Windows 宿主。 |
| `python -B -X utf8 v5_server/tools/verify_minigame_empty_login.py` | exit 0，4 项。 |
| `python -B -X utf8 v5_server/tools/verify_slot_refresh.py` | exit 0，14 项，含原字节恢复新回归。 |
| `python -B -X utf8 v5_server/tools/verify_slot_delete_ui.py` | exit 0，8 项。 |
| `python -B -X utf8 tests/m3_import_check.py` | exit 0，14 项，31.215 秒；覆盖源状态、发布和并发，真实输入保持阻塞。 |
| `npm run check`（web_src） | exit 0。 |
| `npm run build`（web_src） | exit 0；保留原 chunk 体积提示，未弱化构建配置。 |
| `dotnet build LocalServer/LocalServer.csproj -p:Platform=x64 --nologo -v:minimal` | A1 续作 exit 0；SDK 10.0.404，0 警告、0 错误。前轮缺 SDK 的失败记录仍保留。 |
| `python -B -X utf8 v5_server/gen_cert.py --check --json` | A1 续作 exit 0，ready=true，问题列表为空；部署前 exit 1 的证据仍保留。 |
| `& ./selftest_tmp/priority-repair/a1-deploy.ps1` | exit 0；复用构建后的 CertificateManager，生成／安装退出 0，两库信任与 Windows 链通过。 |
| `& ./selftest_tmp/priority-repair/a1-native-https.ps1` | exit 0；默认 Windows .NET TLS，HTTPS 200，根／叶指纹匹配，错误主机名拒绝。未设置验证回调；严格 CRL curl 失败单列在进度台账。 |

浏览器 C 证据是临时同 UID 双存档。D 证据是临时启动配置与周期库。D 实读 HTTPS 11443、CDN relay；周期从 9000/15000 变为 0/0，货币 2=777、材料 41201=7 保持。两个临时服务均已停止。[启动画面](../../selftest_tmp/priority-repair/d-launch-browser.jpg)和[周期画面](../../selftest_tmp/priority-repair/d-cycle-browser.jpg)不是游戏客户端证据。

## 缺失模块与保留覆盖

B1 本轮只新增 `v5_server/tools/verify_boss_reward_guard.py:103` 的测试方法，模块／类／顶层函数净增均为 `0`。该方法由奖励套件和周期套件调用。定向 unittest 退出 `0`，Ran 1；三份原始日志及数据保护回执位于 `selftest_tmp/priority-repair/b1-recheck-20261113/`。9 个保护路径哈希不变。根 Codex 与 `gpt-6-luna`／`high` 已分别完成需求、临时库边界和日志复核；另行复杂度复核删除清单：无。没有生产缺陷修复声明，原生缺证、A2-W01 和严格 CRL 限制保留。

B1 已实际应用并恢复临时路由，Apply／Restore 均退出 `0`；原字节哈希一致，两关键域独立查询恢复为 `203.107.63.115`。临时完整服务与用户客户端两次重试已执行：小 UID `42` 引发 SDK 类型异常；换用自动分配的 `261113200139` 后，用户确认越过初始化，随后更新缺件。82 个不同请求文件均属于所选 321 清单，清单尺寸合计 `244992009` 字节，本机缓存未命中；这不是全量版本缺口。12 项数值操作执行数为 `0`，不能推断 `0` 个客户端缺陷。证据与恢复结果见 `b1-client-20261113/` 和进度台账本轮记录。根 Codex 与 `gpt-6-luna/high` 完成不同模型复核及单独复杂度复核，删除清单：无；生产代码未改，初始化兼容缺口和资源缺件保持 filed。该段为 11 月 13 日历史记录；B1～B3 后续已按确认范围完成，当前结果见本文“计划覆盖”。

历史 B0 计划登记阶段只编辑现有总计划、台账、交付、优先级、客户端验收和交接 6 份文档，不新增文件或代码产物，模块／类／顶层函数增删及净增均为 `0`。B1-R01 的版本／资源适配归 B0 接续，B1-C01 保留证据及处置要求，B1 已有成果不重置。新增 B0 不代表自动启动实施；下一确认点是开始 B0。纯文档变更不运行无关代码测试，也不把既有客户端重试算作 B0 通过。

B0 计划已由根 Codex 与 `gpt-6-luna/high` 分别完成功能和独立复杂度复核。单次登录范围、隔离 UID 门槛及准备资料／运行时离线边界已明确；建议与处置见台账 B0 记录。删除清单：无；过时接续顺序已替换。

B0 实施产物：`v5_server/cdn_proxy.py:330` 扩展已有缓存查找；`res_version_manager.py:239` 扩展 Bili 目录并回读命中根；`dynamic_versions.json`／`native_manifest_sources.json`／`resource_distribution.json` 登记和选择已核验 332；`static_resources/pc/native/native-pc-6a610d4d8550/` 新增 4 个官方主／语音清单。`verify_resource_storage.py` 新增 2 个类内方法并证明只读、缓存优先、中文语音、MD5 和 junction 拒绝；`verify_manifest_management.py` 修正 fixed／auto 夹具并保留原断言。生产模块／类／顶层函数增删及净增均为 0，无新参数或配置键。

数据证明：官方 4 文件合计 7,715,245 字节，主清单与安装副本逐字节一致；本机 69,429 对象通过大小／MD5，临时缓存补齐 1,846 对象共 6,163,821,436 字节、497.2 秒、失败 0；合并 71,275 对象、63,325,313,135 字节，缺失／坏对象 0。校验发生于准备时间窗，并非原子快照；每次实际读取仍沿用原校验。官方 probe 与真实 HTTP 证据见 `b0-local-client/`，4 个专项实际命令和日志见进度台账 B0 实施段。未把下载耗时当作在线服务性能证据。

根 Codex 与 Luna 已分别复核共享读取／路径边界及测试变更，并完成独立复杂度复核，删除清单：无。B0-P01 清单选择在 cache miss 时的开销保持未验证观察；B1-C01 小 UID 兼容问题未通过换大 UID 冒充生产修复。客户端验收必须另填，当前不可标 B0 done。


| 原缺失模块 | 当前入口与保留行为 |
| --- | --- |
| test_battle_entry_timing | 新 BattleEntryTests；握手、Ready、PONG 精度、序列、重连和异常包。 |
| audit_core_regular_old_settlement_probe | test_settlement_retry_boundary；真实 Core／handler／SQL／codec，以 `_settle_frames` 夹具限定收据、重试、跨周期和 pending 身份断言，不代表完整结算引擎。 |
| test_cost_fallback_boundary | test_hero_response_boundary；真实升级、扣费和响应失败回滚。 |
| test_entity_rollback_notifications | test_hero_response_boundary；真实通知、编码失败、状态恢复和顺序断言。 |
| test_issue_hero_payload | verify_battle_entry_fail_closed；实际英雄载荷、入场身份和异常拒绝。 |
| verify_mainline_trial_entry | verify_battle_entry_fail_closed；真实多维／Rogue 会话和试用角色行为。 |
| verify_all_cosmetic_mail.CosmeticTests | verify_overflow_ownership；两个贴纸／多目标转换行为并入现有类。 |
| verify_save_generator.SaveGeneratorTests | verify_rogueteam_tutorial_skip；普通、跳序章、快速体验均调用真实 builder。 |

原生 extract_autochess_cfg 及 Lua、部分 before archive 仍缺失。运行夹具改用打包配置，原生核对保持独立失败。方法名／assert 数量扫描没有发现原断言减少；此扫描只辅助审查，实际结果仍以行为用例和根代理 diff 复核为准。

## 功能复核与处置

| 类别 | 结论 | 处置 |
| --- | --- | --- |
| 确认缺陷 | GM 假成功、任意货币降级、缺失错误码。 | fixed：真实落库或明确未支持，失败回滚。 |
| 确认缺陷 | 清理误限材料类型、同 UID 切档旧响应覆盖。 | fixed：分类与保护优先、身份和请求序号检查；同类路径已扫。 |
| 确认缺陷 | 注册表读写异常被吞、大小写重复、写后复核丢旧表、删除顺序。 | fixed：共用跨进程锁、原子写回／还原、稳定映射、先提交再回收；已扫，无第二处。 |
| 确认缺陷 | 导入探测污染、只验协议号、UID 全表替换、邮箱类型、结束帧和残缺连接。 | fixed：纯映射、实际 wire 数值、最终 UID 重建、类型 1、原帧头及唯一双向流。 |
| 确认缺陷 | 暂存误认旧目录／链接目标；模板正文与 hash 不一致。 | fixed：本次目录所有权、原路径清理、冻结模板同源字节；定向红绿和异模型复核。 |
| 未验证项 | M2、三关、小游戏自然游玩、真实恢复档、Windows 宿主托管重启。 | filed：客户端验收表和导入契约记录具体缺项；不标通过。 |
| 可选建议 | 删除 CLI 的第一次 RAM 构建。 | rejected：固定公开接口和锁内最终重建保留；已删除重复隔离子进程。 |

执行者与复核者为根 Codex 和 gpt-6-luna high。A2／D／E／H 文档和 G 初版由子代理执行；共享业务由根代理串行修改。Luna 分别复核 C、G、H 共享路径，G 最后复核明确确认暂存、模板来源和最终 UID 修复。两者是不同模型；未将同模型重复检查算作第二模型。

## 单独复杂度复核

删除清单：四段伪造成功正文、任意货币降级、重复 AST 选择器、重复 battle 解包段、伪造数据库／Core 夹具、单调用 launch_values／教学包装、导入生成器探测、批量 UID 改写、伪造验证标志／结束帧、单调用邮箱摘要包装、未用参数和一次重复隔离登录。无新顶层包、CLI 选项、线上提供方或兼容层。生成后内容未变的 CSS 和 gm_console 已还原检出换行格式。

### 实际产物计数

统计为 Python 模块顶层 AST，不含类方法和内嵌子进程脚本文本。新增 7 模块、8 类、22 顶层函数；删除 0 模块、0 类、1 私有函数；净增 7 模块、8 类、21 顶层函数。数据另新增五类模板 JSON 和 10 份人格稿。

总计划加 H1 的公共产物清单保持。额外的 14 个导入内部助手和 2 个测试协议助手服务于既定能力，没有增加操作入口。单调用内部助手按真实解析／映射／验证责任保留，不作为公共扩展点。既有类新增 Inventory 两方法和注册表锁方法。

### 新模块与类

| 模块／类 | 入口或第一调用方 | 第二调用方或内部范围 |
| --- | --- | --- |
| `v5_server/tools/test_battle_entry_timing.py:13` · `BattleEntryTests` | 独立 unittest 入口 | 共享 BattleTimingMemoryTests |
| `tests/m4_gm_api_check.py:31` · `GmApiTests` | 独立测试入口 | 临时浏览器夹具 |
| `v5_server/tools/verify_launch_cycles.py:36` · `LaunchCycleTests` | 独立测试入口 | 无第二生产调用者；测试类 |
| `v5_server/capture_import.py:28` · `CapturedFrame` | JSONL 解码 | 测试协议快照 |
| `v5_server/capture_import.py:42` · `CaptureSnapshot` | read_snapshot | 合成快照测试 |
| `v5_server/capture_import.py:76` · `ImportReport` | _report 构造 | CLI／测试读取报告 |
| `tests/m3_import_check.py:67` · `CaptureImportTests` | 独立测试入口 | unittest 定向回归入口 |
| `tests/m4_ai_prompt_check.py:21` · `AiPromptTests` | 独立测试入口 | 无第二生产调用者；测试类 |
| `tools/import_capture_archive.py:15` · `main` | 命令行入口 | CaptureImportTests |

### 新顶层函数

| 位置／函数 | 第一调用方 | 第二调用方或单一责任 |
| --- | --- | --- |
| `tools/import_capture_archive.py:15` · `main` | CLI __main__ | CaptureImportTests |
| `v5_server/ai_translator.py:65` · `_get_greeting_prompts` | 五路问候分支 | 离线模板测试 |
| `v5_server/capture_import.py:91` · `_decode_frame` | _load_stream | 仅流读取；独立的帧结构和 codec 边界 |
| `v5_server/capture_import.py:136` · `_summary_connections` | read_snapshot | 仅快照读取；独立的端点归属解析 |
| `v5_server/capture_import.py:171` · `_load_stream` | read_snapshot | 仅快照读取；独立的文件字节与连续性检查 |
| `v5_server/capture_import.py:193` · `_canonical` | _merge_chapters | 邮箱冲突检查、wire 记录排序 |
| `v5_server/capture_import.py:197` · `_merge_chapters` | read_snapshot | 仅快照读取；章节主键合并责任 |
| `v5_server/capture_import.py:213` · `_mail_record` | _assess | _build_rows、隔离验证期望数据 |
| `v5_server/capture_import.py:239` · `_assess` | read_snapshot | _report、测试 |
| `v5_server/capture_import.py:322` · `read_snapshot` | CLI main | CaptureImportTests |
| `v5_server/capture_import.py:420` · `_report` | CLI main | build_imported_save |
| `v5_server/capture_import.py:433` · `_one` | _build_rows 的多个协议映射 | 无第二函数调用者；复用唯一快照检查 |
| `v5_server/capture_import.py:440` · `_json` | _build_rows | 隔离验证期望文件 |
| `v5_server/capture_import.py:444` · `_build_rows` | build_imported_save | 仅构建器；账号表映射责任 |
| `v5_server/capture_import.py:703` · `_wire_state` | _protocol_state | 实际邮件与正文核对 |
| `v5_server/capture_import.py:713` · `_protocol_state` | 隔离进程源协议视图 | 实际 wire 视图；没有第二业务调用者 |
| `v5_server/capture_import.py:723` · `_verify_isolated_login` | publish_imported_save | 仅发布门；独立挂载与 wire 责任 |
| `v5_server/capture_import.py:876` · `build_imported_save` | CLI main | publish_imported_save、测试 |
| `v5_server/capture_import.py:909` · `publish_imported_save` | CLI main | CaptureImportTests |
| `v5_server/save_generator.py:149` · `copy_static_catalogs` | 普通建档 _copy_catalogs | 导入器、小游戏内存目录夹具 |
| `v5_server/tools/verify_battle_entry_fail_closed.py:24` · `wire_fields` | entry_heroes | 同一解包流程三层重复使用；测试私有范围 |
| `v5_server/tools/verify_battle_entry_fail_closed.py:28` · `entry_heroes` | 入场英雄检查 | 试用英雄检查、before 复现 |

## 文件变更与原因

每行位置为新增入口或首个实际差异行。生成资产按源文件重建，未手工修改压缩结果。

| 位置 | 原因 |
| --- | --- |
| `M2-数值bug登记簿.md:3` | 明确本轮未完成实机数值走查，保留历史实例来源。 |
| `v5_server/ai_context_builder.py:113` | 按既定顺序注入三键，并兼容 v1。 |
| `v5_server/ai_translator.py:31` | 外置五模板，保留事件、fallback 和发信行为。 |
| `v5_server/data/ai_prompt_fragments.json:2` | 新增三键并升级为 v2，旧文本保持。 |
| `v5_server/gm_api.py:743` | 消除七个假成功路径，使用真实事务与离线门禁。 |
| `v5_server/inventory_service.py:22` | 实现完整六槽发放及有用途证据的材料清理。 |
| `v5_server/login.py:20` | 读取到首个结束标记，保留超过 192 行的必需帧。 |
| `v5_server/replay.py:115` | 修正已失效的 192 行范围注释。 |
| `v5_server/save_generator.py:9` | 共用冻结目录复制和建档锁，明确忙碌错误。 |
| `v5_server/save_slot_manager.py:284` | 跨进程保护注册表，并在失败时保留旧映射。 |
| `v5_server/server_net.py:253` | 让离线写入拒绝消息适用于本轮操作。 |
| `v5_server/static_web/app.js:9` | 发布本轮 Inventory 源码构建结果。 |
| `v5_server/static_web/control-panel.html:17` | 同步内嵌控制台构建结果。 |
| `v5_server/tools/test_commit_recovery.py:85` | 扩展既有 AST 助手，供角色和入场测试共用。 |
| `v5_server/tools/test_hero_response_boundary.py:1` | 迁移到真实内存 Core 和打包配置。 |
| `v5_server/tools/test_linux_setup.py:12` | 按当前入口检查 argv／环境，复用 Nginx mocks。 |
| `v5_server/tools/test_settlement_retry_boundary.py:1` | 恢复结算重试行为检查，并明确有限夹具边界。 |
| `v5_server/tools/verify_battle_entry_fail_closed.py:1` | 保留入场拒绝断言，复用真实 handler 和共用 AST 助手。 |
| `v5_server/tools/verify_hero_race_collect.py:1` | 分开运行行为与明确失败的原生对照。 |
| `v5_server/tools/verify_minigame_point_rewards.py:3` | 从静态目录建立真实内存物品类型，不用空 Lua 表。 |
| `v5_server/tools/verify_overflow_ownership.py:132` | 将两个贴纸转换行为纳入既有溢出类。 |
| `v5_server/tools/verify_rogueteam_tutorial_skip.py:6` | 用真实 builder 检查三种预设。 |
| `v5_server/tools/verify_servant_awake_guard.py:11` | 把 native exporter 导入移到原核对用例，解除 B1 运行阻塞。 |
| `v5_server/tools/verify_slot_refresh.py:4` | 实测写后复读失败仍逐字节保留旧表。 |
| `v5_server/tools/verify_sphero_leisure.py:33` | 补真实奖励头像的目录夹具，消除两项夹具失败。 |
| `v5_server/web_src/src/lib/api.ts:882` | 发送后端读取的 star，并限制材料清理类别。 |
| `v5_server/web_src/src/panels/Inventory.tsx:30` | 增加真实操作、确认和回读，防止切档旧响应覆盖。 |
| `tests/m3_import_check.py:1` | 验证导入与失败／并发边界。 |
| `tests/m4_ai_prompt_check.py:1` | 验证离线提示词与真实邮件回读。 |
| `tests/m4_gm_api_check.py:1` | 验证真实 GM 写入、回滚和存档范围。 |
| `tools/import_capture_archive.py:1` | 提供固定的预览／apply 命令。 |
| `v5_server/capture_import.py:1` | 冻结快照、映射并验证后发布新独立档。 |
| `v5_server/tools/test_battle_entry_timing.py:1` | 执行真实战斗握手和计时用例。 |
| `v5_server/tools/verify_launch_cycles.py:1` | 用临时配置和 Flask 验证启动与周期门禁。 |
| `v5_server/data/ai_greeting_prompts.json:1` | 保存五段逐字外置模板。 |
| `v5_server/data/ai_personas/90001001.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001002.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001003.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001004.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001005.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001006.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001007.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001008.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001009.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `v5_server/data/ai_personas/90001010.json:1` | 交付一份未审校、未启用的人格试稿。 |
| `docs/plans/2026-11-12-repair-plan.md:1` | 指向实际执行状态，不宣称整体收官。 |
| `docs/plans/2026-11-12-repair-progress.md:1` | 记录每票命令、结果和门禁。 |
| `docs/plans/2026-11-13-client-acceptance.md:1` | 逐项记录 M2、三关、预设与玩法客户端状态。 |
| `docs/plans/2026-11-13-material-clear-contract.md:1` | 列出 21 个可清材料的真实扣料依据与保护项。 |
| `docs/plans/2026-11-13-gameplay-contracts.md:1` | 冻结五域证据、哈希、状态边界与缺样。 |
| `docs/plans/2026-11-13-ai-split-subplans.md:1` | 校正 AI 配置来源并记录拆分门禁。 |
| `docs/plans/2026-11-13-ai-pilot-review.md:1` | 提供 10 人审校入口。 |
| `docs/plans/2026-11-13-capture-import-contract.md:1` | 说明当前映射、发布门禁与真实缺项。 |
| `docs/plans/2026-11-13-repair-delivery.md:1` | 映射计划、实际产物、验证与复核结论。 |
| `docs/backlog-status-2026-11-05.md:1` | 回填当前状态，保留历史证据。 |
| `M4-执行计划.md:1` | 标注旧 .env／操作数等前提已变化。 |

B0 11 月 14 日验收收尾：用户确认昵称 `B0版本适配`、UID `261113211627`、主界面、角色列表、背包和退出重登全部正常。实际日志有两次 slot 3 登录及两次版本 `332` 的登录推送完成，均为 `207/218` 帧、动态 `207`；11 帧进度合并为一次全量，再按既有版本策略略过 `89013`。207 是实际发送数，218 是合并／过滤前候选数，不相加为独立覆盖。库内唯一用户、等级 `70` 与身份回读一致，quick_check=`ok`；此处没有替代 B1 的资产数值验收。

`B0-S01`，confirmed／filed／用户后置：用户完全退出游戏后断开 Wi-Fi／网线，冷启动弹出 B 站登录窗口，因无网无法登录，未进入游戏。当前 Mix SDK 本地接口不等于原生 PCGameSDK 离线认证，仓库没有现成实现；未伪造响应、扩展 10 域名预览、改真实账号或客户端安装文件。断网失败独立保留，联网成功不能覆盖它。

服务 PID `9484` 已不存在，exec `66583` 经 Ctrl+C 退出 `1`，不冒充优雅退出通过。`hosts-transaction.ps1 -Action Apply`／`Restore` 均退出 `0`；恢复后 hosts 与原件逐字节一致，长度 `65492`、SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54`。即时解析回执保留，独立 DNS 两关键域随后均为 `203.107.63.115`。35 个 TCP 端口及 UDP `6105` 可独占绑定，9 个保护文件及客户端主清单哈希未变。

根 Codex 与 `gpt-6-luna/high` 已分别完成功能、共享路径／权限边界及单独复杂度复核，删除清单：无。B1-C01 小 UID 生产兼容仍 filed；B0-P01 为未验证性能观察；渠道请求 10／响应 9 已有本轮正常运行证据，但没有据此猜改字段。只读 SDK 导出字符串线索不证明离线入口可用，未调用。

## B1：11 月 14 日本轮收尾

B0 已由用户授权保存为本地提交 `ce761b770b2620ffd4b53187c2f234504fcf8ada`。用户现已授权本地提交全部 12 个变更文件：4 个 Python 文件和 8 份文档，包括原冷重开测试；本轮提交可用 `git log -1 --format=%H -- v5_server/battle_server.py` 定位。未推送。独立运行副本位于 `selftest_tmp/priority-repair/b1-client-20261114/runtime/v5_server`，唯一合成主人 UID `261113200139`／昵称 `B1隔离验收`；CDN off、capture false，账号库、配置及聊天写入均隔离。冻结资源缓存有意复用 B0 目录。

M2 第 1 项三阶段快照证明精准探测凭证 20→10、10 条抽卡记录、新角色 1056、重复角色转换 10 碎片、8 个钥从及 110 辉芒，重登保持。用户其余整批回报正常，但未逐项留下数值与截图；邮件 1020 的 attach_flag=2，礼物 30012 仍为 5，后者缺赠礼消耗证据。各项状态见客户端验收表，不写 M2 全过。

N-1 已修复：真实 PC 332 战报含英雄 1084 和两个精确空队伍槽，旧解析器把空槽当非法角色，导致整份血量报告无效。仅扩展 `battle_server.py:245` 现有解析器跳过精确空槽，保留总槽数最多 32、全空拒绝、非空 HP／wire／重复字段拒绝及业务编队名单校验。原始 74B battle-info 的 SHA256 为 `8643f2f5ef1a72f65fbef67241d17fdfa24c4d2b95ccb1a0a3bcd098765df0b2`；它测得 HP 8502／10000。

新增 1 个现有类内集成用例；改前 2 项定向检查 exit 1，新增例结算失败，修后 3 项 exit 0。多维 35／Hodur 20／战棋定向 1 均 exit 0，命令见上表；定向与继承有重复，不相加为独立覆盖。A2-W01 的既有资源关闭告警保留。新增生产模块／类／顶层函数／参数／配置键均为 0，临时原始报文诊断块已删除。

N-1 实机复验通过：用户回报“正常了”，同一 UID 的 `server-fixed.log:219`、`:225`、`:230` 记录 54032→18012→18014；前／后快照场景 3035111→3035401、battle_count 0→1、hp_report_complete false→true，当前 HP 9250／10000，两份 quick_check 均为 ok。证据为 `n1-client-fixed-acceptance.json`、`snapshots/11-before-fixed-client.db` 与 `snapshots/n1-after-fixed-client.db`。本场实测与原始报文夹具来自不同战斗；完整一局及任务／成就未验。

N-2 已登记、未修复：新档登录三次下发空 SC42001，本地联合特勤视图固定读取三个组，与用户黑屏相符，但没有当前客户端 Lua 栈。42002 无真实 handler，42004 仅空 42005 模板；旧 Lua／master 分组不证明 332 新档契约，不能复制其他 owner 的刷新计数或猜组。补证前不扩完整刷新玩法。

本轮恢复已回读：游戏及服务 PID 24768 均已退出，exec 35738 经 Ctrl+C 退出 1；`hosts-transaction.ps1 -Action Restore` 退出 0，hosts 原始 65492 字节及 SHA256 完全一致。35 TCP＋UDP 6105 可独占绑定，9 个保护文件及客户端主清单未变；两关键域独立 DNS 查询为 203.107.63.115。最新证据为同目录 `cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`。

根 Codex 与 `gpt-6-luna/high` 完成功能、共享执行路径和权限边界复核。共用解析器仅一处，Polyhedron／Hodur／Warchess 的名单校验保留；同类已扫，无其他重复解析器。单独复杂度复核删除了临时原始报文日志块及交付记录中过期的活动状态，剩余删除清单：无。B1 已收尾并提交 `0112cd0`；N-2 维持 filed。未启动 B2，后续等待用户确认。
