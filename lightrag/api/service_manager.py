"""
服务管理器 - 负责进程生命周期管理
"""
import os
import signal
import atexit
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import psutil


class ServiceState(Enum):
    """服务状态枚举"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    state: ServiceState = ServiceState.INITIALIZING
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    pid: Optional[int] = None
    error_message: Optional[str] = None
    active_connections: int = 0
    active_tasks: List[str] = field(default_factory=list)


class ServiceManager:
    """服务管理器 - 负责优雅关闭和资源管理"""

    def __init__(self):
        self.state = ServiceState.INITIALIZING
        self.start_time = datetime.now()
        self.stop_time = None
        self.shutdown_requested = False
        self.shutdown_callbacks: List[Callable] = []
        self.cleanup_lock = threading.RLock()
        self.processes: List[subprocess.Popen] = []
        self.threads: List[threading.Thread] = []
        self.logger = logging.getLogger(__name__)
        self.error_message = None

        # 服务统计信息
        self.total_requests = 0
        self.active_connections = 0
        self.active_tasks: Dict[str, datetime] = {}

        # 设置信号处理器
        self._setup_signal_handlers()

        # 注册清理函数
        atexit.register(self._cleanup_at_exit)

        self.logger.info("ServiceManager initialized")

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        if os.name == 'nt':  # Windows
            # Windows不支持SIGINT和SIGTERM
            return

        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self.logger.info("Signal handlers set up successfully")
        except ValueError as e:
            self.logger.warning(f"Failed to set up signal handlers: {e}")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.initiate_shutdown(f"Signal {signum} received")

    def _cleanup_at_exit(self):
        """程序退出时的清理函数"""
        if self.state != ServiceState.STOPPED and self.state != ServiceState.ERROR:
            self.logger.warning("Service did not shut down gracefully, cleaning up...")
            self._emergency_cleanup()

    def initiate_shutdown(self, reason: str = "Shutdown requested"):
        """发起优雅关闭"""
        if self.shutdown_requested:
            self.logger.warning("Shutdown already in progress")
            return

        self.shutdown_requested = True
        self.state = ServiceState.STOPPING
        self.logger.info(f"Initiating graceful shutdown: {reason}")

        # 在新线程中执行关闭，避免阻塞信号处理
        shutdown_thread = threading.Thread(target=self._graceful_shutdown, args=(reason,))
        shutdown_thread.daemon = True
        shutdown_thread.start()

    def _graceful_shutdown(self, reason: str):
        """执行优雅关闭"""
        try:
            self.logger.info("Starting graceful shutdown...")

            # 1. 停止接受新连接
            self.state = ServiceState.STOPPING
            self.logger.info("Service state set to STOPPING")

            # 2. 等待活跃任务完成
            self._wait_for_active_tasks()

            # 3. 调用关闭回调
            self._call_shutdown_callbacks()

            # 4. 停止子进程
            self._stop_subprocesses()

            # 5. 停止线程
            self._stop_threads()

            # 6. 清理资源
            self._cleanup_resources()

            # 7. 更新状态
            self.state = ServiceState.STOPPED
            self.stop_time = datetime.now()

            # 记录关闭统计
            duration = (self.stop_time - self.start_time).total_seconds()
            self.logger.info(f"Graceful shutdown completed in {duration:.2f} seconds")
            self.logger.info(f"Total requests handled: {self.total_requests}")

        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
            self.state = ServiceState.ERROR
            self._emergency_cleanup()

    def _wait_for_active_tasks(self, timeout: int = 30):
        """等待活跃任务完成"""
        if not self.active_tasks:
            self.logger.info("No active tasks to wait for")
            return

        self.logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")

        start_time = time.time()
        while self.active_tasks and time.time() - start_time < timeout:
            # 清理已完成的任务
            current_time = datetime.now()
            completed_tasks = [
                task_id for task_id, start_time in self.active_tasks.items()
                if (current_time - start_time).total_seconds() > 300  # 5分钟超时
            ]

            for task_id in completed_tasks:
                self.active_tasks.pop(task_id, None)
                self.logger.warning(f"Task {task_id} timed out, removing from active tasks")

            if self.active_tasks:
                time.sleep(0.5)

        if self.active_tasks:
            self.logger.warning(f"Timeout reached, {len(self.active_tasks)} tasks still active")
        else:
            self.logger.info("All active tasks completed")

    def _call_shutdown_callbacks(self):
        """调用关闭回调函数"""
        if not self.shutdown_callbacks:
            return

        self.logger.info(f"Calling {len(self.shutdown_callbacks)} shutdown callbacks...")

        for callback in self.shutdown_callbacks:
            try:
                callback()
                self.logger.debug(f"Shutdown callback {callback.__name__} executed successfully")
            except Exception as e:
                self.logger.error(f"Error in shutdown callback {callback.__name__}: {e}")

    def _stop_subprocesses(self, timeout: int = 10):
        """停止子进程"""
        if not self.processes:
            return

        self.logger.info(f"Stopping {len(self.processes)} subprocesses...")

        for process in self.processes:
            try:
                if process.poll() is None:  # 进程仍在运行
                    process.terminate()  # 发送SIGTERM
                    try:
                        process.wait(timeout=5)
                        self.logger.debug(f"Subprocess {process.pid} terminated gracefully")
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Subprocess {process.pid} did not terminate, killing...")
                        process.kill()  # 发送SIGKILL
                        process.wait()
                        self.logger.debug(f"Subprocess {process.pid} killed")
            except Exception as e:
                self.logger.error(f"Error stopping subprocess {getattr(process, 'pid', 'unknown')}: {e}")

        self.processes.clear()

    def _stop_threads(self, timeout: int = 5):
        """停止线程"""
        if not self.threads:
            return

        self.logger.info(f"Stopping {len(self.threads)} threads...")

        for thread in self.threads:
            if thread.is_alive() and thread != threading.current_thread():
                # 注意：Python中没有安全的方式强制停止线程
                # 这里只是记录日志，线程应该通过事件等方式自行退出
                self.logger.debug(f"Thread {thread.name} is still running (should exit gracefully)")

        self.threads.clear()

    def _cleanup_resources(self):
        """清理资源"""
        try:
            # 强制垃圾回收
            import gc
            gc.collect()

            # 记录内存使用情况
            process = psutil.Process()
            memory_info = process.memory_info()
            self.logger.info(f"Memory usage before cleanup: {memory_info.rss / 1024 / 1024:.2f} MB")

        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")

    def _emergency_cleanup(self):
        """紧急清理（在异常情况下）"""
        self.logger.warning("Performing emergency cleanup...")

        try:
            # 强制停止所有子进程
            for process in self.processes:
                try:
                    if process.poll() is None:
                        process.kill()
                except:
                    pass

            # 清空列表
            self.processes.clear()
            self.threads.clear()
            self.active_tasks.clear()

        except Exception as e:
            self.logger.error(f"Error during emergency cleanup: {e}")

    # 公共API方法
    def register_shutdown_callback(self, callback: Callable):
        """注册关闭回调函数"""
        self.shutdown_callbacks.append(callback)
        self.logger.debug(f"Shutdown callback registered: {callback.__name__}")

    def register_subprocess(self, process: subprocess.Popen):
        """注册子进程以便管理"""
        self.processes.append(process)
        self.logger.debug(f"Subprocess registered: {process.pid}")

    def unregister_subprocess(self, process: subprocess.Popen):
        """取消注册子进程"""
        if process in self.processes:
            self.processes.remove(process)
            self.logger.debug(f"Subprocess unregistered: {getattr(process, 'pid', 'unknown')}")

    def register_thread(self, thread: threading.Thread):
        """注册线程以便管理"""
        self.threads.append(thread)
        self.logger.debug(f"Thread registered: {thread.name}")

    def unregister_thread(self, thread: threading.Thread):
        """取消注册线程"""
        if thread in self.threads:
            self.threads.remove(thread)
            self.logger.debug(f"Thread unregistered: {thread.name}")

    def start_task(self, task_id: str):
        """开始一个任务"""
        self.active_tasks[task_id] = datetime.now()
        self.logger.debug(f"Task started: {task_id}")

    def finish_task(self, task_id: str):
        """完成一个任务"""
        self.active_tasks.pop(task_id, None)
        self.logger.debug(f"Task finished: {task_id}")

    def increment_connections(self):
        """增加连接计数"""
        self.active_connections += 1
        self.total_requests += 1

    def decrement_connections(self):
        """减少连接计数"""
        self.active_connections = max(0, self.active_connections - 1)

    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()

            return {
                "state": self.state.value,
                "uptime": (datetime.now() - self.start_time).total_seconds(),
                "pid": os.getpid(),
                "total_requests": self.total_requests,
                "active_connections": self.active_connections,
                "active_tasks": len(self.active_tasks),
                "memory_usage_mb": memory_info.rss / 1024 / 1024,
                "cpu_usage_percent": cpu_percent,
                "start_time": self.start_time.isoformat(),
                "stop_time": self.stop_time.isoformat() if self.stop_time else None,
                "shutdown_requested": self.shutdown_requested,
                "error_message": getattr(self, 'error_message', None)
            }
        except Exception as e:
            self.logger.error(f"Error getting service info: {e}")
            return {"error": str(e)}

    def is_healthy(self) -> bool:
        """检查服务是否健康"""
        return self.state == ServiceState.RUNNING and not self.shutdown_requested

    def set_running(self):
        """将服务状态设置为运行中"""
        self.state = ServiceState.RUNNING
        self.start_time = datetime.now()
        self.logger.info("Service state set to RUNNING")

    def set_error(self, error_message: str):
        """将服务状态设置为错误"""
        self.state = ServiceState.ERROR
        self.error_message = error_message
        self.logger.error(f"Service state set to ERROR: {error_message}")


# 全局服务管理器实例
service_manager = ServiceManager()