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
                                        ├── SQLite    (计划/打卡数据)
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
| 存储 | SQLite（计划数据）+ Chroma（向量库）+ Redis（可选，会话状态） |

### 3. 目录结构

```
planhub/
├── frontend/                # React 前端
│   └── src/
│       ├── pages/           # 页面组件
│       │   ├── LangGraphTest.tsx   # AI 对话 + 计划预览
│       │   ├── PlanLibrary.tsx     # 计划库
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
│       │   │   └── plan_store.py    # SQLite 存储
│       │   ├── common/      # 工具定义、LLM 工厂
│       │   ├── mcp/         # MCP 工具适配器
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
       │  输出: ranked_tools = [{tool:"get_weather", params:{city:"杭州"}}, ...]
       │
       ├──→ tool_executor（并行）──→ 调用外部 API → 返回天气/营养/运动数据
       │                                   │
       │                         tool_data_parts = ["天气信息（杭州）...", ...]
       │
       └──→ doc_retriever（并行）──→ 从文档知识库检索相关知识点
                                           │
                                 doc_data_parts = ["[来源: 文档1#3]: ...", ...]
                                           │
                                 ┌─────────▼─────────┐
                                 │     plan_writer     │ ← 等 tool + doc 都完成
                                 └───────┬─────────────┘
                                         │
                               plan_text_cache（纯文本计划，供用户审阅）
                                         │
                                         ▼
                               plan_confirmation（展示计划，询问"是否创建？"）
                                         │ 用户点确认
                                         ▼
                               plan_html_writer（生成杂志风 HTML 页面）
                                         │
                                         ▼
                               extract_plan_title（提取计划标题）
                                         │
                                         ▼
                               create_plan_to_platform（保存到 SQLite）
                                         │
                                         ▼
                                    memory_save → END
```

**设计要点**：
- `plan_writer` 只输出纯文本计划（流式打字机效果），不生成 HTML
- 用户审阅文本计划后点击确认，才触发 `plan_html_writer` 生成杂志风 HTML
- HTML 展示在右侧预览面板（iframe），不出现在聊天区域

### 3. ReAct 自动参数补全

当工具调用因参数模糊失败时（如用户说"高蛋白低碳水"但未指定具体食物），LLM 会：

1. **分析失败原因** — 提取错误信息中的关键词
2. **推断具体参数** — 根据用户需求推断出鸡胸肉、鸡蛋、三文鱼等高蛋白食材
3. **自动重试** — 用新参数重新调用工具，不询问用户

```
tool_executor 调用 get_nutrition("高蛋白低碳水")
       │
       ▼
  失败：参数"高蛋白低碳水"不是具体食物名
       │
       ▼
  ReAct 推理："用户要低碳水高蛋白饮食 → 推荐鸡胸肉、鸡蛋、三文鱼"
       │
       ▼
  重试 get_nutrition("鸡胸肉") → 成功返回营养数据
```

只对**参数模糊类错误**做 ReAct（"未找到"、"缺少"、"无效"等），网络错误不重试。每个工具最多重试一次。

### 4. 节点说明

| 节点 | 职责 |
|------|------|
| `memory_load` | 从 Redis 加载短期记忆 + 从 Chroma 语义检索长期记忆 |
| `supervisor` | 意图分类（plan_creation / rag / chat / clarify）+ 6 层优先级路由 |
| `plan_mode_confirm` | 询问用户是否开启计划收集模式 |
| `plan_generator` | LLM 多轮对话收集用户需求，自动追问缺失信息 |
| `parameter_extractor` | 从 MCP 获取工具 schema，LLM 选择工具 + 提取参数 |
| `tool_executor` | 并行调用外部 API，支持 ReAct 自动补参重试 |
| `doc_retriever` | 从用户上传的文档知识库检索相关内容 |
| `plan_writer` | 综合所有数据生成纯文本计划（流式输出） |
| `plan_confirmation` | 展示文本计划，等待用户确认 |
| `plan_html_writer` | 将文本计划转为杂志风 HTML 页面 |
| `extract_plan_title` | LLM 提取计划标题 |
| `create_plan_to_platform` | 保存计划到 SQLite |
| `rag` | 文档知识库检索问答 |
| `chat` | 闲聊/通用问答 |
| `memory_save` | 保存对话历史 + 提取长期记忆 + 清理 checkpoint |

---

## 三、数据存储

### 1. SQLite — 计划与打卡

数据库文件：`py_agent/data/plans.db`

```sql
-- 计划表
plans (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'PERSONAL',
    priority TEXT DEFAULT 'MEDIUM',
    visibility TEXT DEFAULT 'PUBLIC',
    start_date TEXT,
    target_date TEXT,
    estimated_duration_hours INTEGER,
    user_id TEXT,
    html_path TEXT          -- 杂志风 HTML 预览文件路径
)

-- 打卡表
plan_checkins (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER,
    checkin_date TEXT,
    status TEXT,            -- done / skipped / partial
    note TEXT
)
```

### 2. Chroma 向量库 — RAG + 长期记忆

数据存储：`chroma_db/`

- **文档检索**：用户上传的 Word/Excel/PPT/PDF 文档分块索引
- **长期记忆**：每轮对话后自动提取用户偏好、习惯等事实，语义检索 top-K 条注入计划生成
- **用户画像**：每累积 50 条长期记忆自动提炼画像摘要

### 3. Redis（可选）— 会话状态

对话历史和 LangGraph Checkpoint 存储在 Redis，支持 TTL 自动过期：

| Key 模式 | TTL | 用途 |
|----------|-----|------|
| `session:{session_id}` | 7 天 | 对话历史（前端会话列表） |
| `ckpt:thread:{session_id}` | 24 小时 | LangGraph 状态 checkpoint |
| `user_preference:{user_id}` | 持久 | 用户偏好 |

未安装 Redis 时可通过 `USE_REDIS=false` 关闭，此时会话状态仅存在于内存。

---

## 四、AI 模型配置

支持三种 LLM 提供者，通过环境变量切换：

### 1. LongCat-2.0（默认，推荐）

结构化输出最稳定，适合多 Agent 编排。

```env
ANTHROPIC_AUTH_TOKEN=your_token
ANTHROPIC_BASE_URL=https://api.longcat.chat/anthropic
ANTHROPIC_MODEL=LongCat-2.0
```

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

---

## 五、启动项目

### 前置条件

- Node.js 18+
- Python 3.12+
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

## 六、API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/orchestrator/chat` | LangGraph 对话入口（非流式） |
| `WS` | `/orchestrator/ws` | WebSocket 流式对话 |
| `GET` | `/plans` | 计划列表 |
| `GET` | `/plans/{id}` | 计划详情（含 HTML 预览） |
| `POST` | `/plans/{id}/checkin` | 打卡 |
| `GET` | `/rag/documents` | 文档库列表 |
| `POST` | `/rag/upload` | 上传文档 |
| `GET` | `/conversations` | 会话列表 |
| `GET` | `/health` | 健康检查 |

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

---

## 八、环境变量参考

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

---

## 九、许可证

[MIT](LICENSE)
