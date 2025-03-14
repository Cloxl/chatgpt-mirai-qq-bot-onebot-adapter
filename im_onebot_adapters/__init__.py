from kirara_ai.logger import get_logger
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.web.app import WebServer

from .adapter import OneBotAdapter
from .config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    web_server: WebServer  # 声明为类属性，会自动注入
    
    def __init__(self):
        pass

    def on_load(self):
        # 注册适配器类型
        self.im_registry.register(
            "onebot",
            OneBotAdapter,
            OneBotConfig,
            "OneBot 协议机器人",
            "支持 OneBot 协议的机器人，可直接接入 go-cqhttp、OneBot-YaYa 等实现。",
            """
支持 OneBot 协议（原 CQHTTP 协议）的机器人，支持通过 WebSocket 反向连接的方式接入。
常见的实现有 go-cqhttp、OneBot-YaYa 等。详细配置请参考 Kirara AI 文档。
            """
        )
        
        # 添加图标资源
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "onebot.png")
        if os.path.exists(icon_path):
            self.web_server.add_static_assets("/assets/icons/im/onebot.png", icon_path)
        
        logger.info("OneBotAdapter plugin loaded")

    def on_start(self):
        logger.info("OneBotAdapter plugin started")

    def on_stop(self):
        logger.info("OneBotAdapter plugin stopped")

# 导出插件类，确保框架能够找到它
__all__ = ["OneBotAdapterPlugin", "OneBotAdapter", "OneBotConfig"]