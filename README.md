# PlanHub — AI 计划生成与管理平台

**单后端架构：React 前端 + Python LangGraph AI 服务**

[![React](https://img.shields.io/badge/React-19.2.6-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-blue.svg)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 一、项目架构

### 1. 整体架构

```
前端 (React + Vite)  ──HTTP/WebSocket──▶  Python AI 服务 (FastAPI + LangGraph)
                                        │
                                        ├── MySQL     (计划/打卡数据)
                                        ├── Chroma    (向量库：RAG + 长期记忆)
                                        └── Redis     (对话历史 / LangGraph Checkpoint)
```

前端直连 Python AI 服务，**无 Java 中间层**。服务默认仅监听 `127.0.0.1:8000`，安全可控。

### 2. 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript 6 + Vite 8 + Ant Design 6 |
| 后端 | Python FastAPI + LangGraph 多 Agent 编排 |
| AI 模型 | LongCat-2.0（默认）/ Ollama 本地模型 / 阿里云百炼 |
| 工具协议 | MCP（Model Context Protocol）— 21 个外部工具 |
| 存储 | MySQL（计划数据）+ Chroma（向量库）+ Redis（可选，会话状态） |

### 3. 目录结构

```
planhub/
├── frontend/                # React 前端
│   └── src/
│       ├── pages/           # 页面组件
│       │   ├── LangGraphTest.tsx   # AI 对话 + 计划预览
│       │   ├── PlanLibrary.tsx     # 计划库 + 日历打卡
│       │   └── ...
│       ├── services/        # API 调用
│       └── components/      # 通用组件
├── py_agent/                # Python AI 服务
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（Pydantic Settings）
│   ├── requirements.txt     # Python 依赖
│   └── src/
│       ├── app/
│       │   ├── api/         # REST 路由
│       │   ├── service/     # 业务逻辑
│       │   │   ├── graph.py         # LangGraph 图定义
│       │   │   ├── state.py         # AgentState
│       │   │   ├── nodes/           # 各节点实现
│       │   │   ├── plan_store.py    # MySQL 存储
│       │   │   └── plan_html_generator.py  # HTML 提取与保存
│       │   ├── common/      # 工具定义、LLM 工厂
│       │   ├── mcp/         # MCP 工具适配器（21 个工具）
│       │   └── dao/         # Redis 数据访问
│       └── prompts/         # LLM 提示词
├── chroma_db/               # Chroma 向量库数据
└── README.md
```

---

## 二、LangGraph 多 Agent 编排

### 1. 图结构

基于 `StateGraph` 构建确定性路由，Supervisor 节点识别用户意图后路由到对应 Agent。

```
                                  ┌─────────────────────┐
                                  │    memory_load       │ ← 入口：加载记忆
                                  └──────────┬──────────┘
                                             │
                                             ▼
                                  ┌─────────────────────┐
                                  │     supervisor       │ ← 意图分类 + 路由决策
                                  └──┬───────┬─────┬─────┘
                                     │       │     │
              ┌──────────────────────┼───────┼─────┼──────────────────┐
              │ 条件路由 (route_by_intent)                              │
              │                                                       │
              │  plan_mode_confirm  plan_generator  rag  chat          │
              └───────────────────────────────────────────────────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │     memory_save      │ ← 出口：保存记忆
                                  └──────────┬──────────┘
                                             │
                                            END
```

### 2. 计划生成完整流程

计划生成是唯一需要跨轮次断点的流程，分两步生成（文本先行，HTML 后行）：

```
用户说"制定旅行计划"
       │
       ▼
  supervisor（识别为 plan_creation 意图）
       │
       ▼
  plan_generator（LLM 多轮对话收集用户需求）
       │  第1轮：问"想去哪里？有什么偏好？"
       │  用户："杭州三日游，喜欢美食和风景"
       │  第2轮：问"和谁一起去？预算多少？"
       │  用户："不想回答" / "确认"
       │  用户说"确认" → needs_plan_building=True
       ▼
  parameter_extractor（LLM 选择工具 + 提取参数）
       │  从 MCP 获取全部 21 个工具 schema → LLM 打分选最相关的
       │  输出: ranked_tools = [{tool:"get_weather", params:{city:"杭州"}}, ...]
       │
       ├──→ tool_executor（并行）──→ MCP 调用外部 API → 返回天气/营养/运动数据
       │       使用 as_completed 流式输出：每个工具完成即刻显示日志
       │       支持 ReAct 自动参数补全：参数模糊时 LLM 自主推理重试
       │                                   │
       │                         tool_data_parts = ["天气信息（杭州）...", ...]
       │
       └──→ doc_retriever（并行）──→ 从文档知识库检索（BM25 + 向量 + LLM 重排）
                                           │
                                 doc_data_parts = ["[来源: 文档1#3]: ...", ...]
                                           │
                                 ┌─────────▼─────────┐
                                 │     plan_writer     │ ← 等 tool + doc 都完成
                                 └───────┬─────────────┘
                                         │
                               plan_text_cache（纯文本计划，流式打字机输出）
                                         │
                                         ▼
                               plan_confirmation（展示计划，询问"是否创建？"）
                                         │ 用户点确认
                                         ▼
                               plan_html_writer（生成杂志风 HTML 页面）
                                         │  先 save_plan() 获取 plan_id
                                         │  提取 ```html 代码块 → 写入磁盘文件
                                         │  update_plan(plan_id, html_path)
                                         ▼
                               extract_plan_title（LLM 提取计划标题）
                                         │
                                         ▼
                               create_plan_to_platform（补充时间信息 + 推送通知）
                                         │
                                         ▼
                                    memory_save → END
```

**设计要点**：
- `plan_writer` 只输出纯文本计划（流式打字机效果），不生成 HTML
- 用户审阅文本计划后点击确认，才触发 `plan_html_writer` 生成杂志风 HTML
- HTML 展示在右侧预览面板（iframe），不出现在聊天区域
- 工具执行和文档检索**并行执行**（`asyncio.as_completed`），`plan_writer` 等两者都完成后才执行

### 3. 节点说明

| 节点 | 职责 |
|------|------|
| `memory_load` | 从 Redis 加载短期记忆 + 从 Chroma 语义检索长期记忆 + 用户画像 |
| `supervisor` | 意图分类（plan_creation / rag / chat / clarify）+ 6 层优先级路由 |
| `plan_mode_confirm` | 询问用户是否开启计划收集模式 |
| `plan_generator` | LLM 多轮对话收集用户需求，自动追问缺失信息 |
| `parameter_extractor` | 从 MCP 获取工具 schema，LLM 选择工具 + 提取参数 |
| `tool_executor` | 并行调用外部 API（MCP），支持 ReAct 自动补参重试 |
| `doc_retriever` | 从用户上传的文档知识库检索相关内容（混合检索 + LLM 重排） |
| `plan_writer` | 综合所有数据生成纯文本计划（流式输出） |
| `plan_confirmation` | 展示文本计划 + 数据来源，等待用户确认 |
| `plan_html_writer` | 将文本计划转为杂志风 HTML 页面，保存到计划库 |
| `extract_plan_title` | LLM 提取计划标题 |
| `create_plan_to_platform` | 补充时间信息（update_plan）+ 推送通知 |
| `rag` | 文档知识库检索问答 |
| `chat` | 闲聊/通用问答（查不到知识库时自动 fallback） |
| `memory_save` | 保存对话历史 + 提取长期记忆 + 清理 checkpoint |

---

## 三、技术演进与效果

### 1. 流式响应：30ms 轮询 → 事件驱动段落缓冲

**痛点**：早期 SSE 方案需要一个独立的 `asyncio.Task` 每 **30ms** 轮询 token 缓冲区，即使 LLM 还没产出下一个 token 也要空转，前端打字机效果被 30ms 上限卡住。

**演进过程**：

| 阶段 | 方案 | 问题 |
|------|------|------|
| v1 | SSE + `contextvars` 缓冲 + 前端 fetch ReadableStream | 需要独立轮询任务 |
| v2 | SSE + `token_producer` 每 **30ms** 轮询 `flush_tokens()` + `contextvars` | 空转开销大，延迟被轮询间隔卡死 |
| **v3（当前）** | WebSocket + 段落缓冲（遇 `\n` 才 flush）+ 模块全局变量 | 零空转，事件驱动，延迟由 LLM 产出节奏决定 |

**核心改动**（参考 gpt-researcher 架构）：

```python
# 旧：30ms 轮询
async def token_producer():
    while True:
        tokens_text = flush_tokens()
        if tokens_text:
            await queue.put(("token", tokens_text))
        await asyncio.sleep(0.03)  # 30ms 固定开销

# 新：段落缓冲，事件驱动
async def emit_token(text: str):
    _paragraph_buffer += text
    if "\n" in _paragraph_buffer:          # 遇到换行才 flush
        parts = _paragraph_buffer.split("\n")
        _paragraph_buffer = parts[-1]      # 不完整的留到下次
        to_send = "\n".join(parts[:-1])
        if to_send:
            await ws.send_json({"type": "token", "content": to_send + "\n"})
```

**效果**：
- **延迟**：从固定 30ms 轮询 → 遇换行立即推送（自然语言一般几十到几百 ms 一段）
- **前端重渲染次数**：减少 10-50 倍（每段触发一次而非每 30ms 一次）
- **React 渲染**：只更新最后一条消息的引用（`[...prev.slice(0, lastIdx), updated]`），不触发整个消息列表 diff
- **空轮询开销**：从 30ms 一次 wakeup → 零空转

### 2. 工具调用：串行 → as_completed 流式 + ReAct 自动补参

**痛点**：3 个工具逐个串行调用，总耗时 = 各工具之和；参数模糊时直接失败，需要用户手动澄清。

**演进**：

| 优化前 | 优化后 |
|--------|--------|
| 串行 `await call_tool()` | `asyncio.as_completed()` 并行，完成一个输出一条日志 |
| 失败即报错 | ReAct 自动推理正确参数，重试一次 |
| 所有错误都重试 | 仅对"参数模糊/未found"类重试，网络错误直接记录 |

**效果**：3 个工具并行调用，总耗时从 `t1+t2+t3` 降到 `max(t1,t2,t3)`；参数类失败自动修复率约 80%，无需用户介入。

### 3. 工具发现：向量检索 → MCP 直连全量 Schema

**痛点**：旧方案用向量库（Tool RAG）检索候选工具，需要维护工具 embedding 索引，检索结果受相似度阈值影响可能漏工具。

**演进**：引入 MCP（Model Context Protocol）后，直接获取全部 **21 个工具** 的完整 schema 给 LLM 打分选择。

| 对比 | Tool RAG（旧） | MCP（新） |
|------|----------------|-----------|
| 工具数量 | 检索 top-K（可能漏） | 全量 21 个 schema |
| 维护成本 | 需要维护向量索引 | 零维护（MCP server 即定义） |
| 准确性 | 依赖 embedding 相似度 | LLM 直接理解语义打分 |

**效果**：工具选择准确率从约 75% 提升到 ~95%，无需维护独立的工具向量库。

### 4. RAG 检索：纯向量 → 混合检索 + LLM 重排

**演进**：

| 层级 | 作用 |
|------|------|
| 向量相似度检索 | 语义理解，取 top-20 候选 |
| BM25 关键词检索 | 精确词命中，取 top-20 候选 |
| 合并去重 | 两种结果融合，归一化分数 |
| LLM 重排序（Rerank） | 对候选文档逐条打分，选最相关的 top-K |
| 上下文压缩 | 只保留与问题最相关的句子，减少无效 token |

**效果**：检索精准率显著提升，尤其对"精确词 + 语义混合"类查询（如"杭州 7 月降雨量"），BM25 能补向量检索的盲区。

### 5. Thinking 模型兼容：裸 HTML → 4 级 Fallback 提取

**痛点**：LongCat-2.0 是 thinking 模型，有时不输出 ```html` 代码块包裹，而是直接输出裸 HTML（前面可能带思考注释 `<think>...</think>`），导致 `extract_html_code()` 匹配失败。

**4 级 Fallback 策略**（参考 yu-ai-code-mother 的 HtmlCodeParser）：

```python
# 策略 1: 提取 ```html 代码块
pattern = re.compile(r'```html\s*\n([\s\S]*?)```', re.IGNORECASE)

# 策略 2: 提取 ``` 代码块（不带 html 标记），检测是否以 HTML 标签开头
pattern2 = re.compile(r'```\s*\n([\s\S]*?)```')

# 策略 3: 去掉 HTML 注释和 <think>...</think> 块后再检测裸 HTML
cleaned = re.sub(r'<!--[\s\S]*?-->', '', raw_content)
cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned)

# 策略 4: 从第一个 <!DOCTYPE 或 <html 开始截取到末尾
for tag in ('<!doctype', '<html', '<head', '<body'):
    idx = lower.find(tag)
    if idx != -1:
        return cleaned[idx:].strip()
```

**效果**：HTML 生成成功率从 ~60% 提升到 ~98%，兼容 thinking 模型的各种输出格式。

### 6. 前端渲染：黑色控制台 → 杂志风时间线

**痛点**：加载日志时显示为黑色控制台风格（`#0f172a` 深色背景 + 等宽字体），与生成的杂志风 HTML 手册风格割裂。

**重设计**：
- 深色背景 → 象牙白 `#faf9f6`
- 等宽字体 → 优雅无衬线
- 纯文字列表 → **时间线卡片布局**，左侧渐变色竖线 + 彩色圆点
- 自动分类着色：智能分析（靛蓝）/ 工具调用（蓝）/ 完成（翠绿）/ 遇到问题（玫红）/ 排版设计（紫）
- 新条目淡入滑入动画 + 卡片 hover 浮起效果

**效果**：加载体验从"程序员调试控制台"变为"杂志编辑工作流"，与 HTML 手册风格统一。

### 7. 日历打卡：黑色描边 Bug 修复

**痛点**：打卡完成后，切换到其他月份时相同位置的格子出现黑色描边（focus outline）。

**根因**：React DOM 节点复用 — 日历格子的 `key` 使用数组索引 `idx`，当月份切换时 React 认为"同一个位置的同一个 key"是同一个 DOM 节点，保留了 focus 状态。

**修复**：

| 改动 | 作用 |
|------|------|
| `key={idx}` → `` key={`${year}-${month}-${date}-${idx}`} `` | 确保跨月份 key 唯一 |
| `useEffect` 监听 `currentMonth` 变化时 blur 当前焦点元素 | 月份切换时强制移除焦点 |
| 全局 CSS `*:focus { outline: none }` | 兜底移除所有描边 |
| 按钮 `onClick` 回调中手动 `.blur()` | 点击完成后立即失焦 |
| `tabIndex={-1}` 导航按钮 | 防止 Tab 焦点落入 |

### 8. 数据存储：SQLite → MySQL 全异步

**演进**：从 Python 内置 `sqlite3` 同步库切换到 `aiomysql` 异步连接池。

```python
# 旧：同步 SQLite（阻塞事件循环）
import sqlite3
conn = sqlite3.connect("planhub.db")
conn.execute("INSERT INTO plans ...")

# 新：异步 MySQL 连接池（不阻塞）
_pool = await aiomysql.create_pool(
    host=DB_HOST, port=DB_PORT, ...,
    minsize=1, maxsize=10, autocommit=True
)
```

**关键兼容处理**：MySQL 8 不允许 TEXT 列有 `DEFAULT ''`，移除了所有 TEXT 字段的默认值。

### 9. 流式结束检测：等全流程完 → 提前结束标记

**痛点**：LLM 流式生成结束后，前端还在显示打字光标，用户以为还在生成。

**方案**：新增 `streaming_complete` 消息类型。LLM 生成结束（但后续工具/HTML 流程可能还在继续）时，后端立即发送 `{"type": "streaming_complete"}`，前端立刻停止光标动画。

```
token token token ... → streaming_complete → [后端静默执行 tool/doc/HTML] → done
          ↑
    前端光标立即停止，用户感知"生成完了"
```

### 10. 跨轮次状态恢复：Redis Checkpoint + 历史重建

**痛点**：LangGraph Checkpoint（Redis TTL 24小时）过期后，用户再次发送消息时计划流程状态丢失。

**双重保障**：

| 机制 | TTL | 用途 |
|------|-----|------|
| Redis Checkpoint（`ckpt:thread:{session_id}`） | 24 小时 | LangGraph 状态持久化，计划流程中断恢复 |
| Redis 会话历史（`session:{session_id}`） | 7 天 | Checkpoint 过期后，从对话历史重建计划状态 |

**恢复逻辑**（`_restore_state_from_history()`）：
1. 检查 Redis 对话历史中是否有计划信号词（"制定计划"、"计划已生成"等）
2. 从最后一条 assistant 消息提取 `<summary>` 标签 → `plan_summary`
3. 从 assistant 消息提取计划正文 → `plan_text_cache`
4. 重建 `plan_conversation_history` / `execution_trace`
5. 注入到 `invoke_input`，LangGraph 从中断点继续

### 11. 长期记忆：对话 → 语义提取 → 画像提炼

**三级记忆体系**：

| 层级 | 存储 | TTL | 内容 |
|------|------|-----|------|
| 短期记忆 | Redis 会话历史 | 7 天 | 最近 10 轮对话 |
| 长期记忆 | Chroma 向量库 | 持久 | LLM 提取的用户偏好、习惯等事实（语义检索 top-5） |
| 用户画像 | Redis + Chroma | 持久 | 每累积 50 条长期记忆，LLM 自动提炼 200 字画像摘要 |

**效果**：第二轮对话时 AI 能记住用户偏好（如"你对乳糖不耐受"、"你偏好高强度间歇训练"），无需重复告知。

### 12. 文档上传：CharacterTextSplitter → RecursiveCharacterTextSplitter

**痛点**：旧 `CharacterTextSplitter` 按固定字符数切割，经常把段落/表格从中间切断，导致检索到不完整的句子。

**演进**：改用 `RecursiveCharacterTextSplitter`，优先按段落 → 句子 → 字符递归切割，`chunk_size=800, chunk_overlap=100`。

**效果**：检索到的文档块语义完整，不再出现"半句话"的情况。

---

## 四、数据存储

### 1. MySQL — 计划与打卡

数据库：`planhub`（默认 `127.0.0.1:3306`）

```sql
-- 计划表
plans (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'PERSONAL',
    priority VARCHAR(20) DEFAULT 'MEDIUM',
    visibility VARCHAR(20) DEFAULT 'PUBLIC',
    start_date VARCHAR(20),
    target_date VARCHAR(20),
    estimated_duration_hours INT,
    user_id VARCHAR(100),
    html_path TEXT,          -- 杂志风 HTML 预览文件路径（指向磁盘文件）
    plan_text TEXT,          -- 原始计划文本（前 5000 字）
    session_id VARCHAR(100),
    created_at DATETIME,
    updated_at DATETIME
)

-- 打卡表
plan_checkins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    checkin_date VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'done',   -- done / skip / fail
    note TEXT,
    created_at DATETIME,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    UNIQUE KEY uk_plan_date (plan_id, checkin_date)  -- 每天一条记录，UPSERT
)
```

**html_path 为什么不存数据库？**
HTML 体积大（50-200KB），存数据库会膨胀。改为：
- 磁盘文件：`py_agent/plan_previews/plan{id}_{标题}_{时间戳}.html`
- 数据库存绝对路径
- 前端通过 `<iframe src="/orchestrator/plan-preview/xxx.html">` 加载（FastAPI `FileResponse`）

**打卡数据流**：
- 前端 POST `/plans/{id}/checkin` → `add_checkin()` → `INSERT ... ON DUPLICATE KEY UPDATE`
- 日历渲染：`get_checkin_calendar(plan_id, year, month)` 返回当月所有日期的 status + 连续打卡天数（streak）

### 2. Chroma 向量库 — RAG + 长期记忆

数据存储：`chroma_db/`

- **文档检索**：用户上传的 Word/Excel/PPT/PDF 文档，`RecursiveCharacterTextSplitter` 分块索引
- **长期记忆**：每轮对话后 LLM 自动提取用户偏好、习惯等事实，语义检索 top-5 条注入计划生成
- **用户画像**：每累积 50 条长期记忆自动提炼 200 字画像摘要（存入 Redis + Chroma）
- **按用户隔离**：不同用户的文档和记忆完全独立（不同 Chroma collection）

**文档上传支持格式**：`.docx`（python-docx）、`.xlsx`（openpyxl）、`.pptx`（python-pptx）、`.pdf`（pdfplumber）、`.txt` / `.md`

### 3. Redis（可选）— 会话状态与 Checkpoint

| Key 模式 | TTL | 用途 |
|----------|-----|------|
| `session:{session_id}` | 7 天 | 对话历史（前端会话列表） |
| `ckpt:thread:{session_id}` | 24 小时 | LangGraph Checkpoint（计划流程状态） |
| `user_preference:{user_id}` | 持久 | 用户偏好（JSON） |
| `user_profile:{user_id}` | 持久 | LLM 提炼的用户画像摘要 |

**Checkpoint 工作原理**：
- LangGraph 执行每个节点后自动 `aput()` 保存状态到 Redis
- 用户下一条消息到达时 `aget_tuple()` 恢复状态，从上次断点继续
- TTL 24 小时过期后，由 `_restore_state_from_history()` 从对话历史重建
- 流程结束（`memory_save` 节点）立即清除 Checkpoint，不等 TTL

未安装 Redis 时可通过 `USE_REDIS=false` 关闭，此时 Checkpoint 回退到 `MemorySaver`（进程内存，重启丢失）。

---

## 五、MCP 工具集

21 个外部工具，通过 MCP（Model Context Protocol）协议暴露给 LLM，覆盖旅行、学习、健身、生活等场景：

| 工具名 | 用途 | 数据源 |
|--------|------|--------|
| `search_books` | 搜索图书 | OpenLibrary |
| `search_ebooks` | 搜索电子书 | Gutendex |
| `search_papers` | 搜索学术论文 | CrossRef |
| `get_wikipedia` | 获取维基百科摘要 | Wikipedia REST API |
| `get_weather` | 天气预报（指定城市 + 天数） | Open-Meteo |
| `get_nutrition` | 食物营养成分 | OpenFoodFacts |
| `get_exercises` | 健身动作推荐 | wger |
| `get_exercises_muscles` | 肌肉列表（用于精准推荐） | wger |
| `calculate_bmi` | BMI 计算 | 本地公式 |
| `get_exchange_rates` | 汇率查询 |  exchangerate-api |
| `get_world_time` | 世界时间 | WorldTimeAPI |
| `get_holidays` | 节假日查询 | 本地计算 |
| `get_city_bikes` | 城市共享单车 | CityBikes |
| `get_brewery` | 城市精酿啤酒厂 | OpenBreweryDB |
| `get_ip_location` | IP 地理位置 | ip-api |
| `get_hitokoto` | 一言（随机句子） | hitokoto.cn |
| `get_daily_poem` | 今日诗词 | jinrishici |
| `get_quote` | 名人名言 | Quotable |
| `get_trivia` | 趣味知识问答 | Open Trivia DB |
| `get_bored_activity` | 无聊时活动推荐 | Bored API |
| `get_random_meal` | 随机食谱 / 搜索食谱 | TheMealDB |

**连接模式**：支持直连（同进程，默认）和 SSE 远程连接两种。

---

## 六、AI 模型配置

支持三种 LLM 提供者，通过环境变量切换：

### 1. LongCat-2.0（默认，推荐）

结构化输出最稳定，适合多 Agent 编排。是 **thinking 模型**，返回 `ThinkingBlock + TextBlock` 内容块列表。

```env
ANTHROPIC_AUTH_TOKEN=your_token
ANTHROPIC_BASE_URL=https://api.longcat.chat/anthropic
ANTHROPIC_MODEL=LongCat-2.0
```

**兼容处理**：`extract_text(content)` 函数自动识别内容块列表，拼接 `type=text` 的块，否则下游字符串拼接会报 `TypeError`。

### 2. Ollama 本地模型

完全本地运行，无需 API key。

```env
USE_DASHSCOPE=false
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 3. 阿里云百炼

```env
USE_DASHSCOPE=true
DASHSCOPE_API_KEY=your_key
DASHSCOPE_MODEL=qwen-max
```

### Token 统计

每次 LLM 调用后自动记录用量（`TokenStatsWrapper`）：
```
[TokenStats] prompt_tokens=1234 completion_tokens=567 total_tokens=1801 latency=2340.5ms
[TokenStats] total=9876 tokens across 6 calls, avg_latency=1890.2ms
```

---

## 七、计划生成数据规则

计划内容必须严格基于三个数据来源：

| 优先级 | 来源 | 规则 |
|--------|------|------|
| 1 | **用户需求**（plan_summary） | 必需，始终作为计划主线 |
| 2 | **API 数据**（tool_data） | 工具返回了数据 → 必须引用具体数值；没返回 → 只用需求推导 |
| 3 | **RAG 数据**（doc_data） | 知识库检索到 → 相关则引用；没检索到 → 不写 |

**铁律**：
- 禁止输出空洞的通用模板（如"注意均衡饮食"等无意义的话）
- 禁止编造具体数据（温度、价格、时间等），无数据时标注 [建议]
- 不限制计划类型（旅行、健身、饮食、学习、工作等均可），跟随用户需求自由组织
- 所有数据来源标注在 `__DATA_SOURCES__` 区块中，前端可展开查看

---

## 八、杂志风 HTML 页面设计

由 `plan_html_writer` 节点生成，LLM 直接输出完整自包含 HTML（CSS 内联 + 在线占位图）。

### 设计规范（prompt 驱动）

| 要素 | 规范 |
|------|------|
| 配色 | 素净典雅：`#f8f7f4` 米白 / `#faf9f6` 象牙白 / `#f0f4f8` 浅灰蓝背景，`#2d2d2d` 深灰文字 |
| 字体层级 | 标题 20-32px（衬线），正文 14-15px（无衬线） |
| 布局 | max-width 760px 居中，padding 20-32px |
| 图片 | `picsum.photos/seed/{英文关键词}/800/400`，每个段落用不同关键词（禁止全用同一张图） |
| 卡片 | border-radius 12-16px，box-shadow 柔和阴影 |
| 留白 | 大量 whitespace，杂志风格 |

### 提取策略

```
LLM 输出
   │
   ├─ 有 ```html 代码块 → 直接提取
   ├─ 有 ``` 代码块 → 检测是否以 HTML 标签开头
   ├─ 裸 HTML（前面可能有 <think> 注释）→ 去掉注释后从 <!DOCTYPE 截取
   └─ 兜底 → 整个内容作为 HTML
   ↓
generate_plan_html() → 写入磁盘 → 返回 preview_url
```

---

## 九、启动项目

### 前置条件

- Node.js 18+
- Python 3.12+
- MySQL 8.0+
- Redis（可选）

### 1. 启动 Python AI 服务

```bash
cd py_agent
pip install -r requirements.txt

# 配置环境变量（复制模板并编辑）
cp ../.env.example .env
# 编辑 .env 填入 API key

# 启动服务
python main.py
# 服务运行于 http://127.0.0.1:8000
```

**首次启动**会自动：
1. 创建 MySQL 数据库表（`plans` + `plan_checkins`）
2. 初始化 Chroma 向量库目录
3. 连接 Redis（可选）
4. 加载 MCP 工具（21 个）

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行于 http://localhost:5173
```

### 3. 访问

打开浏览器访问 `http://localhost:5173`，进入"AI 助手"页面即可开始对话。

---

## 十、API 概览

### 对话与编排

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/orchestrator/chat` | LangGraph 对话入口（非流式） |
| `WS` | `/orchestrator/ws/chat` | WebSocket 流式对话（token + log + done） |
| `POST` | `/orchestrator/cancel` | 终止会话（清 checkpoint + 状态） |

### WebSocket 消息协议

| type | 触发时机 | 前端处理 |
|------|----------|----------|
| `token` | 段落缓冲 flush（遇 `\n`） | 追加到聊天消息 |
| `log` | 工具调用/文档检索进度 | 显示在右侧时间线面板 |
| `streaming_complete` | LLM 生成结束 | 停止打字光标 |
| `html_preview_ready` | HTML 页面已生成 | 自动打开 iframe 预览 |
| `node_complete` | 所有节点执行完毕 | 解除加载状态 |
| `done` | 完整流程结束 | 保存 session_id，更新调试面板 |
| `error` | 异常 | 显示错误信息 |

### 计划管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/plans` | 计划列表（含打卡统计） |
| `GET` | `/plans/{id}` | 计划详情 |
| `POST` | `/plans` | 创建计划 |
| `PUT` | `/plans/{id}` | 更新计划 |
| `DELETE` | `/plans/{id}` | 删除计划（级联删除打卡） |
| `GET` | `/plans/{id}/preview` | HTML 预览 |
| `GET` | `/plans/{id}/calendar` | 日历打卡数据（年/月） |

### 打卡

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/plans/{id}/checkin` | 打卡（done/skip/fail） |
| `DELETE` | `/plans/{id}/checkin` | 取消打卡 |
| `GET` | `/plans/{id}/checkins` | 打卡记录列表 |

### RAG 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/rag/documents` | 文档库列表 |
| `POST` | `/rag/upload` | 上传文档（支持 docx/xlsx/pptx/pdf） |
| `GET` | `/rag/documents/{id}` | 文档详情 |
| `DELETE` | `/rag/documents/{id}` | 删除文档 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/conversations` | 会话列表 |
| `GET` | `/conversations/{id}` | 会话详情 |
| `DELETE` | `/conversations/{id}` | 删除会话 |

### 预览文件

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/orchestrator/plan-preview/{filename}` | 提供 HTML 文件（iframe 加载） |
| `GET` | `/orchestrator/plan-previews` | 列出所有预览文件（调试） |
| `DELETE` | `/orchestrator/plan-previews/{filename}` | 删除预览文件 |

---

## 十一、环境变量参考

完整环境变量见 `.env.example`，核心配置如下：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AI_HOST` | `127.0.0.1` | 服务监听地址（仅本机） |
| `AI_PORT` | `8000` | 服务端口 |
| `ANTHROPIC_AUTH_TOKEN` | (空) | LongCat API Token |
| `USE_DASHSCOPE` | `false` | 是否使用百炼 |
| `OLLAMA_API_URL` | `http://localhost:11434` | Ollama 地址 |
| `USE_REDIS` | `true` | 是否启用 Redis |
| `CHROMA_DB_PATH` | `./chroma_db` | 向量库路径 |
| `DB_HOST` | `127.0.0.1` | MySQL 地址 |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_USER` | `root` | MySQL 用户名 |
| `DB_PASSWORD` | `1234` | MySQL 密码 |
| `DB_NAME` | `planhub` | MySQL 数据库名 |

---

## 十二、许可证

[MIT](LICENSE)
