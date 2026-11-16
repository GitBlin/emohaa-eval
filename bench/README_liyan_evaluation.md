# ToMBench：李言老师-bench测试（1030）

脚本evaluate_liyan.py；默认中英文，每题3次、32并发，双语全量17160次。结果文件夹统一为“榜单_智能体名称_ID”，内部运行目录也加相同前缀。自定义--output-dir时仅覆盖输出根目录，运行目录仍保留前缀。

## 当前正式结果

- 完成目录：`/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/ToMBench_李言老师-bench测试_1030/ToMBench_李言老师-bench测试_1030_20261111T032603Z_70b9feba`
- 可读报告：上述目录的report.md；Word及完整整理报告在`ToMBench_李言老师-bench测试_1030/reports/`。
- 中文三轮平均78.46%，英文77.38%；全部17160次完成，无接口/上下文审计错误。
- 历史试跑、并发校准和空dry-run目录已按用户要求清除。参数校准摘要保存在reports中，原始试跑证据不再保留。

## 运行命令

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt

# 查询当前凭证可用智能体
python3 bot_chat_client.py --list

# 参数帮助
python3 bench/evaluate_liyan.py --help

# 全量输入离线检查
python3 bench/evaluate_liyan.py --bot-id 1030 --bot-name 李言老师-bench测试 --dry-run

# 小规模测试；会创建新的独立试跑记录
python3 -u bench/evaluate_liyan.py --bot-id 1030 --bot-name 李言老师-bench测试 --limit 8 --languages zh en --repeats 3 --workers 32 --credentials-module "$PWD/bot_chat_client.py"

# 双语全量后台运行；不要重复启动已有的运行
mkdir -p "bench/ToMBench_李言老师-bench测试_1030/logs"
nohup python3 -u bench/evaluate_liyan.py --bot-id 1030 --bot-name 李言老师-bench测试 --limit 0 --languages zh en --repeats 3 --workers 32 --interval 0 --summary-every 200 --max-attempts 2 --timeout 60 --credentials-module "$PWD/bot_chat_client.py" > "bench/ToMBench_李言老师-bench测试_1030/logs/ToMBench_1030_$(date +%Y%m%d_%H%M%S).log" 2>&1 &

# 恢复中断，使用该运行冻结的脚本；替换实际RUN_DIR
python3 -u /实际RUN_DIR/snapshot/evaluate_liyan.py --resume /实际RUN_DIR

# 离线重建汇总，使用冻结脚本
python3 /实际RUN_DIR/snapshot/evaluate_liyan.py --report-only /实际RUN_DIR

# 查看日志/优雅停止（替换实际名称/PID）
tail -f "bench/ToMBench_李言老师-bench测试_1030/logs/实际日志文件.log"
kill -TERM 实际PID

# 离线测试，仅使用自动清理的临时目录
python3 bench/test_evaluate_liyan.py
```

新凭证使用1030。LINGX_API_KEY/LINGX_API_SECRET环境变量优先于凭证模块，运行前确认没有仍指向旧凭证的变量。默认新运行示例路径：`bench/ToMBench_李言老师-bench测试_1030/ToMBench_李言老师-bench测试_1030_<UTC时间>_<随机标识>/`。

## 参数完整说明


| 参数 | 默认值 | 含义 |
|---|---|---|
| --limit | 0 | 0为全量2860题，正数为抽样题数 |
| --repeats | 3 | 每题次数；每次独立打乱选项 |
| --workers | 32 | 同时运行的试次上限 |
| --languages | zh en | 可选zh、en或zh en；双语全量×3为17160次，英文有已记录数据异常，须先核对 |
| --seed | 42 | 抽样和选项重排种子 |
| --cot | 关闭 | 使用原数据仓库CoT模板，可能增加耗时 |
| --interval | 0 | 每个worker完成试次后的间隔秒数，并非全局限速 |
| --max-attempts | 2 | 每试次最多尝试次数，仅接口/协议失败重试；不因答错重试 |
| --timeout | 60 | 网络读取超时秒数；连接超时10秒 |
| --summary-every | 200 | 每完成200次刷新汇总；逐题结果立即保存 |
| --max-consecutive-errors | 5 | 按完成顺序连续最终请求失败达到阈值，停止派发；在途任务等待保存 |
| --credentials-module | ../bot_chat_client.py | 凭证来源；使用当前项目bot_chat_client.py，环境变量优先 |
| --base-url | LINGX_BASE_URL或https://www.ai-role.cn | 平台地址 |
| --user-id | 自动生成 | 运行用户命名空间/预检用户；试次用户由它与trial_id派生；不要跨运行复用 |
| --data-dir | bench/Tombench/data | 题库目录 |
| --output-dir | bench/<ToMBench_智能体名称_ID> | 结果根目录 |
| --model-version | unreported | 记录模型版本，不改变服务端模型 |
| --harness-version | unreported | 记录封装版本，不改变服务端配置 |
| --insecure | 关闭 | 显式关闭证书校验；正常运行不需要 |
| --dry-run | 关闭 | 只准备输入、快照和报告 |
| --resume | 无 | 恢复运行，使用manifest冻结参数；CLI workers等不会覆盖旧配置 |
| --report-only | 无 | 从已有结果重建报告 |
| --help | 无 | 输出帮助 |

目标通过--bot-id选择；新凭证使用1030，脚本默认242保留旧调用兼容。--bot-name用于结果目录命名，正式命令应填写实际智能体名称。温度、top_p、底层模型、服务端记忆开关没有公开可配置参数，不会伪造设置。


## 结果与评分

每试次使用独立用户；每次尝试先清理并检查历史为空，失败则不发送题目。三次独立重排选项，严格提取唯一[[A]]类答案；错误、无效和请求失败计错。投票映射回原选项后统计，并列计错。模型及生成参数由服务端控制。

完整留档：manifest.json、plan.json、snapshot/、trials/、responses.jsonl、badcases.jsonl、question_votes.json、summary.json、review_queue.json、report.md、artifact_index.json。逐题result.json即时保存，汇总每200次刷新。中英文三轮分别汇总；标准差不等于置信区间。

恢复沿用冻结设置和用户映射，跳过已有结果，包括已记录最终失败；仅补未完成项。不得同时有其他进程操作同一运行。

原题Strange Story Task:293英文题目/选项错配，保留原始成绩并提供两种语言排除此题的辅助分数。本地适配成绩未正式提交榜单，后台模型/harness版本仍待提供。保持独立开发集和新holdout，避免用失败样本反复调参后再声称未接触。

## 迁移说明

原始完整运行目录、配置和快照保持原字节，artifact_index.json不重写。旧路径在冻结的manifest、调用日志和代码快照中作为历史事实保留；当前路径见bench/结果目录迁移与清理记录.json。迁移后的console.log是原后台日志。数据源目录Tombench等保留原名。

## 单次双语全量与自定义留档名称

`--repeats 1` 表示每个题目每种语言只运行一次。保留原始智能体 ID 1030 与名称，仅通过独立的 `--archive-name` 修改目录名称。

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt
ARCHIVE_NAME="李言老师full"
python bench/evaluate_liyan.py \
  --bot-id 1030 --bot-name "李言老师-bench测试" \
  --archive-name "$ARCHIVE_NAME" \
  --languages zh en --repeats 1 --workers 32
```

共 2860 × 2 = 5720 个答题试次。新留档目录为 `bench/ToMBench_李言老师full_1030/ToMBench_李言老师full_1030_<UTC时间>_<ID>/`。
`ARCHIVE_NAME` 是 shell 变量，按需修改后通过参数传入；只影响新运行的目录命名及 manifest 中的留档标签，不更改 botId、凭证、实际智能体名称、提示词或评分规则。历史目录不会重命名。空格等路径字符会转为下划线。

仅评中文使用 `--languages zh`，仅评英文使用 `--languages en`，各 2860 个试次。恢复旧运行继续使用该运行 `snapshot/evaluate_liyan.py --resume <运行目录>`，留档标签沿用旧运行。


## 1032 的稳定性校准（2026-11-12）

默认并发已由32降为2（脚本1.3.3）。1032在并发2累计52次零错误，3和4均观察到生成失败；不保证全量零错误。1030的历史32并发设置仍保存在原始快照中。当前1032建议新建运行，显式使用 `--workers 2 --max-attempts 2 --timeout 60`。详细记录见 `ToMBench_李言老师baseline_full_mediumm_1032/并发参数建议_20261112.md`。
