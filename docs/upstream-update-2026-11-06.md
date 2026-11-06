# 2026-11-06 上游更新记录

已将上游 `origin/main` 的 5 个新提交合入本地 `main`，更新到 v5.0.3。
重新启动服务后，你可以按 [README](../README.md#三-快速部署与多端运行指南) 检查实际游戏体验。

## 同步范围

| 项目 | 结果 |
| --- | --- |
| 更新前本地提交 | `f97ea2e` |
| 更新前上游提交 | `92671ab` |
| 本次上游提交 | `8fdb41e88e2b5b2ca91381d815f60a125c48e0fb` |
| 上游差量 | 5 个提交、440 个文件；由 `git diff --shortstat 92671ab..8fdb41e` 统计 |
| 更新前备份 | `codex/backup-before-upstream-20261106-f97ea2e` |
| 冲突处理 | `.gitignore`、`v5_server/operations.py`、`v5_server/polyhedron_service.py` 全部采用远端原文 |
| 本地提交 | 保留原有 47 个独有提交的历史；冲突内容按远端覆盖 |

原有 6 个未跟踪文件保持不变，已核对 SHA-256。
采用远端 `.gitignore` 后，原先被忽略的 `tests/min_params.json` 会显示为未跟踪文件。
该文件保留在本地，不纳入本次提交。

## 主要更新

- **面板密码**：增加密码登录、会话撤销、CSRF 校验和失败次数限制。Linux 配置向导要求设置管理员密码。
- **虚构推演**：完善节点切换、隐藏岛、战术指令、能量继承、成就和重登恢复。新存档跳过 101 教学。
- **常驻小游戏**：补充刺桐巷任务、探索、收集和海战。修复小游戏领奖、结算及断线恢复。
- **周常玩法**：调整多维变量、梦境再构和失序深区的周期，补充首领记分、跨期校验及队伍隔离。
- **存档一致性**：修复成就重复领取、道具扣除、钥从与刻印操作、角色获取、签到和月卡发奖。
- **部署与资源**：Linux 入口统一为 `sh server.sh`。CDN 增加关闭、仅穿透、穿透存盘模式。Android 官服渠道改为 7。

完整条目见 [CHANGELOG](../CHANGELOG.md#v503--2026-11-06) 和 [上游源码更新说明](../v5_server/docs/source_update_20261106.md)。

## 本地测试适配

`tests/m2_defect_checks.py` 使用合法多维探索数据验证两个结算入口。
原有任务进度、成功回执和 `sc_28007` 通知断言均保留。
临时丢弃结算 `ctx` 后，测试按预期失败，证明仍能捕获原缺陷。

`tests/smoke_baseline.json` 从 408 个操作更新到 423 个操作。
原有操作全部保留，新增 15 个操作。
已复核 46 个既有操作的返回结构变化，再使用原有 `--update-baseline` 更新。
`tests/smoke_dispatch.py` 的操作集合和新增失败断言保持不变。

冒烟检查验证调度和返回结构。其中 52 个操作有有效参数。
它不能代替完整业务链和游戏客户端实测。

## 验证结果

以下命令从仓库根目录运行；前端命令从 `v5_server/web_src` 运行。

| 命令 | 实际结果 |
| --- | --- |
| `python -X utf8 tests/m2_defect_checks.py` | 10 项检查通过，输出 `ALL PASSED` |
| `python -X utf8 tests/smoke_dispatch.py` | 423 个操作，0 个未捕获异常，0 个基线变化 |
| `python v5_server/tools/test_admin_password.py` | 17 项通过；检查 111 个管理路由与方法组合 |
| `python -B v5_server/tools/test_commit_recovery.py` | 10 项通过，由第二审阅者执行 |
| `python -X utf8 v5_server/tools/test_cdn_relay.py` | 17 项通过 |
| `python -X utf8 v5_server/tools/test_http_disconnect.py` | 6 项通过 |
| `python -X utf8 v5_server/tools/test_linux_setup.py` | 41 项通过；使用隔离配置和模拟系统操作 |
| `python -X utf8 v5_server/tools/verify_polyhedron_weekly.py` | 5 项通过 |
| `python -X utf8 v5_server/tools/verify_panel_password_integration.py` | 2 项通过 |
| `npm run check` | 退出码 0 |
| `npm run build` | 退出码 0；8 条 CSS 语法警告和包体大小警告 |

另外，对上游改动中的 271 个 Python 文件执行 AST 解析，对 34 个 JSON 文件执行 JSON 解析，均通过。
前端重建产物与上游版本的 Git 内容一致。
游戏客户端、浏览器交互和真实 Linux 部署未实测。

## 已登记的上游验证缺口

执行 `python -m unittest discover -s v5_server/tools -p 'verify_polyhedron_*.py'` 时，3 个模块导入失败：

- `verify_polyhedron_achievement_boundary.py`
- `verify_polyhedron_lifecycle.py`
- `verify_polyhedron_login.py`

共同原因是 `v5_server/tools/verify_report_small_fixes.py:24` 引用了缺失的 `test_battle_entry_timing`。
同次发现运行中，独立的周期测试 5 项通过。
因此，上述 3 个模块的业务测试未执行。

对 178 个上游工具脚本的静态依赖扫查，又确认了下列同类缺口。
以下 8 个辅助模块均未包含在上游提交中；静态依赖结果不代表已运行这些测试。

| 引用位置 | 缺失模块 |
| --- | --- |
| `v5_server/tools/verify_report_small_fixes.py:24` | `test_battle_entry_timing` |
| `v5_server/tools/test_settlement_retry_boundary.py:17` | `audit_core_regular_old_settlement_probe` |
| `v5_server/tools/test_hero_response_boundary.py:12` | `test_cost_fallback_boundary` |
| `v5_server/tools/test_hero_response_boundary.py:13` | `test_entity_rollback_notifications` |
| `v5_server/tools/verify_battle_entry_fail_closed.py:14` | `test_issue_hero_payload` |
| `v5_server/tools/verify_battle_entry_fail_closed.py:15` | `verify_mainline_trial_entry` |
| `v5_server/tools/verify_overflow_ownership.py:145` | `verify_all_cosmetic_mail` |
| `v5_server/tools/verify_rogueteam_tutorial_skip.py:7` | `verify_save_generator` |

处置：已登记。待上游补齐测试文件后，重新运行受影响脚本。
本次同步保持这些上游脚本原文。

## 复核与交付范围

第二审阅者：GPT-6 Astra，推理级别 high。
审阅范围：冲突决策、本地修复调用链、测试适配和基线变化。

已修复：本地多维测试夹具与新版前置条件不兼容；冒烟基线缺少新增操作。
已登记：上游缺少测试辅助文件，部分验证无法执行。
独立复杂度审查的删除清单：无。

本次自主新增 1 份更新记录，修改 2 个现有测试文件；新增和删除代码模块、类、顶层函数均为 0。
上游 440 个文件按原提交导入，不另做功能扩展。

| 计划项 | 状态与位置 |
| --- | --- |
| 建立更新前备份 | 已完成：备份分支指向 `f97ea2e` |
| 合并上游并解决冲突 | 已完成：本地 `main`；3 个冲突文件采用远端版本 |
| 验证本地兼容性 | 已完成：上述测试命令；上游缺失依赖已单独登记 |
| 总结更新与限制 | 已完成：本文件、`CHANGELOG.md:3` |

本次仅更新本地源码并生成验证产物，未向远端推送或部署运行服务。
