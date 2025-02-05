from typing import Optional

from pydantic import BaseModel, Field


class OneBotConfig(BaseModel):
    """OneBot 适配器配置"""
    host: str = Field(default="127.0.0.1", description="OneBot 服务器地址")
    port: int = Field(default=5455, description="OneBot 服务器端口")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    heartbeat_interval: int = Field(default=15, description="心跳间隔 (秒)")

    class Config:
        # 允许额外字段
        extra = "allow"