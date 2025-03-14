import uuid
from typing import Optional

from pydantic import BaseModel, Field


def make_webhook_url():
    return f"/im/webhook/onebot/{str(uuid.uuid4())[:8]}"


def auto_generate_webhook_url(s: dict):
    s["readOnly"] = True
    s["default"] = make_webhook_url()
    s["textType"] = True


class OneBotConfig(BaseModel):
    """OneBot 适配器配置"""
    host: str = Field(default="127.0.0.1", description="OneBot 服务器地址")
    port: int = Field(default=5455, description="OneBot 服务器端口")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    heartbeat_interval: int = Field(default=15, description="心跳间隔 (秒)")
    
    webhook_url: str = Field(
        default_factory=make_webhook_url,
        description="供 OneBot 回调的 URL，由系统自动生成",
        json_schema_extra=auto_generate_webhook_url
    )

    class Config:
        # 允许额外字段
        extra = "allow"