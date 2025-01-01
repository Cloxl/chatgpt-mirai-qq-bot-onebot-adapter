from typing import Any

from framework.im.message import TextMessage


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
