#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import platform
import json
import shutil
import tempfile
import threading
import urllib.request
import zipfile
import time
from datetime import datetime
from functools import partial
import requests

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, 
    QGroupBox, QRadioButton, QButtonGroup, QFileDialog, 
    QSpinBox, QDoubleSpinBox, QSlider, QProgressBar,
    QMessageBox, QApplication, QCheckBox, QSplitter,
    QAction, QListWidget, QListWidgetItem, QInputDialog, QFormLayout, QGridLayout,
    QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSettings, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices, QFont, QFontMetrics, QTextCursor

from ui.role_dialog import RoleEditDialog

try:
    from ui.mac_style_helper import MacStyleHelper
except ImportError:
    # 创建一个假的MacStyleHelper类以避免导入错误
    class MacStyleHelper:
        @staticmethod
        def apply_button_style(*args, **kwargs): pass
        @staticmethod
        def apply_input_style(*args, **kwargs): pass
        @staticmethod
        def apply_text_area_style(*args, **kwargs): pass
        @staticmethod
        def apply_title_style(*args, **kwargs): pass
        @staticmethod
        def apply_status_style(*args, **kwargs): pass
        @staticmethod
        def apply_tab_style(*args, **kwargs): pass
        @staticmethod
        def apply_window_style(*args, **kwargs): pass

# 设置日志器
logger = logging.getLogger(__name__)

class UnifiedMainWindow(QMainWindow):
    """统一的主窗口类，结合语音助手和桌面宠物的UI"""
    
    # 添加来自main_window.py的必要信号
    speech_recognized_signal = pyqtSignal(str)
    response_received_signal = pyqtSignal(str)
    update_models_signal = pyqtSignal(list)
    update_chat_signal = pyqtSignal(str, str)  # (sender, message)
    update_status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)  # (title, message)
    speech_help_clicked = pyqtSignal()
    performance_tips_clicked = pyqtSignal()
    voice_diagnostic_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        self.settings = QSettings("AIVoiceAssistant", "VoiceAssistant")
        self.voice_assistant = None  # 将由main.py设置
        self.chat_history = []
        self.is_initializing = True
        
        # 设置窗口属性
        self.setWindowTitle("AI语音助手与桌面宠物")
        self.setMinimumSize(800, 600)
        
        # 创建中央小部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页小部件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各种标签页
        self.create_chat_tab()
        self.create_recognition_tab()
        self.create_role_tab()
        self.create_voice_tab()
        self.create_pet_control_tab()
        self.create_settings_tab()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        self.status_label = QLabel("准备就绪")
        self.statusBar().addPermanentWidget(self.status_label)
        
        # 创建菜单
        self.create_menus()
        
        # 创建UI组件别名，便于访问
        self._create_ui_aliases()
        
        # 连接自己的信号
        self.update_chat_signal.connect(self.update_chat)
        self.update_status_signal.connect(self.update_status)
        self.error_signal.connect(self.show_error)
        
        # 应用样式
        self._apply_stylesheet()
        
        # 设置窗口位置
        self.resize(950, 700)
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry(self)
        self.move(screen_rect.center() - self.rect().center())
        
        # 连接信号
        self.connect_signals()
        
        # 检查资源
        self.check_resources()
        
        # 延迟检查UI一致性，确保所有组件都已初始化
        QTimer.singleShot(500, self.check_ui_consistency)
        
        # 延迟加载角色列表
        QTimer.singleShot(1000, self.load_roles)
        
        # 完成初始化
        self.is_initializing = False
        logger.info("UI组件初始化完成")
        
    def _apply_stylesheet(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QPushButton {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #f8f8f8;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
    def create_chat_tab(self):
        """创建聊天标签页"""
        self.chat_tab = QWidget()
        chat_layout = QVBoxLayout(self.chat_tab)
        
        # 创建聊天历史区域
        self.chat_history_text = QTextEdit()
        self.chat_history_text.setReadOnly(True)
        self.chat_history_text.setPlaceholderText("聊天历史将显示在这里")
        chat_layout.addWidget(self.chat_history_text)
        
        # 创建输入区域
        input_layout = QHBoxLayout()
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("输入文字消息...")
        self.input_text.returnPressed.connect(self.on_send_clicked)
        
        # 创建按钮
        self.send_text_btn = self._create_button("发送", self.on_send_clicked, primary=True)
        self.start_listen_btn = self._create_button("开始聆听", self.on_start_listen_clicked)
        self.stop_listen_btn = self._create_button("停止聆听", self.on_stop_listen_clicked)
        self.stop_listen_btn.setEnabled(False)
        self.clear_chat_btn = self._create_button("清空聊天", self.on_clear_chat)
        
        # 添加到布局
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_text_btn)
        chat_layout.addLayout(input_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_listen_btn)
        button_layout.addWidget(self.stop_listen_btn)
        button_layout.addWidget(self.clear_chat_btn)
        chat_layout.addLayout(button_layout)
        
        self.tab_widget.addTab(self.chat_tab, "聊天")
        
    def create_pet_control_tab(self):
        """创建桌面宠物控制标签页"""
        self.pet_tab = QWidget()
        pet_layout = QVBoxLayout(self.pet_tab)
        
        # 添加说明文本
        info_label = QLabel("<h2>Live2D桌面宠物</h2><p>支持动作、物理效果和互动的桌面宠物系统</p>")
        info_label.setAlignment(Qt.AlignCenter)
        pet_layout.addWidget(info_label)
        
        # 创建按钮
        self.start_pet_btn = self._create_button("启动宠物", primary=True)
        self.stop_pet_btn = self._create_button("停止宠物")
        self.debug_pet_btn = self._create_button("调试宠物")
        self.pet_download_model_btn = self._create_button("下载宠物模型")
        
        # 创建布局
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_pet_btn)
        control_layout.addWidget(self.stop_pet_btn)
        
        debug_layout = QHBoxLayout()
        debug_layout.addWidget(self.debug_pet_btn)
        debug_layout.addWidget(self.pet_download_model_btn)
        
        # 添加到主布局
        pet_layout.addLayout(control_layout)
        pet_layout.addLayout(debug_layout)
        pet_layout.addStretch()
        
        self.tab_widget.addTab(self.pet_tab, "桌面宠物")
    
    def update_chat(self, sender, message, time_str=None):
        """更新聊天记录"""
        try:
            if not time_str:
                time_str = time.strftime("%H:%M:%S")
            
            if sender.lower() == "user":
                format_msg = f'<div style="margin: 10px 0; text-align: right;"><span style="background-color: #dcf8c6; padding: 8px 12px; border-radius: 10px; display: inline-block;"><b>你 ({time_str}):</b><br>{message}</span></div>'
            else:
                format_msg = f'<div style="margin: 10px 0;"><span style="background-color: #f1f0f0; padding: 8px 12px; border-radius: 10px; display: inline-block;"><b>助手 ({time_str}):</b><br>{message}</span></div>'
            
            # 更新聊天历史
            if hasattr(self, "chat_history_text"):
                cursor = self.chat_history_text.textCursor()
                cursor.movePosition(QTextCursor.End)
                cursor.insertHtml(format_msg)
                self.chat_history_text.setTextCursor(cursor)
                self.chat_history_text.ensureCursorVisible()
        except Exception as e:
            logger.error(f"更新聊天记录失败: {e}")
    
    def update_status(self, message):
        """更新状态栏信息"""
        try:
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.setText(message)
                self.statusBar().showMessage(message)
                logger.info(message)
        except Exception as e:
            logger.error(f"更新状态栏失败: {e}")
    
    def show_error(self, title, message):
        """显示错误对话框"""
        self._show_message_box(title, message, icon=QMessageBox.Critical)

    def on_clear_chat(self):
        """清空聊天记录"""
        if hasattr(self, "chat_history_text") and self.chat_history_text:
            self.chat_history_text.clear()
        self.chat_history = []
        self.update_status("聊天已清空")

    def update_role_list(self, role_names):
        """更新角色列表
        
        Args:
            role_names: 角色名称列表
        """
        try:
            # 更新角色列表
            if hasattr(self, 'role_list'):
                # 保存当前选择
                current_item = self.role_list.currentItem()
                current_role = current_item.text() if current_item else None
                
                # 更新列表
                self.role_list.clear()
                for name in role_names:
                    self.role_list.addItem(name)
                    
                # 尝试恢复原来的选择
                if current_role:
                    items = self.role_list.findItems(current_role, Qt.MatchExactly)
                    if items:
                        self.role_list.setCurrentItem(items[0])
            
            # 更新角色组合框
            if hasattr(self, 'role_combo'):
                # 保存当前选择
                current_role = self.role_combo.currentText() if self.role_combo.currentText() else None
                
                # 更新列表
                self.role_combo.clear()
                for name in role_names:
                    self.role_combo.addItem(name)
                    
                # 尝试恢复原来的选择
                if current_role:
                    index = self.role_combo.findText(current_role)
                    if index >= 0:
                        self.role_combo.setCurrentIndex(index)
                        
            logger.info(f"角色列表已更新，共{len(role_names)}个角色")
        except Exception as e:
            logger.error(f"更新角色列表失败: {e}")
            self.show_error("更新失败", f"无法更新角色列表: {str(e)}")
        
    def update_voice_list(self, voices):
        """更新语音列表
        
        Args:
            voices: 语音名称列表
        """
        try:
            if hasattr(self, 'voice_combo') and self.voice_combo:
                # 保存当前选择的语音
                current_voice = self.voice_combo.currentText() if self.voice_combo.currentText() else None
                
                # 更新列表
                self.voice_combo.clear()
                for voice in voices:
                    self.voice_combo.addItem(voice)
                    
                # 尝试恢复原来的选择
                if current_voice:
                    index = self.voice_combo.findText(current_voice)
                    if index >= 0:
                        self.voice_combo.setCurrentIndex(index)
                        
                logger.info(f"语音列表已更新，共{len(voices)}个语音")
        except Exception as e:
            logger.error(f"更新语音列表失败: {e}")
    
    def update_role_preview(self, role_data):
        """更新角色预览"""
        if not role_data:
            self.role_preview.clear()
            return
        
        # 构建预览文本
        preview = (
            f"<h3>{role_data['name']}</h3>"
            f"<p><b>性格特征:</b> {role_data['traits']}</p>"
            f"<p><b>说话风格:</b> {role_data['style']}</p>"
            f"<p><b>背景设定:</b> {role_data['background']}</p>"
            f"<p><b>规则:</b></p><ul>"
        )
        
        for rule in role_data['rules']:
            preview += f"<li>{rule}</li>"
        
        preview += "</ul>"
        
        self.role_preview.setHtml(preview)
    
    def on_role_selection_changed(self, row):
        """角色选择改变时的回调"""
        try:
            if hasattr(self, "role_list") and self.role_list.currentItem():
                role_name = self.role_list.currentItem().text()
                if hasattr(self, "voice_assistant") and self.voice_assistant:
                    if hasattr(self.voice_assistant, "role_manager"):
                        role = self.voice_assistant.role_manager.get_role(role_name)
                        if role:
                            # 预处理文本，避免在f-string中使用反斜杠
                            system_prompt = role['system_prompt'].replace('\n', '<br>')
                            description = role.get('description', '').replace('\n', '<br>')
                            
                            # 构建HTML模板
                            html_template = """
                            <div style="margin: 10px;">
                                <h3 style="color: #333;">{name}</h3>
                                <div style="margin: 10px 0;">
                                    <p><b>系统提示词:</b></p>
                                    <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                                        {system_prompt}
                                    </div>
                                </div>
                                {description_block}
                                {special_block}
                            </div>
                            """
                            
                            # 构建描述块
                            description_block = ""
                            if role.get('description'):
                                description_block = f"""
                                <div style="margin: 10px 0;">
                                    <p><b>描述:</b></p>
                                    <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
                                        {description}
                                    </div>
                                </div>
                                """
                            
                            # 构建特殊角色块
                            special_block = ""
                            if role.get('is_special'):
                                special_block = """
                                <div style="margin: 10px 0; padding: 10px; background-color: #e8f5e9; border-radius: 5px;">
                                    <p><i>这是一个特殊角色，具有特定的功能和限制。</i></p>
                                </div>
                                """
                            
                            # 组装最终的预览文本
                            preview_text = html_template.format(
                                name=role['name'],
                                system_prompt=system_prompt,
                                description_block=description_block,
                                special_block=special_block
                            )
                            
                            if hasattr(self, "role_preview"):
                                self.role_preview.setHtml(preview_text)
                            
                            # 同步组合框选择
                            if hasattr(self, "role_combo"):
                                index = self.role_combo.findText(role_name)
                                if index >= 0:
                                    self.role_combo.setCurrentIndex(index)
                                    
                            # 更新状态
                            self.update_status(f"当前角色: {role_name}")
        except Exception as e:
            logger.error(f"更新角色预览失败: {e}")
            self.show_error("预览错误", f"无法更新角色预览: {str(e)}")

    def update_api_ui_state(self, is_local=True):
        """根据API类型更新UI状态"""
        if is_local:
            self.local_api_btn.setChecked(True)
            self.api_key.setEnabled(False)
            # 如果当前显示的不是localhost地址，自动更新
            if not ('localhost' in self.ollama_url.text() or '127.0.0.1' in self.ollama_url.text()):
                self.ollama_url.setText("http://localhost:11434")
        else:
            self.remote_api_btn.setChecked(True)
            self.api_key.setEnabled(True)
            # 如果当前显示的是localhost地址，自动更新
            if 'localhost' in self.ollama_url.text() or '127.0.0.1' in self.ollama_url.text():
                self.ollama_url.setText("https://openrouter.ai/api/v1")
        
        # 更新提示标签
        font_size = 11 if len(self.ollama_url.text()) < 40 else 10
        self.api_url_hint.setStyleSheet(f"color: #666; font-size: {font_size}px;")

    def update_model_status(self, status):
        """更新模型状态"""
        if hasattr(self, 'model_status_label'):
            self.model_status_label.setText(f"模型状态: {status}")

    def update_local_models(self, model_type, models):
        """更新本地模型列表"""
        try:
            if model_type == "vosk" and hasattr(self, 'vosk_model_combo'):
                    self.vosk_model_combo.clear()
                    for model in models:
                        self.vosk_model_combo.addItem(f"{model}")
                    logger.info(f"更新了{len(models)}个Vosk模型")
            
            elif model_type == "whisper" and hasattr(self, 'whisper_model_combo'):
                    self.whisper_model_combo.clear()
                    for model in models:
                        self.whisper_model_combo.addItem(f"{model}")
                    logger.info(f"更新了{len(models)}个Whisper模型")
                
            # 确保UI刷新
            QApplication.processEvents()
            
        except Exception as e:
            logger.error(f"更新{model_type}模型列表UI失败: {str(e)}")

    def refresh_models(self, model_type):
        """刷新语音识别模型列表
        
        Args:
            model_type: 模型类型，"vosk"或"whisper"
        """
        try:
            # 获取本地模型
            models_dir = self.get_models_directory(model_type)
            if not models_dir:
                self.update_status(f"无法获取{model_type}模型目录")
                return []
            
            local_models = []
            
            if os.path.exists(models_dir):
                # 根据模型类型获取相应的文件
                if model_type == "vosk":
                    # 获取所有目录作为模型
                    local_models = [
                        d for d in os.listdir(models_dir) 
                        if os.path.isdir(os.path.join(models_dir, d))
                    ]
                    
                    # 添加[已下载]标记
                    local_models = [f"{model} [已下载]" for model in local_models]
                    
                    # 标准可下载模型列表
                    available_models = [
                        "vosk-model-small-cn-0.22",
                        "vosk-model-cn-0.22",
                        "vosk-model-small-en-us-0.15",
                        "vosk-model-en-us-0.22",
                        "vosk-model-small-fr-0.22",
                        "vosk-model-fr-0.22",
                        "vosk-model-small-de-0.15",
                        "vosk-model-de-0.21",
                        "vosk-model-small-ru-0.22",
                        "vosk-model-ru-0.22",
                        "vosk-model-ja-0.22"
                    ]
                    
                    # 添加未下载的可用模型
                    for model in available_models:
                        if not any(model in m for m in local_models):
                            local_models.append(f"{model} [可下载]")
                
                elif model_type == "whisper":
                    # 获取所有.pt或.bin文件
                    local_models = [
                        f for f in os.listdir(models_dir) 
                        if f.endswith('.pt') or f.endswith('.bin')
                    ]
                    
                    # 添加标准大小选项
                    standard_sizes = ["tiny", "base", "small", "medium", "large"]
                    for size in standard_sizes:
                        if not any(size in m for m in local_models):
                            local_models.append(f"{size} [可下载]")
            
            # 根据模型类型更新相应的组件
            if model_type == "vosk":
                if hasattr(self, 'vosk_model_combo'):
                    self.vosk_model_combo.clear()
                    for model in local_models:
                        self.vosk_model_combo.addItem(model)
                    logger.info(f"更新了{len(local_models)}个Vosk模型")
            elif model_type == "whisper":
                if hasattr(self, 'whisper_model_combo'):
                    self.whisper_model_combo.clear()
                    for model in local_models:
                        self.whisper_model_combo.addItem(model)
                    logger.info(f"更新了{len(local_models)}个Whisper模型")
            
            # 确保UI刷新
            QApplication.processEvents()
            
            self.update_status(f"已获取 {len(local_models)} 个 {model_type} 模型")
            return local_models
            
        except Exception as e:
            error_msg = f"刷新{model_type}模型失败: {e}"
            logger.error(error_msg)
            self.error_signal.emit("刷新失败", str(e))
            return []

    def download_model(self, model_type, model_name=None):
        """下载语音识别模型"""
        if not hasattr(self, "voice_assistant") or not self.voice_assistant:
            return False
        
        try:
            if not hasattr(self.voice_assistant, "audio_processor"):
                return False
            
            success = self.voice_assistant.audio_processor.download_model(model_type, model_name)
            if success:
                self.update_status("模型下载完成")
                # 刷新模型列表
                self.refresh_models(model_type)
                return True
            else:
                self.update_status("模型下载失败")
                return False
        except Exception as e:
            logger.error(f"下载模型失败: {e}")
            self.show_error("下载失败", f"无法下载模型: {str(e)}")
            return False

    def debug_ui_layout(self):
        """调试UI布局的方法"""
        try:
            debug_info = "=== UI调试信息 ===\n"
            
            # 打印所有标签页
            debug_info += f"标签页数量: {self.tab_widget.count()}\n"
            for i in range(self.tab_widget.count()):
                debug_info += f"标签页 {i}: {self.tab_widget.tabText(i)}\n"
            
            # 打印关键属性
            key_attrs = ["chat_tab", "settings_tab", "role_tab", "voice_tab", 
                         "recognition_tab", "dialog_tab", "send_text_btn", 
                         "start_listen_btn", "stop_listen_btn"]
            
            debug_info += "\n关键组件状态:\n"
            for attr in key_attrs:
                debug_info += f"属性 '{attr}' 存在: {hasattr(self, attr)}\n"
            
            # 打印UI别名
            debug_info += f"\nUI别名: {list(self.ui_aliases.keys())}\n"
            
            logger.info(debug_info)
            self._show_message_box("UI调试", "UI调试信息已记录到日志文件", debug_info)
        except Exception as e:
            logger.error(f"UI调试失败: {e}")
            self._show_message_box("调试错误", f"UI调试失败: {e}", icon=QMessageBox.Warning)

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 在这里可以添加关闭前的确认对话框或清理操作
        event.accept()

    # 辅助方法区域
    def _create_default_spinbox(self, min_val=0, max_val=100, default=0, suffix=""):
        """创建默认样式的数字输入框"""
        spinbox = QSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default)
        
        if suffix:
            spinbox.setSuffix(suffix)
        
        # 应用样式
        spinbox.setStyleSheet("""
            QSpinBox {
                border: 1px solid #CECED2;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
            }
        """)
        
        return spinbox

    def _create_default_double_spinbox(self, min_val=0.0, max_val=1.0, default=0.5, step=0.1, suffix=""):
        """创建默认样式的浮点数输入框"""
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default)
        spinbox.setSingleStep(step)
        
        if suffix:
            spinbox.setSuffix(suffix)
        
        # 应用样式
        spinbox.setStyleSheet("""
            QDoubleSpinBox {
                border: 1px solid #CECED2;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
            }
        """)
        
        return spinbox

    def on_start_listen_clicked(self):
        """处理开始聆听按钮点击事件"""
        try:
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if self.voice_assistant.start_listening():
                    self.update_status("正在聆听...")
                    # 更新按钮状态
                    if hasattr(self, "start_listen_btn"):
                        self.start_listen_btn.setEnabled(False)
                    if hasattr(self, "stop_listen_btn"):
                        self.stop_listen_btn.setEnabled(True)
            else:
                self.update_status("启动语音识别失败")
        except Exception as e:
            logger.error(f"开始聆听失败: {e}")
            self.show_error("聆听错误", f"开始聆听失败: {e}")

    def on_stop_listen_clicked(self):
        """处理停止聆听按钮点击事件"""
        try:
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if self.voice_assistant.stop_listening():
                    self.update_status("停止聆听")
                    # 更新按钮状态
                    if hasattr(self, "start_listen_btn"):
                        self.start_listen_btn.setEnabled(True)
                    if hasattr(self, "stop_listen_btn"):
                        self.stop_listen_btn.setEnabled(False)
            else:
                self.update_status("停止语音识别失败")
        except Exception as e:
            logger.error(f"停止聆听失败: {e}")
            self.show_error("聆听错误", f"停止聆听失败: {e}")

    def connect_signals(self):
        """连接所有信号"""
        try:
            # 常用信号连接
            button_connections = [
                ('send_text_btn', self.on_send_clicked),
                ('input_text', self.on_send_clicked, 'returnPressed'),
                ('start_listen_btn', self.on_start_listen_clicked),
                ('stop_listen_btn', self.on_stop_listen_clicked),
                ('clear_chat_btn', self.on_clear_chat),
                ('speech_recognition_help_btn', self.on_speech_help_clicked),
                ('voice_diagnostic_btn', self.on_voice_diagnostic_clicked),
                ('refresh_vosk_models_btn', self.on_refresh_vosk_models),
                ('download_model_btn', self.on_download_vosk_model),
                ('refresh_whisper_models_btn', self.on_refresh_whisper_models),
                ('download_whisper_btn', self.on_download_whisper_model),
                ('new_role_btn', self.on_new_role_clicked),
                ('edit_role_btn', self.on_edit_role_clicked),
                ('delete_role_btn', self.on_delete_role_clicked)
            ]
            
            for connection in button_connections:
                if len(connection) == 2:
                    btn_name, handler = connection
                    signal_name = 'clicked'
                else:
                    btn_name, handler, signal_name = connection
                    
                if hasattr(self, btn_name):
                    component = getattr(self, btn_name)
                    if component:
                        signal = getattr(component, signal_name) if hasattr(component, signal_name) else None
                        if signal and callable(signal):
                            self.safe_connect(signal, handler, f"{btn_name}.{signal_name}")
            
            # 连接语音识别模式切换信号
            if hasattr(self, 'recognition_cloud_btn'):
                self.recognition_cloud_btn.toggled.connect(lambda checked: self.on_recognition_mode_changed('cloud') if checked else None)
            if hasattr(self, 'recognition_vosk_btn'):
                self.recognition_vosk_btn.toggled.connect(lambda checked: self.on_recognition_mode_changed('vosk') if checked else None)
            if hasattr(self, 'recognition_whisper_btn'):
                self.recognition_whisper_btn.toggled.connect(lambda checked: self.on_recognition_mode_changed('whisper') if checked else None)
            
            # 连接角色列表选择变化信号
            if hasattr(self, 'role_list'):
                self.role_list.currentRowChanged.connect(self.on_role_selection_changed)
            
            # 连接角色组合框变化信号
            if hasattr(self, 'role_combo'):
                self.role_combo.currentIndexChanged.connect(self._on_role_combo_changed)
            
        except Exception as e:
            logger.error(f"连接信号失败: {e}")

    def on_recognition_mode_changed(self, mode):
        """处理语音识别模式切换"""
        if not hasattr(self, "voice_assistant") or not self.voice_assistant:
            return
        
        try:
            if not hasattr(self.voice_assistant, "audio_processor"):
                return
            
            # 检查模型初始化状态
            if mode in ["vosk", "whisper"]:
                if not self.voice_assistant.audio_processor._ensure_model_initialized():
                    self.update_status(f"初始化{mode}模型失败")
                    return
            
            # 设置识别模式
            if self.voice_assistant.audio_processor.set_recognition_mode(mode):
                # 更新UI状态
                self._update_recognition_ui_state(mode)
                self.update_status(f"已切换到{mode}识别模式")
                logger.info(f"语音识别模式已切换到: {mode}")
            else:
                self.show_error("切换失败", f"无法切换到{mode}识别模式")
        except Exception as e:
            logger.error(f"切换语音识别模式失败: {e}")
            self.show_error("切换失败", f"无法切换到{mode}识别模式: {str(e)}")

    def _update_recognition_ui_state(self, mode):
        """更新语音识别UI状态"""
        try:
            # 更新模型选择框状态
            if hasattr(self, 'vosk_model_combo'):
                self.vosk_model_combo.setEnabled(mode == 'vosk')
            if hasattr(self, 'whisper_model_combo'):
                self.whisper_model_combo.setEnabled(mode == 'whisper')
            
            # 更新下载按钮状态
            if hasattr(self, 'download_model_btn'):
                self.download_model_btn.setEnabled(mode == 'vosk')
            if hasattr(self, 'download_whisper_btn'):
                self.download_whisper_btn.setEnabled(mode == 'whisper')
            
            # 更新刷新按钮状态
            if hasattr(self, 'refresh_vosk_models_btn'):
                self.refresh_vosk_models_btn.setEnabled(mode == 'vosk')
            if hasattr(self, 'refresh_whisper_models_btn'):
                self.refresh_whisper_models_btn.setEnabled(mode == 'whisper')
        except Exception as e:
            logger.error(f"更新UI状态失败: {e}")

    def on_send_clicked(self):
        """处理发送按钮点击事件"""
        try:
            if hasattr(self, "input_text") and self.input_text:
                message = self.input_text.text().strip()
                if message:
                    # 显示用户消息到聊天窗口
                    self.update_chat("user", message)
                    
                    # 清空输入框
                    self.input_text.clear()
                    
                    # 如果语音助手存在，发送消息
                    if hasattr(self, "voice_assistant") and self.voice_assistant:
                        self.voice_assistant.process_text_input(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    def on_speech_help_clicked(self):
        """显示语音识别帮助"""
        help_text = """<h3>语音识别帮助</h3>
        <p>本应用支持三种语音识别模式:</p>
        <ul>
            <li><b>Vosk离线识别</b>: 不需要网络连接，但需要下载语音模型。</li>
            <li><b>Whisper离线识别</b>: 基于OpenAI的Whisper模型，准确度高但需要下载模型。</li>
            <li><b>云端识别</b>: 使用云服务进行语音识别，需要网络连接和API密钥。</li>
        </ul>
        <p><b>语音设置说明:</b></p>
        <ul>
            <li><b>最小能量阈值</b>: 决定声音需要多大才会被检测为语音，值越小越敏感。</li>
            <li><b>停顿阈值</b>: 多长的停顿被视为语音结束，单位为秒。</li>
            <li><b>最长聆听时间</b>: 每次最多聆听多少秒。</li>
        </ul>
        <p><b>如果遇到识别问题:</b></p>
        <ul>
            <li>确保麦克风已正确连接并设置为系统默认输入设备</li>
            <li>调整最小能量阈值 - 在安静环境中可以设置得更低</li>
            <li>确保已下载对应语言的模型</li>
            <li>尝试使用测试按钮检查麦克风和识别状态</li>
        </ul>
        <p><b>性能提示:</b></p>
        <ul>
            <li>Vosk小模型占用资源少但准确度略低</li>
            <li>高准确度的大模型会占用更多内存和处理能力</li>
            <li>如果电脑配置较低，建议使用小模型</li>
        </ul>
        """
        
        self._show_message_box("语音识别帮助", help_text)
        
        # 发射信号
        self.speech_help_clicked.emit()

    def on_voice_diagnostic_clicked(self):
        """语音诊断功能"""
        try:
            # 创建诊断信息
            system_info = f"操作系统: {platform.system()} {platform.version()}"
            python_info = f"Python版本: {platform.python_version()}"
            
            audio_devices = self._get_audio_devices_info()
            voice_components = self._get_voice_components_info()
            
            # 设置诊断信息
            diagnostic_info = f"{system_info}\n{python_info}\n\n音频设备信息:\n{audio_devices}\n\n语音组件状态:\n{voice_components}"
            
            # 创建诊断窗口
            self._show_message_box("语音系统诊断", "语音系统诊断结果:", diagnostic_info)
            
            # 发射信号
            self.voice_diagnostic_clicked.emit()
        except Exception as e:
            self._show_message_box("诊断错误", f"执行诊断时发生错误: {str(e)}", icon=QMessageBox.Warning)

    def _get_audio_devices_info(self):
        """获取音频设备信息"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            input_devices = []
            output_devices = []
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(f"{device_info['name']} (索引: {i})")
                if device_info['maxOutputChannels'] > 0:
                    output_devices.append(f"{device_info['name']} (索引: {i})")
            
            info = ""
            if input_devices:
                input_list = "\n".join(input_devices)
                info = f"输入设备:\n{input_list}\n\n输出设备:\n" + "\n".join(output_devices)
            
            # 获取默认设备
            try:
                default_input = p.get_default_input_device_info()['name']
                default_output = p.get_default_output_device_info()['name']
                info += f"\n\n默认输入设备: {default_input}\n默认输出设备: {default_output}"
            except Exception as e:
                info += f"\n\n获取默认设备失败: {str(e)}"
            
            p.terminate()
            return info
        except Exception as e:
            return f"获取音频设备信息失败: {str(e)}"

    def _get_voice_components_info(self):
        """获取语音组件信息"""
        components = [
            ("speech_recognition", "speech_recognition"),
            ("vosk", "vosk"),
            ("whisper", "whisper"),
            ("pyttsx3", "pyttsx3")
        ]
        
        info = ""
        missing_components = []
        
        for display_name, module_name in components:
            try:
                __import__(module_name)
                info += f"{display_name}: 已安装\n"
            except ImportError:
                missing_components.append(module_name)
                info += f"{display_name}: 未安装\n"
        
        if missing_components:
            install_command = f"pip install {' '.join(missing_components)}"
            info += f"\n缺少的组件安装命令:\n{install_command}"
        
        return info

    def _show_message_box(self, title, message, detailed_text=None, icon=QMessageBox.Information):
        """显示统一样式的消息框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        
        if detailed_text:
            msg_box.setDetailedText(detailed_text)
            
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        return msg_box.exec_()

    def update_ui_components(self, component_type, data_list, component_name=None):
        """统一的UI组件更新方法
        
        Args:
            component_type: 组件类型，如'role', 'voice', 'model', 'vosk', 'whisper'
            data_list: 要更新的数据列表
            component_name: 指定组件名称，若为None则使用默认名称
        """
        try:
            # 确定组件名称
            if component_name is None:
                if component_type == 'role':
                    component_name = 'role_combo'
                elif component_type == 'voice':
                    component_name = 'voice_combo'
                elif component_type == 'vosk':
                    component_name = 'vosk_model_combo'
                elif component_type == 'whisper':
                    component_name = 'whisper_model_combo'
                elif component_type == 'model':
                    component_name = 'model_combo'
            
            # 获取组件        
            if not hasattr(self, component_name):
                logger.warning(f"组件 {component_name} 不存在")
                return False
                
            component = getattr(self, component_name)
            if component is None:
                logger.warning(f"组件 {component_name} 为None")
                return False
            
            # 保存当前选择
            current_text = component.currentText() if component.currentText() else None
            
            # 更新列表
            component.clear()
            for item in data_list:
                component.addItem(str(item))
                
            # 尝试恢复原来的选择
            if current_text:
                index = component.findText(current_text)
                if index >= 0:
                    component.setCurrentIndex(index)
                    
            logger.info(f"已更新 {component_name}，共 {len(data_list)} 项")
            return True
        except Exception as e:
            logger.error(f"更新 {component_type} 失败: {e}")
            return False

    def safe_connect(self, signal, slot, description=""):
        """安全地连接信号和槽，避免重复连接"""
        try:
            # 尝试断开连接，如果成功则说明已连接
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                # 未连接，无需操作
                pass
            
            # 连接信号
            signal.connect(slot)
            return True
        except Exception as e:
            logger.error(f"连接信号失败({description}): {e}")
            return False

    def create_recognition_tab(self):
        """创建语音识别设置标签页"""
        # 创建语音识别标签页
        self.recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(self.recognition_tab)
        
        # 创建语音识别组
        recognition_group = QGroupBox("语音识别设置")
        recognition_form = QFormLayout()
        recognition_group.setLayout(recognition_form)
        
        # 创建选择语音识别类型的按钮组
        recognition_type_layout = QHBoxLayout()
        self.recognition_cloud_btn = QRadioButton("云端识别")
        self.recognition_vosk_btn = QRadioButton("Vosk本地识别")
        self.recognition_whisper_btn = QRadioButton("Whisper本地识别")
        
        # 设置默认选中
        self.recognition_vosk_btn.setChecked(True)
        
        recognition_type_layout.addWidget(self.recognition_cloud_btn)
        recognition_type_layout.addWidget(self.recognition_vosk_btn)
        recognition_type_layout.addWidget(self.recognition_whisper_btn)
        
        # 创建RadioButton容器组件
        radio_container = QWidget()
        radio_container.setLayout(recognition_type_layout)
        
        # 添加到表单布局
        recognition_form.addRow("识别类型:", radio_container)
        
        # 添加Vosk模型选择和刷新下载
        vosk_models_layout = QHBoxLayout()
        self.vosk_model_combo = QComboBox()
        self.refresh_vosk_models_btn = QPushButton("刷新")
        self.download_model_btn = QPushButton("下载模型")
        
        vosk_models_layout.addWidget(self.vosk_model_combo, 3)
        vosk_models_layout.addWidget(self.refresh_vosk_models_btn, 1)
        vosk_models_layout.addWidget(self.download_model_btn, 1)
        
        vosk_container = QWidget()
        vosk_container.setLayout(vosk_models_layout)
        recognition_form.addRow("Vosk模型:", vosk_container)
        
        # 添加Whisper模型选择和刷新下载
        whisper_models_layout = QHBoxLayout()
        self.whisper_model_combo = QComboBox()
        self.refresh_whisper_models_btn = QPushButton("刷新")
        self.download_whisper_btn = QPushButton("下载模型")
        
        whisper_models_layout.addWidget(self.whisper_model_combo, 3)
        whisper_models_layout.addWidget(self.refresh_whisper_models_btn, 1)
        whisper_models_layout.addWidget(self.download_whisper_btn, 1)
        
        whisper_container = QWidget()
        whisper_container.setLayout(whisper_models_layout)
        recognition_form.addRow("Whisper模型:", whisper_container)
        
        # 添加Whisper参数设置
        whisper_params_layout = QGridLayout()
        
        # 模型大小
        self.whisper_model_size_combo = QComboBox()
        self.whisper_model_size_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model_size_combo.setCurrentIndex(1)
        
        # 质量设置
        self.whisper_quality_combo = QComboBox()
        self.whisper_quality_combo.addItems(["standard", "high"])
        
        # 语言设置
        self.whisper_language_combo = QComboBox()
        self.whisper_language_combo.addItems(["auto", "zh", "en", "ja", "ko", "fr", "de", "es"])
        
        whisper_params_layout.addWidget(QLabel("大小:"), 0, 0)
        whisper_params_layout.addWidget(self.whisper_model_size_combo, 0, 1)
        whisper_params_layout.addWidget(QLabel("质量:"), 0, 2)
        whisper_params_layout.addWidget(self.whisper_quality_combo, 0, 3)
        whisper_params_layout.addWidget(QLabel("语言:"), 1, 0)
        whisper_params_layout.addWidget(self.whisper_language_combo, 1, 1, 1, 3)
        
        whisper_params_container = QWidget()
        whisper_params_container.setLayout(whisper_params_layout)
        recognition_form.addRow("Whisper参数:", whisper_params_container)
        
        # 添加灵敏度滑块
        sensitivity_layout = QHBoxLayout()
        self.vosk_sensitivity_slider = QSlider(Qt.Horizontal)
        self.vosk_sensitivity_slider.setMinimum(0)
        self.vosk_sensitivity_slider.setMaximum(100)
        self.vosk_sensitivity_slider.setValue(50)
        self.vosk_sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.vosk_sensitivity_slider.setTickInterval(10)
        
        sensitivity_label = QLabel("50")
        self.vosk_sensitivity_slider.valueChanged.connect(lambda v: sensitivity_label.setText(str(v)))
        
        sensitivity_layout.addWidget(self.vosk_sensitivity_slider)
        sensitivity_layout.addWidget(sensitivity_label)
        
        recognition_form.addRow("灵敏度:", sensitivity_layout)
        
        # 创建更多设置
        self.listen_timeout = self._create_default_spinbox(
            min_val=1, 
            max_val=30, 
            default=5, 
            suffix=" 秒"
        )
        self.energy_threshold = self._create_default_spinbox(
            min_val=100, 
            max_val=4000, 
            default=300
        )
        self.pause_threshold = self._create_default_double_spinbox(
            min_val=0.1, 
            max_val=3.0, 
            default=0.8, 
            step=0.1, 
            suffix=" 秒"
        )
        
        recognition_form.addRow("超时时间:", self.listen_timeout)
        recognition_form.addRow("能量阈值:", self.energy_threshold)
        recognition_form.addRow("暂停阈值:", self.pause_threshold)
        
        # 添加应用按钮
        self.apply_recognition_params_btn = QPushButton("应用设置")
        recognition_form.addRow("", self.apply_recognition_params_btn)
        
        # 添加到主布局
        recognition_layout.addWidget(recognition_group)
        
        # 创建按钮以便查看帮助信息
        help_layout = QHBoxLayout()
        self.speech_recognition_help_btn = QPushButton("语音识别帮助")
        self.voice_diagnostic_btn = QPushButton("语音诊断")
        
        help_layout.addWidget(self.speech_recognition_help_btn)
        help_layout.addWidget(self.voice_diagnostic_btn)
        help_layout.addStretch()
        
        recognition_layout.addLayout(help_layout)
        recognition_layout.addStretch()
        
        # 添加到标签页
        self.tab_widget.addTab(self.recognition_tab, "语音识别")
        logger.info("语音识别标签页创建完成")

    def create_role_tab(self):
        """创建角色标签页"""
        self.role_tab = QWidget()
        role_layout = QVBoxLayout(self.role_tab)
        
        # 创建角色列表
        self.role_list = QListWidget()
        
        # 创建按钮布局
        btn_layout = QHBoxLayout()
        
        self.new_role_btn = QPushButton("新建角色")
        self.edit_role_btn = QPushButton("编辑角色")
        self.delete_role_btn = QPushButton("删除角色")
        
        self.new_role_btn.setProperty("primary", True)
        
        btn_layout.addWidget(self.new_role_btn)
        btn_layout.addWidget(self.edit_role_btn)
        btn_layout.addWidget(self.delete_role_btn)
        
        # 创建当前角色选择
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("当前角色:"))
        self.role_combo = QComboBox()
        selection_layout.addWidget(self.role_combo)
        
        # 添加角色预览区域
        self.role_preview = QTextEdit()
        self.role_preview.setReadOnly(True)
        self.role_preview.setPlaceholderText("选择一个角色以查看详情")
        
        # 添加到布局
        role_layout.addLayout(selection_layout)
        role_layout.addWidget(self.role_list, 2)
        role_layout.addWidget(self.role_preview, 1)
        role_layout.addLayout(btn_layout)
        
        # 添加到标签页
        self.tab_widget.addTab(self.role_tab, "角色设置")
        
        # 初始化角色列表
        if hasattr(self, "voice_assistant") and self.voice_assistant:
            if hasattr(self.voice_assistant, "role_manager"):
                roles = self.voice_assistant.role_manager.get_all_roles()
                for role in roles:
                    self.role_list.addItem(role["name"])
                    self.role_combo.addItem(role["name"])
        
        logger.info("角色标签页创建完成")

    def create_voice_tab(self):
        """创建语音合成标签页"""
        self.voice_tab = QWidget()
        voice_layout = QVBoxLayout(self.voice_tab)
        
        # 创建语音引擎选择组
        engine_group = QGroupBox("语音引擎")
        engine_layout = QVBoxLayout(engine_group)
        
        # 创建引擎选择按钮
        self.system_voice_btn = QRadioButton("系统TTS")
        self.ai_voice_btn = QRadioButton("AI语音")
        self.chat_tts_btn = QRadioButton("ChatTTS")
        
        self.system_voice_btn.setChecked(True)
        
        engine_layout.addWidget(self.system_voice_btn)
        engine_layout.addWidget(self.ai_voice_btn)
        engine_layout.addWidget(self.chat_tts_btn)
        
        # 创建语音选择组
        voice_group = QGroupBox("语音设置")
        voice_form = QFormLayout(voice_group)
        
        # 添加语音选择
        self.voice_combo = QComboBox()
        voice_form.addRow("选择语音:", self.voice_combo)
        
        # 添加语速设置
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(50, 200)
        self.rate_slider.setValue(100)
        self.rate_slider.setTickPosition(QSlider.TicksBelow)
        self.rate_slider.setTickInterval(10)
        
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(self.rate_slider)
        self.rate_value_label = QLabel("100%")
        self.rate_slider.valueChanged.connect(
            lambda v: self.rate_value_label.setText(f"{int(v)}%")
        )
        rate_layout.addWidget(self.rate_value_label)
        voice_form.addRow("语速:", rate_layout)
        
        # 添加音量设置
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(10)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_slider)
        self.volume_value_label = QLabel("80%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_value_label.setText(f"{int(v)}%")
        )
        volume_layout.addWidget(self.volume_value_label)
        voice_form.addRow("音量:", volume_layout)
        
        # 添加ChatTTS路径设置
        chat_tts_path_layout = QHBoxLayout()
        self.chat_tts_path = QLineEdit()
        self.chat_tts_path.setPlaceholderText("ChatTTS路径...")
        self.chat_tts_browse_btn = QPushButton("浏览...")
        self.chat_tts_browse_btn.clicked.connect(self.on_browse_chat_tts)
        chat_tts_path_layout.addWidget(self.chat_tts_path)
        chat_tts_path_layout.addWidget(self.chat_tts_browse_btn)
        voice_form.addRow("ChatTTS路径:", chat_tts_path_layout)
        
        # 应用设置按钮
        self.apply_voice_settings_btn = QPushButton("应用语音设置")
        voice_form.addRow("", self.apply_voice_settings_btn)
        
        # 创建测试区域
        test_group = QGroupBox("测试语音")
        test_layout = QVBoxLayout(test_group)
        
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("输入要测试的文本...")
        
        self.test_voice_btn = QPushButton("测试发音")
        
        test_layout.addWidget(self.test_input)
        test_layout.addWidget(self.test_voice_btn)
        
        # 添加到布局
        voice_layout.addWidget(engine_group)
        voice_layout.addWidget(voice_group)
        voice_layout.addWidget(test_group)
        voice_layout.addStretch()
        
        # 添加到标签页
        self.tab_widget.addTab(self.voice_tab, "语音合成")
        logger.info("语音合成标签页创建完成")

    def on_browse_chat_tts(self):
        """浏览选择ChatTTS路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择ChatTTS目录")
        if folder:
            self.chat_tts_path.setText(folder)

    def create_settings_tab(self):
        """创建设置标签页"""
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        
        # 创建API设置组
        api_group = QGroupBox("API设置")
        api_layout = QVBoxLayout(api_group)
        
        # API类型选择
        api_type_layout = QHBoxLayout()
        api_type_layout.addWidget(QLabel("API类型:"))
        
        self.local_api_btn = QRadioButton("本地API")
        self.remote_api_btn = QRadioButton("远程API")
        
        self.local_api_btn.setChecked(True)
        
        api_type_layout.addWidget(self.local_api_btn)
        api_type_layout.addWidget(self.remote_api_btn)
        api_layout.addLayout(api_type_layout)
        
        # API URL设置
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Ollama URL:"))
        self.ollama_url = QLineEdit("http://localhost:11434")
        url_layout.addWidget(self.ollama_url)
        api_layout.addLayout(url_layout)
        
        # 提示说明
        self.api_url_hint = QLabel("输入本地Ollama服务地址或远程API地址")
        self.api_url_hint.setStyleSheet("color: #666; font-size: 11px;")
        api_layout.addWidget(self.api_url_hint)
        
        # API KEY设置
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        self.api_key = QLineEdit()
        self.api_key.setEnabled(False)  # 本地模式下禁用
        key_layout.addWidget(self.api_key)
        api_layout.addLayout(key_layout)
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo)
        self.refresh_models_btn = QPushButton("刷新")
        model_layout.addWidget(self.refresh_models_btn)
        api_layout.addLayout(model_layout)
        
        # 模型状态
        self.model_status_label = QLabel("模型状态: 未连接")
        api_layout.addWidget(self.model_status_label)
        
        # 应用按钮
        self.apply_api_settings_btn = QPushButton("应用设置")
        api_layout.addWidget(self.apply_api_settings_btn)
        
        # 添加到布局
        settings_layout.addWidget(api_group)
        settings_layout.addStretch()
        
        # 添加到标签页
        self.tab_widget.addTab(self.settings_tab, "设置")
        logger.info("设置标签页创建完成")

    def create_menus(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self.menuBar().addMenu("编辑")
        
        # 清空聊天动作
        clear_action = QAction("清空聊天", self)
        clear_action.setShortcut("Ctrl+Del")
        clear_action.triggered.connect(self.on_clear_chat)
        edit_menu.addAction(clear_action)
        
        # 工具菜单
        tools_menu = self.menuBar().addMenu("工具")
        
        # 语音诊断动作
        voice_diagnostic_action = QAction("语音诊断", self)
        voice_diagnostic_action.triggered.connect(self.on_voice_diagnostic_clicked)
        tools_menu.addAction(voice_diagnostic_action)
        
        # 语音帮助动作
        speech_help_action = QAction("语音识别帮助", self)
        speech_help_action.triggered.connect(self.on_speech_help_clicked)
        tools_menu.addAction(speech_help_action)
        
        # 调试UI布局
        debug_ui_action = QAction("调试UI布局", self)
        debug_ui_action.triggered.connect(self.debug_ui_layout)
        tools_menu.addAction(debug_ui_action)
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(lambda: self._show_message_box(
            "关于AI语音助手", 
            "AI语音助手与桌面宠物\n版本 1.0\n一个支持语音交互的AI助手应用"
        ))
        help_menu.addAction(about_action)
        
        logger.info("菜单创建完成")

    def _create_ui_aliases(self):
        """创建UI组件别名，便于访问"""
        # 定义需要访问的关键UI组件
        critical_components = [
            "chat_history_text", "input_text", "send_text_btn", 
            "start_listen_btn", "stop_listen_btn", "clear_chat_btn",
            "speech_recognition_help_btn", "voice_diagnostic_btn",
            "vosk_model_combo", "whisper_model_combo", 
            "refresh_vosk_models_btn", "download_model_btn",
            "refresh_whisper_models_btn", "download_whisper_btn"
        ]
        
        # 创建组件字典
        self.ui_aliases = {}
        
        # 扫描并添加组件到字典
        for attr_name in dir(self):
            # 跳过方法和私有属性
            if callable(getattr(self, attr_name)) or attr_name.startswith('_'):
                continue
                
            # 检查属性是否是UI组件
            attr = getattr(self, attr_name)
            if hasattr(attr, 'objectName') and not attr_name in self.ui_aliases:
                self.ui_aliases[attr_name] = attr
                
        # 设置其他别名
        aliases_map = {
            "chat_history": "chat_history_text",
            "send_button": "send_text_btn",
            "listen_button": "start_listen_btn",
            "stop_button": "stop_listen_btn",
            "clear_button": "clear_chat_btn",
            "voice_speed_spin": "rate_slider",
            "voice_volume_spin": "volume_slider"
        }
        
        for alias, actual in aliases_map.items():
            if hasattr(self, actual) and getattr(self, actual) is not None:
                setattr(self, alias, getattr(self, actual))
                
        # 确保关键组件存在
        missing = [name for name in critical_components 
                  if not hasattr(self, name) or getattr(self, name) is None]
        
        if missing:
            logger.warning(f"缺少关键UI组件: {', '.join(missing)}")
            
        logger.info(f"UI别名已创建，组件总数: {len(self.ui_aliases)}")

    def check_resources(self):
        """检查必要的资源文件和目录"""
        try:
            # 检查目录结构
            directories = [
                "models",
                "models/vosk",
                "models/whisper",
                "config",
                "logs"
            ]
            
            for directory in directories:
                dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), directory)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"已创建目录: {dir_path}")
                    
            # 检查配置文件
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json")
            if not os.path.exists(config_path):
                # 创建默认配置
                default_config = {
                    "voice": {
                        "engine": "system",
                        "rate": 100,
                        "volume": 80
                    },
                    "recognition": {
                        "type": "vosk",
                        "energy_threshold": 300,
                        "pause_threshold": 0.8,
                        "timeout": 5
                    }
                }
                
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"已创建默认配置文件: {config_path}")
            
            logger.info("资源检查完成")
        except Exception as e:
            logger.error(f"资源检查失败: {e}")

    def _create_button(self, text, handler=None, primary=False):
        """创建标准按钮"""
        button = QPushButton(text)
        
        if primary:
            button.setProperty("primary", True)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #007AFF;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #0069D9;
                }
                QPushButton:pressed {
                    background-color: #0062CC;
                }
            """)
        
        if handler:
            button.clicked.connect(handler)
            
        return button

    def load_roles(self):
        """加载角色列表"""
        try:
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if hasattr(self.voice_assistant, "role_manager"):
                    roles = self.voice_assistant.role_manager.get_all_roles()
                    # 更新角色列表
                    if hasattr(self, "role_list"):
                        self.role_list.clear()
                        for role in roles:
                            self.role_list.addItem(role["name"])
                        # 更新角色下拉框
                        self.update_role_list([role["name"] for role in roles])
                        logger.info(f"已加载{len(roles)}个角色")
        except Exception as e:
            logger.error(f"加载角色列表失败: {e}")
            self.show_error("加载失败", f"无法加载角色列表: {str(e)}")

    def check_recognition_mode(self):
        """检查当前识别模式的状态"""
        try:
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if hasattr(self.voice_assistant, "audio_processor"):
                    mode = self.voice_assistant.audio_processor.recognition_mode
                    # 检查模型初始化状态
                    if mode == "vosk" and not self.voice_assistant.audio_processor.vosk_model:
                        self.update_status("Vosk模型未初始化，请先下载模型")
                        return False
                    elif mode == "whisper" and not self.voice_assistant.audio_processor.whisper_model:
                        self.update_status("Whisper模型未初始化，请先下载模型")
                        return False
                    return True
            return False
        except Exception as e:
            logger.error(f"检查识别模式失败: {e}")
            return False

    def check_ui_consistency(self):
        """检查UI组件的一致性，避免错误访问"""
        try:
            required_components = [
                'start_listen_btn', 'stop_listen_btn', 'send_text_btn',
                'input_text', 'chat_history_text', 'tab_widget'
            ]
            
            missing = [c for c in required_components if not hasattr(self, c)]
            
            if missing:
                error_msg = f"缺少必要的UI组件: {', '.join(missing)}"
                logger.error(error_msg)
                return False
            
            # 检查按钮连接
            buttons_to_check = [
                ('refresh_vosk_models_btn', self.on_refresh_vosk_models),
                ('download_model_btn', self.on_download_vosk_model),
                ('speech_recognition_help_btn', self.on_speech_help_clicked),
                ('voice_diagnostic_btn', self.on_voice_diagnostic_clicked),
                ('start_listen_btn', self.on_start_listen_clicked),
                ('stop_listen_btn', self.on_stop_listen_clicked),
                ('send_text_btn', self.on_send_clicked),
                ('clear_chat_btn', self.on_clear_chat)
            ]
            
            for btn_name, handler in buttons_to_check:
                if hasattr(self, btn_name):
                    btn = getattr(self, btn_name)
                    if btn and not self._is_signal_connected(btn.clicked, handler):
                        btn.clicked.connect(handler)
                        logger.debug(f"已连接 {btn_name} 到对应处理函数")
            
            return True
        except Exception as e:
            logger.error(f"检查UI一致性失败: {e}")
            return False

    def _is_signal_connected(self, signal, slot):
        """检查信号是否已连接到指定的槽函数"""
        try:
            signal.disconnect(slot)
            signal.connect(slot)
            return True
        except TypeError:
            signal.connect(slot)
            return False
        except Exception:
            return False

    def on_refresh_vosk_models(self):
        """刷新Vosk模型列表"""
        try:
            models = self.refresh_models("vosk")
            if models:
                self.update_status(f"找到 {len(models)} 个Vosk模型")
                return True
            return False
        except Exception as e:
            logger.error(f"刷新Vosk模型列表失败: {e}")
            self.show_error("刷新失败", f"无法刷新Vosk模型列表: {str(e)}")
            return False

    def on_download_vosk_model(self):
        """下载Vosk模型"""
        try:
            # 获取当前选择的模型
            model_name = None
            if hasattr(self, "vosk_model_combo"):
                model_name = self.vosk_model_combo.currentText()
                if "[已下载]" in model_name:
                    model_name = model_name.split(" [已下载]")[0]
                elif "[可下载]" in model_name:
                    model_name = model_name.split(" [可下载]")[0]
            
            # 下载模型
            if self.download_vosk_model_directly(model_name):
                self.update_status("模型下载完成")
                # 刷新模型列表
                self.on_refresh_vosk_models()
                return True
            return False
        except Exception as e:
            logger.error(f"下载Vosk模型失败: {e}")
            self.show_error("下载失败", f"无法下载Vosk模型: {str(e)}")
            return False

    def on_refresh_whisper_models(self):
        """刷新Whisper模型列表"""
        try:
            models = self.refresh_models("whisper")
            if models:
                self.update_status(f"找到 {len(models)} 个Whisper模型")
                return True
            return False
        except Exception as e:
            logger.error(f"刷新Whisper模型列表失败: {e}")
            self.show_error("刷新失败", f"无法刷新Whisper模型列表: {str(e)}")
            return False

    def on_download_whisper_model(self):
        """下载Whisper模型"""
        try:
            # 获取当前选择的模型大小
            model_size = None
            if hasattr(self, "whisper_model_combo"):
                model_size = self.whisper_model_combo.currentText()
                if "[已下载]" in model_size:
                    model_size = model_size.split(" [已下载]")[0]
                elif "[可下载]" in model_size:
                    model_size = model_size.split(" [可下载]")[0]
            
            # 下载模型
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if hasattr(self.voice_assistant, "audio_processor"):
                    if self.voice_assistant.audio_processor.check_and_download_whisper(model_size):
                        self.update_status("模型下载完成")
                        # 刷新模型列表
                        self.on_refresh_whisper_models()
                        return True
            return False
        except Exception as e:
            logger.error(f"下载Whisper模型失败: {e}")
            self.show_error("下载失败", f"无法下载Whisper模型: {str(e)}")
            return False

    def get_voice_rate(self):
        """获取语音速率"""
        if self.has_ui_component("voice_speed_spin"):
            return int(self.main_window.voice_speed_spin.value())
        return 180

    def get_voice_volume(self):
        """获取语音音量"""
        if self.has_ui_component("voice_volume_spin"):
            return float(self.main_window.voice_volume_spin.value()) / 100.0
        return 0.9

    def get_listen_timeout(self):
        """获取监听超时时间"""
        if self.has_ui_component("listen_timeout"):
            return int(self.main_window.listen_timeout.value())
        return 5

    def get_energy_threshold(self):
        """获取能量阈值"""
        if self.has_ui_component("energy_threshold"):
            return int(self.main_window.energy_threshold.value())
        return 300

    def get_pause_threshold(self):
        """获取暂停阈值"""
        if self.has_ui_component("pause_threshold"):
            return float(self.main_window.pause_threshold.value())
        return 0.8

    def get_models_directory(self, model_type):
        """获取模型目录路径
        
        Args:
            model_type: 模型类型 ("vosk" 或 "whisper")
            
        Returns:
            str: 模型目录的完整路径
        """
        try:
            # 获取项目根目录
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 创建模型目录
            models_dir = os.path.join(root_dir, "models")
            if not os.path.exists(models_dir):
                os.makedirs(models_dir, exist_ok=True)
                logger.info(f"创建模型目录: {models_dir}")
            
            # 根据类型返回对应的子目录
            if model_type == "vosk":
                model_dir = os.path.join(models_dir, "vosk")
            elif model_type == "whisper":
                model_dir = os.path.join(models_dir, "whisper")
            else:
                logger.error(f"不支持的模型类型: {model_type}")
                return None
            
            # 确保子目录存在
            if not os.path.exists(model_dir):
                os.makedirs(model_dir, exist_ok=True)
                logger.info(f"创建{model_type}模型目录: {model_dir}")
            
            return model_dir
        except Exception as e:
            logger.error(f"获取模型目录失败: {e}")
            return None

    def download_vosk_model_directly(self, model_name):
        """直接下载指定的Vosk模型
        
        Args:
            model_name: 要下载的模型名称，如"vosk-model-small-cn-0.22"
            
        Returns:
            bool: 下载是否成功启动
        """
        try:
            self.update_status(f"准备下载模型: {model_name}")
            
            # 获取模型目录
            models_dir = self.get_models_directory("vosk")
            if not models_dir:
                raise Exception("无法获取模型目录")
            
            # 下载函数
            def download_thread():
                try:
                    # 设置下载参数
                    download_url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
                    temp_dir = tempfile.mkdtemp()
                    zip_path = os.path.join(temp_dir, f"{model_name}.zip")
                    
                    # 开始下载
                    self.update_status("正在下载模型...")
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(response.headers.get('content-length', 0))
                    block_size = 8192
                    downloaded = 0
                    
                    # 写入文件
                    with open(zip_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=block_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                # 更新进度
                                if total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    self.update_status(f"下载进度: {percent:.1f}%")
                    
                    # 解压文件
                    self.update_status("正在解压模型...")
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(models_dir)
                    
                    # 清理临时文件
                    shutil.rmtree(temp_dir)
                    self.update_status("模型下载完成")
                    
                    # 刷新模型列表
                    self.refresh_models("vosk")
                except Exception as e:
                    logger.error(f"下载过程中出错: {e}")
                    self.update_status(f"下载失败: {str(e)}")
                    self._show_message_box("下载错误", f"下载过程中出错: {str(e)}", icon=QMessageBox.Warning)
            
            # 启动下载线程
            thread = threading.Thread(target=download_thread)
            thread.daemon = True
            thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动下载失败: {e}")
            self._show_message_box("下载错误", f"无法启动下载: {str(e)}", icon=QMessageBox.Warning)
            return False
    
    def _on_role_combo_changed(self, index):
        """处理角色下拉框选择变化"""
        try:
            if hasattr(self, 'role_combo') and self.role_combo:
                role_name = self.role_combo.currentText()
                # 更新角色列表选择
                if hasattr(self, 'role_list'):
                    items = self.role_list.findItems(role_name, Qt.MatchExactly)
                    if items:
                        self.role_list.setCurrentItem(items[0])
                
                # 如果有语音助手，设置角色
                if hasattr(self, 'voice_assistant') and self.voice_assistant:
                    if hasattr(self.voice_assistant, 'set_role'):
                        self.voice_assistant.set_role(role_name)
        except Exception as e:
            logger.error(f"更新角色选择失败: {e}")
            
    def has_ui_component(self, component_name):
        """检查UI组件是否存在"""
        return hasattr(self, component_name) and getattr(self, component_name) is not None
    
    def on_new_role_clicked(self):
        """创建新角色"""
        try:
            dialog = RoleEditDialog(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                role_data = dialog.get_role_data()
                
                # 保存角色
                if hasattr(self, "voice_assistant") and self.voice_assistant:
                    if hasattr(self.voice_assistant, "role_manager"):
                        self.voice_assistant.role_manager.add_role(role_data)
                        
                        # 刷新角色列表
                        roles = self.voice_assistant.role_manager.get_all_roles()
                        self.update_role_list([role["name"] for role in roles])
                        
                        # 选择新添加的角色
                        if hasattr(self, "role_list"):
                            items = self.role_list.findItems(role_data["name"], Qt.MatchExactly)
                            if items:
                                self.role_list.setCurrentItem(items[0])
                        
                        self.update_status(f"已添加新角色: {role_data['name']}")
        except Exception as e:
            logger.error(f"创建角色失败: {e}")
            self.show_error("创建失败", f"无法创建新角色: {str(e)}")
            
    def on_edit_role_clicked(self):
        """编辑角色"""
        try:
            # 获取当前选择的角色
            if not hasattr(self, "role_list") or not self.role_list.currentItem():
                self.show_error("选择错误", "请先选择一个角色")
                return
                
            role_name = self.role_list.currentItem().text()
            
            # 获取角色数据
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                if hasattr(self.voice_assistant, "role_manager"):
                    role = self.voice_assistant.role_manager.get_role(role_name)
                    if role:
                        # 打开编辑对话框
                        dialog = RoleEditDialog(parent=self, role_data=role)
                        if dialog.exec_() == QDialog.Accepted:
                            updated_role = dialog.get_role_data()
                            
                            # 更新角色
                            self.voice_assistant.role_manager.update_role(updated_role)
                            
                            # 刷新角色列表
                            roles = self.voice_assistant.role_manager.get_all_roles()
                            self.update_role_list([role["name"] for role in roles])
                            
                            # 选择编辑后的角色
                            items = self.role_list.findItems(updated_role["name"], Qt.MatchExactly)
                            if items:
                                self.role_list.setCurrentItem(items[0])
                            
                            self.update_status(f"角色已更新: {updated_role['name']}")
        except Exception as e:
            logger.error(f"编辑角色失败: {e}")
            self.show_error("编辑失败", f"无法编辑角色: {str(e)}")
            
    def on_delete_role_clicked(self):
        """删除角色"""
        try:
            # 获取当前选择的角色
            if not hasattr(self, "role_list") or not self.role_list.currentItem():
                self.show_error("选择错误", "请先选择一个角色")
                return
                
            role_name = self.role_list.currentItem().text()
            
            # 确认删除
            confirm = QMessageBox.question(
                self, 
                "确认删除", 
                f"确定要删除角色 '{role_name}' 吗？此操作不可撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # 删除角色
                if hasattr(self, "voice_assistant") and self.voice_assistant:
                    if hasattr(self.voice_assistant, "role_manager"):
                        self.voice_assistant.role_manager.delete_role(role_name)
                        
                        # 刷新角色列表
                        roles = self.voice_assistant.role_manager.get_all_roles()
                        self.update_role_list([role["name"] for role in roles])
                        
                        self.update_status(f"角色已删除: {role_name}")
        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            self.show_error("删除失败", f"无法删除角色: {str(e)}")
    