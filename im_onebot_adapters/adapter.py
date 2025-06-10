from typing import Dict, Optional, Set, Any, List
import asyncio
import functools
import random
import time
from urllib.parse import urlparse

from aiocqhttp import CQHttp, Event
from aiocqhttp import MessageSegment
import aiocqhttp
from hypercorn.asyncio import serve
from hypercorn.config import Config

from kirara_ai.im.adapter import BotProfileAdapter, EditStateAdapter, IMAdapter, UserProfileAdapter
from kirara_ai.im.message import FaceElement, IMMessage, ImageMessage, JsonElement, MentionElement, ReplyElement, TextMessage, AtElement, VideoMessage, VoiceMessage
from kirara_ai.im.profile import UserProfile, Gender
from kirara_ai.im.sender import ChatSender, ChatType
from kirara_ai.logger import get_logger, HypercornLoggerWrapper
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.dispatch.dispatcher import WorkflowDispatcher
from .config import OneBotConfig
from .handlers.message_result import MessageResult
from .utils.message import create_message_element


class OneBotAdapter(IMAdapter, UserProfileAdapter, BotProfileAdapter, EditStateAdapter):
    dispatcher: WorkflowDispatcher
    web_server: WebServer

    def __init__(self, config: OneBotConfig):
        # 初始化
        super().__init__()
        self.config = config
        self.bot = CQHttp()
        self.logger = get_logger("OneBot")
        self.self_id = None

        # 统一的连接状态管理
        self.connections = {}  # {bot_id: {'last_heartbeat': timestamp, 'active': True}}
        self.heartbeat_interval = config.heartbeat_interval
        self.heartbeat_timeout = config.heartbeat_interval * 2
        
        # 任务管理
        self._server_task = None
        self._heartbeat_task = None
        self._reconnect_task = None
        
        # 简化的连接管理
        self._mount_path = None
        
        # 注册事件处理器
        self.bot.on_meta_event(self._handle_meta)
        self.bot.on_notice(self.handle_notice)
        self.bot.on_message(self._handle_msg)

        # 用户资料缓存
        self._profile_cache: Dict[str, UserProfile] = {}
        self._profile_cache_time: Dict[str, float] = {}
        self._cache_ttl = 3600

    async def _check_heartbeats(self):
        """检查所有连接的心跳状态"""
        while True:
            try:
                current_time = time.time()
                for bot_id, conn_info in list(self.connections.items()):
                    if current_time - conn_info['last_heartbeat'] > self.heartbeat_timeout:
                        self.logger.warning(f"Bot {bot_id} 心跳超时断开")
                        self.connections.pop(bot_id, None)
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.logger.error(f"心跳检查异常: {e}")
                await asyncio.sleep(5)

    async def _handle_meta(self, event: Event):
        """处理元事件"""
        self_id = event.self_id

        if event.get('meta_event_type') == 'lifecycle':
            if event.get('sub_type') == 'connect':
                self.logger.info(f"Bot {self_id} Connected")
                self.connections[self_id] = {
                    'last_heartbeat': time.time(),
                    'active': True
                }

            elif event.get('sub_type') == 'disconnect':
                self.logger.info(f"Bot {self_id} Disconnected")
                self.connections.pop(self_id, None)

        elif event.get('meta_event_type') == 'heartbeat':
            if self_id in self.connections:
                self.connections[self_id]['last_heartbeat'] = time.time()
            else:
                self.connections[self_id] = {
                    'last_heartbeat': time.time(),
                    'active': True
                }

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
                self.logger.error(f"消息元素转换失败: {e}")

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
                self.logger.error(f"消息段转换失败 {element.__class__.__name__}: {e}")

        return segments

    async def _start_standalone_server(self):
        """启动独立服务器"""
        # 配置 hypercorn
        hypercorn_config = Config()
        hypercorn_config.bind = [f"{self.config.host}:{self.config.port}"]
        hypercorn_config._log = hypercorn_config.__class__.log_class(hypercorn_config)
        hypercorn_config._log.access_logger = HypercornLoggerWrapper(self.logger)
        hypercorn_config._log.error_logger = HypercornLoggerWrapper(self.logger)
        
        # 启动心跳检查和服务器
        self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
        self._server_task = asyncio.create_task(serve(self.bot._server_app, hypercorn_config))
        self.logger.info(f"OneBot适配器已在独立模式下启动：{self.config.host}:{self.config.port}")

    async def _inject_websocket_service(self):
        """注入 WebSocket 服务到现有Web应用中"""
        try:
            # 获取WebSocket URL和应用
            app = self.bot._server_app
            ws_url = self.config.websocket_url
            
            # 简化URL处理
            url_parts = urlparse(ws_url)
            path = url_parts.path.rstrip('/')
            
            # 从路径中提取挂载点和WebSocket路由
            if '/' in path:
                mount_path, ws_route = path.rsplit('/', 1)
            else:
                mount_path = ''
                ws_route = path or 'ws'
                
            # 确保挂载路径格式正确
            if mount_path and not mount_path.startswith('/'):
                mount_path = '/' + mount_path
                
            # 存储挂载路径
            self._mount_path = mount_path
            
            # 注册WebSocket路由
            if hasattr(self.bot, '_server_app'):
                from quart import websocket
                
                @self.bot._server_app.websocket(f'/{ws_route}')
                async def ws_handler():
                    # 每个新的WebSocket连接都会触发此处理器
                    try:
                        await self.bot._handle_ws()
                    except Exception as e:
                        self.logger.error(f"WebSocket处理异常: {e}")
            
            # 挂载WebSocket应用
            self.web_server.app.mount(mount_path, app)
            
            # 启动心跳检查和重连监控
            self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
            self._reconnect_task = asyncio.create_task(self._websocket_reconnect_monitor())
            
            self.logger.info(f"OneBot适配器已启动于 {mount_path}，WebSocket路由: /{ws_route}")
            
        except Exception as e:
            self.logger.error(f"挂载WebSocket服务失败: {e}")
            raise

    async def _websocket_reconnect_monitor(self):
        """WebSocket重连监控"""
        try:
            while True:
                await asyncio.sleep(15)
                
                # 仅当没有活动连接时尝试重连
                if not self.connections and self._mount_path and self.web_server:
                    try:
                        # 检查路由是否存在
                        has_route = any(
                            hasattr(route, 'path') and str(route.path) == self._mount_path
                            for route in self.web_server.app.routes
                        )
                        
                        # 路由不存在时重新挂载
                        if not has_route and hasattr(self.bot, '_server_app'):
                            self.web_server.app.mount(self._mount_path, self.bot._server_app)
                            self.logger.info(f"已重新挂载WebSocket路由: {self._mount_path}")
                            
                            # 尝试重新初始化WebSocket
                            if hasattr(self.bot, '_initialize_ws'):
                                await self.bot._initialize_ws()
                                self.logger.info("已重新初始化WebSocket连接")
                    except Exception as e:
                        self.logger.error(f"WebSocket重连失败: {e}")
                        
        except asyncio.CancelledError:
            return
        except Exception as e:
            self.logger.error(f"WebSocket重连监控异常: {e}")

    async def start(self):
        """启动适配器"""
        try:
            # 重置状态
            self.connections.clear()
            
            # 根据配置选择启动模式
            if self.config.host and self.config.port:
                self.logger.warning("正在使用过时的独立服务器模式，建议更新为WebSocket URL模式")
                await self._start_standalone_server()
            else:
                await self._inject_websocket_service()
                
        except Exception as e:
            self.logger.error(f"启动OneBot适配器失败: {e}")
            raise

    async def stop(self):
        """停止适配器"""
        try:
            # 1. 取消所有后台任务
            for task in [self._reconnect_task, self._heartbeat_task, self._server_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 清空任务引用
            self._reconnect_task = None
            self._heartbeat_task = None
            self._server_task = None
            
            # 2. 停止消息总线
            if hasattr(self.bot, '_bus'):
                self.bot._bus._subscribers.clear()

            # 3. 关闭WebSocket连接
            if hasattr(self.bot, '_websocket') and self.bot._websocket:
                if not isinstance(self.bot._websocket, functools.partial):
                    try:
                        await self.bot._websocket.close()
                    except Exception as e:
                        self.logger.error(f"关闭WebSocket连接失败: {e}")

            # 4. 根据启动模式清理资源
            if self.config.host and self.config.port:
                # 关闭独立服务器
                if hasattr(self.bot, '_server_app') and hasattr(self.bot._server_app, 'shutdown'):
                    try:
                        await self.bot._server_app.shutdown()
                    except Exception as e:
                        self.logger.error(f"关闭独立服务器失败: {e}")
            else:
                # 从web_server卸载路由
                if self._mount_path and self.web_server and hasattr(self.web_server, 'app'):
                    routes_to_remove = [
                        route for route in self.web_server.app.routes
                        if hasattr(route, 'path') and str(route.path) == self._mount_path
                    ]
                    
                    for route in routes_to_remove:
                        self.web_server.app.routes.remove(route)
                
                # 关闭WebSocket客户端
                if hasattr(self.bot, '_server_app'):
                    clients = getattr(self.bot._server_app, 'websocket_clients', [])
                    for client in list(clients):
                        if hasattr(client, 'close'):
                            try:
                                await client.close()
                            except Exception:
                                pass
            
            # 5. 清理状态
            self.connections.clear()
            
            self.logger.info("OneBot适配器已停止")
        except Exception as e:
            self.logger.error(f"停止OneBot适配器失败: {e}")

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

    async def set_chat_editing_state(
        self, chat_sender: ChatSender, is_editing: bool = True
    ):
        """
        设置或取消对话的编辑状态
        :param chat_sender: 对话的发送者
        :param is_editing: True 表示正在编辑，False 表示取消编辑状态
        """
        # OneBot不支持发送输入状态，这里只记录日志
        self.logger.debug(
            f"Setting chat editing state to {is_editing} for chat_sender {chat_sender}"
        )
