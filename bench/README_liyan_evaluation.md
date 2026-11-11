# 李言老师242：并发ToMBench评测（v1.2.0）

## 2026-11-11 新凭证与新智能体

新凭证当前可访问 `1030 — 李言老师-bench测试`。通过 `--bot-id 1030 --bot-name 李言老师-bench测试` 切换目标；清理、历史核查、聊天、权限预检均使用同一目标ID，默认242仍保留以兼容旧调用。
新凭证来自当前项目的bot_chat_client.py；不要使用下面旧242示例里的Lingx凭证模块。环境变量LINGX_API_KEY/SECRET若存在会优先覆盖模块。

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt

# 查询新凭证当前用户的可用智能体
python3 bot_chat_client.py --list

# 新智能体小规模双语试跑：8题×2语言×3次=48次
python3 -u bench/evaluate_liyan.py --bot-id 1030 --bot-name 李言老师-bench测试 --limit 8 --languages zh en --repeats 3 --workers 32 --credentials-module "$PWD/bot_chat_client.py"

# 新智能体双语全量：17160次，完整留档
mkdir -p bench/run_logs
nohup python3 -u bench/evaluate_liyan.py --bot-id 1030 --bot-name 李言老师-bench测试 --limit 0 --languages zh en --repeats 3 --workers 32 --interval 0 --summary-every 200 --max-attempts 2 --timeout 60 --credentials-module "$PWD/bot_chat_client.py" > "bench/run_logs/liyan1030_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
```

项目当前分支main，origin为https://github.com/GitBlin/emohaa-eval.git。以下仅提交评测代码、测试和文档，避免把带明文凭证的bot_chat_client.py及大量本地输出一并提交：

```bash
git add bench/evaluate_liyan.py bench/test_evaluate_liyan.py bench/README_liyan_evaluation.md
git diff --cached --stat
git commit -m "Support configurable bot IDs and isolated bilingual concurrent evaluation"
git push -u origin main
```

这里只提供推送命令，未实际commit/push。部署到另一台机器时应在当地配置API凭证，不要通过Git同步密钥。

默认中英文各2860题，每题每语言3次，共17160个试次，32并发、interval=0、summary-every=200。这里的3轮对应每道题的repeat=0/1/2，任务可交错执行；不代表三个模型版本。
每个试次使用独立用户（由运行标识和trial_id派生），每次尝试仍先清理上下文、核验无旧消息后再提问。每个线程独享Client/Session/Token。恢复时沿用原用户映射，跳过已有result.json；重试前再次清理。独立用户有助于减少跨题用户记忆污染，但不能证明服务端不存在机构级共享状态。

## 命令

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench

# 帮助：列出所有参数
python3 evaluate_liyan.py --help

# 查询有权限的旧凭证可用智能体
python3 /home/wangaoyun/wangaoyun/Lingx/bot_chat_client.py --list

# 离线准备全部17160个试次，不发请求
python3 evaluate_liyan.py --dry-run --limit 0 --repeats 3 --languages zh en --workers 32 --interval 0 --summary-every 200 --credentials-module /home/wangaoyun/wangaoyun/Lingx/bot_chat_client.py

# 小规模并发试跑：20题×2语言×3次=120次
python3 -u evaluate_liyan.py --limit 20 --repeats 3 --languages zh en --workers 32 --interval 0 --summary-every 200 --credentials-module /home/wangaoyun/wangaoyun/Lingx/bot_chat_client.py

# 全量中英文：2860题×2语言×3次=17160次，32并发
python3 -u evaluate_liyan.py --limit 0 --repeats 3 --languages zh en --workers 32 --interval 0 --summary-every 200 --credentials-module /home/wangaoyun/wangaoyun/Lingx/bot_chat_client.py

# 后台全量：与上一条二选一，不要重复启动
mkdir -p run_logs
nohup python3 -u evaluate_liyan.py --limit 0 --repeats 3 --languages zh en --workers 32 --interval 0 --summary-every 200 --credentials-module /home/wangaoyun/wangaoyun/Lingx/bot_chat_client.py > "run_logs/liyan_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
# shell会显示PID；日志首行RUN_DIR是完整结果目录

# 查看后台日志（替换实际文件名）
tail -f run_logs/实际日志文件.log

# 优雅停止后台任务：停止派发，等待在途任务保存
kill -TERM 实际PID

# 恢复（替换实际RUN_DIR，必须用该运行的快照脚本）
python3 -u /实际RUN_DIR/snapshot/evaluate_liyan.py --resume /实际RUN_DIR

# 重建汇总报告，不联网；不能与同目录正在运行的任务同时执行
python3 /实际RUN_DIR/snapshot/evaluate_liyan.py --report-only /实际RUN_DIR

# 查看结果
cat /实际RUN_DIR/report.md
python3 -m json.tool /实际RUN_DIR/summary.json

# 离线回归测试
python3 test_evaluate_liyan.py
```

命令显式选择旧凭证模块，因为当前新凭证没有242权限；不会覆盖bot_chat_client.py中的新凭证。LINGX_API_KEY/LINGX_API_SECRET环境变量若存在，会优先于模块；运行前需确认它们对应有权限的凭证。不要在命令或日志中粘贴密钥。全量会创建17160个试次用户（另有1个预检用户），应使用测试机构。已对8/16/32/64/128并发进行多轮双语测试；持续负载测试中32并发最快，具体记录见concurrency_checks/。这不保证未来负载下速度不变。

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
| --credentials-module | ../bot_chat_client.py | 凭证来源，建议使用上方旧凭证绝对路径；环境变量优先 |
| --base-url | LINGX_BASE_URL或https://www.ai-role.cn | 平台地址 |
| --user-id | 自动生成 | 运行用户命名空间/预检用户；试次用户由它与trial_id派生；不要跨运行复用 |
| --data-dir | bench/Tombench/data | 题库目录 |
| --output-dir | bench/liyan_evaluations | 结果根目录 |
| --model-version | unreported | 记录模型版本，不改变服务端模型 |
| --harness-version | unreported | 记录封装版本，不改变服务端配置 |
| --insecure | 关闭 | 显式关闭证书校验；正常运行不需要 |
| --dry-run | 关闭 | 只准备输入、快照和报告 |
| --resume | 无 | 恢复运行，使用manifest冻结参数；CLI workers等不会覆盖旧配置 |
| --report-only | 无 | 从已有结果重建报告 |
| --help | 无 | 输出帮助 |

目标固定botId=242。温度、top_p、底层模型、服务端记忆开关没有公开可配置参数，不会伪造设置。

## 结果与评分

每次运行独立目录，保存完整输入、选项映射、响应、清理及历史审计、失败/重试、耗时、代码和数据快照。认证密钥/Token不保存。
summary.json中的rounds_by_language分别列出中英文三轮成绩、均值和标准差，question_vote_accuracy_by_language给各语言投票准确率。by_repeat是合并语言的各轮成绩（键0/1/2），repeat_statistics给完整轮次的平均准确率和样本标准差；question_votes.json保存每题映射回原选项后的投票结果。失败与无效答案计错，并列投票不猜答案。重复测量可观察随机性与选项位置敏感性，不能消除数据偏差；三轮标准差不是置信区间。
运行中responses.jsonl/summary.json每200次刷新，trials/*/result.json逐次落盘。停止派发后在途任务完成再汇总；恢复不会重发已有结果（包括已记录失败），未完成请求可能再次发送且会新建attempt目录。
单个目录加进程锁，防止重复恢复互相覆盖。不同运行请使用默认自动生成的独立用户命名空间。

## 双语数据异常

Strange Story Task:293 的中文为赵阳是否说真话的二选一，英文故事仍是赵阳，但英文问题和四个选项变成了李华的另一道题，属于明显错配。脚本保留原题、全量执行并完整记录；summary.json的excluding_option_count_mismatches给两种语言同时排除此题的辅助成绩，不擅自修改题库或宣称全量成绩等价于官方论文成绩。

## 验证与性能

10项离线回归测试通过，覆盖并发用户隔离、三轮统计、双语分开汇总、异常题辅助统计、恢复、上下文阻断及SSE解析。双语全量17160个输入离线检查通过。
性能测试原始记录：concurrency_checks/20261110T101518Z/results.json（短批次）和concurrency_checks/20261110T101720Z/results.json（每批384次持续测试）。每个配置重复2次，采用相同样本、选项映射和中英文比例；测试时max-attempts=1，避免重试掩盖失败。正式运行恢复默认2次以容忍暂时错误。
只根据吞吐量和请求/协议/上下文可靠性选择并发，不根据holdout答题分数调参。短批次耗时不能保证全量耗时；速度外推需考虑长时间限流、磁盘留档和服务波动。
