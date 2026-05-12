# dnd-llm

AI 驱动的 D&D (龙与地下城) 桌面角色扮演辅助平台

## 项目简介

本项目为 D&D TRPG 玩家和主持人提供一站式智能游戏辅助体验。依托多 Agent 协作和知识检索 (RAG) 技术，自动生成剧情、管理角色、规则解释和流程引导，极大降低游戏门槛、简化桌面流程、提升剧本创新性和流畅度。

> **核心痛点解决：**  
> - 助理主持缺乏经验/规则难查的问题  
> - 剧情素材生成慢，流程繁琐  
> - 场外资料分散，影响沉浸感  
> - 玩家与主持互动效率较低

## 仓库结构

- `FYP-demo-BackEnd`  
  FastAPI + LangChain 智能后端，负责：
  - 多 Agent 剧情流转与自动修正
  - 知识检索（RAG）与规则解析
  - 完整 API (REST/SSE) 服务

- `FYP-demo-FrontEnd`  
  Next.js + TypeScript 响应式前端，负责：
  - 聊天驱动、多人在线协作界面
  - 角色卡片、剧情进度与操作引导

## 主要功能特性

- 🧩 多 Agent 协作完成剧情整理、细化与反馈驱动自动修正（支持长链推理、版本化管理）
- 🔎 嵌入式知识检索 (RAG)，查找规则与资料文档，实时补充剧情，保障合理性
- ♻️ SSE流式响应，实现沉浸式交互体验
- 🧙 全自动角色生成、互动与背包管理

## 技术栈

- **后端**：Python, FastAPI, LangChain, ChromaDB, SQLite
- **前端**：Next.js, React, TypeScript, Shadcn-UI
- **向量检索/知识库**：ChromaDB
- **API 文档与测试**：集成见 `FYP-demo-BackEnd/documents/api.md`

## 快速开始

确保 Python >=3.10, Node.js >=18 已安装。

**后端启动**  
```bash
cd FYP-demo-BackEnd
# 建议新建虚拟环境
pip install -r requirements.txt
uvicorn main:app --reload
```

**前端启动**  
```bash
cd FYP-demo-FrontEnd
npm install
npm run dev
# 浏览器访问 http://localhost:3000
```

## 贡献 & 问题反馈

欢迎提交 Issue 或 PR，一起完善智能桌游生态！

---

如需深入使用文档或Agent扩展，请详见各子目录README及 `FYP-demo-BackEnd/documents/` 下详细说明。
