# 效率小样本评测

智能体：1030；bench：tombench；并发：4。无自动重试。

仅代表本次样本，P95不能作为稳定生产结论。传输成功与答题正确分开。

```json
{
  "overall": {
    "selected_cases": 10,
    "chat_attempts": 10,
    "setup_failures": 0,
    "successful_chats": 10,
    "failed_chats": 0,
    "success_rate": 1.0,
    "first_text": {
      "n": 10,
      "p50_seconds": 1.2941005419997964,
      "p95_seconds": 2.0061468738482287
    },
    "complete": {
      "n": 10,
      "p50_seconds": 1.3365924464997079,
      "p95_seconds": 2.028343241646871
    },
    "successful_and_first_text_within": {
      "1": 0.1,
      "2": 0.9,
      "3": 1.0,
      "5": 1.0
    },
    "text_gaps": {
      "scope": "successful requests only; each request contributes one maximum",
      "measured_requests": 10,
      "requests_with_at_least_two_text_events": 10,
      "single_text_event_requests": 0,
      "max_gap_p50_seconds": 0.00011471800280560274,
      "max_gap_p95_seconds": 0.029317262451149847,
      "max_gap_seconds": 0.04014576500048861,
      "requests_exceeding_gap": {
        "0.5": 0,
        "1": 0,
        "2": 0
      },
      "tail_wait_p50_seconds": 0.021969510498820455,
      "tail_wait_p95_seconds": 0.023405722949792106
    },
    "answer_format_valid": 10,
    "correct_answers": 8
  },
  "by_group": {
    "zh": {
      "selected_cases": 5,
      "chat_attempts": 5,
      "setup_failures": 0,
      "successful_chats": 5,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 5,
        "p50_seconds": 1.1456629259992042,
        "p95_seconds": 2.059562775598897
      },
      "complete": {
        "n": 5,
        "p50_seconds": 1.1674374710019038,
        "p95_seconds": 2.0816664773970843
      },
      "successful_and_first_text_within": {
        "1": 0.2,
        "2": 0.8,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 5,
        "requests_with_at_least_two_text_events": 5,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.00010955800098599866,
        "max_gap_p95_seconds": 0.00011530000265338458,
        "max_gap_seconds": 0.00011568800255190581,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.021689116998459212,
        "tail_wait_p95_seconds": 0.022140689199295592
      },
      "answer_format_valid": 5,
      "correct_answers": 3
    },
    "en": {
      "selected_cases": 5,
      "chat_attempts": 5,
      "setup_failures": 0,
      "successful_chats": 5,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 5,
        "p50_seconds": 1.3542288019998523,
        "p95_seconds": 1.584264431399788
      },
      "complete": {
        "n": 5,
        "p50_seconds": 1.4165554239989433,
        "p95_seconds": 1.6216578026003845
      },
      "successful_and_first_text_within": {
        "1": 0.0,
        "2": 1.0,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 5,
        "requests_with_at_least_two_text_events": 5,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.015964948001055745,
        "max_gap_p95_seconds": 0.035333097200782496,
        "max_gap_seconds": 0.04014576500048861,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.022469950999948196,
        "tail_wait_p95_seconds": 0.023792815198976313
      },
      "answer_format_valid": 5,
      "correct_answers": 5
    }
  }
}
```
