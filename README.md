# Minecraft 更新日志提醒插件

这是一个 AstrBot 插件，用于监控 Minecraft Feedback 的最新文章，并在有新文章时自动推送通知。

**版本**: v1.6.1

## 功能

- **定时轮询**：每隔指定时间检查 Minecraft Feedback Beta 和 Release 版本的最新文章
- **自动通知**：检测到新文章时，自动向配置的会话发送通知（包含标题和链接）
- **会话管理**：支持动态添加/移除通知会话
- **手动检查**：支持手动触发检查更新
- **查询最新版本**：支持查询当前最新的 Beta 和 Release 版本信息
- **多语言指令**：支持中文、英文和原始指令，完全兼容 QQ 官方机器人 API

## 安装

1. 将插件目录放在 AstrBot 的 `data/plugins/` 目录下
2. 在 AstrBot WebUI 的插件管理页面安装此插件
3. 配置轮询间隔和目标会话

## 使用

### 命令

每个指令都支持三种调用方式：原始指令、中文指令、英文指令。

| 原始指令 | 中文指令 | 英文指令 | 功能 |
|------------|----------|----------|--------|
| `/mcupdate` | `/检查更新` | `/check` | 手动检查 MC 更新（仅管理员） |
| `/mcupdate_latest` | `/最新文章` | `/latest` | 显示当前最新的正式版/测试版 |
| `/mcupdate_push_beta` | `/推送测试版` | `/pushbeta` | 推送最新的测试版到所有会话（仅管理员） |
| `/mcupdate_push_release` | `/推送正式版` | `/pushrelease` | 推送最新的正式版到所有会话（仅管理员） |
| `/mcupdate_add_session` | `/添加会话` | `/addsession` | 添加当前会话到通知列表（仅管理员） |
| `/mcupdate_list_sessions` | `/会话列表` | `/listsessions` | 查看当前的通知会话列表 |
| `/mcupdate_remove_session` | `/移除会话` | `/removesession` | 从通知列表移除当前会话（仅管理员） |

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

## 修复记录

### v1.6.0 (2025-11-16)
- 为所有指令添加中文和英文备用指令（別名）
- 完全兼容 QQ 官方機器人 API，不支持特殊符号
- 为每个指令添加详细的中文注释和描述
- 改进插件可用性，支持多种调用方式

### v1.5.0 (2025-11-15)
- 完全重构插件，修复 AstrBot 框架兼容性问题
- 优化代码结构，提高可维护性
- 改进错误处理和日志输出
- 优化消息格式，添加 emoji 表情

## 依赖

- `aiohttp>=3.8.0` - 用于异步 HTTP 请求

## 许可证

MIT
