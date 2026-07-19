"""任务管理服务 —— TTS 合成任务的状态机"""

import uuid
import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.schemas.requests import TaskState, TaskStatus


@dataclass
class Task:
    task_id: str
    state: TaskState = TaskState.PENDING
    text: str = ""
    audio_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    error_message: Optional[str] = None
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

    def create_task(self, text: str) -> Task:
        task = Task(task_id=uuid.uuid4().hex[:12], text=text)
        with self._lock:
            self._active_task = task
        return task

    def start_task(self, task: Task):
        with self._lock:
            task.state = TaskState.RUNNING

    def complete_task(self, task: Task, audio_path: str, duration: float, sr: int):
        with self._lock:
            task.state = TaskState.COMPLETED
            task.audio_path = audio_path
            task.duration_seconds = round(duration, 2)
            task.sample_rate = sr
            self._active_task = None
            self._add_to_history(task)

    def fail_task(self, task: Task, error: str):
        with self._lock:
            task.state = TaskState.FAILED
            task.error_message = error
            self._active_task = None
            self._add_to_history(task)

    def cancel_task(self, task: Task):
        with self._lock:
            task.cancel()
            self._active_task = None
            self._add_to_history(task)

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
            created_at=t.created_at,
        )
