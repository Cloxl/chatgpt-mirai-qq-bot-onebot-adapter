import asyncio
import random
import time

from aiocqhttp import CQHttp, Event, MessageSegment

from kirara_ai.im.adapter import IMAdapter, UserProfileAdapter
from kirara_ai.im.message import AtElement, IMMessage, TextMessage
from kirara_ai.im.profile import Gender, UserProfile
from kirara_ai.im.sender import ChatSender, ChatType
from kirara_ai.logger import get_logger
from kirara_ai.web.app import WebServer
from kirara_ai.workflow.core.dispatch.dispatcher import WorkflowDispatcher

from .config import OneBotConfig
from .handlers.message_result import MessageResult
from .utils.message import create_message_element


class OneBotAdapter(IMAdapter, UserProfileAdapter):
    dispatcher: WorkflowDispatcher
    web_server: WebServer  # 接收Web服务器引用

    def __init__(self, config: OneBotConfig):
        # 初始化
        super().__init__()
        self.config = config  # 配置
        self.bot = CQHttp()  # 初始化CQHttp
        self.logger = get_logger("OneBot")
        self.is_running = False  # 运行状态标志
        self.mounted_path = None  # 挂载路径

        # 初始化状态
        self.heartbeat_states = {}  # 存储每个 bot 的心跳状态
        self.heartbeat_interval = self.config.heartbeat_interval  # 心跳间隔
        self.heartbeat_timeout = self.config.heartbeat_interval * 2  # 心跳超时
        self._heartbeat_task = None  # 心跳检查任务

        # 注册事件处理器
        self.bot.on_meta_event(self._handle_meta)  # 元事件处理器
        self.bot.on_notice(self.handle_notice)  # 通知处理器
        self.bot.on_message(self._handle_msg)  # 消息处理器

        # 添加用户资料缓存,TTL为1小时
        self._profile_cache = {}  # 用户资料缓存
        self._profile_cache_time = {}  # 缓存时间记录
        self._cache_ttl = 3600  # 缓存过期时间(秒)
        
        # 跟踪WebSocket连接
        self._websocket_connections = set()

    async def _check_heartbeats(self):
        """
        检查所有连接的心跳状态

        兼容一些不发送disconnect事件的bot平台
        """
        while True:
            current_time = time.time()
            for self_id, last_time in list(self.heartbeat_states.items()):
                if current_time - last_time > self.heartbeat_timeout:
                    self.logger.warning(f"Bot {self_id} disconnected (heartbeat timeout)")
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

    async def _handle_msg(self, event: Event):
        """处理消息的回调函数"""
        if not self.is_running:
            self.logger.warning("OneBot adapter is not running, ignoring message")
            return
            
        message = self.convert_to_message(event)
        await self.dispatcher.dispatch(self, message)

    async def handle_notice(self, event: Event):
        """处理通知事件"""
        pass

    def convert_to_message(self, event: Event) -> IMMessage:
        """将 OneBot 消息转换为统一消息格式"""
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
                
                element = create_message_element(msg['type'], msg['data'], self.logger)
                if element:
                    message_elements.append(element)
            except Exception as e:
                self.logger.error(f"Failed to convert message element: {e}")

        return IMMessage(
            sender=sender,
            message_elements=message_elements,
            raw_message=event
        )

    def convert_to_message_segment(self, message: IMMessage) -> list[MessageSegment]:
        """将统一消息格式转换为 OneBot 消息段列表"""
        segments = []
        
        segment_converters = {
            'text': lambda data: MessageSegment.text(data['text']),
            'mention': lambda data: MessageSegment.at(data['data']['target']['user_id']),
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
            try:
                data = element.to_dict()
                msg_type = data['type']
                
                if msg_type in segment_converters:
                    segment = segment_converters[msg_type](data)
                    segments.append(segment)
            except Exception as e:
                self.logger.error(f"Failed to convert message segment type {msg_type}: {e}")

        return segments

    async def _track_websocket(self, websocket):
        """跟踪WebSocket连接"""
        self._websocket_connections.add(websocket)
        try:
            yield
        finally:
            self._websocket_connections.remove(websocket)

    async def start(self):
        """启动适配器"""
        try:
            self.logger.info("Starting OneBot adapter")

            # 启动心跳检查任务
            self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
            
            # 获取 quart 应用实例
            app = self.bot._server_app
            
            # 添加WebSocket连接跟踪中间件
            original_handle_websocket = self.bot._handle_websocket
            
            @app.websocket('/')
            async def patched_websocket_handler(websocket):
                async with self._track_websocket(websocket):
                    await original_handle_websocket(websocket)
            
            # 挂载到主Web服务器
            self.mounted_path = self.config.webhook_url
            self.web_server.mount_app(self.mounted_path, app)
            
            # 标记为运行中
            self.is_running = True
            self.logger.info(f"OneBot adapter mounted at {self.mounted_path}")
        except Exception as e:
            self.logger.error(f"Failed to start OneBot adapter: {str(e)}")
            raise

    async def stop(self):
        """停止适配器"""
        try:
            # 标记为不再运行
            self.is_running = False
            
            # 1. 停止消息处理
            if hasattr(self.bot, '_bus'):
                self.bot._bus._subscribers.clear()  # 清除所有事件监听器
                # 等待所有正在处理的消息完成
                await asyncio.sleep(0.5)

            # 2. 停止心跳检查
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await asyncio.wait_for(self._heartbeat_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._heartbeat_task = None

            # 3. 关闭所有WebSocket连接
            for ws in list(self._websocket_connections):
                try:
                    await ws.close(code=1000)  # 正常关闭
                except Exception as e:
                    self.logger.warning(f"Error closing WebSocket: {e}")
            
            # 4. 从Web服务器卸载应用
            if self.mounted_path:
                # 找到并移除挂载的路由
                for mount in list(self.web_server.app.routes):
                    if hasattr(mount, "path") and mount.path == self.mounted_path:
                        self.web_server.app.routes.remove(mount)
                        break
            
            # 5. 清理状态
            self.heartbeat_states.clear()
            self._websocket_connections.clear()

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
        if not self.is_running:
            result = MessageResult()
            result.success = False
            result.error = "OneBot adapter is not running"
            return result
            
        result = MessageResult()
        try:
            # 只在发送者是 ChatSender 实例时才查询用户资料
            if isinstance(message.sender, ChatSender):
                try:
                    profile = await self.query_user_profile(message.sender)
                    self.logger.info(f"query profile result: {profile}")
                except Exception as e:
                    self.logger.error(f"query profile failed: {e}")

            segments = self.convert_to_message_segment(message)

            for i, segment in enumerate(segments):
                # 如果不是第一条消息,添加随机延时
                if i > 0:
                    # 获取消息内容长度(如果是文本)
                    content_length = len(str(segment)) if isinstance(segment, MessageSegment) else 10
                    # 根据内容长度和随机因子计算延时
                    duration = content_length * 0.1 + random.uniform(0.5, 1.5)
                    await asyncio.sleep(duration)

                if recipient.chat_type == ChatType.GROUP:
                    send_result = await self.bot.send_group_msg(
                        group_id=int(recipient.group_id),
                        message=segment
                    )
                else:
                    send_result = await self.bot.send_private_msg(
                        user_id=int(recipient.user_id),
                        message=segment
                    )

                result.message_id = send_result.get('message_id')
                result.raw_results.append({"action": "send", "result": send_result})

            return result

        except Exception as e:
            result.success = False
            result.error = f"Error in send_message: {str(e)}"
            return result

    async def send_at_message(self, group_id: str, user_id: str, message: str):
        """发送@消息"""
        if not self.is_running:
            self.logger.warning("OneBot adapter is not running, cannot send at message")
            return
            
        bot_sender = ChatSender.from_group_chat(
            user_id="<@bot>",
            group_id=group_id,
            display_name="Bot"
        )
        
        msg = IMMessage(
            sender=bot_sender,
            message_elements=[
                AtElement(user_id),
                TextMessage(" " + message)
            ]
        )
        
        recipient = ChatSender.from_group_chat(
            user_id="<@bot>",
            group_id=group_id,
            display_name="Bot"
        )
        
        await self.send_message(msg, recipient)

    async def mute_user(self, group_id: str, user_id: str, duration: int):
        """禁言用户"""
        if not self.is_running:
            self.logger.warning("OneBot adapter is not running, cannot mute user")
            return
            
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
        if not self.is_running:
            self.logger.warning("OneBot adapter is not running, cannot kick user")
            return
            
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
                self.logger.info(f"Fetching group member info for user_id={user_id} in group_id={group_id}")
                info = await self.bot.get_group_member_info(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    no_cache=True
                )
                self.logger.info(f"Raw group member info: {info}")
                profile = self._convert_group_member_info(info)
            # 获取用户信息
            else:
                self.logger.info(f"Fetching stranger info for user_id={user_id}")
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
            self.logger.error(f"Failed to get user profile for {chat_sender}: {e}", exc_info=True)
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
