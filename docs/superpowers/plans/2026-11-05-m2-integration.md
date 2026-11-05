# M2 Integration Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for continuous execution in the current checkout.

**Goal:** 将 M2 有效修复整合到本地 `main`，保留新版功能。

**Architecture:** 合并 M2 历史，逐项处理冲突。复用 `cdn_integrity.object_lock`，改进现有证书写入函数。

**Tech Stack:** Python、SQLite、现有前端检查工具。

**Spec:** `docs/superpowers/specs/2026-11-05-m2-integration-design.md`

## Artifacts

- 新生产模块、类、顶层函数：0。删除生产模块、类、顶层函数：0。
- M2 原有 4 个 Python 文件随合并纳入：`tests/m2_defect_checks.py`、`tests/smoke_dispatch.py`、`tools/gen_min_params.py`、`tools/diff_battle_logs.py`。它们的测试及 CLI 入口沿用 M2。
- `PolyhedronRunManager.settle_run(uid, db, ctx)` 调整已有签名；两个调用方为 `PolyhedronRewardOp.apply` 和 `PolyhedronSettleQueryOp.apply`。
- `gen_cert._write_with_backup(path, data)` 保持已有接口；调用方为证书生成和描述文件生成。
- `cdn_integrity.object_lock` 增加证书生成调用方；现有调用方为 CDN 发布流程。
- 在 M2 测试文件增加章节回执、失败发布、多进程生成和缺少本地存档的测试。调用方为脚本测试入口和 pytest。
- 保留 M2 的 5 个文档或数据文件，并恢复标为历史的 `实施计划.md`。
- 新增设计和计划文档 2 个。生产结构净变化为 0；M2 的工具和测试文件是历史整合内容。

## Global Constraints

- 使用用户指定的当前 `main`，以备份分支提供恢复点。
- 保留上游新版接口、根证书策略和 `sc_24065` 定义。
- 不改真实数据库、密钥、系统信任库或现有未跟踪文件。
- 不增加生产参数来辅助测试。

## Review Focus

- 两个结算调用点均传递真实上下文，通知进入实际回包。
- 多个生成进程不会交错写出不配套的证书。
- 发布失败时，原有文件保持可用，临时文件被清理。
- 强制续签保持根证书，检查命令输出有效 JSON。
- 冒烟基线核对操作集合，新增或缺失操作必须被发现。

## Task 1: 合并准备和测试红灯

- [x] 保存恢复分支和数据备份。
- [x] 先引入 M2 测试文件，扩展真实结算通知与证书发布测试。
- [x] 运行测试，确认刻印回包、任务通知和发布保护的失败原因。
- [x] 执行不提交的 M2 合并，记录 3 个预期冲突。

## Task 2: 业务修复

- [x] 保留 `main` 的 `codec.py`，确认 `sc_24065` 的 `result=0` 编码为 `0800`。
- [x] 接受 M2 的刻印回包与空上下文保护。
- [x] 将真实 `ctx` 传入结算函数及两个操作调用点。
- [x] 验证任务进度落库，并在实际响应中包含 `sc_28007`。

## Task 3: 证书保护

- [x] 以新版 `gen_cert.py` 为基础，复用既有文件锁保护完整生成流程。
- [x] 将已有 `_write_with_backup` 改为唯一临时文件、刷新和原子替换。
- [x] 验证线程及进程并发、故障发布、根证书保持和 JSON 检查接口。

## Task 4: 工具、文档和交付

- [x] 合并忽略规则，保留 M2 文档，并标注旧总计划为历史记录。
- [x] 核对当前操作集合和旧基线差异，适配冒烟脚本并建立经核对的新基线。
- [x] 运行 M2 完整检查、全量冒烟和上游相关回归。
- [x] 进行不同模型复核和独立复杂度复核，处理确认问题。
- [x] 验证用户文件哈希和 Git 状态，将结果保存为本地合并提交。

## 验证记录

M2 检查 10 项、付费权益 17 项、CDN 30 项、资源清单 20 项、版本隔离 13 项、打包合同 17 项均通过，共 107 项。408 个操作冒烟完成，52 个命中抓包参数，未捕获异常和基线结构变化均为 0。无本地存档条件下，M2 检查另行通过。生产代码已经不同模型复核，确认问题已修正。

原有本地证书与私钥不配套的部署问题仍存在；本次不执行证书重新部署。
