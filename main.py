import asyncio
import json
import os
from datetime import datetime

import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter, MessageChain
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star, register


@register()
class MCUpdateReminder(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.context = context
        self.config = config or {}
        
        self.sections = [
            {
                'name': 'fb_Beta',
                'url': 'https://minecraftfeedback.zendesk.com/api/v2/help_center/en-us/sections/360001185332/articles?per_page=5'
            },
            {
                'name': 'fb_Release',
                'url': 'https://minecraftfeedback.zendesk.com/api/v2/help_center/en-us/sections/360001186971/articles?per_page=5'
            }
        ]
        
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
        }
        
        self.poll_interval = self.config.get("poll_interval", 60)
        self.target_sessions = self.config.get("target_sessions", [])
        self.admin_ids = self.config.get("admin_ids", [])
        
        self.running = False
        self.task = None
        self.session = None
        
        # 数据持久化路径
        self.data_dir = os.path.join("data", "plugins", "astrbot_plugin_mc_update")
        self.data_file = os.path.join(self.data_dir, "mc_versions.json")
        
        # 跟踪上次推送的版本信息，不重复推送
        self.last_pushed_versions = {
            "fb_Beta": {"title": "", "url": ""},
            "fb_Release": {"title": "", "url": ""}
        }

    async def initialize(self):
        """插件初始化"""
        if self.admin_ids:
            logger.info(f"MC 更新提醒: 管理员 ID: {self.admin_ids}")
        
        logger.info(f"MC 更新提醒: 当前通知会话: {self.target_sessions}")
        
        # 创建数据目录
        self._ensure_data_dir()
        
        # 加载持久化的版本信息
        await self._load_data()
        
        # 初始化 HTTP 会话
        self.session = aiohttp.ClientSession(headers=self.headers)
        self.running = True
        
        # 启动前先初始化版本信息，不要在启动时推送
        await self._init_versions()
        
        # 启动轮询任务
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("MC 更新提醒插件已启动")

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            logger.debug(f"数据目录已准备: {self.data_dir}")
        except Exception as e:
            logger.error(f"创建数据目录失败: {e}")

    async def _load_data(self):
        """从文件加载持久化的版本信息"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_pushed_versions = data
                    logger.info(f"已加载持久化的版本信息")
            else:
                logger.debug(f"数据文件不存在，将使用默认值: {self.data_file}")
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            logger.warning("将使用默认的版本信息")

    async def _save_data(self):
        """保存版本信息到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_pushed_versions, f, ensure_ascii=False, indent=2)
                logger.debug(f"版本信息已保存到文件")
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")

    async def _init_versions(self):
        """初始化版本信息，不推送通知"""
        """在启动时获取当前版本，以便下次检查时比较"""
        for section in self.sections:
            try:
                data = await self._fetch_articles(section["url"])
                if data and data.get("title") and data.get("url"):
                    self.last_pushed_versions[section["name"]] = {
                        "title": data.get("title"),
                        "url": data.get("url")
                    }
                    logger.debug(f"已初始化 {section['name']} 版本: {data.get('title')}")
            except Exception as e:
                logger.error(f"初始化 {section['name']} 版本失败: {e}")
        
        # 初始化完成后保存数据
        await self._save_data()

    async def _fetch_articles(self, url: str) -> dict:
        """从API获取文章数据"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "articles" in data and data["articles"]:
                        latest = data["articles"][0]
                        return {
                            "title": latest.get("title", ""),
                            "url": latest.get("html_url", ""),
                            "updated_at": latest.get("updated_at", "")
                        }
        except Exception as e:
            logger.error(f"获取文章失败: {e}")
        return {"title": "获取失败", "url": "", "updated_at": ""}

    async def _poll_loop(self):
        """轮询循环"""
        while self.running:
            try:
                await self._check_updates()
            except Exception as e:
                logger.error(f"轮询过程中出错: {e}")
            
            await asyncio.sleep(self.poll_interval)

    async def _check_updates(self):
        """检查更新"""
        if not self.session:
            return
        
        for section in self.sections:
            try:
                data = await self._fetch_articles(section["url"])
                if data and data.get("title") and data.get("url"):
                    # 检查是否不同于上次推送的版本
                    last_version = self.last_pushed_versions.get(section["name"], {})
                    if last_version.get("title") != data.get("title") or last_version.get("url") != data.get("url"):
                        await self._send_notification(section["name"], data["title"], data["url"])
                        # 更新上次推送的版本
                        self.last_pushed_versions[section["name"]] = {
                            "title": data.get("title"),
                            "url": data.get("url")
                        }
                        # 保存更新到文件
                        await self._save_data()
                    else:
                        logger.debug(f"{section['name']} 版本未改变，无需推送")
            except Exception as e:
                logger.error(f"检查 {section['name']} 时出错: {e}")

    async def _send_notification(self, section_name: str, title: str, url: str):
        """发送通知"""
        message_text = f"Minecraft Feedback 发布了新的文章：\n\n标题：\n{title}\n\n链接：\n{url}"
        logger.info(f"MC 更新提醒: 检测到 {section_name} 有新更新, 开始推送通知")
        await self._send_to_all_sessions(message_text)

    @filter.command("mcupdate")
    async def manual_check(self, event: AstrMessageEvent, *args, **kwargs):
        """手动检查更新（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        await self._check_updates()
        yield event.plain_result("已完成手动检查 MC 更新")

    @filter.command("mcupdate_latest")
    async def show_latest(self, event: AstrMessageEvent, *args, **kwargs):
        """显示当前最新的正式版/测试版"""
        try:
            # 直接从API获取最新数据
            beta_data = await self._fetch_articles(self.sections[0]["url"])
            release_data = await self._fetch_articles(self.sections[1]["url"])
            
            message = f"""Minecraft Feedback 最新文章：

🔜 测试版 (Beta):
{beta_data.get('title', '获取失败')}
链接: {beta_data.get('url', '')}
更新时间: {beta_data.get('updated_at', '未知')}

🌟 正式版 (Release):
{release_data.get('title', '获取失败')}
链接: {release_data.get('url', '')}
更新时间: {release_data.get('updated_at', '未知')}"""
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取最新版本时出错: {e}")
            yield event.plain_result("获取最新版本信息时出错，请稍后再试")

    @filter.command("mcupdate_push_beta")
    async def push_beta(self, event: AstrMessageEvent, *args, **kwargs):
        """推送最新的测试版（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        try:
            # 直接从API获取最新数据
            beta_data = await self._fetch_articles(self.sections[0]["url"])
            
            if not beta_data.get("title") or not beta_data.get("url"):
                yield event.plain_result("错误：获取测试版数据失败")
                return
                
            message_text = f"Minecraft Feedback 发布了新的文章：\n\n🔜 测试版 (Beta):\n{beta_data['title']}\n\n链接:\n{beta_data['url']}"
            
            await self._send_to_all_sessions(message_text)
            yield event.plain_result("已向所有会话推送最新的测试版信息")
            
        except Exception as e:
            logger.error(f"推送测试版时出错: {e}")
            yield event.plain_result(f"推送测试版时出错: {e}")

    @filter.command("mcupdate_push_release")
    async def push_release(self, event: AstrMessageEvent, *args, **kwargs):
        """推送最新的正式版（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        try:
            # 直接从API获取最新数据
            release_data = await self._fetch_articles(self.sections[1]["url"])
            
            if not release_data.get("title") or not release_data.get("url"):
                yield event.plain_result("错误：获取正式版数据失败")
                return
                
            message_text = f"Minecraft Feedback 发布了新的文章：\n\n🌟 正式版 (Release):\n{release_data['title']}\n\n链接:\n{release_data['url']}"
            
            await self._send_to_all_sessions(message_text)
            yield event.plain_result("已向所有会话推送最新的正式版信息")
            
        except Exception as e:
            logger.error(f"推送正式版时出错: {e}")
            yield event.plain_result(f"推送正式版时出错: {e}")

    async def _send_to_all_sessions(self, message_text: str):
        """向所有会话发送消息"""
        if not self.target_sessions:
            logger.warning("未配置目标会话，不推送消息")
            return
        
        logger.info(f"开始推送消息到 {len(self.target_sessions)} 个会话")
        
        message_chain = MessageChain([Plain(message_text)])
        
        for session_id in self.target_sessions:
            try:
                logger.debug(f"正在向会话 {session_id} 推送消息...")
                result = await self.context.send_message(session_id, message_chain)
                logger.info(f"成功向 {session_id} 推送消息, 结果: {result}")
            except Exception as e:
                logger.error(f"向 {session_id} 推送消息失败: {type(e).__name__}: {e}", exc_info=True)

    @filter.command("mcupdate_add_session")
    async def add_session(self, event: AstrMessageEvent, *args, **kwargs):
        """添加会话到通知列表（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        session_id = event.unified_msg_origin
        
        if session_id not in self.target_sessions:
            self.target_sessions.append(session_id)
            self.config["target_sessions"] = self.target_sessions
            logger.info(f"MC 更新提醒: 已添加会话 {session_id} 到通知列表")
            yield event.plain_result(
                f"✅ 已添加此会话到通知列表。\n"
                f"会话 ID: {session_id}\n\n"
                "提示: 下次推送时将会向此会话发送通知。"
            )
        else:
            yield event.plain_result("⚠️ 此会话已在通知列表中")

    @filter.command("mcupdate_list_sessions")
    async def list_sessions(self, event: AstrMessageEvent, *args, **kwargs):
        """查看当前的通知会话列表"""
        if not self.target_sessions:
            yield event.plain_result("ℹ️ 当前没有添加任何会话。\n\n使用 /mcupdate_add_session 添加当前会话。")
        else:
            sessions_str = "\n".join([f"- {s}" for s in self.target_sessions])
            yield event.plain_result(f"📋 当前的通知会话列表：\n\n{sessions_str}")

    @filter.command("mcupdate_remove_session")
    async def remove_session(self, event: AstrMessageEvent, *args, **kwargs):
        """从通知列表移除会话（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        session_id = event.unified_msg_origin
        
        if session_id in self.target_sessions:
            self.target_sessions.remove(session_id)
            self.config["target_sessions"] = self.target_sessions
            logger.info(f"MC 更新提醒: 已从通知列表移除会话 {session_id}")
            yield event.plain_result(
                f"✅ 已从通知列表移除此会话。\n"
                f"会话 ID: {session_id}"
            )
        else:
            yield event.plain_result("⚠️ 此会话不在通知列表中")

    async def terminate(self):
        """插件卸载"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
        
        logger.info("MC 更新提醒插件已停止")
