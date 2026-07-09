# PlanHub - AI 驱动的计划管理与社交平台

**双后端架构：Java Spring Boot 业务中台 + Python LangGraph AI 编排系统**

[![Java](https://img.shields.io/badge/Java-17-blue.svg)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.0-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.2.6-blue.svg)](https://react.dev.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 一、项目架构

### 1. 双后端安全架构

```
前端 → Java 安全网关（JWT 鉴权）→ Python AI 服务（仅监听 127.0.0.1）
```

- **Java 后端**：业务逻辑、数据权限隔离、JWT 认证、MySQL/Redis 数据层
- **Python AI 服务**：LangGraph 编排 + LangChain 工具调用，通过内网密钥鉴权，零外部暴露

### 2. LangGraph 编排系统总览

基于 `StateGraph` 构建多 Agent 确定性路由，Supervisor 节点识别意图后路由到对应 Agent。整个编排层代码位于 `py_agent/src/app/orchestrator/`，分为三层：

```
orchestrator/
├── graph.py          # StateGraph 定义（节点注册 + 边 + 条件路由函数）
├── state.py          # AgentState — 整个图的唯一状态对象（TypedDict）
├── schemas.py        # 结构化输出（IntentResult）、能力开关（CapabilityFlags）
├── memory_bridge.py  # Redis 读写桥接（对话历史、短期记忆、会话持久化）
└── nodes/
    ├── supervisor.py          # 意图分类 + 路由决策
    ├── plan_mode_confirm.py   # 计划模式确认（是否开启计划收集）
    ├── plan_generator.py      # LLM 多轮对话收集用户需求
    ├── parameter_extractor.py # 工具选择 + 参数提取（Tool RAG + LLM Rerank）
    ├── tool_executor.py       # 纯工具调用执行器（调用外部 API）
    ├── doc_retriever.py       # 用户文档检索（从用户上传的知识库）
    ├── plan_writer.py         # 最终计划文本生成（LLM 综合所有数据）
    ├── plan_confirmation.py   # 询问是否创建到平台
    ├── extract_plan_title.py  # LLM 提取计划标题
    ├── create_plan_to_platform.py  # 调用 Java 后端创建计划
    ├── assistant.py           # 通用工具调用 Agent（搜索/打卡/发帖/查看）
    ├── rag.py                 # 文档知识库检索问答
    ├── chat.py                # 闲聊节点
    └── memory_load.py / memory_save.py  # 记忆加载/保存（graph.py 内联）
```

#### 2.1 完整图结构与路由

```
                                    ┌──────────────────────┐
                                    │     memory_load       │ ← 入口：从 Redis 加载历史对话
                                    └──────────┬───────────┘
                                               │ (固定边)
                                               ▼
                                    ┌──────────────────────┐
                                    │     supervisor        │ ← 意图分类 + 前置规则匹配
                                    └──┬──────┬──────┬─────┘
                                       │      │      │
              ┌────────────────────────┼──────┼──────┼────────────────────┐
              │ 条件路由 (route_by_intent)                                       │
              │                                                               │
              │  plan_mode_confirm  plan_generator  assistant  rag  chat       │
              │       │                  │            │          │      │     │
              │       │                  │            │          │      │     │
              │       ▼                  ▼            ▼          ▼      ▼     │
              │  [计划确认]          [计划收集]    [工具调用]  [RAG]  [闲聊]  │
              │                                                               │
              └──────────────────────────────────────────────────────────────┘
                                               │
                                    ┌──────────▼───────────┐
                                    │     memory_save       │ ← 出口：保存对话到 Redis
                                    └──────────┬───────────┘
                                               │
                                              END
```

#### 2.2 计划生成完整子流程（唯一需要跨节点断点的流程）

```
用户说"制定旅行计划"
       │
       ▼
  supervisor（识别为 plan_creation 意图）
       │
       ▼
  plan_mode_confirm（问"是否开启计划模式？"）
       │ 用户说"是"
       ▼
  plan_generator（LLM 多轮对话收集需求）
       │  第1轮：问"想去哪里？"
       │  用户："杭州三日游，喜欢美食和风景"
       │  第2轮：问"和谁一起去？"
       │  用户："不想回答" 或 "确认"
       │  用户说"确认" → needs_plan_building=True
       ▼
  parameter_extractor（Tool RAG 检索工具 + LLM 提取参数）
       │  输出: ranked_tools = [{tool:"get_weather_forecast", params:{city:"杭州", days:3}}, ...]
       │
       ├──→ tool_executor（并行）──→ 调用外部 API → 返回天气/营养/运动数据
       │                                        │
       │                              tool_data_parts = ["天气信息（杭州）...", ...]
       │
       └──→ doc_retriever（并行）──→ 从用户选中的文档检索相关知识点
                                                │
                                      doc_data_parts = ["[来源: 文档1#3]: ...", ...]
                                                │
                                    ┌───────────▼───────────┐
                                    │     plan_writer        │ ← 等 tool_executor + doc_retriever 都完成
                                    └───┬───────────┬───────┘
                                        │           │
                              plan_text_cache    plan_metadata
                              （最终计划文本）   （数据来源标注）
                                        │
                                        ▼
                              plan_confirmation（问"是否创建到平台？"）
                                        │ 用户说"是"
                                        ▼
                              extract_plan_title（LLM 提取标题，如"杭州三日游计划"）
                                        │
                                        ▼
                              create_plan_to_platform（调 Java 后端 API 创建计划）
                                        │
                                        ▼
                                   memory_save → END
```

---

### 3. 节点路由机制：怎么走到正确节点的？

#### 3.1 Supervisor 的分层决策

Supervisor 是整个编排的"大脑"，决策分 **6 层优先级**（从高到低）：

```
优先级1: 正在计划流程中？ ──────────────────────────────────────┐
  └─ execution_trace 里有 plan_generator/plan_mode_confirm?     │
     └─ 是 → 直接路由回 plan_generator/plan_confirmation        │
                                                                  │
优先级2: 用户选中了文档且非计划意图？ ─────────────────────────── │
  └─ selected_doc_ids 非空 + 用户输入不含"计划/制定"?           │
     └─ 是 → 直接路由到 rag 节点                                │
                                                                  │
优先级3: 对话状态机等待参数/选择？ ───────────────────────────── │
  └─ ConversationState 是 WAITING_PARAM/WAITING_SELECT?          │
     └─ 是 → 路由到 assistant（继续执行未完成的打卡/搜索任务）   │
                                                                  │
优先级4: 等待计划模式确认？ ──────────────────────────────────── │
  └─ waiting_for_plan_mode_confirm=True?                         │
     └─ 是 → plan_mode_confirm                                   │
                                                                  │
优先级5: 等待计划创建确认？ ──────────────────────────────────── │
  └─ waiting_for_plan_confirmation=True?                         │
     └─ 是 → plan_confirmation                                   │
                                                                  │
优先级6: 前置关键词规则匹配 ──────────────────────────────────── │
  └─ 搜索词开头？打卡词开头？发帖词开头？纯数字/序号？计划关键词？│
     └─ 命中 → 直接路由（不走 LLM，避免误判）                    │
                                                                  │
优先级7: LLM 意图分类（兜底） ──────────────────────────────────  │
  └─ 把用户输入 + 系统 prompt 发给 LLM，返回结构化 IntentResult  │
     └─ plan_creation → plan_mode_confirm                        │
     └─ assistant → assistant                                    │
     └─ chat → chat                                              │
     └─ clarify → chat                                           │
```

**为什么需要前置规则（优先级1-6）？** 因为小模型（7B）对用户说的"是"、"确认"、"搜索旅游"这类短输入很容易误分类。前置规则用代码确定性匹配，覆盖高频场景；LLM 只处理复杂长尾输入。

#### 3.2 任务不被打断的设计

计划流程的核心问题是：**用户说了"制定计划"后，中间要等多轮对话，怎么让下一轮不走错节点？**

答案是三管齐下：

```
┌─────────────────────────────────────────────────────────────┐
│ 机制1: LangGraph Checkpoint（Redis，30分钟TTL）              │
│   每轮图执行完，LangGraph 自动把整个 AgentState 序列化到     │
│   Redis 的 ckpt:thread:{session_id} key。                    │
│   下次同 session 发消息，LangGraph 自动反序列化恢复所有字段。 │
│                                                             │
│ 机制2: execution_trace（写在 AgentState 里）                 │
│   每个节点执行后把 {node, status, collecting_info,            │
│   plan_generated, needs_plan_building} 追加到 trace 列表。   │
│   supervisor 读 trace 就知道"当前走到哪一步"。                │
│                                                             │
│ 机制3: boolean 标记（waiting_for_plan_mode_confirm 等）      │
│   各节点在结束时设置标记，supervisor 优先检查这些标记。       │
│   例如 plan_mode_confirm 后设置 waiting_for_plan_mode_confirm=True │
│   → supervisor 下次直接路由到 plan_mode_confirm 处理用户回复  │
└─────────────────────────────────────────────────────────────┘
```

具体执行流（以用户说"是"为例）：

```
第1轮：
  用户输入 "制定旅行计划"
  → graph.ainvoke({user_input: "制定旅行计划", ...})
  → memory_load（从 Redis 加载历史对话）
  → supervisor（LLM 分类为 plan_creation）
  → plan_mode_confirm（返回"是否开启计划？"）
  → memory_save（保存对话 + 清除 checkpoint）
  → LangGraph 自动写 checkpoint: {execution_trace:[...], waiting_for_plan_mode_confirm=True, ...}

第2轮（Redis checkpoint 还在）：
  用户输入 "是"
  → graph.ainvoke({user_input: "是", ...})
  → LangGraph 先从 checkpoint 恢复 state → waiting_for_plan_mode_confirm=True
  → supervisor（检查优先级4 → 直接路由到 plan_mode_confirm）
  → plan_mode_confirm（检测到确认 → 返回 + 设置 selected_agent=plan_generator）
  → plan_generator（问第一个问题"想去哪里？"）
  → memory_save → 写新 checkpoint

第3轮（Redis checkpoint 还在）：
  用户输入 "杭州三日游"
  → LangGraph 恢复 state → execution_trace 里有 plan_generator(collecting_info=True)
  → supervisor（检查优先级1 → trace 显示还在收集信息 → 路由回 plan_generator）
  → plan_generator（问第二个问题）
  → ...

第N轮：用户说"确认"
  → plan_generator（检测到确认 → needs_plan_building=True, plan_conversation_history=[...]）
  → 路由到 parameter_extractor
  → parameter_extractor → tool_executor + doc_retriever（并行）→ plan_writer → plan_confirmation
  → 问"是否创建到平台？"
```

---

### 4. State 数据传递机制

#### 4.1 AgentState 结构与生命周期

```python
class AgentState(TypedDict):
    # ── 输入（每轮重置）──
    user_input: str
    session_id: str
    user_id: Optional[str]
    capabilities: Dict[str, Any]
    selected_doc_ids: List[str]

    # ── 路由决策（supervisor 写入）──
    intent: Optional[str]
    selected_agent: Optional[str]
    confidence: float

    # ── 计划流程状态（跨轮次持久化）──
    plan_conversation_history: List[Dict]    # plan_generator 的多轮对话历史
    plan_summary: str                       # 用户需求摘要
    plan_text_cache: str                    # plan_writer 生成的最终计划
    waiting_for_plan_mode_confirm: bool     # 标记：等用户确认开启计划
    waiting_for_plan_confirmation: bool     # 标记：等用户确认创建到平台
    needs_plan_building: bool               # 标记：plan_generator 收集完成
    plan_generated: bool                    # 标记：计划已生成

    # ── 工具执行状态 ──
    ranked_tools: List[Dict]                # parameter_extractor 输出
    tool_call_results: List[Dict]           # tool_executor 输出
    tool_data_parts: List[str]              # 格式化后的工具数据文本
    doc_data_parts: List[str]               # doc_retriever 输出

    # ── execution_trace（Annotated 追加语义）──
    execution_trace: Annotated[List[Dict], operator.add]
    # ↑ 关键：LangGraph 的 Annotated + add 实现追加而非覆盖！
```

**核心原理**：LangGraph 的状态传递不是替换整个 state，而是 **reducer 合并**。`execution_trace` 用 `operator.add` 实现追加，其他字段用默认的覆盖语义。每个节点返回一个 dict，LangGraph 自动 merge 到全局 state。

#### 4.2 State 的持久化与清理时机

```
┌──────────────────────────────────────────────────────────────────┐
│                    Checkpoint TTL: 30 分钟                        │
│                    Redis key: ckpt:thread:{session_id}            │
│                                                                    │
│  写入时机：每次 memory_save 完成后 LangGraph 自动写入              │
│  清除时机：                                                        │
│    1. 流程走完（memory_save 节点主动调 _clear_checkpoint）         │
│    2. 用户点终止按钮（POST /orchestrator/cancel）                  │
│    3. TTL 过期（30分钟自动删除）                                   │
│    4. 从历史列表加载旧会话时（新 checkpoint 覆盖）                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    对话历史 TTL: 7 天                              │
│                    Redis key: session:{session_id}                 │
│                                                                    │
│  写入时机：每次 memory_save 时追加本轮用户输入 + 助手回复          │
│  清除时机：7 天后自动过期                                          │
│  用途：左侧历史列表展示、30分钟后断点续传时重建状态                │
└──────────────────────────────────────────────────────────────────┘
```

**为什么流程结束要主动清除 checkpoint？**
如果不清，下次用户说"帮我搜索xxx"时，LangGraph 从 checkpoint 恢复 state，发现 `execution_trace` 里有 `plan_generator` 节点记录，supervisor 会误以为还在计划流程里，路由回 plan_generator。所以流程结束必须清。

**30 分钟断点续传**：checkpoint 过期但对话历史还在时，`_restore_state_from_history()` 从 `session:{session_id}` 的对话历史中识别计划相关消息（如 assistant 回复里含"请说确认"），重建 `plan_conversation_history`、`plan_summary`、`execution_trace` 注入到当次 invoke 的输入里，supervisor 据此恢复路由。

---

### 5. 用户上下文历史怎么保存和传递的？

#### 5.1 保存时机（memory_save 节点）

```python
# graph.py — memory_save_node
async def memory_save_node(state) -> dict:
    # 1. 取本轮 user_input + agent_output
    chat_history = [
        {"role": "user", "content": state["user_input"]},
        {"role": "assistant", "content": state["agent_output"]}
    ]

    # 2. 追加到 Redis 历史会话（session:{session_id}，7天TTL）
    #    同时读取现有历史 + 合并（用于前端历史列表展示）
    memory_bridge.save_conversation(session_id, user_id, history=full_history)

    # 3. 短期记忆也追加（memory:short:{session_id}，2小时TTL，最近20条）
    memory_bridge.save_memory(session_id, user_id, chat_history)

    # 4. 流程结束 → 清除 checkpoint
    await _clear_checkpoint(session_id)
```

#### 5.2 历史怎么传给节点的

不同节点有不同的历史获取方式：

```
┌──────────────────────────────────────────────────────────────────┐
│ 节点              │ 历史来源           │ 获取方式                   │
├───────────────────┼────────────────────┼────────────────────────────┤
│ chat 节点         │ 无                 │ 无状态，每轮独立            │
│ rag 节点          │ Redis 短期记忆     │ query_rag_internal 内部读   │
│                   │                    │ get_chat_history(session_id)│
├───────────────────┼────────────────────┼────────────────────────────┤
│ assistant 节点    │ LangGraph          │ AgentService.run_async:     │
│                   │ MemorySaver +      │ memory_service.get_short_term│
│                   | Redis 短期记忆     │ (session_id) → short_term   │
│                   |                    │ (20条, 2小时TTL)            │
├───────────────────┼────────────────────┼────────────────────────────┤
│ plan_generator    │ AgentState.        │ state["plan_conversation_   │
│                   │ plan_conversation_  │ history"] — 在 state 里     │
│                   │ history            │ 跨轮次持久化                │
├───────────────────┼────────────────────┼────────────────────────────┤
│ 其他计划链路节点   │ 不需要历史          │ 只读 state 里的工具数据     │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.3 上下文压缩

RAG 节点有两处压缩机制：

```python
# rag.py — 上下文压缩（可选）
# 对检索到的文档按句子切分，计算每句与问题的关键词重合度
# 只保留最相关的句子，减少 token
# 规则：至少保留 3 句，保留内容长度至少为原文的 30%

# agent_service.py — 短期记忆裁剪
# memory:short:{session_id} 是 Redis List，固定保留最近 20 条
# memory_bridge._ltrim(key, 0, 19)  # 自动裁剪
```

---

### 6. RAG 的三个子系统设计

本项目有 **三条独立但互补的 RAG 路径**：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG 路径对比                                │
├──────────────┬──────────────────┬──────────────────┬───────────────┤
│              │ RAG 节点         │ Tool RAG         │ Doc Retriever │
│              │ (文档问答)       │ (计划工具选择)   │ (计划文档注入) │
├──────────────┼──────────────────┼──────────────────┼───────────────┤
│ 触发条件     │ 用户选中了文档   │ plan_generator   │ plan_generator │
│              │ 且无明确计划意图 │ 确认后自动触发   │ 确认后自动触发 │
│ 检索对象     │ 用户上传的知识库 │ TOOL_DOCS 列表   │ 用户选中的文档 │
│              │ (Chroma 向量库)  │ (24个API工具文档) │ (hybrid_search)│
│ 召回方式     │ 向量 + BM25      │ 向量 + BM25      │ 向量 + BM25    │
│              │ + HyDE           │ + 触发词降级     │ (无 HyDE)      │
│ 排序方式     │ 归一化加权 +     │ LLM Rerank       │ 归一化加权     │
│              │ LLM Rerank       │ (参数提取)       │ (无需 Rerank)  │
│ 后处理       │ 上下文压缩       │ 参数校验 +       │ 带来源标记    │
│              │ + 来源校验       │ 实体解析         │ 的原始片段     │
│ 输出用途     │ 回答用户问题     │ 调用外部 API     │ 注入 plan_writer│
│              │                  │ 获取实时数据     │ 作为额外依据   │
└──────────────┴──────────────────┴──────────────────┴───────────────┘
```

#### 6.1 RAG 节点（文档检索问答）

**触发**：用户在前端勾选了文档 + 输入非计划意图（如"帮我总结文档内容"）

**执行链路**：
```
用户问题 "杭州有什么必去景点？"
    │
    ▼
rag_node（检查 selected_doc_ids → 有选中 → 调 query_rag_internal）    │
    ▼
query_rag_internal → query_rag:
    │
    ├──→ HyDE 扩展：LLM 生成假设笔记
    │    "假设用户在杭州旅行，想了解西湖、灵隐寺、西溪湿地等景点..."
    │
    ├──→ hybrid_search：向量 + BM25 双路召回（各取 fetch_k=20）
    │    向量：Chroma 余弦相似度
    │    BM25：关键词词频统计
    │    归一化融合：final_score = 0.5 × vector_norm + 0.5 × bm25_norm
    │
    ├──→ LLM Rerank：逐篇打分 0-10，取 Top-K
    │
    ├──→ 上下文压缩：保留关键词重合度最高的句子
    │
    ├──→ LLM 生成回答（system prompt 强约束：禁止用先验知识）
    │
    └──→ 返回 {answer, sources}
    │
    ▼
rag_node 检查结果是否有效（非"未找到相关内容"）
    │ 有效 → 返回 answer
    │ 无效 → 设置 rag_fallback_to_chat=True → 路由到 chat 节点
    │        （chat 节点会在回答开头说明"知识库未找到，以下是我的思考"）
```

**兜底策略**：
- 用户未选中文档 → 直接 fallback 到 chat
- 知识库查不到 → 设置 `rag_fallback_to_chat=True` → chat 节点用通用知识回答
- LLM 生成失败 → 返回友好错误信息

#### 6.2 Tool RAG（计划工具选择 + 参数提取）

**触发**：用户说完"确认"后，plan_generator 设置 `needs_plan_building=True`

**核心设计思路**：把每个外部 API 当作一个"文档"做 RAG。每个工具构建包含【功能】【触发词】【适用场景】【参数格式】的语义索引文档（共 24 个工具）。

```python
# tool_rag.py — TOOL_DOCS 示例（天气工具）
Document(
    page_content="""
    【功能】查询指定城市未来7-16天的天气预报，包括温度、天气状况、是否下雨
    【触发词】天气、气温、温度、下雨、晴天、阴天、目的地、旅行、旅游...
    【适用场景】任何涉及城市/地点的计划都应该调用此工具
    【注意】即使用户没提"天气"，只要涉及目的地，天气就是必要信息
    【参数】city(必填,城市名), days(可选,预测天数,默认7)
    """,
    metadata={
        "tool_name": "get_weather_forecast",
        "required_slots": ["city"],
        "optional_slots": ["days"],
        "triggers": ["天气", "气温", "目的地", "旅行", ...]
    }
)
```

**执行链路（parameter_extractor 节点）**：
```
plan_summary = "用户计划从合肥出发去杭州三日游，喜欢美食和风景"
    │
    ▼
1. Tool RAG 检索：retrieve_relevant_tools(plan_document, top_k=7)
    ├─ 向量检索：对 24 个工具文档做 embedding 相似度匹配
    ├─ 降级：向量检索失败 → _fallback_keyword_match（用 triggers 关键词匹配）
    └─ 返回：[{tool_name:"get_weather_forecast", required_slots:["city"], ...},
             {tool_name:"get_food_nutrition", required_slots:["query"], ...},
             {tool_name:"get_wger_exercises", ...}, ...]
    │
    ▼
2. LLM Rerank + 参数提取（一次调用完成两件事）：
    给 LLM 的 prompt 包含：
    - 【计划信息】：plan_summary
    - 【候选工具列表（含完整参数Schema）】
    要求 LLM：
    a. 对每个工具打分 0-10（≥6 分才选）
    b. 从 plan_summary 中按 Schema 提取参数值
    c. 禁止编造、禁止推测
    
    输出示例：
    ```json
    {"rankings": [
      {"tool":"get_weather_forecast", "score":10, "params":{"city":"杭州","days":3}},
      {"tool":"get_food_nutrition", "score":8, "params":{"query":"杭州特色美食"}},
      {"tool":"calculate_bmi", "score":3, "params":{}}   ← 分数低于6，不选
    ]}
    ```
    │
    ▼
3. 参数校验：过滤 LLM 提取的非法 key（不在 required/optional_slots 里的一律丢弃）
    │
    ▼
输出：ranked_tools = [{tool, score, params}, ...] → 传给 tool_executor
```

**为什么不用 end-to-end（直接让 LLM 选工具+填参数一次性输出）？**

因为小模型（7B）同时做"选工具"和"精确填参数"容易出错：要么选了不该选的工具，要么参数格式不对。拆成两阶段：
1. Tool RAG 召回候选工具（代码做，确定性强）
2. LLM 只做打分排序 + 参数提取（难度降低，只需从结构化文本里摘取）

**兜底策略**：
- 向量检索失败 → 降级为关键词匹配（`triggers` 字段）
- LLM 返回空/解析失败 → `ranked_tools=[]` → tool_executor 不执行任何工具 → plan_writer 进入通用知识模式
- LLM 提取的参数含非法 key → 参数校验时丢弃

#### 6.3 tool_executor 的实体解析与降级

tool_executor 不是简单地 `call_tool(tool_name,params)`，而是做了**三层防护**：

```
输入: ranked_tools = [{tool:"get_food_nutrition", params:{query:"杭州的特色食物"}}]
    │
    ▼
1. 跳过空参数工具：所有参数都为 null → 不调用
    │
    ▼
2. 实体解析（safe_resolve_entity）：
    原始值 "杭州的特色食物" → 解析为具体食物名
    - get_food_nutrition: 调用 _safe_resolve_food → 对齐到标准食物名
    - search_open_library 等: 调用 _safe_resolve_book → 对齐到标准书名
    - 返回三态: {status:"ok", entity:"西湖醋鱼"} / {status:"ambiguous", candidates:[...]} / {status:"invalid"}
    │
    ├─ ok → 继续
    ├─ ambiguous → 把候选列表写入 tool_data_parts，告诉 plan_writer "不确定，供参考"
    └─ invalid → 跳过该工具
    │
    ▼
3. 调用工具 + 降级：
    call_tool("get_food_nutrition", {query:"西湖醋鱼"})
    ├─ 成功 → 记录到 tool_call_results
    └─ 失败 → 查 FALLBACK_MAP 降级：
         get_food_nutrition 失败 → 降级为 get_themealdb（搜索相似食物）
         get_fruit_nutrition 失败 → 降级为 get_wikipedia_summary
         get_wger_exercises 失败 → 降级为 get_bored_activity
    │
    ▼
4. 格式化输出：每个成功结果格式化为 "[来源: xxx] ..." 格式，写入 tool_data_parts
    │
    ▼
输出: tool_data_parts = ["食物营养（西湖醋鱼）\n  热量：...\n[来源: Open Food Facts]", ...]
```

#### 6.4 doc_retriever（计划生成里的文档 RAG）

**触发**：与 tool_executor 并行执行（都在 `needs_plan_building=True` 后触发）

**与 RAG 节点的区别**：
- RAG 节点面向用户直接提问（需要 HyDE、Rerank、压缩 → 精度高但慢）
- doc_retriever 面向计划生成（只需 hybrid_search → 快，因为 plan_summary 本身已经是自然语言，不需要 HyDE 扩展）

**执行链路**：
```
plan_summary = "用户计划从合肥出发去杭州三日游，喜欢美食和风景"
selected_doc_ids = ["doc_001"]  ← 用户在前端勾选的文档
    │
    ▼
doc_retriever_node:
    ├─ 检查 selected_doc_ids → 为空则跳过
    ├─ 检查 plan_summary → 为空则跳过
    │
    ▼
hybrid_search(plan_summary, top_k=5, fetch_k=20, doc_ids=selected_doc_ids, user_id=user_id)
    ├─ 向量检索：在 doc_001 的 chunks 中做 embedding 匹配
    ├─ BM25 检索：关键词词频匹配
    ├─ 归一化融合 → 取 Top-5
    │
    ▼
格式化每个片段：doc_parts = ["[来源: 杭州攻略#3]: 西湖景区建议早上7点去..."]
同时记录来源：doc_sources = [{name:"杭州攻略", chunk:3, score:0.92}, ...]
    │
    ▼
输出: doc_data_parts + doc_sources → 在 plan_writer 节点合并到计划中
```

**为什么 plan_summary 不需要 HyDE？**
RAG 节点的用户输入可能很短（"杭州景点？"），HyDE 能扩展成更丰富的语义。而 plan_generator 已经跟用户聊了多轮，`plan_summary` 是 LLM 总结的完整需求（包含目的地、天数、偏好），语义已经很丰富，直接用混合检索就够了。

**兜底**：
- 用户未选中文档 → 直接跳过，`doc_data_parts=[]`
- 检索结果为空 → `doc_retrieval_status="no_results"`，plan_writer 只用工具数据生成
- 检索异常 → 捕获异常，返回空，不影响计划生成

---

### 7. Plan Writer：如何融合所有数据生成计划

```python
# plan_writer.py
async def plan_writer_node(state) -> dict:
    # 1. 合并所有数据源
    all_data_parts = tool_data_parts  # 工具调用结果
    if doc_data_parts:                # 文档知识
        all_data_parts.append("【知识库参考】" + "\n\n".join(doc_data_parts))

    # 2. 构建最终 prompt
    user_input_text = f"""
    【计划信息】{plan_summary}
    【API数据】{tool_data_text}  # 合并了当前日期 + 所有工具/文档数据
    请生成一份完整的执行计划。
    """

    # 3. LLM 生成（temperature=0.7，max_tokens=8192）
    # 4. 空输出 → _build_fallback_plan（从 plan_summary 提取目标生成简易计划）
    # 5. 构建 plan_metadata（数据来源标注，供前端调试面板展示）
```

**prompt 约束**：
- 严禁编造具体数据（温度、价格、时间等）
- API 数据为空时基于通用知识生成框架
- `[参考]` 标记的信息以建议口吻呈现
- 字数 500-2000

---

### 8. 多标签页与会话隔离

```
session_id 管理策略（前端）：
┌────────────────────────────────────────────────────────┐
│ localStorage 存 {tab_id: session_id} 映射               │
│ sessionStorage 存 tab_id（关标签页即丢失）              │
│                                                        │
│ - 刷新页面：tab_id 不变 → 恢复 session_id → 恢复状态    │
│ - 新标签页：新 tab_id → 新 session_id → 完全隔离       │
│ - 关标签页再打开：tab_id 丢失 → 无法自动恢复           │
│   → 但可通过左侧历史列表手动恢复任意会话               │
└────────────────────────────────────────────────────────┘
```

---

### 9. 数据生命周期总结

```
                              TTL
ckpt:thread:{session_id}      30 分钟（流程结束主动清除）
  └─ LangGraph checkpoint（完整 AgentState）
  └─ 用途：跨轮次状态恢复、断点续传

session:{session_id}          7 天
  └─ 完整对话历史（[{role, content}, ...]）
  └─ 用途：左侧历史列表、30分钟后断点恢复重建状态

memory:short:{session_id}     2 小时（最近 20 条）
  └─ 短期对话记忆（assistant/RAG 节点读取）
  └─ 用 Redis List + ltrim 自动裁剪

memory:pref:{user_id}         永不过期
  └─ 用户偏好（assistant 节点读取）

memory:working:{session_id}   1 小时
  └─ 工作记忆（任务中间状态）
```

**状态清理时机**：
1. **流程正常结束**：`memory_save` → `_clear_checkpoint()`（不等 TTL）
2. **用户点终止按钮**：`POST /orchestrator/cancel` → 清除 checkpoint + ConversationState
3. **TTL 过期**：Redis 自动删除（checkpoint 30分钟、短期记忆 2小时、会话历史 7天）

---

## 二、RAG 完整实现（知识库侧）

> 知识库底层代码位于 `py_agent/src/app/api/rag.py`。本章讲解**文档怎么入库、怎么检索**。
> 编排层的三条 RAG 路径（RAG/Tool RAG/Doc Retriever）见上方第 6 章。

### 2.1 文档入库

```
上传文件 → 加载（PyPDFLoader/Docx2txtLoader/TextLoader）
         → 分块（RecursiveCharacterTextSplitter, chunk_size=800, overlap=100）
         → 生成 embedding（Ollama bge-m3）
         → 双写：Chroma 向量库 + BM25 词频表
```

**分块策略**：
```python
RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", "(?<=[。！？!?；;])", ",", " ", ""]
    # 优先级：双换行 → 单换行 → 句子分隔符 → 逗号 → 空格 → 字符
)
```

**多索引入口**：Chroma 向量库（按 user_id 隔离 collection）+ BM25 词频表（内存）+ MySQL 元数据。

### 2.2 检索流程

```
用户提问
  → HyDE 生成假设文档（解决词汇差异）（可选）
  → 混合检索（向量 + BM25 双路召回）
  → 归一化 + 加权融合（向量 0.5 + BM25 0.5）
  → LLM Rerank 精排（逐篇打分 0-10，取 Top-K）（可选）
  → 上下文压缩（按句子切分，保留关键词重合度最高的句子）（可选）
  → LLM 生成回答
  → 返回结果
```

**HyDE**：LLM 生成一段"个人笔记风格"的假设文档，解决用户说"登录"文档写"认证"的词汇差异。

**混合检索融合公式**：`final_score = 0.5 × vector_score_norm + 0.5 × bm25_score_norm`

**上下文压缩**：至少保留 3 句，保留内容长度至少为原文的 30%，确保不遗漏关键信息。

**LLM 生成约束**：文档是唯一信息来源，禁止先验知识、禁止泛化、硬性规则严格执行。后处理正则校验 `[来源: xxx]` 引用，剔除编造的文件名。

---

## 三、技术栈与快速开始

| 层级 | 技术 |
|------|------|
| **前端** | React 19 + TypeScript + Vite 8 + Ant Design 6 |
| **Java 后端** | Spring Boot 3.2 + MyBatis-Plus + JWT + MySQL 8.0 + Redis 7.0 |
| **Python AI** | FastAPI + LangChain + LangGraph + ChromaDB + Ollama / DashScope |

### 快速开始

```bash
# 1. 克隆
git clone https://github.com/zcx220963-maker/planhub.git
cd planhub

# 2. 配置环境变量
cp .env.example .env

# 3. 初始化数据库
mysql -u root -p -e "CREATE DATABASE planhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p planhub < planhub_schema.sql

# 4. 启动服务
cd backend && mvn clean package -DskipTests && java -jar target/planhub-backend-1.0.0.jar
cd py_agent && pip install -r requirements.txt && python main.py
cd frontend && npm install && npm run dev
```

浏览器访问：**http://localhost:5173**

---

## 四、项目结构

```
planhub2.0/
├── backend/                # Java 后端
│   └── src/main/java/com/planhub/
│       ├── controller/     # 16 个 REST 控制器
│       ├── service/        # 业务逻辑层
│       ├── entity/         # 数据库实体
│       └── mapper/         # MyBatis 映射器
├── frontend/               # React 前端
│   └── src/
│       ├── pages/          # 页面组件
│       ├── components/     # 通用组件
│       └── services/       # API 服务层
├── py_agent/               # Python AI 服务
│   └── src/app/
│       ├── api/            # API 路由（rag.py、chat.py 等）
│       ├── orchestrator/   # LangGraph 编排器
│       │   ├── graph.py    # StateGraph 定义（节点、边、路由）
│       │   ├── nodes/      # 各节点实现
│       │   └── state.py    # AgentState 定义
│       ├── service/        # 业务服务（agent_service、memory_service）
│       └── common/         # 公共工具（langchain_tools、mcp_tools、llm_factory）
└── planhub_schema.sql      # 数据库建表脚本
```

---


## 许可证

[MIT License](LICENSE)
