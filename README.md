# Minecraft 更新日志提醒插件

这是一个 AstrBot 插件，用于监控 Minecraft Feedback 的最新文章，并在有新文章时自动推送通知。

**版本**: v1.4.0

## 功能

- **定时轮询**：每隔指定时间检查 Minecraft Feedback Beta 和 Release 版本的最新文章
- **自动通知**：检测到新文章时，自动向配置的会话发送通知（包含标题和链接）
- **会话管理**：支持动态添加/移除通知会话
- **手动检查**：支持手动触发检查更新
- **查询最新版本**：支持查询当前最新的 Beta 和 Release 版本信息

## 安装

1. 将插件目录放在 AstrBot 的 `data/plugins/` 目录下
2. 在 AstrBot WebUI 的插件管理页面安装此插件
3. 配置轮询间隔和目标会话

## 使用

### 命令

- `/mcupdate` - 手动检查 MC 更新（仅管理员）
- `/mcupdate_latest` - 显示当前最新的正式版/测试版
- `/mcupdate_add_session` - 添加当前会话到通知列表（仅管理员）
- `/mcupdate_list_sessions` - 查看当前的通知会话列表
- `/mcupdate_remove_session` - 从通知列表移除当前会话（仅管理员）
- `/mcupdate_push_beta` - 推送最新的测试版到所有会话（仅管理员）
- `/mcupdate_push_release` - 推送最新的正式版到所有会话（仅管理员）

### 配置

在 AstrBot WebUI 的插件配置页面配置以下项：

- **poll_interval**：轮询间隔（秒），默认 60 秒
- **target_sessions**：目标会话列表，可通过命令动态添加
- **admin_ids**：管理员 ID 列表，仅这些 ID 的用户可以执行管理员命令（如推送消息）

## 数据存储

插件数据存储在 `data/plugins/astrbot_plugin_mc_update/mc_versions.json` 文件中，包括：

- 最新的 Beta 版本文章信息（标题和链接）
- 最新的 Release 版本文章信息（标题和链接）
- 通知目标会话列表

数据文件格式：
```json
{
  "fb_Beta": {
    "title": "最新文章标题",
    "url": "文章链接"
  },
  "fb_Release": {
    "title": "最新文章标题",
    "url": "文章链接"
  },
  "target_sessions": []
}
```

## 依赖

- `aiohttp>=3.8.0` - 用于异步 HTTP 请求

## 许可证

MIT
