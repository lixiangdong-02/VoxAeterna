"""任务管理服务 —— TTS 合成任务的状态机"""

import uuid
import threading
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.schemas.requests import TaskState, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class Task:
    task_id: str
    state: TaskState = TaskState.PENDING
    text: str = ""
    audio_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    error_message: Optional[str] = None
    prompt_text: str = ""
    speed_factor: float = 1.0
    ref_audio_path: str = ""
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    _cancel_event: threading.Event = field(default_factory=threading.Event)

    @property
    def progress(self) -> float:
        if self.state == TaskState.COMPLETED:
            return 1.0
        if self.state == TaskState.RUNNING:
            return 0.5  # 简化：运行中固定 50%
        return 0.0

    def cancel(self):
        self._cancel_event.set()
        self.state = TaskState.CANCELLED


class TaskService:
    MAX_HISTORY = 5

    def __init__(self):
        self._active_task: Optional[Task] = None
        self._history: List[Task] = []
        self._lock = threading.Lock()

    def create_task(self, text: str, user_id: int = 0, prompt_text: str = "",
                     speed_factor: float = 1.0, ref_audio_path: str = "") -> Task:
        task = Task(task_id=uuid.uuid4().hex[:12], text=text,
                    prompt_text=prompt_text, speed_factor=speed_factor,
                    ref_audio_path=ref_audio_path)
        with self._lock:
            self._active_task = task
        return task

    def start_task(self, task: Task):
        with self._lock:
            task.state = TaskState.RUNNING

    def complete_task(self, task: Task, audio_path: str, duration: float, sr: int, user_id: int = 0):
        with self._lock:
            task.state = TaskState.COMPLETED
            task.audio_path = audio_path
            task.duration_seconds = round(duration, 2)
            task.sample_rate = sr
            self._active_task = None
            self._add_to_history(task)
        # 持久化到 SQLite
        if user_id > 0:
            from app.services.history_store import save_task
            save_task(task, user_id)

    def fail_task(self, task: Task, error: str, user_id: int = 0):
        with self._lock:
            task.state = TaskState.FAILED
            task.error_message = error
            self._active_task = None
            self._add_to_history(task)
        if user_id > 0:
            from app.services.history_store import save_task
            save_task(task, user_id)

    def cancel_task(self, task: Task, user_id: int = 0):
        """取消指定任务（会触发 cancel_event 并加入历史记录）"""
        with self._lock:
            task.cancel()
            self._active_task = None
            self._add_to_history(task)
        if user_id > 0:
            from app.services.history_store import save_task
            save_task(task, user_id)

    def cancel_task_by_id(self, task_id: str, user_id: int = 0):
        """根据 task_id 取消任务（不存在则不创建僵尸记录）"""
        with self._lock:
            if self._active_task and self._active_task.task_id == task_id:
                task = self._active_task
                task.cancel()
                self._active_task = None
                self._add_to_history(task)
                # 持久化
                if user_id > 0:
                    from app.services.history_store import save_task
                    save_task(task, user_id)
            else:
                logger.warning(f"任务 {task_id} 不在活跃状态，无法取消")

    def _add_to_history(self, task: Task):
        self._history.insert(0, task)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[: self.MAX_HISTORY]

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        # 检查活跃任务
        if self._active_task and self._active_task.task_id == task_id:
            return self._to_status(self._active_task)
        # 检查历史
        for t in self._history:
            if t.task_id == task_id:
                return self._to_status(t)
        return None

    def list_history(self) -> List[TaskStatus]:
        return [self._to_status(t) for t in self._history]

    @staticmethod
    def _to_status(t: Task) -> TaskStatus:
        return TaskStatus(
            task_id=t.task_id,
            state=t.state,
            progress=t.progress,
            text=t.text[:200] if t.text else None,
            audio_path=t.audio_path,
            duration_seconds=t.duration_seconds,
            sample_rate=t.sample_rate,
            error_message=t.error_message,
            prompt_text=t.prompt_text,
            speed_factor=t.speed_factor,
            ref_audio_path=t.ref_audio_path,
            created_at=t.created_at,
        )
