from ast import List
import asyncio
import functools
import random
import time
from typing import Dict, Optional

from aiocqhttp import CQHttp, Event
from aiocqhttp import MessageSegment
import aiocqhttp
from hypercorn.asyncio import serve
from hypercorn.config import Config

from kirara_ai.im.adapter import BotProfileAdapter, IMAdapter, UserProfileAdapter
from kirara_ai.im.message import FaceElement, IMMessage, ImageMessage, JsonElement, MentionElement, ReplyElement, TextMessage, AtElement, VideoMessage, VoiceMessage
from kirara_ai.im.profile import UserProfile, Gender
from kirara_ai.im.sender import ChatSender, ChatType
from kirara_ai.logger import get_logger, HypercornLoggerWrapper
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from .config import OneBotConfig
from .handlers.message_result import MessageResult
from .utils.message import create_message_element


class OneBotAdapter(IMAdapter, UserProfileAdapter, BotProfileAdapter):
    dispatcher: WorkflowDispatcher
    web_server: WebServer

    def __init__(self, config: OneBotConfig):
        # 初始化
        super().__init__()
        self.config = config  # 配置
        self.bot = CQHttp()  # 初始化CQHttp
        self.logger = get_logger("OneBot")
        self.self_id = None

        # 初始化状态
        self._server_task = None  # 反向ws任务
        self.heartbeat_states: Dict[int, float] = {}  # 存储每个 bot 的心跳状态
        self.heartbeat_interval = self.config.heartbeat_interval  # 心跳间隔
        self.heartbeat_timeout = self.config.heartbeat_interval * 2  # 心跳超时
        self._heartbeat_task = None  # 心跳检查任务

        # 注册事件处理器
        self.bot.on_meta_event(self._handle_meta)  # 元事件处理器
        self.bot.on_notice(self.handle_notice)  # 通知处理器
        self.bot.on_message(self._handle_msg)  # 消息处理器

        # 添加用户资料缓存,TTL为1小时
        self._profile_cache: Dict[str, UserProfile] = {}  # 用户资料缓存
        self._profile_cache_time: Dict[str, float] = {}  # 缓存时间记录
        self._cache_ttl = 3600  # 缓存过期时间(秒)

    async def _check_heartbeats(self):
        """
        检查所有连接的心跳状态

        兼容一些不发送disconnect事件的bot平台
        """
        while True:
            current_time = time.time()
            for self_id, last_time in list(self.heartbeat_states.items()):
                if current_time - last_time > self.heartbeat_timeout:
                    self.logger.warning(
                        f"Bot {self_id} disconnected (heartbeat timeout)")
                    self.heartbeat_states.pop(self_id, None)
            await asyncio.sleep(self.heartbeat_interval)

    async def _handle_meta(self, event: Event):
        """处理元事件"""
        self_id = event.self_id

        if event.get('meta_event_type') == 'lifecycle':
            if event.get('sub_type') == 'connect':
                self.logger.info(f"Bot {self_id} connected")
                self.heartbeat_states[self_id] = time.time()

            elif event.get('sub_type') == 'disconnect':
                # 当bot断开连接时,  停止该bot的事件处理
                self.logger.info(f"Bot {self_id} disconnected")
                self.heartbeat_states.pop(self_id, None)

        elif event.get('meta_event_type') == 'heartbeat':
            self.heartbeat_states[self_id] = time.time()

        self.self_id = self_id

    async def _handle_msg(self, event: Event):
        """处理消息的回调函数"""
        message = await self.convert_to_message(event)

        await self.dispatcher.dispatch(self, message)

    async def handle_notice(self, event: Event):
        """处理通知事件"""
        pass

    async def convert_to_message(self, event: Event) -> IMMessage:
        """将 OneBot 消息转换为统一消息格式"""
        assert event.message is not None
        # 构造发送者信息
        sender_info = event.sender or {}
        if event.group_id:
            sender = ChatSender.from_group_chat(
                user_id=str(event.user_id),
                group_id=str(event.group_id),
                display_name=sender_info.get('nickname', str(event.user_id)),
                metadata=sender_info
            )
        else:
            sender = ChatSender.from_c2c_chat(
                user_id=str(event.user_id),
                display_name=sender_info.get('nickname', str(event.user_id)),
                metadata=sender_info
            )

        # 转换消息元素
        message_elements = []
        for msg in event.message:
            try:
                if msg['type'] == 'at':
                    if str(msg['data']['qq']) == str(event.self_id):
                        msg['data']['is_bot'] = True  # 标记这是at机器人的消息

                element = create_message_element(
                    msg['type'], msg['data'], self.logger)
                if element:
                    message_elements.append(element)
            except Exception as e:
                self.logger.error(f"Failed to convert message element: {e}")

        return IMMessage(
            sender=sender,
            message_elements=message_elements,
            raw_message=event
        )

    async def convert_to_message_segment(self, message: IMMessage) -> list[MessageSegment]:
        """将统一消息格式转换为 OneBot 消息段列表"""
        segments: list[MessageSegment] = []

        async def convert_image(data: ImageMessage) -> MessageSegment:
            url: str = await data.get_url()
            return MessageSegment.image(url)

        async def convert_voice(data: VoiceMessage) -> MessageSegment:
            url: str = await data.get_url()
            return MessageSegment.record(url)

        async def convert_video(data: VideoMessage) -> MessageSegment:
            url: str = await data.get_url()
            return MessageSegment.video(url)

        segment_converters = {
            TextMessage: lambda data: MessageSegment.text(data.text),
            MentionElement: lambda data: MessageSegment.at(data.target.user_id),
            ImageMessage: convert_image,
            AtElement: lambda data: MessageSegment.at(data.user_id),
            ReplyElement: lambda data: MessageSegment.reply(data.message_id),
            FaceElement: lambda data: MessageSegment.face(data.face_id),
            VoiceMessage: convert_voice,
            VideoMessage: convert_video,
            JsonElement: lambda data: MessageSegment.json(data.data)
        }

        for element in message.message_elements:
            try:
                for k, v in segment_converters.items():
                    if isinstance(element, k):
                        if asyncio.iscoroutinefunction(v):
                            segment = await v(element)
                        else:
                            segment = v(element)
                        segments.append(segment)
                        break
            except Exception as e:
                self.logger.error(
                    f"Failed to convert message segment type {element.__class__.__name__}: {e}")

        return segments

    async def _start_standalone_server(self):
        """启动旧版服务器"""
        # 使用现有的事件循环
        
        # 配置 hypercorn
        from hypercorn.logging import Logger
        hypercorn_config = Config()
        hypercorn_config.bind = [f"{self.config.host}:{self.config.port}"]
        hypercorn_config._log = Logger(hypercorn_config)
        hypercorn_config._log.access_logger = HypercornLoggerWrapper(
            self.logger) # type: ignore
        hypercorn_config._log.error_logger = HypercornLoggerWrapper(
            self.logger) # type: ignore
        
        self._heartbeat_task = asyncio.create_task(self._check_heartbeats())

        # 获取 quart 应用实例
        app = self.bot._server_app

        # 使用 hypercorn serve 启动 quart 应用
        self._server_task = asyncio.create_task(
            serve(app, hypercorn_config)
        )

        self.logger.info(f"OneBot adapter started")

    async def _inject_websocket_service(self):
        """注入 WebSocket 服务"""
        app = self.bot._server_app
        # 因为 CQHttp 注册了 /ws 路径，所以需要去除掉后缀再注册
        register_base_url = self.config.websocket_url.removesuffix("/ws")
        self.web_server.app.mount(register_base_url, app) # type: ignore
        self.logger.info(f"OneBot adapter started")

    async def start(self):
        """启动适配器"""
        try:
            if self.config.host and self.config.port:
                self.logger.warning("正在使用过时的启动模式，请尽快更新为 Websocket Url 模式。")
                await self._start_standalone_server()
            else:
                await self._inject_websocket_service()

        except Exception as e:
            self.logger.error(f"Failed to start OneBot adapter: {str(e)}")
            raise

    async def _stop_standalone_server(self):
        """停止旧版服务器"""
        # 4. 关闭 Hypercorn 服务器
        if hasattr(self.bot, '_server_app'):
            try:
                # 获取 Hypercorn 服务器实例
                server = getattr(self.bot._server_app, '_server', None)
                if server:
                    # 停止接受新连接
                    server.close()
                    await server.wait_closed()

                # 关闭所有 WebSocket 连接
                for client in getattr(self.bot._server_app, 'websocket_clients', []):
                    if hasattr(client, 'close'):
                        await client.close()

                # 关闭 ASGI 应用
                if hasattr(self.bot._server_app, 'shutdown'):
                    await self.bot._server_app.shutdown()

            except Exception as e:
                self.logger.warning(
                    f"Error shutting down Hypercorn server: {e}")

    async def stop(self):
        """停止适配器"""
        try:
            # 1. 停止消息处理
            if hasattr(self.bot, '_bus'):
                self.bot._bus._subscribers.clear()  # 清除所有事件监听器

            # 2. 停止心跳检查
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                self._heartbeat_task = None

            # 3. 关闭 WebSocket 连接
            if hasattr(self.bot, '_websocket') and self.bot._websocket:
                if not isinstance(self.bot._websocket, functools.partial):  # 检查类型
                    await self.bot._websocket.close()

            if self.config.host and self.config.port:
                await self._stop_standalone_server()
            else:
                # unregister old route if exists
                for route in self.web_server.app.routes:
                    if self.config.websocket_url in route.path: # type: ignore
                        self.web_server.app.routes.remove(route)
            # 6. 清理状态
            self.heartbeat_states.clear()

            self.logger.info("OneBot adapter stopped")
        except Exception as e:
            self.logger.error(f"Error stopping OneBot adapter: {e}")

    async def recall_message(self, message_id: int, delay: int = 0):
        """撤回消息

        Args:
            message_id: 要撤回的消息ID
            delay: 延迟撤回的时间(秒) 默认为0表示立即撤回
        """
        if delay > 0:
            await asyncio.sleep(delay)
        await self.bot.delete_msg(message_id=message_id)

    async def send_message(self, message: IMMessage, recipient: ChatSender) -> MessageResult:
        """发送消息"""
        result = MessageResult()
        try:
            segments = await self.convert_to_message_segment(message)

            buffer: list[MessageSegment] = []
            text_length = 0

            async def flush():
                nonlocal text_length
                if not buffer:
                    return
                # 计算延时
                duration = max(text_length * 0.1, 1) + random.uniform(0.5, 1.5)
                await asyncio.sleep(duration)

                # 发送消息
                if recipient.chat_type == ChatType.GROUP:
                    assert recipient.group_id is not None
                    send_result = await self.bot.send_group_msg(
                        group_id=int(recipient.group_id),
                        message=buffer
                    )
                else:
                    send_result = await self.bot.send_private_msg(
                        user_id=int(recipient.user_id),
                        message=buffer
                    )
                result.message_id = send_result.get('message_id')
                result.raw_results.append(
                    {"action": "send", "result": send_result})

                # 清空buffer和text_length
                buffer.clear()
                text_length = 0

            for segment in segments:
                # 判断是否需要flush
                if segment.type in ("text", "record", "video", "rps", "dice", "shake", "poke", "share", "contact", "location"):
                    await flush()
                    buffer = [segment]
                    if segment.type == "text":
                        text_length = len(segment.data.get("text", ""))
                else:
                    buffer.append(segment)
                    if segment.type == "text":
                        text_length += len(segment.data.get("text", ""))

            # 发送剩余的消息
            await flush()

            return result

        except Exception as e:
            result.success = False
            result.error = f"Error in send_message: {str(e)}"
            return result

    async def mute_user(self, group_id: str, user_id: str, duration: int):
        """禁言用户"""
        await self.bot.set_group_ban(
            group_id=int(group_id),
            user_id=int(user_id),
            duration=duration
        )

    async def unmute_user(self, group_id: str, user_id: str):
        """解除禁言"""
        await self.mute_user(group_id, user_id, 0)

    async def kick_user(self, group_id: str, user_id: str):
        """踢出用户"""
        await self.bot.set_group_kick(
            group_id=int(group_id),
            user_id=int(user_id)
        )

    async def query_user_profile(self, chat_sender: ChatSender) -> UserProfile:
        """查询用户资料"""
        self.logger.info(f"Querying user profile for sender: {chat_sender}")

        user_id = chat_sender.user_id
        group_id = chat_sender.group_id if chat_sender.chat_type == ChatType.GROUP else None

        # 处理特殊用户 ID
        if user_id == 'bot' or not str(user_id).isdigit():
            return UserProfile(
                user_id=user_id,
                username=user_id,
                display_name=chat_sender.display_name or 'Bot'
            )

        cache_key = f"{user_id}:{group_id}" if group_id else user_id

        # 检查缓存是否存在且未过期
        current_time = time.time()
        if (cache_key in self._profile_cache and
                current_time - self._profile_cache_time.get(cache_key, 0) < self._cache_ttl):
            self.logger.info(f"Cache hit for {cache_key}")
            return self._profile_cache[cache_key]

        try:
            # 获取群成员信息
            if group_id:
                self.logger.info(
                    f"Fetching group member info for user_id={user_id} in group_id={group_id}")
                info = await self.bot.get_group_member_info(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    no_cache=True
                )
                self.logger.info(f"Raw group member info: {info}")
                profile = self._convert_group_member_info(info)
            # 获取用户信息
            else:
                self.logger.info(
                    f"Fetching stranger info for user_id={user_id}")
                info = await self.bot.get_stranger_info(
                    user_id=int(user_id),
                    no_cache=True
                )
                self.logger.info(f"Raw stranger info: {info}")
                profile = self._convert_stranger_info(info)

            # 更新缓存
            self._profile_cache[cache_key] = profile
            self._profile_cache_time[cache_key] = current_time
            self.logger.info(f"Profile cached and returned: {profile}")
            return profile

        except Exception as e:
            self.logger.error(
                f"Failed to get user profile for {chat_sender}: {e}", exc_info=True)
            # 在失败时返回一个基本的用户资料
            return UserProfile(
                user_id=user_id,
                username=user_id,
                display_name=chat_sender.display_name
            )

    def _convert_group_member_info(self, info: dict) -> UserProfile:
        """转换群成员信息为通用格式"""
        gender = Gender.UNKNOWN
        if info.get('sex') == 'male':
            gender = Gender.MALE
        elif info.get('sex') == 'female':
            gender = Gender.FEMALE

        profile = UserProfile(
            user_id=str(info.get('user_id')),
            username=info.get('card') or info.get('nickname'),
            display_name=info.get('card') or info.get('nickname'),
            full_name=info.get('nickname'),
            gender=gender,
            age=info.get('age'),
            level=info.get('level'),
            avatar_url=info.get('avatar'),
            extra_info={
                'role': info.get('role'),
                'title': info.get('title'),
                'join_time': info.get('join_time'),
                'last_sent_time': info.get('last_sent_time')
            }
        )
        return profile

    def _convert_stranger_info(self, info: dict) -> UserProfile:
        """转换陌生人信息为通用格式"""
        gender = Gender.UNKNOWN
        if info.get('sex') == 'male':
            gender = Gender.MALE
        elif info.get('sex') == 'female':
            gender = Gender.FEMALE

        profile = UserProfile(
            user_id=str(info.get('user_id')),
            username=info.get('nickname'),
            display_name=info.get('nickname'),
            gender=gender,
            age=info.get('age'),
            level=info.get('level'),
            avatar_url=info.get('avatar')
        )
        return profile

    async def get_bot_profile(self) -> Optional[UserProfile]:
        """获取机器人资料"""
        try:
            profile = await self.bot.get_login_info()
        except aiocqhttp.exceptions.ApiNotAvailable:
            return UserProfile(
                user_id="unknown",
                username="未连接",
                display_name="未连接"
            )

        return UserProfile(
            user_id=str(self.self_id),
            username=profile.get('nickname'),
            display_name=profile.get('nickname'),
            avatar_url=f"https://q1.qlogo.cn/g?b=qq&nk={self.self_id}&s=640"
        )
