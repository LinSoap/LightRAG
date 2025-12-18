from datetime import datetime
from pathlib import Path
import traceback
from typing import List
from lightrag.api.utils.file import pipeline_enqueue_file
from lightrag.document_manager import DocumentManager
from lightrag.lightrag import LightRAG
from lightrag.utils import logger


async def background_delete_documents(
    rag: LightRAG,
    doc_manager: DocumentManager,
    doc_ids: List[str],
    delete_file: bool = False,
):
    """Background task to delete multiple documents"""
    from lightrag.kg.shared_storage import (
        get_namespace_data,
        get_pipeline_status_lock,
    )

    pipeline_status = await get_namespace_data("pipeline_status")
    pipeline_status_lock = get_pipeline_status_lock()

    total_docs = len(doc_ids)
    successful_deletions = []
    failed_deletions = []

    # Double-check pipeline status before proceeding
    async with pipeline_status_lock:
        if pipeline_status.get("busy", False):
            logger.warning("Error: Unexpected pipeline busy state, aborting deletion.")
            return  # Abort deletion operation

        # Set pipeline status to busy for deletion
        pipeline_status.update(
            {
                "busy": True,
                "job_name": f"Deleting {total_docs} Documents",
                "job_start": datetime.now().isoformat(),
                "docs": total_docs,
                "batchs": total_docs,
                "cur_batch": 0,
                "latest_message": "Starting document deletion process",
            }
        )
        # Use slice assignment to clear the list in place
        pipeline_status["history_messages"][:] = ["Starting document deletion process"]

    try:
        # Loop through each document ID and delete them one by one
        for i, doc_id in enumerate(doc_ids, 1):
            async with pipeline_status_lock:
                start_msg = f"Deleting document {i}/{total_docs}: {doc_id}"
                logger.info(start_msg)
                pipeline_status["cur_batch"] = i
                pipeline_status["latest_message"] = start_msg
                pipeline_status["history_messages"].append(start_msg)

            file_path = "#"
            try:
                result = await rag.adelete_by_doc_id(doc_id)
                file_path = (
                    getattr(result, "file_path", "-") if "result" in locals() else "-"
                )
                if result.status == "success":
                    successful_deletions.append(doc_id)
                    success_msg = (
                        f"Document deleted {i}/{total_docs}: {doc_id}[{file_path}]"
                    )
                    logger.info(success_msg)
                    async with pipeline_status_lock:
                        pipeline_status["history_messages"].append(success_msg)

                    # Handle file deletion if requested and file_path is available
                    if (
                        delete_file
                        and result.file_path
                        and result.file_path != "unknown_source"
                    ):
                        try:
                            deleted_files = []
                            # check and delete files from input_dir directory
                            file_path = doc_manager.input_dir / result.file_path
                            if file_path.exists():
                                try:
                                    file_path.unlink()
                                    deleted_files.append(file_path.name)
                                    file_delete_msg = f"Successfully deleted input_dir file: {result.file_path}"
                                    logger.info(file_delete_msg)
                                    async with pipeline_status_lock:
                                        pipeline_status["latest_message"] = (
                                            file_delete_msg
                                        )
                                        pipeline_status["history_messages"].append(
                                            file_delete_msg
                                        )
                                except Exception as file_error:
                                    file_error_msg = f"Failed to delete input_dir file {result.file_path}: {str(file_error)}"
                                    logger.debug(file_error_msg)
                                    async with pipeline_status_lock:
                                        pipeline_status["latest_message"] = (
                                            file_error_msg
                                        )
                                        pipeline_status["history_messages"].append(
                                            file_error_msg
                                        )

                            # Also check and delete files from __enqueued__ directory
                            enqueued_dir = doc_manager.input_dir / "__enqueued__"
                            if enqueued_dir.exists():
                                # Look for files with the same name or similar names (with numeric suffixes)
                                base_name = Path(result.file_path).stem
                                extension = Path(result.file_path).suffix

                                # Search for exact match and files with numeric suffixes
                                for enqueued_file in enqueued_dir.glob(
                                    f"{base_name}*{extension}"
                                ):
                                    try:
                                        enqueued_file.unlink()
                                        deleted_files.append(enqueued_file.name)
                                        logger.info(
                                            f"Successfully deleted enqueued file: {enqueued_file.name}"
                                        )
                                    except Exception as enqueued_error:
                                        file_error_msg = f"Failed to delete enqueued file {enqueued_file.name}: {str(enqueued_error)}"
                                        logger.debug(file_error_msg)
                                        async with pipeline_status_lock:
                                            pipeline_status["latest_message"] = (
                                                file_error_msg
                                            )
                                            pipeline_status["history_messages"].append(
                                                file_error_msg
                                            )

                            if deleted_files == []:
                                file_error_msg = f"File deletion skipped, missing file: {result.file_path}"
                                logger.warning(file_error_msg)
                                async with pipeline_status_lock:
                                    pipeline_status["latest_message"] = file_error_msg
                                    pipeline_status["history_messages"].append(
                                        file_error_msg
                                    )

                        except Exception as file_error:
                            file_error_msg = f"Failed to delete file {result.file_path}: {str(file_error)}"
                            logger.error(file_error_msg)
                            async with pipeline_status_lock:
                                pipeline_status["latest_message"] = file_error_msg
                                pipeline_status["history_messages"].append(
                                    file_error_msg
                                )
                    elif delete_file:
                        no_file_msg = (
                            f"File deletion skipped, missing file path: {doc_id}"
                        )
                        logger.warning(no_file_msg)
                        async with pipeline_status_lock:
                            pipeline_status["latest_message"] = no_file_msg
                            pipeline_status["history_messages"].append(no_file_msg)
                else:
                    failed_deletions.append(doc_id)
                    error_msg = f"Failed to delete {i}/{total_docs}: {doc_id}[{file_path}] - {result.message}"
                    logger.error(error_msg)
                    async with pipeline_status_lock:
                        pipeline_status["latest_message"] = error_msg
                        pipeline_status["history_messages"].append(error_msg)

            except Exception as e:
                failed_deletions.append(doc_id)
                error_msg = f"Error deleting document {i}/{total_docs}: {doc_id}[{file_path}] - {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                async with pipeline_status_lock:
                    pipeline_status["latest_message"] = error_msg
                    pipeline_status["history_messages"].append(error_msg)

    except Exception as e:
        error_msg = f"Critical error during batch deletion: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        async with pipeline_status_lock:
            pipeline_status["history_messages"].append(error_msg)
    finally:
        # Final summary and check for pending requests
        async with pipeline_status_lock:
            pipeline_status["busy"] = False
            completion_msg = f"Deletion completed: {len(successful_deletions)} successful, {len(failed_deletions)} failed"
            pipeline_status["latest_message"] = completion_msg
            pipeline_status["history_messages"].append(completion_msg)

            # Check if there are pending document indexing requests
            has_pending_request = pipeline_status.get("request_pending", False)

        # If there are pending requests, start document processing pipeline
        if has_pending_request:
            try:
                logger.info(
                    "Processing pending document indexing requests after deletion"
                )
                await rag.apipeline_process_enqueue_documents()
            except Exception as e:
                logger.error(f"Error processing pending documents after deletion: {e}")


async def pipeline_index_file(rag: LightRAG, file_path: Path, track_id: str = None):
    """Index a file with track_id

    Args:
        rag: LightRAG instance
        file_path: Path to the saved file
        track_id: Optional tracking ID
    """
    try:
        success, returned_track_id = await pipeline_enqueue_file(
            rag, file_path, track_id
        )
        if success:
            await rag.apipeline_process_enqueue_documents()

    except Exception as e:
        logger.exception("Error indexing file %s: %s", file_path.name, e)


async def pipeline_index_files_batch(rag: LightRAG, file_paths: List[Path], batch_track_id: str):
    """批量索引文件，避免pipeline竞争

    Args:
        rag: LightRAG instance
        file_paths: List of file paths to index
        batch_track_id: Batch tracking ID
    """
    from lightrag.kg.shared_storage import get_namespace_data, get_pipeline_status_lock

    pipeline_status = await get_namespace_data("pipeline_status")
    pipeline_status_lock = get_pipeline_status_lock()

    successful_files = []
    failed_files = []

    try:
        # 第一步：将所有文件加入队列
        for file_path in file_paths:
            try:
                success, _ = await pipeline_enqueue_file(rag, file_path, batch_track_id)
                if success:
                    successful_files.append(file_path)
                    logger.info(f"Successfully enqueued file: {file_path.name}")
                else:
                    failed_files.append(file_path)
                    logger.error(f"Failed to enqueue file: {file_path.name}")
            except Exception as e:
                failed_files.append(file_path)
                logger.exception("Error enqueuing file %s: %s", file_path.name, e)

        # 第二步：一次性启动pipeline处理
        if successful_files:
            try:
                # Let apipeline_process_enqueue_documents handle status and locking
                await rag.apipeline_process_enqueue_documents()
                logger.info(f"Batch processing initiated for {len(successful_files)} files")

            except Exception as e:
                logger.exception("Error during batch pipeline processing: %s", e)

        logger.info(f"Batch indexing completed: {len(successful_files)} successful, {len(failed_files)} failed")

    except Exception as e:
        logger.exception("Error during batch file indexing: %s", e)
