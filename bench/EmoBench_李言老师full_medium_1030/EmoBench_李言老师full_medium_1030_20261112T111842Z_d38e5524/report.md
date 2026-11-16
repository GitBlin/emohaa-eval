# EmoBench 独立评测报告

状态：complete；完成800/800；botId=1030。

| 任务 | 语言 | 答对/次数 | 三轮/多轮均值 | 样本标准差（百分点） | EU情绪准确率 | EU原因准确率 |
|---|---|---:|---:|---:|---:|---:|
| EU | zh | 123/200 | 61.50% | N/A | 63.50% | 83.00% |
| EU | en | 144/200 | 72.00% | N/A | 75.00% | 85.00% |
| EA | zh | 146/200 | 73.00% | N/A | N/A | N/A |
| EA | en | 151/200 | 75.50% | N/A | N/A | N/A |

| 任务 | 语言 | 轮次 | 答对/次数 | 准确率 |
|---|---|---:|---:|---:|
| EU | zh | 1 | 123/200 | 61.50% |
| EU | en | 1 | 144/200 | 72.00% |
| EA | zh | 1 | 146/200 | 73.00% |
| EA | en | 1 | 151/200 | 75.50% |

EU主成绩要求情绪和原因同时正确；情绪/原因分数只是辅助诊断。EA主成绩要求所选动作/回应正确。全局合并准确率不是官方EU/EA分数的替代。

默认不打乱选项，使用官方提示词和JSON字段；本客户端将系统指令合并进用户消息，后台生成参数无法锁定，不宣称完全复现论文设置。

多轮按次平均为主成绩；投票为辅助成绩，EU按完整答案对投票而非分别拼接情绪/原因。并列计错。

## 完整分类、轮次和投票

```json
{
  "EU": {
    "zh": {
      "overall": {
        "count": 200,
        "correct": 123,
        "accuracy": 0.615,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": 0.635,
        "cause_accuracy": 0.83
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 123,
          "accuracy": 0.615,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.635,
          "cause_accuracy": 0.83
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.615,
      "sample_std_accuracy": null,
      "categories": {
        "complex_emotions": {
          "count": 49,
          "correct": 38,
          "accuracy": 0.7755102040816326,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8163265306122449,
          "cause_accuracy": 0.9183673469387755
        },
        "emotional_cues": {
          "count": 28,
          "correct": 20,
          "accuracy": 0.7142857142857143,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7142857142857143,
          "cause_accuracy": 0.8928571428571429
        },
        "personal_beliefs_and_experiences": {
          "count": 56,
          "correct": 32,
          "accuracy": 0.5714285714285714,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5892857142857143,
          "cause_accuracy": 0.8571428571428571
        },
        "perspective_taking": {
          "count": 67,
          "correct": 33,
          "accuracy": 0.4925373134328358,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5074626865671642,
          "cause_accuracy": 0.7164179104477612
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 23,
          "correct": 13,
          "accuracy": 0.5652173913043478,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5652173913043478,
          "cause_accuracy": 0.9130434782608695
        },
        "emotion_transition": {
          "count": 15,
          "correct": 11,
          "accuracy": 0.7333333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7333333333333333,
          "cause_accuracy": 0.8666666666666667
        },
        "false_belief": {
          "count": 26,
          "correct": 11,
          "accuracy": 0.4230769230769231,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.46153846153846156,
          "cause_accuracy": 0.5769230769230769
        },
        "faux_pas": {
          "count": 25,
          "correct": 14,
          "accuracy": 0.56,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.56,
          "cause_accuracy": 0.88
        },
        "mixture_of_emotions": {
          "count": 14,
          "correct": 10,
          "accuracy": 0.7142857142857143,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7857142857142857,
          "cause_accuracy": 0.9285714285714286
        },
        "persona": {
          "count": 17,
          "correct": 8,
          "accuracy": 0.47058823529411764,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5294117647058824,
          "cause_accuracy": 0.6470588235294118
        },
        "sentimental_value": {
          "count": 16,
          "correct": 11,
          "accuracy": 0.6875,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6875,
          "cause_accuracy": 1.0
        },
        "strange_story": {
          "count": 16,
          "correct": 8,
          "accuracy": 0.5,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5,
          "cause_accuracy": 0.6875
        },
        "unexpected_outcome": {
          "count": 20,
          "correct": 17,
          "accuracy": 0.85,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9,
          "cause_accuracy": 0.95
        },
        "visual_cues": {
          "count": 15,
          "correct": 11,
          "accuracy": 0.7333333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7333333333333333,
          "cause_accuracy": 0.8
        },
        "vocal_cues": {
          "count": 13,
          "correct": 9,
          "accuracy": 0.6923076923076923,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6923076923076923,
          "cause_accuracy": 1.0
        }
      },
      "question_types": {},
      "auxiliary_vote": {
        "questions": 200,
        "correct": 123,
        "accuracy": 0.615,
        "ties_or_no_answer": 0
      }
    },
    "en": {
      "overall": {
        "count": 200,
        "correct": 144,
        "accuracy": 0.72,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": 0.75,
        "cause_accuracy": 0.85
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 144,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.75,
          "cause_accuracy": 0.85
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.72,
      "sample_std_accuracy": null,
      "categories": {
        "complex_emotions": {
          "count": 49,
          "correct": 39,
          "accuracy": 0.7959183673469388,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8775510204081632,
          "cause_accuracy": 0.8979591836734694
        },
        "emotional_cues": {
          "count": 28,
          "correct": 20,
          "accuracy": 0.7142857142857143,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7142857142857143,
          "cause_accuracy": 0.8928571428571429
        },
        "personal_beliefs_and_experiences": {
          "count": 56,
          "correct": 38,
          "accuracy": 0.6785714285714286,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6964285714285714,
          "cause_accuracy": 0.8928571428571429
        },
        "perspective_taking": {
          "count": 67,
          "correct": 47,
          "accuracy": 0.7014925373134329,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7164179104477612,
          "cause_accuracy": 0.7611940298507462
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 23,
          "correct": 14,
          "accuracy": 0.6086956521739131,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6086956521739131,
          "cause_accuracy": 0.9130434782608695
        },
        "emotion_transition": {
          "count": 15,
          "correct": 12,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9333333333333333,
          "cause_accuracy": 0.8
        },
        "false_belief": {
          "count": 26,
          "correct": 19,
          "accuracy": 0.7307692307692307,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7307692307692307,
          "cause_accuracy": 0.8076923076923077
        },
        "faux_pas": {
          "count": 25,
          "correct": 16,
          "accuracy": 0.64,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.68,
          "cause_accuracy": 0.68
        },
        "mixture_of_emotions": {
          "count": 14,
          "correct": 9,
          "accuracy": 0.6428571428571429,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7857142857142857,
          "cause_accuracy": 0.8571428571428571
        },
        "persona": {
          "count": 17,
          "correct": 12,
          "accuracy": 0.7058823529411765,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7647058823529411,
          "cause_accuracy": 0.7647058823529411
        },
        "sentimental_value": {
          "count": 16,
          "correct": 12,
          "accuracy": 0.75,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.75,
          "cause_accuracy": 1.0
        },
        "strange_story": {
          "count": 16,
          "correct": 12,
          "accuracy": 0.75,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.75,
          "cause_accuracy": 0.8125
        },
        "unexpected_outcome": {
          "count": 20,
          "correct": 18,
          "accuracy": 0.9,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9,
          "cause_accuracy": 1.0
        },
        "visual_cues": {
          "count": 15,
          "correct": 8,
          "accuracy": 0.5333333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5333333333333333,
          "cause_accuracy": 0.8
        },
        "vocal_cues": {
          "count": 13,
          "correct": 12,
          "accuracy": 0.9230769230769231,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9230769230769231,
          "cause_accuracy": 1.0
        }
      },
      "question_types": {},
      "auxiliary_vote": {
        "questions": 200,
        "correct": 144,
        "accuracy": 0.72,
        "ties_or_no_answer": 0
      }
    }
  },
  "EA": {
    "zh": {
      "overall": {
        "count": 200,
        "correct": 146,
        "accuracy": 0.73,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": null,
        "cause_accuracy": null
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 146,
          "accuracy": 0.73,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.73,
      "sample_std_accuracy": null,
      "categories": {
        "Personal-Others": {
          "count": 50,
          "correct": 35,
          "accuracy": 0.7,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Personal-Self": {
          "count": 50,
          "correct": 40,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Others": {
          "count": 50,
          "correct": 34,
          "accuracy": 0.68,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Self": {
          "count": 50,
          "correct": 37,
          "accuracy": 0.74,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "fine_categories": {},
      "question_types": {
        "Action": {
          "count": 100,
          "correct": 75,
          "accuracy": 0.75,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 100,
          "correct": 71,
          "accuracy": 0.71,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "auxiliary_vote": {
        "questions": 200,
        "correct": 146,
        "accuracy": 0.73,
        "ties_or_no_answer": 0
      }
    },
    "en": {
      "overall": {
        "count": 200,
        "correct": 151,
        "accuracy": 0.755,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": null,
        "cause_accuracy": null
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 151,
          "accuracy": 0.755,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.755,
      "sample_std_accuracy": null,
      "categories": {
        "Personal-Others": {
          "count": 50,
          "correct": 36,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Personal-Self": {
          "count": 50,
          "correct": 40,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Others": {
          "count": 50,
          "correct": 37,
          "accuracy": 0.74,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Self": {
          "count": 50,
          "correct": 38,
          "accuracy": 0.76,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "fine_categories": {},
      "question_types": {
        "Action": {
          "count": 100,
          "correct": 73,
          "accuracy": 0.73,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 100,
          "correct": 78,
          "accuracy": 0.78,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "auxiliary_vote": {
        "questions": 200,
        "correct": 151,
        "accuracy": 0.755,
        "ties_or_no_answer": 0
      }
    }
  }
}
```

## 运行配置与限制

```json
{
  "script_version": "1.0.2",
  "model_version": "unreported",
  "harness_version": "unreported",
  "seed": 42,
  "cot": false,
  "shuffle_options": false,
  "context_policy": "unique user per trial; clear and verify before every attempt",
  "protocol_differences": [
    "official system instruction carried in user content",
    "platform model/generation parameters are not fixed by this client",
    "three repeats are saved/scored separately; plurality is auxiliary",
    "duplicate JSON keys rejected; invalid format is not retried for a better answer"
  ]
}
```

所有样本/错误和请求证据保存在plan.json、responses.jsonl、badcases.jsonl、trials/；输入/提示词/代码及官方来源在snapshot/和manifest.json。未自动公开样本或提交榜单。
