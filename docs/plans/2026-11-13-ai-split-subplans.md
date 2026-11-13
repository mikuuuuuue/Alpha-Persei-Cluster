# H 前置子计划：AI 与拆分

对应 [`2026-11-12-repair-plan.md`](./2026-11-12-repair-plan.md) 批次 H。H1 离线实现和 10 人试稿已交付；本文件保留执行前证据与后续门禁。

| 票据 | 前置结论 | 当前状态 |
|---|---|---|
| H1 AI | 已完成三键片段、五类模板外置、4 项离线测试和 10 人未审校试稿。 | 离线实现完成；试稿审校、全量扩展、真实回填、在线和游戏内验收待完成。 |
| H2 拆分 | 已记录三文件符号规模和领域边界；本轮基础回归通过。 | 快照完成；M2 真机收官未通过，禁止迁移业务代码。 |

## H1：AI 提示词、问候信与人格

### 执行前源码证据

| 结论 | 证据 |
|---|---|
| API 凭据按存档保存 | `ai_api_profiles.CONFIG_KEY` 为 `ai.api_profiles.v1`，读取 `server_global_config`；运行时清空默认提供方凭据后，仅装载当前存档 profile。 |
| 旧全局配置不能恢复 | `ai_bot_config.get_bot_config(db)` 走 `ai_api_profiles.resolve(db)`；无 DB 返回无凭据模板。旧环境读取和写入入口 `get_api_key()`、`set_env_variable()` 已停用。 |
| 现有提示词片段为 v1 | `data/ai_prompt_fragments.json` 执行前含 version、context_header、player、time_of_day、affinity、absence、birthday 七组。原 M4 中的三键为 `role_guard`、`term_glossary_head`、`output_style`。 |
| 五类问候 prompt 仍内联 | `AITranslator._generate_single_greeting()` 执行前区分角色生日、管理员生日、普通节日、总务处节日、总务处管理员生日五类。须移出原文，维持生成条件、标题、附件、落款及无 key fallback。 |
| 51 人名册不等于真实人格覆盖 | roster 有 51 条，`system_prompt` 字段不作存档事实。人格运行来源是对应存档 `ai_characters` 表；不得仅凭 JSON 名册回填。 |

证据路径和 SHA256（执行前取证快照，后续实现结果见文末）：

| 来源 | SHA256 |
|---|---|
| `M4-执行计划.md`（执行前版本） | `a2cadc151c0e2dff7790c8303eb6e4773543cb4509da23dd3ffce6fad4e66b5f` |
| `v5_server/ai_api_profiles.py` | `b6d94085ae7a0fb25eca0fe2f25079bbac7cfe11ea9394eec0ed33c88ae0908c` |
| `v5_server/ai_bot_config.py` | `70c75c19607ab831d9c7bb24ee54383355e6b1c279907429d7f7a9779b080efe` |
| `v5_server/ai_translator.py` | `fb616e28793c9703be5280861cb099989f82374e082d7dcc59858dbe9fc199e9` |
| `v5_server/data/ai_prompt_fragments.json` | `b6892f363e4a3c8a489322ae504cce8b97c2dbe78aec99e4efb24c718906b4e6` |
| `v5_server/data/ai_holiday_templates.json` | `92d664c104e1d981e82aec8f3beb59879082a1de5a2e20ad96d94ae14ac0ac64` |
| `v5_server/data/ai_characters_roster.json` | `664d7d0333417707bbe262588927e63e0b0c12461f177a76443e2ed35991bd18` |

### 实施顺序和验收门

1. **离线测试基线。** 新增独立测试，仅用临时库、fixture 和离线 fallback。覆盖存档 API profile 隔离、掩码回读、路由和凭据不泄露；不读取任何现存 API profile 内容。记录 51 个 roster 项及存档人格覆盖差异，但真实库仅以获授权的脱敏读取方式审计。
2. **三键提示词片段。** `ai_prompt_fragments.json` 由 v1 改 v2，只新增 `role_guard`、`term_glossary_head`、`output_style` 三个顶层片段键。现有七组文本原样保留；v1 文件仍可读取。测试检查拼接次序、缺键处理和注入输入转义。
3. **问候模板外置。** 原样外置五类 prompt 文本，保留每类事件的使用条件、信件解析、静态 fallback、礼物白名单和发送行为。离线检查比较迁移前后构造的提示词和邮件结构。
4. **10 人试稿与审校。** 先选 10 名角色，保存来源事实、稿件版本和审校意见。稿件需逐项审查角色身份、语气、关系边界、知识范围和禁忌。未由内容审校人明确通过，不生成或启用 51 人全量数据。
5. **51 人扩展。** 只有 10 人门通过后，按 roster 和当前存档角色数据逐人补齐。离线断言检查 ID、归属、非空文本和禁用内容；覆盖名册不自动覆盖存档原人格。
6. **真实库回填门。** 任何读取真实存档进行审计或回填都必须在动作时另有授权。dry-run 报告只列 UID 脱敏标识、角色 ID、字段是否为空和变更摘要，不打印人格正文、API 凭据或用户内容。`--apply` 先备份，经授权后在隔离副本验证，真实写入前再次确认目标路径和目标行数。
7. **在线与游戏验收门。** 在线调用必须在当轮获授权、明确提供测试 profile、目标和费用边界后执行。检查超时、错误响应、fallback 和数据保存；在线模型输出需由人审。最后在隔离客户端验证游戏内私聊与问候邮件。离线测试通过、在线调用通过和游戏内验收分别记状态。

**动作门禁：** 不调用在线模型、不读取真实密钥、不查看真实存档人格内容、不写入真实存档。10 人试稿在离线阶段交付，待你审校；不把契约或离线测试标成在线／客户端通过。

## H2：M2 门禁与模块拆分

### 当前符号快照和职责边界

本快照用于安排职责，不是拆分设计授权。数据来自当前工作区 AST 和源码顶层声明。

| 文件 | 当前规模 | 符号/职责 | 后续边界 |
|---|---:|---|---|
| `v5_server/account_db.py` | 7,342 行；`AccountDB`、`_Transaction`；2 个顶层函数 | 存档连接和事务、SQL、用户资产及业务持久化访问。 | 先画出现有表/方法消费者图；复用已存在的服务和账本抽取。不得因体积单独建新包。 |
| `v5_server/operations.py` | 8,803 行；282 个顶层类、32 个顶层函数 | Operation 请求处理、字段校验、业务服务调用与协议回包。 | 按真实协议域标出注册表和每类 Operation；已有 Polyhedron、RogueTeam、WarChess、Mode4 服务优先视为职责边界。 |
| `v5_server/middleware.py` | 4,254 行；4 个顶层类、113 个顶层函数 | TCP 请求/响应包装、协议分派、战斗报文处理、异步通知与会话身份。 | 标出 `handle_request` 分派、各 `h_*` 调用和 battle/session 共享路径；共享执行路径需独立模型复核。 |

已有局部抽取可复用：`polyhedron_*`、`rogueteam_*`、`warchess_*`、`core_mode4_reward_service.py`。不得再复制这些领域实现或以行数作为拆分目标。

源代码 SHA256：

| 来源 | SHA256 |
|---|---|
| `v5_server/account_db.py` | `44a05f8c824b399e6c3ee4ef5f7075df4d15040b85cd7338e58e502f214cefa7` |
| `v5_server/operations.py` | `04011d5109111944b573ae7d5ade62f349b65f024d2dcdf9a067c7c2fca8530a` |
| `v5_server/middleware.py` | `74f6e78cc41021a097e17dc483ead3f0e3d87d4d6c084ec4475d2f3464068ec2` |
| `tests/m2_defect_checks.py` | `cd872249edc588494ec05752e614611cc122433b0aaa8e3274ff716c58026b04` |
| `tests/smoke_dispatch.py` | `eb6db729ce24c9eff2d57b55f123af82f3115528e3acb565434f18db9d04a2f1` |

### 门禁和子任务

1. **先复验 M2 能力。** 从总计划要求的当前基线 `main@4bec98f` 核实提交与工作区差异。执行 `python -B -X utf8 tests/m2_defect_checks.py`；缺 `tests/min_params.json` 时，只用既有本地抓包生成器按总计划生成，再执行 `python -B -X utf8 tests/smoke_dispatch.py`。当前总计划验收要求冒烟输出 **423 个操作、52 个有效抓包参数**。旧 M2 计划记录的 408/52 是历史结果，不代替当前基线复验。
2. **符号快照。** 冻结本次审计的三个源文件 SHA256；生成公开类/函数、内部 helper、直接调用点、注册点及跨模块消费者清单。对每个候选迁移点列至少一个生产 caller 与一个验证入口；无法解析动态注册的项标缺证，不猜调用图。
3. **职责映射。** 将符号映射到数据库访问、协议操作、middleware 三类既有职责，并引用已有专用服务；记录当前行为、调用方向、异常/返回约定、事务和依赖，不更改函数签名。
4. **拆分子计划。** 按数据库、操作、中间件分别提出可独立回滚的迁移批次，每批只移动一组有同一职责的符号；保留原导入门面、Operation 注册名、协议响应、事务边界和 session 行为。每批列文件、符号、调用者、迁移前后验证和回退点。
5. **持续门禁。** 任一 M2 检查失败、操作数量/参数命中数不符、动态调用边界未查清或共享执行路径未获不同模型复核，均不开始业务拆分。先修门禁证据或登记具体阻塞项。

### 当前门禁状态

2026-11-13 已复验当前提交 `4bec98f`：`tests/m2_defect_checks.py` 退出 `0`；冒烟退出 `0`，423 个操作、52 个有效参数，0 个未捕获异常。完整 M2 的 12 项客户端走查和 M-5 仍未完成，因此 **H2 当前门禁状态为“基础自动检查通过，客户端收官阻塞，不得迁移”**。

完整顶层符号、类方法、装饰器及语法可见调用点已保存为 `selftest_tmp/priority-repair/h2-symbols.json`。三个文件的条目数分别为 4／314／117；调用点来自仓库 Python AST，动态注册目标仍需逐项人工确认。这是拆分输入，不是已经验证的完整生产调用图。本次未迁移三个业务模块。

## 范围与复杂度复核

子计划取证阶段净新增代码结构为 0。单独复杂度复核完成，删除清单：无。后续离线实现按以下清单登记；真实数据变更、在线调用和业务拆分继续服从门禁。

### H1 离线执行产物登记

- 新增 `tests/m4_ai_prompt_check.py`，含 `AiPromptTests`；独立测试入口及后续在线验收的离线前置使用。
- 在 `ai_translator.py` 新增 `_get_greeting_prompts()`；问候生成器和迁移逐字校验测试调用。
- 新增 `data/ai_greeting_prompts.json`，只搬移五段现有模板；保留生日日期上下文和全部静态 fallback。
- 修改 `ai_context_builder.py` 和片段文件，只接入约定的三个键；不增加模型路由或凭据配置。
- 新增 10 份 `data/ai_personas/<char_id>.json` 试稿，均为 `reviewed=false`；不加载、不回填、不扩展到 51 人。

本阶段净增 1 个代码模块、1 个类、1 个顶层函数；删除公开产物为 0。试稿内容经你审校后，才登记后续回填工具与扩展产物。

### H1 当前离线结果

`python -B -X utf8 tests/m4_ai_prompt_check.py` 已运行，4 项通过。覆盖三键次序、v1 兼容、昵称控制字符处理、五模板原文 SHA256、五路真实内存邮件、异常静态 fallback、聊天历史不写入及 10 稿身份对应关系。Luna high 从 `HEAD` 的 Python AST 独立提取模板，五段均逐字匹配。

10 人试稿为 90001001～90001010，全部 `reviewed=false`。前 7 人按既定 pilot 名单，其余按名册顺序补齐。身份仅取名册及英雄目录，语气为待审校原创提案。试稿没有运行时加载者，没有写入真实存档。下一步是你审阅这 10 稿；通过后再执行 51 人扩展、回填工具与在线专项。
