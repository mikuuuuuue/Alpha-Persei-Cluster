# 2026-11-12 上游更新记录

本地 `main` 已合入上游 v5.0.4 更新。
你可以重新启动服务，检查新增的启动配置页和周期管理卡片。

## 同步范围

| 项目 | 结果 |
| --- | --- |
| 更新前本地提交 | `392d32c` |
| 更新前上游提交 | `8fdb41e` |
| 本次上游提交 | `26c2769cd1d55b166892f497b18f1fecc819a436` |
| 新提交 | `40ee57d`：Linux 认证与 Nginx；`26c2769`：启动配置与任务周期 |
| 上游差量 | 2 个提交、38 个文件，无合并冲突 |
| 更新前备份 | `codex/backup-before-upstream-20261112-392d32c` |
| 本地分支 | 保留 `main` 和本次备份，替换旧备份分支 |

文件数来自 `git diff --shortstat 8fdb41e..26c2769`。
上游文件按远端原文导入。本地既有修复和 7 个未跟踪文件保留。

## 主要更新

- **启动配置**：Web 面板集中设置网络端口、资源模式、存档和日志参数。保存后可通过受支持的托管进程重启内核。见 `v5_server/launch_settings.py:233`。
- **周期管理**：面板显示日常、周常、梦境和战令等 8 类周期进度。重置需校验当前状态，并要求对应玩家离线。见 `v5_server/panel_cycles.py:260` 和 `v5_server/gm_api.py:2929`。
- **任务同步**：调整任务到期时间和日周重置通知。见 `v5_server/task_cycle_notifications.py:27`。
- **Linux 部署**：登录前可加载面板登录页，管理 API 继续受认证保护。更新 Nginx 游戏入口、面板片段及上游证书校验。见 `v5_server/admin_session_auth.py:365` 和 `v5_server/linux_nginx.py:217`。
- **Windows 托管**：启动壳识别内核请求重启的退出码，并重新启动内核。见 `LocalServer/ServerSupervisor.cs:477`。

## 验证结果

以下命令从仓库根目录运行；前端命令从 `v5_server/web_src` 运行。

| 命令 | 实际结果 |
| --- | --- |
| `python -X utf8 tests/m2_defect_checks.py` | 10 项通过，输出 `ALL PASSED` |
| `python -X utf8 tests/smoke_dispatch.py` | 423 个操作；有效参数覆盖 52 个；0 个未捕获异常，0 个基线变化 |
| `python -X utf8 v5_server/tools/test_admin_password.py` | 17 项通过；检查 113 个管理路由与方法组合 |
| `python -X utf8 v5_server/tools/verify_panel_password_integration.py` | 3 项通过 |
| `python -X utf8 v5_server/tools/verify_polyhedron_weekly.py` | 5 项通过 |
| `python -X utf8 v5_server/tools/test_linux_setup.py` | 41 项中 38 项通过、3 项错误，原因见下节 |
| `npm run check` | 退出码 0 |
| `npm run build` | 退出码 0；有 8 条 CSS 语法警告和包体大小警告 |
| `dotnet --version` | 未找到 .NET SDK；Windows 宿主构建未执行 |

另外，对上游改动的 22 个 Python 文件和 1 个 JSON 文件执行解析，均通过。
前端重建的 6 个文件按 Git 规则计算内容哈希，与远端一致。
冒烟检查只验证调度和返回结构。游戏、浏览器交互和真实 Linux 部署未实测。

## 已登记的上游测试问题

本节记录实际失败，不把这些测试计为通过。
这些文件直接来自上游，本次没有修改生产实现或测试断言。

| 位置 | 原因与影响 | 后续修复方向 |
| --- | --- | --- |
| `v5_server/tools/test_linux_setup.py:210` | 测试仍引用 `lm.runpy.run_path`；上游已改用新的启动流程。测试进入业务前抛出 `AttributeError`，无法验证密码文件挂载。 | 隔离当前启动调用，检查实际传递的密码文件环境变量。 |
| `v5_server/tools/test_linux_setup.py:233` | 同样引用已不存在的 `lm.runpy`，无法验证旧认证变量清理和临时参数覆盖。 | 按当前启动流程重建夹具，保留原有可观察行为断言。 |
| `v5_server/tools/test_linux_setup.py:585` | 半自动向导测试未隔离 Nginx 依赖；在 `linux_nginx.py:220` 检查真实 Nginx，当前主机没有该程序。 | 复用该测试文件的 `nginx_mocks()`，并提供符合新 HTTPS 站点要求的夹具。 |

处置：3 项均已登记，保持上游原文。
同类扫查：`v5_server/tools` 中 `lm.runpy` 仅上述 2 处；半自动向导漏隔离的场景仅上述 1 处。

## 复核与完成条件

第二审阅者：GPT-6 Luna，推理级别 high。
审阅范围：本地修复兼容性、启动与周期接口权限、测试错误和本次更新记录。
独立复杂度审查删除清单：无。

本次自主新增 1 份更新记录；新增和删除代码模块、类、顶层函数均为 0。
上游功能按原提交导入，测试失败和构建限制如实保留。

| 计划项 | 状态与位置 |
| --- | --- |
| 检查上游差异 | 已完成：`origin/main` 的 2 个新提交 |
| 保存更新前版本 | 已完成：备份分支指向 `392d32c` |
| 合并更新 | 已完成：本地 `main`，无冲突 |
| 保留最新两个本地分支 | 已完成：`main` 和本次备份 |
| 验证并登记限制 | 已完成：本文件验证结果和测试问题；Windows 宿主构建因缺少 SDK 未执行 |

本次更新本地源码，未向远端推送，也未重启正在运行的服务。
