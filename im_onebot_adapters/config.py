from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

WEBSOCKET_URL_PREFIX = "/im/websocket/onebot"


def make_websocket_url():
    return f"{WEBSOCKET_URL_PREFIX}/{str(uuid.uuid4())[:8]}/ws"


def auto_generate_websocket_url(s: dict):
    s["readOnly"] = True
    s["default"] = make_websocket_url()
    s["textType"] = True
    s["apiEndpoint"] = True


class OneBotConfig(BaseModel):
    """OneBot 适配器配置"""
    websocket_url: str = Field(
        title="反向 Websocket 服务器 URL", description="反向 Websocket 服务器 URL，填写在机器人平台配置中",
        default_factory=make_websocket_url,
        json_schema_extra=auto_generate_websocket_url
    )
    
    access_token: Optional[str] = Field(
        default=None, title="访问Token", description="访问令牌，可空，需与机器人平台配置一致")

    heartbeat_interval: int = Field(
        default=15, title="心跳间隔", description="用于维持连接的间隔时间，单位为秒，可保持默认。")

    host: Optional[str] = Field(
                        default=None, 
                        title="反向 Websocket 服务器地址",
                        description="服务监听地址，需要让机器人平台可访问到（已过时，请使用 websocket_url 代替）",
                        json_schema_extra={"hidden_unset": True})
    port: Optional[int] = Field(
                        default=None, 
                        title="反向 Websocket 服务器端口",
                        description="服务监听端口（已过时，请使用 websocket_url 代替）",
                        json_schema_extra={"hidden_unset": True})
    
    model_config = ConfigDict(extra="allow")
