from typing import Any, Dict

from framework.im.message import MessageElement


class AtElement(MessageElement):
    """@消息元素"""
    def __init__(self, user_id: str, nickname: str = ""):
        self.user_id = user_id
        self.nickname = nickname

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "at",
            "data": {
                "qq": self.user_id
            }
        }


class ReplyElement(MessageElement):
    """回复消息元素"""
    def __init__(self, message_id: str):
        self.message_id = message_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "reply",
            "data": {
                "id": self.message_id
            }
        }


class FileElement(MessageElement):
    """文件消息元素"""
    def __init__(self, file_name: str):
        self.file_name = file_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "file",
            "data": {
                "file": self.file_name
            }
        }


class JsonElement(MessageElement):
    """JSON消息元素"""
    def __init__(self, data: str):
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "json",
            "data": {
                "data": self.data
            }
        }


class FaceElement(MessageElement):
    """表情消息元素"""
    def __init__(self, face_id: str):
        self.face_id = face_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "face",
            "data": {
                "id": self.face_id
            }
        }
