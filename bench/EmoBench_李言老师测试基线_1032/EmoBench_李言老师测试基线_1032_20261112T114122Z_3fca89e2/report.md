# EmoBench 独立评测报告

状态：complete；完成800/800；botId=1032。

| 任务 | 语言 | 答对/次数 | 三轮/多轮均值 | 样本标准差（百分点） | EU情绪准确率 | EU原因准确率 |
|---|---|---:|---:|---:|---:|---:|
| EU | zh | 130/200 | 65.00% | N/A | 66.50% | 85.00% |
| EU | en | 142/200 | 71.00% | N/A | 75.50% | 86.00% |
| EA | zh | 149/200 | 74.50% | N/A | N/A | N/A |
| EA | en | 148/200 | 74.00% | N/A | N/A | N/A |

| 任务 | 语言 | 轮次 | 答对/次数 | 准确率 |
|---|---|---:|---:|---:|
| EU | zh | 1 | 130/200 | 65.00% |
| EU | en | 1 | 142/200 | 71.00% |
| EA | zh | 1 | 149/200 | 74.50% |
| EA | en | 1 | 148/200 | 74.00% |

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
        "correct": 130,
        "accuracy": 0.65,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": 0.665,
        "cause_accuracy": 0.85
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 130,
          "accuracy": 0.65,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.665,
          "cause_accuracy": 0.85
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.65,
      "sample_std_accuracy": null,
      "categories": {
        "complex_emotions": {
          "count": 49,
          "correct": 42,
          "accuracy": 0.8571428571428571,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8775510204081632,
          "cause_accuracy": 0.9591836734693877
        },
        "emotional_cues": {
          "count": 28,
          "correct": 20,
          "accuracy": 0.7142857142857143,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7142857142857143,
          "cause_accuracy": 0.8571428571428571
        },
        "personal_beliefs_and_experiences": {
          "count": 56,
          "correct": 31,
          "accuracy": 0.5535714285714286,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5892857142857143,
          "cause_accuracy": 0.875
        },
        "perspective_taking": {
          "count": 67,
          "correct": 37,
          "accuracy": 0.5522388059701493,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5522388059701493,
          "cause_accuracy": 0.746268656716418
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 23,
          "correct": 12,
          "accuracy": 0.5217391304347826,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5652173913043478,
          "cause_accuracy": 0.9130434782608695
        },
        "emotion_transition": {
          "count": 15,
          "correct": 14,
          "accuracy": 0.9333333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9333333333333333,
          "cause_accuracy": 1.0
        },
        "false_belief": {
          "count": 26,
          "correct": 12,
          "accuracy": 0.46153846153846156,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.46153846153846156,
          "cause_accuracy": 0.6153846153846154
        },
        "faux_pas": {
          "count": 25,
          "correct": 16,
          "accuracy": 0.64,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.64,
          "cause_accuracy": 0.88
        },
        "mixture_of_emotions": {
          "count": 14,
          "correct": 11,
          "accuracy": 0.7857142857142857,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7857142857142857,
          "cause_accuracy": 1.0
        },
        "persona": {
          "count": 17,
          "correct": 9,
          "accuracy": 0.5294117647058824,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5882352941176471,
          "cause_accuracy": 0.7058823529411765
        },
        "sentimental_value": {
          "count": 16,
          "correct": 10,
          "accuracy": 0.625,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.625,
          "cause_accuracy": 1.0
        },
        "strange_story": {
          "count": 16,
          "correct": 9,
          "accuracy": 0.5625,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5625,
          "cause_accuracy": 0.75
        },
        "unexpected_outcome": {
          "count": 20,
          "correct": 17,
          "accuracy": 0.85,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.9,
          "cause_accuracy": 0.9
        },
        "visual_cues": {
          "count": 15,
          "correct": 10,
          "accuracy": 0.6666666666666666,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6666666666666666,
          "cause_accuracy": 0.8
        },
        "vocal_cues": {
          "count": 13,
          "correct": 10,
          "accuracy": 0.7692307692307693,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7692307692307693,
          "cause_accuracy": 0.9230769230769231
        }
      },
      "question_types": {},
      "auxiliary_vote": {
        "questions": 200,
        "correct": 130,
        "accuracy": 0.65,
        "ties_or_no_answer": 0
      }
    },
    "en": {
      "overall": {
        "count": 200,
        "correct": 142,
        "accuracy": 0.71,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": 0.755,
        "cause_accuracy": 0.86
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 142,
          "accuracy": 0.71,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.755,
          "cause_accuracy": 0.86
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.71,
      "sample_std_accuracy": null,
      "categories": {
        "complex_emotions": {
          "count": 49,
          "correct": 40,
          "accuracy": 0.8163265306122449,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8979591836734694,
          "cause_accuracy": 0.9183673469387755
        },
        "emotional_cues": {
          "count": 28,
          "correct": 22,
          "accuracy": 0.7857142857142857,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7857142857142857,
          "cause_accuracy": 0.9285714285714286
        },
        "personal_beliefs_and_experiences": {
          "count": 56,
          "correct": 38,
          "accuracy": 0.6785714285714286,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7321428571428571,
          "cause_accuracy": 0.8928571428571429
        },
        "perspective_taking": {
          "count": 67,
          "correct": 42,
          "accuracy": 0.6268656716417911,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6567164179104478,
          "cause_accuracy": 0.7611940298507462
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 23,
          "correct": 16,
          "accuracy": 0.6956521739130435,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7391304347826086,
          "cause_accuracy": 0.9565217391304348
        },
        "emotion_transition": {
          "count": 15,
          "correct": 13,
          "accuracy": 0.8666666666666667,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 1.0,
          "cause_accuracy": 0.8666666666666667
        },
        "false_belief": {
          "count": 26,
          "correct": 16,
          "accuracy": 0.6153846153846154,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6153846153846154,
          "cause_accuracy": 0.8076923076923077
        },
        "faux_pas": {
          "count": 25,
          "correct": 15,
          "accuracy": 0.6,
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
          "correct": 10,
          "accuracy": 0.625,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6875,
          "cause_accuracy": 0.9375
        },
        "strange_story": {
          "count": 16,
          "correct": 11,
          "accuracy": 0.6875,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6875,
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
          "correct": 10,
          "accuracy": 0.6666666666666666,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6666666666666666,
          "cause_accuracy": 0.8666666666666667
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
        "correct": 142,
        "accuracy": 0.71,
        "ties_or_no_answer": 0
      }
    }
  },
  "EA": {
    "zh": {
      "overall": {
        "count": 200,
        "correct": 149,
        "accuracy": 0.745,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": null,
        "cause_accuracy": null
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 149,
          "accuracy": 0.745,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.745,
      "sample_std_accuracy": null,
      "categories": {
        "Personal-Others": {
          "count": 50,
          "correct": 33,
          "accuracy": 0.66,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Personal-Self": {
          "count": 50,
          "correct": 37,
          "accuracy": 0.74,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Others": {
          "count": 50,
          "correct": 40,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Self": {
          "count": 50,
          "correct": 39,
          "accuracy": 0.78,
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
          "correct": 77,
          "accuracy": 0.77,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 100,
          "correct": 72,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "auxiliary_vote": {
        "questions": 200,
        "correct": 149,
        "accuracy": 0.745,
        "ties_or_no_answer": 0
      }
    },
    "en": {
      "overall": {
        "count": 200,
        "correct": 148,
        "accuracy": 0.74,
        "request_errors": 0,
        "invalid_answers": 0,
        "strict_format_rate": 1.0,
        "emotion_accuracy": null,
        "cause_accuracy": null
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 148,
          "accuracy": 0.74,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 1,
      "mean_accuracy": 0.74,
      "sample_std_accuracy": null,
      "categories": {
        "Personal-Others": {
          "count": 50,
          "correct": 34,
          "accuracy": 0.68,
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
          "correct": 36,
          "accuracy": 0.72,
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
          "correct": 72,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 100,
          "correct": 76,
          "accuracy": 0.76,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "auxiliary_vote": {
        "questions": 200,
        "correct": 148,
        "accuracy": 0.74,
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
