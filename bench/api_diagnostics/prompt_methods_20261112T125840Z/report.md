# 组装后 Prompt 查询方法核查

日期：2026-11-12 20:58（北京时间）。范围：本项目文档；检索 71 个 DOCX、Markdown、TXT 等文件，包含两份根目录文档及 API 核对、各评测说明。排除 .git、依赖目录、trials、snapshot、retry_history、code_migrations 和本次诊断目录中的重复/运行记录。完整文件清单、SHA256 与匹配段落见 document_search.json。未声称覆盖服务器内部文档或未提供的管理后台文档。

## 结论

当前凭据下，对 1030、1032 逐项实测，没有取得服务端组装后的 system/user prompt、完整 messages、变量展开值或编译记录。不能据此断言内部没有相关功能；只能确认当前文档未公开查询方法、本次公开接口响应未提供。

## 文档依据与验证

| 方法 | 文档依据 | 两个智能体的实测结果 |
|---|---|---|
| GET /open/bot/list 和 /open/bot/{id} | 最佳实践 §2、§5.2 | 返回角色资料，无 prompt/模型请求配置 |
| POST /open/chat/completions，isStream=true | §3.1、§7 示例 | 完整读取 SSE；只有回复、用量、会话标识，无 meta.info/metainfo |
| 同接口 isStream=false | §3.1 | JSON success=true；返回 ChatEntity，无完整模型输入 |
| 检查 reminderContext/customMessage/contents | §5.3 | 前两者为空；contents 含回复、用量、来源等，没有 prompt 原文 |
| 添加 inputs.diagnostic_marker 唯一标记 | §3.1 inputs 为部分平台输入变量 | 请求成功，无变量回显或展开后的模板；不能证明该字段被使用或未使用 |
| GET /open/chat/context | §3.2 | 每轮新增 user/role 记录，无 system 或组装后消息 |
| clearContext 后 onlyLastSession=true/false | §3.2–3.3 | true 返回空，false 返回 6 条聊天记录和 flush_context 标记，未出现隐藏提示词 |
| sessionId 过滤 | §3.2 | 本次记录 sessionId=null，无可用的真实 sessionId，因此未伪造 ID 测试；此参数本身仅用于过滤记录 |
| 工程编译层与逐轮记录 | 工程算法 todo list §S1 | 文档写“校验层与记录层缺失”，无查询 URL，无法据此调用 |

认证、查询和清理均成功；6 次聊天均完成（两个机器人各三轮）。每个机器人使用新建独立 probe 用户，仅清理该测试用户的上下文，不影响评测用户。

## 用量观察

同一条短消息，1030 三轮输入 token 为 1108、1289、1314；1032 为 149、149、149。第二轮为非流式，第三轮附加 inputs 标记，并处于同一个测试会话，因此不能把变化单独归因于 inputs 或响应模式。首轮均无已有可见聊天记录；用量差异不能还原具体注入内容，也不能仅凭 token 数判断记忆是否启用或模型是否相同。

## 后续需要服务端提供的能力

在最后一次组装完成、真正调用模型之前记录最终请求体，并关联 chatId、消息 ID、botId、实际模型和配置版本。若要定位各类注入，还需分别记录模板版本、变量渲染结果、历史/记忆/检索片段及裁剪过程。网关日志只有在网关接收到的就是最终请求时才足以验证模型输入。当前客户端日志只能证明发送给智能体平台的 content。

未尝试无文档依据的 debug 参数或猜测内部接口；ASR/TTS 与音色/分类接口没有查询文本模型 prompt 的文档语义，因此未发起无关音视频任务。

## 证据

- document_search.json：文档清单与匹配段落。
- results.json：逐项验证摘要与相关字段。
- 1030/、1032/：无凭据的请求、HTTP 状态、完整原始响应、解析后的 SSE/JSON、各阶段上下文。
- probe.py：本次执行脚本，重新执行会创建新用户并发送 6 条测试消息。
