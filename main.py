# coding: utf-8
# Copyright (c) 2025 HuaEr DevGroup. Licensed under MIT.
import re
from pathlib import Path
from asyncio import to_thread, gather

from astrbot import logger
from astrbot.api.event import filter
from astrbot.api import AstrBotConfig
from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent as Event

from .tools import chat
from .tools import config as cc
from .tools.config import Information, Tools
from .tools.group import GroupManagement, GroupManager

# 权限响应器
perm_dec = filter.permission_type(filter.PermissionType.ADMIN)
even_pub_dec = filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
even_pri_dec = filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE)

@register(
    name="HuaEr聊天bot",
    author="HuaEr DevGroup",
    desc="基于SiliconFlow API的多组群聊天插件，支持人格设定、markdown显示、联网搜索、检索增强生成（RAG）等功能",
    version="2.2.1",
    repo="https://github.com/suizoe-cosine/astrbot-plugin-huaer-bot"
)
class HuaErBot(Star):
    """机器人类"""
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context, config)
        self.conf = config

        # 如果在仪表盘配置了apikey的话，则使用。
        if self.conf['API_keys']['LLM']: 
            cc.API_KEY = self.conf['API_keys']['LLM']
            chat.API_KEY = self.conf['API_keys']['LLM']
        if self.conf['API_keys']['SEA']: 
            cc.SAPI_KEY = self.conf['API_keys']['SEA']
            chat.SAPI_KEY = self.conf['API_keys']['SEA']

        # 初始化核心组件
        self.groupmanager = GroupManager()
        self.ID_symbol = None  # 管理员控制符号


    async def initialize(self):
        "初始化完成时打印模块信息"
        version_info = (
            f"\n{'='*40}\n"
            f" HuaEr bot Initialized\n"
            f" Version: {Information.full_version()}\n"
            f" Build Date: {Information.build_date()}\n"
            f"{'='*40}\n"
        )
        logger.info(version_info)

    def _get_group(self, group_id: str) -> GroupManagement:
        return self.groupmanager.get_group(group_id)
    
    def _is_superuser(self, user: str) -> bool:
        return True if user == "admin" else False

    def _get_info(self, event: Event) -> str:
        "获取事件对应的组编号"
        if (event.is_admin() and self.ID_symbol is not None):
            return self.ID_symbol
        elif not event.is_private_chat():
            return str(event.get_group_id())
        elif event.is_private_chat():
            return self.groupmanager.private_group_id

    def _check_access(self, event: Event) -> bool:
        "依据白名单鉴权"
        user_id = event.get_sender_id()
        group_id =  None if event.is_private_chat() else str(event.get_group_id())
        if group_id:
            return event.is_admin() and group_id in self.groupmanager.whitelist_manager.groups \
                or self.groupmanager.whitelist_manager._check_access(user_id, group_id, True)
        elif group_id == None:
            return event.is_admin() or self.groupmanager.whitelist_manager._check_access(user_id, group_id, False)
    

    # ===================== 对话事件组 =====================
    # 对话事件响应器定义
    # 对话功能的具体实现

    @filter.command("对话")
    async def handle_chat(self, event: Event):
        """核心功能，可设置调用限制，参见配置文件"""
        if not self._check_access(event):
            return
        yield event.plain_result(await self._get_group(self._get_info(event)).chat_handler.handle_chat(event, Tools._extract_args(event.get_message_str(), "对话")))

    @filter.command("MD")
    async def handle_markdown(self, event: Event):
        """markdown显示上一段回复，无历史记录或记忆体容量为0则无效"""
        if not self._check_access(event):
            return
        proc = await self._get_group(self._get_info(event)).chat_handler.handle_markdown()
        if isinstance(proc, str) and not proc.startswith("❌"):
            url = await self.html_render(proc, {})
            yield event.image_result(url)
        else:
            yield event.plain_result(proc)

    @filter.command("模型列表")
    async def handle_model_prompt(self, event: Event):
        """列出所有可选模型"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group("public").chat_handler.handle_model_prompt())

    @filter.command("模型设置")
    async def handle_model_setting(self, event: Event, content: str):# 这里只取输入的第一个数字
        """通过查看`模型列表`内容选定模型"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.handle_model_setting(content))

    @filter.command("思考")
    async def handle_switch_thinking(self, event: Event):
        """部分模型具备思考功能，此命令可设定是否显示思考内容 (switch型,即关闭时此命令会使其开启，反之亦然)"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.switch_thinking())

    @filter.command("联网搜索")
    async def handle_switch_search(self, event: Event):
        """是否启用联网搜索(switch)"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.switch_search())

    # ===================== 记忆事件组 =====================
    # 记忆事件响应器定义
    # 具体实现实则属于对话类

    @filter.command("RAGS")
    async def handle_switch_rag(self, event: Event):
        """开/关RAG功能(switch)"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.switch_rag())

    @filter.command("SSIN")
    async def handle_switch_ssin(self, event: Event):
        """是否存储搜索到的信息至RAG索引(switch)"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.switch_ssin())

    @filter.command("ALLIN")
    async def handle_switch_allin(self, event: Event):
        """是否存储所有对话内容至RAG索引(switch)"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.switch_allin())

    @filter.command("撤回")
    async def handle_recall_memory(self, event: Event):
        """撤回上一段对话记录，可在配置文件中设置限额，管理员（superuser）不受限制"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.handle_recall_memory(event.is_admin()))

    @filter.command("记忆添加")
    async def handle_add_memory(self, event: Event):
        """手动增加一段记忆，建议成对添加，多用户语境建议在内容前加上用户名或助手标识"""
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "记忆添加")
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.handle_add_memory(contents))

    @filter.command("记忆输出")
    async def handle_print_memory(self, event: Event):
        """输出目前记忆体的所有内容，方便调试"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.handle_print_memory())

    @filter.command("记忆清除")
    async def handle_clean_memory(self, event: Event):
        """清空记忆体"""
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).chat_handler.handle_clean_memory())

    @filter.command("RAG添加")
    async def handle_insert_rag(self, event: Event):
        """添加文档至RAG索引(多个内容可用空格分隔)"""
        if not self._check_access(event):
            return
        yield event.plain_result("开始插入，请稍等...")
        contents = Tools._extract_args(event.get_message_str(), "RAG添加")
        yield event.plain_result(await self._get_group(self._get_info(event)).chat_handler.handle_insert_index(contents))

    @filter.command("RAG删除")
    async def handle_delete_rag(self, event: Event):
        """从RAG索引删除文档(多个内容可用空格分隔)"""
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "RAG删除")
        yield event.plain_result(await self._get_group(self._get_info(event)).chat_handler.handle_delete_index(contents))

    @filter.command("RAG清空")
    async def handle_clear_rag(self, event: Event):
        """清空RAG索引，相当于清空RAG部分的记忆"""
        if not self._check_access(event):
            return
        yield event.plain_result(await self._get_group(self._get_info(event)).chat_handler.handle_clear_index())

    @filter.command("RAG保存")
    async def handle_save_rag(self, event: Event):
        """保存当前RAG索引内容"""
        if not self._check_access(event):
            return
        yield event.plain_result(await self._get_group(self._get_info(event)).chat_handler.handle_save_index())

    # ===================== 人格管理事件组 =====================
    # 人格管理响应器定义
    # 与bot行为相关的设定

    @filter.command("人格设置")
    async def handle_set_personality(self, event: Event, content: str):
        "设定一个人格吧！（会清空当前记忆）"
        if not self._check_access(event):
            return
        yield event.plain_result(await self._get_group(self._get_info(event)).personality_manager.handle_set_personality(content))

    @filter.command("人格储存")
    async def handle_save_persona(self, event: Event):
        "为人格取名后存储至指定文件夹（包括记忆）（参数位置不敏感）"
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "人格储存")
        yield event.plain_result(await self._get_group(self._get_info(event)).personality_manager.handle_save_persona(contents))

    @filter.command("人格列表")
    async def handle_list_persona(self, event: Event):
        "此群已经存储的人格（私有人格）或公共人格将被列出"
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).personality_manager.handle_list_persona())

    @filter.command("人格读取")
    async def handle_load_persona(self, event: Event):
        "通过查看 `人格列表`内容选定人格（参数位置不敏感）"
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "人格读取")
        yield event.plain_result(self._get_group(self._get_info(event)).personality_manager.handle_load_persona(contents))

    # ===================== 白名单管理事件组 =====================
    # 白名单管理响应器定义
    # 内置两种响应规则，参见配置文件

    @filter.command("用户白名单")
    async def handle_user_whitelist(self, event: Event):
        "操作用户白名单"
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "用户白名单")
        yield event.plain_result(await self.groupmanager.whitelist_manager.handle_user_whitelist(contents))

    @filter.command("群聊白名单")
    async def handle_group_whitelist(self, event: Event):
        "操作群聊白名单"
        if not self._check_access(event):
            return
        contents = Tools._extract_args(event.get_message_str(), "群聊白名单")
        response = await self.groupmanager.whitelist_manager.handle_group_whitelist(contents)
        info = Tools._parse_args(contents, "增加", "删除")
        if info:
            if info[1] == "增加":
                await self.groupmanager.add_group(info[0])
            elif info[1] == "删除":
                await self.groupmanager.remove_group(info[0])
        yield event.plain_result(response)

    # ===================== 组管理器事件组 =====================
    # 组管理器响应器定义
    # 对于每个群都会生成的管理容器

    @filter.command("保存配置")
    async def save_group(self, event: Event):
        "将此群的配置保存到自身配置文件中"
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).save_group())

    @filter.command("加载配置")
    async def load_group(self, event: Event):
        "加载此群自身的配置文件"
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).load_group())

    @filter.command("重置配置")
    async def reset_group(self, event: Event):
        "恢复默认配置"
        if not self._check_access(event):
            return
        yield event.plain_result(await self.groupmanager.reset_group(self._get_info(event)))

    # ===================== 文档命令组 =====================
    # 文档命令响应器定义
    # 信息文本

    @filter.command("readme")
    async def show_user_doc(self, event: Event):
        "用户文档"
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).show_user_doc())

    @filter.command("功能列表")
    async def show_dev_doc(self, event: Event):
        "列出指令表（精简版）"
        if not self._check_access(event):
            return
        yield event.plain_result(self._get_group(self._get_info(event)).show_dev_doc())

    # ===================== 总控函数组 =====================
    # 总控函数响应器定义
    # 见github主页备注一

    @filter.command("选择群聊")
    async def choose_group(self, event: Event):
        """控制群聊"""
        contents = Tools._extract_args(event.get_message_str(), "选择群聊")
        for string in contents:
            arg_text = string.strip()
            if match := re.search(r'\d+|public|private', arg_text):
                extracted_group = match.group()
                if extracted_group in self.groupmanager.groups:
                    self.ID_symbol = extracted_group
                    logger.info(f"当前组群：{self.ID_symbol}")
                    yield event.plain_result("✅ 选定成功")
                else:
                    logger.warning("组群号无效")
                    yield event.plain_result("⚠️ 组群号无效")
            else:
                logger.warning("未检测到组群号")
                yield event.plain_result("⚠️ 请输入组群号")

    @filter.command("退出群聊")
    async def exit_group(self, event: Event):
        """解控群聊"""
        if self.ID_symbol is not None:
            self.ID_symbol = None
            yield event.plain_result("✅ 解控成功")
        else:
            yield event.plain_result("⚠️ 当前没有选中的组群")

    
    async def terminate(self):
        """关闭时自动保存函数"""
        logger.info("检测到终止指令，自动保存中...")

        tasks = []
        for group in self.groupmanager.groups.values():
            tasks.append(to_thread(group.save_group))
            tasks.append(group.chat_handler.handle_save_index())

        results = await gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"保存任务失败: {result}")

        logger.info("保存完毕！")

# ===================================================
#                   项目落款 / Project Footer
# ===================================================
# 版本号 / Version: 2.2.2 (stable)
# 最新修改日期 / Last Modified: 2025年8月17日 / August 20, 2025
# 开发团队 / Development Team: 华尔开发组 / Huaer Development Group
# ---------------------------------------------------
# 版权声明 / Copyright: © 2025 华尔开发组 
#                  © 2025 Huaer DevGroup. 
# ---------------------------------------------------
# 开源协议 / License: MIT
# 代码仓库 / Repository: github.com/suizoe-cosine/astrbot_plugin_huaer_bot
# ---------------------------------------------------
# 联系方式 / Contact:
#   - 电子邮件 / Email: HuaEr_DevGroup@outlook.com
#   - Q群 / Forum: 1006249997
# ===================================================