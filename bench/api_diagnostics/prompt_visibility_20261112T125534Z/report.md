# Prompt 可见性实测

2026-11-12 20:55（北京时间），botId=1030，使用独立 probe 用户发送一条核验消息，未修改智能体配置或评测会话。

结论：本次聊天接口与上下文接口没有返回服务端组装后的完整 prompt。

- 查询上下文前为空，发送后返回 2 条记录：原始 user 消息和机器人回复。
- 完整读取 SSE 返回流，7 个事件，没有 meta.info 或 metainfo，没有 system prompt 或完整 messages。
- 上下文 contents 记录 promptTokens=1108、completionTokens=8、responseSource=agent:llm。这些是平台报告的用量与来源，并非 prompt 原文；不能由此确定隐藏内容和变量。
- reminderContext、customMessage 等相关字段为空。
- 如需完整输入，应在服务端模板渲染、历史/记忆/检索拼接完成后、实际向模型发请求前，记录最终请求体及关联 chatId。仅网关日志仍可能漏掉网关下游的额外拼接。

证据：chat.request.json、chat.raw.txt、chat.events.json、context_before.body.bin、context_after.body.bin、inspection.json。未保存鉴权凭据。
