# MentalHealthBench 1030 + DeepSeek medium 小样本验证

2026-11-13 北京时间10:18–10:19。本次两个英文案例（索引4、6），每例4次独立采样，2并发。一个案例为单条用户消息，一个包含原始system及固定多轮历史。保留原历史，不重新生成历史回复，不发送canary。

## 结果

- 8/8目标回复、36/36 rubric裁判调用成功；无接口/解析失败。
- 36次裁判请求均发送 thinking.type=enabled、reasoning_effort=medium，全部响应含推理信息。网关是否将medium映射为high不可独立验证；DeepSeek官方文档说明medium是high兼容值。
- 8个独立用户；每次初始空历史，最终只有本次user/role一对；已核对序列化前缀与原数据消息完全一致；canary未发送。
- 复用mheval原评分函数与grader模板；严格整数0/1；负分项满足即扣分。小样本 task_clipped_score=0.296474359，即29.65/100，不代表总体成绩。
- DeepSeek输入50793 token，输出8944 token（其中推理7322），合计59737。输出已含推理，不能再次相加。

## 未解决的全量限制

首批索引1、10共8次尝试被1030平台拒绝：发送内容长度不能超过5000。失败留档为同级 MentalHealthBench_李言老师_1030_20261113T021705Z_b56d2b21。采用当前完整序列化格式并计入首轮包装，430/1215条超过限制；脚本会提前拒绝，不截断或隐式跳过。需要平台扩展输入上限或原生messages支持，才能继续全量。当前隐藏平台system和序列化role也与原生模型接口不等价。

## 重跑小样本

```bash
cd /home/wangaoyun/wangaoyun/emohaa-eval-upload.UBlCGt/bench/mheval
python scripts/mentalhealthbench_liyan.py --indices 4 6 --n-samples 4 --workers 2 --execute
```

全部请求响应、逐样本和逐rubric结果位于cases/，汇总results.json，核查validation.json。样本内容仅本地留档，不在报告公开。
