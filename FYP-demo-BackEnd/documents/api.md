# 后端 API 文档

## 概述

本 API 提供与大语言模型 (LLM) 进行交互的功能，包括会话管理和聊天消息传递。后端基于 LangChain 框架实现，提供强大的工具调用和记忆管理功能。

## 通用端点

### `GET /api`

*   **描述**: 返回一个欢迎消息，确认 API 正在运行。
*   **响应 (200 OK)**:
    ```json
    {
      "message": "Welcome to the LLM Interaction API"
    }
    ```

## 会话管理 (`/api/sessions`)

这些端点用于管理聊天会话。

### `POST /api/sessions`

*   **描述**: 创建一个新的聊天会话。
*   **请求体**: `schemas.ChatSessionCreate`
    ```json
    {
      "name": "My First Chat" // 可选的会话名称
    }
    ```
*   **响应 (200 OK)**: `schemas.ChatSession` (包含会话 ID、可选的名称、创建时间等)
    ```json
    {
      "id": "some-unique-session-id",
      "name": "My First Chat", // 如果提供，则返回名称
      "created_at": "2023-10-27T10:00:00Z"
      // ... 其他会话属性
    }
    ```

### `GET /api/sessions`

*   **描述**: 获取所有聊天会话的列表。
*   **查询参数**:
    *   `skip` (int, optional, default: 0): 跳过的会话数量。
    *   `limit` (int, optional, default: 100): 返回的最大会话数量。
*   **响应 (200 OK)**: `List[schemas.ChatSession]` (聊天会话对象列表)

### `GET /api/sessions/{session_id}`

*   **描述**: 获取具有指定 ID 的特定聊天会话的详细信息。
*   **路径参数**:
    *   `session_id` (str, required): 要检索的会话的唯一 ID。
*   **响应 (200 OK)**: `schemas.ChatSession` (包含会话 ID、可选的名称、创建时间以及主角色存在状态)
    ```json
    {
      "id": "some-unique-session-id",
      "name": "My First Chat",
      "created_at": "2023-10-27T10:00:00Z",
      "is_main_character_exist": true // 或 false
      // ... 其他会话属性
    }
    ```
*   **响应 (404 Not Found)**: 如果具有给定 ID 的会话不存在。
    ```json
    {
      "detail": "Session not found"
    }
    ```

### `DELETE /api/sessions/{session_id}`

*   **描述**: 删除指定会话以及与之绑定的角色、聊天消息和对话选项记录。操作在单个事务中完成，如任一环节失败会回滚并提示错误。
*   **路径参数**:
    *   `session_id` (str, required): 需要删除的会话 ID。
*   **响应 (200 OK)**:
    ```json
    {
      "message": "Session deleted successfully"
    }
    ```
*   **响应 (404 Not Found)**: 重复删除或 ID 不存在时返回。
    ```json
    {
      "detail": "Session not found"
    }
    ```
*   **响应 (500 Internal Server Error)**: 删除过程中发生异常时返回 `{ "detail": "删除失败" }`，前端可提示用户稍后重试。

## 聊天交互 (`/api/chat`)

这些端点用于在特定会话中发送和接收聊天消息。

### `POST /api/chat/messages`

*   **描述**: 向指定的聊天会话发送一条消息（非流式）。此端点主要用于记录用户消息，实际的 LLM 交互建议通过流式端点进行。
*   **函数参数**:
    *   `session_id` (str, required): 消息所属的会话 ID。作为函数参数传递。
*   **请求体**: `schemas.MessageSendRequest`
    ```json
    {
      "content": "Hello, how are you?"
    }
    ```
*   **响应 (200 OK)**: `schemas.ChatMessage` (已保存的用户消息对象)
*   **响应 (404 Not Found)**: 如果指定的 `session_id` 不存在。

### `GET /api/chat/history`

*   **描述**: 获取指定聊天会话的所有消息历史记录，包含关联的对话选项。
*   **查询参数**:
    *   `session_id` (str, required): 要检索其历史记录的会话 ID。
*   **响应 (200 OK)**: `List[schemas.ChatMessage]` (消息对象列表，按时间顺序排列，每个消息可能包含 `suggestions` 字段)
    ```json
    [
      {
        "id": 1,
        "session_id": "session-123",
        "role": "user",
        "content": "我想进行一次冒险",
        "created_at": "2023-10-27T10:00:00Z",
        "suggestions": null
      },
      {
        "id": 2,
        "session_id": "session-123", 
        "role": "assistant",
        "content": "欢迎来到龙与地下城的世界！你发现自己站在一个古老的洞穴入口前...",
        "created_at": "2023-10-27T10:01:00Z",
        "suggestions": [
          "进入洞穴探索",
          "在洞穴外搜寻线索", 
          "呼唤洞穴内部",
          "点燃火把照明",
          "检查装备和物品"
        ]
      }
    ]
    ```
*   **响应 (404 Not Found)**: 如果指定的 `session_id` 不存在。

### `POST /api/chat/stream`

*   **描述**: 向指定的聊天会话发送一条消息，并以服务器发送事件 (SSE) 的形式流式接收 LLM 的响应。支持流式响应和工具调用。
*   **查询参数**:
    *   `session_id` (str, required): 消息所属的会话 ID。通过查询参数传递。
*   **请求体**: `schemas.MessageSendRequest`
    ```json
    {
      "content": "Tell me a joke."
    }
    ```
*   **响应 (200 OK)**: `text/event-stream`
    *   事件流包含一系列 JSON 对象，每个对象代表响应的一部分 (`delta`)、工具调用相关事件或流结束事件。
    *   **技术说明**: 内部服务层使用 `tool_start`、`tool_result`、`tool_error` 事件类型，在 API 层转换为 `tool_call_start`、`tool_call_result`、`tool_call_error` 供前端使用。详见 [`function_call.md`](function_call.md)。
    *   **主要事件类型**:
        *   **文本增量 (`delta`)**: 当 LLM 生成文本响应时发送。
            ```json
            {"delta": "some text chunk"}
            ```
        *   **工具调用开始 (`tool_call_start`)**: 当 LLM 决定调用一个工具时发送。
            ```json
            {
              "event": "tool_call_start",
              "id": "call_xxxxxxxxxxxx", // 工具调用的唯一ID
              "name": "tool_name",       // 要调用的工具名称
              "arguments": {"arg1": "value1"} // 工具的参数 (JSON对象)
            }
            ```
        *   **工具调用结果 (`tool_call_result`)**: 当工具成功执行后发送。
            ```json
            {
              "event": "tool_call_result",
              "id": "call_xxxxxxxxxxxx", // 对应的工具调用ID
              "name": "tool_name",       // 执行的工具名称
              "payload": "tool execution result" // 工具执行的结果 (通常是字符串)
            }
            ```
        *   **工具调用错误 (`tool_call_error`)**: 当工具执行失败时发送。
            ```json
            {
              "event": "tool_call_error",
              "id": "call_xxxxxxxxxxxx", // 对应的工具调用ID
              "name": "tool_name",       // 尝试执行的工具名称
              "payload": "error message"  // 错误信息
            }
            ```
        *   **流结束 (`stream_end`)**: 表示所有响应（包括文本和工具调用后的最终文本）已发送完毕。
            ```json
            {"event": "stream_end", "reason": "stop_token_or_finish_reason"} // reason是可选的
            ```
        *   **选项生成 (`suggestions_generated`)**: 在流结束后生成的对话选项，供前端展示给用户选择。
            ```json
            {
              "event": "suggestions_generated",
              "suggestions": [
                "选择选项 A",
                "选择选项 B",
                "选择选项 C"
              ]
            }
            ```

## 配置管理 (`/api/settings`)

用于读取与更新运行时关键配置（数据库优先，环境变量仅用于首启落库或缺省兜底）。

### `GET /api/settings`

* **描述**: 返回当前配置的键值对，键名直接对应配置项。
* **响应示例 (200 OK)**:
  ```json
  {
    "OPENAI_API_KEY": "sk-***",
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OPENAI_MODEL": "gpt-4o-mini",
    "RAG_EMBEDDING_API_KEY": null,
    "RAG_EMBEDDING_BASE_URL": null,
    "RAG_EMBEDDING_MODEL": "text-embedding-3-large",
    "SUGGEST_OPTIONS_MODEL": "gpt-4o-mini"
  }
  ```

### `PUT /api/settings`

* **描述**: 更新一组配置；未提供的字段保持不变，字段显式设为 `null` 表示清空。
* **请求体**: 与响应同结构，允许部分字段。
  ```json
  {
    "OPENAI_API_KEY": "sk-xxx",
    "OPENAI_BASE_URL": "https://api.deepseek.com/v1"
  }
  ```
* **响应 (200 OK)**: 返回更新后的完整配置对象，与 `GET` 相同。

> 说明：首启时若数据库缺少配置，会将 `.env` 中对应变量落库；之后读取均以数据库为准，环境变量仅在无记录时兜底。
            **功能说明**:
            - 此功能由环境变量 `SUGGEST_OPTIONS_ENABLED` 控制（默认为 true），设置为 false 可禁用选项生成
            - 选项由 `app/services/options_service.py` 中的 `generate_conversation_options` 函数通过 LLM 异步生成
            - 生成过程在流式响应结束后异步进行，仅针对最后一条助手消息生成选项
            - 生成的选项会保存到 `conversation_suggestions` 数据库表中，与对应的助手消息关联
            - 选项列表最多包含 5 个建议，用于引导用户进行下一步交互
            - 如果选项生成失败，不会影响主流程，错误会被记录但不会中断响应
    *   **示例事件序列 (包含工具调用和选项生成)**:
        ```
        data: {"delta": "Okay, I will roll a dice for you."}
        
        data: {"event": "tool_call_start", "id": "call_abc123", "name": "roll_dice", "arguments": {"sides": 6}}
        
        data: {"event": "tool_call_result", "id": "call_abc123", "name": "roll_dice", "payload": "4"}
        
        data: {"delta": "The dice roll result is: 4. What would you like to do next?"}
        
        data: {"event": "stream_end"}
        
        data: {"event": "suggestions_generated", "suggestions": ["再次掷骰子", "检查背包", "观察周围环境", "与NPC对话"]}
        ```
*   **响应 (404 Not Found)**: 如果指定的 `session_id` 不存在。
*   **错误事件**: 如果在流处理期间发生错误，将发送一个包含错误信息的事件。
    ```
    data: {"error": "Some error message", "event": "error"}
    ```
*   **实现差异说明**:
    *   迭代上限：服务端内部最多执行 5 轮“模型输出→工具调用→再输出”循环，超过会直接发送 `{"event":"stream_end","reason":"max_iterations"}`。
    *   选项生成触发条件：只有当本轮流中至少落地了一条助手文本消息（而非纯工具调用）时才会尝试生成 `suggestions_generated` 事件；纯工具回合不会产出对话选项。

## 剧情梗概系统 (`/api/stories`)

这些端点用于管理故事剧情、梗概和玩家反馈，以下描述与当前实现保持一致。

### `POST /api/stories`

*   **描述**: 创建新故事并生成初始剧情列表。
*   **请求体**: `schemas.StoryCreateRequest`
    ```json
    {
      "title": "龙与地下城冒险",
      "theme": "奇幻冒险",
      "N": 6,
      "style": "light",
      "created_by": "玩家名称",
      "session_id": "chat-session-id-optional"
    }
    ```
    * `N` 为必填且 >0，指定最少节点数；`style` 可选。
    * `session_id` 可选；如提供且该会话下存在 `is_player=true` 的角色，会自动把玩家角色序列化后作为 `player_character` 传入剧情列表生成模型，便于生成更贴合角色的节点。
*   **响应 (200 OK)**: `schemas.StoryWithOutlineResponse`
    ```json
    {
      "story_id": 1,
      "title": "龙与地下城冒险",
      "theme": "奇幻冒险",
      "outline_version": 1,
      "outline": {
        "nodes": [
          { "index": 1, "title": "新手村", "status": "Pending", "is_ending": false, "summary": "玩家在村庄中开始冒险" },
          { "index": 2, "title": "森林探险", "status": "Pending", "is_ending": false, "summary": "探索神秘的森林" }
        ]
      }
    }
    ```

### `GET /api/stories/{story_id}`

*   **描述**: 获取故事详情，包括当前激活的剧情列表（如存在）和最新梗概（按创建时间倒序取第一条）。
*   **路径参数**: `story_id` (int, required)
*   **响应 (200 OK)**: `schemas.StoryDetailResponse`，字段：`story`、`outline`、`synopsis`（后两者可能为 `null`）。

### `POST /api/stories/{story_id}/synopsis`

*   **描述**: 基于当前激活剧情列表生成梗概，支持非流式和 SSE 流式。
*   **查询参数**: `stream` (bool, default: false)。
*   **请求体 (可选)**: `schemas.SynopsisCreateRequest`，含 `style`(str|None)、`word_limit`(int, default 100, >0)、`language`(str|None)。
*   **响应 (200 OK)**:
    *   **非流式**: `schemas.SynopsisSchema`
    *   **流式**: `text/event-stream`
        ```
        data: {"event":"delta","text":"This "}
        ...
        data: {"event":"done","synopsis_id":1,"outline_version":1}
        ```

### `PATCH /api/stories/{story_id}/nodes/{node_index}`

*   **描述**: 更新剧情节点状态（DM 操作），作用于当前激活的剧情列表。
*   **路径参数**: `story_id` (int), `node_index` (int, 1-based)
*   **请求体**: `schemas.PlotNodeStatusUpdateRequest`
    ```json
    { "status": "InProgress" }
    ```
*   **响应 (200 OK)**: `schemas.PlotOutlineSchema`

### `PATCH /api/stories/{story_id}/nodes/{node_index}/ending`

*   **描述**: 标记/取消标记剧情节点为结局节点（DM 操作）。
*   **请求体**: `schemas.PlotNodeEndingUpdateRequest`
    ```json
    { "is_ending": true }
    ```
*   **响应 (200 OK)**: `schemas.PlotOutlineSchema`

### `POST /api/stories/{story_id}/feedback`

*   **描述**: 提交玩家反馈，驱动 RevisionAgent 生成新剧情/梗概；支持流式。
*   **查询参数**: `stream` (bool, default: false)
*   **请求体**: `schemas.PlayerFeedbackCreateRequest`
    ```json
    { "feedback_text": "希望有更多战斗场景", "type": "ModifyExisting" }
    ```
*   **响应 (200 OK)**:
    *   **非流式**: `schemas.PlayerFeedbackSchema`（返回数据库记录，包含 `outline_version`、`synopsis_id`、`processed=true`）
    *   **流式**: `text/event-stream`
        ```
        data: {"event":"heartbeat","message":"stream_started"}
        data: {"event":"delta","text":"B"}
        ...
        data: {"event":"done","feedback_id":1,"outline_version":2,"synopsis_id":2}
        ```

## D&D 角色管理 (`/api/characters`)

这些端点用于创建和管理龙与地下城 (D&D) 5e 角色。

### `GET /api/characters/dnd-data`

*   **描述**: 获取所有用于创建角色的基础数据，如种族、职业、技能等及其对应的ID。**前端在展示创建选项时应首先调用此接口。**
*   **响应 (200 OK)**: `schemas.DndDataResponse` (包含所有选项的字典)
    ```json
    {
      "races": { "1": "矮人", "2": "精灵", ... },
      "classes": { "1": "战士", "2": "游荡者", ... },
      "spells": { "1": "火球术", "2": "治疗术", ... },
      "features": { "1": "战斗风格", "2": "法术列表", ... },
      "proficiencies": { "1": "运动", "2": "体操", ... }
    }
    ```

### `POST /api/characters`

*   **描述**: 根据用户选择的基础数据，创建一个新的 D&D 角色。后端将自动计算角色的衍生属性（如生命值、护甲等级、属性加成等）。
*   **请求体**: `schemas.CharacterCreate` (用户的所有选择)
    ```json
    {
      "name": "Durin_Stonehand",
      "session_id": "associated-session-id", // 新增：关联的会话ID
      "race_id": 1,
      "class_id": 1,
      "strength": 15,
      "dexterity": 10,
      "constitution": 14,
      "intelligence": 8,
      "wisdom": 12,
      "charisma": 10,
      "proficiency_ids": [1, 10],
      "is_player": true ,// 新增：可选，默认为 false
      "is_male": true // 新增：可选，默认为 false
    }
    ```
*   **实现提示**:
    *   默认金币为 15，背包会自动加入 `packsack`、`food (1day)`、`water bag` 三件基础物品；装备为空。
    *   未做角色重名或种族/职业 ID 额外校验，提交无效 ID 将导致 500 或数据库错误；仅校验 `session_id` 存在（不存在返回 404）。
*   **响应 (201 Created)**: `schemas.Character` (返回计算完成后的完整角色卡)

### `GET /api/characters`

*   **描述**: 获取所有已创建的角色列表，支持分页。
*   **查询参数**:
    *   `skip` (int, optional, default: 0): 跳过的角色数量。
    *   `limit` (int, optional, default: 100): 返回的最大角色数量。
*   **响应 (200 OK)**: `List[schemas.Character]`

### `GET /api/characters/session/{session_id}`

*   **描述**: 获取与指定 `session_id` 关联的所有角色列表。
*   **路径参数**:
    *   `session_id` (str, required): 要检索其关联角色的会话的唯一 ID。
*   **响应 (200 OK)**: `List[schemas.Character]`
*   **响应 (404 Not Found)**: 如果具有给定 ID 的会话不存在，或者该会话没有关联的角色。
    ```json
    {
      "detail": "Session not found or no characters associated with this session"
    }
    ```

### `GET /api/characters/id/{character_id}`

*   **描述**: 根据角色的 UUID 获取单个角色的详细信息。**推荐使用**该接口以避免名称重复带来的歧义。
*   **路径参数**:
    *   `character_id` (str, required): 角色的 UUID。
*   **响应 (200 OK)**: `schemas.Character`
*   **响应 (404 Not Found)**: 如果具有该 UUID 的角色不存在。
    ```json
    {
      "detail": "Character not found"
    }
    ```

### `GET /api/characters/{name}`

*   **描述**: 根据角色名称获取单个角色的详细信息。
*   **路径参数**:
    *   `name` (str, required): 要检索的角色名称。
*   **响应 (200 OK)**: `schemas.Character`
*   **响应 (404 Not Found)**: 如果具有该名称的角色不存在
*   **注意**: 此端点已标记为弃用，每次调用都会在服务端记录警告日志，请尽快迁移至 `GET /api/characters/id/{character_id}`。


## Schemas (数据模型)


*   **`ChatSessionCreate`**: 用于创建新会话的输入 (对应 [`schemas.ChatSessionCreate`](app/schemas.py:12))。
    *   `name` (str | None, default: None): 会话的名称。
*   **`ChatSession`**: 表示一个聊天会话 (对应 [`schemas.ChatSession`](app/schemas.py:16))。
    *   `id` (str): 会话的唯一标识符 (自动生成)。
    *   `name` (str | None, default: None): 会话的名称。
    *   `created_at` (datetime): 会话创建的时间戳 (自动生成)。
    *   `is_main_character_exist` (bool): 指示该会话是否存在关联的主角色（`is_player` 为 `true` 的角色）。
*   **`MessageSendRequest`**: 用于发送消息的输入 (对应 [`schemas.MessageSendRequest`](app/schemas.py:52))。
    *   `content` (str): 消息的文本内容。
*   **`ChatMessageCreate`**: 用于在数据库中创建聊天消息的内部模式 (对应 [`schemas.ChatMessageCreate`](app/schemas.py:39)，基于 [`schemas.ChatMessageBase`](app/schemas.py:26))。
    *   `session_id` (str): 消息所属的会话 ID。
    *   `role` (Literal["user", "assistant", "system", "tool"]): 消息发送者的角色。
    *   `content` (str | None, default: None): 消息的文本内容。对于仅进行工具调用的助手消息，此字段可以为 null。
    *   `name` (str | None, default: None): 当 `role` 是 "tool" 时，表示工具的名称。
    *   `tool_call_id` (str | None, default: None): 对于助手发起的工具调用或工具返回结果时，关联的工具调用ID。
    *   `tool_arguments` (Dict | None, default: None): 当 `role` 是 "assistant" 且助手决定进行工具调用时，此字段包含工具调用的参数。
*   **`ChatMessage`**: 表示一条聊天消息 (对应 [`schemas.ChatMessage`](app/schemas.py:43)，基于 [`schemas.ChatMessageBase`](app/schemas.py:26))。
    *   `id` (int): 消息的唯一标识符 (数据库生成)。
    *   `session_id` (str): 消息所属的会话 ID。
    *   `role` (Literal["user", "assistant", "system", "tool"]): 消息发送者的角色。
    *   `content` (str | None): 消息的文本内容。
    *   `name` (str | None, default: None): 当 `role` 是 "tool" 时，表示工具的名称。
    *   `tool_call_id` (str | None, default: None): 对于助手发起的工具调用或工具返回结果时，关联的工具调用ID。
    *   `tool_arguments` (Dict | None, default: None): 当 `role` 是 "assistant" 且助手决定进行工具调用时，此字段包含工具调用的参数。
    *   `created_at` (datetime): 消息创建的时间戳 (自动生成)。
    *   `suggestions` (List[str] | None, default: None): 与此消息关联的对话选项列表 (仅对助手消息有意义)。
*   **`CharacterCreate`**: 用于创建新角色的输入。
    *   `name` (str): 角色名称。
    *   `session_id` (str): 关联的会话ID。
    *   `race_id` (int): 种族 ID。
    *   `class_id` (int): 职业 ID。
    *   `strength` (int): 力量值。
    *   `dexterity` (int): 敏捷值。
    *   `constitution` (int): 体质值。
    *   `intelligence` (int): 智力值。
    *   `wisdom` (int): 感知值。
    *   `charisma` (int): 魅力值。
    *   `proficiency_ids` (List[int]): 选择的技能熟练项 ID 列表。
    *   `half_elf_choices` (List[str] | None, optional): 半精灵种族的属性选择（需要选择两个除魅力外的属性）。
    *   `is_player` (bool, optional, default: false): 角色是否为玩家控制。
    *   `is_male` (bool, optional, default: false): 角色性别
*   **`Character`**: 代表一张完整的角色卡 (对应 [`schemas.Character`](app/schemas.py:80))。
    *   `id` (str): 角色唯一ID。
    *   `name` (str): 角色名称。
    *   `created_at` (datetime): 创建时间。
    *   `gold` (int): 金币数量。
    *   `experience` (int): 经验值。
    *   `level` (int): 等级。
    *   `armor` (int): 护甲等级。
    *   `speed` (int): 速度。
    *   `health` (int): 当前生命值。
    *   `temp_health` (int): 临时生命值。
    *   `race_id` (int): 种族 ID。
    *   `class_id` (int): 职业 ID。
    *   `spells` (List[str]): 法术列表。
    *   `features` (List[str]):特性列表。
    *   `proficiencies` (List[str]): 熟练项列表。
    *   `equipment` (Dict[str, Dict[str, Any]]): 装备，格式为 `{"装备名": {"item_name": "装备名", "item_description": "装备描述", "item_quantity": 数量}}`。
    *   `inventory_items` (Dict[str, Dict[str, Any]]): 物品栏，格式为 `{"物品名": {"item_name": "物品名", "item_description": "物品描述", "item_quantity": 数量}}`。
    *   `strength` (int): 力量值。
    *   `strength_proficiency` (bool): 力量豁免熟练。
    *   `dexterity` (int): 敏捷值。
    *   `dexterity_proficiency` (bool): 敏捷豁免熟练。
    *   `constitution` (int): 体质值。
    *   `constitution_proficiency` (bool): 体质豁免熟练。
    *   `intelligence` (int): 智力值。
    *   `intelligence_proficiency` (bool): 智力豁免熟练。
    *   `wisdom` (int): 感知值。
    *   `wisdom_proficiency` (bool): 感知豁免熟练。
    *   `charisma` (int): 魅力值。
    *   `charisma_proficiency` (bool): 魅力豁免熟练。
    *   `is_player` (bool): 角色是否为玩家控制。
    *   `is_male` (bool):角色性别
*   **`StoryCreateRequest`**: `title`(str), `theme`(str|None), `N`(int, >0), `style`(str|None), `created_by`(str|None)。
    * 额外：`session_id`(str|None)；若提供，后端会用该会话中的玩家角色（`is_player=True`）作为 `player_character` 传给剧情生成。
*   **`StoryWithOutlineResponse`**: `story_id`(int), `title`(str), `theme`(str|None), `outline_version`(int), `outline`(PlotOutlineSchema)。
*   **`StorySchema`**: `id`, `title`, `theme`, `created_by`, `created_at`, `updated_at`。
*   **`PlotNodeSchema`**: `index`, `title`, `status`(Pending/InProgress/Finish/Canceled), `is_ending`(bool), `summary`。
*   **`PlotOutlineSchema`**: `nodes` (List[PlotNodeSchema])。
*   **`SynopsisCreateRequest`**: `style`(str|None), `word_limit`(int, >0, default 100), `language`(str|None)。
*   **`SynopsisSchema`**: `id`, `story_id`, `outline_version`, `content`, `is_active`, `created_at`。
*   **`PlayerFeedbackCreateRequest`**: `feedback_text`(str), `type`(`ModifyExisting` / `CreateNew`)。
*   **`PlayerFeedbackSchema`**: `id`, `story_id`, `outline_version`(int|None), `synopsis_id`(int|None), `feedback_text`, `type`, `processed`(bool), `created_at`。
