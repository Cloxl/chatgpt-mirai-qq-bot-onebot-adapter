from framework.logger import get_logger
from framework.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from framework.plugin_manager.plugin import Plugin
from framework.im.im_registry import IMRegistry
from .adapter import OneBotAdapter
from .config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    def __init__(self):
        pass

    def on_load(self):

        class OneBotAdapterFactory:
            def __init__(self, dispatcher: WorkflowDispatcher):
                self.dispatcher = dispatcher
            
            def __call__(self, config: OneBotConfig):
                return OneBotAdapter(config, self.dispatcher)
        
        self.im_registry.register(
            "onebot",
            OneBotAdapterFactory(self.workflow_dispatcher),
            OneBotConfig
        )
        
        logger.info("OneBotAdapter plugin loaded")

    def on_start(self):
        logger.info("OneBotAdapter plugin started")

    def on_stop(self):
        logger.info("OneBotAdapter plugin stopped")