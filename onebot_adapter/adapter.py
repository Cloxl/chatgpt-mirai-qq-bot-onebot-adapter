import asyncio
import os

from aiocqhttp import CQHttp, Event
from aiocqhttp import Message as OneBotMessage
from aiocqhttp import MessageSegment

from framework.im.adapter import IMAdapter
from framework.im.message import Message
from framework.logger import get_logger

from .config import OneBotConfig
from .handlers.event_filter import EventFilter
from .message.media import create_message_element

logger = get_logger("OneBot")


class OneBotAdapter(IMAdapter):
    def __init__(self, config: OneBotConfig):
        self.config = config
        # 配置反向 WebSocket
        self.bot = CQHttp(
            enable_http_post=False,
            websocket=False,  # 禁用正向 WebSocket
            ws_reverse_url=f"ws://{self.config.host}:{self.config.port}/ws",  # 反向 WebSocket 地址
            ws_reverse_api_url=f"ws://{self.config.host}:{self.config.port}/ws/api",  # API
            ws_reverse_event_url=f"ws://{self.config.host}:{self.config.port}/ws/event",  # 事件
            ws_reverse_reconnect_interval=int(self.config.reconnect_interval),  # 重连间隔
            ws_reverse_reconnect_on_code_1000=True,  # 允许正常关闭时重连
        )

        # 从配置获取过滤规则文件路径
        filter_path = os.path.join(
            os.path.dirname(__file__),
            self.config.filter_file
        )
        self.event_filter = EventFilter(filter_path)
        self._server_task = None

        # 注册消息和元事件处理器
        self.bot.on_message(self._handle_msg)
        self.bot.on_meta_event(self._handle_meta)

    async def _handle_meta(self, event):
        """处理元事件"""
        # 连接事件处理
        if event.get('meta_event_type') == 'lifecycle':
            if event.get('sub_type') == 'connect':
                logger.info(f"bot {event.self_id} connected")
            elif event.get('sub_type') == 'disconnect':
                logger.info(f"bot {event.self_id} disconnected")

        elif event.get('meta_event_type') == 'heartbeat':
            # logger.debug("Received heartbeat")
            pass

    async def _handle_msg(self, event):
        """处理消息的回调函数"""
        if not self.event_filter.should_handle(event):
            return

        message = self.convert_to_message(event)

        await self.handle_message(
            event=event,
            message=message
        )

    async def handle_message(self, event: Event, message: Message):
        """处理普通消息"""
        pass

    def convert_to_message(self, event):
        """将 OneBot 消息转换为统一消息格式"""
        segments = []
        sender = event.get('sender', {}).get('nickname', '') or str(event.get('user_id', ''))

        for msg in event['message']:
            element = create_message_element(msg['type'], msg['data'])

            if element:
                segments.append(element)

        return Message(sender=sender, message_elements=segments, raw_message={})

    def convert_to_message_segment(self, message: Message) -> OneBotMessage:
        """将统一消息格式转换为 OneBot 消息"""
        onebot_message = OneBotMessage()

        # 消息类型到转换方法的映射
        segment_converters = {
            'text': lambda data: MessageSegment.text(data['text']),
            'image': lambda data: MessageSegment.image(data['url']),
            'at': lambda data: MessageSegment.at(data['data']['qq']),
            'reply': lambda data: MessageSegment.reply(data['data']['id']),
            'face': lambda data: MessageSegment.face(int(data['data']['id'])),
            'record': lambda data: MessageSegment.record(data['data']['url']),
            'voice': lambda data: MessageSegment.record(data['url']),
            'video': lambda data: MessageSegment.video(data['data']['file']),
            'json': lambda data: MessageSegment.json(data['data']['data'])
        }

        for element in message.message_elements:
            data = element.to_dict()
            msg_type = data['type']

            try:
                if msg_type in segment_converters:
                    segment = segment_converters[msg_type](data)
                    onebot_message.append(segment)
            except Exception as e:
                logger.error(f"Failed to convert message segment type {msg_type}: {e}")

        return onebot_message

    def run(self):
        """启动适配器"""
        try:
            logger.info(f"Starting OneBot adapter [{self.config.name}] on {self.config.host}:{self.config.port}")

            # 创建事件循环
            loop = asyncio.new_event_loop()

            self._server_task = loop.create_task(self.bot.run_task(
                host=self.config.host,
                port=int(self.config.port)
            ))
            loop.run_forever()

            logger.info(f"OneBot adapter [{self.config.name}] started")
        except Exception as e:
            logger.error(f"Failed to start OneBot adapter: {str(e)}")
            raise

    async def stop(self):
        """停止适配器"""
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            self._server_task = None
            await self.bot._server_app.shutdown()
        logger.info("OneBot adapter stopped")

    async def send_message(self, self_id: int, chat_id: str, message: Message):
        """发送消息"""
        onebot_message = self.convert_to_message_segment(message)
        message_type = 'private' if chat_id.startswith('private_') else 'group'
        target_id = int(chat_id.split('_')[1])

        if message_type == 'private':
            await self.bot.send_private_msg(self_id=self_id, user_id=target_id, message=onebot_message)
        else:
            await self.bot.send_group_msg(self_id=self_id, group_id=target_id, message=onebot_message)