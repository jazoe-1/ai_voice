#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from logger import logger

# 数据采集助手的系统提示词
DATA_COLLECTOR_PROMPT = """你是一个专注于帮助用户个性化AI系统的数据采集助手。你的任务是引导用户进行有深度的对话，从而生成高质量的个性化训练数据。

请遵循以下指导原则：

1. 主动了解用户的兴趣领域、工作内容、日常活动和个人偏好
2. 鼓励用户详细解释他们的想法和需求，使用"能具体说说吗"、"有什么例子吗"等引导性问题
3. 引导对话涵盖用户特有的专业知识、偏好和习惯
4. 针对用户提到的个性化需求，主动提出适合的定制方案和建议
5. 记住用户提供的个人信息和偏好，并在后续对话中引用
6. 避免过于简短的回答，尽量提供详细、丰富的解释和建议
7. 对于用户的专业领域问题，请鼓励他们分享专业知识和个人经验
8. 询问用户的日常流程和习惯，以便更好地进行个性化定制

记住，你的目标是通过自然、流畅的对话，收集能够帮助AI系统理解这位特定用户的高质量数据。尽量让对话深入、详细且个性化，同时保持友好和自然。"""

class RoleManager:
    """角色管理器类"""
    
    def __init__(self, roles_file="roles.json"):
        """初始化角色管理器"""
        self.roles_file = roles_file
        self.roles = []
        self.load_roles()
    
    def load_roles(self):
        """加载角色配置"""
        try:
            if os.path.exists(self.roles_file):
                with open(self.roles_file, "r", encoding="utf-8") as f:
                    self.roles = json.load(f)
                    logger.info(f"已加载 {len(self.roles)} 个角色")
                    
                # 确保特殊角色存在
                self._ensure_special_roles_exist()
            else:
                # 创建默认角色
                self.roles = [
                    {
                        "name": "助手",
                        "system_prompt": "你是一个有帮助、有礼貌的AI助手。你会提供有用、安全、道德的回答。",
                        "description": "默认助手角色"
                    },
                    {
                        "name": "诗人",
                        "system_prompt": "你是一位诗人，善于用优美的语言和丰富的想象力创作诗歌。回答用户问题时，尽量用诗歌的形式。",
                        "description": "以诗歌形式回答问题的角色"
                    },
                    {
                        "name": "数据采集助手",
                        "system_prompt": DATA_COLLECTOR_PROMPT,
                        "description": "专注于引导用户提供高质量对话数据的助手",
                        "is_special": True,
                        "special_type": "data_collector"
                    }
                ]
                self.save_roles()
                logger.info("创建了默认角色配置")
        except Exception as e:
            logger.error(f"加载角色配置失败: {e}")
            # 确保至少有一个默认角色和数据采集助手
            self.roles = [
                {
                    "name": "默认助手",
                    "system_prompt": "你是一个有帮助的AI助手。",
                    "description": "基础助手角色"
                },
                {
                    "name": "数据采集助手",
                    "system_prompt": DATA_COLLECTOR_PROMPT,
                    "description": "专注于引导用户提供高质量对话数据的助手",
                    "is_special": True,
                    "special_type": "data_collector"
                }
            ]
    
    def _ensure_special_roles_exist(self):
        """确保特殊角色存在"""
        # 检查数据采集助手是否存在
        data_assistant = self.get_role("数据采集助手")
        
        if not data_assistant:
            # 创建数据采集助手角色
            special_role = {
                "name": "数据采集助手",
                "system_prompt": DATA_COLLECTOR_PROMPT,
                "description": "专注于引导用户提供高质量对话数据的助手",
                "is_special": True,
                "special_type": "data_collector"
            }
            self.roles.append(special_role)
            self.save_roles()
            logger.info("已添加数据采集助手角色")
        elif not data_assistant.get("is_special"):
            # 如果存在但没有特殊标记，添加标记
            data_assistant["is_special"] = True
            data_assistant["special_type"] = "data_collector"
            # 确保系统提示词是最新的
            data_assistant["system_prompt"] = DATA_COLLECTOR_PROMPT
            self.save_roles()
            logger.info("已更新数据采集助手角色")
    
    def save_roles(self):
        """保存角色配置"""
        try:
            with open(self.roles_file, "w", encoding="utf-8") as f:
                json.dump(self.roles, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.roles)} 个角色")
            return True
        except Exception as e:
            logger.error(f"保存角色配置失败: {e}")
            return False
    
    def get_all_roles(self):
        """获取所有角色"""
        return self.roles
    
    def get_role(self, name):
        """获取指定名称的角色"""
        for role in self.roles:
            if role.get("name") == name:
                return role
        return None
    
    def add_role(self, name, system_prompt, description=""):
        """添加新角色"""
        # 检查是否已存在同名角色
        if self.get_role(name):
            logger.warning(f"已存在同名角色: {name}")
            return False
        
        # 创建新角色
        new_role = {
            "name": name,
            "system_prompt": system_prompt,
            "description": description
        }
        
        # 添加到列表
        self.roles.append(new_role)
        
        # 保存配置
        return self.save_roles()
    
    def update_role(self, name, new_name=None, system_prompt=None, description=None):
        """更新角色"""
        # 查找角色
        role = self.get_role(name)
        if not role:
            logger.warning(f"角色不存在: {name}")
            return False
        
        # 检查是否为特殊角色且尝试更改名称
        if role.get("is_special") and new_name and new_name != name:
            logger.warning(f"不能更改特殊角色的名称: {name}")
            return False
        
        # 检查新名称是否与其他角色冲突
        if new_name and new_name != name and self.get_role(new_name):
            logger.warning(f"新名称与现有角色冲突: {new_name}")
            return False
        
        # 更新特殊角色时保留特殊属性
        is_special = role.get("is_special", False)
        special_type = role.get("special_type", None)
        
        # 更新角色
        if new_name:
            role["name"] = new_name
            
        if system_prompt is not None:
            # 对于数据采集助手，确保系统提示词包含必要的指导
            if is_special and special_type == "data_collector":
                # 允许更新，但保留一些核心指导原则
                if "引导用户提供高质量对话数据" not in system_prompt:
                    system_prompt = f"{system_prompt}\n\n记住，你的目标是收集高质量的个性化数据。"
            role["system_prompt"] = system_prompt
            
        if description is not None:
            role["description"] = description
        
        # 保存特殊属性
        if is_special:
            role["is_special"] = is_special
            role["special_type"] = special_type
        
        # 保存配置
        return self.save_roles()
    
    def delete_role(self, name):
        """删除角色"""
        # 查找角色
        role = self.get_role(name)
        if not role:
            logger.warning(f"角色不存在: {name}")
            return False
        
        # 检查是否为特殊角色
        if role.get("is_special"):
            logger.warning(f"无法删除特殊角色: {name}")
            return False
        
        # 确保至少保留一个角色
        if len(self.roles) <= 1:
            logger.warning("无法删除最后一个角色")
            return False
        
        # 删除角色
        self.roles.remove(role)
        
        # 保存配置
        return self.save_roles()