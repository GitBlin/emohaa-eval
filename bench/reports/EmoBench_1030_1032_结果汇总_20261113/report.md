> 留档清理更新：EmoBench 1032 基线第一次运行（8eefca75，575/800）已按用户要求删除。本文若引用该次分数，属于删除前历史分析；当前保留的基线第二次为3fca89e2（569/800）。

# EmoBench：1030 与 1032 历史结果汇总

核对日期：2026-11-13；时间均为北京时间。以各运行当前 summary.json 与 responses.jsonl 为准，已逐次核对记录数与正确数。不修改原始运行记录。

## 评分口径

EU 为情绪理解，情绪与原因两问同时正确才算该场景正确；EA 为情绪应用。每轮 EU中文、EU英文、EA中文、EA英文各200条，共800条；多轮是重复答同一题库，不是新增独立题目。综合准确率按全部答题记录统计，格式无效和请求失败均算错。

## 全量运行

| 记录 | 开始时间 | 轮数 | 正确/总数 | 综合 | EU中文 | EU英文 | EA中文 | EA英文 | 最终请求失败 | 格式无效 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1030 李言老师-bench测试 | 2026-11-11 12:01:12 | 3 | 1597/2400 | 66.54% | 56.17% | 61.83% | 74.50% | 73.67% | 0 | 9 |
| 1032 李言老师测试基线 | 2026-11-12 17:12:11 | 1 | 575/800 | 71.88% | 65.00% | 72.50% | 73.00% | 77.00% | 0 | 0 |
| 1030 李言老师full_medium | 2026-11-12 19:18:42 | 1 | 561/800 | 70.12% | 61.50% | 72.00% | 73.00% | 74.00% | 0 | 3 |
| 1032 李言老师测试基线 | 2026-11-12 19:41:22 | 1 | 569/800 | 71.12% | 65.00% | 71.00% | 74.50% | 74.00% | 0 | 0 |

## 对比结论

- 1030 的 full_medium 留档：70.125%，较早期三轮汇总66.5417%高3.5833个百分点。
- 1032 基线两次完整运行：71.875%和71.125%，两次均值71.50%；是两次重复测量，合计1144/1600，不是1600道不同题。
- 1032 两次均值相对1030 full_medium高1.375个百分点；两次单独分别高1.75和1.00个百分点。
- 最近一次1032相对1030 full_medium：EU中文+3.5个百分点、EU英文−1.0、EA中文+1.5、EA英文持平，合计多答对8条。
- 1032 两次结果相差0.75个百分点（6条）。不能仅凭这些重复次数宣称统计显著或因果提升。
- 四次完整留档当前请求失败均为0，历史补跑之前曾发生请求失败；格式无效仍按错保留：早期1030为9条，full_medium为3条，1032均0条。上下文审计错误均为0。
- full_medium、baseline等是留档名称；manifest中底层模型版本和harness版本均为unreported，不能以名称证明模型思考深度或后端配置。1030早期三轮、后期一轮和1032两次独立运行不宜不加说明地合并。

## 不计入全量对比的记录

- EmoBench_李言老师测试基线_1032_20261112T114102Z_5c5ddb70：interrupted，仅29/800条；保留但不纳入全量分数。

## 原始留档索引

- [EmoBench_李言老师-bench测试_1030_20261111T040112Z_ced181e6](/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师-bench测试_1030/EmoBench_李言老师-bench测试_1030_20261111T040112Z_ced181e6/report.md)；同目录 responses.jsonl 为全部逐题答题记录，trials/ 含请求响应；retry_history/（如存在）为补跑前记录。
- [EmoBench_李言老师full_medium_1030_20261112T111842Z_d38e5524](/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师full_medium_1030/EmoBench_李言老师full_medium_1030_20261112T111842Z_d38e5524/report.md)；同目录 responses.jsonl 为全部逐题答题记录，trials/ 含请求响应；retry_history/（如存在）为补跑前记录。
- [EmoBench_李言老师测试基线_1032_20261112T091211Z_8eefca75](/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师测试基线_1032/EmoBench_李言老师测试基线_1032_20261112T091211Z_8eefca75/report.md)；同目录 responses.jsonl 为全部逐题答题记录，trials/ 含请求响应；retry_history/（如存在）为补跑前记录。
- [EmoBench_李言老师测试基线_1032_20261112T114102Z_5c5ddb70](/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师测试基线_1032/EmoBench_李言老师测试基线_1032_20261112T114102Z_5c5ddb70/report.md)；同目录 responses.jsonl 为全部逐题答题记录，trials/ 含请求响应；retry_history/（如存在）为补跑前记录。
- [EmoBench_李言老师测试基线_1032_20261112T114122Z_3fca89e2](/home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/EmoBench_李言老师测试基线_1032/EmoBench_李言老师测试基线_1032_20261112T114122Z_3fca89e2/report.md)；同目录 responses.jsonl 为全部逐题答题记录，trials/ 含请求响应；retry_history/（如存在）为补跑前记录。
