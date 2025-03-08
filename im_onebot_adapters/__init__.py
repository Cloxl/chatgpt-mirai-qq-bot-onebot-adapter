from kirara_ai.logger import get_logger
from kirara_ai.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from kirara_ai.plugin_manager.plugin import Plugin
from kirara_ai.im.im_registry import IMRegistry
from .adapter import OneBotAdapter
from .config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):
        self.im_registry.register(
            "onebot",
            OneBotAdapter,
            OneBotConfig
        )
        
        logger.info("OneBotAdapter plugin loaded")

    def on_start(self):
        logger.info("OneBotAdapter plugin started")

    def on_stop(self):
        logger.info("OneBotAdapter plugin stopped")