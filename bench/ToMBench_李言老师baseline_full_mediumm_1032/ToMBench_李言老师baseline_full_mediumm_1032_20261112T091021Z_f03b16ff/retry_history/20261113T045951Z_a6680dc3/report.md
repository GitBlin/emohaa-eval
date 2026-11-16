# 李言老师 ToMBench 本地评测

状态：complete；更新时间：2026-11-13T04:59:17.602328+00:00（UTC）。
botId=1032；底座版本=unreported；harness版本=unreported。

完成 5720/5720 次；按次准确率 81.77%；按题投票准确率 81.77%。
无效答案 0；最终请求失败 1；所有尝试中错误 410。

| 题目文件 | 次数 | 答对 | 无效 | 请求失败 | 准确率 |
|---|---:|---:|---:|---:|---:|
| Completion of Failed Actions | 40 | 22 | 0 | 0 | 55.00% |
| Hinting Task Test | 206 | 195 | 0 | 0 | 94.66% |
| Discrepant Emotions | 80 | 74 | 0 | 0 | 92.50% |
| False Belief Task | 1200 | 1084 | 0 | 0 | 90.33% |
| Ambiguous Story Task | 400 | 338 | 0 | 0 | 84.50% |
| Multiple Desires | 40 | 39 | 0 | 0 | 97.50% |
| Discrepant Intentions | 80 | 72 | 0 | 0 | 90.00% |
| Knowledge-Attention Links | 40 | 20 | 0 | 0 | 50.00% |
| Faux-pas Recognition Test | 1120 | 900 | 0 | 0 | 80.36% |
| Unexpected Outcome Test | 600 | 465 | 0 | 0 | 77.50% |
| Prediction of Actions | 40 | 32 | 0 | 0 | 80.00% |
| Discrepant Desires | 40 | 25 | 0 | 0 | 62.50% |
| Scalar Implicature Test | 400 | 230 | 0 | 1 | 57.50% |
| Moral Emotions | 80 | 69 | 0 | 0 | 86.25% |
| Knowledge-Pretend Play Links | 60 | 28 | 0 | 0 | 46.67% |
| Emotion Regulation | 40 | 15 | 0 | 0 | 37.50% |
| Percepts-Knowledge Links | 80 | 79 | 0 | 0 | 98.75% |
| Strange Story Task | 814 | 722 | 0 | 0 | 88.70% |
| Persuasion Story Task | 200 | 131 | 0 | 0 | 65.50% |
| Hidden Emotions | 160 | 137 | 0 | 0 | 85.62% |

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

本次智能体1032在已完成的5720次ToMBench本地适配试次上，按次准确率为81.77%；不代表临床效果或harness增益。
1. 完成度：5720/5720，数据、提示词与代码哈希见manifest，完整输入见plan。
2. 协议与接口：无效回答0，最终失败1，原始证据见trials。
3. 分项成绩见summary，失败案例见badcases，待核查原因及优化排期见review_queue；后台版本仍需确认。

## 各轮成绩（repeat从0计数）

{
  "0": {
    "count": 5720,
    "correct": 4677,
    "valid": 5719,
    "invalid": 0,
    "errors": 1,
    "accuracy": 0.8176573426573427,
    "accuracy_on_valid": 0.8178003147403392,
    "strict_format_rate": 0.9998251748251749
  }
}

{
  "complete_rounds": 1,
  "mean_accuracy": 0.8176573426573427,
  "sample_std_accuracy": null
}

## 中英文分别的三轮成绩

{
  "en": {
    "rounds": {
      "1": {
        "count": 2860,
        "correct": 2347,
        "valid": 2859,
        "invalid": 0,
        "errors": 1,
        "accuracy": 0.8206293706293706,
        "accuracy_on_valid": 0.8209164043371808,
        "strict_format_rate": 0.9996503496503496
      }
    },
    "complete_rounds": 1,
    "mean_accuracy": 0.8206293706293706,
    "sample_std_accuracy": null
  },
  "zh": {
    "rounds": {
      "1": {
        "count": 2860,
        "correct": 2330,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.8146853146853147,
        "accuracy_on_valid": 0.8146853146853147,
        "strict_format_rate": 1.0
      }
    },
    "complete_rounds": 1,
    "mean_accuracy": 0.8146853146853147,
    "sample_std_accuracy": null
  }
}

各语言按题投票：
{
  "en": {
    "completed_questions": 2860,
    "accuracy": 0.8206293706293706
  },
  "zh": {
    "completed_questions": 2860,
    "accuracy": 0.8146853146853147
  }
}

## 排除跨语言选项数异常的辅助成绩

{
  "excluded_sample_ids": [
    "Strange Story Task:293"
  ],
  "note": "辅助口径：两种语言均排除选项数不一致题目；原始全量结果保留，不修改题库",
  "by_language": {
    "en": {
      "count": 2859,
      "correct": 2347,
      "valid": 2858,
      "invalid": 0,
      "errors": 1,
      "accuracy": 0.8209164043371808,
      "accuracy_on_valid": 0.8212036389083275,
      "strict_format_rate": 0.9996502273522211
    },
    "zh": {
      "count": 2859,
      "correct": 2329,
      "valid": 2859,
      "invalid": 0,
      "errors": 0,
      "accuracy": 0.8146204966771599,
      "accuracy_on_valid": 0.8146204966771599,
      "strict_format_rate": 1.0
    }
  }
}

## 耗时外推

{
  "measured_trials": 5720,
  "mean_seconds_per_trial_including_interval": 5.324424364911457,
  "median_seconds": 2.3664871249347925,
  "p95_seconds": 24.414129596203566,
  "remaining_hours_estimate": 0.0,
  "full_dataset_1_repeat_1_language_hours": 4.229959356568546,
  "full_dataset_5_repeats_1_language_hours": 21.14979678284273,
  "workers": 8,
  "caveat": "剩余耗时按并发数理想缩放；full_dataset字段为串行估计；不含认证、限流和中断"
}
