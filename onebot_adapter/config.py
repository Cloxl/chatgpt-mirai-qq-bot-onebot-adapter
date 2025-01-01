from typing import Optional

from pydantic import BaseModel, Field


class OneBotConfig(BaseModel):
    """OneBot 适配器配置"""
    name: str = Field(..., description="适配器实例名称")
    host: str = Field(default="127.0.0.1", description="OneBot 服务器地址")
    port: int = Field(default=5455, description="OneBot 服务器端口")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    filter_file: str = Field(default="filter.json", description="过滤规则文件路径")

    class Config:
        # 允许额外字段
        extra = "allow"