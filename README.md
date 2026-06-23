# PlanHub - AI驱动的计划管理与社交平台

<div align="center">

**基于LangGraph构建多Agent编排系统，支持智能计划生成、社区互动和知识库问答**

[![Java](https://img.shields.io/badge/Java-17-blue.svg)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2.0-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.6-blue.svg)](https://react.dev.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 一、项目结构

```
planhub2.0/
├── .env.example                  # 环境变量模板
├── README.md                     # 项目文档
├── planhub_schema.sql            # 数据库建表脚本
├── backend/                      # Java后端模块
│   └── src/main/java/com/planhub/
│       ├── config/               # 配置类（JWT、安全、AI等）
│       ├── controller/           # REST控制器（16个）
│       ├── service/              # 业务逻辑层
│       ├── entity/               # 数据库实体（17个）
│       └── mapper/               # MyBatis映射器
├── frontend/                     # React前端模块
│   └── src/
│       ├── pages/                # 页面组件（21个）
│       ├── components/           # 通用组件（6个）
│       ├── services/             # API服务层
│       └── types/                # TypeScript类型定义
└── py_agent/                     # Python AI服务模块
    └── src/app/
        ├── api/                  # API路由（5个）
        ├── orchestrator/         # LangGraph编排器
        │   ├── graph.py          # 图结构定义
        │   ├── nodes/            # 11个节点实现
        │   ├── state.py          # 状态定义
        │   └── memory_bridge.py  # 记忆桥接
        ├── service/              # 业务服务（8个）
        └── common/               # 公共工具
```


## 二、核心特性

### 1. 多Agent编排系统（LangGraph）
基于LangGraph构建ReAct状态机，设计多Agent动态路由策略：
- **计划生成Agent**：自动提取用户意图，生成结构化计划
- **智能助手Agent**：通过Function Calling自动调用后端API完成社区操作
- **知识库Agent**：基于混合检索的智能问答
- **意图识别**：自动识别用户意图并路由到对应的Agent

### 2. Tool Calling智能助手
实现Tool Calling智能助手系统，支持15+社区操作：
- 创建计划、发布帖子、搜索内容、计划打卡
- 通过Function Calling自动调用后端API完成任务

### 3. 三层记忆架构
在Redis中构建三层记忆架构，实现跨会话上下文理解：
- **短期对话历史**：存储最近20条对话消息
- **工作记忆状态**：记录当前任务执行状态
- **用户偏好摘要**：长期积累的用户偏好和行为模式

### 4. 混合检索RAG系统
- **BM25关键词检索** + **向量相似度检索** + **LLM重排优化**
- 支持PDF/DOCX/PPTX/XLSX文档解析

### 5. 双后端安全架构
- Java后端负责业务逻辑与JWT鉴权
- Python后端专注AI处理，仅监听127.0.0.1
- 确保AI服务零外部暴露


## 三、技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19 + TypeScript + Vite 8 + Ant Design 6 |
| **Java后端** | Spring Boot 3.2 + MyBatis-Plus + JWT + MySQL 8.0 + Redis 7.0 |
| **Python AI** | FastAPI + LangChain + LangGraph + ChromaDB + Ollama/DashScope |


## 四、快速开始

### 环境要求
- **JDK**：17+
- **Python**：3.12+
- **Node.js**：18+
- **MySQL**：8.0+
- **Redis**：5.0+

### 克隆项目
```bash
git clone https://gitee.com/xuzhichengchxy/planhub.git
cd planhub
```

### 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入你的配置
```

### 初始化数据库
```bash
mysql -u root -p -e "CREATE DATABASE planhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p planhub < planhub_schema.sql
```

### 启动服务
```bash
# 1. 启动Java后端
cd backend && mvn clean package -DskipTests && java -jar target/planhub-backend-1.0.0.jar

# 2. 启动Python AI服务
cd py_agent && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python main.py

# 3. 启动前端
cd frontend && npm install && npm run dev
```

### 访问应用
打开浏览器访问：**http://localhost:5173**



## 五、Java后端（Spring Boot）

### 安全网关模式
Java后端作为AI服务的安全网关，负责验证JWT后转发到Python：
- 前端请求携带JWT Token
- Java后端验证Token，提取用户ID
- 添加内部密钥（X-Internal-Api-Secret）
- 转发到Python AI服务（仅监听127.0.0.1）

### 用户认证
- JWT Token生成/验证/刷新
- BCrypt密码加密
- Token有效期：访问令牌1小时，刷新令牌24小时

### 计划打卡业务
- 实现打卡记录、进度计算、照片上传
- 支持计划创建/编辑/删除
- 自动计算完成进度百分比

### 社区互动业务
- 帖子管理、点赞分享
- 评论系统
- 用户活动Feed流

### 数据权限隔离
- 所有查询基于user_id过滤
- 确保数据安全性


## 六、AI助手系统

### 三个层次的AI助手

#### 1. ChatBot（智能对话助手）
- 基于LangChain的对话系统
- 支持多轮对话和上下文记忆
- 流式响应（SSE）


1. ChatBot（智能对话助手）流程图


```text
┌─────────────────────────────────────────────────────────────┐
│                     用户输入问题                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   模式选择开关        │
              │  (plan_mode / rag)   │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              │              ▼
   ┌─────────────┐       │       ┌─────────────┐
   │ 计划模式开启 │       │       │ RAG模式开启  │
   └──────┬──────┘       │       └──────┬──────┘
          │              │              │
          ▼              │              ▼
   ┌─────────────┐       │       ┌─────────────┐
   │ 构建计划提示 │       │       │ 检索知识库  │
   │ 词+上下文    │       │       │ (向量+BM25) │
   └──────┬──────┘       │       └──────┬──────┘
          │              │              │
          │              ▼              │
          │       ┌─────────────┐       │
          │       │ 普通对话模式 │       │
          │       │ (默认状态)  │       │
          │       └──────┬──────┘       │
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  LangChain处理       │
              │  ChatOpenAI /        │
              │  ChatOllama          │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  对话记忆管理         │
              │  ConversationBuffer  │
              │  WindowMemory        │
              │  (保留最近10轮)      │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │     返回响应          │
              └──────────────────────┘
```

**核心特性：**
- **计划模式开关**：用户可开启计划生成模式，自动提取意图生成结构化计划
- **知识库模式开关**：用户可开启RAG模式，基于文档库进行智能问答
- **文档管理**：支持上传、管理PDF/DOCX/PPTX/XLSX文档
- **模式切换**：支持实时切换不同AI能力，无需重启对话

**LangChain应用：**
- **对话管理**：使用`ChatOpenAI`/`ChatOllama`构建对话系统，支持多轮对话
- **上下文记忆**：通过`ConversationBufferWindowMemory`保留最近20条对话历史
- **提示词工程**：动态拼接系统提示词 + 历史对话 + 用户输入
- **流式响应**：使用`stream()`方法实现SSE流式输出，提升用户体验
- **Token控制**：每次调用记录Token消耗，自动压缩历史对话控制成本

#### 2. Assistant（智能助手）
- 基于LangChain Tool Calling
- 支持15+社区操作（发帖、搜索、打卡、查看活动等）
- 自动调用后端API完成任务


2. Assistant（智能助手）流程图


```text
┌─────────────────────────────────────────────────────────────┐
│                     用户输入请求                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   解析用户意图        │
              │  (15+工具函数定义)   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  LangChain Tool      │
              │  Calling 选择工具    │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         │               │               │               │
         ▼               ▼               ▼               ▼
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │ 计划管理    │ │ 社区互动    │ │ 用户信息    │ │ 统计分析    │
  │ 工具调用    │ │ 工具调用    │ │ 工具调用    │ │ 工具调用    │
  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
         │               │               │               │
         ▼               ▼               ▼               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              调用 Java Spring Boot API                      │
  │  (通过 HTTP 请求后端接口)                                    │
  └────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
              ┌──────────────────────┐
              │   MySQL 数据库       │
              │   执行增删改查       │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   返回操作结果        │
              │   格式化响应          │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │     返回给用户          │
              └──────────────────────┘

可用工具列表：
- create_plan()        : 创建新计划
- update_plan()        : 更新计划
- delete_plan()        : 删除计划
- get_plan()           : 获取计划详情
- list_plans()         : 列出用户计划
- create_post()        : 发布社区帖子
- like_post()          : 点赞帖子
- comment_post()       : 评论帖子
- follow_user()        : 关注用户
- get_user_profile()   : 获取用户信息
- update_user_profile() : 更新用户信息
- get_statistics()     : 获取统计数据
```

**LangChain Tool Calling应用：**
- **工具定义**：使用`@tool`装饰器定义15+社区操作工具（发帖、搜索、打卡等）
- **自动调用**：LLM根据用户输入自动选择并调用合适的工具
- **参数提取**：LLM自动从自然语言中提取工具所需参数
- **结果格式化**：工具返回结果自动格式化为用户友好的响应

#### 3. LangGraph Orchestrator（多Agent编排器）
基于LangGraph构建的**统一编排系统**，整合ChatBot、Assistant和RAG三个AI能力：


3. LangGraph Orchestrator（多Agent编排器）流程图


```text
┌─────────────────────────────────────────────────────────────┐
│                     用户输入问题                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  ① memory_load      │
              │  加载记忆上下文      │
              │  - 短期记忆(20条)   │
              │  - 工作记忆(任务态) │
              │  - 用户偏好         │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  ② supervisor       │
              │  意图分类与路由      │
              │  支持10种意图:       │
              │  learning/health/   │
              │  travel/work/       │
              │  finance/rag/chat.. │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         │               │               │               │
         ▼               ▼               ▼               ▼
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
  │ 创建计划    │ │ 社区互动    │ │ 知识问答    │ │ 闲聊       │
  │ 流程        │ │ 流程        │ │ 流程        │ │ 流程       │
  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
         │               │               │               │
         ▼               │               │               │
  ┌─────────────┐        │               │               │
  │ ③ plan_mode │        │               │               │
  │   _confirm  │        │               │               │
  │  计划模式   │        │               │               │
  │  确认       │        │               │               │
  └──────┬──────┘        │               │               │
         │ 是            │               │               │
         ▼               │               │               │
  ┌─────────────┐        │               │               │
  │ ④ plan_     │        │               │               │
  │  generator  │        │               │               │
  │  生成计划   │        │               │               │
  │  详细内容   │        │               │               │
  └──────┬──────┘        │               │               │
         │               │               │               │
         ▼               │               │               │
  ┌─────────────┐        │               │               │
  │ ⑤ plan_     │        │               │               │
  │ confirmation│        │               │               │
  │  计划确认   │        │               │               │
  └──────┬──────┘        │               │               │
         │ 确认           │               │               │
         ▼               │               │               │
  ┌─────────────┐        │               │               │
  │ ⑥ extract_  │        │               │               │
  │  plan_title │        │               │               │
  │  提取计划   │        │               │               │
  │  标题       │        │               │               │
  └──────┬──────┘        │               │               │
         │               │               │               │
         ▼               │               │               │
  ┌─────────────┐        │               │               │
  │ ⑦ create_   │        │               │               │
  │  plan_to_   │        │               │               │
  │  platform   │        │               │               │
  │  保存计划   │        │               │               │
  │  到平台     │        │               │               │
  └──────┬──────┘        │               │               │
         │               │               │               │
         └───────────────┼───────────────┼───────────────┘
                         │
                         │  (其他流程直接汇聚)
                         │
                         ▼
              ┌──────────────────────┐
              │  ⑨ rag / assistant  │
              │      / chat         │
              │   (执行具体任务)    │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  ⑩ memory_save      │
              │  保存记忆到Redis     │
              │  - 更新短期记忆     │
              │  - 更新工作记忆     │
              │  - 更新用户偏好     │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │       END            │
              │    返回响应          │
              └──────────────────────┘

记忆系统架构：
┌─────────────────────────────────────────────────────────────┐
│                     三层记忆架构                              │
├─────────────────────────────────────────────────────────────┤
│ 短期记忆 (Short-term)                                       │
│  - Redis List存储，保留最近20条消息                        │
│  - TTL: 2小时                                               │
│  - 用于上下文理解                                           │
├─────────────────────────────────────────────────────────────┤
│ 工作记忆 (Working Memory)                                    │
│  - Redis String存储，当前任务状态                           │
│  - TTL: 1小时                                               │
│  - 用于多步骤任务追踪                                       │
├─────────────────────────────────────────────────────────────┤
│ 用户偏好 (User Preference)                                   │
│  - Redis String存储，持久化                                 │
│  - 无过期时间                                               │
│  - 用于个性化推荐                                           │
└─────────────────────────────────────────────────────────────┘
```

**核心架构：**

1. **状态机设计**
   - 使用`StateGraph`定义完整的Agent工作流
   - 每个节点是一个异步函数，接收`AgentState`返回更新
   - 支持条件路由、循环、并行执行

2. **节点实现（11个节点）**

| 节点名称 | 功能 | 说明 |
|---------|------|------|
| `memory_load` | 记忆加载 | 从Redis加载三层记忆（短期、工作、偏好） |
| `supervisor` | 意图识别 | 使用LLM进行意图分类，决定路由到哪个Agent |
| `plan_mode_confirm` | 计划模式确认 | 询问用户是否开启计划生成模式 |
| `plan_generator` | 计划生成 | 收集信息（目标、时间、偏好），生成结构化计划 |
| `plan_confirmation` | 计划确认 | 展示计划，询问用户是否创建到平台 |
| `extract_plan_title` | 提取标题 | 从生成的计划中提取标题 |
| `create_plan_to_platform` | 创建到平台 | 调用Java后端API创建计划 |
| `assistant` | 智能助手 | 执行Tool Calling，调用Java API完成社区操作 |
| `rag` | 知识库查询 | 查询Chroma向量数据库 + BM25索引 |
| `chat` | 简单对话 | 处理闲聊、问候等 |
| `memory_save` | 记忆保存 | 保存对话和状态到Redis |

3. **边（Edges）定义**

**条件边（Conditional Edges）：**
```python
# Supervisor → 根据意图路由
workflow.add_conditional_edges(
    "supervisor",
    route_by_intent,
    {
        "plan_mode_confirm": "plan_mode_confirm",  # 计划相关意图
        "assistant": "assistant",                  # 社区操作意图
        "rag": "rag",                              # 知识库查询意图
        "chat": "chat",                            # 闲聊
    }
)

# Plan Generator → 根据生成状态路由
workflow.add_conditional_edges(
    "plan_generator",
    route_after_plan_generator,
    {
        "plan_confirmation": "plan_confirmation",  # 计划已生成，等待确认
        "memory_save": "memory_save",              # 继续收集信息
    }
)

# Plan Confirmation → 根据用户选择路由
workflow.add_conditional_edges(
    "plan_confirmation",
    route_after_plan_confirmation,
    {
        "extract_plan_title": "extract_plan_title",  # 用户确认创建
        "memory_save": "memory_save",                  # 用户拒绝
    }
)
普通边（Normal Edges）：


# 记忆加载 → 意图识别
workflow.add_edge("memory_load", "supervisor")

# 计划标题提取 → 创建到平台
workflow.add_edge("extract_plan_title", "create_plan_to_platform")

# 创建完成 → 保存记忆
workflow.add_edge("create_plan_to_platform", "memory_save")

# 各Agent执行完成 → 保存记忆
workflow.add_edge("assistant", "memory_save")
workflow.add_edge("rag", "memory_save")
workflow.add_edge("chat", "memory_save")

# 记忆保存完成 → 结束
workflow.add_edge("memory_save", END)
意图识别（Supervisor节点）

使用结构化输出的LLM进行意图分类
支持10种意图：学习计划、健康计划、旅行计划、工作计划、财务计划、知识库查询、社区操作、闲聊等
自动识别上下文状态（如正在收集计划信息、等待用户确认等）
关键规则：检测到正在进行的任务时，自动路由回对应节点继续执行
提示词拼接策略

系统提示词：定义AI角色、能力范围、输出格式
上下文注入：动态注入用户记忆、历史对话、当前状态
工作流提示：根据当前节点（如plan_generator）加载专用提示词
多轮拼接：保留最近20条对话历史，控制Token消耗
记忆系统设计

短期记忆（Redis）：最近20条对话，TTL 2小时
工作记忆（Redis）：当前任务状态（如收集计划信息进度），TTL 1小时
用户偏好（Redis）：长期积累的用户偏好，持久化存储
会话索引（Redis）：前端会话列表，TTL 7天
状态管理（AgentState）


class AgentState(TypedDict):
    user_input: str              # 用户输入
    session_id: str              # 会话ID
    user_id: str                 # 用户ID
    intent: str                  # 识别的意图
    selected_agent: str          # 选中的Agent
    short_term_memory: list      # 短期记忆
    working_memory: dict         # 工作记忆
    user_preference: str         # 用户偏好
    execution_trace: list        # 执行追踪
    capabilities: dict           # 能力开关
```
错误处理和降级

每个节点都有try-catch错误处理
主LLM失败时自动降级到备用模型（阿里云→Ollama）
降级到简单对话模式确保服务可用性
编排流程示例：

场景1：用户说"帮我制定一个学习计划"
1. memory_load → 从Redis加载用户记忆和历史对话
2. supervisor → 识别意图为"learning"，路由到 plan_mode_confirm
3. plan_mode_confirm → 询问用户确认开启计划模式
4. 用户确认 → 路由到 plan_generator
5. plan_generator → 收集信息（目标、时间、偏好）
6. plan_confirmation → 展示计划，询问是否创建
7. 用户确认 → extract_plan_title → create_plan_to_platform
8. memory_save → 保存对话和状态到Redis
9. END → 返回结果


场景2：用户说"搜索关于Python的文档"
1. memory_load → 加载记忆
2. supervisor → 识别意图为"rag"，路由到 rag节点
3. rag → 查询Chroma向量数据库 + BM25索引
4. memory_save → 保存查询记录
5. END → 返回搜索结果


场景3：用户说"帮我发个帖子"
1. memory_load → 加载记忆
2. supervisor → 识别意图为"assistant"，路由到 assistant节点
3. assistant → 调用Function Calling，自动调用Java后端API
4. memory_save → 保存操作记录
5. END → 返回操作结果

## 六、RAG知识库系统

### 1. 整体架构
```text
用户问题
↓
┌─────────────────────────────────────────────────────────────┐
│                       RAG Pipeline                          │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   文档加载   │ →  │   文档分割   │ →  │  向量化存储  │  │
│  │   Loader     │    │   Splitter   │    │   ChromaDB   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   问题嵌入   │ →  │   混合检索   │ →  │   LLM重排    │  │
│  │  Embedding   │    │  BM25+向量   │    │   Rerank     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                               ↓                             │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │  上下文压缩  │ →  │   LLM生成    │ →  返回答案          │
│  │ Compression  │    │   Generate   │                      │
│  └──────────────┘    └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```


### 2. 文档加载（Document Loaders）

支持多种文档格式，使用LangChain的文档加载器：

| 文档格式 | 加载器 | 说明 |
|---------|--------|------|
| **PDF** | `PyPDFLoader` | 提取文本内容，保留页面结构 |
| **DOCX** | `Docx2txtLoader` | 提取Word文档文本 |
| **PPTX** | `UnstructuredPowerPointLoader` | 提取PPT文本内容 |
| **XLSX** | `UnstructuredExcelLoader` | 提取Excel表格数据 |
| **TXT** | `TextLoader` | 纯文本文件 |
| **批量加载** | `DirectoryLoader` | 批量加载目录下所有文档 |

**代码示例：**
```python
from langchain_community.document_loaders import (
    PyPDFLoader, Docx2txtLoader, 
    UnstructuredPowerPointLoader, UnstructuredExcelLoader
)

# 根据文件类型选择加载器
LOADERS = {
    '.pdf': PyPDFLoader,
    '.docx': Docx2txtLoader,
    '.pptx': UnstructuredPowerPointLoader,
    '.xlsx': UnstructuredExcelLoader,
    '.txt': TextLoader,
}

def load_document(file_path: str) -> List[Document]:
    """加载文档并返回Document对象列表"""
    ext = Path(file_path).suffix.lower()
    loader_class = LOADERS.get(ext, TextLoader)
    loader = loader_class(file_path)
    return loader.load()
```
### 3. 文档分割（Text Splitting）
使用递归字符分割器（RecursiveCharacterTextSplitter），优先按语义单元分割：
```python
分割策略：


from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # 每个块500个字符
    chunk_overlap=50,         # 相邻块重叠50个字符（保持上下文连贯）
    separators=[              # 分割优先级：段落→句子→标点→空格
        "\n\n",               # 1. 优先按段落分割
        "\n",                 # 2. 其次按换行分割
        "(?<=[。！？!?；;])", # 3. 按中文标点分割
        ",",                  # 4. 按逗号分割
        " ",                  # 5. 最后按空格分割
        ""                    # 6. 兜底：强制字符分割
    ]
)
```

分割原理：

chunk_size=500：每个文档块约500个字符，平衡语义完整性和检索精度
chunk_overlap=50：相邻块重叠50字符，避免关键信息被切断
多级分隔符：优先按段落、句子等语义单元分割，避免从句子中间切断

分割示例：
```

原始文档（2000字）：
├─ 段落1（300字）
├─ 段落2（600字） → 分割为 chunk1(500字) + chunk2(150字，与chunk1重叠50字)
├─ 段落3（800字） → 分割为 chunk3(500字) + chunk4(350字，与chunk3重叠50字)
└─ 段落4（300字） → chunk5(300字，与chunk4重叠50字)
```
### 4. 向量化存储（Vector Storage）
使用ChromaDB作为向量数据库，存储文档嵌入向量：

嵌入模型：

本地模型：Ollama bge-m3（推荐，免费，效果好）
云端模型：DashScope text-embedding-v2（阿里云百炼）
存储结构：

```python
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# 创建嵌入模型
embeddings = OllamaEmbeddings(
    base_url="http://localhost:11434",
    model="bge-m3"
)

# 创建向量存储
vector_store = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

# 添加文档
vector_store.add_documents(documents)

# 相似度检索
results = vector_store.similarity_search(query, k=8)
```
每个文档块存储的元数据：
```json

{
    "filename": "example.pdf",
    "doc_id": "example",
    "chunk_index": 0,
    "total_chunks": 5,
    "upload_time": "2024-01-01T12:00:00"
}
```
### 5. 混合检索（Hybrid Retrieval）
结合BM25关键词检索和向量相似度检索，提高检索准确率：

（1）BM25关键词检索

```python
# BM25 词频表结构
bm25_index = {
    "doc_chunk_key": {
        "filename": "example.pdf",
        "doc_id": "example",
        "tf": {"Python": 3, "学习": 5, "计划": 2},  # 词频
        "length": 500,  # 文档块长度
        "content": "..."  # 原始内容
    }
}

# BM25 评分公式
score = IDF(term) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_length / avg_length)))
```
（2）向量相似度检索

```python
# 使用余弦相似度
query_embedding = embeddings.embed_query(query)
results = vector_store.similarity_search_by_vector(query_embedding, k=20)
```
（3）混合策略

先使用BM25检索top-20候选
再使用向量检索top-20候选
合并去重后，使用LLM重排选择top-8
### 6. LLM重排序（Rerank）
使用大模型对候选文档进行精排，选择最相关的文档：

重排流程：
```python

async def rerank_with_llm(query: str, documents: List[Document], top_k: int = 8):
    """使用LLM对文档进行重排序"""
    
    # 构建重排提示词
    prompt = f"""给定用户问题和以下文档，请按相关性排序（最相关的排前面）。

用户问题：{query}

文档：
{chr(10).join([f'{i+1}. {doc.page_content[:200]}...' for i, doc in enumerate(documents)])}

请返回最相关的{top_k}个文档编号（如：1,3,5,2...）："""
    
    # 调用LLM
    llm = get_llm()
    response = await llm.ainvoke(prompt)
    
    # 解析结果，返回重排后的文档
    ranked_indices = parse_ranking(response.content)
    return [documents[i] for i in ranked_indices[:top_k]]
```
### 7. 上下文压缩（Context Compression）
只保留与问题最相关的句子，减少Token消耗：

压缩流程：
```python

def compress_context(query: str, documents: List[Document]) -> str:
    """压缩上下文，只保留相关内容"""
    
    # 提取所有句子
    all_sentences = []
    for doc in documents:
        sentences = re.split(r'[。！？!?\n]', doc.page_content)
        all_sentences.extend([s.strip() for s in sentences if s.strip()])
    
    # 计算每个句子与问题的相似性
    query_embedding = embeddings.embed_query(query)
    sentence_embeddings = embeddings.embed_documents(all_sentences)
    
    # 选择最相关的句子（最多保留3000字）
    relevant_sentences = []
    current_length = 0
    for sentence in sorted_by_relevance(all_sentences, query_embedding):
        if current_length + len(sentence) > 3000:
            break
        relevant_sentences.append(sentence)
        current_length += len(sentence)
    
    return "。".join(relevant_sentences)
```
### 8. 完整检索流程
```python
async def rag_query(question: str, top_k: int = 8) -> str:
    """完整的RAG查询流程"""
    
    # 1. 问题嵌入
    query_embedding = embeddings.embed_query(question)
    
    # 2. 粗检索（先找更多候选）
    # 2.1 BM25关键词检索
    bm25_results = bm25_search(question, top_k=20)
    
    # 2.2 向量相似度检索
    vector_results = vector_store.similarity_search_by_vector(
        query_embedding, k=20
    )
    
    # 3. 合并去重
    candidates = merge_and_deduplicate(bm25_results, vector_results)
    
    # 4. LLM重排序（选择最相关的top_k个）
    ranked_docs = await rerank_with_llm(question, candidates, top_k=top_k)
    
    # 5. 上下文压缩
    context = compress_context(question, ranked_docs)
    
    # 6. LLM生成答案
    prompt = f"""基于以下上下文回答用户问题。如果上下文不包含相关信息，请说明。

上下文：
{context}

用户问题：{question}

请给出详细、准确的回答："""
    
    llm = get_llm()
    answer = await llm.ainvoke(prompt)
    
    return answer.content
```
### 9. 支持的文档格式
格式	加载器	说明
PDF	PyPDFLoader	提取文本，保留页面结构
DOCX	Docx2txtLoader	Word文档
PPTX	UnstructuredPowerPointLoader	PowerPoint演示文稿
XLSX	UnstructuredExcelLoader	Excel表格
TXT	TextLoader	纯文本文件
批量	DirectoryLoader	批量加载目录下所有文档
### 10. 性能优化
索引持久化：ChromaDB自动持久化到磁盘，重启后无需重新构建
BM25缓存：BM25索引保存到pickle文件，重启后快速加载
嵌入缓存：相同文档的嵌入向量缓存，避免重复计算
批量处理：支持批量上传文档，提高处理效率




## 八、安全架构

### 多层安全防护

1. **前端 → Java后端**
   - JWT Bearer Token认证
   - BCrypt密码加密

2. **Java后端 → Python AI服务（安全网关模式）**
   - 内部API密钥认证（X-Internal-Api-Secret Header）
   - 仅监听127.0.0.1，不暴露到外部网络

### Java后端转发请求到Python的完整流程

Java后端作为**安全网关**，负责转发请求到Python AI服务：

**架构图：**

```
前端 → Java后端（验证JWT） → 添加内部密钥 → Python AI服务（仅监听127.0.0.1）
```

**转发机制（AIController.java）：**

```java
@RestController
@RequestMapping("/api/ai")
public class AIController {
    
    // 构建内部请求Header
    private HttpHeaders buildInternalHeaders(String contentType, String jwtToken) {
        HttpHeaders headers = new HttpHeaders();
        // 1. 添加内部密钥（防止外部直接访问Python）
        headers.set("X-Internal-Api-Secret", internalSecret);
        // 2. 传递用户JWT Token（Python调用Java API时需要）
        headers.set("Authorization", "Bearer " + jwtToken);
        return headers;
    }
    
    // 转发JSON POST请求
    private ResponseEntity<Map> forwardJsonPost(String path, Map body,
            Authentication auth, HttpServletRequest request) {
        String url = aiServiceUrl + path;
        String userId = getCurrentUserId(auth);
        String jwtToken = extractJwtToken(request);
        
        // 确保请求体中包含user_id
        body.putIfAbsent("user_id", userId);
        
        HttpHeaders headers = buildInternalHeaders("application/json", jwtToken);
        HttpEntity<Map> entity = new HttpEntity<>(body, headers);
        
        return restTemplate.postForEntity(url, entity, Map.class);
    }
}
```

**转发流程：**

1. 前端请求 `POST /api/ai/orchestrator/chat`（携带JWT Token）
2. Java后端验证JWT Token，提取 `user_id`
3. 构建新请求，添加 `X-Internal-Api-Secret` 内部密钥
4. 转发到 `http://127.0.0.1:8000/orchestrator/chat`
5. Python验证内部密钥，处理请求
6. 返回响应给Java，再返回给前端

**安全隔离：**

- Python服务仅监听 `127.0.0.1:8000`，不暴露到外部网络
- 必须携带正确的 `X-Internal-Api-Secret` 才能访问
- JWT Token通过Header传递，Python可调用需认证的Java API



## 九、许可证

本项目使用 [MIT License](LICENSE) 许可证。


** 如果这个项目对你有帮助，请给我们一个Star！**
