from typing import List, Optional
from pydantic import BaseModel, Field
from lightrag.path_manager import get_default_storage_dir
import os
import json
import threading


class LightRAGConfig(BaseModel):
    """
    Centralized configuration for LightRAG.
    Implemented as a pydantic model (JSON-serializable).
    """

    WORKING_DIR: str = Field(
        default_factory=lambda: str(get_default_storage_dir() / "workspace")
    )
    KV_STORAGE: str = "JsonKVStorage"
    VECTOR_STORAGE: str = "NanoVectorDBStorage"
    GRAPH_STORAGE: str = "NetworkXStorage"
    DOC_STATUS_STORAGE: str = "JsonDocStatusStorage"
    CHUNK_TOKEN_SIZE: int = 1200
    CHUNK_OVERLAP_TOKEN_SIZE: int = 100
    LLM_MODEL_MAX_ASYNC: int = 20
    COSINE_BETTER_THAN_THRESHOLD: float = 0.2
    MAX_BATCH_SIZE: int = 32
    ENTITY_EXTRACT_MAX_GLEANING: int = 0
    SUMMARY_TO_MAX_TOKENS: int = 2000
    FORCE_LLM_SUMMARY_ON_MERGE: int = 10
    DEFAULT_LANGUAGE: str = "Simplified Chinese"
    COSINE_THRESHOLD: float = 0.2
    ENABLE_LLM_CACHE_FOR_ENTITY_EXTRACT: bool = True
    ENABLE_LLM_CACHE: bool = True
    MAX_PARALLEL_INSERT: int = 2
    MAX_GRAPH_NODES: int = 1000
    CHUNK_OVERLAP_SIZE: int = 100
    SUMMARY_CONTEXT_SIZE: int = 12000
    SUMMARY_MAX_TOKENS: int = 3000
    MAX_ASYNC: int = 4
    SUMMARY_LANGUAGE: str = "Simplified Chinese"
    # store as list for easier programmatic use; if you want to keep the JSON string,
    # use .json() / .model_dump_json()
    ENTITY_TYPES: List[str] = Field(
        default_factory=lambda: [
            "Organization",
            "Person",
            "Location",
            "Event",
            "Technology",
            "Equipment",
            "Product",
            "Document",
            "Category",
        ]
    )

    # Query control configuration
    TOP_K: int = 30
    CHUNK_TOP_K: int = 10
    MAX_ENTITY_TOKENS: int = 10000
    MAX_RELATION_TOKENS: int = 10000
    MAX_TOTAL_TOKENS: int = 30000
    HISTORY_TURNS: int = 0
    OLLAMA_EMULATING_MODEL_NAME: str = "lightrag"
    OLLAMA_EMULATING_MODEL_TAG: str = "latest"
    VERBOSE: str = "false"


class LLMConfig(BaseModel):
    """Centralized configuration for LLM"""

    LLM_BINDING: Optional[str] = None  # openai, ollama
    LLM_MODEL: Optional[str] = None
    LLM_BINDING_HOST: Optional[str] = None
    LLM_BINDING_API_KEY: Optional[str] = None
    LLM_TIMEOUT: int = 2400  # 默认超时 2400 秒（Worker: 4800s, Health Check: 4815s）


class EmbeddingConfig(BaseModel):
    """Centralized configuration for Embedding"""

    EMBEDDING_BINDING: str = "openai"
    EMBEDDING_MODEL: Optional[str] = None
    EMBEDDING_BINDING_HOST: Optional[str] = None
    EMBEDDING_BINDING_API_KEY: Optional[str] = None
    EMBEDDING_DIM: int = 1024
    EMBEDDING_BATCH_NUM: int = 10
    EMBEDDING_FUNC_MAX_ASYNC: int = 8
    EMBEDDING_MAX_TOKEN_SIZE: int = 8192
    EMBEDDING_TIMEOUT: int = 600  # 默认超时 600 秒（Embedding 通常较快）


class RerankConfig(BaseModel):
    """Centralized configuration for Rerank functionality"""

    ENABLE_RERANK: bool = True
    RERANK_BINDING: Optional[str] = None  # null, cohere, jina, aliyun
    RERANK_MODEL: Optional[str] = None
    RERANK_BINDING_HOST: Optional[str] = None
    RERANK_BINDING_API_KEY: Optional[str] = None
    MIN_RERANK_SCORE: float = 0.6


class AppConfig(BaseModel):
    """Top-level application config that aggregates sub-configs.

    Expected JSON shape (example):
    {
      "lightrag_config": { ... },
      "llm_config": { ... },
      "embedding_config": { ... },
      "rerank_config": { ... }
    }
    """

    lightrag_config: LightRAGConfig = Field(default_factory=LightRAGConfig)
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    embedding_config: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    rerank_config: RerankConfig = Field(default_factory=RerankConfig)

    @classmethod
    def _default_path(cls) -> str:
        """Return the default path for app_config.json in the default storage dir."""
        default_storage = str(get_default_storage_dir())
        os.makedirs(default_storage, exist_ok=True)
        return os.path.join(default_storage, "app_config.json")

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """Load AppConfig from a JSON file. If the file does not exist, return a default instance.

        Args:
            path: Optional path to JSON file. If None, uses the default storage path.

        Returns:
            AppConfig instance loaded from file or defaults when loading fails.
        """
        target = path or cls._default_path()
        try:
            if os.path.exists(target):
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls.model_validate(data)
            else:
                return cls()
        except Exception:
            # If anything goes wrong, return defaults instead of raising so callers can continue.
            return cls()

    def save(self, path: Optional[str] = None) -> None:
        """Save the AppConfig to a JSON file.

        Args:
            path: Optional path to JSON file. If None, uses the default storage path.
        """
        target = path or self._default_path()
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(target), exist_ok=True)
            # Use pydantic's model_dump to get a serializable dict
            data = self.model_dump()
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Silently ignore save errors for now; callers may handle logging if needed.
            pass


# Module-level cache and lock to provide a thread-safe singleton-like access
# to the application's `AppConfig`.
_config_lock = threading.Lock()
_config_instance: Optional[AppConfig] = None


def get_app_config(path: Optional[str] = None) -> AppConfig:
    """Return the cached AppConfig instance, loading it from disk on first call.

    This function is thread-safe. If `path` is provided on first call it will be
    used to load the configuration; subsequent calls ignore the `path` and
    return the cached instance until `reload_app_config` is called.
    """
    global _config_instance
    with _config_lock:
        if _config_instance is None:
            _config_instance = AppConfig.load(path)
        return _config_instance


def reload_app_config(path: Optional[str] = None) -> AppConfig:
    """Force re-load the AppConfig from disk (or create defaults).

    This replaces the module cache with a fresh instance and returns it.
    """
    global _config_instance
    with _config_lock:
        _config_instance = AppConfig.load(path)
        return _config_instance


def save_app_config(path: Optional[str] = None) -> None:
    """Save the currently cached AppConfig to disk.

    If no cached instance exists this will load the default instance and save
    that. The operation is thread-safe.
    """
    global _config_instance
    with _config_lock:
        if _config_instance is None:
            _config_instance = AppConfig.load(path)
        _config_instance.save(path)
