# 2026-11-15 本地集成与主题分支

## 概览

已按图片顺序保存成果、同步上游、排重并拆出 12 个本地主题分支。每个分支直接基于 `origin/main@5768ca7`，各有 1 个本地提交。

按你补充的“注意是本地提交”执行：没有推送，没有创建远端 PR。当前工作分支为 `main`。

## 快速查看

先查看某个主题的差异：

```powershell
git diff origin/main...codex/pr-battle-empty-party-slots-20261115
```

再查看该主题的本地提交：

```powershell
git log --oneline origin/main..codex/pr-battle-empty-party-slots-20261115
```

## 2. 保存本地成果

| 本地提交 | 用途 |
| --- | --- |
| `6480d45` | 保存开始时的 13 个已跟踪改动文件，形成 A/B 成果基线。 |
| `ebbf500` | 合并最新上游，保留本地修复并解冲突。 |
| `00143d6` | 导入验收改用上游已有的道具发放接口，解除对 GM 套装扩展的依赖。 |
| `f34600e` | 测试奖励目录改为直接只读查询，解除对抓包导入扩展的依赖。 |

备份分支：`codex/ab-baseline-20261115`，指向 `6480d45`。拆分前集成源码为 `f34600e`。

## 3. 同步上游

上游从 `26c2769` 更新到 `5768ca7`，新增 2 个提交。`git diff --shortstat 26c2769..origin/main` 实测 2,691 个文件变化，包含上游新增资源文件，不代表本地修复规模。

| 上游提交 | 内容 |
| --- | --- |
| `bb767c1` | CDN 下载、存档管理和 332 清单。 |
| `5768ca7` | 移转之花跨池扣费。 |

本次处理 9 个冲突文件：

- `v5_server/dynamic_versions.json`、`v5_server/native_manifest_sources.json`：使用上游三平台登记。
- `v5_server/save_slot_manager.py`：保留注册表跨进程锁、回读及恢复；面板和网关共用上游 `delete_save`。
- `v5_server/server_net.py`：保留上游 `busy_message` 接口，最终与上游一致。
- `v5_server/web_src/src/panels/Inventory.tsx`：保留上游在线、认证和存档范围状态，接入本地套装与材料操作。
- `v5_server/static_web/app.js`、`v5_server/static_web/control-panel.html`：从合并源码重新构建。
- `v5_server/tools/verify_manifest_management.py`：保留上游完整测试，最终与上游一致。
- `v5_server/tools/verify_slot_refresh.py`：保留双方测试和注册表原字节恢复断言。

### 本轮适配位置

| 位置 | 原因 |
| --- | --- |
| `v5_server/resource_distribution.json:5` | 选择已核对相同的上游 PC 332 清单。 |
| `v5_server/save_slot_manager.py:321` | 跨进程锁和原字节恢复继续保护注册表，删除路径使用上游共用实现。 |
| `v5_server/web_src/src/panels/Inventory.tsx:205` | 在上游真实库存状态中保留已验写操作和存档切换隔离。 |
| `tests/m3_import_check.py:87` | 用已有发放接口准备同样的 6 件刻印，允许导入分支独立验证。 |
| `tests/m3_import_check.py:334` | 回收夹具适配暂存目录，并保留路径及文件类型检查。 |
| `tests/m4_gm_api_check.py:68` | 临时存档管理器提供上游新增的真实锁和面板请求生命周期。 |
| `v5_server/tools/verify_launch_cycles.py:68` | 启动周期夹具适配上游面板管理器；两个目录创建允许已存在。 |
| `v5_server/tools/verify_save_api_panel.py:269` | 两处调用使用会抛出失败的统一注册表写入接口。 |
| `v5_server/tools/verify_slot_gateway_actions.py:107` | 补齐假对象的锁状态，并更新注册表写入断言。 |
| `v5_server/tools/verify_slot_refresh.py:199` | 保留上游刷新检查和本地注册表恢复用例。 |
| `v5_server/tools/verify_minigame_point_rewards.py:20` | 直接只读查询静态目录，解除测试对导入扩展的依赖。 |

前端产物 `v5_server/static_web/app.js:1` 和 `control-panel.html:1` 由构建命令生成。

## 4. 重新比较差异

4 份本地 PC 332 清单与上游逐字节相同。已删除重复的 `native-pc-6a610d4d8550` 目录，并将本机资源选择改为上游 `native-pc-2aa906ca92fa`。原文件仍可从基线提交恢复。

哈希和大小证据：[manifest-dedup.json](../../archive/local-pr-20261115/manifest-dedup.json)。`dynamic_versions.json`、`native_manifest_sources.json`、`server_net.py` 和 `verify_manifest_management.py` 已没有相对上游的差异，未重复拆分。

除本记录外，以下 34 个差异文件保留在本地集成分支；其余 63 个文件分入主题分支：

| 文件 | 保留原因 |
| --- | --- |
| `AGENTS.md` | 本地规则、计划、审阅或验收记录。 |
| `M2-执行计划.md` | 本地规则、计划、审阅或验收记录。 |
| `M2-数值bug登记簿.md` | 本地规则、计划、审阅或验收记录。 |
| `M2-数值走查清单.md` | 本地规则、计划、审阅或验收记录。 |
| `M3-执行计划.md` | 本地规则、计划、审阅或验收记录。 |
| `M4-执行计划.md` | 本地规则、计划、审阅或验收记录。 |
| `_review/_ratio.py` | 本地规则、计划、审阅或验收记录。 |
| `_review/backup_project.ps1` | 本地规则、计划、审阅或验收记录。 |
| `_review/关键差异报告.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/backlog-status-2026-11-05.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-12-repair-plan.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-12-repair-progress.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-ai-pilot-review.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-ai-split-subplans.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-client-acceptance.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-gameplay-contracts.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-repair-delivery.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-repair-handoff.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/plans/2026-11-13-repair-plan-review.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/superpowers/plans/2026-11-05-m2-integration.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/superpowers/specs/2026-11-05-m2-integration-design.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/upstream-update-2026-11-06.md` | 本地规则、计划、审阅或验收记录。 |
| `docs/upstream-update-2026-11-12.md` | 本地规则、计划、审阅或验收记录。 |
| `tests/m2_defect_checks.py` | 跨多个修复主题的集成验收；各主题已单独执行对应检查。 |
| `v5_server/AetherGazer.mobileconfig` | 本机证书或安装描述文件。 |
| `v5_server/docs/repair_tracker.json` | 本地规则、计划、审阅或验收记录。 |
| `v5_server/resource_distribution.json` | 本机缓存位置或资源选择。 |
| `v5_server/sdk_ca.crt` | 本机证书或安装描述文件。 |
| `v5_server/sdk_ca.mobileconfig` | 本机证书或安装描述文件。 |
| `v5_server/sdk_cert.cer` | 本机证书或安装描述文件。 |
| `v5_server/sdk_cert.crt` | 本机证书或安装描述文件。 |
| `v5_server/server_config.json` | 本机缓存位置或资源选择。 |
| `v5_server/tools/verify_sphero_leisure.py` | 其他阶段的既有夹具；原生资料缺证保持登记，本轮不扩展验收。 |
| `实施计划.md` | 本地规则、计划、审阅或验收记录。 |

## 5. 逐项拆分本地主题分支

所有分支均在实际切换后验证，再作本地提交。没有堆叠分支。公共握手测试夹具在战报和回归分支使用同一路径、同一内容，避免引入生产依赖。

| 本地分支 | 提交 | 文件数 | 主题 |
| --- | --- | --- | --- |
| `codex/pr-equip-decompose-response-20261115` | `59c752f` | 1 | 修复刻印分解设置响应缺失 |
| `codex/pr-polyhedron-task-event-20261115` | `d80eb6b` | 1 | 修复多维通关事件空上下文与任务通知 |
| `codex/pr-certificate-publication-20261115` | `87f8d6e` | 1 | 串行发布证书并原子替换文件 |
| `codex/pr-battle-empty-party-slots-20261115` | `e97034d` | 5 | 按原生战报跳过空队伍槽并保留血量边界 |
| `codex/pr-pc-installed-resource-cache-20261115` | `6227935` | 3 | 复用已安装 PC 资源并识别 B 服目录 |
| `codex/pr-windows-source-launcher-20261115` | `ca9452d` | 1 | 识别系统 Python 3.14 与标准源码目录 |
| `codex/pr-regression-fixtures-20261115` | `f4f3115` | 13 | 恢复回归夹具并验证版本与启动周期边界 |
| `codex/pr-gm-save-writes-20261115` | `9a59d29` | 8 | 让 GM 写入所选存档并回读真实库存 |
| `codex/pr-capture-save-import-20261115` | `83429f3` | 11 | 将审核后的抓包导入新存档并同步槽位 |
| `codex/pr-ai-offline-prompts-20261115` | `8c79df1` | 15 | 外置 AI 离线提示词并保存待审校试稿 |
| `codex/pr-protocol-smoke-tools-20261115` | `bb9a634` | 4 | 保存协议冒烟基线与抓包最小参数工具 |
| `codex/pr-battle-log-diff-20261115` | `5129da8` | 1 | 按会话时间窗比较战斗帧序 |

### 分支验证命令与实际结果

以下命令均退出 0。用例存在继承和重叠，不相加作为独立覆盖数。证书、分解和任务检查复用已保存的 M2 验收函数；临时入口位于 `archive/local-pr-20261115/check-m2-topic.py`。

| 主题 | 实际命令 | 日志结果 |
| --- | --- | --- |
| equip-decompose-response | `python -B -X utf8 archive/local-pr-20261115/check-m2-topic.py test_gen_13057_payload` | 退出 0 |
| polyhedron-task-event | `python -B -X utf8 archive/local-pr-20261115/check-m2-topic.py test_on_polyhedron_pass_ctx_none test_on_polyhedron_pass_advances_cond423` | 退出 0 |
| certificate-publication | `python -B -X utf8 archive/local-pr-20261115/check-m2-topic.py test_gen_cert_existing_check_verifies_leaf test_gen_cert_concurrent_atomicity test_gen_cert_failed_publish_preserves_existing test_gen_cert_process_atomicity` | 退出 0 |
| battle-empty-party-slots | `python -B -X utf8 v5_server/tools/verify_polyhedron_lifecycle.py` | Ran 35；OK |
| battle-empty-party-slots | `python -B -X utf8 v5_server/tools/verify_hodur_challenge.py` | Ran 20；OK |
| pc-installed-resource-cache | `python -B -X utf8 v5_server/tools/verify_resource_storage.py` | Ran 16；OK |
| windows-source-launcher | `dotnet build LocalServer/LocalServer.csproj -p:Platform=x64 --no-restore --nologo -v:minimal` | 构建成功；0 警告、0 错误 |
| regression-fixtures | `python -B -X utf8 v5_server/tools/test_battle_entry_timing.py` | Ran 6；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/test_commit_recovery.py` | Ran 10；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/test_hero_response_boundary.py` | Ran 13；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/test_linux_setup.py` | Ran 41；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/test_settlement_retry_boundary.py` | Ran 8；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_battle_entry_fail_closed.py` | Ran 12；OK；1 项既有 skip |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_boss_reward_guard.py` | Ran 21；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_client_version.py` | Ran 13；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_overflow_ownership.py` | Ran 21；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_rogueteam_tutorial_skip.py` | Ran 5；OK |
| regression-fixtures | `python -B -X utf8 v5_server/tools/verify_launch_cycles.py` | Ran 7；OK |
| gm-save-writes | `python -B -X utf8 tests/m4_gm_api_check.py` | Ran 10；OK |
| gm-save-writes | `npm --prefix v5_server/web_src run check` | TypeScript 检查通过 |
| capture-save-import | `python -B -X utf8 tests/m3_import_check.py` | Ran 14；OK |
| capture-save-import | `python -B -X utf8 v5_server/tools/verify_slot_refresh.py` | Ran 15；OK |
| capture-save-import | `python -B -X utf8 v5_server/tools/verify_save_api_panel.py` | Ran 19；OK |
| capture-save-import | `python -B -X utf8 v5_server/tools/verify_slot_gateway_actions.py` | Ran 18；OK |
| ai-offline-prompts | `python -B -X utf8 tests/m4_ai_prompt_check.py` | Ran 4；OK |
| protocol-smoke-tools | `python -B -X utf8 tests/smoke_dispatch.py` | 423 操作、52 有效参数；0 未捕获异常、0 行为变化 |
| protocol-smoke-tools | `python -B -X utf8 tools/gen_min_params.py --selftest` | [+] selftest 通过（cs_16010 黄金样例 + 覆盖量 64 ≥ 60） |
| battle-log-diff | `python -B -X utf8 tools/diff_battle_logs.py archive/local-pr-20261115/battle-log-fixture/a.log archive/local-pr-20261115/battle-log-fixture/b.log` | A 为 2 个协议标记，B 为 4 个协议标记；准确显示新增 cs_54032/sc_54033 |

各分支的完整文件清单、命令、退出码和日志：[split-results.json](../../archive/local-pr-20261115/split-results.json)。

### 集成验证和交互

- `python -B -X utf8 tests/m2_defect_checks.py`：10 项通过，`ALL PASSED`。
- `python -B -X utf8 v5_server/tools/verify_manifest_management.py`：25 项通过。
- `npm --prefix v5_server/web_src run check`：退出 0。
- `npm --prefix v5_server/web_src run build`：退出 0。保留 8 条既有 CSS 警告和包体积提示。构建进程使用仓库临时目录作为 TEMP/TMP。
- 浏览器使用临时同 UID 双存档：other 档发放 6 件套装，持仓 14 种变为 20 种；清理确认框显示 other.db / UID 42，取消成功；切换 selected 档后持仓仍为 14 种、旧反馈清空、操作按钮恢复可用。
- 临时浏览器服务已停止；未重启正式服务，未修改 hosts 或系统信任。

![库存切换回读](C:/Users/<user>/Desktop/Alpha-Persei-Cluster/archive/local-pr-20261115/inventory-browser.png)

### 复核与保留事项

根 Codex 完成功能复核。GPT-6 Luna high 独立复核锁顺序、共享删除路径、GM 存档范围和只读夹具。

已修复并扫查的兼容问题：

- `tests/m4_gm_api_check.py`、`v5_server/tools/verify_launch_cycles.py`：用真实临时 SaveSlotManager 替换缺少面板锁方法的假对象；同类站点为这 2 处。
- `v5_server/tools/verify_save_api_panel.py` 两处、`verify_slot_gateway_actions.py` 一处：移除旧 strict 参数调用或断言；生产及测试同类调用已扫查，无其他。
- `tests/m3_import_check.py`：回收夹具适配上游暂存目录，继续检查边界、符号链接和子项类型。另两处回收夹具没有旧目录布局假设。
- `v5_server/tools/verify_slot_gateway_actions.py`：补齐已有假对象缺失的注册表锁深度。
- `tests/m3_import_check.py`、`verify_minigame_point_rewards.py`：解除不必要的跨主题夹具依赖，保持数据和断言。

独立复杂度审查：删除重复的 4 份清单；只读查询替代复制表；删除额外候选清单：无。

真实抓包导入的缺失邮件／协议、AI 试稿审校、B0-S01、N-2 和历史 WAL 缺证保持原登记。Lua 原生对照仍缺资料，显式失败要求保留；本次未将该项计为通过。

本次新增 1 份整理记录。自主新增／删除代码模块、类、顶层函数均为 0；主题分支只整理已有实现和必要夹具适配。删除的 4 个文件均为重复清单。

### 计划覆盖

| 图片步骤 | 状态 | 位置与验收 |
| --- | --- | --- |
| 2 保存成果 | done | 6480d45；备份分支 codex/ab-baseline-20261115。 |
| 3 同步上游 | done | ebbf500；origin/main@5768ca7 为 main 祖先，9 个冲突已解。 |
| 4 重新比较 | done | 本文第 4 节；重复清单已核对并移除，其余本地文件逐项说明。 |
| 5 逐项拆分 | done（本地） | 本文第 5 节；12 个分支各 1 个提交，父提交统一为 5768ca7，逐分支验证退出 0。 |

最终核对使用 `git status --porcelain`、`git diff --check`、每分支 `git rev-parse <branch>^` 和 `git rev-list --count origin/main..<branch>`。
