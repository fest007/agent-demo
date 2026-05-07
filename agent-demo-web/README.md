# Agent Demo - 前端界面层

基于 React + TypeScript + Ant Design 的智能 Agent 前端界面，提供对话交互、知识库管理、技能管理等完整的管理中台。

## 技术栈

- **框架**: React 19 + TypeScript
- **构建**: Vite 6
- **UI**: Ant Design 5 + @ant-design/icons
- **状态管理**: Zustand
- **Markdown 渲染**: react-markdown + remark-gfm
- **测试**: Playwright

## 快速开始

```bash
# 安装依赖
pnpm install

# 启动开发服务器（自动代理 /api 到 localhost:8000）
pnpm dev
```

访问 http://localhost:3000

## 功能模块

### 对话界面
- 流式输出（SSE），逐 token 实时显示
- Markdown 渲染（支持代码高亮、表格、列表等）
- 情绪标识展示（开心/难过/生气等）
- 工具调用过程展示
- TTS 语音播放（自动去除 Markdown 符号）
- 消息时间戳

### 会话管理
- 新建对话（上下文隔离）
- 会话列表（侧边栏展示，点击切换）
- LLM 自动总结命名（首轮对话后自动生成 ≤8 字标题）
- 批量删除（多选模式）

### 知识库管理
- 文件上传（PDF/Word/MD/TXT）
- URL 抓取入库
- 知识列表查看与删除

### 技能管理
- 查看内置技能
- AI 自动生成新技能

### 工具管理
- 查看已注册工具列表

### 设置
- 模型配置
- TTS 引擎选择

## 项目结构

```
src/
├── api/              # API 调用封装（chat, session, knowledge, skills, tts）
├── components/       # UI 组件
│   ├── ChatBox.tsx       # 对话主界面
│   ├── MessageBubble.tsx # 消息气泡
│   ├── InputBar.tsx      # 输入栏
│   ├── VoicePlayer.tsx   # TTS 语音播放
│   ├── SessionList.tsx   # 会话列表
│   ├── Sidebar.tsx       # 侧边栏导航
│   ├── Knowledge.tsx     # 知识库管理
│   ├── Skills.tsx        # 技能管理
│   └── Settings.tsx      # 设置页
├── stores/           # Zustand 状态管理
│   ├── chatStore.ts      # 对话状态
│   ├── sessionStore.ts   # 会话状态
│   └── appStore.ts       # 全局状态
├── hooks/            # React Hooks
│   └── useChat.ts        # 对话核心逻辑
├── utils/            # 工具函数
│   ├── stripMarkdown.ts  # Markdown 清理（TTS 用）
│   └── formatTime.ts     # 时间格式化
└── types/            # TypeScript 类型定义
```

## 开发命令

```bash
pnpm dev          # 启动开发服务器
pnpm build        # 构建生产版本（tsc + vite build）
pnpm preview      # 预览生产构建

# 测试（需要前端 dev server 和后端 API 运行中）
npx playwright test tests/app.spec.ts
```

## 环境变量

前端通过 Vite 代理 `/api` 请求到后端，无需额外配置 API 地址。如需修改代理目标，编辑 `vite.config.ts`。
