from typing import Any

from framework.im.message import TextMessage, IMMessage
from aiocqhttp import Event

from plugins.onebot_adapter.onebot_adapter.message.media import create_message_element


def degrade_to_text(element: Any) -> TextMessage:
    """将消息元素降级为文本"""
    if isinstance(element, TextMessage):
        return element

    # 根据元素类型进行降级
    if hasattr(element, 'nickname') and hasattr(element, 'user_id'):  # At
        return TextMessage(f"@{element.nickname or element.user_id}")

    elif hasattr(element, 'message_id'):  # Reply
        return TextMessage(f"[回复:{element.message_id}]")

    elif hasattr(element, 'file_name'):  # File
        return TextMessage(f"[文件:{element.file_name}]")

    elif hasattr(element, 'face_id'):  # Face
        return TextMessage(f"[表情:{element.face_id}]")

    elif hasattr(element, 'data') and isinstance(element.data, str):  # Json
        return TextMessage(f"[JSON消息:{element.data}]")

    return TextMessage("[不支持的消息类型]")


class MessageConverter:
    """消息转换器，用于OneBot消息和IMMessage之间的转换"""
    
    def to_internal(self, event: Event) -> IMMessage:
        """将 OneBot 消息转换为统一消息格式"""
        segments = []
        
        # 构造 sender
        if event.get('group_id'):
            sender = f"group_{event.get('group_id')}"
        else:
            sender = f"private_{event.get('user_id')}"
        
        for msg in event['message']:
            element = create_message_element(msg['type'], msg['data'])
            if element:
                segments.append(element)
        
        return IMMessage(
            sender=sender,
            message_elements=segments,
            raw_message={}
        )
