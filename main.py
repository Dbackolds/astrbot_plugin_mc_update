import asyncio
import json
import os
from datetime import datetime

import aiohttp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain
from astrbot.api.star import Context, Star, register


@register("astrbot_plugin_mc_update", "Your Name", "Minecraft 更新日志提醒", "1.2.0")
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
        
        self.data_dir = os.path.join("data", "plugins", "astrbot_plugin_mc_update")
        self.data_file = os.path.join(self.data_dir, "mc_versions.json")
        
        self.poll_interval = self.config.get("poll_interval", 60)
        self.target_sessions = self.config.get("target_sessions", [])
        self.admin_ids = self.config.get("admin_ids", [])
        
        self.running = False
        self.task = None
        self.session = None

    async def initialize(self):
        """插件初始化"""
        os.makedirs(self.data_dir, exist_ok=True)
        self._init_data_file()
        
        data = self._load_data()
        if "target_sessions" in data:
            self.target_sessions = data["target_sessions"]
        
        if self.admin_ids:
            logger.info(f"MC 更新提醒: 管理员 ID: {self.admin_ids}")
        
        self.session = aiohttp.ClientSession(headers=self.headers)
        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("MC 更新提醒插件已启动")

    def _init_data_file(self):
        """初始化数据文件"""
        if not os.path.exists(self.data_file):
            initial_data = {
                "fb_Beta": {"title": "", "url": ""},
                "fb_Release": {"title": "", "url": ""},
                "target_sessions": []
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)

    def _load_data(self) -> dict:
        """加载数据"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            return {"fb_Beta": {"title": "", "url": ""}, "fb_Release": {"title": "", "url": ""}, "target_sessions": []}

    def _save_data(self, data: dict):
        """保存数据"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")

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
        
        data = self._load_data()
        
        for section in self.sections:
            try:
                async with self.session.get(section["url"], timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"API 请求失败: {resp.status}")
                        continue
                    
                    mcfb_json = await resp.json()
                    
                    if not mcfb_json.get("articles"):
                        logger.warning(f"{section['name']} 没有文章")
                        continue
                    
                    latest_article = mcfb_json["articles"][0]
                    latest_title = latest_article.get("name", "")
                    latest_url = latest_article.get("html_url", "")
                    
                    current_data = data.get(section["name"], {})
                    if isinstance(current_data, str):
                        current_data = {"title": "", "url": ""}
                    
                    if current_data.get("title") != latest_title:
                        logger.info(f"检测到 {section['name']} 有新文章: {latest_title}")
                        
                        await self._send_notification(section["name"], latest_title, latest_url)
                        
                        data[section["name"]] = {"title": latest_title, "url": latest_url}
                        self._save_data(data)
            
            except asyncio.TimeoutError:
                logger.warning(f"{section['name']} 请求超时")
            except Exception as e:
                logger.error(f"检查 {section['name']} 时出错: {e}")

    async def _send_notification(self, section_name: str, title: str, url: str):
        """发送通知"""
        message_text = f"Minecraft Feedback 发布了新的文章：\n\n标题：\n{title}\n\n链接：\n{url}"
        
        if self.target_sessions:
            for session_id in self.target_sessions:
                try:
                    await self.context.send_message(session_id, [Plain(message_text)])
                    logger.info(f"已向 {session_id} 发送通知")
                except Exception as e:
                    logger.error(f"向 {session_id} 发送消息失败: {e}")
        else:
            logger.info(f"未配置目标会话，不发送通知。消息内容: {message_text}")

    @filter.command("mcupdate")
    async def manual_check(self, event: AstrMessageEvent):
        """手动检查更新（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        await self._check_updates()
        yield event.plain_result("已完成手动检查 MC 更新")

    @filter.command("mcupdate_latest")
    async def show_latest(self, event: AstrMessageEvent):
        """显示当前最新的正式版/测试版"""
        data = self._load_data()
        
        beta_data = data.get("fb_Beta", {})
        release_data = data.get("fb_Release", {})
        
        if isinstance(beta_data, str):
            beta_data = {"title": "", "url": ""}
        if isinstance(release_data, str):
            release_data = {"title": "", "url": ""}
        
        beta_title = beta_data.get("title") or "暂无数据"
        beta_url = beta_data.get("url") or ""
        release_title = release_data.get("title") or "暂无数据"
        release_url = release_data.get("url") or ""
        
        message = f"""Minecraft Feedback 发布了新的文章：

🔜 测试版 (Beta):
{beta_title}
链接:
{beta_url}

🌟 正式版 (Release):
{release_title}
链接:
{release_url}"""
        
        yield event.plain_result(message)

    @filter.command("mcupdate_push_beta")
    async def push_beta(self, event: AstrMessageEvent):
        """推送最新的测试版（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        data = self._load_data()
        beta_data = data.get("fb_Beta", {})
        
        if isinstance(beta_data, str):
            beta_data = {"title": "", "url": ""}
        
        title = beta_data.get("title") or "暂无数据"
        url = beta_data.get("url") or ""
        
        message_text = f"Minecraft Feedback 发布了新的文章：\n\n🔜 测试版 (Beta):\n{title}\n\n链接:\n{url}"
        
        await self._send_to_all_sessions(message_text)
        yield event.plain_result("已向所有会话推送最新的测试版信息")

    @filter.command("mcupdate_push_release")
    async def push_release(self, event: AstrMessageEvent):
        """推送最新的正式版（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        data = self._load_data()
        release_data = data.get("fb_Release", {})
        
        if isinstance(release_data, str):
            release_data = {"title": "", "url": ""}
        
        title = release_data.get("title") or "暂无数据"
        url = release_data.get("url") or ""
        
        message_text = f"Minecraft Feedback 发布了新的文章：\n\n🌟 正式版 (Release):\n{title}\n\n链接:\n{url}"
        
        await self._send_to_all_sessions(message_text)
        yield event.plain_result("已向所有会话推送最新的正式版信息")

    async def _send_to_all_sessions(self, message_text: str):
        """向所有会话发送消息"""
        if self.target_sessions:
            for session_id in self.target_sessions:
                try:
                    await self.context.send_message(session_id, [Plain(message_text)])
                    logger.info(f"已向 {session_id} 推送消息")
                except Exception as e:
                    logger.error(f"向 {session_id} 推送消息失败: {e}")
        else:
            logger.info("未配置目标会话，不推送消息")

    @filter.command("mcupdate_add_session")
    async def add_session(self, event: AstrMessageEvent):
        """添加会话到通知列表（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        data = self._load_data()
        session_id = event.unified_msg_origin
        
        if "target_sessions" not in data:
            data["target_sessions"] = []
        
        if session_id not in data["target_sessions"]:
            data["target_sessions"].append(session_id)
            self._save_data(data)
            self.target_sessions = data["target_sessions"]
            logger.info(f"MC 更新提醒: 已添加会话 {session_id} 到通知列表")
            yield event.plain_result(f"已添加此会话到通知列表。\n会话 ID: {session_id}\n\n提示: 下次推送时将会向此会话发送通知。")
        else:
            yield event.plain_result(f"此会话已在通知列表中")

    @filter.command("mcupdate_list_sessions")
    async def list_sessions(self, event: AstrMessageEvent):
        """查看当前的通知会话列表"""
        data = self._load_data()
        sessions = data.get("target_sessions", [])
        
        if not sessions:
            yield event.plain_result("当前没有添加任何会话。\n\n使用 /mcupdate_add_session 添加当前会话。")
        else:
            sessions_str = "\n".join([f"- {s}" for s in sessions])
            yield event.plain_result(f"当前的通知会话列表：\n\n{sessions_str}")

    @filter.command("mcupdate_remove_session")
    async def remove_session(self, event: AstrMessageEvent):
        """从通知列表移除会话（仅管理员）"""
        sender_id = event.get_sender_id()
        if sender_id not in self.admin_ids:
            yield event.plain_result("你没有权限执行此操作")
            return
        
        data = self._load_data()
        session_id = event.unified_msg_origin
        
        if "target_sessions" not in data:
            data["target_sessions"] = []
        
        if session_id in data["target_sessions"]:
            data["target_sessions"].remove(session_id)
            self._save_data(data)
            self.target_sessions = data["target_sessions"]
            yield event.plain_result(f"已从通知列表移除此会话。会话 ID: {session_id}")
        else:
            yield event.plain_result(f"此会话不在通知列表中")

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
