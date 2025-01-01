from typing import Optional, Tuple


class CommandHandler:
    def parse_command(self, text: str) -> Tuple[str, str]:
        """解析命令和参数
        
        Args:
            text: 消息文本
            
        Returns:
            (command, args): 命令和参数
        """
        if not text.startswith('/'):
            return '', ''

        # 移除开头的 /
        text = text[1:]
        
        # 查找命令列表中的命令
        commands = ['test']
        for cmd in commands:
            if text.startswith(cmd):
                args = text[len(cmd):].strip()
                return cmd, args

        return '', ''
