import inspect
import logging
import os
import json
from lightrag.config_manager import get_app_config
from lightrag.kg.shared_storage import (
    finalize_share_data,
    initialize_pipeline_status,
)
from lightrag.lightrag import LightRAG
from lightrag.rerank import get_rerank_func
from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import EmbeddingFunc


class LightRAGError(Exception):
    """Base exception for LightRAG operations"""

    pass


class LightRagManager:
    """LightRAG Manager to handle LightRAG instances per collection"""

    def __init__(self):
        app_config = get_app_config()

        self.logger = logging.getLogger("lightrag")
        self.rag_instances = {}
        self.config_manager = None
        self.lightrag_config = app_config.lightrag_config
        self.llm_config = app_config.llm_config
        self.embedding_config = app_config.embedding_config
        self.rerank_config = app_config.rerank_config

    def set_config_manager(self, config_manager):
        """设置配置管理器实例"""
        self.config_manager = config_manager
        self.logger.info("配置管理器已设置")

    async def list_collections(self):
        working_dir = str(self.lightrag_config.WORKING_DIR)
        if not os.path.exists(working_dir):
            return []

        collections = [
            name
            for name in os.listdir(working_dir)
            if os.path.isdir(os.path.join(working_dir, name))
        ]

        result = {}
        for name in collections:
            status_path = os.path.join(working_dir, name, "kv_store_doc_status.json")
            try:
                if os.path.exists(status_path):
                    with open(status_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result[name] = data
                else:
                    result[name] = {}
            except Exception as e:
                # keep listing robust: log and return empty dict for this collection
                self.logger.debug(
                    f"Failed to read doc status for collection {name}: {e}"
                )
                result[name] = {}

        return result

    async def get_rag_instance(self, collection_id) -> LightRAG | None:
        """Get or create a LightRAG instance for the given collection"""
        working_dir = str(self.lightrag_config.WORKING_DIR)
        if not os.path.exists(os.path.join(working_dir, collection_id)):
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
                self.llm_config.LLM_MODEL,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                base_url=self.llm_config.LLM_BINDING_HOST,
                api_key=self.llm_config.LLM_BINDING_API_KEY,
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
                # 获取动态配置
                embedding_config = self.embedding_config.model_dump()
                binding = embedding_config["EMBEDDING_BINDING"]

                if binding == "ollama":
                    from lightrag.llm.ollama import ollama_embed

                    return await ollama_embed(
                        texts,
                        embed_model=embedding_config["EMBEDDING_MODEL"],
                        host=embedding_config["EMBEDDING_BINDING_HOST"],
                        api_key=embedding_config["EMBEDDING_BINDING_API_KEY"],
                    )
                elif binding == "jina":
                    from lightrag.llm.jina import jina_embed

                    return await jina_embed(
                        texts,
                        dimensions=embedding_config["EMBEDDING_DIM"],
                        base_url=embedding_config["EMBEDDING_BINDING_HOST"],
                        api_key=embedding_config["EMBEDDING_BINDING_API_KEY"],
                    )
                else:  # openai and compatible
                    from lightrag.llm.openai import openai_embed

                    return await openai_embed(
                        texts,
                        model=embedding_config["EMBEDDING_MODEL"],
                        base_url=embedding_config["EMBEDDING_BINDING_HOST"],
                        api_key=embedding_config["EMBEDDING_BINDING_API_KEY"],
                    )
            except ImportError as e:
                raise Exception(f"Failed to import {binding} embedding: {e}")

        return optimized_embedding_function

    async def create_lightrag_instance(self, collection_id: str) -> LightRAG:
        """
        Create a new LightRAG instance for the given collection.
        Since LightRAG is now stateless, we create a fresh instance each time.
        """
        try:
            # 获取动态配置
            embedding_config = self.embedding_config.model_dump()
            embedding_func = EmbeddingFunc(
                embedding_dim=embedding_config["EMBEDDING_DIM"],
                func=self.create_optimized_embedding_function(),
            )

            rerank_model_func = get_rerank_func()
            

            llm_func = self._create_llm_model_func(self.llm_config.LLM_BINDING)

            rag = LightRAG(
                working_dir=str(self.lightrag_config.WORKING_DIR),
                workspace=collection_id,
                llm_model_func=llm_func,
                llm_model_name=self.llm_config.LLM_MODEL,
                llm_model_max_async=self.lightrag_config.LLM_MODEL_MAX_ASYNC,
                summary_max_tokens=self.lightrag_config.SUMMARY_MAX_TOKENS,
                summary_context_size=self.lightrag_config.SUMMARY_CONTEXT_SIZE,
                chunk_token_size=self.lightrag_config.CHUNK_TOKEN_SIZE,
                chunk_overlap_token_size=self.lightrag_config.CHUNK_OVERLAP_SIZE,
                llm_model_kwargs={},
                embedding_func=embedding_func,
                default_llm_timeout=60,
                default_embedding_timeout=60,
                kv_storage=self.lightrag_config.KV_STORAGE,
                graph_storage=self.lightrag_config.GRAPH_STORAGE,
                vector_storage=self.lightrag_config.VECTOR_STORAGE,
                doc_status_storage=self.lightrag_config.DOC_STATUS_STORAGE,
                vector_db_storage_cls_kwargs={
                    "cosine_better_than_threshold": self.lightrag_config.COSINE_THRESHOLD
                },
                enable_llm_cache_for_entity_extract=self.lightrag_config.ENABLE_LLM_CACHE_FOR_ENTITY_EXTRACT,
                enable_llm_cache=self.lightrag_config.ENABLE_LLM_CACHE,
                rerank_model_func=rerank_model_func,
                max_parallel_insert=self.lightrag_config.MAX_PARALLEL_INSERT,
                max_graph_nodes=self.lightrag_config.MAX_GRAPH_NODES,
                addon_params={
                    "language": self.lightrag_config.SUMMARY_LANGUAGE,
                    "entity_types": self.lightrag_config.ENTITY_TYPES,
                },
            )

            await rag.initialize_storages()
            await initialize_pipeline_status()
            await rag.check_and_migrate_data()
            # pipeline_status = await get_namespace_data("pipeline_status")
            return rag

        except Exception as e:
            self.logger.error(
                f"Failed to create LightRAG instance for collection '{collection_id}': {str(e)}"
            )
            raise LightRAGError(f"Failed to create LightRAG instance: {str(e)}") from e

    async def clear_rag_instance(self, collection_id: str):
        """Clear the LightRAG instance for the given collection"""
        self.rag_instances.pop(collection_id, None)
        if collection_id in self.rag_instances:
            rag = self.rag_instances[collection_id]
            # Clean up database connections
            await rag.finalize_storages()
            finalize_share_data()
