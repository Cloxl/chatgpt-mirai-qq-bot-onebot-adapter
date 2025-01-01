# OneBot-adapter for ChatGPT-Mirai-QQ-Bot

本项目是 [ChatGPT-Mirai-QQ-Bot](https://github.com/lss233/chatgpt-mirai-qq-bot) 的一个插件，用于将OneBot协议的消息转换为ChatGPT-Mirai-QQ-Bot的消息格式。

## 安装

```bash
pip install chatgpt-mirai-qq-bot-onebot-adapter
```

## 使用

在 `config.yaml` 中的 `ims` 中添加以下内容：

```yaml
ims:
  enable:
    onebot: ['onebot-default']
    ... # 其他IM配置
  configs:
    onebot-default:
      host: '0.0.0.0'
      port: '5545'
      access_token: ''
      filter_file: 'filter.json'
      name: 'onebot'
      heartbeat_interval: '15000'    # 心跳间隔（毫秒）
      reconnect_interval: '3000'     # 重连间隔（毫秒）
    ... # 其他IM配置
```

什么是`filter.json`？

`filter.json` 是`事件过滤器`，用于过滤消息的规则文件，具体请参考 [CQHTTP-API](https://github.com/kyubotics/coolq-http-api/blob/master/docs/4.15/EventFilter.md)

## 项目工作原理
```mermaid
sequenceDiagram
    participant 客户端 as OneBot Client
    participant 适配器 as OneBotAdapter
    participant 过滤器 as EventFilter
    participant 消息处理 as MessageHandler
    participant 命令处理 as CommandHandler
    participant 消息转换 as MessageConverter

    客户端->>适配器: WebSocket消息
    适配器->>适配器: 处理消息事件
    适配器->>过滤器: 检查是否需要处理

    alt 通过过滤
        过滤器-->>适配器: 返回true
        适配器->>消息处理: 转换为统一消息格式
        消息处理-->>适配器: 返回Message对象
        Note over 适配器: 提取会话ID和文本内容
        适配器->>命令处理: 解析命令

        alt 是命令消息
            命令处理-->>适配器: 返回命令和参数
            适配器->>适配器: 处理命令
            Note over 适配器: 创建响应消息
        else 普通消息
            命令处理-->>适配器: 返回空字符串
            适配器->>适配器: 处理普通消息
        end

        Note over 适配器: 创建文本消息响应
        适配器->>消息转换: 转换为OneBot消息格式
        Note over 消息转换: 转换各种消息元素
        消息转换-->>适配器: 返回OneBot消息

        alt 私聊消息
            适配器->>客户端: 发送私聊消息
        else 群聊消息
            适配器->>客户端: 发送群聊消息
        end

        客户端-->>适配器: 消息发送完成

    else 被过滤
        过滤器-->>适配器: 返回false
        Note over 适配器: 忽略该消息
    end
```

## 开源协议

本项目基于 [ChatGPT-Mirai-QQ-Bot](https://github.com/lss233/chatgpt-mirai-qq-bot) 开发，遵循其 [开源协议](https://github.com/lss233/chatgpt-mirai-qq-bot/blob/master/LICENSE)

## 感谢

感谢 [ChatGPT-Mirai-QQ-Bot](https://github.com/lss233/chatgpt-mirai-qq-bot) 的作者 [lss233](https://github.com/lss233) 提供框架支持

感谢 [AIOCQHTTP](https://github.com/nonebot/aiocqhttp) 的作者 [nonebot](https://github.com/nonebot) 提供CQHTTP协议支持

