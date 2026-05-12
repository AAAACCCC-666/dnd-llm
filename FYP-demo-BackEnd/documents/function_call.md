# LangChain 工具系统实现

本文档介绍了基于 LangChain 框架的工具系统实现，该系统允许语言模型调用外部工具来获取信息或执行操作。

**核心文件：** (注意：文件路径中的行号仅供参考，可能因代码更新而变化)
*   `app/services/langchain_service.py` - 主要服务入口 (`get_langchain_stream` 函数)
*   `app/services/message_builder.py` - 消息构建器 (`build_messages_direct` 函数)
*   `app/services/langchain_tools/tool_executor.py` - 工具执行器 (`LangChainToolExecutor` 类)
*   `app/services/langchain_tools/tool_registry.py` - 工具注册器 (`LangChainToolRegistry` 类)
*   `app/services/langchain_tools/tool_base.py` - 工具基类 (`BaseDnDTool`)
*   `app/services/langchain_tools/tools.py` - 工具实现

## 核心流程

LangChain 工具系统允许语言模型在需要时请求调用外部工具来获取额外信息或执行特定操作，然后将工具返回的结果整合到其后续的响应中。本系统基于自定义的 `BaseDnDTool` 基类实现，该基类继承自 LangChain 的 `BaseTool`。

实现围绕 `app/services/langchain_service.py` 中的 `get_langchain_stream` 函数，结合 `LangChainToolExecutor` 类。具体步骤如下：

1.  **工具定义与注册 (Tools Definition & Registration)**:
    *   工具定义基于自定义的 `BaseDnDTool` 基类，在 `app/services/langchain_tools/tools.py` 中实现。
    *   每个工具类包含：
        - `name`: 工具的唯一标识符
        - `description`: 工具功能的详细描述
        - `args_schema`: 基于 Pydantic 的参数验证模式
        - `_execute_tool()`: 具体的工具逻辑实现方法
    *   工具注册由 `LangChainToolRegistry` 类管理，通过 `register_all_tools()` 函数手动注册所有工具。
    *   例如，`RollDiceTool` 类定义了掷骰子功能，包含完整的参数验证和类型注解。
    *   通过 `langchain_tool_registry.get_all_tools()` 获取所有已注册工具的列表。

2.  **发起 API 请求 (Initiating API Request)**:
    *   在 `get_langchain_stream` 中，使用 LangChain 的 `ChatOpenAI` 客户端创建聊天模型实例。
    *   将已注册的工具列表绑定到模型：`llm = llm.bind_tools(tools)`。
    *   使用 `build_messages_direct` 直接从数据库构建消息。

3.  **处理模型响应流 (Processing Model's Response Stream)**:
    *   直接使用 `llm.astream()` 处理流式响应。
    *   通过 `async for chunk in response_stream` 处理事件。
    *   支持实时流式输出文本内容和工具调用状态。

4.  **识别工具调用请求 (Identifying Tool Call Request)**:
    *   当模型决定调用工具时，LangChain 会生成包含 `tool_calls` 的 `AIMessage`。
    *   系统会检测到工具调用并提取工具名称、参数和调用 ID。
    *   工具调用信息会以结构化格式返回。

5.  **执行本地工具 (Executing Local Tools via LangChainToolExecutor)**:
    *   使用 `LangChainToolExecutor` 处理工具调用。
    *   执行器通过工具名称查找对应的 LangChain 工具实例。
    *   使用 Pydantic 模型进行参数验证和类型转换。
    *   异步执行工具并返回结构化结果。
    *   支持错误处理和异常捕获。

6.  **返回结果给模型 (Returning Results to the Model)**:
    *   工具执行结果被格式化为 LangChain 的 `ToolMessage`。
    *   结果被添加到消息历史中，供模型在后续响应中使用。

7.  **模型继续生成 (Model Continues Generation)**:
    *   模型接收工具执行结果后，利用这些信息继续生成最终响应。
    *   支持多轮工具调用和复杂的工具链。
    *   流式输出最终的用户回复。

8.  **结束对话 (Ending the Conversation)**:
    *   当模型完成响应生成或达到内部迭代上限时，发送 "stream_end" 事件。当前实现中最多允许 5 轮“模型响应 → 工具调用 → 再次响应”的循环，超过将以 `reason: "max_iterations"` 结束。
    *   所有消息（包括工具调用和结果）都被保存到数据库。

## 技术特性

### 自定义工具基类架构
本系统基于自定义的 `BaseDnDTool` 基类构建，该基类继承自 LangChain 的 `BaseTool`，提供：
- **统一的错误处理**: 标准化的异常捕获和错误信息格式化
- **数据库会话管理**: 自动处理数据库连接的创建和清理
- **参数验证**: 基于 Pydantic 模型的严格类型检查
- **角色验证**: 内置的角色存在性验证和名称获取功能
- **标准化返回格式**: 使用 `ToolResult` 类统一工具返回值格式

### 工具基类架构
- 所有工具类都继承 `BaseDnDTool` 基类（不使用 `@tool` 装饰器），确保一致的行为
- `BaseDnDTool` 继承自 LangChain 的 `BaseTool`，提供完整的工具生命周期管理
- 每个工具类必须实现 `_execute_tool()` 方法来定义具体的工具逻辑
- 支持复杂的 Pydantic 模型作为参数类型（通过 `args_schema` 属性定义）
- 自动生成标准化的 JSON Schema 供模型使用
- 提供同步和异步执行支持
- 内置数据库会话管理和统一的错误处理机制

### 工具注册系统
- 使用 `LangChainToolRegistry` 类管理工具注册
- 通过 `register_all_tools()` 函数手动注册工具，需要在函数中明确列出每个工具实例
- 工具在应用启动时通过模块导入自动执行注册（`tools.py` 模块底部调用 `register_all_tools()`）
- 提供工具元数据查询和管理功能
- 通过 `get_all_tools()` 方法获取所有已注册工具

### 流式工具执行
- 支持工具调用的实时事件流
- 提供工具开始、进行中、完成和错误状态的细粒度反馈
- 内部事件类型：`tool_start`、`tool_result`、`tool_error`
- 前端 API 事件类型：`tool_call_start`、`tool_call_result`、`tool_call_error`（在 chat.py 中转换）
- 与前端实时更新兼容

### 消息与记忆管理
- `build_messages_direct()` 直接查询 `chat_messages` 表构建 LangChain 消息。
- 最新一条用户消息在构建时会注入 RAG 检索结果、当前玩家角色以及 NPC 概览，其余历史消息以原始内容回放，保障上下文连贯。
- 所有上下文均来自数据库存量数据，天然与现有存储结构兼容，可按需扩展自定义规则。

## 工具列表

*   **`roll_dice`**
    *   **描述**: 模拟掷一个或多个指定面数的骰子，并返回结果列表。
    *   **Python 实现**: `RollDiceTool` 类
    *   **参数**:
        *   `sides` (int): 骰子的面数 (例如, 6 表示D6, 20 表示D20)。最小为1。
        *   `num_dice` (int, 可选, 默认值: 1): 投掷的骰子数量。

*   **`modify_character_integer_attribute`**
    *   **描述**: 修改指定角色的单个整数属性值，例如金币、生命值或力量。在角色属性因剧情推进、战斗或任何其他事件发生变化时，你必须调用相应的工具来更新数据库中的角色属性。
    *   **Python 实现**: `ModifyCharacterIntegerAttributeTool` 类
    *   **参数**:
        *   `character_id` (str): 要修改的角色的唯一ID。
        *   `attribute` (str): 要修改的属性名称。允许的值：`gold`, `experience`, `level`, `armor`, `speed`, `health`, `temp_health`, `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma`。
        *   `value` (int): 要设置的新的整数值。

*   **`modify_character_bool_attribute`**
    *   **描述**: 修改指定角色的单个布尔属性值，例如豁免熟练项或角色状态。
    *   **Python 实现**: `ModifyCharacterBoolAttributeTool` 类
    *   **参数**:
        *   `character_id` (str): 要修改的角色的唯一ID。
        *   `attribute` (str): 要修改的属性名称。允许的值：`strength_proficiency`, `dexterity_proficiency`, `constitution_proficiency`, `intelligence_proficiency`, `wisdom_proficiency`, `charisma_proficiency`, `is_player`, `is_male`。
        *   `value` (bool): 要设置的新的布尔值。

*   **`modify_character_race_and_class`**
    *   **描述**: 修改指定角色的种族和职业。
    *   **Python 实现**: `ModifyCharacterRaceAndClassTool` 类
    *   **参数**:
        *   `character_id` (str): 要修改的角色的唯一ID。
        *   `race_id` (int): 要设置的新的种族ID。
        *   `class_id` (int): 要设置的新的职业ID。

*   **`modify_character_items`**
    *   **描述**: 修改指定角色的装备和物品栏。可以一次性添加、更新或移除多个物品或装备。
    *   **Python 实现**: `ModifyCharacterItemsTool` 类
    *   **参数**:
        *   `character_id` (str): 要修改的角色的唯一ID。
        *   `items` (List[ItemModification]): 要修改的物品列表。
            *   `name` (str): 物品或装备的名称。
            *   `description` (str, 可选, 默认值: ""): 物品或装备的描述。
            *   `quantity` (int): 物品或装备的数量。如果为0，将从角色身上移除。
            *   `type` (str): 修改的类型，'equipment' 表示装备, 'inventory' 表示物品栏中的物品。

*   **`update_plot_node_status`**
    *   **描述**: 更新故事激活剧情列表中特定剧情节点的状态。当故事场景/节点完成、开始或跳过时使用此工具。
    *   **Python 实现**: `UpdatePlotNodeStatusTool` 类
    *   **参数**:
        *   `story_id` (int): 故事ID
        *   `node_index` (int): 剧情节点索引（1-based）
        *   `status` (str): 新的节点状态，必须是 "Pending"、"InProgress"、"Finish" 或 "Canceled" 之一

*   **`mark_plot_node_as_ending`**
    *   **描述**: 标记或取消标记故事激活剧情列表中的特定剧情节点为结局节点。当调整哪些场景算作可能的结局时使用此工具。
    *   **Python 实现**: `MarkPlotNodeAsEndingTool` 类
    *   **参数**:
        *   `story_id` (int): 故事ID
        *   `node_index` (int): 剧情节点索引（1-based）
        *   `is_ending` (bool): 是否为结局节点

*   **`trigger_regenerate_synopsis`**
    *   **描述**: 基于当前激活的剧情列表重新生成故事梗概。在对剧情列表或节点状态进行重大更改后使用此工具，以便玩家看到最新的故事摘要。
    *   **Python 实现**: `TriggerRegenerateSynopsisTool` 类
    *   **参数**:
        *   `story_id` (int): 故事ID
        *   `style` (str, 可选): 梗概风格提示，例如 "light"、"dark"、"anime-like"
        *   `word_limit` (int, 可选, 默认值: 100): 梗概的最大英文单词数
        *   `language` (str, 可选): 目标语言代码（如 `"en"` 或 `"zh"`），若为空由模型自行决定

## 兼容性说明

本系统保持了以下兼容性：

1. **API 兼容性**: 所有现有的 REST API 端点保持不变
2. **数据库兼容性**: 消息和工具调用数据使用相同的数据库结构存储
3. **前端兼容性**: 前端无需修改即可使用后端

## 环境配置

相关环境变量：
- `OPENAI_MODEL`: 指定使用的模型（默认 gpt-4o-mini）。
- `OPENAI_API_KEY`: LangChain OpenAI 客户端使用的 API Key。
- `OPENAI_BASE_URL`: 可选，自定义 OpenAI 兼容服务地址（为空则走官方 endpoint）。

## 性能优势

LangChain 工具系统提供：

1. **更好的类型安全**: 使用 Pydantic 模型进行严格的参数验证
2. **更强的扩展性**: 支持复杂的工具链和多轮调用
3. **更轻量的依赖**: 通过自研基类与注册表，在保持 LangChain 兼容的同时简化运行期开销
4. **更简洁的代码**: 使用基类继承统一工具定义和接口
5. **更好的错误处理**: 统一的异常处理和错误报告机制
