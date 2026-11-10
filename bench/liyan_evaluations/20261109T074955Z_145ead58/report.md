# 李言老师 ToMBench 本地评测

状态：complete；更新时间：2026-11-09T07:51:50.105280+00:00（UTC）。
botId=242；底座版本=unreported；harness版本=unreported。

完成 20/20 次；按次准确率 90.00%；按题投票准确率 90.00%。
无效答案 0；最终请求失败 0；所有尝试中错误 0。

| 题目文件 | 次数 | 答对 | 无效 | 请求失败 | 准确率 |
|---|---:|---:|---:|---:|---:|
| Completion of Failed Actions | 1 | 1 | 0 | 0 | 100.00% |
| Hinting Task Test | 1 | 1 | 0 | 0 | 100.00% |
| Discrepant Emotions | 1 | 1 | 0 | 0 | 100.00% |
| False Belief Task | 1 | 1 | 0 | 0 | 100.00% |
| Ambiguous Story Task | 1 | 1 | 0 | 0 | 100.00% |
| Multiple Desires | 1 | 1 | 0 | 0 | 100.00% |
| Discrepant Intentions | 1 | 1 | 0 | 0 | 100.00% |
| Knowledge-Attention Links | 1 | 1 | 0 | 0 | 100.00% |
| Faux-pas Recognition Test | 1 | 1 | 0 | 0 | 100.00% |
| Unexpected Outcome Test | 1 | 1 | 0 | 0 | 100.00% |
| Prediction of Actions | 1 | 1 | 0 | 0 | 100.00% |
| Discrepant Desires | 1 | 1 | 0 | 0 | 100.00% |
| Scalar Implicature Test | 1 | 1 | 0 | 0 | 100.00% |
| Moral Emotions | 1 | 1 | 0 | 0 | 100.00% |
| Knowledge-Pretend Play Links | 1 | 0 | 0 | 0 | 0.00% |
| Emotion Regulation | 1 | 1 | 0 | 0 | 100.00% |
| Percepts-Knowledge Links | 1 | 1 | 0 | 0 | 100.00% |
| Strange Story Task | 1 | 1 | 0 | 0 | 100.00% |
| Persuasion Story Task | 1 | 0 | 0 | 0 | 0.00% |
| Hidden Emotions | 1 | 1 | 0 | 0 | 100.00% |

## 口径与限制

本报告是线上智能体的 ToMBench 适配评测，不是纯 Emohaa 分数或官方榜单提交。模型与 harness 标识由操作者填写，服务端版本锁定需负责人确认。
答题要求放在用户消息；温度等生成参数由服务端控制。二选一提示词去掉不存在的选项；错误标准答案 A. 被规范化为 A。
严格提取唯一 [[A]] 类标记；无效/失败计错。多次答案映射回原选项后按最高票选取，并列不猜测；缺失试次的题不计入投票分母。
与原仓库默认A、并列取首个等行为存在差异，不能不加说明直接对比论文数值。20个题目文件不等于论文8类任务；能力标签保留原始字符串并去除首尾空格。
每次尝试前清理并核查当前会话；这不保证跨会话长期记忆、其他业务状态完全清除。请勿用其他进程同时操作本次user_id。
本次只评测ToMBench；EmoBench、Psy-Arena、MentalHealthBench，以及安全、记忆、抢话等业务指标不由此成绩替代。
所有题目仅用于评估，原始数据、代码、提示词及哈希均留档；badcases只在本地保存，未公开或对外提交。

## 交付物

manifest.json、plan.json、snapshot/、trials/、responses.jsonl、question_votes.json、summary.json、badcases.jsonl、artifact_index.json。
trials下保留每次清理、历史查询、聊天请求、原始响应体、解析事件和错误；不保存API密钥或认证Token。

## 耗时外推

{
  "measured_trials": 20,
  "mean_seconds_per_trial_including_interval": 1.6609354685992002,
  "median_seconds": 1.6457376897335052,
  "p95_seconds": 1.8097456030547618,
  "remaining_hours_estimate": 0.0,
  "full_dataset_1_repeat_1_language_hours": 1.3195209556093646,
  "full_dataset_5_repeats_1_language_hours": 6.597604778046823,
  "caveat": "基于当前样本和服务速度线性外推，不含长期限流/中断；CoT与不同语言需另测"
}
