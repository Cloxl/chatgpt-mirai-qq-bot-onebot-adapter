from enum import Enum, auto
from dataclasses import dataclass


class OperationType(Enum):
    """操作类型"""
    MUTE = auto()      # 禁言
    UNMUTE = auto()    # 解除禁言
    KICK = auto()      # 踢出
    RECALL = auto()    # 撤回
    AT = auto()        # @用户


@dataclass
class OperationEvent:
    """操作事件"""
    operation_type: OperationType
    group_id: str
    user_id: str
    duration: int = 0      # 持续时间(禁言用)
    message_id: str = ""   # 消息ID(撤回用)
    reason: str = ""       # 原因(踢出用)
