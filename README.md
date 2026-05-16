# OpenRHTV

使用 LangGraph 复现 RunningHub RHTV 的 **Agent + 人 + 无限画布** 协同工作模式，维持长视频创作心流。

## 背景

[RunningHub](https://www.runninghub.cn/) 是国内最大的云端 ComfyUI 平台，2026 年推出了 [RHTV](https://rhtv.ai/)——一个把 AI Agent 原生嵌入无限画布的一站式内容创作平台。用户通过自然语言驱动 Agent，Agent 在画布上自动完成剧本、分镜、生图、生视频、配音、剪辑全流程，每步可见、可干预、可回退，告别「盲盒抽卡」式的黑盒生成。

OpenRHTV 是对这一模式的**学习性开源复现**，重点探索两个问题：

1. **Agent 如何控制画布**——LangGraph 多角色 Agent 如何与 React Flow 画布双向交互
2. **人机协同的心流**——如何设计交互让创作者不被工具打断，保持创作连续性

## 核心概念

### 三位一体：Agent + 人 + 画布

```
┌────────────────────────────────────────────┐
│                  无限画布                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  剧本节点  │──│  分镜节点  │──│  视频节点  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│       ▲              ▲              ▲        │
│       │    Agent 自动搭建 + 人随时干预  │        │
│       └──────────────┴──────────────┘        │
│                     │                        │
│              对话面板（自然语言交互）            │
└────────────────────────────────────────────┘
```

| 角色 | 职责 |
|------|------|
| **Agent** | 理解创作意图，拆解任务，调度外部 API，在画布上搭建工作流 |
| **人** | 下达指令，在关键节点做决策（选方案、定风格、审成片），随时干预修改 |
| **画布** | 承载全流程的可视化节点树，每一步 100% 透明，支持单节点精准修改 |

### 心流（Flow）

传统视频创作需要频繁切换工具：写脚本 → 切换软件 → 找素材 → 切换软件 → 剪辑 → 切回修改……每次切换都是一次上下文中断。

RHTV / OpenRHTV 的思路是**画布即工作区**——所有产出物以节点形式留在画布上，对话历史、中间产物、修改记录全部可视可追溯，创作者始终在一个空间内推进，不被工具边界打断。

## Agent 角色体系

基于 LangGraph 的 DeepAgent，5 个专业角色协同完成创作：

```
用户一句话指令
      │
      ▼
┌──────────┐     ┌──────────┐     ┌──────────────┐
│   导演    │────▶│   策划    │────▶│   分镜师      │
│ Director │     │ Planner  │     │ Storyboarder │
└──────────┘     └──────────┘     └──────┬───────┘
                                         │
                    ┌────────────────────┘
                    ▼
┌──────────────┐     ┌──────────┐
│  形象设计师   │────▶│   剪辑师   │
│ Visual       │     │  Editor   │
│ Designer     │     │           │
└──────────────┘     └──────────┘
```

| 角色 | 职责 | 产出的画布节点 |
|------|------|--------------|
| **导演 Director** | 理解用户意图，统筹创作方向，拍板关键决策，调度其他角色 | 项目总览、创意方向 |
| **策划 Planner** | 拆解需求为可执行任务序列，编排工作流 | 任务清单、依赖关系 |
| **分镜师 Storyboarder** | 生成分镜脚本，包含镜头描述、构图、运镜、时长 | 分镜节点（时间线） |
| **形象设计师 Visual Designer** | 锁定角色/产品视觉锚点（三视图、定稿板），确保全片风格统一 | 锚点节点、风格参考 |
| **剪辑师 Editor** | 串联素材，添加转场、配音、字幕，输出成片 | 成片时间线、导出节点 |

角色之间通过 LangGraph 的状态图进行消息传递和任务交接，每个角色的输出都作为画布节点持久化，用户可在任意节点介入修改。

## 全流程链路

```
剧本 → 分镜 → 生图 → 生视频 → 配音 → 剪辑
  │       │       │       │        │       │
  ▼       ▼       ▼       ▼        ▼       ▼
导演+   分镜师  形象设计  外部API   外部API  剪辑师
策划      +      师调    生视频    TTS     串联
        导演     ComfyUI                   输出
        审阅     API
```

每个环节：
- **Agent 驱动**：角色自动推进，生成中间产物并写入画布节点
- **人可干预**：每个节点支持暂停、修改、替换、回退
- **锚点先行**：在生图阶段之前先锁定视觉锚点，避免后续风格漂移

## 技术栈

| 层 | 技术 |
|----|------|
| Agent 框架 | [LangGraph](https://github.com/langchain-ai/langgraph) + [DeepAgents](https://github.com/langchain-ai/deepagents)（Python） |
| 画布 | [React Flow](https://reactflow.dev/) |
| 前端 | React + TypeScript |
| LLM | 可插拔适配（默认支持 OpenAI / Anthropic / DeepSeek） |
| 生图/生视频 | ComfyUI API / RunningHub API |
| TTS | 待定 |
| 后端 | Python（LangGraph 服务端运行，WebSocket 与前端画布通信） |

## 通信协议

前后端通过 WebSocket 通信，协议如下：

### 连接

```
ws://localhost:8765/{thread_id}
```

每个 `thread_id` 对应一个独立会话，拥有独立的画布 JSON 文件和 agent 对话上下文。

### 消息格式

**前端 → 后端：用户消息**

```json
{
  "type": "user_message",
  "content": "帮我创作一支赛博朋克风格的短片"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"user_message"` | 固定值 |
| `content` | `string` | 用户的自然语言输入 |

**后端 → 前端：Agent 响应 + 画布同步**

```json
{
  "type": "agent_response",
  "content": "好的，我先确认几个问题……",
  "canvas": {
    "nodes": {
      "script-abc123": {
        "id": "script-abc123",
        "type": "script",
        "title": "赛博朋克短片剧本",
        "description": "……",
        "status": "done",
        "result": { "content": "[剧本] ...", "word_count": 120 }
      }
    },
    "edges": []
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"agent_response"` | 固定值 |
| `content` | `string` | Agent 的文本回复 |
| `canvas` | `object \| null` | 当前画布完整快照，`nodes` 为节点字典，`edges` 为连线 |

### 数据流

```
前端 ChatPanel 输入
    │
    ▼
WS: { type: "user_message", content: "..." }
    │
    ▼
后端 server.py → agent.invoke()
    │
    ├─ agent 调用 create_canvas_node → 写入 backend/data/canvas/{thread_id}.json
    ├─ agent 调用 execute_node → 更新节点状态，写入 mock 结果
    └─ agent 调用 update_canvas_node / delete_canvas_node
    │
    ▼
读取画布 JSON → WS: { type: "agent_response", content: "...", canvas: {...} }
    │
    ▼
前端 onResponse → Zustand store → React Flow 重新渲染节点
```

### 画布 JSON 存储

后端所有工具操作的画布文件位于 `backend/data/canvas/{thread_id}.json`，每轮对话结束后全量推送给前端。

## 快速开始

> 项目处于早期开发阶段，以下为规划中的启动方式。

```bash
# 克隆项目
git clone https://github.com/your-org/OpenRHTV.git
cd OpenRHTV

# 1. 配置 LLM
cp .env.example .env
# 编辑 .env，填入 GOOGLE_API_KEY

# 2. 启动后端 WebSocket 服务
cd backend
uv sync
uv run python -m agent.server

# 3. 启动前端画布（新终端）
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
```

## 项目结构

```
OpenRHTV/
├── video_agent/                  # LangGraph + DeepAgents 后端
│   ├── pyproject.toml            # uv 项目配置, deepagents + websockets
│   ├── .python-version           # Python 3.12
│   └── src/video_agent/
│       ├── main.py               # 入口：组装 Director DeepAgent + 4 个 subagent
│       ├── state.py              # 画布状态 TypedDict，agent 与前端共享的数据模型
│       ├── server.py             # WebSocket 服务，双向桥接 agent 与前端
│       ├── tools/
│       │   ├── canvas.py         # 画布操作工具：创建/更新/删除/连接节点
│       │   └── generation.py     # 外部 API 工具：生图/生视频/TTS
│       └── prompts/
│           ├── director.md       # Director agent 系统指令
│           ├── planner.md        # Planner subagent 指令
│           ├── storyboarder.md   # Storyboarder subagent 指令
│           ├── visual_designer.md # Visual Designer subagent 指令
│           └── editor.md         # Editor subagent 指令
│
├── frontend/                     # React Flow 前端
│   └── src/
│       ├── main.tsx              # React 入口
│       ├── App.tsx               # 根组件，三栏布局（Header / Canvas / ChatPanel）
│       ├── components/
│       │   ├── Header.tsx        # 顶部栏：项目名、创作阶段指示器
│       │   ├── Canvas.tsx        # React Flow 画布，渲染节点树
│       │   ├── ChatPanel.tsx     # 对话面板，用户输入自然语言指令
│       │   └── nodes/
│       │       ├── ScriptNode.tsx     # 剧本节点
│       │       ├── StoryboardNode.tsx # 分镜节点
│       │       ├── ImageNode.tsx      # 图片节点（缩略图预览）
│       │       ├── VideoNode.tsx      # 视频节点（可播放预览）
│       │       └── ExportNode.tsx     # 成片导出节点
│       ├── hooks/
│       │   ├── useWebSocket.ts   # WebSocket 连接管理与消息收发
│       │   └── useCanvas.ts      # 画布操作 hook：响应 agent 事件更新节点
│       ├── store/
│       │   └── canvasStore.ts    # 前端画布状态（Zustand）：节点/边/选中态
│       └── types/
│           └── index.ts          # 共享类型：节点类型枚举、WS 消息协议
│
└── README.md
```

### 各文件职责

#### 后端 `video_agent/`

| 文件 | 核心职责 |
|------|---------|
| `main.py` | 调用 `create_deep_agent()` 创建 Director 主 agent，注入 4 个 subagent（Planner / Storyboarder / Visual Designer / Editor）。配置画布工具、interrupt_on 规则、checkpointer。返回 CompiledStateGraph |
| `state.py` | 定义画布状态 TypedDict：`nodes`（当前画布节点列表）、`messages`（对话历史）、`phase`（创作阶段：scripting / storyboard / generation / editing / done）。agent 和工具函数共享读写 |
| `server.py` | WebSocket 服务层。接收前端发来的用户消息→喂给 agent graph→agent 执行过程中的工具调用事件（画布操作）通过 WS 推回前端。管理多 session（thread_id） |
| `tools/canvas.py` | 画布工具函数集合。Agent 调用它们来操控前端画布：`create_node(type, data, position)`、`update_node(id, data)`、`delete_node(id)`、`connect(source, target)`。函数内部更新 state，同时通过 WS 推送事件 |
| `tools/generation.py` | 外部 API 调用封装。Agent 调用它们生成实际内容：`generate_image(prompt, style_ref)`、`generate_video(image_ref, motion_desc)`、`generate_tts(text, voice)` 等。具体 API 待定，先用 mock |
| `prompts/*.md` | 5 个 markdown 文件定义每个 agent 角色的系统指令。描述角色人设、可用工具、输入输出规范、行为边界。从 `main.py` 中读取注入 |

#### 前端 `frontend/`

| 文件 | 核心职责 |
|------|---------|
| `App.tsx` | 根组件。三栏布局：左侧 `<ChatPanel>` / 右侧 `<Canvas>` / 顶部 `<Header>`。管理全局状态（Zustand store） |
| `Canvas.tsx` | React Flow 实例。注册 5 种自定义节点类型（Script / Storyboard / Image / Video / Export）。监听 WebSocket 画布事件，动态增删节点和边 |
| `ChatPanel.tsx` | 用户输入自然语言指令，通过 WebSocket 发给后端。展示 Director agent 的回复消息和进度更新 |
| `Header.tsx` | 显示当前项目名、创作阶段（剧本→分镜→生图→剪辑）、agent 状态指示 |
| `nodes/*.tsx` | 5 种自定义 React Flow 节点。每种节点有独立的渲染 UI（如 ImageNode 显示缩略图，VideoNode 有播放按钮），支持点击查看详情、右键菜单操作 |
| `useWebSocket.ts` | 封装 WebSocket 连接生命周期：连接/断开/重连。收发 JSON 消息，按 `msg.type` 分流到对应 handler |
| `useCanvas.ts` | 画布操作 hook。暴露 `addNode` `updateNode` `removeNode` `addEdge` 等方法，内部同步更新 Zustand store，同时提供 `handleAgentEvent` 统一处理来自 agent 的画布指令 |
| `canvasStore.ts` | Zustand store。持有 `nodes: Node[]` `edges: Edge[]` `selectedNodeId`。所有画布变更统一走 store，保证 React Flow 渲染一致 |
| `types/index.ts` | TypeScript 类型定义。`NodeType` 枚举、`CanvasNode` 接口、`WSMessage` 协议类型，前后端共享协议基准 |

## 路线图

- [ ] **Phase 1** — LangGraph 5 角色基础编排，命令行对话交互
- [ ] **Phase 2** — React Flow 画布搭建，Agent 可通过 WebSocket 操作画布节点
- [ ] **Phase 3** — 对话面板接入，用户与 Agent 自然语言交互
- [ ] **Phase 4** — 对接 ComfyUI API，实现生图/生视频节点
- [ ] **Phase 5** — 全链路跑通：一句话 → 成片

## 参考

- [RHTV 官方](https://rhtv.ai/)
- [RunningHub 社区](https://www.runninghub.cn/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [React Flow 文档](https://reactflow.dev/)
