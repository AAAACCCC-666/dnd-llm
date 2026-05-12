# 剧情梗概系统文档

本文档详细介绍了剧情梗概系统的架构、组件和工作流程。该系统负责管理D&D游戏的剧情发展、梗概生成和玩家反馈处理。

## 系统概述

剧情梗概系统是一个完整的叙事管理解决方案，包含以下核心组件：

- **剧情列表规划器 (OutlinePlannerAgent)**: 生成完整的剧情列表
- **梗概生成器 (SynopsisAgent)**: 基于剧情列表生成故事梗概
- **修订代理 (RevisionAgent)**: 根据玩家反馈修订剧情和梗概
- **数据库模型**: 存储故事、剧情列表、梗概和反馈数据
- **API端点**: 提供完整的CRUD和流式生成功能
- **工具集成**: 与LangChain工具系统深度集成

## 核心组件

### 1. 剧情列表规划器 (OutlinePlannerAgent)

**位置**: `app/services/outline_planner_agent.py`

**功能**:
- 设计完整的剧情列表，描述故事的关键阶段
- 确保剧情列表包含从开始到结局的连贯序列
- 支持最小节点数要求和结局节点标记

**主要方法**:
- `generate_plot_outline(theme, min_nodes, style)`: 生成剧情列表（`min_nodes` 对应 API 请求体字段 `N`）

**示例输出**:
```json
{
  "nodes": [
    {
      "index": 1,
      "title": "新手村",
      "status": "Pending",
      "is_ending": false,
      "summary": "玩家在村庄中开始冒险"
    },
    {
      "index": 2,
      "title": "森林探险",
      "status": "Pending", 
      "is_ending": false,
      "summary": "探索神秘的森林"
    }
  ]
}
```

### 2. 梗概生成器 (SynopsisAgent)

**位置**: `app/services/synopsis_agent.py`

**功能**:
- 基于剧情列表生成梗概，支持流式和非流式
- 可配置风格、单词/字数限制和目标语言

**主要方法**:
- `generate_plot_synopsis(outline, style, word_limit=100, language=None)`: 非流式生成
- `generate_plot_synopsis_stream(outline, style, word_limit=100, language=None)`: 流式生成

**示例输出**:
```
"This is an epic adventure story about a hero who begins their journey in a small village and ventures into the mysterious forest..."
```

### 3. 修订代理 (RevisionAgent)

**位置**: `app/services/revision_agent.py`

**功能**:
- 根据玩家反馈修订现有的剧情列表和梗概
- 支持两种修订类型:
  - `ModifyExisting`: 调整现有剧情列表，保持整体结构
  - `CreateNew`: 基于主题和反馈创建全新的剧情列表
- 确保修订后的内容符合游戏世界约束和原始故事基调

**主要方法**:
- `revise(original_outline, original_synopsis, feedback_text, task_type)`: 执行修订

## 数据库架构

### 核心表

1. **`stories`**: 故事基本信息
2. **`plot_outlines`**: 剧情列表，支持版本管理
3. **`synopses`**: 故事梗概，与剧情列表版本关联
4. **`player_feedback`**: 玩家反馈记录

### 版本管理

- 每个故事可以有多个版本的剧情列表和梗概
- 只有激活的版本会被使用
- 版本号递增，便于追踪变更历史

## API端点（与当前实现一致）

### 故事管理
- `POST /api/stories`: 创建故事并生成初始剧情列表（请求体含 `title/theme/N/style/created_by/session_id`，`N` 必填且 >0；`session_id` 可选，提供后将把该会话的玩家角色（`is_player=true`）序列化为 `player_character` 传给剧情生成模型，以便定制化节点）
- `GET /api/stories/{story_id}`: 获取故事详情、激活剧情列表及最新梗概

### 梗概生成
- `POST /api/stories/{story_id}/synopsis`: 生成故事梗概（支持流式，流事件 `delta`/`done`；请求体可选 `style/word_limit/language`）。当剧情节点数量超过 7 个时，实际只取前 3 个与后 3 个节点参与生成（共 6 个）。

### 剧情节点管理 (DM操作)
- `PATCH /api/stories/{story_id}/nodes/{node_index}`: 更新节点状态
- `PATCH /api/stories/{story_id}/nodes/{node_index}/ending`: 标记/取消结局节点

### 反馈处理
- `POST /api/stories/{story_id}/feedback`: 提交反馈并生成修订（支持流式，事件含 `heartbeat`、逐字符 `delta`、最终 `done`）

## 工具集成

### DM工具

系统为地下城主提供了三个专用工具：

1. **`update_plot_node_status`**
   - 更新剧情节点的状态
   - 在故事场景完成、开始或跳过时使用

2. **`mark_plot_node_as_ending`**
   - 标记或取消标记剧情节点为结局节点
   - 调整可能的结局场景时使用

3. **`trigger_regenerate_synopsis`**
   - 基于当前剧情列表重新生成梗概
   - 在剧情列表发生重大变化后使用

### 工具使用规则

- 所有工具调用后必须继续叙事描述
- 禁止在工具调用后保持沉默
- 必须遵循纯叙事规则：无问题、无明确建议、无选项

## 工作流程

### 1. 故事创建流程
```
创建故事 → 生成剧情列表 → 保存激活版本 → 生成梗概（可流式） → 保存激活梗概
```

### 2. 游戏进行流程
```
玩家行动 → DM叙事 → 工具调用更新节点状态 → 继续叙事
```

### 3. 反馈处理流程
```
玩家反馈 → 修订代理处理 → 生成新版本 → 保存并激活新版本
```

## 配置和模型

### 环境变量
- `PLOT_OUTLINE_MODEL`: 剧情列表生成模型（未设置时回退到 `OPENAI_MODEL`）
- `PLOT_SYNOPSIS_MODEL`: 梗概生成模型（未设置时回退到 `OPENAI_MODEL`）  
- `PLOT_REVISION_MODEL`: 修订模型（未设置时回退到 `OPENAI_MODEL`）

### 默认配置
未显式设置三项专用模型时，都会使用 `OPENAI_MODEL`（项目默认值为 `gpt-4o-mini`）。当前实现未内置 Qwen 作为默认模型。

## 错误处理

- 所有组件都有完善的错误处理和重试机制
- API端点提供详细的错误信息和状态码
- 工具调用失败时会抛出明确的验证错误

## 性能优化

- 流式生成减少用户等待时间
- 版本管理避免重复生成
- 异步处理提高系统响应性
- 合理的节点数量限制（最多7个节点参与梗概生成）

## 使用示例

### 创建新故事
```python
# 通过API创建故事
response = await client.post("/api/stories", json={
    "title": "龙与地下城冒险",
    "theme": "奇幻冒险"
})
```

### 生成梗概
```python
# 流式生成梗概
async for event in generate_plot_synopsis_stream(outline, style="轻松"):
    if "delta" in event:
        print(event["delta"], end="")
```

### 处理玩家反馈
```python
# 提交反馈并获取修订
revision = await run_revision(
    original_outline=current_outline,
    original_synopsis=current_synopsis,
    feedback_text="希望有更多战斗场景",
    task_type="ModifyExisting"
)
```

## 最佳实践

1. **剧情列表设计**: 确保有清晰的开始、发展和结局节点
2. **梗概生成**: 当节点很多时，聚焦头尾关键节点即可（实现会自动截取前3/后3）
3. **工具使用**: 及时更新节点状态以反映故事进展
4. **反馈处理**: 根据反馈类型选择合适的修订策略
5. **版本管理**: 定期清理旧版本以优化存储空间

该系统为D&D游戏提供了完整的叙事管理解决方案，支持动态的故事发展和玩家驱动的剧情演进。
