# 仓库修复执行台账

2026-11-13 开始执行。起点为 `4bec98f16ba8dc95f4c01d104bcdc5b88d77ed10`，与[总计划](2026-11-12-repair-plan.md)一致。已有未跟踪计划、`_review/` 和 `tests/min_params.json` 保留。

## 当前结果与下一步

2026-11-14 B1 收尾：用户决定 M2 第 2～7、10 项与赠礼后重登按“已完成”归档，不再补三阶段截图；联合特勤 N-2 维持 filed、不修复。本轮实施并验证 B1 剩余两项：B1-C01 Mix SDK 登录 `data.id` 改为字符串；B1-R01 将 332 冻结缓存登记为 `storage.cdn_read_roots` 只读历史根。四项回归专项（16／30／13／7）均 exit 0。B1 本轮收尾，不进入 B2。

| 任务 | 源码／材料 | 自动检查 | 客户端验收 | 下一步与门禁 |
| --- | --- | --- | --- | --- |
| A1 | 已重部署证书与分发文件，安装两处 Windows 根信任 | 文件检查退出 `0`；Windows 链、HTTPS 200、指纹及错误主机名检查通过 | 未运行，不属于本票证书级探针 | done；用户已确认接续 A2 |
| A2 | 六个消费者及相关专项复验完成，本轮未改代码 | 10 个脚本均退出 `0`，156 次执行含继承重复；Linux 41 全过 | 不适用 | done（消费者范围）；保留 1 项历史归档 skip，资源告警单独登记 |
| B0 | 已扩展本机只读分片与 Bili 探测，登记官方 332 资料，PC 已选 332 | 存储 16、探测 5、分发 21、连接版本 13 均退出 0；71,275 对象就绪 | 联网主界面／角色／背包／重登通过，slot3／UID／332 与库一致；断网卡 B 站登录 | partial，仅 B0-S01 后置；本地提交 ce761b7，B1 已恢复，临时环境已清理 |
| B1 | N-1 已修；B1-C01／B1-R01 本轮 fixed；N-2 维持 filed | 本轮回归 16／30／13／7 均 exit 0；旧周期 2 error 保留 | M2 各项按用户决定归档完成；联合特勤不修复 | done（本轮范围）；N-2 维持 filed，不进入 B2 |
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

### B1：礼物实机复验收尾

- 用户回报“验证通过”。实际领取邮件 1023 后连续执行 4 次 14100，每次向档案 1045 赠送 50001×1；最后库存 1、档案经验 20、gift_list 记录 50001×4。不是计划中的只送 1 本；按真实操作记通过，不回滚或套用旧预期。
- 证据目录 `b1-client-20261114/gift-recheck-20261114T111341Z/`：`after-client-acceptance.json`、`02-before-client.db`、`03-after-client.db` 和 `04-after-stop.db`。赠礼前无 50001 持仓行、档案经验 0；之后持仓 1、经验 20，30012 仍为 10，7 个角色交心值未变。前后及停服冷读 quick_check 均为 ok。
- `server.log:210` 为真实领取 30004→30005；30008 是看邮件详情，不是领取。:229／235／238／241 为 4 次赠礼请求，:230／236／239／242 为成功响应，:253 为退出连接。领取中间库存 5 来自邮件附件和领取证据，未保存独立的中间库快照。4 次请求是实机执行次数，不是 4 项独立测试覆盖。
- 用户客户端反馈和实库提交均通过；停服后重新打开文件仍为库存 1、经验 20。本轮日志只有初次登录，没有赠礼后的第二次游戏登录，不把文件冷读当客户端重登。该缺证单列，不要求重做其他正常项目，不据此扩成 M2／B1 全过。
- 清理完成：游戏进程数 0。Ctrl+C 未停止本进程，精确 Stop-Process PID18388 exit 0；exec35371 最终 exit 1，不算优雅退出通过。hosts Restore exit 0，与原始 65,492 字节相同；35 TCP＋UDP6105 可独占绑定。源仓库 9 个保护文件、运行副本 8 个证书／私钥和客户端主清单均未变。独立 DNS 当前为 198.18.0.4／198.18.0.5，原样保存，未把它写成历史 203.107.63.115。见该轮 `cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`。
- 根 Codex 与 `gpt-6-luna/high` 完成实际快照／请求／响应的功能复核和单独复杂度复核。准备错误已纠正；重登独立证据 filed；删除清单：无。本轮生产修改和新测试为 0，未重跑已通过套件。当前只保留 4 份文档未提交改动，未推送；N-2、完整多维和其他逐项缺证继续保留。

### B1：一阶礼物复验准备（历史阶段）

- 用户要求继续，额度读回为 5 小时剩余 100%、周剩余 49%，未使用重置。分支 main／HEAD 9be30c2 不变，已有 4 份文档改动保留。只接续礼物，不重做其余正常项目。
- 新证据目录为 `b1-client-20261114/gift-recheck-20261114T111341Z/`。复用原隔离运行副本，使用现有 `AccountDB.backup_save_file` 保存 `00-before-preparation.db`、`01-prepared.db`、`02-before-client.db`；准备后 quick_check=ok。没有新增生产模块、类、顶层函数、参数、配置键或测试。
- 332 原生 `HeroFileGiftPage` 已定向提取，LJD exit 0，来源／命令／哈希在该轮 `native332/manifest.json`。其 :248、:284-297 表明交心等级 0 时仍列出有库存的一阶 subtype 1 礼物，:144 走 `HeroAction.SendGift`。332 `GameSetting.gift_value` 为 [10,5]，与现有一阶服务偏好／普通礼物经验一致；二阶配置中的 20 不是本次 14100 经验规则。
- 使用现有 `send_gm_mail` 给本票 UID 261113200139 补投邮件 1023「B1-09 一阶礼物复验」，附件 50001×5，当前未领。users／currency／material／hero／hero_archive／equip／task／polyhedron_run 八表未因投信变化；原 30012×10、交心等级及档案经验不变。角色 1045「赤音／亚莉莎」已拥有，档案经验 0，50001 对该档案为普通礼物，单件预期经验 +5。
- 准备时服务和临时 hosts 活动，现已结束。PID 18388／exec 35371。显式绑定本票数据库、配置和聊天目录，CLI `--gw-port 18102`；当时默认 TLS、状态／区服接口均通过，回读 332／UID261113200139／slot3端口18104／CDN off／capture false。35 TCP 监听及 UDP6105 同属该 PID。证书检查 exit 0，运行副本 8 个证书／私钥与源 9 保护文件不变，10 域名 Apply exit 0。清理结果见上方收尾节。
- 根 Codex 与 `gpt-6-luna/high` 完成功能及单独复杂度复核：修正礼物阶段准备错误；客户端显示、单件消耗和重登保持仍待验，未报通过。删除清单：无。实际启动参数与检查命令保存在该轮 `commands.json`，最新活动状态见 `b1-client-20261114/running-service.json`。
- 用户只需领取 1023、给 1045 送 1 本、重登核对 4 本和经验 5，然后退出游戏统一回报。代理之后回读实际请求／库快照，再停服和 Restore；游戏由用户操作。

### B1：礼物空列表反馈与额度停止

- 用户整批回报：“礼物不对，打开礼物盒子背包什么都没有，送礼界面也什么都没有。其余的功能都正常。”完整快照为 `resume-20261114T070645Z/03-after-user-batch.db`，quick_check=ok；报告为同目录 `user-batch-report.json`。邮件 1022 的 attach_flag=2，30012 从 5→10，未见赠礼消耗；一阶礼物库存为空，7 个角色 trust_level 均为 0。
- 已确认验收准备错误：30012 是 type 10／sub_type 2 的二阶交心礼物，不能作为本档当前一阶好感赠礼的准备资产。332 原生 ItemCfg 的 30012 在 `gift-diagnosis/lua/game/config/itemcfg.lua:10289`，50001「崭新的记事本」在 :25865，后者为 type 10／sub_type 1。两个原生文件由已验证的 332 包提取，LJD 均 exit 0，来源／哈希见 `gift-diagnosis/native-source.json`。
- 根 Codex 与 `gpt-6-luna/high` 已复核已有 `ArchiveService.give_gifts`：一阶 14100 与二阶 73012 是不同入口。50001 属于一阶允许集，当前已拥有角色／档案 1045、档案 exp=0，可作为最小复验对象。不能把 trust_level 全 0 解释为一阶也不可送。未确认生产 handler 缺陷；背包过滤和实际消耗仍待客户端复验。
- 正确修正尚未实施：额度恢复后先保存快照，再用现有 GM 邮件给本隔离档发 50001×5，让用户领取并送 1 份，核对库存、好感和重登。保留 30012×10，不强改交心等级，不重做其余正常项目。本次没有新测试或生产修改。复杂度删除清单：无；复用既有邮件及一阶赠礼服务。
- 额度读回为 5 小时剩余 9%、周剩余 49%，触发用户不超过 10% 停止规则，未重置。该回读后只清理和保存交接，没有补发新礼物或运行新测试。
- 清理完成：用户游戏进程数回读为 0。Ctrl+C 未结束本 PID，随后精确停止本票 PID 38872；exec 54815 最终 exit 1，不算优雅退出通过。hosts Restore exit 0，65,492 字节与原件相同；本轮 35 TCP＋UDP 6105 均可独占绑定，源仓库 9 个保护文件和安装主清单未变。两关键域独立解析均为 203.107.63.115。最新证据为该轮 `cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`；`running-service.json` 已标 active=false。
- “其余正常”保留为客户端汇总，不等于逐项三阶段数值全过。多维快照仍为 state 2／3035401／battle_count 1，本轮没有新的完整局结算证据，M2 不写成全过。

### B1：同票恢复剩余客户端验收（历史阶段）

- 用户追问为何停住后，纠正执行边界：原授权覆盖 B1 剩余工作，N-2 缺证只阻塞自身修复；不把取证子项结束解释为需重新确认 B1。当前继续独立的第 2～11 项客户端验收，仍不进入 B2 或 B0-S01。
- 已复用原隔离运行副本，未复制新环境。新证据目录为 `selftest_tmp/priority-repair/b1-client-20261114/resume-20261114T070645Z/`。已有 `00-before-preparation.db`、`01-prepared.db` 和 `02-before-client.db`；由现有 `AccountDB.backup_save_file` 生成，quick_check 均为 ok，旧快照和备份保留。生产模块、类、顶层函数、参数、配置键及测试净增均为 0。
- 原网关池预检 exit 1：8110、8111 被外部进程占用，不能监听。只用现有 CLI `--gw-port 18102` 临时避开，未停止外部进程；新监听计划 35 TCP＋UDP 6105，`linux_manager.probe_endpoints` exit 0。复核发现旧 `launch_config.json` 不由 main 加载，已删除该无效配置改动并逐字节恢复，实际生效依据为 CLI、HTTPS 回读及监听 PID。
- 现有 `AccountDB.send_gm_mail` 只向本票合成档补投邮件 1022「B1-08 补证」，附件为票 38×5、币 2×1000、礼物 30012×5。邮件未领，旧 1020 保持已领；users／currency／material／hero／equip／task／polyhedron_run 均未因准备操作变化。原有礼物仍为 5，多维起点 3035401、HP 9250/10000、battle_count 1。
- 启动前证书检查 exit 1：隔离叶证书缺当前探测 IP 2.0.0.1，根仍可用。先备份隔离环境 8 个证书／私钥文件，再由普通启动现有机制更新隔离叶证书。原根证书及根私钥哈希不变，旧叶私钥备份在；源仓库 9 个保护文件不变。没有重装或改变 Windows 信任。启动后 `python -B -X utf8 gen_cert.py --check --json` exit 0，ready=true。
- 当时服务和临时 hosts 活动，现已结束。PID 38872／exec 54815。显式绑定本票数据库、配置和聊天目录；HTTPS 状态及区服查询均 HTTP 200，默认 TLS 校验通过。回读 UID261113200139／B1隔离验收／332／CDN off／capture false，slot3端口18104，35 TCP＋UDP6105 同属该 PID。10 域名 Apply exit 0、全部为 127.0.0.1；原 hosts 已备份。该会话后续清理记录保留，不能作为当前活动状态。
- 根 Codex 与 `gpt-6-luna/high` 已复核端口映射、账号和证书权限边界。生产 `battle_server.py` 与源码一致；运行副本内两个旧测试文件未同步，不由服务调用，也未拿它们冒充本轮测试结果。复杂度删除清单：无效的旧 launch_config 改值已还原；剩余可删项：无。
- 下一步由用户手工按整批清单操作并统一回报；不是等待新票许可。代理随后回读日志／快照、停止本 PID、恢复 hosts 并核对保护文件和本轮端口。客户端结果尚未取得，B1 仍为 partial。
- 最近额度回读：5 小时剩余 19%、周剩余 51%，未重置。用户回报后先重新读取；任一不超过 10% 时只清理和保存交接。

### B1：11 月 14 日 N-2 取证接续（历史阶段）

- 起点核对完成：`git status --short` 为空，分支 `main`，HEAD 为 `9be30c2a335c85b390762cdedc1f554c53010468`。完整读取交接及其指定资料。接手额度为 5 小时剩余 52%、周剩余 56%，未重置。本轮只执行 N-2 取证，没有实施修复或启动客户端验收。
- 产物完成：更新本台账、客户端验收和交接 3 份现有文档；证据包位于 `selftest_tmp/priority-repair/b1-n2-evidence-20261114/`。包内保存 9 份字节码、9 份反编译 Lua、9 份工具日志和 `evidence.json`。新增／删除生产模块、类、顶层函数、参数、配置键及测试均为 0；没有新工具文件。
- 来源核对完成：复用本机解包项目的 `text_pipeline_lib.resources`、UnityPy 和 LJD。源目录为 `C:\Users\<user>\Desktop\解包\文案数据\12_JSON库\增量_307332_20261113\raw`。索引与仓库冻结 332 主清单逐字节相同；索引 SHA256 为 `5ca62a34276532fc0712cd83ca07a010693f94f4ac624e721287b3c3b6516089`。`scripts64.ys` 与当前安装源逐字节相同，大小 36,371,876 字节，MD5 为 `2bdff33d321b45c2aff3c174d5ef8dfd`，SHA256 为 `2f3dd7d1628a2eaae88541be951942b9417e3858252ad87fb3df355634652f09`。提取文件可归属 app 307／build 332／v5.3.6。
- 消费与编码核对完成：332 的 `EnchantmentStageView.lua:302` 固定读取 3 组。`StageGroupCfg` 提供 ID 1～30 的 30 个 type 8 候选组，每组有 3 个难度关卡；这不是新档选组规则。332 的 `protocol/p42_pb.lua:21` 与仓库 schema 的 4 个消息、6 个字段逐项相符。描述符默认值不等于业务初值。`GameSetting` 只证明客户端阈值、费用和解锁等级。
- 实际命令：3 次 `python -B -X utf8 -` 分别提取 7 个入口／配置文件、直接依赖 `gamesetting` 和 `p42_pb`，均 exit 0。包内 `files[].command` 保存 9 次 LJD 的完整实际参数；9 次均 exit 0。字段／候选组回读命令 `python -B -X utf8 -` exit 0，输出为 9 个文件、0 个反编译失败、4 个消息／6 个字段相符、30 个候选组。上述是静态取证数，不是测试覆盖数或客户端通过数；未重跑已通过专项。
- 缺证已登记：仍缺新档三组的选择、顺序、去重及权重规则，以及刷新计数初值和周期迁移规则。当前实机 Lua 栈与有效 332 新档成功初始化会话也未取得。公开检索未取得可用方案；GitHub 代码搜索页面未能读取，检索不完整。没有猜组、复制其他 owner 计数或扩刷新玩法，N-2 保持 filed，B1 保持 partial。
- 本机证据核对完成：13 个指定证据文件／目录均在，包括隔离库、抽卡三阶段快照、N-1 原始战报、前后快照、原始日志、hosts 备份及 B0 缓存。指定周期 before 归档仍缺失，旧 2 error／exit 1 保留。本轮没有再次验游戏；整局多维、任务／成就和其余逐项数值仍缺证。
- 复核完成：根 Codex 与 `gpt-6-luna/high` 分别完成证据、实际文档差异及单独复杂度复核。9/9 字节码与 Lua 哈希相符，9 份 LJD 日志未见错误／断言／告警标记。fixed：历史活动状态和邮件准备表述；filed：N-2 业务契约、端口绑定失败及 `skeleton.json:3694` 的过时注释。332 客户端确实发送 42002；服务端 CORE_HANDLERS／OPERATIONS 未见 42002／42004 专用业务处理器，42004 仅配置空 42005 模板。同类“无 Lua 调用点”注释检索到 68 个静态候选，逐处位置保存在证据包；仅 42002 在本轮证实过时，其余 67 处未验证，不算当前缺陷。未修改 skeleton。删除清单：过时的当前活动措辞；剩余可删项：无。没有 rejected 项。
- 环境回读有保留失败：保护 9 文件及当前安装主清单哈希不变，hosts 与原始 65,492 字节相同；33/35 个 TCP 端口和 UDP 6105 可独占绑定。8110、8111 返回 WinError 10013，整条环境检查 exit 1。`netstat` 随后显示这两端口分别有 Codex／verge-mihomo 出站连接，未显示监听；尚未证明绑定失败的完整原因。未停止这些外部进程。CIM 查询因拒绝访问 exit 1；改用 `Get-Process` exit 0，未见游戏、LocalServer 或 Python 进程。下次起服前重检端口，不能沿用上轮 35/35。
- 收尾核对完成：`git diff --check` exit 0；`git check-ignore -v selftest_tmp/priority-repair/b1-n2-evidence-20261114/evidence.json` exit 0，证据包仍受既有忽略规则保护。工作区仅上述 3 份文档改动，未提交、未推送。最近额度回读为 5 小时剩余 38%、周剩余 54%，未重置。
- 下一确认点：本轮取证结束，等待确认下一张 B1 票。若继续 N-2，先补可信的新档成功初始化样本或服务端规则；若验完整多维及剩余数值，先准备隔离环境并给出整批清单。不进入 B2，不重开 B0-S01。

### B1：11 月 14 日 N-2 补证复核（本轮）

- 本轮目标为“继续梳理 N-2 取证材料”。只读，不改代码、不启服、不改 hosts。起点仍为 `main@9be30c2`。
- 复核 A（客户端字节码常量扫描）：对 332 `scripts64.ys` 全部 TextAsset 做内存级扫描，排除 `game/config`、`game/laterconfig`、`game/qworld/generated`，匹配 `BattleEnchantAction`、`EnchantmentInit`、`BattleEnchantmentData`、`EnchantmentStageView`、`ChapterEquipEnchantmentItemView`、`ENCHANTMENT_INIT`、`ENCHANTMENT_REFRESH`、`DAILY_EQUIP_ENCHANT`、`STAGE_TYPE_ENCHANTMENT`、`42001`～`42005`。结果：`protocol/p42_pb.lua` 仅含 42001／42002／42004／42005 字符串常量；`game/includemod.lua` 的 LazyLoad 名表含上述类名，且作为拼装字符串出现 42001～42005（非协议使用）；`game/action/battleenchantaction.lua` 含全部 5 个 cmd 与两个事件；`game/const/chapterconst.lua` 与 `game/const/redpointconst.lua` 仅含 `DAILY_EQUIP_ENCHANT`；`manager/redpointmgr.lua` 命中但无联合特勤业务逻辑；`game/views/sectioninfo/enchantmentstage/enchantmentsectioninfoview.lua`、`game/tools/battleinstance.lua`、`game/battle/templat/battleenchantmentstagetemplate.lua`、`game/battle/battlestagetools.lua`、`game/bridge/battlesettlementstrategy/battleresultgotohandler.lua`、`game/views/battleresult/multiple/*` 仅含 `STAGE_TYPE_ENCHANTMENT`；`game/data/datainclude.lua:293` 注入 `BattleEnchantmentData`；`game/routesconfig.lua` 与 `game/tools/operationrecorder.lua` 含 `EnchantmentStageView`；story 脚本中的 42001～42005 为剧情字符串，不是协议调用。结论：**42002（客户端主动 Push）与 42004（SendWithLoadingNew）只在 `BattleEnchantAction.lua` 中发出，服务端没有任何 Python handler。**
- 复核 B（配置与关卡元数据）：`StageGroupCfg` 的 type 8 共 30 组：level 1 共 15 组（ID 1,2,3,4,5,6,7,16,18,19,23,24,27,28,29），level 2 共 10 组（ID 9,11,14,17,20,21,22,25,26,30），level 3 共 5 组（ID 8,10,12,13,15）。`stage_meta.json` 的 203 前缀 ENCHANT 关卡 90 个全部存在、max_star 均为 3；`daily_stage_drop_cfg.json` 90 个键与 90 关一一对应，掉落库仅 210001／210002／210003 三档。**这意味着 30 组×3 档＝90 关的静态闭合没有问题；问题仅在“新档初始选中哪 3 组（以及顺序）”。**
- 复核 C（真实 42001 帧）：Alpha-Persei-Captures 的 9/26 登录、9/26 批量、9/27 补抓三次独立会话，42001 帧均为 `08021000180b18081805`，解码 `{free=2, buy=0, list=[11,8,5]}`；9/26 登录中的另一帧为 `08021000180b18081805`（同上），9/27 补抓为 `08021000180b18081805`，但早前捕获记录显示 `[11,6,5]`（同账号刷新后）。**这证实：服务端 42001 的 `enchantment_battle_list` 是持久化状态，同一账号跨会话保持不变、刷新后改变。不是每次登录重新随机。**
- 复核 D（刷新与跨日链路）：`GameTimer.GetNextDayFreshTime` 由 `PlayerAction.SyncSeverTime` 设置；`RequestNewDayData` 发 `cs_10500`→`sc_10501` 后 `Invoke(NEW_DAY)`。`GameSetting.fm_*` 五键含义已确认：`fm_free_refresh_limit_count=2`、`fm_item_refresh_limit_count=10`、`fm_get_refresh_count=2`、`fm_item_refresh_cost` 为 10～100 的 10 档阶梯、`fm_stage_unlock=[40,45,50]`。`TipsCfg[60227]` 原文明确「每日刷新次数重置」「免费刷新次数用完后消耗移转之辉」。**刷新是客户端主动行为；跨日只重置计数，不重新抽组。**
- 复核 E（服务端现状）：`v5_server` 全部 Python 文件中，除 `minigame_service.py:80` 的 `VEHICLE_BALL_LIMITED_TASK_ACTIVITY_ID = 4200401` 和两条测试／导出脚本外，无 42001～42005 业务代码。`skeleton.json:3694` 仍写「无 LUA 调用点且历次抓包/日志未观测」，已被本轮证伪（332 客户端确实 `Push(42002, {})`）。`CORE_HANDLERS` 无 42002／42004，`42004` 在 `skeleton.json` 仅配置 `sc_42005` 空模板。
- 结论：**N-2 仍 filed，未修复。缺口从“五个问题”收敛为“一个未发布的市场数据”**——新档初始三组的抽样来源（是随机、按玩家等级/章节进度、还是服务端配置表？）。已排除：随机每次重抽（同账号跨会话固定）、客户端决定（42001 是服务端下发）、配置表驱动（StageGroupCfg 只有 30 组，无初始标记）。仍缺可信 332 新档成功初始化样本或权威服务端规则。
- 本轮产物：仅 2 份文档补证（交接 `docs/plans/2026-11-13-repair-handoff.md` 与本节）；新增／删除生产模块、类、顶层函数、参数、配置键、测试均为 0。未改 `skeleton.json`，未改客户端代码。没有新证据文件（本轮全部为只读扫描，无字节码导出）。
- 复核：本轮只读；`git status --short` 仍有 4 份文档改动（含本轮 2 处编辑），未提交、未推送。下一确认点：如需继续，需用户提供可用的真实 332 新档成功初始化样本（进入联合特勤界面时的 42001 响应），或接受“维持 filed、不修复”的当前边界。

### B1：本轮收尾——B1-C01 与 B1-R01 修复

- 用户决定：N-2 维持 filed、不修复；M2 第 2～7、10 项与赠礼后重登按“已完成”归档，不再补三阶段截图；本轮只做 B1-C01 与 B1-R01 两项。
- **B1-C01 根因确认：** `v5_server/server_net.py:1758` 把存档主人 UID 作为 JSON 裸数字下发。实测 `2174928301 > 2^31-1 = 2147483647`，即既有默认主人本身就超 Int32；12 位 UID 超得更多。对照 `save_slot_manager.py:880-882` 的区服列表 `uid`／`mixId` 本就用 `str()`，登录接口是唯一不一致点。改前探针确认 `{"data":{"id":2174928301}}` 为 `int` 且超 Int32。
- **B1-C01 修复：** `server_net.py:1758` 改为 `"id": str(_gen.DEFAULT_UID)`，并补两行注释说明原因与对照。改后探针：`42`／`2174928301`／`261113200139` 三者均序列化为字符串且回读无损。
- **B1-R01 根因确认：** 332 冻结缓存 `selftest_tmp/priority-repair/b0-local-client/asset-cache`（实测 1846 个 `.ys`、6,266,198,823 字节）不在 `cdn_proxy.cache_roots('pc')` 返回的 3 个根中。用真实文件名 `0017fcd338ae9791400e0726ca569b04.ys`（4,481,227 字节，文件确实存在）验证 `find_cached_file` 返回 `None`，即必然 MISS。
- **B1-R01 修复：** 在 `v5_server/server_config.json` 的既有配置项 `storage.cdn_read_roots` 中登记 `../selftest_tmp/priority-repair/b0-local-client/asset-cache`。第一次写 `selftest_tmp/...` 被解析到 `v5_server/selftest_tmp/...`（`normalize` 以 `SERVER` 为基准），已改为 `..` 相对路径并回读确认解析到仓库根的 `asset-cache`。未改 `cdn_cache_dir`、未复制缓存、未改代码。
- **B1-R01 验证：** `cache_roots('pc')` 现为 4 项；前 5 个文件 5/5 HIT；随机 200 个样本 200/200 HIT；`integrity.valid_file` 对命中文件返回 True（MD5 校验通过）。
- **回归：** `verify_resource_storage.py` 16 项 exit 0；`test_cdn_foundation.py` 30 项 exit 0；`verify_client_version.py` 13 项 exit 0；`verify_gateway_handoff.py` 7 项 exit 0。未重跑本轮无关套件。
- **M2 归档：** 隔离库回读确认 1020／1022／1023 均 `attach_flag=2`；`material 50001 num=1`；`material 30012 num=10`；`hero_archive` 唯一行 `archive_id=1045, exp=20, gift_list=[{"id":50001,"num":4}]`；`polyhedron_run` 为 `state=2, tier_id=1002`，`run_data.latest.stage=3035401`、`stats.battle_count=1`、`hp_report_complete=true`、`hero_list[0].health=9250/10000`。另注意 `chapter` 表中 203 系列为 0 行——联合特勤关卡进度从未产生，与 N-2 的“界面拿不到组”是两个独立事实。
- **产物：** 改 1 个生产文件（`server_net.py`，一行表达式 + 两行注释）、1 个既有配置文件（`server_config.json` 加一条数组元素）；更新 3 份现有文档。新增／删除模块、类、顶层函数、参数、配置键、测试均为 0。未改 `skeleton.json`、未改客户端、未启动服务、未改 hosts。
- **复核：** 改动为单点表达式替换，同类扫查 `v5_server` 中其它 `"id": _gen.DEFAULT_UID` 形式未再命中；配置项为既有键、按既有 `read_roots` 只读语义生效。复杂度删除清单：无（未新增抽象）；`b1-r01-probe/` 为临时探针目录，可删。

### B0：计划登记（历史）

- 用户要求“计划中新加一个 B0，让这个离线服务器适配本地最新版本”。本次只编辑 6 份现有状态文档，新增／删除代码模块、类、顶层函数均为 `0`，净增 `0`，没有新路由、参数或配置键，也没有启动服务、测试、下载或修改系统。
- 目标是本机当前安装的 PC B 服版本，已有资源快照 app `307`／build `332`、`v5.3.6`；SDK gateway `308` 和渠道 `10` 分别核对，不混作资源版本。实施前复查并冻结实际目标，不要求换旧 321 客户端。
- 复用现有版本、原生资料、资源校验、SDK、连接绑定和专项。B1-R01 的版本／资源适配由 B0 接续；B1-C01 核对处置后保留来源。完整可信资料、匹配对象及渠道响应契约是已知待核项，不把 82 个已请求 321 文件当作 332 全部缺口。
- 完成条件见总计划 B0：可信主／语音清单和资源集通过校验、目标版本选择正确、无运行时上游回源时实际进入隔离主界面并重登、角色／背包与库回读一致、失败路径及恢复有证据。只验证启动子集仍为 partial；M2 的 12 项留在 B1。
- 当前状态为 planned，等待确认实施 B0。既有 B1 自动结果和历史不重置；B0 完成后停止，再确认恢复 B1，不自动开始 B2。
- 计划功能复核：根 Codex 与 `gpt-6-luna/high` 分别核对范围、依赖和实际版本轴。fixed：明确单次登录下行帧与自动分配隔离 UID 的客户端门槛。建议“准备阶段一律禁止联网”rejected：用户要求运行时离线，未禁止资料准备；已区分两阶段，资料获取仍按实际授权与环境权限执行，本次没有获取。另行复杂度复核删除清单：无；已替换过时的 A2／B1 接续顺序，没有新增生产抽象。纯文档验证使用 `git diff --check`，不运行无关代码测试。

### B0：11 月 14 日接续

- 用户确认昵称 `B0版本适配`、UID `261113211627`、主界面、角色列表、背包和退出重登全部正常。实际日志有两次 slot 3 登录及两次版本 `332` 的登录推送完成，均为 `207/218` 帧、动态 `207`；11 帧进度合并为一次全量，再按既有版本策略略过 `89013`。207 是实际发送数，218 是合并／过滤前候选数，不相加为独立覆盖。库内唯一用户、等级 `70` 与身份回读一致，quick_check=`ok`；此处没有替代 B1 的资产数值验收。
- `B0-S01`，confirmed／filed／用户后置：用户完全退出游戏后断开 Wi-Fi／网线，冷启动弹出 B 站登录窗口，因无网无法登录，未进入游戏。当前 Mix SDK 本地接口不等于原生 PCGameSDK 离线认证，仓库没有现成实现；未伪造响应、扩展 10 域名预览、改真实账号或客户端安装文件。断网失败独立保留，联网成功不能覆盖它。
- 服务 PID `9484` 已不存在，exec `66583` 经 Ctrl+C 退出 `1`，不冒充优雅退出通过。`hosts-transaction.ps1 -Action Apply`／`Restore` 均退出 `0`；恢复后 hosts 与原件逐字节一致，长度 `65492`、SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54`。即时解析回执保留，独立 DNS 两关键域随后均为 `203.107.63.115`。35 个 TCP 端口及 UDP `6105` 可独占绑定，9 个保护文件及客户端主清单哈希未变。
- 根 Codex 与 `gpt-6-luna/high` 已分别完成功能、共享路径／权限边界及单独复杂度复核，删除清单：无。B1-C01 小 UID 生产兼容仍 filed；B0-P01 为未验证性能观察；渠道请求 10／响应 9 已有本轮正常运行证据，但没有据此猜改字段。只读 SDK 导出字符串线索不证明离线入口可用，未调用。
- 证据目录 `selftest_tmp/priority-repair/b0-local-client/`：`client-online-acceptance-20261114.json`、`client-offline-blocker-20261114.json`、`cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`、`review-resume-20261114.json`。新备份 `hosts.before-resume-20261114-073937.bin` 与原件一致，旧运行和回滚回执另存 before-resume 副本。原始 SDK 日志含凭据，仅留忽略目录，不原样输出。最后额度回读为 5 小时剩余 `86%`、周 `68%`，未重置。

### B0：11 月 13 日实施记录（历史）

- 客户端最新反馈：已到登录页，弹窗正文是创建新存档提示。实际日志和区服 API 证明 slot 1 是新建、slot 2 是删除入口，slot 3 为 `【当前】account`，注册表 `3 → account.db`；库内唯一用户仍为 `261113211627 / B0版本适配 / 70`。用户曾创建并删除一个临时新档，目标档保留。已提示点确定后刷新区服并选择 `【当前】account`，等待真正入场结果；不能把存档菜单的通知窗口判为官方账号处罚，也不能把登录页当作主界面通过。

- 起点仍为 `main@93bbcc2`，保留此前 7 个未提交改动。用户明确“开始 B0”；根串行修改，Luna 负责只读取证与复核。没有新增生产模块、类、顶层函数、参数或配置键；新增 2 个现有类测试方法和 4 个官方清单数据文件。
- 修改：`cdn_proxy.py:330` 在现有缓存全部未命中后，按已选原生 BASE 版本和主清单 MD5 核对探测结果，再读取 Windows／Voice 分片，路径逃逸拒绝，继续使用原 MD5 校验。`res_version_manager.py:239` 增加 Bili 路径并回读实际命中 Windows 根。`native_manifest_sources.json`、`dynamic_versions.json`、`resource_distribution.json` 登记并选择 `native-pc-6a610d4d8550`；Android／iOS 选择未变，原文件有备份。
- 官方来源：冻结 307/332、v5.3.6。普通沙箱出站最初报 WinError 10013；按 B0 授权通过提权工具完成官方 HEAD／GET，未改变系统网络。4 个官方文件共 7,715,245 字节；主清单与本机逐字节一致，渠道 10 的现有 probe 返回同一身份。先在临时准备目录解析、校验，再按既有原生登记流程封存，没有以本机 hint 冒充来源。
- 资源：主清单 65,538 项，ja 835、zh 4,922，去重合并 71,275 个对象、63,325,313,135 字节。本机 69,429 个对象逐项大小／MD5 验证通过，117.4 秒；1,846 个缺失对象在临时缓存补齐 6,163,821,436 字节，497.2 秒、失败 0。合并缺失／坏对象均为 0；这是准备窗口内校验，非原子文件系统快照。未写游戏安装目录。
- 验证命令均为 `python -B -X utf8 v5_server/tools/<脚本>`：`verify_resource_storage.py` 16 项／exit 0，`verify_resource_probe.py` 5 项／exit 0，`verify_resource_distribution.py` 21 项／exit 0，`verify_client_version.py` 13 项／exit 0。各脚本日志分开保留，不把重跑次数相加为独立覆盖。
- 先红后绿：新分片用例原因 Bili 根探测失败；Windows symlink fixture 无特权，改用 fixture 内 junction，原逃逸断言保留、未加 skip。分发原 fixture 固定 PC 底包 307 却断言随请求 308，按现有 UI 契约先补 fixed 模式断言，再明确选择 auto；原断言不删，生产底包选择逻辑未改。
- 实际资源回读：`offline-http-readback.json` 为真实 Flask SDK build 332、安装源与临时缓存各一对象 HTTP 200，运行时 upstream／download mock 禁止且调用 0。9 个保护文件及客户端主清单哈希未变。此结果不代替游戏客户端。
- 人工环境已收尾：PID `37896` 不存在，原 exec `84105` 经 Ctrl+C 退出 `1`；首次 Stop-Process 异常保留记录，不冒充优雅退出。`hosts-transaction.ps1 -Action Restore` exit 0，原字节／65492 字节／原 SHA256 一致；独立 DNS 两关键域均为 `203.107.63.115`。TCP 35 端口及 UDP 6105 已释放，9 个保护文件及客户端主清单未变。见本轮 `cleanup-readback.json`、`hosts-restore-receipt.json`、`dns-after-restore.json`。副本和缓存保留，昵称 `B0版本适配`、UID `261113211627`。
- 停止原因：5 小时额度剩余 9%、周 71%，按用户不超过 10% 的规则只做清理和交接，未自动重置。额度恢复后只接续 B0，恢复隔离环境后选第 3 项 `【当前】account`，再验证主界面、角色／背包、重登和离线依赖；不能把存档菜单通知或登录页记作通过。
- 复核：根 Codex 与 `gpt-6-luna/high` 已检查实际代码、官方来源、完整性和共享路径边界。fixed：只读路径与 fixture 缺陷；B1-C01 小 UID 和渠道 10/9 差异仍 filed。未验证性能观察 B0-P01：PC 缓存 miss 会重读选择目录，真实客户端影响待观察，不提前增加缓存框架。单独复杂度复核删除清单：无；ja 来源在本票双语音范围内保留。
- 证据目录 `selftest_tmp/priority-repair/b0-local-client/`，包括 target、official-*、installed-audit、asset-download-results、offline-http-readback、protection-current、running-service 和各专项日志。原始 SDK 日志只在忽略目录保留，禁止输出渠道凭据及签名。B0 尚未完成，不恢复 B1。

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

### B1：11 月 14 日 N-1 修复与验收（历史）

- 最新修复：2026-11-14 B1：N-1 多维首战后推进失败已完成源码修复、自动检查及客户端复验；实际场景由 3035111 推进到 3035401，本轮完整通关与任务／成就仍缺证。N-2 联合特勤缺 332 权威初始化契约，已登记、未修复。第 1 项数值／重登已有证据，其余按用户汇总正常与逐项缺证记录，M2 未全过。临时服务已停、hosts 已恢复。B0 本地提交 ce761b7 未推送，B0-S01 后置；不进入 B2。
- 本轮服务及 hosts 已清理：游戏进程数 0，PID 24768 已不存在，exec 35738 经 Ctrl+C 退出 1；Restore 退出 0，hosts 原始 65492 字节／SHA256 相同。35 TCP＋UDP 6105 可独占绑定，9 个保护文件及客户端主清单未变；两关键域独立 DNS 查询为 203.107.63.115。当时回执位于 `b1-client-20261114/cleanup-readback.json`；最新环境另见 N-2 取证接续。
- N-1真实证据：74B battle-info SHA256 `8643f2f5ef1a72f65fbef67241d17fdfa24c4d2b95ccb1a0a3bcd098765df0b2`，field10含英雄1084（HP8502／max10000）和2个精确空消息；服务端latest.heroes也仅1084。旧parser把空槽当非法角色使characters=None。当前仅跳过空队伍槽；有槽但全空、非空坏HP／重复字段／错wire仍拒绝，总槽数最多32；无field10保留旧兼容，下游队伍名单校验不动。
- 新增1个现有类内集成方法，用真实battle-info加合成外层走现有parser→Core54032→保存8502／10000→领奖18012→选下一场景18014。改前2项定向检查exit1（新例结算码1≠0，1项失败）；修后3项定向exit0。全套多维35／Hodur20各exit0，另战棋HP既有1项exit0；定向和继承有重叠，不相加为独立覆盖。旧skeleton ResourceWarning仍归A2-W01。
- 根Codex与gpt-6-luna/high独立复核通过，扫查共用解析器仅1处，Polyhedron／Hodur／Warchess消费者名单校验保留，无其他重复解析器需同步。新增生产模块／类／顶层函数／参数／配置键均0；临时原始报文诊断块已删除，单独复杂度复核剩余删除清单：无。
- N-1 客户端复验：用户回报“正常了”；`server-fixed.log:219`、`:225`、`:230` 分别记录本场 54032、18012、18014。前／后库场景 3035111→3035401、battle_count 0→1、hp_report_complete false→true，英雄 1084 当前 HP 为 9250／10000，两份 quick_check 均 ok；本场血量不等于原始夹具的 8502。证据 `n1-client-fixed-acceptance.json` 与 `snapshots/11-before-fixed-client.db`、`snapshots/n1-after-fixed-client.db`。原推进故障已 fixed，整局通关／任务／成就仍缺证；B1 partial，本轮代码及文档随本地快照保存，未进入 B2。

以下为本轮此前取证与准备记录（历史状态）：

- 最新：2026-11-14 B1 整批反馈：用户报告联合特勤黑屏、多维首战后不能进入下一关，其余正常。第1项数值与重登已有三阶段库证据；其余仅有用户汇总，不能替代各项数值／截图。两次多维结算因 characters=None 被拒绝；新档42001空列表与联合特勤入口契约冲突。两项登记N-1／N-2，B1仍in progress，不进入B2。
- 历史诊断会话：当时诊断服务和临时 hosts 活动，结束后须恢复。PID `11224`、exec `60503`，目录 `selftest_tmp/priority-repair/b1-client-20261114/`，日志 `server-diagnostic.log`，昵称B1隔离验收／UID `261113200139`／版本332。旧PID8068已停止并Restore exit0，原字节、35 TCP+UDP6105、保护9及客户端清单均已回读；旧回执另存before-diagnostic后缀。当时已重新备份并Apply同10域；此会话现已结束。
- N-1：12:19:50及12:21:08的54032均报多维角色血量报告无效，战斗摘要characters=None；客户端随后重试／重置，不能把画面胜利当推进成功。原始332报文尚缺，只在现有battle_server.py的132分支、134/135 ACK之后记录异常原因及最多4096字节field4报告。HPguard不变；新增模块／类／顶层函数／参数／配置键0；两个既有UDP解析边界用例exit0。诊断不等于修复，现只等待一次多维复现。
- N-2：新档login.py的schema默认路径下发空SC42001，登录日志三次可证；本地BattleEnchantAction绑定42001，EnchantmentStageView固定读取3个组。43001是另一装备状态帧，25009是关卡进度，不能替代42001。42002无真实handler，42004仅空42005模板；旧Lua/master样本没有332版本与初始分组规则，不能复制其他owner计数或猜组。已filed待332初始化契约，不扩多人解封或完整刷新玩法。

以下为本轮前期准备记录（历史运行状态）：

- 操作方式改为用户整批自查，后续不逐项提问。`case-01-result.json` 记录第1项三阶段数据；`batch-readiness.json` 和 `snapshots/02-12-before-batch.db` 记录余项准备状态。第8项邮件1020已发未领（票38×5、币2×1000、普通礼物30012×5），不算客户端领取通过。
- 2026-11-14 用户已授权“本地提交 B0，继续 B1”。B0 已保存为本地提交 `ce761b770b2620ffd4b53187c2f234504fcf8ada`，17 个文件，未推送；仅 B 站离线认证 `B0-S01` 按用户指示后置，B0 保留 partial。当前只接续 B1：既有自动结果沿用，M2 第 1 项的扣费、产出和重登已由用户与三阶段库快照核对，截图尚未回传。其余项按用户最新要求改为整批清单自查，等待统一回报，不逐项问答；目前不算已执行。
- 历史准备会话：当时 B1 服务和临时 hosts 活动，结束后须恢复。PID `8068`、exec `80993`；目录 `selftest_tmp/priority-repair/b1-client-20261114/runtime/v5_server`，日志 `server-console.log`，昵称 `B1隔离验收`、UID `261113200139`、版本 `332`。独立副本来自已验 B0 源码，账号由旧 B1 合成库经 SQLite backup API 复制；旧 B0／B1 和真实主库未改。CDN off、capture false、空 AI profile、配置和聊天显式绑定本副本。hosts 本轮原字节备份为 `b1-client-20261114/hosts.original.bin`，同一 10 域名 Apply exit 0；验收后已 Restore，此会话现已结束。
- 沿用既有结算串行 5 项、发奖失败 16 项、奖励 21 项及冷重开通过结果；周期 32 次执行中指定历史 before 缺失的 2 个子用例仍 error／exit 1，不写成通过。B0 的资源 16／探测 5／分发 21／连接版本 13 均已通过，本轮未再改这些路径，不重跑。没有客户端数值缺陷的零发现结论，M2 未完成前不能写 0 缺陷。
- 本轮产物只包括现有走查／台账／交付／交接文档、隔离运行副本及前／后／重登快照。新增生产模块、类、顶层函数、参数和配置键均为 0；既有 `verify_boss_reward_guard.py` 冷重开方法留在工作区，不纳入 B0 提交。第 12 项仍是 M2 的可选 M-5 观察入口，本票只登记结果或未执行原因，不自动实施 B2 的转储分析和三关修复。
- M2 第 1 项：用户确认“协议锚定探测／奇迹缔造法则”，精准探测凭证 `20`、十连显示成本 `10`。实际库 `currency.id=38` 为 20，两个对应池 `5020301`／`5020601` 的 `cost_ten_times=[38,10]`，抽卡记录初始为空。`snapshots/01-before.db` 和 JSON 已由现有 `AccountDB.backup_save_file` 保存完整一致性快照；用户已完成一次十连及重登。before／after／relogin 三份实际库快照证明票38由20→10、draw_record新增10条、角色1056雷獠·伽梨新增、1148重复转10碎片、钥从新增8个、共鸣辉芒新增110，after与relogin对应状态相同。数值与重登核对通过，截图尚未回传；不能据此把全部M2写成通过。

### B1：首次资产与客户端准备复验（历史）

- 起点：`main@93bbcc2946513e3f24333b2efb1fb74314491186`，工作区干净，领先远端 51 个提交。用户明确要求“开始推进 B1”；本轮没有提交或推送。
- 产物：扩展 `verify_boss_reward_guard.py:103`，新增 1 个测试方法。新增／删除模块、类、顶层函数均为 `0`，净增 `0`；不改生产代码、配置或断言，不新增抽象。扣费复用已通过的 `test_hero_response_boundary.py:163`、`:255`、`:348`、`:355`，不重复开发或重跑。
- 查重结论：旧 `cold_history` 只在同一内存库生成协议，不能证明磁盘恢复。新增方法将隔离库备份到临时文件，关闭目标连接和源库，调用 `AccountDB.open_existing()`，重建 Core／Connection 并重绑 `_db`。
- 实际结果：`45101` 读回、资产及领取记录与关闭前一致；单档重领返回 `2013`，一键空领成功且资产不变，`integrity_check=ok`。本用例不证明客户端重登或冷重开后的跨周迁移。
- 命令：设置 `PYTHONPATH=v5_server/tools` 后执行 `python -B -X utf8 -m unittest -v verify_boss_reward_guard.BossRewardTests.test_claim_history_and_balances_survive_database_reopen`，退出 `0`，Ran 1。`python -B -X utf8 v5_server/tools/verify_boss_reward_guard.py` 退出 `0`，Ran 21。`python -B -X utf8 v5_server/tools/verify_boss_cycle_clock.py` 退出 `1`，Ran 32，errors 2。三次运行有重复，不相加为独立覆盖数。
- 保留失败：同一周期方法的 2 个子用例仍缺 `archive/boss_cycle_clock_20261104/before/v5_server/weekly_challenge_service.py`，filed；未补近似原件、放宽断言或增加 skip。既有 `middleware.py:4088` 资源告警仍归 A2-W01。
- 证据：`selftest_tmp/priority-repair/b1-recheck-20261113/` 包含三份原始日志、逐项命令 `results.json`、哈希 `before.json`／`summary.json`。9 个受保护路径的 SHA256 不变，包含真实主库及证书／私钥／分发文件。
- 客户端准备：用户提供启动器 `C:\Program Files\AetherGazerStarter_Bili\AetherGazerLauncher.exe`；本体位于同目录下 `AetherGazer_Bili\AetherGazer_Bili.exe`。Unity 为 `2022.3.62f3c1`，不能据此认定游戏资源版本 `321`。`url.txt` 指向生产活动 API。hosts 中项目映射为 `0/10`，实测 `open.ys4fun.com` 与 `prod-api-activity.ys4fun.com` 均解析到 `203.107.63.115`。
- 门禁：尚未启动游戏或完整服务。`client-preflight.json` 与 `hosts-proposed.txt` 保存实际值和现有启动壳 10 域名的本地映射预览，未应用。需用户确认临时路由变更；获得授权后先备份 hosts，配置隔离库／槽位／配置／备份目录，再验证 B 服版本与本地登录，最后执行 M2 12 项。A1 信任成果沿用，不再次安装。
- 功能复核：根 Codex 与 `gpt-6-luna`／`high` 分别检查实际调用和日志；根以不同模型复核共享 Core／Connection 及临时库边界。新增覆盖完成；历史缺证与客户端门禁 filed。单独复杂度复核删除清单：无。同类冷读误称已扫，奖励脚本原两处同库查询均保留为协议回读，不记作文件恢复。
- 额度：开始剩余 5 小时 `18%`、周 `87%`；最终读取为 `10%`、`86%`，已触发用户“任一窗口剩余不超过 10% 时停止并保存交接”规则，立即停止实施和测试，只保存交接。未重置额度。B1 仍为 partial，不能声称发现 `0` 个客户端缺陷或完成 M2；额度恢复后只接续 B1，临时路由仍需确认，不开始 B2。

### B1：临时路由与客户端实际重试

- 范围：用户本轮明确授权按预览临时修改 Windows hosts，先备份、验收后恢复；随后要求自行操作客户端。根串行操作，两个 `gpt-6-luna/high` 子代理只读复核 hosts 交易、隔离边界、SDK 契约与资源路径。本轮没有新增生产模块、类、函数、配置键或测试，净增均为 `0`。
- 隔离：复制 5934 个跟踪文件到 `selftest_tmp/priority-repair/b1-client-20261113/runtime/`。复用存档构建器，只读取得既有审核静态目录，生成唯一主人合成档，空 API 配置，不继承真实账号或凭据。CDN off、no-capture、no-dns；未请求官方更新或下载。临时完整服务的自检退出 `0`，代码操作数 `429`、骨架 `920`，只是启动自检口径，不替代原 423 操作冒烟或客户端验收。
- 路由：`hosts-transaction.ps1 -Action Apply` 退出 `0`，原始 65492 字节只追加 406 字节标记块，10 域名均回读 `127.0.0.1`。原件备份及前后哈希保留。操作脚本的 DNS 数组判定在执行前修正，根和 Luna 复核后才应用，同类已扫，无其他。
- 初始化：用户截图卡住，客户端日志 4 次报小 UID `42` 的 `Int32→Int64` 异常。B1-C01 filed；SDK JSON 动态数字 ID 同类只命中 `server_net.py:1758`，GM JSON 状态和网关 protobuf 不属于该 SDK 消费路径。旧隔离档保留后，复用 `allocate_uid()` 和构建器生成 `261113200139`；实际 API／SDK／主人回读一致，完整性 `ok`，用户重开后确认越过初始化。仅修正夹具前置，不宣称生产兼容缺口已修，也不作为 M2 数值首例。
- 资源：安装主清单为 app `307`／build `332`，服务端所选 PC 原生为 `307/321`。用户确认更新失败；冻结访问日志记录 `.ys` 请求 2928 次，全为 `404`，含重试，唯一文件名 82 个；82 个均对应 321 清单，清单尺寸合计 `244992009` 字节。该集合不代表全版本缺口。安装目录 70085 个文件及仓库已有缓存均无这 82 个同名文件；未用不匹配来源、未弱化校验，B1-R01 filed。仅设置资源 root 不能补齐文件。
- 收尾：用户确认退出。`hosts-transaction.ps1 -Action Restore` 退出 `0`，恢复 SHA256 `5C1717F046D7DB88ACC5C2626BF41DB40C4866C9BD24AB9B25DE1E2CC6027A54`、长度 `65492`，与原始字节一致。即时回执解析值仍为回环地址，另存后续独立 DNS 回读：两关键域均为 `203.107.63.115`，只声明这两项查询。PID `34236`／`37124` 和两个 exec 会话已退出，35 个 TCP 端口及 UDP `6105` 可独占绑定。9 个保护路径及客户端原清单哈希不变。
- 证据：本轮目录内 `preparation.json`、`uid-rebuild.json`、`sdk-initialization-blocker.json`、`resource-update-blocker.json`、`resource-missing-specs.json`、`cleanup-readback.json` 和 hosts／DNS 回执。原始日志含渠道凭据及签名，保留于忽略目录，不原样输出。
- 复核：根 Codex 与 Luna 分别检查真实客户端结果、SDK 和资源实际调用、写入边界及恢复证据。独立复杂度复核删除清单：无；保留临时副本、旧夹具和证据。未验证的渠道 `10/9` 差异 filed，不猜改。当前 B1 为 partial；先补可信匹配资源，再接续同一张票，不开始 B2。
- 额度：本轮最近成功读取为 5 小时剩余 `80%`、周 `82%`；收尾读取接口返回无法读取，未将旧值当作当前实时值，未重置。

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

A 阶段成果和缺证边界保留。B0 的版本／资源及联网客户端完整流程已有证据，仅 B0-S01 断网 B 站认证按用户指示后置，整票保持 partial；其他必需项无遗漏。临时 hosts 和服务已清理，用户已确认恢复 B1，第 1 项数值与重登已核对，其余待用户整批自查。G 仍需同会话邮箱与协议证据，B2／F 需实际游玩，D 托管重启未验，H1 待审校，H2 保留 M2 门禁。

历史 A2 开始时额度剩余 5 小时 `30%`、周 `89%`；最新 B0 额度见本轮记录。没有使用额度重置或购买。
