#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QLabel, QLineEdit, QTextEdit, QPushButton, 
                            QListWidget, QListWidgetItem, QMessageBox, QDialogButtonBox)
from PyQt5.QtCore import Qt
from logger import logger

class RoleEditDialog(QDialog):
    """角色编辑对话框"""
    
    def __init__(self, parent=None, role=None):
        super().__init__(parent)
        
        self.role = role  # 如果是编辑现有角色则不为None
        self.init_ui()
        
        # 如果是编辑模式，填充已有数据
        if role:
            self.fill_role_data(role)
            
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("编辑角色" if self.role else "新建角色")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # 创建布局
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # 创建表单控件
        self.name_edit = QLineEdit()
        self.system_prompt_edit = QTextEdit()
        self.description_edit = QTextEdit()
        
        # 设置提示文本
        self.name_edit.setPlaceholderText("输入角色名称")
        self.system_prompt_edit.setPlaceholderText("输入系统提示词")
        self.description_edit.setPlaceholderText("输入角色描述（可选）")
        
        # 添加到表单布局
        form_layout.addRow("角色名称:", self.name_edit)
        form_layout.addRow("系统提示词:", self.system_prompt_edit)
        form_layout.addRow("角色描述:", self.description_edit)
        
        # 创建按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # 设置布局
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)
        
    def fill_role_data(self, role):
        """填充已有角色数据"""
        try:
            self.name_edit.setText(role.get("name", ""))
            self.system_prompt_edit.setText(role.get("system_prompt", ""))
            self.description_edit.setText(role.get("description", ""))
        except Exception as e:
            logger.error(f"填充角色数据失败: {e}")
            QMessageBox.warning(self, "警告", f"加载角色数据失败: {str(e)}")
            
    def get_role_data(self):
        """获取角色数据"""
        return {
            "name": self.name_edit.text().strip(),
            "system_prompt": self.system_prompt_edit.toPlainText().strip(),
            "description": self.description_edit.toPlainText().strip()
        }
        
    def accept(self):
        """确认按钮点击事件"""
        # 验证数据
        name = self.name_edit.text().strip()
        system_prompt = self.system_prompt_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "角色名称不能为空")
            return
            
        if not system_prompt:
            QMessageBox.warning(self, "错误", "系统提示词不能为空")
            return
            
        super().accept()