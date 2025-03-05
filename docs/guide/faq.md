---
title: 插件配置指南
outline: deep
---

# 常见问题解答 ❓

## Onebot 适配器相关问题

### 端口被占用怎么办？

当遇到端口被占用的错误时，可以：

1. 查看端口占用情况:
```bash
# Windows
netstat -ano | findstr "5545"  # 替换为实际端口号
# Linux/Mac
lsof -i :5545  # 替换为实际端口号
```

2. 关闭占用端口的进程:
```bash
# Windows
taskkill /F /PID <进程ID>
# Linux/Mac
kill -9 <进程ID>
```

3. 或者修改配置文件，更换一个未被占用的端口

### 适配器报错导致程序无响应怎么办？

当遇到适配器报错导致程序卡死，`Ctrl+C` 无法停止的情况：

1. 强制终止进程:
```bash
# Windows
# 打开任务管理器，找到 Python 进程并结束
taskkill /F /IM python.exe

# Linux/Mac
pkill -9 python
# 或者
ps aux | grep python
kill -9 <进程ID>
```

2. 重启程序前的检查:
   - 确认端口未被占用
   - 检查配置文件是否正确
   - 确保之前的进程已完全关闭

::: warning 注意
- 强制关闭程序可能会导致数据丢失
- 建议定期备份重要的配置文件
- 如果频繁出现此问题，可以尝试：
  1. 更换端口号
  2. 检查网络连接
  3. 查看日志文件排查具体原因
:::

### 如何查看错误日志？

程序运行出错时，可以查看日志文件来定位问题：

```bash
cd logs
```
目录内按照日期生成日志文件，例如：
```bash
log_2025-03-02.log
```
如果自己解决不了, 请详细描述你做了什么操作, 报错信息是什么, 放到[issue](https://github.com/Cloxl/chatgpt-mirai-qq-bot-onebot-adapter/issues/new)中, 或者联系我 cloxl996@outlook.com

常见错误码说明：
- `EADDRINUSE`: 端口被占用
- `ECONNREFUSED`: 连接被拒绝
- `ETIMEDOUT`: 连接超时
