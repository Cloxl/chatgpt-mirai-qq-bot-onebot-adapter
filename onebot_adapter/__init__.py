from framework.logger import get_logger
from framework.plugin_manager.plugin import Plugin
from framework.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from framework.plugin_manager.plugin import Plugin
from framework.im.im_registry import IMRegistry
from .adapter import OneBotAdapter
from .config import OneBotConfig

logger = get_logger("OneBot-Adapter")


class OneBotAdapterPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "onebot_adapter"
        self.description = "OneBot adapter for chatgpt-mirai-qq-bot"
        self.version = "0.1.4"

    def on_init(self):
        """初始化插件"""
        # 注册 OneBot 适配器
        im_registry = self.container.resolve(IMRegistry)
        im_registry.register("onebot", OneBotAdapter, OneBotConfig)

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