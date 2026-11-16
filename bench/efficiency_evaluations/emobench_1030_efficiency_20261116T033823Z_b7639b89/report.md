# 效率小样本评测

智能体：1030；bench：emobench；并发：1。无自动重试。

仅代表本次样本，P95不能作为稳定生产结论。传输成功与答题正确分开。

```json
{
  "overall": {
    "selected_cases": 4,
    "chat_attempts": 4,
    "setup_failures": 0,
    "successful_chats": 4,
    "failed_chats": 0,
    "success_rate": 1.0,
    "first_text": {
      "n": 4,
      "p50_seconds": 1.7059110145019076,
      "p95_seconds": 2.1679513499488166
    },
    "complete": {
      "n": 4,
      "p50_seconds": 1.7904811880016496,
      "p95_seconds": 2.2472814626991746
    },
    "successful_and_first_text_within": {
      "1": 0.0,
      "2": 0.75,
      "3": 1.0,
      "5": 1.0
    },
    "text_gaps": {
      "scope": "successful requests only; each request contributes one maximum",
      "measured_requests": 4,
      "requests_with_at_least_two_text_events": 4,
      "single_text_event_requests": 0,
      "max_gap_p50_seconds": 0.03042903599998681,
      "max_gap_p95_seconds": 0.062225124799988395,
      "max_gap_seconds": 0.06730134499957785,
      "requests_exceeding_gap": {
        "0.5": 0,
        "1": 0,
        "2": 0
      },
      "tail_wait_p50_seconds": 0.022310449499855167,
      "tail_wait_p95_seconds": 0.022605957401901834
    },
    "answer_format_valid": 4,
    "correct_answers": 3
  },
  "by_group": {
    "EA_zh": {
      "selected_cases": 1,
      "chat_attempts": 1,
      "setup_failures": 0,
      "successful_chats": 1,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 1,
        "p50_seconds": 1.0747971279997728,
        "p95_seconds": 1.0747971279997728
      },
      "complete": {
        "n": 1,
        "p50_seconds": 1.123909399000695,
        "p95_seconds": 1.123909399000695
      },
      "successful_and_first_text_within": {
        "1": 0.0,
        "2": 1.0,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 1,
        "requests_with_at_least_two_text_events": 1,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.026561050999589497,
        "max_gap_p95_seconds": 0.026561050999589497,
        "max_gap_seconds": 0.026561050999589497,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.02225940499920398,
        "tail_wait_p95_seconds": 0.02225940499920398
      },
      "answer_format_valid": 1,
      "correct_answers": 1
    },
    "EU_zh": {
      "selected_cases": 1,
      "chat_attempts": 1,
      "setup_failures": 0,
      "successful_chats": 1,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 1,
        "p50_seconds": 1.9053445240024303,
        "p95_seconds": 1.9053445240024303
      },
      "complete": {
        "n": 1,
        "p50_seconds": 2.0245054370025173,
        "p95_seconds": 2.0245054370025173
      },
      "successful_and_first_text_within": {
        "1": 0.0,
        "2": 1.0,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 1,
        "requests_with_at_least_two_text_events": 1,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.06730134499957785,
        "max_gap_p95_seconds": 0.06730134499957785,
        "max_gap_seconds": 0.06730134499957785,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.022649098002148094,
        "tail_wait_p95_seconds": 0.022649098002148094
      },
      "answer_format_valid": 1,
      "correct_answers": 0
    },
    "EA_en": {
      "selected_cases": 1,
      "chat_attempts": 1,
      "setup_failures": 0,
      "successful_chats": 1,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 1,
        "p50_seconds": 1.506477505001385,
        "p95_seconds": 1.506477505001385
      },
      "complete": {
        "n": 1,
        "p50_seconds": 1.5564569390007819,
        "p95_seconds": 1.5564569390007819
      },
      "successful_and_first_text_within": {
        "1": 0.0,
        "2": 1.0,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 1,
        "requests_with_at_least_two_text_events": 1,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.02739819499765872,
        "max_gap_p95_seconds": 0.02739819499765872,
        "max_gap_seconds": 0.02739819499765872,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.022361494000506354,
        "tail_wait_p95_seconds": 0.022361494000506354
      },
      "answer_format_valid": 1,
      "correct_answers": 1
    },
    "EU_en": {
      "selected_cases": 1,
      "chat_attempts": 1,
      "setup_failures": 0,
      "successful_chats": 1,
      "failed_chats": 0,
      "success_rate": 1.0,
      "first_text": {
        "n": 1,
        "p50_seconds": 2.214293730998179,
        "p95_seconds": 2.214293730998179
      },
      "complete": {
        "n": 1,
        "p50_seconds": 2.286594878998585,
        "p95_seconds": 2.286594878998585
      },
      "successful_and_first_text_within": {
        "1": 0.0,
        "2": 0.0,
        "3": 1.0,
        "5": 1.0
      },
      "text_gaps": {
        "scope": "successful requests only; each request contributes one maximum",
        "measured_requests": 1,
        "requests_with_at_least_two_text_events": 1,
        "single_text_event_requests": 0,
        "max_gap_p50_seconds": 0.0334598770023149,
        "max_gap_p95_seconds": 0.0334598770023149,
        "max_gap_seconds": 0.0334598770023149,
        "requests_exceeding_gap": {
          "0.5": 0,
          "1": 0,
          "2": 0
        },
        "tail_wait_p50_seconds": 0.022120257999631576,
        "tail_wait_p95_seconds": 0.022120257999631576
      },
      "answer_format_valid": 1,
      "correct_answers": 1
    }
  }
}
```
