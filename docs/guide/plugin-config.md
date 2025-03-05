---
title: 插件配置指南
outline: deep
---

# 插件配置指南 🔧

::: tip 重要提示
- 服务端配置方式（WebUI/配置文件）只需选择一种
- 客户端选择（NapCat/LLOneBot）只需选择一种
- IP地址选择说明:
  - 使用 `127.0.0.1`: 适用于框架与协议端在同一系统环境下
  - 使用 `0.0.0.0` 或实际IP: 适用于框架与协议端在不同系统环境下
  
应用场景示例:
- 同一设备: 框架与协议端都在同一台电脑上
- 不同设备: 
  - 框架运行在公网服务器，协议端在本地设备
  - 框架在内网设备1，协议端在内网设备2
:::
##  Onebot 服务端配置
Onebot 服务端指的是支持 Onebot 协议的协议服务端, 在本教程中指的是 `Kirara_AI` 的 `Onebot` 插件  
服务端开放 `WebSocket` 服务, 并配置 `WebSocket` 服务地址和端口  供客户端连接

### WebUI 配置
- 点击聊天平台管理, 进入聊天平台管理页面
- 点击右上角"添加适配器"按钮

![进入平台管理](/assets/connet/websocket-webui-step-1.png)

- 在弹出的适配器选择框中, 从下拉菜单选择"onebot"选项

![添加适配器](/assets/connet/websocket-webui-step-2.png)

在适配器配置页面, 填写以下信息:
- 名称: 为该适配器设置一个名称(随意填写)
- Heartbeat Interval: 心跳检测间隔(默认15秒检查一次连接)
- Host: 适配器开放地址
  - 使用127.0.0.1时仅允许本机设备内部连接
  - 使用0.0.0.0时允许设备内部与外部(内网及外网)连接
- Port: 适配器开放端口,用于协议端连接(注意避免与其他端口冲突)  

![选择onebot适配器](/assets/connet/websocket-webui-step-3.png)

- 填写完成后点击"确定"保存配置

![配置适配器](/assets/connet/websocket-webui-step-4.png)

<!-- ### 修改配置文件
::: warning 注意
WebUI 配置方式和修改配置文件方式, 只需要选择一种就行, 不要俩种都配置!  
WebUI 配置方式和修改配置文件方式, 只需要选择一种就行, 不要俩种都配置!  
WebUI 配置方式和修改配置文件方式, 只需要选择一种就行, 不要俩种都配置!  
:::

在项目目录下, 进入`data`目录, 修改`config.yaml`文件
```bash
# linux
vim data/config.yaml
# windows
notepad data/config.yaml
```

在`config.yaml`文件中, 找到`ims`配置项, 修改或添加`onebot`适配器配置:

```yaml
ims:
  - name: onebot  # [!code ++]
    enable: true  # [!code ++]
    adapter: onebot  # [!code ++]
    config:  # [!code ++]
      host: 0.0.0.0  # [!code ++] 
      port: '5545' # 这里的5545仅仅是示例值, 你可以修改为任意端口 [!code ++]
      access_token: ''  # [!code ++]
      heartbeat_interval: '15'  # [!code ++]
```

随后找到`plugins`配置项, 修改或添加`onebot`插件配置:

```yaml
plugins:
  enable:
  - im_onebot_adapters  # [!code ++]
``` -->

##  Onebot 客户端配置
Onebot 客户端指的是支持 Onebot 协议的客户端, 在本教程中指的运行在 `ntqq` 中的插件, 例如 `NapCat` 和 `LLOneBot`  
客户端通过 `WebSocket` 连接到服务端, 并上报自身消息

- [NepCat安装教程](https://napneko.github.io/guide/install)
- [LLOneBot安装教程](https://llonebot.github.io/zh-CN/guide/getting-started)

### NapCat 配置

- 点击"网络配置", 进入网络配置页面
- 点击右上角"新建"按钮

![进入网络配置](/assets/connet/NapCat/websocket-napcat-step-1.png)

- 在弹出的新建网络配置菜单中, 选择"Websocket客户端"选项

![选择Websocket客户端](/assets/connet/NapCat/websocket-napcat-step-2.png)

在Websocket客户端配置页面中:
  - 启用: 开启此配置
  - 名称: 填写任意名称(如 Kirara)
  - URL: 填写框架适配器开放地址和端口
    - 格式为: `ws://ip:端口/ws`
    - 示例: `ws://192.168.10.172:5455/ws`
    - 如果在同一设备上运行，可使用: `ws://127.0.0.1:5455/ws`
  - 上报自身消息: 开启此选项
  - Token: 保持为空
  - 心跳间隔: 30000
  - 重连间隔: 30000

![配置Websocket客户端](/assets/connet/NapCat/websocket-napcat-step-3.png)

5. 填写完成后点击"保存"按钮。当看到终端输出连接成功的日志时，表示配置完成

![连接成功](/assets/connet/NapCat/websocket-napcat-step-final.png)

### LLOneBot 配置

- 开启"是否启用 LLOneBot, 重启 QQ 后生效"
- 开启"是否启用 OneBot 协议"

![启用LLOneBot](/assets/connet/LLOneBot/websocket-llonebot-step-1.png)

- 启用反向 WebSocket 服务
  - 开启"启用反向WebSocket服务"
  - 在"反向WebSocket监听地址"中填写框架适配器开放地址和端口
     - 格式为: `ws://ip:端口/ws`
     - 如果在同一设备上运行，填写: `ws://127.0.0.1:5455/ws`
     - 如果在不同设备上运行，填写实际的 IP 地址
  - 点击"添加"按钮保存配置

![配置反向WebSocket](/assets/connet/LLOneBot/websocket-llonebot-step-2.png)

配置完成后重启 QQ，当看到终端输出连接成功的日志时，表示配置完成：

![连接成功](/assets/connet/LLOneBot/websocket-llonebot-step-final.png)
