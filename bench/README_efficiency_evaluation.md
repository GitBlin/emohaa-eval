# ToMBench / EmoBench 效率评测

入口：`bench/evaluate_efficiency.py`。读取既有完整实验的plan.json，复用原始题目、选项排列和提示词，用其快照判分；目标bot ID由命令指定。它是独立评测入口，原evaluate_liyan.py/evaluate_emobench.py及历史快照未增加计时，继续运行原命令不会生成这些新指标。

## 小批量命令

在项目根目录执行。默认不联网，加入`--execute`才实际调用。

```bash
python bench/evaluate_efficiency.py --benchmark tombench --bot-id 1030 --samples-per-group 2 --workers 1 --execute
python bench/evaluate_efficiency.py --benchmark emobench --bot-id 1030 --samples-per-group 1 --workers 1 --execute
```

ToMBench按中文/英文分组，2条/组共4条；EmoBench按EU/EA×中文/英文分组，1条/组共4条。改`--bot-id 1032`可测当前基线。默认seed=42，相同来源、seed和分组数量使用相同题目。

扩大采样时，例如ToMBench设`--samples-per-group 10`得到20条，EmoBench设5得到20条。`--samples-per-group 0`选择原plan中repeat=0的全部案例（默认来源分别5720/800条），请按预算运行。`--workers`控制最大并发，实际在途聊天请求数会受到认证和历史审计影响。

默认来源：ToMBench的1030 full_mediumm 20261112T025335Z；EmoBench的1030 full_medium 20261112T111842Z。可传`--source-run /绝对路径/原运行目录`切换。源目录必须有plan.json及snapshot中的评分脚本。

## 统计口径

- 首字：聊天HTTP请求发出前到首个非空白有效正文被解析；排除已知错误、meta、TTS、推理等类型。平台未标记的占位文本无法可靠识别，仍是限制。
- 完整耗时：同一起点到正常结束事件；要求非空回答。非流式响应在本流式测试中标为不支持/失败。
- 成功率：正常完成聊天数/已发起聊天数；答案错或格式错与传输成功分开。
- 时限达标率：成功且首字≤1/2/3/5秒的请求数/已发起聊天数。
- 线性插值P50/P95。首字统计含已出字后失败的请求；完整耗时只统计成功回复。样本不足时P95仅作观察。
- 每案例独立用户、清空并验证；无自动重试。认证/清空/历史审计不计入聊天耗时，准备失败单列且不计作已发起聊天。
- 单字节流读取降低大缓冲等待，时间包含客户端解析开销；事件在请求结束后落盘。正式大规模性能结论前需评估采集CPU开销。
- 平台实际模型/思考深度未通过本工具验证，结果反映测试时bot在线配置。

## 留档

每次生成新目录`bench/efficiency_evaluations/<benchmark>_<botid>_efficiency_<timestamp>_<id>`：
- manifest.json、plan.json：来源hash、采样设置、实际请求内容。
- trials/<id>/request.json、events.jsonl、timing.json、result.json：请求、带相对时间的事件、计时和答题结果。
- before/after历史响应：独立案例隔离核验。
- summary.json：总体及分组四项指标；report.md：可阅读报告。

首次试测（2026-11-16，1030，并发1）各4条，总计8条。ToM成功4/4、答对4/4；Emo成功4/4、答对3/4。不是全量能力成绩，也不能代表长咨询回复或生产P95。

离线验证：`python -m unittest discover -s bench -p test_evaluate_efficiency.py -v`。覆盖元信息与推理排除、真实HTTP分片计时、错误和中断的统计分母。

## 正文片段间隔（2026-11-16新增）

相同命令现在额外记录`text_event_count`、`text_arrival_seconds`、`text_event_characters`、`text_gap_seconds`、`max_text_gap_seconds`及`tail_wait_seconds`。仅统计非空白有效正文片段；排除已知错误、元信息及单独的推理事件。

summary.json的`text_gaps`按成功请求汇总，每条请求贡献一个最大间隔，再计算这些最大值的P50/P95；不是把所有片段间隔混在一起计算。另报告超过0.5/1/2秒的请求数和收尾等待。阈值仅为观察窗口。单正文片段没有相邻间隔，返回null并单列数量；失败请求保留已观测间隔，但不纳入成功请求汇总。

这是客户端观察到的SSE正文片段间隔，受服务端分片、网络及客户端缓冲影响，不能等同于逐token生成延迟。

## Arena：10个完整多轮会话

新增`bench/evaluate_arena_efficiency.py`，复用相同SSE测量函数和现有Arena对话流程。

```bash
# 环境缺少依赖时建立一次
python -m venv --system-site-packages .venv-efficiency
.venv-efficiency/bin/python -m pip install openai python-docx

# ToMBench：10题，中英文各5题
.venv-efficiency/bin/python bench/evaluate_efficiency.py --benchmark tombench --bot-id 1030 --samples-per-group 5 --workers 4 --execute

# Arena：案例0–9，每个25轮；只生成对话和效率记录，不调用质量裁判
.venv-efficiency/bin/python bench/evaluate_arena_efficiency.py --bot-id 1030 --cards 10 --workers 4 --execute
```

Arena使用当前PsiArena/.env中的来访者配置，服务端咨询师配置不由这些参数控制。全历史、psycho提示词、每案例独立用户、开始清空一次、逐轮审计历史。每次聊天和模拟来访者调用不自动重放；`--session-attempts 2`（默认）允许失败案例从新用户整体重建，所有失败尝试保留。

每轮计时位于`cards/<case>/attempt_<n>/memory/timings/turn_<n>_chat/`。汇总含`all_attempts`（所有咨询师请求）、`completed_session_turns`（最终完整会话请求）、`by_turn_group`和`per_card`。客户端最大会话并发不等于持续请求负载；不可用整场墙钟时间推断纯咨询师吞吐能力。
