# 李言老师 ToMBench 本地评测

状态：prepared；更新时间：2026-11-09T07:53:35.279810+00:00（UTC）。
botId=242；底座版本=unreported；harness版本=unreported。

完成 0/28600 次；按次准确率 N/A；按题投票准确率 N/A。
无效答案 0；最终请求失败 0；所有尝试中错误 0。

| 题目文件 | 次数 | 答对 | 无效 | 请求失败 | 准确率 |
|---|---:|---:|---:|---:|---:|

## 口径与限制

本报告是线上智能体的 ToMBench 适配评测，不是纯 Emohaa 分数或官方榜单提交。模型与 harness 标识由操作者填写，服务端版本锁定需负责人确认。
答题要求放在用户消息；温度等生成参数由服务端控制。二选一提示词去掉不存在的选项；错误标准答案 A. 被规范化为 A。
严格提取唯一 [[A]] 类标记；无效/失败计错。多次答案映射回原选项后按最高票选取，并列不猜测；缺失试次的题不计入投票分母。
与原仓库默认A、并列取首个等行为存在差异，不能不加说明直接对比论文数值。20个题目文件不等于论文8类任务；能力标签保留原始字符串并去除首尾空格。
每次尝试前清理并核查当前会话；这不保证跨会话长期记忆、其他业务状态完全清除。请勿用其他进程同时操作本次user_id。
本次只评测ToMBench；EmoBench、Psy-Arena、MentalHealthBench，以及安全、记忆、抢话等业务指标不由此成绩替代。
所有题目仅用于评估，原始数据、代码、提示词及哈希均留档；badcases只在本地保存，未公开或对外提交。

## 交付物

manifest.json、plan.json、data_audit.json、snapshot/、trials/、responses.jsonl、question_votes.json、summary.json、badcases.jsonl、review_queue.json、artifact_index.json。
trials下保留每次清理、历史查询、聊天请求、原始响应体、解析事件和错误；不保存API密钥或认证Token。

## 结论草稿与三条支撑（内部使用）

本次李言老师242在已完成的0次ToMBench本地适配试次上，按次准确率为N/A；不代表临床效果或harness增益。
1. 完成度：0/28600，数据、提示词与代码哈希见manifest，完整输入见plan。
2. 协议与接口：无效回答0，最终失败0，原始证据见trials。
3. 分项成绩见summary，失败案例见badcases，待核查原因及优化排期见review_queue；后台版本仍需确认。
