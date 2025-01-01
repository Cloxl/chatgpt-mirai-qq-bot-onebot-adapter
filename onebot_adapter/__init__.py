from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from plugins.onebot_adapter.adapter import OneBotAdapter
from plugins.onebot_adapter.config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register("onebot", OneBotAdapter, OneBotConfig)
        logger.info("OneBotAdapter registered")

    def on_start(self):
        logger.info("OneBotAdapterPlugin started")

    def on_stop(self):
        logger.info("OneBotAdapterPlugin stopped")
