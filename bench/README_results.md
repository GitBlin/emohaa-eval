# 评测数据和正式结果目录

结果目录统一按“榜单_智能体名称_ID”命名，内部运行目录加相同前缀。数据集源码、官方参考文件及正式运行中的snapshot/trials子目录保留其语义名称。

| 榜单/智能体 | 完成数 | 正式结果目录 |
|---|---:|---|
| ToMBench / 李言老师-bench测试1030 | 17160 | [ToMBench_李言老师-bench测试_1030/ToMBench_李言老师-bench测试_1030_20261111T032603Z_70b9feba](ToMBench_李言老师-bench测试_1030/ToMBench_李言老师-bench测试_1030_20261111T032603Z_70b9feba/report.md) |
| EmoBench / 李言老师-bench测试1030 | 2400 | [EmoBench_李言老师-bench测试_1030/EmoBench_李言老师-bench测试_1030_20261111T040112Z_ced181e6](EmoBench_李言老师-bench测试_1030/EmoBench_李言老师-bench测试_1030_20261111T040112Z_ced181e6/report.md) |

清除冗余记录：50049个文件，文件内容合计约0.49GiB；原始预检、试跑、并发校准、隔离检查及空准备记录已移除。清理清单见[结果目录迁移与清理记录.json](结果目录迁移与清理记录.json)。

保留数据目录：Emobench、Tombench、PsiArena、MentalHealthBench；emobench_official保留官方参考源与许可证。现有完整结果不自动重跑或覆盖。

ToMBench整理版Word报告及CSV在`ToMBench_李言老师-bench测试_1030/reports/`。每个正式运行目录的responses.jsonl是全部答题，badcases.jsonl是失败记录。
