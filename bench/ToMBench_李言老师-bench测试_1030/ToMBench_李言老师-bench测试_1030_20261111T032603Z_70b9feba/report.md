# 李言老师 ToMBench 本地评测

状态：complete；更新时间：2026-11-11T03:45:26.832108+00:00（UTC）。
botId=1030；底座版本=unreported；harness版本=unreported。

完成 17160/17160 次；按次准确率 77.92%；按题投票准确率 78.65%。
无效答案 0；最终请求失败 0；所有尝试中错误 0。

| 题目文件 | 次数 | 答对 | 无效 | 请求失败 | 准确率 |
|---|---:|---:|---:|---:|---:|
| Completion of Failed Actions | 120 | 66 | 0 | 0 | 55.00% |
| Hinting Task Test | 618 | 581 | 0 | 0 | 94.01% |
| Discrepant Emotions | 240 | 223 | 0 | 0 | 92.92% |
| False Belief Task | 3600 | 3000 | 0 | 0 | 83.33% |
| Ambiguous Story Task | 1200 | 987 | 0 | 0 | 82.25% |
| Multiple Desires | 120 | 113 | 0 | 0 | 94.17% |
| Discrepant Intentions | 240 | 211 | 0 | 0 | 87.92% |
| Knowledge-Attention Links | 120 | 42 | 0 | 0 | 35.00% |
| Faux-pas Recognition Test | 3360 | 2653 | 0 | 0 | 78.96% |
| Unexpected Outcome Test | 1800 | 1324 | 0 | 0 | 73.56% |
| Prediction of Actions | 120 | 88 | 0 | 0 | 73.33% |
| Discrepant Desires | 120 | 65 | 0 | 0 | 54.17% |
| Scalar Implicature Test | 1200 | 592 | 0 | 0 | 49.33% |
| Moral Emotions | 240 | 205 | 0 | 0 | 85.42% |
| Knowledge-Pretend Play Links | 180 | 36 | 0 | 0 | 20.00% |
| Emotion Regulation | 120 | 67 | 0 | 0 | 55.83% |
| Percepts-Knowledge Links | 240 | 218 | 0 | 0 | 90.83% |
| Strange Story Task | 2442 | 2122 | 0 | 0 | 86.90% |
| Persuasion Story Task | 600 | 375 | 0 | 0 | 62.50% |
| Hidden Emotions | 480 | 403 | 0 | 0 | 83.96% |

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

本次智能体1030在已完成的17160次ToMBench本地适配试次上，按次准确率为77.92%；不代表临床效果或harness增益。
1. 完成度：17160/17160，数据、提示词与代码哈希见manifest，完整输入见plan。
2. 协议与接口：无效回答0，最终失败0，原始证据见trials。
3. 分项成绩见summary，失败案例见badcases，待核查原因及优化排期见review_queue；后台版本仍需确认。

## 各轮成绩（repeat从0计数）

{
  "0": {
    "count": 5720,
    "correct": 4438,
    "valid": 5720,
    "invalid": 0,
    "errors": 0,
    "accuracy": 0.7758741258741259,
    "accuracy_on_valid": 0.7758741258741259,
    "strict_format_rate": 1.0
  },
  "1": {
    "count": 5720,
    "correct": 4458,
    "valid": 5720,
    "invalid": 0,
    "errors": 0,
    "accuracy": 0.7793706293706294,
    "accuracy_on_valid": 0.7793706293706294,
    "strict_format_rate": 1.0
  },
  "2": {
    "count": 5720,
    "correct": 4475,
    "valid": 5720,
    "invalid": 0,
    "errors": 0,
    "accuracy": 0.7823426573426573,
    "accuracy_on_valid": 0.7823426573426573,
    "strict_format_rate": 1.0
  }
}

{
  "complete_rounds": 3,
  "mean_accuracy": 0.7791958041958041,
  "sample_std_accuracy": 0.003237807548505603
}

## 中英文分别的三轮成绩

{
  "en": {
    "rounds": {
      "1": {
        "count": 2860,
        "correct": 2203,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.7702797202797202,
        "accuracy_on_valid": 0.7702797202797202,
        "strict_format_rate": 1.0
      },
      "2": {
        "count": 2860,
        "correct": 2209,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.7723776223776224,
        "accuracy_on_valid": 0.7723776223776224,
        "strict_format_rate": 1.0
      },
      "3": {
        "count": 2860,
        "correct": 2227,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.7786713286713287,
        "accuracy_on_valid": 0.7786713286713287,
        "strict_format_rate": 1.0
      }
    },
    "complete_rounds": 3,
    "mean_accuracy": 0.7737762237762238,
    "sample_std_accuracy": 0.004367131467411496
  },
  "zh": {
    "rounds": {
      "1": {
        "count": 2860,
        "correct": 2235,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.7814685314685315,
        "accuracy_on_valid": 0.7814685314685315,
        "strict_format_rate": 1.0
      },
      "2": {
        "count": 2860,
        "correct": 2249,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.7863636363636364,
        "accuracy_on_valid": 0.7863636363636364,
        "strict_format_rate": 1.0
      },
      "3": {
        "count": 2860,
        "correct": 2248,
        "valid": 2860,
        "invalid": 0,
        "errors": 0,
        "accuracy": 0.786013986013986,
        "accuracy_on_valid": 0.786013986013986,
        "strict_format_rate": 1.0
      }
    },
    "complete_rounds": 3,
    "mean_accuracy": 0.7846153846153846,
    "sample_std_accuracy": 0.0027308565300372925
  }
}

各语言按题投票：
{
  "en": {
    "completed_questions": 2860,
    "accuracy": 0.7818181818181819
  },
  "zh": {
    "completed_questions": 2860,
    "accuracy": 0.7912587412587413
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
      "count": 8577,
      "correct": 6636,
      "valid": 8577,
      "invalid": 0,
      "errors": 0,
      "accuracy": 0.7736970968870235,
      "accuracy_on_valid": 0.7736970968870235,
      "strict_format_rate": 1.0
    },
    "zh": {
      "count": 8577,
      "correct": 6729,
      "valid": 8577,
      "invalid": 0,
      "errors": 0,
      "accuracy": 0.7845400489681706,
      "accuracy_on_valid": 0.7845400489681706,
      "strict_format_rate": 1.0
    }
  }
}

## 耗时外推

{
  "measured_trials": 17160,
  "mean_seconds_per_trial_including_interval": 1.6971311473819517,
  "median_seconds": 1.6256464160978794,
  "p95_seconds": 2.284806877374649,
  "remaining_hours_estimate": 0.0,
  "full_dataset_1_repeat_1_language_hours": 1.3482764115312174,
  "full_dataset_5_repeats_1_language_hours": 6.741382057656087,
  "workers": 32,
  "caveat": "剩余耗时按并发数理想缩放；full_dataset字段为串行估计；不含认证、限流和中断"
}
