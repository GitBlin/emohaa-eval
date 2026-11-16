# PsiArena：33 维评分与李言老师适配

本地修订版，2026-11-11。参考[官方仓库](https://github.com/Cognition-and-Language-Group/PsiArena)与[论文 arXiv v1](https://arxiv.org/html/2505.03293v1)。本地已修改提示词、评分和接口层，不再与官方源码完全相同。2026-11-13 增加会话并发和完整历史选项；离线测试已通过，实际 API 结果按独立运行报告留档。

## 当前运行配置（2026-11-13 更新）

来访者和三方评分现已改为 `thinking=enabled`、`reasoning_effort=medium`。此前无推理测试结果保持原样，不与新配置混合。官方接口将 medium 兼容映射为 high，网关内部映射未公开；留档记录实际发送的 medium，不声称验证了独立的 medium 档位。来源：https://api-docs.deepseek.com/api/create-chat-completion/ 。

当前本地 .env：来访者 max_tokens=8192，裁判 max_tokens=16384，timeout=180；这是推理加正文的预算上限，不代表固定消耗。咨询师仍是 1030，其思考参数由智能体平台控制。

```bash
# 完整 100 张角色卡，每张 25 轮，4 个会话并发
python scripts/smoke_liyan.py --start 0 --cards 100 --workers 4 --turns 25 --history full --protocol code --execute
```

共 2500 次咨询师、2500 次来访者、300 次裁判调用，另有鉴权及历史审计。评分只用最终回答，不把推理文本写入对话。每张卡独立用户；会话内部连续历史。4 并发此前在无推理模式验证通过，不能直接当作 medium 模式已完成长时间稳定性测试。无自动断点续跑；失败案例保留记录，汇总明确列出缺失项。

## 此前无推理测试的模型分工

| 职责 | 配置 |
|---|---|
| 被测咨询师 | 李言老师 1030，保留单会话历史 |
| 模拟来访者 | deepseek-v4.1-flash-1017，thinking disabled |
| 三方评分，含督导 | deepseek-v4.1-flash-1017，thinking disabled |

关闭推理参数参考 [DeepSeek 官方说明](https://api-docs.deepseek.com/guides/thinking_mode/)。实际网关行为以请求响应和 token usage 留档为准。

## 本次修复

- 来访者量表移除原第 9 项“承认错误、道歉、不狡辩”，原 10–17 项重新编号为 9–16，与论文 v1 附录的项目对应。三视角固定 16+8+9=33 维。
- 各视角单独校验完整维度块、重复项、分值范围和固定维度 ID。新裁判输出必须依次使用 `client_01` 等 ID。历史具名块可按顺序解析，但不能补救旧的 17 项结果，也不能验证历史具名块的语义顺序。
- 得分只从 `[得分]` 后解析，避免误读维度编号。缺项、重复、越界、额外项、截断均作为失败保留原文。
- 汇总保留未舍入的逐会话分数，最后输出时才由使用者选择精度；Overall 展示与通过判定使用同一逐会话算法。
- 报告计划数、有效评分数、覆盖率、无效原因。主通过率分母是全部计划会话；无效/缺失不算通过，同时给出仅有效样本的辅助通过率。

## 评分协议

默认 `--protocol code`，按用户要求保留原代码口径，不声称复现论文成绩：

| 项目 | code（默认） | paper_v1（论文正文口径） |
|---|---|---|
| 来访者 | 平均分 ≥2.6 | 总分 >42 |
| 督导 | 平均分 ≥3.0 | 总分 >24 |
| 咨询师 | 平均分 ≥3.8 | 总分 >35 |
| Overall 分数 | 有效总分 / (16+9+督导非 N/A 项数) | 三视角平均分的算术平均 |
| Overall 通过 | Overall ≥3.0 | 三视角均通过 |
| N/A | 来访者/咨询师固定分母，督导排除 N/A | 一律按 0、固定分母 |

`code` 的 Overall 保留原解析函数的项目加权算法；修复了原汇总函数显示为三视角等权平均、与通过判定不一致的问题。裁判原始 N/A 始终保留在结构化结果中。

论文正文的 AND 规则与表 2 某些 Overall 通过率存在矛盾，`paper_v1` 仅指按照正文规则实现，不代表重现表格。论文 v1 的模拟来访者和三视角评分均使用 GPT-4o；若选择 GPT-4o-mini 来访者，需要在报告中标注不同配置。

## 李言老师的记忆与接口

默认 `PSIARENA_COUNSELOR_PROVIDER=ai_role`，智能体 ID 1030。每个角色卡会话生成独立随机 userId，并在开始时执行一次 clearContext，确认 `flush_context` 和空历史。会话内部不会清空，不会在每轮重新发送全部历史，只向平台追加当前来访者消息。每轮前后检查服务端 user/role 消息对数，预期从 0 逐步增加至 25。

请求或记忆检查失败会阻断该会话，禁止自动重发、清空后假装续接。重跑应创建新运行及新用户；已收到的请求、响应及进度会保留。检查可发现可见历史丢失或多余消息，不能证明平台内部模型实际使用了所有历史，也不能关闭平台潜在的机构共享记忆。

平台的隐藏系统提示词及上下文窗口不可由当前接口直接控制。第一轮把咨询行为要求放进普通用户消息，其后保留平台服务端历史；少量测试入口默认 `--history full`，模拟来访者发送完整会话历史；可用 `--history sliding` 保留原仓库的滑动窗口。原有分步入口仍默认滑动窗口。因此结果应标注为“李言老师产品配置下的 PsiArena 适配评测”，不能称为系统提示词与上下文窗口完全等价的论文复现。

ai-role 暂支持 `vanilla` / `psycho`；`rewrite` 会产生额外咨询师反思调用，可能污染会话，已明确禁止。OpenAI 兼容咨询师可继续使用原来的 rewrite 流程。三种模式、不同协议及不同模型配置应分别留档，不能混合汇总。

## 配置

在项目目录执行：

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/PsiArena
pip install -r requirements.txt
cp -n .env.example .env
```

本地 `.env` 已配置用户提供的 AxonHub 地址与密钥，密钥仅保存在忽略提交的本地文件中。公开模板 `.env.example` 不含密钥。若本地配置已存在，不要用模板覆盖它。

当前模拟来访者和三视角评分（来访者、督导、咨询师自评）均使用 `deepseek-v4.1-flash-1017`；被测咨询师仍为李言老师 1030。`PSIARENA_CLIENT_THINKING=disabled` 和 `PSIARENA_JUDGE_THINKING=disabled` 会经 SDK 的 `extra_body` 发送顶层 `thinking: {"type": "disabled"}`，不附带 `reasoning_effort`。若响应仍有非空 `reasoning_content` 或正数 reasoning_tokens，代码将保留原始响应并拒绝接受该结果；没有这些字段也不能独立证明平台内部没有思考计算。每次运行均留档实际请求、响应和用量；是否通过以该次记录为准。

`model_catalog.json` 记录本次 GET `/v1/models` 返回的模型：`deepseek-v4.1-flash-1017`、`glm-5.3-flash`。后者未用于本次配置。更换裁判和来访者后，结果应标明 DS Flash 无推理适配配置，不能直接等同论文 GPT-4o 的成绩。可分别覆盖各角色的 `MODEL/BASE_URL/API_KEY/THINKING`；缺少角色模型配置会直接报错，不会回退到李言老师充当裁判。

李言老师凭证优先使用 `PSIARENA_AI_ROLE_API_KEY/API_SECRET`；留空时仅通过 AST 读取本地 `../../bot_chat_client.py` 的默认凭证常量，不执行该文件、不打印或复制凭证。也可用 `PSIARENA_AI_ROLE_CREDENTIAL_FILE` 指定本地文件。不要提交 `.env` 或含凭证的客户端文件。

默认温度 0.7、普通生成 max_tokens=2048、裁判 max_tokens=4096、超时 120 秒。裁判逐维分析可能超过 2048，遇到 `length` 截断会保留响应并判失败。李言老师的模型参数由平台控制，不能将客户端参数当成它的实际参数。

## 少量测试脚本

重新查询模型列表（只 GET，不生成回复）：

```bash
python scripts/list_models.py
```

先查看计划，不发起 API 请求，也不创建评测结果：

```bash
python scripts/smoke_liyan.py --cards 2
```

执行两张角色卡，每张完整 25 轮并进行三方评分：

```bash
python scripts/smoke_liyan.py --cards 2 --workers 2 --turns 25 --history full --protocol code --execute
```

默认共 100 次对话调用（咨询师 50、来访者 50）及 6 次裁判调用，另有鉴权、清理及历史审计请求。`--workers` 控制独立会话并发，默认 2，不超过角色卡数；单个会话的 25 轮严格顺序执行，三视角裁判也顺序执行。每个线程使用独立日志与会话上下文。输出位于：

```text
../PsiArena_李言老师-bench测试_1030/
  PsiArena_李言老师-bench测试_1030_<UTC时间>_<随机ID>/
```

只检查短对话和记忆链路，不评分：

```bash
python scripts/smoke_liyan.py --cards 2 --turns 3 --skip-judge --execute
```

如需快速检查生成和三方评分格式，可执行 `python scripts/smoke_liyan.py --cards 1 --turns 3 --execute`，但该短会话没有正式成绩意义。

少于 25 轮会标为 `partial_session`，即使选择评分也不能作为正式成绩。`--skip-judge` 仍需提供完整角色配置供启动验证，但不会调用裁判。该脚本每次执行建立新目录，没有中途续接功能。

## 留档

每次少量测试保存：

- `manifest.json`：计划、模型标识、参数、适配差异，以及代码/数据/提示词 SHA256。
- `snapshot/`：本次实际代码、角色卡、量表及提示词；不包含 `.env` 或凭证文件。
- `dialogueN.txt`、`scoresN.txt`：完成的对话与完整三方评分。
- `cards/NNN/memory/`：userId、开头清理、每轮历史审计和平台请求/原始响应。
- `cards/NNN/requests/`：来访者与裁判请求、响应、usage。未完成的裁判输出在 `judge_*.txt`、`scores.partial.txt`。
- `dialogue_progress.json`：每完成一轮更新，失败时仍保留请求级记录。
- `parsed_scores.json`、`summary.json`、`execution_log.jsonl`：逐项结果、覆盖率及错误类型。
- `usage_summary.json`：按角色汇总接口返回 token。平台未暴露 usage 时标注未知，不伪造估值。

运行记录可能含完整咨询内容，公开失败样本前需要按实际内容处理个人信息。

## 独立记忆行为验证

```bash
python scripts/verify_memory.py --execute
```

使用两条人工合成数据，各25轮；只调用李言老师，不调用来访者或裁判模型。每段只写入一次随机标记，在第5、15、25轮追问，追问不包含标记、不重发历史；每段完成后在同一用户下清空并盲问。第二段使用新用户，写入新标记前先盲问。共52次聊天请求，另有鉴权、清空和历史审计。

输出到 `../PsiArena_李言老师-bench测试_1030/PsiArena_李言老师_记忆验证_<时间>_<ID>/`，保存 `report.json`、`report.md` 和原始接口记录，不计入基准成绩。第二段的跨会话检查是在第一段已经清空后进行；它验证清空加独立用户的组合策略，不单独证明未清空用户之间不存在共享记忆。反复追问也可能强化标记，结果不等于模型完整保留所有25轮细节。

## 原有分步入口

```bash
python scripts/generate_dialogues.py --mode psycho --start 0 --end 2 --output-dir runs/liyan_small
python scripts/evaluate_dialogues.py --start 0 --end 2 --input-dir runs/liyan_small
python scripts/aggregate_scores.py --score-dir runs/liyan_small --start 0 --end 2 --protocol code --output runs/liyan_small/summary.json
python scripts/aggregate_scores.py --score-dir runs/liyan_small --start 0 --end 2 --check
```

分步生成已接入相同会话隔离。分步入口的 `--resume` 仅用于人工确认配置未变化后的跳过已完成文件，不提供配置一致性保护；少量测试优先使用 `smoke_liyan.py` 的独立新运行目录。汇总缺失/无效时仍输出完整 JSON，退出码为 2。全量时区间改为 `--start 0 --end 100`。

## 离线回归用例

```bash
python -m unittest discover -s tests -v
```

用例覆盖越界/重复/缺项、N/A、论文严格边界及 AND、Overall 一致性和覆盖率，以及假接口下清空一次、会话内追加、独立用户及历史丢失阻断。不会访问网络。

## 2026-11-13 完整会话并发测试

```bash
# 4 张新角色卡，4 个独立会话并发，每张 25 轮及 33 维评分
python scripts/smoke_liyan.py --start 2 --cards 4 --workers 4 --turns 25 --history full --protocol code --execute
```

来访者和全部三个裁判视角使用同一个 DeepSeek 配置；其中咨询师视角的评分也是 DeepSeek 扮演的评价视角，不是向李言老师追加自评消息。督导在对话结束后评分，当前 psycho 模式没有在线督导干预。完整历史与替换模型均属于适配设置，不能称为原论文配置复现。失败时保留记录并将该会话判为失败，不盲重试可能已被服务端处理的咨询师消息。

并行会话的独立记忆探针（两会话同时存在，各 3 轮，不计入成绩）：

```bash
python scripts/verify_parallel_memory.py --execute
```

随机标记只在各自第一轮提供；第三轮询问不包含标记，也不重发历史。验证自己的标记被回忆且没有混入另一会话的标记。这是有限的行为验证，不保证平台所有隐藏记忆机制完全隔离。
