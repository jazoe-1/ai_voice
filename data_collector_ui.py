#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PyQt5.QtWidgets import QMessageBox, QComboBox, QLabel, QAction, QPushButton
from PyQt5.QtCore import QSettings, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette
from logger import logger

class DataCollectorUI:
    """数据采集助手UI增强类"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.settings = QSettings("AI语音助手", "数据采集")
        
        # 创建图标
        self._create_icon()
        
        # 添加UI元素
        self._setup_ui()
    
    def _create_icon(self):
        """创建数据采集助手图标"""
        try:
            # 从资源目录加载图标，如果不存在则创建一个基本图标
            icon_path = os.path.join("resources", "data_collector.png")
            if os.path.exists(icon_path):
                self.icon = QIcon(icon_path)
            else:
                # 创建一个简单的彩色图标
                pixmap = QPixmap(16, 16)
                pixmap.fill(QColor(0, 120, 215))
                self.icon = QIcon(pixmap)
        except Exception as e:
            logger.error(f"创建数据采集助手图标失败: {e}")
            self.icon = None
    
    def _setup_ui(self):
        """设置UI元素"""
        # 当应用初始化完成后执行
        QTimer.singleShot(1000, self.enhance_role_selector)
        QTimer.singleShot(2000, self.show_first_time_tip)
    
    def enhance_role_selector(self):
        """增强角色选择器"""
        try:
            # 找到角色选择下拉框
            role_combo = self._find_role_combo()
            if not role_combo:
                return
            
            # 保存原始的角色切换方法
            if not hasattr(role_combo, 'originalCurrentIndexChanged'):
                role_combo.originalCurrentIndexChanged = role_combo.currentIndexChanged
            
            # 获取所有角色
            role_manager = getattr(self.main_window, 'role_manager', None)
            if not role_manager:
                return
                
            roles = role_manager.get_all_roles()
            
            # 给特殊角色添加图标和提示
            for i in range(role_combo.count()):
                role_name = role_combo.itemText(i)
                role = role_manager.get_role(role_name)
                
                if role and role.get("is_special") and self.icon:
                    role_combo.setItemIcon(i, self.icon)
                    
                    if role.get("special_type") == "data_collector":
                        role_combo.setItemData(
                            i, 
                            "此角色专注于优化个性化学习数据，帮助AI更好地理解您", 
                            Qt.ToolTipRole
                        )
            
            # 添加特殊处理 - 当切换到数据采集助手时显示提示
            def enhanced_index_changed(index):
                role_name = role_combo.itemText(index)
                role = role_manager.get_role(role_name)
                
                # 调用原始方法
                role_combo.originalCurrentIndexChanged.emit(index)
                
                # 如果是第一次切换到数据采集助手，显示提示
                if role and role.get("special_type") == "data_collector":
                    if not self.settings.value(f"data_collector_tip_shown_{role_name}", False):
                        QTimer.singleShot(500, lambda: self._show_collector_tip(role_name))
                        self.settings.setValue(f"data_collector_tip_shown_{role_name}", True)
            
            # 将信号连接到新方法
            role_combo.currentIndexChanged.disconnect()
            role_combo.currentIndexChanged.connect(enhanced_index_changed)
            
        except Exception as e:
            logger.error(f"增强角色选择器失败: {e}")
    
    def show_first_time_tip(self):
        """显示首次使用提示"""
        if not self.settings.value("data_collection_tip_shown", False):
            QMessageBox.information(self.main_window, 
                "个性化数据采集", 
                "您可以使用「数据采集助手」角色，它会引导您进行更有价值的对话，"
                "帮助AI更好地了解您的需求和偏好，从而提供更个性化的服务。\n\n"
                "您可以从角色选择下拉菜单中选择此角色。")
            self.settings.setValue("data_collection_tip_shown", True)
    
    def _show_collector_tip(self, role_name):
        """显示数据采集助手提示"""
        QMessageBox.information(self.main_window, 
            "数据采集助手已激活", 
            f"您已切换到「{role_name}」模式。\n\n"
            f"此模式下，AI会更专注于了解您的偏好和需求，"
            f"通过引导式对话收集高质量的个性化数据。\n\n"
            f"建议：尝试与AI深入讨论您的兴趣、工作和日常习惯，这将帮助系统更好地适应您。")
    
    def _find_role_combo(self):
        """查找角色选择下拉框"""
        # 在主窗口中查找QComboBox
        for child in self.main_window.findChildren(QComboBox):
            # 通过名称或内容判断是否为角色选择框
            if hasattr(child, 'objectName') and 'role' in child.objectName().lower():
                return child
            
            # 通过检查其内容
            for i in range(child.count()):
                if child.itemText(i) in ["助手", "诗人", "数据采集助手"]:
                    return child
        
        return None
    
    def suggest_data_collector(self, user_input):
        """基于用户输入建议切换到数据采集助手"""
        # 个性化指示词
        personalization_indicators = [
            "记住我的", "个性化", "自定义", "我喜欢", "适合我的", 
            "我的喜好", "我的习惯", "帮我设置", "了解我", "记得我"
        ]
        
        # 检查是否有个性化需求指示
        if any(indicator in user_input for indicator in personalization_indicators):
            # 获取当前角色
            role_manager = getattr(self.main_window, 'role_manager', None)
            if not role_manager:
                return
            
            current_role_name = getattr(self.main_window, 'current_role_name', None)
            if not current_role_name or current_role_name == "数据采集助手":
                return
                
            # 检查是否已经推荐过
            suggestion_key = "data_collector_suggested"
            if self.settings.value(suggestion_key, 0) >= 2:
                # 已经推荐过2次，不再推荐
                return
            
            # 显示推荐对话框
            response = QMessageBox.question(
                self.main_window,
                "个性化建议",
                "检测到您有个性化需求，是否切换到「数据采集助手」角色？\n\n"
                "这个特殊角色能更好地引导对话，收集您的偏好，提供更个性化的服务。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            # 更新推荐次数
            self.settings.setValue(suggestion_key, self.settings.value(suggestion_key, 0) + 1)
            
            if response == QMessageBox.Yes:
                # 查找角色选择器并切换
                combo = self._find_role_combo()
                if combo:
                    index = combo.findText("数据采集助手")
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        return True
        
        return False


def initialize_data_collector_ui(main_window):
    """初始化数据采集助手UI"""
    try:
        collector_ui = DataCollectorUI(main_window)
        main_window.data_collector_ui = collector_ui
        
        # 注册用户输入监听
        if hasattr(main_window, 'on_user_input'):
            original_on_input = main_window.on_user_input
            
            def enhanced_on_input(text):
                # 调用原始方法
                result = original_on_input(text)
                
                # 尝试提供数据采集助手建议
                collector_ui.suggest_data_collector(text)
                
                return result
            
            main_window.on_user_input = enhanced_on_input
        
        return collector_ui
    except Exception as e:
        logger.error(f"初始化数据采集助手UI失败: {e}")
        return None 