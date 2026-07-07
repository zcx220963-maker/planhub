# PlanHub - AI 驱动的计划管理与社交平台

**双后端架构：Java Spring Boot 业务中台 + Python LangGraph AI 编排系统**

[![Java](https://img.shields.io/badge/Java-17-blue.svg)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.0-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.2.6-blue.svg)](https://react.dev.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![CI](https://github.com/zcx220963-maker/planhub/actions/workflows/ci.yml/badge.svg)](https://github.com/zcx220963-maker/planhub/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 一、项目架构

### 1. 双后端安全架构

```
前端 → Java 安全网关（JWT 鉴权）→ Python AI 服务（仅监听 127.0.0.1）
```

- **Java 后端**：业务逻辑、数据权限隔离、JWT 认证、MySQL/Redis 数据层
- **Python AI 服务**：LangGraph 编排 + Tool Calling，通过内网密钥鉴权，零外部暴露

---

### 2. LangGraph 编排系统总览

基于 `StateGraph` 构建多 Agent 确定性路由。`Supervisor` 节点识别意图后路由到对应 Agent，所有 Agent 通过 `AgentState`（TypedDict）共享状态。

编排层代码位于 `py_agent/src/app/orchestrator/`：

```
orchestrator/
├── graph.py              # StateGraph 定义（节点注册 + 边 + 条件路由函数）
├── state.py              # AgentState — 整个图的唯一状态对象
├── schemas.py            # 结构化输出定义（IntentResult, CapabilityFlags）
├── memory_bridge.py      # Redis 读写桥接（短期记忆 + 会话持久化）
├── tool_rag.py           # Tool RAG — 工具文档检索（双路召回 + LLM Rerank）
└── nodes/
    ├── supervisor.py             # 意图分类 + 路由决策（关键词优先 + LLM 兜底）
    ├── plan_mode_confirm.py      # 询问用户是否要开启计划模式
    ├── plan_collector.py         # LLM 多轮对话收集用户需求（XML 标签输出）
    ├── parameter_extractor.py    # Tool RAG 检索 + LLM 打分选工具 + 参数提取
    ├── tool_executor.py          # 并行调用 59 个免费外部 API
    ├── doc_retriever.py          # 从用户知识库文档中检索相关知识
    ├── plan_writer.py            # 合并所有数据段（规划摘要+工具数据+文档+记忆）生成最终计划
    ├── plan_confirmation.py      # 询问用户是否将计划创建到平台
    ├── extract_plan_title.py     # LLM 从计划文本中提取标题
    ├── create_plan_to_platform.py  # 调用 Java 后端 API 创建计划
    ├── orchestrator_assistant.py # 通用工具调用 Agent（搜索/打卡/发帖）
    ├── orchestrator_rag.py       # 用户知识库文档问答
    ├── orchestrator_chat.py      # 闲聊/普通对话
    ├── memory_load.py            # 加载短期记忆（Redis）
    └── memory_save.py            # 保存短期+长期记忆，计划完成后清空状态
```

---

### 3. 完整图结构与路由

```
                           ┌──────────────────┐
                           │   supervisor      │ ← 入口点（所有请求先进这里）
                           └───────┬──────────┘
                                   │ (route_by_intent)
                  ┌────────────────┼─────────────────┬──────────────────────┐
                  ▼                ▼                  ▼                      ▼
         ┌─────────────┐  ┌────────────────┐  ┌──────────┐        ┌────────────────┐
         │ plan_mode_   │  │ assistant/rag/ │  │ parameter│        │ plan_          │
         │ confirm      │  │ chat/          │  │_extractor│        │ confirmation   │
         └──────┬───────┘  │ clarify        │  └────┬─────┘        └──────┬──────────┘
                │          └───────┬────────┘       │                      │
                ▼ (确认)           │                 │                      │
     ┌────────────────────┐       │                 │                      │
     │ memory_load_for_   │       │                 │                      │
     │ generator          │       ▼                 ├──→ tool_executor     │
     └─────────┬──────────┘    (执行后→             │    (并行)            │
               ▼                 memory_save)       │                      │
        ┌──────────────┐                            ├──→ doc_retriever     │
        │ plan_         │                            │    (并行)            │
        │ collector     │◁────────── supervisor      │                      │
        │ (多轮收集)     │    回溯（collecting_info）  └──┬──→ memory_load_ ──┘
        └──────┬───────┘                                │    for_writer
               ▼ (点击确认)                               ▼
        ┌──────────────────┐                     ┌──────────────┐
        │ parameter_       │                     │ plan_writer   │
        │ extractor        │                     │ (合并所有数据) │
        └──────┬───────────┘                     └──────┬───────┘
               │                                       │ (plan_generated)
               ├──→ tool_executor (并行)                 ▼
               │             ↓                  ┌──────────────────┐
               ├──→ doc_retriever (并行)         │ plan_            │
               │             ↓                  │ confirmation     │
               └──→ memory_load_for_writer       └──┬────┬─────────┘
                               ↓                   │    │
                         ┌──────────────┐       确认 │    │ 跳过/聊天
                         │ plan_writer   │           ▼    ▼
                         └──────┬───────┘     ┌───────────┐
                                ▼             │ extract_  │  直接返回计划文本
                         ┌──────────────┐     │ plan_title│
                         │ plan_        │     └─────┬─────┘
                         │ confirmation │           │
                         └──────┬───────┘           ▼
                           确认  │ 跳过     ┌──────────────────┐
                                ▼          │ create_plan_to_  │
                        ┌───────────┐      │ platform         │
                        │ extract_  │      └────────┬─────────┘
                        │ plan_title│               │
                        └─────┬─────┘               ▼
                              ▼              ┌──────────┐
                      ┌──────────────┐       │ memory_  │
                      │ create_plan_ │       │ save     │
                      │ to_platform  │       └────┬─────┘
                      └──────┬───────┘            │
                             ▼                    ▼
                      ┌──────────┐          ┌──────────┐
                      │ memory_  │          │   END    │
                      │ save     │          └──────────┘
                      └────┬─────┘
                           ▼
                      ┌──────────┐
                      │   END    │
                      └──────────┘
```

**路由关键点：**

| 节点 | 路由函数 | 路由目标 |
|------|---------|---------|
| supervisor → | `route_by_intent` | plan_mode_confirm / memory_load_for_generator / parameter_extractor / plan_confirmation / assistant / rag / chat |
| plan_mode_confirm → | `route_after_plan_mode_confirm` | memory_load_for_generator（确认）/ chat（拒绝）/ memory_save（等待） |
| plan_generator → | `route_after_plan_generator` | parameter_extractor（确认后）/ plan_confirmation（生成后）/ memory_save（收集中） |
| parameter_extractor → | 并行边 | tool_executor + doc_retriever |
| tool_executor + doc_retriever → | 并行汇合 | memory_load_for_writer |
| plan_writer → | `route_after_plan_writer` | plan_confirmation（成功）/ memory_save（失败） |
| plan_confirmation → | `route_after_plan_confirmation` | extract_plan_title（确认）/ chat（聊天）/ memory_save（等待） |
| rag → | `route_after_rag` | memory_save（成功）/ chat（失败 fallback） |

---

### 4. Supervisor 的分层路由机制

Supervisor 是整个编排的"大脑"，决策分多层优先级（从高到低）：

```
优先级1: 前端点确认/否超链接？
  └─ user_input == "__CLICK_CONFIRM__"
     └─ 检查当前处于哪个阶段（优先级：plan_confirmation > plan_collector > plan_mode_confirm）
        └─ 直接路由到对应节点，绕过后面的所有逻辑

  └─ user_input == "__CLICK_NO__"
     └─ waiting_for_plan_confirmation=True → 路由到 plan_confirmation（跳过）

优先级2: 正在进行计划生成流程？
  └─ execution_trace 有计划节点 + waiting_for_* 标记为 True
     └─ 是 → 跳过 RAG 守卫，不走文档选中拦截

优先级3: 用户选中文档且不是计划意图？
  └─ selected_doc_ids 非空 + 用户输入不含"计划/制定"
     └─ 是 → 直接路由到 rag 节点

优先级4: waiting_for_plan_mode_confirm?
  └─ 是 → plan_mode_confirm

优先级5: waiting_for_plan_confirmation?
  └─ 是 → plan_confirmation

优先级6: execution_trace 中有计划流程记录？
  └─ 计划已生成 → plan_confirmation
  └─ 还在收集 → 路由回 plan_generator

优先级7: 前置关键词规则匹配（确定性，不走 LLM）
  └─ 搜索词开头？→ assistant
  └─ 打卡词开头？→ assistant
  └─ 发帖词开头？→ assistant
  └─ 数字/序号？→ assistant
  └─ 计划关键词？→ plan_mode_confirm

优先级8: LLM 意图分类（兜底）
  └─ 把用户输入发给 LLM，返回 IntentResult
     └─ plan_creation → plan_mode_confirm
     └─ assistant → assistant
     └─ chat → chat
```

**为什么需要前置规则？** 因为小模型对短输入（如"是"、"确认"）容易误分类。前置规则用代码确定性匹配覆盖高频场景，LLM 只处理复杂长尾输入。

---

### 5. 计划生成完整子流程

```
用户说"制定旅行计划"
       │
       ▼
  supervisor（前置规则匹配「计划创建」→ plan_mode_confirm）
       │
       ▼
  plan_mode_confirm（第一次进入）
       │ 输出："请点击「确认」开始制定。"
       │ waiting_for_plan_mode_confirm = True
       │
       ▼ （用户点击确认 → __CLICK_CONFIRM__）
  plan_mode_confirm → selected_agent = "plan_collector"
       │
       ▼
  memory_load_for_generator → 加载短期记忆（Redis）
       │
       ▼
  plan_collector（第一轮）→ 输出 <question>（无 summary）
       │ 输出："你想制定一个关于什么的计划呢？"
       │ waiting_for_plan_confirmation = False
       │
       ▼ （用户回复"旅行计划"）
  plan_collector（第二轮+）→ 输出 <summary> + <question>
       │ 输出：<summary>用户想要制定旅行计划</summary>
       │        <question>想去哪里呢？...</question>
       │
       ▼ （多轮... 用户点击确认 → __CLICK_CONFIRM__）
  plan_collector → _build_plan_summary() → needs_plan_building = True
       │ plan_summary = "用户想要制定一个为期5天的旅行计划..."
       │
       ▼
  parameter_extractor
       ├── Tool RAG 双路召回（向量+BM25）→ 14个候选
       ├── LLM Rerank → 保留7个
       └── LLM 打分 + 参数提取 → 选中6个
           ranked_tools = [
             {"tool":"get_weather_forecast", "params":{"city":"杭州"}},...
           ]
       │
       ├──→ tool_executor（并行调用6个API → 天气成功3个，城市介绍失败3个）
       │      ↓
       │    tool_data_parts = ["[天气信息（杭州）]...", ...]
       │
       └──→ doc_retriever（从用户选中知识库双路召回→Rerank→5个片段）
              ↓
            doc_data_parts = ["[来源: 文档1#3]（相关度: 0.85）\n...", ...]
              ↓
            ┌────────────── 同步点 ──────────────┐
            │ tool_executor + doc_retriever 都完成 │
            └────────────────────────────────────┘
              ↓
       memory_load_for_writer
         ├── 短期记忆（Redis，最近8条）
         └── 长期记忆（Chroma 语义检索，top-5）
              ↓
       plan_writer（合并所有数据段）
         ├── 【计划信息】← plan_summary
         ├── 【用户长期记忆 - 偏好与习惯】← LTM（不相关则忽略）
         ├── 【最近对话背景】← 短期记忆
         ├── 【API 数据】← tool_data_parts
         └── 【知识库参考】← doc_data_parts
              ↓
         生成计划文本（500-2000字）+ plan_metadata
              ↓
       plan_confirmation
         │ 输出：计划已生成！（摘要截断）
         │ 请点击「确认」来创建，或点击「否」跳过。
         │ waiting_for_plan_confirmation = True
              │
         ┌────┴────┐
         ▼          ▼
      确认(创建)   跳过(不创建)
         │          │
         ▼          ▼
  extract_plan_title   直接返回计划文本
  create_plan_to_platform
         │
         ▼
  memory_save → 清空所有计划流程状态 → END
```

**tool_executor 与 doc_retriever 并行执行**，两者都完成后才进入 plan_writer，最大化利用时间。

---

### 6. 节点详解

#### 6.1 Supervisor 节点
- **文件**：[supervisor.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/supervisor.py)
- **功能**：意图分类 + 路由决策
- **特殊指令**：
  - `__CLICK_CONFIRM__` → 根据当前阶段路由到 plan_confirmation / plan_collector / plan_mode_confirm（优先级倒序：最新的阶段最优先）
  - `__CLICK_NO__` → 路由到 plan_confirmation（跳过创建）
- **前置关键词**：搜索、打卡、发帖、数字序号、计划创建 → 直接路由（不走 LLM）
- **LLM 兜底**：用 `with_structured_output(IntentResult)` 做意图分类

#### 6.2 Plan Mode Confirm 节点
- **文件**：[plan_mode_confirm.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/plan_mode_confirm.py)
- **功能**：询问用户是否开启计划模式
- **确认方式**：只认 `__CLICK_CONFIRM__`，普通文字"确认"不算
- **首次进入**：保存原始问题到 `original_user_input`，输出"请点击「确认」开始制定"
- **已询问过**：`__CLICK_CONFIRM__` → 开始计划收集；普通对话 → 路由到 chat（保持等待状态）

#### 6.3 Plan Collector 节点
- **文件**：[plan_collector.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/plan_collector.py)
- **功能**：LLM 多轮对话收集用户需求，输出 XML 标签格式
- **第一轮**：输出 `<question>`（无 summary）
- **第二轮+**：格式为 `<summary>总结内容</summary><question>追问问题</question>`
- **多轮历史**：通过 `plan_conversation_history` 状态字段持久化
- **引导语**：
  - 第一轮：`如果不想回答或者没有需要补充修改的话，点击「确认」来生成计划`
  - 后续轮：`如果信息收集得差不多了，点击「确认」来生成计划`
- **确认后**：`_build_plan_summary()` 从最后一条 `<summary>` 中提取需求摘要

#### 6.4 Parameter Extractor 节点
- **文件**：[parameter_extractor.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/parameter_extractor.py)
- **功能**：工具选择 + 参数提取
- **两步流程**：
  1. Tool RAG（纯代码）→ 从 59 个工具中双路召回 + LLM Rerank 得到 top-7 候选
  2. LLM 一次调用 → 对候选工具打分(0-10) + 从 plan_summary 中提取参数值
- **过滤**：score < 6 不选；参数 key 不在 `required_slots` / `optional_slots` 中的过滤掉

#### 6.5 Tool Executor 节点
- **文件**：[tool_executor.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/tool_executor.py)
- **功能**：并行调用选中的外部 API
- **工具数量**：59 个免费 API，全部无需 API Key
- **工具分类**：
  - 天气地理：天气预报、汇率、节假日、城市介绍、国家信息、空气质量、IP 查询
  - 学习书籍：Open Library、Gutendex、Bible API、Dictionary API、Numbers API、Datamuse
  - 健康运动：wger 运动、BMI 计算、Open Food Facts 营养查询
  - 旅行生活：CityBikes 共享单车、Open Brewery DB 啤酒厂、Bored API 活动建议、ThemeDB 食谱
  - 娱乐休闲：JokeAPI 笑话、Quotable 名言、FreeToGame 游戏、TVmaze 电视剧、PokéAPI 宝可梦、
    CocktailDB 鸡尾酒、PoetryDB 诗歌、Useless Facts 趣闻
  - 动物图片：Dog CEO 狗狗、RandomFox 狐狸、RandomDuck 鸭子、Cataas 猫咪、
    Dog Facts、Shibe.Online 柴犬
  - 动漫：AnimeChan 名言、Studio Ghibli 电影、Waifu.pics 动漫图片
  - 艺术设计：Colormind 配色、DummyImage 占位图、Chicago Art Institute 艺术品
  - 开发工具：GitHub 搜索、npm 搜索、Icon Horse favicon、GitHub 用户查询、QR 码生成
  - 音乐娱乐：Lyrics.ovh 歌词、iTunes 音乐搜索
  - 趣味工具：RandomUser.me、Agify.io 年龄预测、Genderize.io 性别预测、
    Nationalize.io 国籍预测、Kanye.rest 名言、Chuck Norris 笑话、Advice Slip 建议
  - 资讯科技：Hacker News 头条、Wikipedia 摘要
  - 基础工具：当前时间、IP 查询
- **执行方式**：`asyncio.gather` 并行调用
- **结果格式化**：每个工具对应 `_format_tool_result` 函数，格式化为 `[工具名（参数）]` + 数据文本

#### 6.6 Doc Retriever 节点
- **文件**：[doc_retriever.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/doc_retriever.py)
- **功能**：从用户选中的知识库文档中检索相关知识
- **检索链**：`plan_summary` → 双路召回(向量+BM25) → 融合去重 → LLM Rerank → top-5 片段
- **输出**：`[来源: 文档名#片段序号]（相关度: 分数）\n内容`
- **与 RAG 节点的区别**：RAG 节点是面向用户问答的（HyDE + 压缩），doc_retriever 是面向计划生成的（Rerank 精度优先）

#### 6.7 Plan Writer 节点
- **文件**：[plan_writer.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/plan_writer.py)
- **功能**：合并所有数据段，LLM 生成最终计划文本
- **注入数据**（按 prompt 顺序）：
  1. 【当前日期】
  2. 【计划信息】← plan_summary
  3. 【用户长期记忆 - 偏好与习惯】← LTM（不相关则忽略）
  4. 【最近对话背景】← 短期记忆
  5. 【API 数据】← tool_data_parts
  6. 【知识库参考】← doc_data_parts
- **约束**：严禁编造数据；API 为空时用通用知识生成框架；字数 500-2000
- **输出**：`plan_text_cache` + `plan_metadata`（数据来源标注）

#### 6.8 Plan Confirmation 节点
- **文件**：[plan_confirmation.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/plan_confirmation.py)
- **功能**：询问用户是否创建计划到平台
- **确认方式**：只认 `__CLICK_CONFIRM__`（创建）和 `__CLICK_NO__`（跳过）
- **文本截断**：超过 1000 字时截断展示，标注"计划过长已截断，完整计划将保存到平台"

#### 6.9 Extract Plan Title → Create Plan to Platform
- **文件**：[extract_plan_title.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/extract_plan_title.py)
  [create_plan_to_platform.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/create_plan_to_platform.py)
- **功能**：LLM 从计划文本中提取标题；调用 `langchain_tools.create_plan` 调 Java 后端 API 创建计划
- **日期解析**：从 plan_text 中解析持续时间，自动计算 start_date 和 target_date

#### 6.10 Memory Load / Save（记忆系统）
- **文件**：[memory_load.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/memory_load.py)
  [memory_save.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/nodes/memory_save.py)
  [memory_bridge.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/memory_bridge.py)

**短期记忆**：
- 存储：Redis List，`memory:short:{user_id}:{session_id}`
- TTL：7 天
- 内容：最近 20 条对话消息
- 加载：`memory_load_node` 加载到 `short_term_memory`
- 注入节点：plan_collector 的 system prompt 的 `【短期记忆 - 最近对话上下文】`，plan_writer 的 `【最近对话背景】`

**长期记忆**：
- 存储：Chroma 向量库，collection: `ltm_{user_id}`
- TTL：永久（用户隔离）
- 内容：每轮对话结束时由 LLM 提取值得记住的事实
- 加载：`memory_load_for_writer` 单独检索（不在 memory_load_node 中加载）
- 注入节点：仅 plan_writer 的 `【用户长期记忆 - 偏好与习惯】` 数据段
- 原则：不相关则忽略，不能强行加入计划；plan_collector 完全不接触 LTM，避免 LLM 把 LTM 内容当成用户说过的话

**计划完成后状态清除**：
- memory_save 检测 `user_confirmed_create=True` + `plan_text_cache` 非空
- 清空 26 个字段：计划确认标记、计划内容、对话历史、工具执行结果、文档检索结果、路由标记等

---

### 7. AgentState 状态定义

完整字段见 [state.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/state.py)：

```python
class AgentState(TypedDict):
    # ===== 输入 =====
    user_input: str                 # 本轮用户输入
    session_id: str                 # 会话 ID（UUID）
    user_id: Optional[str]          # 用户 ID
    capabilities: Dict[str, Any]    # 能力开关
    selected_doc_ids: List[str]     # 用户选中的文档 ID
    rag_fallback_to_chat: bool      # RAG 回退标记

    # ===== 路由决策 =====
    intent: Optional[str]           # 意图：plan_creation/assistant/rag/chat
    selected_agent: Optional[str]   # 选中 Agent
    confidence: float               # 置信度

    # ===== Agent 执行记录 =====
    execution_trace: Annotated[List[Dict], operator.add]  # 追加语义

    # ===== 计划确认流程 =====
    waiting_for_plan_mode_confirm: bool   # 等待确认开启计划模式
    waiting_for_plan_confirmation: bool   # 等待确认创建计划
    user_confirmed_create: bool           # 用户确认创建
    plan_text_cache: Optional[str]        # 缓存的计划文本
    plan_title: Optional[str]             # 提取的计划标题
    plan_type: Optional[str]              # 计划类型
    plan_summary: Optional[str]           # 需求摘要（plan_collector 输出）

    # ===== 三阶段计划生成 =====
    ranked_tools: List[Dict]              # 选中工具列表
    tool_data_parts: List[str]            # 工具执行结果文本
    doc_data_parts: List[str]             # 文档检索结果文本

    # ===== 记忆 =====
    short_term_memory: List[BaseMessage]  # 短期记忆
    long_term_memory: List[str]           # 长期记忆
```

**reducer 合并**：`execution_trace` 用 `operator.add` 实现追加，其他字段用默认覆盖语义。

---

### 8. RAG 的三个子系统

| | 用户 RAG 节点 | Tool RAG | Doc Retriever |
|---|---|---|---|
| **触发时机** | 用户选中文档且输入非计划意图 | plan_collector 确认后自动触发 | plan_collector 确认后自动触发 |
| **检索对象** | 用户上传的知识库 | 59 个工具的语义文档 | 用户选中的文档 |
| **召回方式** | 向量 + BM25 双路 | 向量 + BM25 双路 | 向量 + BM25 双路 |
| **排序方式** | LLM Rerank | LLM Rerank | LLM Rerank |
| **输出用途** | 回答用户问题 | 缩小工具选择范围（14→7 候选） | 注入 plan_writer 的【知识库参考】 |
| **实现位置** | orchestrator_rag.py | tool_rag.py | doc_retriever.py |

#### Tool RAG 详解

位置：[tool_rag.py](file:///C:/Users/xu'zhi'cheng/Desktop/检查/planhub/py_agent/src/app/orchestrator/tool_rag.py)

设计思路：把每个外部 API 当作一个"文档"做 RAG。每个工具的 Document 包含：
- `page_content`：语义描述（功能、触发词、适用场景、参数说明）
- `metadata.tool_name`：工具名
- `metadata.required_slots` / `optional_slots`：参数 Schema
- `metadata.triggers`：触发词列表（用于降级关键词匹配）

**执行链路**：
```
plan_summary → _hybrid_search（向量+BM25 双路召回）
             → _llm_rerank（LLM 精排，打分 0-10）
             → _format_tool_result（格式化为候选工具列表）
             → parameter_extractor 的二次 LLM 打分和参数提取
```

---

### 9. 前端交互特性

- **计划引导超链接**：AI 消息中"点击「确认」"等关键词自动转为可点击超链接，点击发送 `__CLICK_CONFIRM__` 特殊指令
- **"是"、"确认"、"开始制定" → 确认操作**；**"否" → 跳过操作**
- **多标签页隔离**：`sessionStorage` 存 tab_id，`localStorage` 存 `{tab_id: session_id}` 映射
- **历史会话**：通过 Java 后端转发到 Python `/orchestrator/conversations`，数据从 Redis 的 `session:*` key 中读取
- **删除会话**：同步清除 Redis 会话数据 + LangGraph checkpoint + 短期记忆

---

### 10. 安全设计

- **密钥管理**：所有 API Key、数据库密码通过环境变量配置，`.env` 已加入 `.gitignore`
- **Java ↔ Python 鉴权**：内部调用通过 `X-Internal-Api-Secret` 请求头鉴权
- **Python 服务**：默认只监听 `127.0.0.1`，不对外暴露
- **JWT 认证**：前端请求通过 Java 后端的 JWT 过滤器认证后，再转发给 Python 服务
- **用户隔离**：短期记忆（Redis）和长期记忆（Chroma）均按 `user_id` 隔离
- **计划完成后状态清除**：26 个状态字段一次性清空，确保下一轮对话不受影响

---

### 11. 项目结构

```
planhub/
├── backend/                     # Java 后端
│   └── src/main/java/com/planhub/
│       ├── controller/          # REST 控制器（含 AI 请求转发）
│       ├── service/             # 业务逻辑层
│       ├── entity/              # 数据库实体
│       ├── mapper/              # MyBatis 映射器
│       ├── config/              # 配置类
│       └── dto/                 # 数据传输对象
├── frontend/                    # React 前端
│   └── src/
│       ├── pages/               # 页面组件
│       ├── components/          # 通用组件
│       ├── context/             # React Context
│       ├── services/            # API 服务层
│       └── types/               # TypeScript 类型定义
├── py_agent/                    # Python AI 服务
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 配置（pydantic-settings）
│   ├── requirements.txt         # Python 依赖
│   └── src/app/
│       ├── api/                 # API 路由（orchestrator、rag_api）
│       ├── orchestrator/        # LangGraph 编排器（核心）
│       │   ├── graph.py         # StateGraph 定义
│       │   ├── state.py         # AgentState 定义
│       │   ├── schemas.py       # 结构化输出
│       │   ├── memory_bridge.py # Redis 记忆桥接
│       │   ├── tool_rag.py      # Tool RAG 检索
│       │   └── nodes/           # 16 个节点实现
│       ├── services/            # 业务服务
│       ├── dao/                 # 数据访问层（Chroma、Redis）
│       └── common/              # 公共工具
└── planhub_schema.sql           # 数据库建表脚本
```

---

### 12. 技术栈与快速开始

| 层级 | 技术 |
|------|------|
| **前端** | React 19 + TypeScript + Vite 8 + Ant Design 6 |
| **Java 后端** | Spring Boot 3.2 + MyBatis-Plus + JWT + MySQL 8.0 + Redis 7.0 |
| **Python AI** | FastAPI + LangChain + LangGraph + ChromaDB + Ollama / 阿里云百炼 |

#### 快速开始

```bash
# 1. 克隆
git clone https://github.com/zcx220963-maker/planhub.git
cd planhub

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，配置数据库、Redis、LLM 等

# 3. 初始化数据库
mysql -u root -p -e "CREATE DATABASE planhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p planhub < planhub_schema.sql

# 4. 启动 Java 后端
cd backend
mvn clean package -DskipTests
java -jar target/planhub-backend-1.0.0.jar

# 5. 启动 Python AI 服务
cd py_agent
pip install -r requirements.txt
python main.py    # 监听 127.0.0.1:8000

# 6. 启动前端
cd frontend
npm install
npm run dev
```

浏览器访问：**http://localhost:5173**

> **注意**：首次启动 Python 服务时，会自动构建 Tool RAG 的向量索引。如果后续新增了工具，需要删除 `py_agent/chroma_db/tool_rag_docs` 让它重建索引。

---

## 许可证

[MIT License](LICENSE)
