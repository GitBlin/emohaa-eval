# EmoBench 独立评测脚本

入口 `evaluate_emobench.py`；独立网络模块 `emobench_api.py`。不依赖或导入ToMBench评测脚本，不修改已有ToMBench结果。Python 3.9+、requests即可，CPU运行，不需要本地GPU。官方YAML已转换为JSON配置并保留原文件，运行时不需要PyYAML、torch、langchain。

## 数据介绍与核对

EmoBench来自ACL 2024论文，评估情绪理解与情绪应用，不仅是简单情感分类。

| 任务 | 场景数（不重复计语言） | 中英文记录 | 题目与选项 | 主评分 |
|---|---:|---:|---|---|
| EU Emotional Understanding，情绪理解 | 200 | 中文200+英文200 | 给场景和人物，同时选择最终情绪（6选1）和原因（4选1） | 两项都正确才算该题正确 |
| EA Emotional Application，情绪应用 | 200 | 中文200+英文200 | 给场景和人物，选最有效动作Action或回应Response（4选1） | 所选动作或回应与标注一致 |
| 合计 | 400 | 800 | 每条EU同时包含两个子问题 | EU和EA分开汇报 |

EU按英文场景计：复杂情绪49、个人信念/经历56、情绪线索28、视角采择67。EA为Personal-Others、Social-Others、Personal-Self、Social-Self四组，各50个场景，每组含Action/Response题型。中文有相应的语言记录，语言字段已存于JSONL中，不是运行时翻译。

本地Emobench/EA.jsonl与EU.jsonl已逐记录核对，与本次获取的作者官方GitHub data/EA.jsonl、data/EU.jsonl一致。所有label都唯一对应某个选项；任务内qid与language组合无重复，中英文qid成对。

来源：

- 作者仓库：https://github.com/Sahandfer/EmoBench
- 官方评分：https://github.com/Sahandfer/EmoBench/blob/master/src/data.py
- 官方提示词：https://github.com/Sahandfer/EmoBench/blob/master/src/configs/prompts.yaml
- 官方回答格式：https://github.com/Sahandfer/EmoBench/blob/master/src/configs/response.yaml
- 数据卡：https://huggingface.co/datasets/SahandSab/EmoBench
- 论文：https://aclanthology.org/2024.acl-long.326/

官方来源文件与Git blob SHA在emobench_official/provenance.json；MIT许可证一并保存。该目录的model.py、data.py等是核对留档的上游源文件，本客户端不执行它们，也不依赖其深度学习包。

## 默认评测口径

默认EU+EA、中英文、每条语言样本3次：200场景×2任务×2语言×3次=2400个请求试次。EU一次请求包含两个问题，不分两次询问，避免给第二问泄露第一问标准答案。

默认保留官方选项顺序，使用官方系统说明、任务提示词及JSON输出格式。EU输出answer_q1和answer_q2，EA输出answer。每轮记录原始回复和答案映射；官方字母精确比较，不从长解释或裸字母猜答案。官方parse_json_response同样要求JSON；本实现进一步拒绝重复JSON键和多段JSON。

每任务每语言分别报告：各轮准确率、重复均值、样本标准差、类别、EU细分类或EA题型。EU情绪单项和原因单项仅作诊断，不替代双正确主分。投票是额外结果，EU按完整(情绪,原因)答案对投票，不分别拼接两个多数选项；并列或无票计错。主成绩是独立各轮与均值，不把投票成绩混成官方主分。

各试次独立用户、独立Session/Token。答题前清理上下文，核验当前会话无旧user/role消息，验证失败不发送题目；答题后再次检查只有1条提问与1条回复。多任务/语言随机交错调度，但输入计划与seed冻结。

与作者原始模型调用的差异：本平台接口只能将官方系统说明放入用户消息；后台模型、温度等无法由客户端设置（作者API示例temperature=0.6）；每条样本独立用户和清理；三个重复显式执行并留档。原上游main.py虽有iter_num参数，但所核对调用路径未使用它实现三次循环。本脚本不宣称完全复现论文同配置，也不会自动提交榜单。--shuffle-options是额外实验，默认关闭。

## 运行命令

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt

# 查看参数
python3 bench/evaluate_emobench.py --help

# 离线准备全量2400个输入，不调用平台
python3 bench/evaluate_emobench.py --dry-run

# 小规模真实试跑：每任务每语言8条×3次=96次
python3 -u bench/evaluate_emobench.py \
  --bot-id 1030 --limit 8 --tasks EU EA --languages zh en \
  --repeats 3 --workers 32 --credentials-module "$PWD/bot_chat_client.py"

# 前台双语全量：2400次
python3 -u bench/evaluate_emobench.py \
  --bot-id 1030 --limit 0 --tasks EU EA --languages zh en \
  --repeats 3 --workers 32 --interval 0 --summary-every 200 \
  --max-attempts 2 --timeout 60 --credentials-module "$PWD/bot_chat_client.py"

# 后台全量：和前台命令二选一
mkdir -p "bench/EmoBench_李言老师-bench测试_1030/logs"
nohup python3 -u bench/evaluate_emobench.py \
  --bot-id 1030 --limit 0 --tasks EU EA --languages zh en \
  --repeats 3 --workers 32 --interval 0 --summary-every 200 \
  --max-attempts 2 --timeout 60 --credentials-module "$PWD/bot_chat_client.py" \
  > "bench/EmoBench_李言老师-bench测试_1030/logs/EmoBench_1030_$(date +%Y%m%d_%H%M%S).log" 2>&1 &

# 只测EU英文，每题一次，共200次
python3 -u bench/evaluate_emobench.py --tasks EU --languages en --repeats 1

# 离线回归测试
python3 bench/test_evaluate_emobench.py

# 查看后台日志，替换实际文件名
tail -f bench/EmoBench_李言老师-bench测试_1030/logs/实际文件.log

# 停止派发，等待在途结果保存；替换实际PID
kill -TERM 实际PID

# 恢复运行：替换日志首行的RUN_DIR，必须用当次快照脚本
python3 -u /实际RUN_DIR/snapshot/evaluate_emobench.py --resume /实际RUN_DIR

# 仅重建报告，不联网；运行中勿对同目录同时执行
python3 /实际RUN_DIR/snapshot/evaluate_emobench.py --report-only /实际RUN_DIR
```

当前新凭证botId=1030。凭证优先级：LINGX_API_KEY/LINGX_API_SECRET环境变量 > --credentials-module中的DEFAULT_API_KEY/SECRET。不要用旧Lingx凭证模块替换本项目新凭证；环境变量如果仍指向旧凭证会导致权限错误。认证密钥和Token不写入运行归档。

## 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| --tasks | EU EA | 可仅EU或EA |
| --languages | zh en | 可仅中文或英文 |
| --limit | 0 | 每任务每语言的场景数量，0=全部；抽样时中英文选同一qid |
| --repeats | 3 | 每条语言样本的独立重复次数 |
| --workers | 32 | 在途试次上限；不等同于每秒请求数 |
| --seed | 42 | 抽样、调度及可选选项重排种子 |
| --shuffle-options | 关闭 | 额外的选项敏感性实验，默认遵循原顺序 |
| --cot | 关闭 | 使用官方推理版JSON提示词 |
| --interval | 0 | 每个worker试次结束后的间隔，非全局限速 |
| --timeout | 60 | 网络读取超时，连接超时10秒 |
| --max-attempts | 2 | 认证、网络、协议失败最多尝试次数；答错或无效格式不重试 |
| --max-consecutive-errors | 5 | 连续最终接口失败触发停止派发，在途任务保存后退出 |
| --summary-every | 200 | 每200个结果刷新汇总，逐题result.json即时保存 |
| --bot-id | 1030 | 智能体ID |
| --bot-name | 李言老师-bench测试 | 记录名称 |
| --model-version / --harness-version | unreported | 记录后台版本；不改变服务端部署 |
| --base-url | LINGX_BASE_URL或https://www.ai-role.cn | 平台地址 |
| --credentials-module | 项目根bot_chat_client.py | 凭证模块路径，环境变量优先 |
| --data-dir | bench/Emobench | 必须包含选定任务的EU.jsonl/EA.jsonl |
| --output-dir | bench/<EmoBench_智能体名称_ID> | 每次创建带榜单、智能体名称和ID前缀的独立运行目录 |
| --insecure | 关闭 | 显式关闭TLS验证；正常使用无需开启 |
| --dry-run | 关闭 | 准备输入和快照，不调用API |
| --resume | 无 | 恢复未完成试次，使用原manifest配置 |
| --report-only | 无 | 离线重建报告 |

恢复会跳过已保存的result.json，包括已记录的最终失败；在途被打断且未落盘的试次重新发送并新增attempt目录。重试不是新的独立重复，不额外计入分母。一个运行目录有进程锁，避免双进程恢复互相覆盖。

## 全部留档

| 文件 | 内容 |
|---|---|
| manifest.json | 日期、版本、全部配置、任务/语言/重复、环境版本、官方源SHA及代码/数据哈希 |
| plan.json | 所有题目原文、标注、选项映射和实际提示词 |
| data_audit.json | 各任务语言数量、分类数量和校验状态 |
| snapshot/ | 独立评测代码、网络模块、原始题库、官方提示词、格式与许可证 |
| sessions/ | 预检机器人列表；不保存认证响应和Token |
| trials/<trial_id>/result.json | 每次答题的原始回复、分项判定、耗时和所有尝试 |
| trials/<trial_id>/attempt_*/ | 清理/历史/聊天请求、原始HTTP响应、SSE事件与异常阶段 |
| responses.jsonl | 全部已完成试次 |
| badcases.jsonl | 错误、无效、格式不符及上下文审计异常，附完整题目和证据路径 |
| official_format/<EU或EA>/round_N.jsonl | 使用原选项字母、按官方字段导出；每轮双语400条，每语言200条；该导出不是正式提交记录 |
| summary.json | EU/EA、中英文分别的总分、各轮、类别、细分类、题型和辅助投票 |
| question_votes.json | 完整答案对/单答案的投票明细 |
| review_queue.json | 待人工核查的错误列表；未自动指定负责人或日期 |
| report.md | 可读报告和完整分类统计 |
| execution_log.jsonl | 开始、完成、中断和致命错误 |
| artifact_index.json | 归档文件哈希索引 |

主分定位：summary.json → task_language → EU/EA → zh/en → rounds及mean_accuracy；EU overall.emotion_accuracy/cause_accuracy仅为辅助。
完成验收：run_status=complete、planned_trials=completed_trials=2400，并检查request_errors、invalid_answers及context_after_audit_errors。invalid_answers不一定为0，格式违规必须如实计错，不能为了更高分随意放宽解析。

## 已验证范围

8项离线测试通过：EU双正确、A-F及选项映射、JSON拒绝与EA评分、清理失败阻断、无效回答不重试、认证失败留档并重试、2400条完整输入与快照防篡改、并发独立用户与恢复不重发、EU整对投票/官方导出（部分在同一用例中验证）。
2026-11-11真实试跑96次，32并发：全部请求完成，0接口失败、0上下文审计错误；95条有效JSON，1条裸字母C按官方JSON格式计无效。试跑不是全量成绩，不能依据这些样本调提示词后再将同题宣称为未接触holdout。该简单试跑原始记录已按用户要求清除；正式全量的全部原始记录保留。
目前没有自动启动2400次全量、公开失败样本或提交官方榜单。

## 结果目录迁移与正式结果

结果根目录为`bench/EmoBench_李言老师-bench测试_1030/`，每次运行子目录也以`EmoBench_李言老师-bench测试_1030_`开头。正式全量2400次结果现位于：`/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师-bench测试_1030/EmoBench_李言老师-bench测试_1030_20261111T040112Z_ced181e6`。原始归档文件和哈希均保持不变，后台日志另存console.log；历史小规模与空准备记录已清除。迁移清单见bench/结果目录迁移与清理记录.json。源数据目录Emobench及官方源文件emobench_official保留原名。
