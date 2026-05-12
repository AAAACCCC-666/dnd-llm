# RAG 子系统说明

本文档描述了当前仓库中用于《Dungeon Master's Guide》资料的检索增强生成（Retrieval-Augmented Generation，简称 RAG）初始化与使用方式。

## 总览
- 目标：在服务启动时自动构建/复用 DM 指南的向量索引，以便后续在对话或工具中消费。
- 核心位置：
  - `app/services/rag/rag_config.py`：读取并校验环境变量，形成 `RagConfig`。
  - `app/services/rag/rag.py`：负责 Markdown 解析、嵌入生成、Chroma 持久化，以及向量化流程的异步执行。
  - `app/app_factory.py`：在 FastAPI 生命周期钩子中 `await ensure_dm_vectorstore()`。
  - `assets/DM.md`：默认的 DM 指南原文（向量化源文件）。
  - `data/chromadb/`：默认的 Chroma 向量库持久化目录。

## 初始化流程
1. 应用启动（`uv run main.py`）时，`app_factory.create_app()` 会加载环境、初始化数据库与静态数据。
2. FastAPI 进入 lifespan startup 阶段时调用 `await ensure_dm_vectorstore()`：
   - 若 `RagConfig.dm_source_path` 不存在，记录警告并跳过。
   - 若未显式设置 `RAG_EMBEDDING_MODEL`（即使 `RAG_ENABLED=True`），RAG 会被视为禁用，直接跳过初始化。
   - 初始化嵌入客户端（默认 `OpenAIEmbeddings`，支持自定义 `api_key` 与 `base_url`，兼容 SiliconFlow / OpenAI 等 OpenAI 接口兼容服务）。
   - 使用 `chromadb.PersistentClient` + `Chroma` 连接/创建集合，禁用匿名遥测。
   - 如果集合中已有向量（`collection.count() > 0`），直接复用。
   - 否则读取 `DM.md`，先按 Markdown 头分段，再按字符数递归切分。
   - 批量、并发调用 `aembed_documents` 生成向量，并通过 `asyncio.to_thread` 将批次写入 Chroma。
   - 向量化完成后执行 `persist()` 落盘。
3. 该流程幂等：若初始化过程中失败，下次启动会重新检测并继续执行。

## 环境变量
`app/services/rag/rag_config.py` 会解析以下配置。所有变量均可写入 `.env`（参见 `.env.example` 中的示例值），并会在首启时写入数据库 `config_entries`；此后读取以数据库值为准，环境变量仅在库中缺少记录时兜底。

| 变量名                      | 默认值                       | 说明                                 |
| --------------------------- | ---------------------------- | ------------------------------------ |
| `RAG_ENABLED`               | `True`                       | 控制是否启用 RAG 初始化流程          |
| `RAG_DM_SOURCE_PATH`        | `assets/DM.md`               | 原始 Markdown 文件路径               |
| `RAG_CHROMA_DIR`            | `data/chromadb`              | Chroma 持久化目录（父目录需可写）    |
| `RAG_CHROMA_COLLECTION`     | `dm_guide_2024`              | Chroma 集合名                        |
| `RAG_EMBEDDING_MODEL`       | **必填，无默认值**           | 嵌入模型名称；未设置时强制禁用 RAG  |
| `RAG_EMBEDDING_API_KEY`     | 空（回退 `OPENAI_API_KEY`）  | 嵌入服务 API Key                     |
| `RAG_EMBEDDING_BASE_URL`    | 空（回退 `OPENAI_BASE_URL`） | 嵌入服务 Base URL                    |
| `RAG_EMBEDDING_BATCH_SIZE`  | `16`                         | 单批次文档数量                       |
| `RAG_EMBEDDING_CONCURRENCY` | `4`                          | 并发嵌入任务上限，受 API 速率限制    |
| `RAG_SPLIT_CHUNK_SIZE`      | `4000`                       | 文本切分目标大小（字符）             |
| `RAG_SPLIT_CHUNK_OVERLAP`   | `400`                        | 相邻切片重叠字符数                   |
| `RAG_SPLIT_HEADERS`         | `#=h1,##=h2,...`             | Markdown 头部拆分规则                |
| `RAG_SEARCH_TOP_K`          | `4`                          | 检索时返回的文档数量上限             |

> 提示：未显式提供 `RAG_EMBEDDING_API_KEY`/`RAG_EMBEDDING_BASE_URL` 时，代码会回退至已有的 `OPENAI_*` 配置；可方便地复用同一 API 凭证。必须显式设置 `RAG_EMBEDDING_MODEL` 才会启用 RAG，即便 `RAG_ENABLED=True`。

> 注意：`RAG_EMBEDDING_MODEL` 留空（或未配置）时，即便 `RAG_ENABLED=True`，RAG 初始化也会被强制禁用，以避免在缺少模型配置的情况下误触向量化流程。

## 运行与验证
1. **构建向量库**  
   - 本地运行 `uv run main.py`，关注日志中 `Ensuring DM guide vector store is ready...` 相关输出。
   - 初次执行会消耗一定时间（受文本体积与 API 限速影响）。日志会记录批次进度与耗时。
   - 成功后 `data/chromadb` 会生成多个持久化文件/目录。

2. **重复启动**  
   - 若向量库已存在且条目数大于 0，后续启动会快速跳过构建步骤，仅加载集合。

3. **检索自检**  
   - 通过 `uv run main.py` 启动服务后，调用内部 `build_rag_context("<query>")` 或加入一条用户消息，并关注日志中 `RAG` 命名空间的检索输出。
   - 也可以直接在 REPL 中导入 `app/services/rag/retriever.py` 的 `build_rag_context` 函数，验证返回的 `results`。

## 重新构建向量库
- 若需重新向量化（例如更换源文件、修改切分参数）：
  1. 删除或备份 `data/chromadb` 目录（或指定新的 `RAG_CHROMA_DIR`）。
  2. 确认 `assets/DM.md` 已更新。
  3. 更新 `.env` 中的参数（如需要）。
  4. 再次运行 `uv run main.py` 触发重建。

> 注意：删除向量库前请确认没有其它服务依赖该目录；也可以通过调整 `RAG_CHROMA_COLLECTION` 实现并行维护多个版本。

## 对话时的检索流程
- `app/services/message_builder.py` 中的 `_build_user_context_on_demand()` 会在生成最新一条用户消息上下文时调用 `app/services/rag/retriever.py` 的 `build_rag_context()`。
- 查询内容为该用户消息的原文，默认返回前 `RAG_SEARCH_TOP_K` 条相似度最高的规则文档片段，并将 `results` 写入最终 JSON 的 `DND_related_rules` 字段供 LLM 消费。
- `build_rag_context()` 返回 `status`、`query` 和 `results`，其中消息构建流程仅使用 `results`。
- 当 `RAG_ENABLED=False` 时，`build_rag_context()` 返回 `status: disabled` 且 `results` 为空，`DND_related_rules` 也会保持空数组。
- 若检索报错或未命中新结果，`results` 为空列表，模型端可据此降级。
