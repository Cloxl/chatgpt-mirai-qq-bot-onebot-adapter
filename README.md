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
    onebot: ['onebot']
    ... # 其他IM配置
  configs:
    onebot:
      host: '0.0.0.0'             # OneBot服务器地址
      port: '5545'                # OneBot服务器端口
      access_token: ''            # OneBot服务器访问令牌
      heartbeat_interval: '15'    # 心跳间隔(秒)
    ... # 其他IM配置
```

## 项目工作原理
```mermaid
sequenceDiagram
    participant Client as OneBot Client
    participant Adapter as OneBotAdapter
    participant Dispatcher as WorkflowDispatcher
    participant Memory as MemorySystem
    participant LLM as LLMService

    Client->>Adapter: WebSocket消息
    Note over Adapter: 心跳检测
    
    alt 元事件
        Adapter->>Adapter: _handle_meta
        Note over Adapter: 更新连接状态
    else 消息事件
        Adapter->>Adapter: _handle_msg
        Adapter->>Adapter: convert_to_message
        Note over Adapter: 转换为IMMessage格式
        
        Adapter->>Dispatcher: dispatch
        
        alt 工作流匹配
            Dispatcher->>Memory: 查询历史记录
            Memory-->>Dispatcher: 返回对话历史
            Dispatcher->>LLM: 请求响应
            LLM-->>Dispatcher: 返回AI回复
            Dispatcher-->>Adapter: 返回处理结果
            
            Adapter->>Adapter: convert_to_message_segment
            Note over Adapter: 转换为OneBot消息段
            
            loop 每个消息段
                Note over Adapter: 添加随机延时
                alt 群消息
                    Adapter->>Client: send_group_msg
                else 私聊消息
                    Adapter->>Client: send_private_msg
                end
            end
            
        else 无匹配工作流
            Note over Dispatcher: 跳过处理
        end
    end

    Client-->>Adapter: 消息处理完成
```

## 开源协议

本项目基于 [ChatGPT-Mirai-QQ-Bot](https://github.com/lss233/chatgpt-mirai-qq-bot) 开发，遵循其 [开源协议](https://github.com/lss233/chatgpt-mirai-qq-bot/blob/master/LICENSE)

## 感谢

感谢 [ChatGPT-Mirai-QQ-Bot](https://github.com/lss233/chatgpt-mirai-qq-bot) 的作者 [lss233](https://github.com/lss233) 提供框架支持

感谢 [AIOCQHTTP](https://github.com/nonebot/aiocqhttp) 的作者 [nonebot](https://github.com/nonebot) 提供CQHTTP协议支持

