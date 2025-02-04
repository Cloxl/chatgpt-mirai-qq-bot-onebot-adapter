from typing import Optional
from framework.im.message import (
    ImageMessage, MediaMessage, MessageElement, TextMessage, VoiceMessage,
    AtElement, FaceElement, FileElement, JsonElement, ReplyElement, VideoElement
)
from framework.logger import get_logger

logger = get_logger("OneBot")

def create_message_element(msg_type: str, data: dict) -> Optional[MessageElement | MediaMessage]:
    """
    根据OneBot消息类型创建对应的消息元素
    
    Args:
        msg_type: OneBot消息类型
        data: 消息数据字典
    
    Returns:
        MessageElement实例 MediaMessage实例 或 None
    """
    # 获取文件URL或路径
    file = data.get('url') or data.get('path')

    # 消息类型到创建函数的映射
    element_creators = {
        'text': lambda: TextMessage(data['text']),
        'at': lambda: AtElement(data['qq']),
        'reply': lambda: ReplyElement(data['id']),
        'file': lambda: FileElement(data['file']),
        'json': lambda: JsonElement(data['data']),
        'face': lambda: FaceElement(data['id']),
        'image': lambda: ImageMessage(url=file) if file else None,
        'record': lambda: VoiceMessage(url=file) if file else None,
        'video': lambda: VideoElement(file) if file else None
    }

    try:
        if msg_type in element_creators:
            return element_creators[msg_type]()
    except Exception as e:
        logger.error(f"Failed to create message element for type {msg_type}: {e}")
    
    return None 