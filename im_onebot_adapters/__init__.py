import os
from kirara_ai.logger import get_logger
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.im.im_registry import IMRegistry
from .adapter import OneBotAdapter
from .config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    
    web_server: WebServer
    
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register(
            "onebot",
            OneBotAdapter,
            OneBotConfig,
            "OneBot V11",
            "OneBot 反向 WebSocket 接口。OneBot 是一个聊天机器人应用接口标准，可以在支持的平台上使用。",
            "OneBot 是一个聊天机器人应用接口标准，可以在[这里](https://oa-docs.cloxl.com/)查看常见聊天机器人平台的配置方法。"
        )
        self.web_server.add_static_assets(
            "/assets/icons/im/onebot.png", os.path.join(os.path.dirname(__file__), "assets", "onebot.png")
        )
        logger.info("OneBotAdapter plugin loaded")

    def on_start(self):
        logger.info("OneBotAdapter plugin started")

    def on_stop(self):
        logger.info("OneBotAdapter plugin stopped")