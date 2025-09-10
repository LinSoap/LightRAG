import logging
import os
from ascii_colors import ASCIIColors
from lightrag.kg.shared_storage import (
    finalize_share_data,
    get_namespace_data,
    initialize_pipeline_status,
)
from lightrag.lightrag import LightRAG
from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import EmbeddingFunc


class LightRAGConfig:
    """Centralized configuration for LightRAG"""

    WORKING_DIR = "./rag_storage"
    KV_STORAGE = "JsonKVStorage"
    VECTOR_STORAGE = "NanoVectorDBStorage"
    GRAPH_STORAGE = "NetworkXStorage"
    DOC_STATUS_STORAGE = "JsonDocStatusStorage"
    CHUNK_TOKEN_SIZE = 1200
    CHUNK_OVERLAP_TOKEN_SIZE = 100
    LLM_MODEL_MAX_ASYNC = 20
    COSINE_BETTER_THAN_THRESHOLD = 0.2
    MAX_BATCH_SIZE = 32
    ENTITY_EXTRACT_MAX_GLEANING = 0
    SUMMARY_TO_MAX_TOKENS = 2000
    FORCE_LLM_SUMMARY_ON_MERGE = 10
    EMBEDDING_MAX_TOKEN_SIZE = 8192
    DEFAULT_LANGUAGE = "Simplified Chinese"
    COSINE_THRESHOLD = 0.2
    ENABLE_LLM_CACHE_FOR_ENTITY_EXTRACT = True
    ENABLE_LLM_CACHE = True
    MAX_PARALLEL_INSERT = 2
    MAX_GRAPH_NODES = 1000
    CHUNK_OVERLAP_SIZE = 100
    SUMMARY_CONTEXT_SIZE = 12000
    SUMMARY_MAX_TOKENS = 1200
    MAX_ASYNC = 20
    SUMMARY_LANGUAGE = "Simplified Chinese"
    ENTITY_TYPES = '["Organization", "Person", "Location", "Event", "Technology", "Equipment", "Product", "Document", "Category"]'


class LLMConfig:
    """Centralized configuration for LLM and Embedding"""

    LLM_BINDING = os.getenv("LLM_BINDING", None)  # openai, ollama
    LLM_MODEL = os.getenv("LLM_MODEL", None)
    LLM_BINDING_HOST = os.getenv("LLM_BINDING_HOST", None)
    LLM_BINDING_API_KEY = os.getenv("LLM_BINDING_API_KEY", None)


class EmbeddingConfig:
    """Centralized configuration for Embedding"""

    EMBEDDING_BINDING = os.getenv("EMBEDDING_BINDING", "openai")  # openai, ollama, jina
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", None)
    EMBEDDING_BINDING_HOST = os.getenv("EMBEDDING_BINDING_HOST", None)
    EMBEDDING_BINDING_API_KEY = os.getenv("EMBEDDING_BINDING_API_KEY", None)
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 1024))


class LightRAGError(Exception):
    """Base exception for LightRAG operations"""

    pass


class LightRagManager:
    """LightRAG Manager to handle LightRAG instances per collection"""

    def __init__(self):
        self.logger = logging.getLogger("lightrag")
        self.rag_instances = {}

    async def get_rag_instance(self, collection_id) -> LightRAG | None:
        """Get or create a LightRAG instance for the given collection"""

        print(os.path.exists(os.path.join(LightRAGConfig.WORKING_DIR, collection_id)))
        if not os.path.exists(os.path.join(LightRAGConfig.WORKING_DIR, collection_id)):
            return None
        if collection_id not in self.rag_instances:
            self.rag_instances[collection_id] = await self.create_lightrag_instance(
                collection_id
            )
        return self.rag_instances[collection_id]

    def _create_optimized_openai_llm_func(self):
        """Create optimized OpenAI LLM function with pre-processed configuration"""

        async def optimized_openai_alike_model_complete(
            prompt,
            system_prompt=None,
            history_messages=None,
            keyword_extraction=False,
            **kwargs,
        ) -> str:
            from lightrag.llm.openai import openai_complete_if_cache

            keyword_extraction = kwargs.pop("keyword_extraction", None)
            if keyword_extraction:
                kwargs["response_format"] = GPTKeywordExtractionFormat
            if history_messages is None:
                history_messages = []

            # Use pre-processed configuration to avoid repeated parsing
            kwargs["timeout"] = 60

            return await openai_complete_if_cache(
                LLMConfig.LLM_MODEL,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                base_url=LLMConfig.LLM_BINDING_HOST,
                api_key=LLMConfig.LLM_BINDING_API_KEY,
                **kwargs,
            )

        return optimized_openai_alike_model_complete

    def _create_llm_model_func(self, binding: str):
        """
        Create LLM model function based on binding type.
        Uses optimized functions for OpenAI bindings and lazy import for others.
        """
        try:
            if binding == "ollama":
                from lightrag.llm.ollama import ollama_model_complete

                return ollama_model_complete
            else:  # openai and compatible
                return self._create_optimized_openai_llm_func()
        except ImportError as e:
            raise Exception(f"Failed to import {binding} LLM binding: {e}")

    def create_optimized_embedding_function(
        self,
        # config_cache: LLMConfigCache, binding, model, host, api_key, dimensions, args
    ):
        """
        Create optimized embedding function with pre-processed configuration for applicable bindings.
        Uses lazy imports for all bindings and avoids repeated configuration parsing.
        """

        async def optimized_embedding_function(texts):
            try:

                if EmbeddingConfig.EMBEDDING_BINDING == "ollama":
                    from lightrag.llm.ollama import ollama_embed

                    return await ollama_embed(
                        texts,
                        embed_model=EmbeddingConfig.EMBEDDING_MODEL,
                        host=EmbeddingConfig.EMBEDDING_BINDING_HOST,
                        api_key=EmbeddingConfig.EMBEDDING_BINDING_API_KEY,
                    )
                elif EmbeddingConfig.EMBEDDING_BINDING == "jina":
                    from lightrag.llm.jina import jina_embed

                    return await jina_embed(
                        texts,
                        dimensions=EmbeddingConfig.EMBEDDING_DIM,
                        base_url=EmbeddingConfig.EMBEDDING_BINDING_HOST,
                        api_key=EmbeddingConfig.EMBEDDING_BINDING_API_KEY,
                    )
                else:  # openai and compatible
                    from lightrag.llm.openai import openai_embed

                    return await openai_embed(
                        texts,
                        model=EmbeddingConfig.EMBEDDING_MODEL,
                        base_url=EmbeddingConfig.EMBEDDING_BINDING_HOST,
                        api_key=EmbeddingConfig.EMBEDDING_BINDING_API_KEY,
                    )
            except ImportError as e:
                raise Exception(
                    f"Failed to import {EmbeddingConfig.EMBEDDING_BINDING} embedding: {e}"
                )

        return optimized_embedding_function

    async def create_lightrag_instance(self, collection_id: str) -> LightRAG:
        """
        Create a new LightRAG instance for the given collection.
        Since LightRAG is now stateless, we create a fresh instance each time.
        """
        try:
            # Generate embedding and LLM functions
            # Create embedding function with optimized configuration
            rerank_model_func = None
            embedding_func = EmbeddingFunc(
                embedding_dim=EmbeddingConfig.EMBEDDING_DIM,
                func=self.create_optimized_embedding_function(),
            )

            llm_func = self._create_llm_model_func(LLMConfig.LLM_BINDING)

            rag = LightRAG(
                working_dir=LightRAGConfig.WORKING_DIR,
                workspace=collection_id,
                llm_model_func=llm_func,
                llm_model_name=LLMConfig.LLM_MODEL,
                llm_model_max_async=LightRAGConfig.MAX_ASYNC,
                summary_max_tokens=LightRAGConfig.SUMMARY_MAX_TOKENS,
                summary_context_size=LightRAGConfig.SUMMARY_CONTEXT_SIZE,
                chunk_token_size=LightRAGConfig.CHUNK_TOKEN_SIZE,
                chunk_overlap_token_size=LightRAGConfig.CHUNK_OVERLAP_SIZE,
                llm_model_kwargs={},
                embedding_func=embedding_func,
                default_llm_timeout=60,
                default_embedding_timeout=60,
                kv_storage=LightRAGConfig.KV_STORAGE,
                graph_storage=LightRAGConfig.GRAPH_STORAGE,
                vector_storage=LightRAGConfig.VECTOR_STORAGE,
                doc_status_storage=LightRAGConfig.DOC_STATUS_STORAGE,
                vector_db_storage_cls_kwargs={
                    "cosine_better_than_threshold": LightRAGConfig.COSINE_THRESHOLD
                },
                enable_llm_cache_for_entity_extract=LightRAGConfig.ENABLE_LLM_CACHE_FOR_ENTITY_EXTRACT,
                enable_llm_cache=LightRAGConfig.ENABLE_LLM_CACHE,
                rerank_model_func=rerank_model_func,
                max_parallel_insert=LightRAGConfig.MAX_PARALLEL_INSERT,
                max_graph_nodes=LightRAGConfig.MAX_GRAPH_NODES,
                addon_params={
                    "language": LightRAGConfig.SUMMARY_LANGUAGE,
                    "entity_types": LightRAGConfig.ENTITY_TYPES,
                },
                # ollama_server_infos=LightRAGConfig.OLLAMA_SERVER_INFOS,
            )

            await rag.initialize_storages()
            await initialize_pipeline_status()
            await rag.check_and_migrate_data()
            pipeline_status = await get_namespace_data("pipeline_status")
            ASCIIColors.green("\nServer is ready to accept connections! 🚀\n")
            return rag

        except Exception as e:
            self.logger.error(
                f"Failed to create LightRAG instance for collection '{collection_id}': {str(e)}"
            )
            raise LightRAGError(f"Failed to create LightRAG instance: {str(e)}") from e

    async def clear_rag_instance(self, collection_id: str):
        """Clear the LightRAG instance for the given collection"""
        if collection_id in self.rag_instances:
            rag = self.rag_instances[collection_id]
            # Clean up database connections
            await rag.finalize_storages()
            finalize_share_data()
