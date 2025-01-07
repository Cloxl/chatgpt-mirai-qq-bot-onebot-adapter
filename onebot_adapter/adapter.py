import asyncio
import os
import time
from typing import Optional, List, Dict, Any

from aiocqhttp import CQHttp, Event
from aiocqhttp import Message as OneBotMessage
from aiocqhttp import MessageSegment

from framework.im.adapter import IMAdapter
from framework.im.message import IMMessage
from framework.logger import get_logger

from .config import OneBotConfig
from .handlers.event_filter import EventFilter
from .message.media import create_message_element
from .handlers.message_result import MessageResult, UserOperationType

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
        self.bot.on_notice(self.handle_notice)

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

    async def handle_notice(self, event: Event):
        pass

    async def handle_message(self, event: Event, message: IMMessage):
        """处理普通消息"""
        pass

    def convert_to_message(self, event) -> IMMessage:
        """将 OneBot 消息转换为统一消息格式"""
        segments = []
        sender = event.get('sender', {}).get('nickname', '') or str(event.get('user_id', ''))

        for msg in event['message']:
            element = create_message_element(msg['type'], msg['data'])

            if element:
                segments.append(element)

        return IMMessage(sender=sender, message_elements=segments, raw_message={})

    def convert_to_message_segment(self, message: IMMessage) -> OneBotMessage:
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

    async def start(self):
        """启动适配器"""
        try:
            logger.info(f"Starting OneBot adapter on {self.config.host}:{self.config.port}")

            # 使用现有的事件循环
            self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
            self._server_task = asyncio.create_task(self.bot.run_task(
                host=self.config.host,
                port=int(self.config.port)
            ))

            logger.info(f"OneBot adapter started")
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

    async def _delayed_recall(
            self,
            message_id: int,
            delay: int,
            results_list: List[Dict[str, Any]]
    ):
        """带结果记录的延迟撤回"""
        try:
            await asyncio.sleep(delay)
            recall_result = await self.bot.delete_msg(message_id=message_id)
            results_list.append({"action": "delayed_recall", "result": recall_result})
        except Exception as e:
            results_list.append({
                "action": "delayed_recall",
                "error": str(e)
            })

    async def send_message(
            self,
            self_id: int,
            chat_id: str,
            message: IMMessage,
            reply_id: Optional[int] = None,
            delete_after: Optional[int] = None,
            target_user_id: Optional[int] = None,
            operation_type: UserOperationType = UserOperationType.NONE,
            operation_duration: Optional[int] = None,
            recall_target_id: Optional[int] = None
    ) -> MessageResult:
        """统一的消息发送方法

        Args:
            self_id: 机器人QQ号
            chat_id: 目标ID (private_{user_id} 或 group_{group_id})
            message: 统一消息格式
            reply_id: 要回复的消息ID
            delete_after: 发送后自动撤回等待时间(秒)
            target_user_id: 目标用户ID
            operation_type: 对目标用户的操作类型
            operation_duration: 操作时长(如禁言时间)
            recall_target_id: 要撤回的目标消息ID
        """
        result = MessageResult(
            target_user_id=target_user_id,
            operation_type=operation_type
        )

        try:
            message_type, target_id = chat_id.split('_')
            target_id = int(target_id)

            # 转换消息格式
            onebot_message = self.convert_to_message_segment(message)

            # 添加回复
            if reply_id:
                onebot_message = MessageSegment.reply(reply_id) + onebot_message

            # 根据操作类型处理
            if message_type == 'group':
                # 撤回消息
                if operation_type == UserOperationType.RECALL and recall_target_id:
                    try:
                        recall_result = await self.bot.delete_msg(message_id=recall_target_id)
                        result.recalled_id = recall_target_id
                        result.raw_results.append({"action": "recall", "result": recall_result})
                        if not message.message_elements:
                            return result
                    except Exception as e:
                        result.success = False
                        result.error = f"Failed to recall message: {str(e)}"
                        return result

                # 不能使用此方法简化if逻辑 如果是普通信息缺失target_user_id会导致无法发送消息
                # if not target_user_id:
                #     ...

                # @用户
                if operation_type == UserOperationType.AT and target_user_id:
                    onebot_message = MessageSegment.at(target_user_id) + MessageSegment.text(' ') + onebot_message

                # 禁言用户
                elif operation_type == UserOperationType.MUTE and target_user_id:
                    try:
                        mute_result = await self.bot.set_group_ban(
                            group_id=target_id,
                            user_id=target_user_id,
                            duration=operation_duration or 60
                        )
                        result.operation_duration = operation_duration
                        result.raw_results.append({"action": "mute", "result": mute_result})
                    except Exception as e:
                        result.success = False
                        result.error = f"Failed to mute user: {str(e)}"
                        return result

                # 踢出用户
                elif operation_type == UserOperationType.KICK and target_user_id:
                    try:
                        kick_result = await self.bot.set_group_kick(
                            group_id=target_id,
                            user_id=target_user_id
                        )
                        result.raw_results.append({"action": "kick", "result": kick_result})
                    except Exception as e:
                        result.success = False
                        result.error = f"Failed to kick user: {str(e)}"
                        return result

            # 发送消息
            try:
                api_func = self.bot.send_private_msg if message_type == 'private' else self.bot.send_group_msg
                target_key = 'user_id' if message_type == 'private' else 'group_id'
                send_result = await api_func(
                    self_id=self_id,
                    **{target_key: target_id},
                    message=onebot_message
                )
                result.message_id = send_result.get('message_id')
                result.raw_results.append({"action": "send", "result": send_result})

                if delete_after and result.message_id:
                    await asyncio.create_task(self._delayed_recall(
                        result.message_id,
                        delete_after,
                        result.raw_results
                    ))

            except Exception as e:
                result.success = False
                result.error = f"Failed to send message: {str(e)}"

            return result

        except Exception as e:
            result.success = False
            result.error = f"Error in send_message: {str(e)}"
            return result
