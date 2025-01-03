import asyncio
import os
import time

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
        self.bot = CQHttp()

        # 从配置获取过滤规则文件路径
        filter_path = os.path.join(
            os.path.dirname(__file__),
            self.config.filter_file
        )
        self.event_filter = EventFilter(filter_path)

        self._server_task = None
        self.heartbeat_states = {}  # 存储每个 bot 的心跳状态
        self.heartbeat_timeout = self.config.heartbeat_interval
        self._heartbeat_task = None

        # 注册消息和元事件处理器
        self.bot.on_message(self._handle_msg)
        self.bot.on_meta_event(self._handle_meta)

    async def _check_heartbeats(self):
        """检查所有连接的心跳状态"""
        while True:
            current_time = time.time()
            for self_id, last_time in list(self.heartbeat_states.items()):
                if current_time - last_time > self.heartbeat_timeout:
                    logger.warning(f"Bot {self_id} disconnected (heartbeat timeout)")
                    self.heartbeat_states.pop(self_id, None)
            await asyncio.sleep(5)  # 每5秒检查一次

    async def _handle_meta(self, event):
        """处理元事件"""
        self_id = event.self_id

        if event.get('meta_event_type') == 'lifecycle':
            if event.get('sub_type') == 'connect':
                logger.info(f"Bot {self_id} connected")
                self.heartbeat_states[self_id] = time.time()
            elif event.get('sub_type') == 'disconnect':
                logger.info(f"Bot {self_id} disconnected")
                self.heartbeat_states.pop(self_id, None)

        elif event.get('meta_event_type') == 'heartbeat':
            self.heartbeat_states[self_id] = time.time()

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
            logger.info(f"Starting OneBot adapter on {self.config.host}:{self.config.port}")
            loop = asyncio.new_event_loop()
            
            # 启动心跳检测服务
            self._heartbeat_task = loop.create_task(self._check_heartbeats())
            
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
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            
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