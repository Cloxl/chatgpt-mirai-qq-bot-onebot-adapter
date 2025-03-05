---
title: 部署教程
outline: deep
---

# 部署教程

安装方式分为两种:
 -  WebUI 安装 (推荐)
 -  pip 安装

## WebUI 安装 (推荐) :rocket:

::: tip
最简单的方式, 一键完成安装!
:::

### 直接安装 :computer:
- 按照下图所示, 进入插件管理->插件市场->安装im_onebot_adapters
![安装步骤1](/assets/deploy/install-webui-default-step-1.png)

### 搜索安装 :mag:

如果首页没有onebot插件, 可以使用搜索安装
::: warning 注意!
直接安装和搜索安装, 只需要选择一种就行, 不是要执行两种安装方式!  
直接安装和搜索安装, 只需要选择一种就行, 不是要执行两种安装方式!  
直接安装和搜索安装, 只需要选择一种就行, 不是要执行两种安装方式!  
:::
- 进入插件管理->插件市场->搜索im_onebot_adapters->搜索
![搜索插件步骤1](/assets/deploy/install-webui-search-step-1.png)
- 搜索完成后, 点击安装
![搜索插件步骤2](/assets/deploy/install-webui-search-step-2.png)

### 视频教程 :video_camera:

<div class="video-container">
  <video 
    controls
    preload="none"
    width="100%"
    style="max-width: 100%; margin: 1rem auto; border-radius: 8px;"
  >
    <source src="/assets/deploy/install-webui-default.mp4" type="video/mp4">
    您的浏览器不支持 video 标签
  </video>
</div>

## pip 安装 📦
::: warning 注意!
WebUI 安装和 pip 安装, 只需要选择一种就行, 不要俩种都安装!  
WebUI 安装和 pip 安装, 只需要选择一种就行, 不要俩种都安装!  
WebUI 安装和 pip 安装, 只需要选择一种就行, 不要俩种都安装!  
:::

```bash
# 创建虚拟环境(推荐)
python -m venv venv

# 确保是 kirara-ai 运行时环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装 Onebot Adapters
pip install chatgpt-mirai-qq-bot-onebot-adapter

# 启动 kirara-ai
python -m kirara-ai
```

## 应用插件 :gear:
- 安装完成后, 进入插件管理->插件列表->启用im_onebot_adapters
![应用插件步骤1](/assets/deploy/install-webui-default-step-2.png)
- 也可以在插件管理->已安装插件->启用im_onebot_adapters
![应用插件步骤2](/assets/deploy/install-webui-other-apply.png)