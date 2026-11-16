# EmoBench 独立评测报告

状态：complete；完成2400/2400；botId=1030。

| 任务 | 语言 | 答对/次数 | 三轮/多轮均值 | 样本标准差（百分点） | EU情绪准确率 | EU原因准确率 |
|---|---|---:|---:|---:|---:|---:|
| EU | zh | 337/600 | 56.17% | 0.5773502691896198 | 58.83% | 78.33% |
| EU | en | 371/600 | 61.83% | 1.0408329997330674 | 64.17% | 80.50% |
| EA | zh | 447/600 | 74.50% | 2.1794494717703388 | N/A | N/A |
| EA | en | 442/600 | 73.67% | 1.7559422921421246 | N/A | N/A |

| 任务 | 语言 | 轮次 | 答对/次数 | 准确率 |
|---|---|---:|---:|---:|
| EU | zh | 1 | 111/200 | 55.50% |
| EU | zh | 2 | 113/200 | 56.50% |
| EU | zh | 3 | 113/200 | 56.50% |
| EU | en | 1 | 123/200 | 61.50% |
| EU | en | 2 | 122/200 | 61.00% |
| EU | en | 3 | 126/200 | 63.00% |
| EA | zh | 1 | 151/200 | 75.50% |
| EA | zh | 2 | 144/200 | 72.00% |
| EA | zh | 3 | 152/200 | 76.00% |
| EA | en | 1 | 151/200 | 75.50% |
| EA | en | 2 | 147/200 | 73.50% |
| EA | en | 3 | 144/200 | 72.00% |

EU主成绩要求情绪和原因同时正确；情绪/原因分数只是辅助诊断。EA主成绩要求所选动作/回应正确。全局合并准确率不是官方EU/EA分数的替代。

默认不打乱选项，使用官方提示词和JSON字段；本客户端将系统指令合并进用户消息，后台生成参数无法锁定，不宣称完全复现论文设置。

多轮按次平均为主成绩；投票为辅助成绩，EU按完整答案对投票而非分别拼接情绪/原因。并列计错。

## 完整分类、轮次和投票

```json
{
  "EU": {
    "zh": {
      "overall": {
        "count": 600,
        "correct": 337,
        "accuracy": 0.5616666666666666,
        "request_errors": 0,
        "invalid_answers": 1,
        "strict_format_rate": 0.9983333333333333,
        "emotion_accuracy": 0.5883333333333334,
        "cause_accuracy": 0.7833333333333333
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 111,
          "accuracy": 0.555,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.59,
          "cause_accuracy": 0.785
        },
        "2": {
          "count": 200,
          "correct": 113,
          "accuracy": 0.565,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.995,
          "emotion_accuracy": 0.585,
          "cause_accuracy": 0.8
        },
        "3": {
          "count": 200,
          "correct": 113,
          "accuracy": 0.565,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.59,
          "cause_accuracy": 0.765
        }
      },
      "complete_rounds": 3,
      "mean_accuracy": 0.5616666666666666,
      "sample_std_accuracy": 0.005773502691896198,
      "categories": {
        "complex_emotions": {
          "count": 147,
          "correct": 111,
          "accuracy": 0.7551020408163265,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8027210884353742,
          "cause_accuracy": 0.8775510204081632
        },
        "emotional_cues": {
          "count": 84,
          "correct": 51,
          "accuracy": 0.6071428571428571,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6071428571428571,
          "cause_accuracy": 0.8452380952380952
        },
        "personal_beliefs_and_experiences": {
          "count": 168,
          "correct": 79,
          "accuracy": 0.47023809523809523,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5059523809523809,
          "cause_accuracy": 0.8214285714285714
        },
        "perspective_taking": {
          "count": 201,
          "correct": 96,
          "accuracy": 0.47761194029850745,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9950248756218906,
          "emotion_accuracy": 0.4925373134328358,
          "cause_accuracy": 0.6567164179104478
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 69,
          "correct": 28,
          "accuracy": 0.4057971014492754,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.4492753623188406,
          "cause_accuracy": 0.855072463768116
        },
        "emotion_transition": {
          "count": 45,
          "correct": 36,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8,
          "cause_accuracy": 0.8888888888888888
        },
        "false_belief": {
          "count": 78,
          "correct": 36,
          "accuracy": 0.46153846153846156,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9871794871794872,
          "emotion_accuracy": 0.46153846153846156,
          "cause_accuracy": 0.5641025641025641
        },
        "faux_pas": {
          "count": 75,
          "correct": 37,
          "accuracy": 0.49333333333333335,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5066666666666667,
          "cause_accuracy": 0.8
        },
        "mixture_of_emotions": {
          "count": 42,
          "correct": 26,
          "accuracy": 0.6190476190476191,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6904761904761905,
          "cause_accuracy": 0.8809523809523809
        },
        "persona": {
          "count": 51,
          "correct": 18,
          "accuracy": 0.35294117647058826,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.4117647058823529,
          "cause_accuracy": 0.6470588235294118
        },
        "sentimental_value": {
          "count": 48,
          "correct": 33,
          "accuracy": 0.6875,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6875,
          "cause_accuracy": 0.9583333333333334
        },
        "strange_story": {
          "count": 48,
          "correct": 23,
          "accuracy": 0.4791666666666667,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5208333333333334,
          "cause_accuracy": 0.5833333333333334
        },
        "unexpected_outcome": {
          "count": 60,
          "correct": 49,
          "accuracy": 0.8166666666666667,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8833333333333333,
          "cause_accuracy": 0.8666666666666667
        },
        "visual_cues": {
          "count": 45,
          "correct": 24,
          "accuracy": 0.5333333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5333333333333333,
          "cause_accuracy": 0.7111111111111111
        },
        "vocal_cues": {
          "count": 39,
          "correct": 27,
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
        "correct": 114,
        "accuracy": 0.57,
        "ties_or_no_answer": 6
      }
    },
    "en": {
      "overall": {
        "count": 600,
        "correct": 371,
        "accuracy": 0.6183333333333333,
        "request_errors": 0,
        "invalid_answers": 3,
        "strict_format_rate": 0.995,
        "emotion_accuracy": 0.6416666666666667,
        "cause_accuracy": 0.805
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 123,
          "accuracy": 0.615,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.995,
          "emotion_accuracy": 0.635,
          "cause_accuracy": 0.815
        },
        "2": {
          "count": 200,
          "correct": 122,
          "accuracy": 0.61,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.995,
          "emotion_accuracy": 0.635,
          "cause_accuracy": 0.805
        },
        "3": {
          "count": 200,
          "correct": 126,
          "accuracy": 0.63,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.995,
          "emotion_accuracy": 0.655,
          "cause_accuracy": 0.795
        }
      },
      "complete_rounds": 3,
      "mean_accuracy": 0.6183333333333333,
      "sample_std_accuracy": 0.010408329997330674,
      "categories": {
        "complex_emotions": {
          "count": 147,
          "correct": 115,
          "accuracy": 0.782312925170068,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9931972789115646,
          "emotion_accuracy": 0.8231292517006803,
          "cause_accuracy": 0.9047619047619048
        },
        "emotional_cues": {
          "count": 84,
          "correct": 55,
          "accuracy": 0.6547619047619048,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9880952380952381,
          "emotion_accuracy": 0.6547619047619048,
          "cause_accuracy": 0.8095238095238095
        },
        "personal_beliefs_and_experiences": {
          "count": 168,
          "correct": 102,
          "accuracy": 0.6071428571428571,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.625,
          "cause_accuracy": 0.875
        },
        "perspective_taking": {
          "count": 201,
          "correct": 99,
          "accuracy": 0.4925373134328358,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9950248756218906,
          "emotion_accuracy": 0.5174129353233831,
          "cause_accuracy": 0.6716417910447762
        }
      },
      "fine_categories": {
        "cultural_value": {
          "count": 69,
          "correct": 39,
          "accuracy": 0.5652173913043478,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5652173913043478,
          "cause_accuracy": 0.9420289855072463
        },
        "emotion_transition": {
          "count": 45,
          "correct": 38,
          "accuracy": 0.8444444444444444,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8888888888888888,
          "cause_accuracy": 0.8666666666666667
        },
        "false_belief": {
          "count": 78,
          "correct": 39,
          "accuracy": 0.5,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9871794871794872,
          "emotion_accuracy": 0.5,
          "cause_accuracy": 0.7435897435897436
        },
        "faux_pas": {
          "count": 75,
          "correct": 42,
          "accuracy": 0.56,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.6266666666666667,
          "cause_accuracy": 0.6666666666666666
        },
        "mixture_of_emotions": {
          "count": 42,
          "correct": 27,
          "accuracy": 0.6428571428571429,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.7142857142857143,
          "cause_accuracy": 0.8571428571428571
        },
        "persona": {
          "count": 51,
          "correct": 27,
          "accuracy": 0.5294117647058824,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.5882352941176471,
          "cause_accuracy": 0.6862745098039216
        },
        "sentimental_value": {
          "count": 48,
          "correct": 36,
          "accuracy": 0.75,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.75,
          "cause_accuracy": 0.9791666666666666
        },
        "strange_story": {
          "count": 48,
          "correct": 18,
          "accuracy": 0.375,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.375,
          "cause_accuracy": 0.5625
        },
        "unexpected_outcome": {
          "count": 60,
          "correct": 50,
          "accuracy": 0.8333333333333334,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9833333333333333,
          "emotion_accuracy": 0.85,
          "cause_accuracy": 0.9666666666666667
        },
        "visual_cues": {
          "count": 45,
          "correct": 21,
          "accuracy": 0.4666666666666667,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9777777777777777,
          "emotion_accuracy": 0.4666666666666667,
          "cause_accuracy": 0.6444444444444445
        },
        "vocal_cues": {
          "count": 39,
          "correct": 34,
          "accuracy": 0.8717948717948718,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": 0.8717948717948718,
          "cause_accuracy": 1.0
        }
      },
      "question_types": {},
      "auxiliary_vote": {
        "questions": 200,
        "correct": 128,
        "accuracy": 0.64,
        "ties_or_no_answer": 0
      }
    }
  },
  "EA": {
    "zh": {
      "overall": {
        "count": 600,
        "correct": 447,
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
          "correct": 151,
          "accuracy": 0.755,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "2": {
          "count": 200,
          "correct": 144,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "3": {
          "count": 200,
          "correct": 152,
          "accuracy": 0.76,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 3,
      "mean_accuracy": 0.745,
      "sample_std_accuracy": 0.021794494717703387,
      "categories": {
        "Personal-Others": {
          "count": 150,
          "correct": 105,
          "accuracy": 0.7,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Personal-Self": {
          "count": 150,
          "correct": 120,
          "accuracy": 0.8,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Others": {
          "count": 150,
          "correct": 106,
          "accuracy": 0.7066666666666667,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Self": {
          "count": 150,
          "correct": 116,
          "accuracy": 0.7733333333333333,
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
          "count": 300,
          "correct": 226,
          "accuracy": 0.7533333333333333,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 300,
          "correct": 221,
          "accuracy": 0.7366666666666667,
          "request_errors": 0,
          "invalid_answers": 0,
          "strict_format_rate": 1.0,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "auxiliary_vote": {
        "questions": 200,
        "correct": 152,
        "accuracy": 0.76,
        "ties_or_no_answer": 1
      }
    },
    "en": {
      "overall": {
        "count": 600,
        "correct": 442,
        "accuracy": 0.7366666666666667,
        "request_errors": 0,
        "invalid_answers": 5,
        "strict_format_rate": 0.9916666666666667,
        "emotion_accuracy": null,
        "cause_accuracy": null
      },
      "rounds": {
        "1": {
          "count": 200,
          "correct": 151,
          "accuracy": 0.755,
          "request_errors": 0,
          "invalid_answers": 2,
          "strict_format_rate": 0.99,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "2": {
          "count": 200,
          "correct": 147,
          "accuracy": 0.735,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.995,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "3": {
          "count": 200,
          "correct": 144,
          "accuracy": 0.72,
          "request_errors": 0,
          "invalid_answers": 2,
          "strict_format_rate": 0.99,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "complete_rounds": 3,
      "mean_accuracy": 0.7366666666666667,
      "sample_std_accuracy": 0.017559422921421246,
      "categories": {
        "Personal-Others": {
          "count": 150,
          "correct": 113,
          "accuracy": 0.7533333333333333,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9933333333333333,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Personal-Self": {
          "count": 150,
          "correct": 113,
          "accuracy": 0.7533333333333333,
          "request_errors": 0,
          "invalid_answers": 2,
          "strict_format_rate": 0.9866666666666667,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Others": {
          "count": 150,
          "correct": 107,
          "accuracy": 0.7133333333333334,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9933333333333333,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Social-Self": {
          "count": 150,
          "correct": 109,
          "accuracy": 0.7266666666666667,
          "request_errors": 0,
          "invalid_answers": 1,
          "strict_format_rate": 0.9933333333333333,
          "emotion_accuracy": null,
          "cause_accuracy": null
        }
      },
      "fine_categories": {},
      "question_types": {
        "Action": {
          "count": 300,
          "correct": 213,
          "accuracy": 0.71,
          "request_errors": 0,
          "invalid_answers": 5,
          "strict_format_rate": 0.9833333333333333,
          "emotion_accuracy": null,
          "cause_accuracy": null
        },
        "Response": {
          "count": 300,
          "correct": 229,
          "accuracy": 0.7633333333333333,
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
        "ties_or_no_answer": 1
      }
    }
  }
}
```

## 运行配置与限制

```json
{
  "script_version": "1.0.0",
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
