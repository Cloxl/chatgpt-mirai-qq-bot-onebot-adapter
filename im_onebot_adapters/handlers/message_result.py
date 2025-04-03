from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from ..events.operation_event import OperationType

@dataclass
class MessageResult:
    """消息操作结果类"""
    success: bool = True
    message_id: Optional[int] = None
    recalled_id: Optional[int] = None
    target_user_id: Optional[int] = None
    operation_type: OperationType = OperationType.MUTE
    operation_duration: Optional[int] = None
    error: Optional[str] = None
    raw_results: List[Dict[str, Any]] = field(default_factory=list)