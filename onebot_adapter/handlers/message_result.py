from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any, Dict, List


class UserOperationType(Enum):
    """用户相关操作类型"""
    NONE = auto()  # 无特殊操作
    AT = auto()  # @用户
    MUTE = auto()  # 禁言用户
    RECALL = auto()  # 撤回消息
    KICK = auto()  # 踢出群聊


@dataclass
class MessageResult:
    """消息操作结果类"""
    success: bool = True
    message_id: Optional[int] = None  # 发送的消息ID
    recalled_id: Optional[int] = None  # 撤回的消息ID
    target_user_id: Optional[int] = None  # 目标用户ID
    operation_type: UserOperationType = UserOperationType.NONE  # 操作类型
    operation_duration: Optional[int] = None  # 操作时长(禁言等)
    error: Optional[str] = None  # 错误信息
    raw_results: List[Dict[str, Any]] = None  # 原始返回结果列表

    def __post_init__(self):
        if self.raw_results is None:
            self.raw_results = []
