from framework.events.event import Event
from framework.im.adapter import IMAdapter
from ..events.operation_event import OperationEvent, OperationType


class AdminWorkflow:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        # 注册事件处理器
        event_bus.register(OperationEvent, self.handle_operation)

    @Event
    async def handle_operation(self, event: OperationEvent, adapter: IMAdapter):
        """处理管理操作事件"""
        match event.operation_type:
            case OperationType.MUTE:
                await adapter.mute_user(
                    event.group_id,
                    event.user_id,
                    event.duration
                )
            case OperationType.UNMUTE:
                await adapter.unmute_user(
                    event.group_id,
                    event.user_id
                )
            case OperationType.KICK:
                await adapter.kick_user(
                    event.group_id,
                    event.user_id
                )
            case OperationType.RECALL:
                await adapter.recall_message(event.message_id)
            case OperationType.PIN:
                await adapter.pin_message(event.message_id) 