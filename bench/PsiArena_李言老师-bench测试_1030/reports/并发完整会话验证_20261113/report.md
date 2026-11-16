# PsiArena DeepSeek + 李言老师 1030 完整会话并发验证

2026-11-13（北京时间）。结论：本次 2 并发和 4 并发均成功，建议先使用 4 个并发会话。更高并发未测，不声称这是最高稳定上限。

## 配置

- 被测咨询师：李言老师 botId=1030；服务端管理会话历史。
- 模拟来访者、三方评分（来访者/督导/咨询师视角）：https://axonhub.ai-role.cn/v1，deepseek-v4.1-flash-1017，thinking.type=disabled。督导是对话后的评分，无实时干预。
- 每个案例 25 轮（25 次咨询师 + 25 次来访者），之后 3 次裁判调用，33 维。
- psycho 模式，code 评分口径；来访者 full 完整历史；温度0.7，生成上限2048，裁判上限4096，超时120秒。咨询师采样参数由平台控制。
- 每案例新随机 userId，开头清空一次并验证空历史。轮内顺序，案例间并发；不重试可能已生效的咨询师请求。

## 实测

| 并发 | 角色卡 | 完成 | 用时 | 错误 |
|---|---|---|---|---|
| 2 | 000,001 | 2/2 | 117.1秒 | 0 |
| 4 | 002,003,004,005 | 4/4 | 126.0秒 | 0 |

6 个案例均通过 25 轮历史审计：共306次上下文查询；最终每案例50条消息与实际发送和回复逐条一致；6个用户与6个会话ID均独立。来访者请求 messages 长度逐轮从2增加到50，未裁剪旧轮次。318次生成调用均完成，168次DeepSeek响应未出现非空推理内容或正数推理token。

额外并行记忆探针：两个同时存在的独立用户，各3轮；随机标记仅首轮发送，第三轮不重发历史，均精确回忆各自标记，没有返回另一会话标记。证据：../../../api_diagnostics/PsiArena_parallel_memory_20261113T014429Z_49320b93/report.json。该探针不计入成绩。

这些证据覆盖可见历史与本次有限行为测试，不能证明服务端模型始终使用全部25轮或所有隐藏共享记忆机制完全隔离。

## 小样本分数（不是全量成绩）

- client: 2.854167；code口径通过 5/6。
- supervisor: 3.312500；code口径通过 5/6。
- counselor: 3.962963；code口径通过 4/6。
- overall: 3.267677；code口径通过 6/6。

code Overall 为逐案例维度加权分数，达到3即通过，不等于三个视角全部通过；不同视角量表上限不同。角色卡不同，不能把两批分数差归因于并发。DeepSeek及完整历史为适配设置，不是原论文GPT-4o/滑窗配置复现。

## DeepSeek用量

{
  "client": {
    "prompt_tokens": 326510,
    "completion_tokens": 4642,
    "total_tokens": 331152,
    "usage_missing": 0
  },
  "judge": {
    "prompt_tokens": 67589,
    "completion_tokens": 22981,
    "total_tokens": 90570,
    "usage_missing": 0
  }
}

## 运行命令

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/PsiArena
python scripts/smoke_liyan.py --cards 4 --workers 4 --turns 25 --history full --protocol code --execute
```

每次创建新目录和用户；不会覆盖本次记录。未运行100案例全量。

## 运行目录

- ../../PsiArena_李言老师-bench测试_1030_20261113T014001Z_54ac368c/ （manifest、summary、validation、usage、完整对话/评分及原始接口记录）
- ../../PsiArena_李言老师-bench测试_1030_20261113T014226Z_b5e3eb99/ （manifest、summary、validation、usage、完整对话/评分及原始接口记录）
