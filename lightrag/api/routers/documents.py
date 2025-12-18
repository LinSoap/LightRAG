from pathlib import Path
import shutil
import traceback
from typing import List
from datetime import datetime
from lightrag.path_manager import get_default_storage_dir
from lightrag.api.schemas.document import (
    DeleteDocRequest,
    DocumentItem,
    DocumentsListData,
    DocumentChunk,
    DocumentChunksData,
    DocumentUploadData,
    BatchUploadData,
    BatchUploadItem,
    PipelineStatusData,
    TrackStatusData,
    DocumentDeletionData,
    RetryDocumentData,
)
from lightrag.api.schemas.common import GenericResponse
from lightrag.api.utils.background import (
    background_delete_documents,
    pipeline_index_file,
    pipeline_index_files_batch,
)
from lightrag.api.utils.file import sanitize_filename
from lightrag.base import DocProcessingStatus, DocStatus
from lightrag.document_manager import DocumentManager
from lightrag.lightrag_manager import LightRagManager
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from lightrag.api.utils.date import format_datetime

import logging

# module logger
logger = logging.getLogger(__name__)

from lightrag.utils import generate_track_id


def create_document_routers() -> APIRouter:
    """Factory to create documents APIRouter using provided or global logger/manager.

    If logger or manager is not provided, defaults are used.
    """
    router = APIRouter(prefix="/documents", tags=["documents"])

    lightrag_manager = LightRagManager()

    @router.get("", response_model=GenericResponse[DocumentsListData])
    async def documents(collection_id: str) -> GenericResponse[DocumentsListData]:
        try:
            rag = await lightrag_manager.get_rag_instance(collection_id)

            # Use the initialized doc_status instance (not the class) and await its async get_all()
            documents_raw = await rag.doc_status.get_all()

            doc_list = []
            for doc_id, doc_data in documents_raw.items():
                # Normalize dict to match DocProcessingStatus constructor
                data = doc_data.copy() if isinstance(doc_data, dict) else {}
                data.pop("content", None)
                if "file_path" not in data:
                    data["file_path"] = "no-file-path"
                if "metadata" not in data:
                    data["metadata"] = {}
                if "error_msg" not in data:
                    data["error_msg"] = None

                try:
                    doc_status = DocProcessingStatus(**data)
                except Exception:
                    # Fallback: skip malformed entries
                    logger.exception(f"Malformed doc status for {doc_id}, skipping")
                    continue

                doc_list.append(
                    DocumentItem(
                        id=doc_id,
                        collection_id=collection_id,
                        content_summary=doc_status.content_summary,
                        content_length=doc_status.content_length,
                        status=doc_status.status,
                        created_at=format_datetime(doc_status.created_at),
                        updated_at=format_datetime(doc_status.updated_at),
                        track_id=doc_status.track_id,
                        chunks_count=doc_status.chunks_count,
                        error_msg=doc_status.error_msg,
                        metadata=doc_status.metadata,
                        file_path=doc_status.file_path,
                    )
                )

            data = DocumentsListData(
                documents=doc_list,
                total_documents=len(doc_list),
                collection_id=collection_id,
            )

            return GenericResponse(
                status="success",
                message=f"Found {len(doc_list)} documents in collection '{collection_id}'",
                data=data,
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception("Error in documents endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/chunk", response_model=GenericResponse[DocumentChunksData])
    async def get_document_chunks(
        collection_id: str, doc_id: str, limit: int = 10, offset: int = 0
    ) -> GenericResponse[DocumentChunksData]:
        try:
            rag = await lightrag_manager.get_rag_instance(collection_id)
            if rag is None:
                logger.warning(f"Collection {collection_id} not found")
                raise HTTPException(status_code=404, detail="Collection not found")

            chunks_raw = await rag.text_chunks.get_by_doc_id(doc_id)

            # Convert chunks to our data model
            chunks = []
            for i, chunk in enumerate(chunks_raw[offset : offset + limit]):
                chunk_data = (
                    chunk if isinstance(chunk, dict) else {"content": str(chunk)}
                )
                chunks.append(
                    DocumentChunk(
                        id=chunk_data.get("id", f"{doc_id}_chunk_{i}"),
                        content=chunk_data.get("content", ""),
                        document_id=doc_id,
                        chunk_index=offset + i,
                        metadata=chunk_data.get("metadata", {}),
                    )
                )

            data = DocumentChunksData(
                doc_id=doc_id,
                chunks=chunks,
                total_chunks=len(chunks_raw),
                limit=limit,
                offset=offset,
            )

            return GenericResponse(
                status="success",
                message=f"Retrieved {len(chunks)} chunks for document '{doc_id}'",
                data=data,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception("Error in get_document_chunks endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/upload", response_model=GenericResponse[DocumentUploadData])
    async def upload_to_input_dir(
        collection_id: str,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
    ) -> GenericResponse[DocumentUploadData]:
        try:
            # Sanitize filename to prevent Path Traversal attacks
            doc_manager = DocumentManager(
                input_dir=str(get_default_storage_dir() / "inputs"),
                workspace=collection_id,
            )

            rag = await lightrag_manager.create_lightrag_instance(collection_id)

            safe_filename = sanitize_filename(file.filename, doc_manager.input_dir)

            if not doc_manager.is_supported_file(safe_filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Supported types: {doc_manager.supported_extensions}",
                )

            file_path = doc_manager.input_dir / safe_filename
            # Check if file already exists
            if file_path.exists():
                data = DocumentUploadData(
                    filename=safe_filename,
                    upload_status="duplicated",
                    message=f"File '{safe_filename}' already exists in the input directory.",
                    track_id="",
                    processing_started=False,
                    timestamp=datetime.now(),
                )
                return GenericResponse(
                    status="success",
                    message="File duplicate check completed",
                    data=data,
                )

            # Get file size
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Seek back to beginning

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            track_id = generate_track_id("upload")

            # Add to background tasks and get track_id
            background_tasks.add_task(pipeline_index_file, rag, file_path, track_id)

            data = DocumentUploadData(
                filename=safe_filename,
                file_size=file_size,
                file_type=(
                    safe_filename.split(".")[-1] if "." in safe_filename else None
                ),
                upload_status="success",
                message=f"File '{safe_filename}' uploaded successfully. Processing will continue in background.",
                track_id=track_id,
                processing_started=True,
                timestamp=datetime.now(),
            )

            return GenericResponse(
                status="success", message="File uploaded successfully", data=data
            )

        except Exception as e:
            logger.exception("Error uploading file: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/upload_batch", response_model=GenericResponse[BatchUploadData])
    async def upload_files_batch(
        collection_id: str,
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
    ) -> GenericResponse[BatchUploadData]:
        """批量上传文件到指定collection"""

        if not files:
            raise HTTPException(status_code=400, detail="No files provided for upload")

        # 限制批次大小防止系统过载
        MAX_BATCH_SIZE = 50
        if len(files) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size too large. Maximum {MAX_BATCH_SIZE} files per batch"
            )

        try:
            # 生成统一的批次track_id
            batch_track_id = generate_track_id("batch")

            # 初始化统计
            uploaded_files = []
            successful_count = 0
            failed_count = 0
            duplicate_count = 0

            # 获取RAG实例（只需要一次）
            doc_manager = DocumentManager(
                input_dir=str(get_default_storage_dir() / "inputs"),
                workspace=collection_id
            )
            rag = await lightrag_manager.create_lightrag_instance(collection_id)

            if rag is None:
                raise HTTPException(status_code=500, detail="Failed to create RAG instance")

            # 第一步：处理文件上传，收集成功的文件路径
            successful_file_paths = []

            # 处理每个文件
            for file in files:
                try:
                    # 验证文件名
                    safe_filename = sanitize_filename(file.filename or "", doc_manager.input_dir)

                    # 检查文件类型支持
                    if not doc_manager.is_supported_file(safe_filename):
                        uploaded_files.append(BatchUploadItem(
                            filename=safe_filename,
                            upload_status="failure",
                            message=f"Unsupported file type: {safe_filename.split('.')[-1] if '.' in safe_filename else 'unknown'}"
                        ))
                        failed_count += 1
                        continue

                    file_path = doc_manager.input_dir / safe_filename

                    # 检查文件是否已存在
                    if file_path.exists():
                        uploaded_files.append(BatchUploadItem(
                            filename=safe_filename,
                            upload_status="duplicated",
                            message=f"File '{safe_filename}' already exists"
                        ))
                        duplicate_count += 1
                        continue

                    # 获取文件大小
                    file.file.seek(0, 2)
                    file_size = file.file.tell()
                    file.file.seek(0)

                    # 保存文件
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                    # 添加到成功文件列表，等待批量处理
                    successful_file_paths.append(file_path)

                    uploaded_files.append(BatchUploadItem(
                        filename=safe_filename,
                        file_size=file_size,
                        file_type=safe_filename.split('.')[-1] if '.' in safe_filename else None,
                        upload_status="success",
                        message=f"File '{safe_filename}' uploaded successfully"
                    ))
                    successful_count += 1

                except Exception as file_error:
                    logger.exception("Error processing file %s: %s", file.filename, file_error)
                    uploaded_files.append(BatchUploadItem(
                        filename=file.filename or "unknown",
                        upload_status="failure",
                        message=f"Upload failed: {str(file_error)}"
                    ))
                    failed_count += 1

            # 第二步：如果成功上传了文件，启动批量后台处理
            if successful_file_paths:
                background_tasks.add_task(
                    pipeline_index_files_batch,
                    rag,
                    successful_file_paths,
                    batch_track_id
                )

            # 确定批次状态
            if failed_count == 0:
                batch_status = "success"
                message = f"All {successful_count} files uploaded successfully"
            elif successful_count == 0:
                batch_status = "failure"
                message = f"All {failed_count} files failed to upload"
            else:
                batch_status = "partial_success"
                message = f"{successful_count} succeeded, {failed_count} failed, {duplicate_count} duplicates"

            # 构建响应数据
            data = BatchUploadData(
                batch_track_id=batch_track_id,
                total_files=len(files),
                successful_uploads=successful_count,
                failed_uploads=failed_count,
                duplicate_files=duplicate_count,
                files=uploaded_files,
                batch_status=batch_status,
                message=message,
                processing_started=successful_count > 0,
                timestamp=datetime.now()
            )

            return GenericResponse(
                status="success",
                message=f"Batch upload completed: {message}",
                data=data
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error in batch upload: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/pipeline_status",
        response_model=GenericResponse[PipelineStatusData],
    )
    async def get_pipeline_status(
        collection_id: str,
    ) -> GenericResponse[PipelineStatusData]:
        """
        Get the current status of the document indexing pipeline.

        This endpoint returns information about the current state of the document processing pipeline,
        including the processing status, progress information, and history messages.

        Returns:
            PipelineStatusResponse: A response object containing:
                - autoscanned (bool): Whether auto-scan has started
                - busy (bool): Whether the pipeline is currently busy
                - job_name (str): Current job name (e.g., indexing files/indexing texts)
                - job_start (str, optional): Job start time as ISO format string
                - docs (int): Total number of documents to be indexed
                - batchs (int): Number of batches for processing documents
                - cur_batch (int): Current processing batch
                - request_pending (bool): Flag for pending request for processing
                - latest_message (str): Latest message from pipeline processing
                - history_messages (List[str], optional): List of history messages (limited to latest 1000 entries,
                  with truncation message if more than 1000 messages exist)

        Raises:
            HTTPException: If an error occurs while retrieving pipeline status (500)
        """
        try:
            from lightrag.kg.shared_storage import (
                get_namespace_data,
                get_all_update_flags_status,
            )

            await lightrag_manager.get_rag_instance(collection_id)

            pipeline_status = await get_namespace_data("pipeline_status")

            # Get update flags status for all namespaces
            update_status = await get_all_update_flags_status()

            # Convert MutableBoolean objects to regular boolean values
            processed_update_status = {}
            for namespace, flags in update_status.items():
                processed_flags = []
                for flag in flags:
                    # Handle both multiprocess and single process cases
                    if hasattr(flag, "value"):
                        processed_flags.append(bool(flag.value))
                    else:
                        processed_flags.append(bool(flag))
                processed_update_status[namespace] = processed_flags

            # Convert to regular dict if it's a Manager.dict
            status_dict = dict(pipeline_status)

            # Add processed update_status to the status dictionary
            status_dict["update_status"] = processed_update_status

            # Convert history_messages to a regular list if it's a Manager.list
            # and limit to latest 1000 entries with truncation message if needed
            if "history_messages" in status_dict:
                history_list = list(status_dict["history_messages"])
                total_count = len(history_list)

                if total_count > 1000:
                    # Calculate truncated message count
                    truncated_count = total_count - 1000

                    # Take only the latest 1000 messages
                    latest_messages = history_list[-1000:]

                    # Add truncation message at the beginning
                    truncation_message = (
                        f"[Truncated history messages: {truncated_count}/{total_count}]"
                    )
                    status_dict["history_messages"] = [
                        truncation_message
                    ] + latest_messages
                else:
                    # No truncation needed, return all messages
                    status_dict["history_messages"] = history_list

            # Ensure job_start is properly formatted as a string with timezone information
            if "job_start" in status_dict and status_dict["job_start"]:
                # Use format_datetime to ensure consistent formatting
                status_dict["job_start"] = format_datetime(status_dict["job_start"])

            data = PipelineStatusData(
                autoscanned=status_dict.get("autoscanned", False),
                busy=status_dict.get("busy", False),
                job_name=status_dict.get("job_name", "Default Job"),
                job_start=status_dict.get("job_start"),
                docs=status_dict.get("docs", 0),
                batchs=status_dict.get("batchs", 0),
                cur_batch=status_dict.get("cur_batch", 0),
                request_pending=status_dict.get("request_pending", False),
                latest_message=status_dict.get("latest_message", ""),
                history_messages=status_dict.get("history_messages"),
                update_status=status_dict.get("update_status"),
                timestamp=datetime.now(),
            )

            return GenericResponse(
                status="success",
                message="Pipeline status retrieved successfully",
                data=data,
            )
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/track_status",
        response_model=GenericResponse[TrackStatusData],
    )
    async def get_track_status(
        collection_id: str, track_id: str
    ) -> GenericResponse[TrackStatusData]:
        """
        Get the processing status of documents by tracking ID.

        This endpoint retrieves all documents associated with a specific tracking ID,
        allowing users to monitor the processing progress of their uploaded files or inserted texts.

        Args:
            track_id (str): The tracking ID returned from upload, text, or texts endpoints

        Returns:
            TrackStatusResponse: A response object containing:
                - track_id: The tracking ID
                - documents: List of documents associated with this track_id
                - total_count: Total number of documents for this track_id

        Raises:
            HTTPException: If track_id is invalid (400) or an error occurs (500).
        """
        try:
            # Validate track_id
            if not track_id or not track_id.strip():
                raise HTTPException(status_code=400, detail="Track ID cannot be empty")

            track_id = track_id.strip()

            rag = await lightrag_manager.get_rag_instance(collection_id)

            # Get documents by track_id
            docs_by_track_id = await rag.aget_docs_by_track_id(track_id)

            # Convert to response format
            documents = []
            status_summary = {}

            for doc_id, doc_status in docs_by_track_id.items():
                documents.append(
                    DocumentItem(
                        id=doc_id,
                        collection_id=collection_id,
                        content_summary=doc_status.content_summary,
                        content_length=doc_status.content_length,
                        status=doc_status.status,
                        created_at=format_datetime(doc_status.created_at),
                        updated_at=format_datetime(doc_status.updated_at),
                        track_id=doc_status.track_id,
                        chunks_count=doc_status.chunks_count,
                        error_msg=doc_status.error_msg,
                        metadata=doc_status.metadata,
                        file_path=doc_status.file_path,
                    )
                )

                # Build status summary
                # Handle both DocStatus enum and string cases for robust deserialization
                status_key = str(doc_status.status)
                status_summary[status_key] = status_summary.get(status_key, 0) + 1

            data = TrackStatusData(
                track_id=track_id,
                documents=documents,
                total_count=len(documents),
                status_summary=status_summary,
                timestamp=datetime.now(),
            )

            return GenericResponse(
                status="success",
                message=f"Retrieved status for {len(documents)} documents with track_id '{track_id}'",
                data=data,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting track status for {track_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete(
        "/delete_document",
        response_model=GenericResponse[DocumentDeletionData],
    )
    async def delete_document(
        collection_id: str,
        delete_request: DeleteDocRequest,
        background_tasks: BackgroundTasks,
    ) -> GenericResponse[DocumentDeletionData]:
        """
        Delete documents and all their associated data by their IDs using background processing.

        Deletes specific documents and all their associated data, including their status,
        text chunks, vector embeddings, and any related graph data.
        The deletion process runs in the background to avoid blocking the client connection.
        It is disabled when llm cache for entity extraction is disabled.

        This operation is irreversible and will interact with the pipeline status.

        Args:
            delete_request (DeleteDocRequest): The request containing the document IDs and delete_file options.
            background_tasks: FastAPI BackgroundTasks for async processing

        Returns:
            DeleteDocByIdResponse: The result of the deletion operation.
                - status="deletion_started": The document deletion has been initiated in the background.
                - status="busy": The pipeline is busy with another operation.
                - status="not_allowed": Operation not allowed when LLM cache for entity extraction is disabled.

        Raises:
            HTTPException:
              - 500: If an unexpected internal error occurs during initialization.
        """
        doc_ids = delete_request.doc_ids
        rag = await lightrag_manager.get_rag_instance(collection_id)
        doc_manager = DocumentManager(
            input_dir=str(get_default_storage_dir() / "inputs"), workspace=collection_id
        )

        # The rag object is initialized from the server startup args,
        # so we can access its properties here.
        if not rag.enable_llm_cache_for_entity_extract:
            data = DocumentDeletionData(
                operation_id=f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="not_allowed",
                message="Operation not allowed when LLM cache for entity extraction is disabled.",
                affected_documents=doc_ids,
                files_to_delete=delete_request.delete_file,
                timestamp=datetime.now(),
            )
            return GenericResponse(
                status="success",
                message="Document deletion permission check completed",
                data=data,
            )

        try:
            from lightrag.kg.shared_storage import get_namespace_data

            pipeline_status = await get_namespace_data("pipeline_status")

            # Check if pipeline is busy
            if pipeline_status.get("busy", False):
                data = DocumentDeletionData(
                    operation_id=f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status="busy",
                    message="Cannot delete documents while pipeline is busy",
                    affected_documents=doc_ids,
                    files_to_delete=delete_request.delete_file,
                    timestamp=datetime.now(),
                )
                return GenericResponse(
                    status="success", message="Pipeline busy check completed", data=data
                )

            # Add deletion task to background tasks
            background_tasks.add_task(
                background_delete_documents,
                rag,
                doc_manager,
                doc_ids,
                delete_request.delete_file,
            )

            data = DocumentDeletionData(
                operation_id=f"del_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="deletion_started",
                message=f"Document deletion for {len(doc_ids)} documents has been initiated. Processing will continue in background.",
                affected_documents=doc_ids,
                files_to_delete=delete_request.delete_file,
                timestamp=datetime.now(),
            )

            return GenericResponse(
                status="success", message="Document deletion initiated", data=data
            )

        except Exception as e:
            error_msg = f"Error initiating document deletion for {delete_request.doc_ids}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=error_msg)

    @router.post("/retry", response_model=GenericResponse[RetryDocumentData])
    async def retry_documents(
        collection_id: str,
        background_tasks: BackgroundTasks,
    ) -> GenericResponse[RetryDocumentData]:
        """
        Retry processing for failed or stuck documents.

        This endpoint triggers the document processing pipeline, which automatically
        picks up documents with 'failed', 'processing' (stuck), and 'pending' status.
        Useful when the server crashed during processing or tasks failed.
        """
        try:
            rag = await lightrag_manager.get_rag_instance(collection_id)
            if rag is None:
                raise HTTPException(
                    status_code=404, detail=f"Collection '{collection_id}' not found"
                )

            from lightrag.kg.shared_storage import get_namespace_data

            pipeline_status = await get_namespace_data("pipeline_status")

            if pipeline_status.get("busy", False):
                data = RetryDocumentData(
                    status="busy",
                    message="Pipeline is currently busy. Please try again later.",
                    timestamp=datetime.now(),
                )
                return GenericResponse(
                    status="success", message="Pipeline busy check completed", data=data
                )

            # Trigger the pipeline processing in background
            # apipeline_process_enqueue_documents automatically picks up FAILED and PROCESSING docs
            background_tasks.add_task(rag.apipeline_process_enqueue_documents)

            data = RetryDocumentData(
                status="started",
                message="Retry process initiated for pending/failed/stuck documents.",
                timestamp=datetime.now(),
            )

            return GenericResponse(
                status="success", message="Retry initiated", data=data
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error retrying documents: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    return router
