"""
LightRAG 系统核心常量

这些常量是系统运行的基石，不应该被用户配置。
更改这些值可能导致系统不稳定或数据损坏。
"""

# ====== 数据存储格式常量 (不可配置) ======
GRAPH_FIELD_SEP = "<SEP>"                    # 数据存储格式分隔符

# ====== 数据库架构常量 (不可配置) ======
DEFAULT_MAX_FILE_PATH_LENGTH = 32768        # Milvus Schema 硬性要求

# ====== 模型元数据常量 (不可配置) ======
DEFAULT_OLLAMA_MODEL_SIZE = 7365960935      # Ollama 模型大小
DEFAULT_OLLAMA_CREATED_AT = "2024-01-15T00:00:00Z"  # Ollama 模型创建时间
DEFAULT_OLLAMA_DIGEST = "sha256:lightrag"    # Ollama 模型摘要

# ====== 算法质量保证常量 (不可配置) ======
DEFAULT_SUMMARY_LENGTH_RECOMMENDED = 600     # 摘要质量保证
DEFAULT_RELATED_CHUNK_NUMBER = 5              # 检索质量保证
DEFAULT_KG_CHUNK_PICK_METHOD = "VECTOR"       # 算法选择逻辑

# ====== 临时保留的常量 (待后续迁移) ======
# 以下常量仍在代码中使用，待后续迁移到 config_manager
DEFAULT_WOKERS = 2                           # 服务器工作进程数
DEFAULT_SUMMARY_LANGUAGE = "English"         # 文档处理默认语言
DEFAULT_MAX_GLEANING = 1                     # 实体抽取最大尝试次数
DEFAULT_TEMPERATURE = 1.0                     # LLM 温度参数
DEFAULT_TIMEOUT = 300                         # Gunicorn 工作进程超时
DEFAULT_MIN_RERANK_SCORE = 0.0                # 重排序最小分数
DEFAULT_RERANK_BINDING = "null"               # 重排序绑定
DEFAULT_LOG_MAX_BYTES = 10485760              # 日志最大字节数
DEFAULT_LOG_BACKUP_COUNT = 5                  # 日志备份数量
DEFAULT_LOG_FILENAME = "lightrag.log"          # 日志文件名
DEFAULT_EMBEDDING_TIMEOUT = 30                 # 嵌入超时时间
