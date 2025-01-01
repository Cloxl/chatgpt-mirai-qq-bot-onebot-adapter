import json
import re
from typing import Any, Dict, Union

from aiocqhttp import Event, Message

from framework.logger import get_logger

logger = get_logger("OneBot-EventFilter")


class EventFilter:
    def __init__(self, filter_file: str):
        """
        初始化事件过滤器

        Args:
            filter_file: 过滤规则文件路径
        """
        self.filter_rules = self._load_filter_rules(filter_file)

    def _load_filter_rules(self, filter_file: str) -> Dict:
        """
        加载过滤规则

        Args:
            filter_file: 过滤规则文件路径

        Returns:
            Dict: 过滤规则
        """
        try:
            with open(filter_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
                logger.info(f"过滤规则加载成功")
                return rules
        except FileNotFoundError:
            logger.warning(f"警告: 过滤规则文件 {filter_file} 不存在")
            return {}
        except json.JSONDecodeError:
            logger.error(f"错误: 过滤规则文件 {filter_file} 格式错误")
            return {}

    def _match_message(self, rule_value: Dict, message: Message) -> bool:
        """
        匹配消息内容

        Args:
            rule_value: 规则值
            message: 消息

        Returns:
            bool: 是否匹配
        """
        if '.type' in rule_value:
            # 匹配消息段类型
            return any(seg.type == rule_value['.type'] for seg in message)

        if '.text' in rule_value:
            # 匹配纯文本内容
            plain_text = message.extract_plain_text()
            text_rule = rule_value['.text']
            if isinstance(text_rule, dict):
                if '.regex' in text_rule:
                    return bool(re.search(text_rule['.regex'], plain_text))
                if '.contains' in text_rule:
                    return text_rule['.contains'] in plain_text
            return plain_text == text_rule

        if '.at' in rule_value:
            # 匹配是否@某人
            return any(seg.type == 'at' and str(seg.data['qq']) == str(rule_value['.at'])
                       for seg in message)

        if '.image' in rule_value:
            # 匹配是否包含图片
            return any(seg.type == 'image' for seg in message)

        return False

    def _match_operator(self, operator: str, rule_value: Any, event_value: Any) -> bool:
        """匹配操作符

        Args:
            operator: 操作符
            rule_value: 规则值
            event_value: 事件值

        Returns:
            bool: 是否匹配
        """
        # 操作符到处理函数的映射
        operators = {
            '.eq': lambda rv, ev: ev == rv,
            '.neq': lambda rv, ev: ev != rv,
            '.in': lambda rv, ev: (
                ev in rv if not isinstance(rv, str) 
                else isinstance(ev, str) and ev in rv
            ),
            '.contains': lambda rv, ev: (
                isinstance(ev, str) and 
                isinstance(rv, str) and 
                rv in ev
            ),
            '.regex': lambda rv, ev: (
                isinstance(ev, str) and 
                bool(re.search(rv, ev))
            ),
            '.not': lambda rv, ev: not self._match_rule(rv, ev),
            '.or': lambda rv, ev: any(
                self._match_rule(sub_rule, ev) 
                for sub_rule in rv
            ),
            '.and': lambda rv, ev: all(
                self._match_rule(sub_rule, ev) 
                for sub_rule in rv
            ),
            '.message': lambda rv, ev: self._match_message(rv, ev)
        }

        try:
            if operator in operators:
                return operators[operator](rule_value, event_value)
            logger.warning(f"Unknown operator: {operator}")
            return False
        except Exception as e:
            logger.error(f"Error matching operator {operator}: {e}")
            return False

    def _match_rule(self, rule: Dict, event_data: Dict) -> bool:
        """匹配规则

        Args:
            rule: 规则
            event_data: 事件数据

        Returns:
            bool: 是否匹配
        """
        for key, value in rule.items():
            if key.startswith('.'):
                # 处理运算符
                return self._match_operator(key, value, event_data)
            else:
                # 处理普通键值对
                if key not in event_data:
                    logger.debug(f"键 {key} 不在事件数据中")
                    return False
                if isinstance(value, dict):
                    if not self._match_rule(value, event_data[key]):
                        return False
                elif event_data[key] != value:
                    logger.debug(f"键值不匹配: {key}, 规则值: {value}, 事件值: {event_data[key]}")
                    return False
        return True

    def should_handle(self, event: Union[Dict, Event]) -> bool:
        """
        检查事件是否通过过滤规则

        Args:
            event: Event对象或事件数据字典

        Returns:
            bool: 是否通过过滤
        """
        if not self.filter_rules:
            return True

        # 如果传入的是 Event 对象，直接使用
        event_data = event if isinstance(event, dict) else dict(event)

        # 确保消息是 Message 对象
        if 'message' in event_data and not isinstance(event_data['message'], Message):
            event_data = event_data.copy()
            event_data['message'] = Message(event_data['message'])

        result = self._match_rule(self.filter_rules, event_data)
        logger.info(f"接收到用户: {event.user_id}, 发送的: {event.raw_message}. 事件过滤器过滤结果: {'通过' if result else '被过滤'}")
        return result
