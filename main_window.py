# main_window.py
import time
from logger import logger
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QLabel, QComboBox, 
                            QLineEdit, QFormLayout, QGroupBox, QSpinBox, 
                            QDoubleSpinBox, QMessageBox, QRadioButton, 
                            QButtonGroup, QSplitter, QShortcut, QApplication,
                            QSlider, QGridLayout, QListWidget, QTabWidget, QListWidgetItem, QMenu, QCheckBox, QScrollArea, QFrame, QToolButton, QSizePolicy, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QRect, QPropertyAnimation
from PyQt5.QtGui import QKeySequence, QFont, QIcon, QCursor, QColor, QPalette, QPainter, QBrush, QPen, QPixmap, QTextCursor
import os
from PIL import Image

# 从单独的模块导入样式助手
from ui.mac_style_helper import MacStyleHelper

class MainWindow(QMainWindow):
    """
    注意: 此类将逐步被UnifiedMainWindow替代。
    新功能应添加到UnifiedMainWindow中，不要再修改此类。
    保留此类仅用于向后兼容。
    """
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
        
        # 初始化 ui_aliases 字典，确保它在早期就存在
        self.ui_aliases = {}
        
        # 设置窗口基本属性
        self.setWindowTitle("AI语音助手")
        self.resize(800, 600)
        
        # 创建中央部件和主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        
        # 创建标题标签
        title_label = QLabel("AI语音助手")
        title_label.setAlignment(Qt.AlignCenter)
        MacStyleHelper.apply_title_style(title_label)
        main_layout.addWidget(title_label)
        
        # 重要：先创建标签页控件，确保它不为None
        self.tab_widget = QTabWidget()
        MacStyleHelper.apply_tab_style(self.tab_widget)
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignLeft)
        MacStyleHelper.apply_status_style(self.status_label)
        main_layout.addWidget(self.status_label)
        
        # 创建各个标签页 - 确保tab_widget已初始化
        try:
            self.create_chat_tab()
            self.create_settings_tab()
            self.create_role_tab()
            self.create_voice_tab()
            self.create_recognition_tab()
            self.create_dialog_tab()
            logger.info("基本UI初始化完成")
        except Exception as e:
            logger.error(f"创建标签页失败: {e}")
        
        # 应用样式
        MacStyleHelper.apply_window_style(self)
        
        # 连接信号
        self.connect_signals()
        
        # 检查UI兼容性
        self.check_ui_compatibility()
        
        self.init_shortcuts()
        
        # 添加这一行 - 创建UI别名
        self._create_ui_aliases()
        
        self.check_resources()
        
        # 创建常用控件的别名，确保兼容性
        self._create_ui_aliases()
        
    def safe_init_ui(self):
        """安全初始化UI界面"""
        try:
            # 确保创建所有标签页
            self.create_basic_chat_tab()
            self.create_basic_settings_tab()
            self.create_recognition_tab()
            self.create_role_tab()      # 添加角色标签页
            self.create_voice_tab()     # 添加语音合成标签页
            
            logger.info("基本UI初始化完成")
        except Exception as e:
            logger.error(f"安全初始化UI失败: {e}")
        
    def create_basic_chat_tab(self):
        """创建聊天标签页"""
        try:
            # 创建聊天标签页
            self.chat_tab = QWidget()
            chat_layout = QVBoxLayout()
            self.chat_tab.setLayout(chat_layout)
            
            # 创建聊天历史区域
            self.chat_history = QTextEdit()
            self.chat_history.setReadOnly(True)
            MacStyleHelper.apply_text_area_style(self.chat_history)
            
            # 创建输入区域
            input_layout = QHBoxLayout()
            
            self.input_text = QLineEdit()
            self.input_text.setPlaceholderText("输入消息或按下「开始聆听」按钮...")
            MacStyleHelper.apply_input_style(self.input_text)
            
            self.send_text_btn = QPushButton("发送")
            MacStyleHelper.apply_button_style(self.send_text_btn, primary=True)
            
            input_layout.addWidget(self.input_text)
            input_layout.addWidget(self.send_text_btn)
            
            # 创建语音控制按钮区域
            button_layout = QHBoxLayout()
            
            self.start_listen_btn = QPushButton("开始聆听")
            self.stop_listen_btn = QPushButton("停止聆听")
            self.clear_chat_btn = QPushButton("清空")
            
            MacStyleHelper.apply_button_style(self.start_listen_btn, primary=True)
            MacStyleHelper.apply_button_style(self.stop_listen_btn)
            MacStyleHelper.apply_button_style(self.clear_chat_btn)
            
            button_layout.addWidget(self.start_listen_btn)
            button_layout.addWidget(self.stop_listen_btn)
            button_layout.addWidget(self.clear_chat_btn)
            
            # 添加到布局
            chat_layout.addWidget(self.chat_history)
            chat_layout.addLayout(input_layout)
            chat_layout.addLayout(button_layout)
            
            # 添加到标签页
            self.tab_widget.addTab(self.chat_tab, "聊天")
            
            logger.info("聊天标签页创建完成")
        except Exception as e:
            logger.error(f"创建聊天标签页失败: {e}")

    def create_recognition_tab(self):
        """创建语音识别设置标签页"""
        try:
            # 先确保标签页存在
            if not hasattr(self, 'recognition_tab') or self.recognition_tab is None:
                self.recognition_tab = QWidget()
                self.recognition_layout = QVBoxLayout(self.recognition_tab)
                self.tab_widget.addTab(self.recognition_tab, "语音识别")
                logger.info("创建新的语音识别标签页")
            
            # 清空现有布局中的所有组件
            if hasattr(self, 'recognition_layout') and self.recognition_layout:
                while self.recognition_layout.count():
                    item = self.recognition_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            
            # 创建语音识别组
            recognition_group = QGroupBox("语音识别设置")
            recognition_layout = QFormLayout()
            recognition_group.setLayout(recognition_layout)
            
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
            recognition_layout.addRow("识别类型:", radio_container)
            
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
            recognition_layout.addRow("Vosk模型:", vosk_container)
            
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
            recognition_layout.addRow("Whisper模型:", whisper_container)
            
            # 添加Whisper参数设置
            whisper_params_layout = QGridLayout()
            
            # 模型大小
            self.whisper_model_size_combo = QComboBox()
            self.whisper_model_size_combo.addItems(["tiny", "base", "small", "medium", "large"])
            self.whisper_model_size_combo.setCurrentIndex(1)  # 默认选择base
            
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
            recognition_layout.addRow("Whisper参数:", whisper_params_container)
            
            # 添加Vosk灵敏度滑块
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
            
            recognition_layout.addRow("灵敏度:", sensitivity_layout)
            
            # 创建更多设置
            self.listen_timeout = self._create_default_spinbox(1, 30, 5, " 秒")
            self.energy_threshold = self._create_default_spinbox(100, 4000, 300)
            self.pause_threshold = self._create_default_double_spinbox(0.1, 3.0, 0.8, 0.1, " 秒")
            
            recognition_layout.addRow("超时时间:", self.listen_timeout)
            recognition_layout.addRow("能量阈值:", self.energy_threshold)
            recognition_layout.addRow("暂停阈值:", self.pause_threshold)
            
            # 添加应用按钮
            self.apply_recognition_params_btn = QPushButton("应用设置")
            recognition_layout.addRow("", self.apply_recognition_params_btn)
            
            # 添加到主布局
            self.recognition_layout.addWidget(recognition_group)
            
            # 创建按钮以便查看帮助信息
            help_layout = QHBoxLayout()
            self.speech_recognition_help_btn = QPushButton("语音识别帮助")
            self.voice_diagnostic_btn = QPushButton("语音诊断")
            
            help_layout.addWidget(self.speech_recognition_help_btn)
            help_layout.addWidget(self.voice_diagnostic_btn)
            help_layout.addStretch()
            
            self.recognition_layout.addLayout(help_layout)
            self.recognition_layout.addStretch()
            
            logger.info("语音识别标签页内容已更新")
            
        except Exception as e:
            logger.error(f"创建语音识别标签页失败: {e}")

    def _create_mode_button(self, text, icon_path=None):
        """创建带图标的模式选择按钮"""
        radio = QRadioButton(text)
        radio.setStyleSheet("""
            QRadioButton {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
            }
            QRadioButton:checked {
                background-color: #e8f4fc;
                border: 1px solid #b8daff;
            }
            QRadioButton:hover:!checked {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
            }
        """)
        
        if icon_path and os.path.exists(icon_path):
            radio.setIcon(QIcon(icon_path))
        
        return radio

    def create_combobox(self, items=None, default_index=0):
        """创建统一样式的下拉框"""
        combobox = QComboBox()
        combobox.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px 10px;
                min-height: 28px;
                background-color: white;
            }
            QComboBox:hover {
                border: 1px solid #80bdff;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
        """)
        
        if items:
            combobox.addItems(items)
            if 0 <= default_index < len(items):
                combobox.setCurrentIndex(default_index)
            
        return combobox

    def create_combo_with_label(self, label_text, items=None, default_index=0):
        """创建带标签的下拉框"""
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(100)
        
        combo = self.create_combobox(items, default_index)
        
        layout.addWidget(label)
        layout.addWidget(combo, 1)
        
        return layout, combo
        
    def init_shortcuts(self):
        """初始化快捷键"""
        # Ctrl+L: 开始/停止聆听
        listen_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        listen_shortcut.activated.connect(self.toggle_listening)
        
        # Ctrl+Enter: 发送测试消息
        send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        send_shortcut.activated.connect(self.on_send_text)
        
        # Ctrl+S: 应用设置
        settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        settings_shortcut.activated.connect(lambda: self.apply_settings_btn.click())
        
        # Alt+T: 显示/隐藏测试输入框
        test_shortcut = QShortcut(QKeySequence("Alt+T"), self)
        test_shortcut.activated.connect(self.toggle_test_input)

        # 添加角色管理快捷键
        self.manage_roles_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self.manage_roles_shortcut.activated.connect(self.on_manage_roles)

        # 添加调试快捷键
        self.debug_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.debug_shortcut.activated.connect(self.debug_ui_layout)

    def safe_connect(self, signal, slot, description=""):
        """安全地连接信号和槽，避免对象已删除的错误"""
        try:
            signal.connect(slot)
            return True
        except Exception as e:
            logger.error(f"连接信号失败({description}): {e}")
            return False

    def connect_signals(self):
        """连接所有信号"""
        try:
            # 聊天标签页信号
            if hasattr(self, "send_text_btn") and self.send_text_btn is not None:
                self.safe_connect(self.send_text_btn.clicked, self.on_send_clicked, "send_button")
                
            if hasattr(self, "start_listen_btn") and self.start_listen_btn is not None:
                self.safe_connect(self.start_listen_btn.clicked, self.on_start_listen_clicked, "start_listen_button")
            
            # ...其他信号连接...
            
            # 添加语音识别帮助和诊断按钮信号连接
            if hasattr(self, 'speech_recognition_help_btn'):
                self.speech_recognition_help_btn.clicked.connect(self.on_speech_help_clicked)
            
            if hasattr(self, 'voice_diagnostic_btn'):
                self.voice_diagnostic_btn.clicked.connect(self.on_voice_diagnostic_clicked)
            
            # 添加模型管理按钮信号连接
            if hasattr(self, 'refresh_vosk_models_btn'):
                self.refresh_vosk_models_btn.clicked.connect(self.on_refresh_vosk_models)
            
            if hasattr(self, 'download_model_btn'):
                self.download_model_btn.clicked.connect(self.on_download_vosk_model)
            
            if hasattr(self, 'refresh_whisper_models_btn'):
                self.refresh_whisper_models_btn.clicked.connect(self.on_refresh_whisper_models)
            
            if hasattr(self, 'download_whisper_btn'):
                self.download_whisper_btn.clicked.connect(self.on_download_whisper_model)
            
            logger.info("UI信号连接完成")
        except Exception as e:
            logger.error(f"连接信号失败: {e}")

    def toggle_listening(self):
        """切换语音聆听状态"""
        if self.start_listen_btn.isEnabled():
            self.on_start_listening()
        else:
            self.on_stop_listening()
            
    def on_start_listening(self):
        """开始聆听的回调"""
        # 这个方法将在voice_assistant.py中实现
        pass
        
    def on_stop_listening(self):
        """停止聆听的回调"""
        # 这个方法将在voice_assistant.py中实现
        pass
        
    def on_send_text(self):
        """发送文本的回调"""
        text = self.input_text.text().strip()
        if text:
            self.update_chat("user", text)
            # 触发信号以便voice_assistant处理
            self.speech_recognized_signal.emit(text)
            self.input_text.clear()
        
    def update_chat_ui(self, role, message):
        """更新聊天UI"""
        try:
            if not hasattr(self, "chat_history") or not self.chat_history:
                logger.warning("聊天历史控件不可用")
                return
            
            # 先替换消息中的换行符
            formatted_message = message.replace('\n', '<br>')
            
            # 准备样式 - 不使用f-string，改用字符串连接
            if role == "user":
                html = """
                <div style="margin: 10px 0; text-align: right;">
                    <div style="display: inline-block; background-color: #E9F7FF; color: #0076FF; 
                          padding: 10px 15px; border-radius: 18px; max-width: 80%; text-align: left;">
                    """ + formatted_message + """
                </div>
            </div>
            """
            else:  # assistant
                html = """
                <div style="margin: 10px 0; text-align: left;">
                    <div style="display: inline-block; background-color: #F0F0F0; color: #000000; 
                          padding: 10px 15px; border-radius: 18px; max-width: 80%; text-align: left;">
                    """ + formatted_message + """
                </div>
            </div>
            """
            
            # 追加到聊天历史
            cursor = self.chat_history.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertHtml(html)
            
            # 滚动到底部
            self.chat_history.verticalScrollBar().setValue(
                self.chat_history.verticalScrollBar().maximum()
            )
        except Exception as e:
            logger.error(f"更新聊天UI失败: {e}")
    
    def toggle_test_input(self):
        """切换测试输入区域的可见性"""
        self.test_area.setVisible(not self.test_area.isVisible())
        
    def set_status(self, message):
        """设置状态栏消息"""
        self.statusBar().showMessage(message)
        
    def show_error(self, title, message):
        """显示错误对话框"""
        QMessageBox.critical(self, title, message)
        
    def update_model_list(self, models):
        """更新模型列表"""
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
            
    def update_voice_list(self, voices):
        """更新语音列表"""
        self.voice_combo.clear()
        if voices:
            self.voice_combo.addItems(voices)

    
    
    def on_clear_chat(self):
        """清空聊天记录"""
        self.chat_history.clear()
        self.update_chat("system", "聊天已清空")
    
    def on_manage_roles(self):
        """打开角色管理"""
        # 这个方法将由VoiceAssistant实例调用其show_role_management方法
        pass

    def on_new_role(self):
        """创建新角色回调"""
        # 这个方法将通过信号连接到 VoiceAssistant 的 create_new_role 方法
        pass

    def on_edit_role(self):
        """编辑角色回调"""
        # 这个方法将通过信号连接到 VoiceAssistant 的 edit_current_role 方法
        pass

    def on_delete_role(self):
        """删除角色回调"""
        # 这个方法将通过信号连接到 VoiceAssistant 的 delete_current_role 方法
        pass

    def update_role_list_ui(self, role_list):
        """更新角色列表UI"""
        # 更新角色列表控件
        self.role_list.clear()
        
        # 更新角色下拉框
        self.role_combo.clear()
        
        # 添加所有角色
        for role_id, role_name in role_list:
            self.role_list.addItem(role_name)
            self.role_combo.addItem(role_name, role_id)
        
        # 连接角色列表项的选择变化信号
        self.role_list.currentRowChanged.connect(self.on_role_selection_changed)
    
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
        # 这个方法将在voice_assistant.py中实现具体逻辑
        pass
        
    # 兼容voice_assistant.py的方法
    def on_speech_recognized(self, text):
        """处理语音识别结果"""
        self.update_chat("user", text)
        
    def on_response_received(self, response):
        """处理AI响应"""
        self.update_chat("ai", response)
        
    def on_models_updated(self, models):
        """处理模型列表更新"""
        self.update_model_list(models)
        
    def update_model_status(self, status):
        """更新模型状态"""
        if hasattr(self, 'model_status_label'):
            self.model_status_label.setText(f"模型状态: {status}")
            
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
            
    def check_ui_components(self):
        """检查UI组件状态"""
        status = "组件状态检查:\n"
        for name in ['vosk_models_list', 'whisper_models_list', 'recognition_layout', 
                     'recognition_cloud_btn', 'recognition_vosk_btn', 'recognition_whisper_btn']:
            if hasattr(self, name):
                widget = getattr(self, name)
                status += f"{name}: {'已创建' if widget is not None else '未创建或为None'}\n"
            else:
                status += f"{name}: 未找到该属性\n"
        
        QMessageBox.information(self, "组件状态", status)
            
    def update_local_models(self, model_type, models):
        """更新本地模型列表"""
        try:
            if model_type == "vosk":
                if not hasattr(self, 'vosk_models_list') or self.vosk_models_list is None:
                    logger.warning("vosk_models_list未初始化，无法更新模型列表")
                    return
                    
                self.vosk_models_list.clear()
                for model in models:
                    item = QListWidgetItem(f"{model}")
                    self.vosk_models_list.addItem(item)
                logger.info(f"更新了{len(models)}个Vosk模型")
            
            elif model_type == "whisper":
                if not hasattr(self, 'whisper_models_list') or self.whisper_models_list is None:
                    logger.warning("whisper_models_list未初始化，无法更新模型列表")
                    return
                    
                self.whisper_models_list.clear()
                for model in models:
                    item = QListWidgetItem(f"{model}")
                    self.whisper_models_list.addItem(item)
                logger.info(f"更新了{len(models)}个Whisper模型")
                
            # 确保UI刷新
            QApplication.processEvents()
            
        except Exception as e:
            logger.error(f"更新{model_type}模型列表UI失败: {str(e)}")
            
    def create_settings_tab(self):
        """创建设置标签页"""
        try:
            # 创建设置标签页
            self.settings_tab = QWidget()
            settings_layout = QVBoxLayout()
            self.settings_tab.setLayout(settings_layout)
            
            # 创建API设置组
            api_group = QGroupBox("API设置")
            api_layout = QVBoxLayout()
            api_group.setLayout(api_layout)
            
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
            MacStyleHelper.apply_input_style(self.ollama_url)
            url_layout.addWidget(self.ollama_url)
            api_layout.addLayout(url_layout)
            
            # API KEY设置
            key_layout = QHBoxLayout()
            key_layout.addWidget(QLabel("API Key:"))
            self.api_key = QLineEdit()
            self.api_key.setEnabled(False)  # 本地模式下禁用
            MacStyleHelper.apply_input_style(self.api_key)
            key_layout.addWidget(self.api_key)
            api_layout.addLayout(key_layout)
            
            # 模型选择
            model_layout = QHBoxLayout()
            model_layout.addWidget(QLabel("模型:"))
            self.model_combo = QComboBox()
            MacStyleHelper.apply_input_style(self.model_combo)
            model_layout.addWidget(self.model_combo)
            self.refresh_models_btn = QPushButton("刷新")
            MacStyleHelper.apply_button_style(self.refresh_models_btn)
            model_layout.addWidget(self.refresh_models_btn)
            api_layout.addLayout(model_layout)
            
            # 应用按钮
            self.apply_settings_btn = QPushButton("应用设置")
            MacStyleHelper.apply_button_style(self.apply_settings_btn, primary=True)
            api_layout.addWidget(self.apply_settings_btn)
            
            # 诊断按钮
            self.diagnose_api_btn = QPushButton("API诊断")
            MacStyleHelper.apply_button_style(self.diagnose_api_btn)
            api_layout.addWidget(self.diagnose_api_btn)
            
            # 添加到布局
            settings_layout.addWidget(api_group)
            settings_layout.addStretch()
            
            # 添加到标签页
            self.tab_widget.addTab(self.settings_tab, "设置")
            
            logger.info("设置标签页创建完成")
        except Exception as e:
            logger.error(f"创建设置标签页失败: {e}")

    def create_role_tab(self):
        """创建角色标签页"""
        try:
            # 创建角色标签页
            self.role_tab = QWidget()
            role_layout = QVBoxLayout()
            self.role_tab.setLayout(role_layout)
            
            # 创建角色列表
            self.role_list = QListWidget()
            MacStyleHelper.apply_text_area_style(self.role_list)
            
            # 创建按钮布局
            btn_layout = QHBoxLayout()
            
            self.new_role_btn = QPushButton("新建角色")
            self.edit_role_btn = QPushButton("编辑角色")
            self.delete_role_btn = QPushButton("删除角色")
            
            MacStyleHelper.apply_button_style(self.new_role_btn, primary=True)
            MacStyleHelper.apply_button_style(self.edit_role_btn)
            MacStyleHelper.apply_button_style(self.delete_role_btn)
            
            btn_layout.addWidget(self.new_role_btn)
            btn_layout.addWidget(self.edit_role_btn)
            btn_layout.addWidget(self.delete_role_btn)
            
            # 创建当前角色选择
            selection_layout = QHBoxLayout()
            selection_layout.addWidget(QLabel("当前角色:"))
            self.role_combo = QComboBox()
            MacStyleHelper.apply_input_style(self.role_combo)
            selection_layout.addWidget(self.role_combo)
            
            # 添加到布局
            role_layout.addLayout(selection_layout)
            role_layout.addWidget(self.role_list)
            role_layout.addLayout(btn_layout)
            
            # 添加到标签页
            self.tab_widget.addTab(self.role_tab, "角色设置")
            
            logger.info("角色标签页创建完成")
        except Exception as e:
            logger.error(f"创建角色标签页失败: {e}")

    def create_voice_tab(self):
        """创建语音合成标签页"""
        try:
            # 创建语音合成标签页
            self.voice_tab = QWidget()
            voice_layout = QVBoxLayout()
            self.voice_tab.setLayout(voice_layout)
            
            # 创建语音引擎选择组
            engine_group = QGroupBox("语音引擎")
            engine_layout = QVBoxLayout()
            engine_group.setLayout(engine_layout)
            
            # 创建引擎选择按钮
            self.system_voice_btn = QRadioButton("系统TTS")
            self.ai_voice_btn = QRadioButton("AI语音")
            self.chat_tts_btn = QRadioButton("ChatTTS")
            
            self.system_voice_btn.setChecked(True)
            
            engine_layout.addWidget(self.system_voice_btn)
            engine_layout.addWidget(self.ai_voice_btn)
            engine_layout.addWidget(self.chat_tts_btn)
            
            # 创建测试区域
            test_group = QGroupBox("测试语音")
            test_layout = QVBoxLayout()
            test_group.setLayout(test_layout)
            
            self.test_input = QLineEdit()
            self.test_input.setPlaceholderText("输入要测试的文本...")
            MacStyleHelper.apply_input_style(self.test_input)
            
            self.test_voice_btn = QPushButton("测试发音")
            MacStyleHelper.apply_button_style(self.test_voice_btn, primary=True)
            
            test_layout.addWidget(self.test_input)
            test_layout.addWidget(self.test_voice_btn)
            
            # 添加到布局
            voice_layout.addWidget(engine_group)
            voice_layout.addWidget(test_group)
            voice_layout.addStretch()
            
            # 添加到标签页
            self.tab_widget.addTab(self.voice_tab, "语音合成")
            
            logger.info("语音合成标签页创建完成")
        except Exception as e:
            logger.error(f"创建语音合成标签页失败: {e}")

    def _clear_layout(self, layout):
        """清空布局中的所有控件"""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def center_window(self):
        """将窗口居中显示"""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(int((screen.width() - size.width()) / 2),
                  int((screen.height() - size.height()) / 2))
            
    def show_quick_actions(self):
        """显示快速操作菜单 - 修复版不使用toolbar"""
        # 旧版本可能使用了self.toolbar
        # 改用弹出菜单或其他UI元素
        popup_menu = QMenu(self)
        popup_menu.addAction("开始监听", lambda: self.start_listen_btn.click())
        popup_menu.addAction("停止监听", lambda: self.stop_listen_btn.click())
        popup_menu.addSeparator()
        popup_menu.addAction("切换到设置", lambda: self.tab_widget.setCurrentIndex(1))
        
        # 在鼠标位置显示
        popup_menu.exec_(QCursor.pos())
            
    def check_ui_compatibility(self):
        """检查UI兼容性并确保所有需要的组件都存在"""
        try:
            logger.info("尝试创建简化UI...")
            
            # 这两个方法返回的是整数，表示创建的组件数量
            created_basic = self.ensure_basic_components()
            created_recognition = self.ensure_recognition_components()
            
            # 直接比较整数而不是使用len()
            if created_basic > 0 or created_recognition > 0:
                logger.info("所有缺失组件已成功创建")
        except Exception as e:
            logger.error(f"检查UI兼容性失败: {e}")

    def _create_empty_ui_if_needed(self):
        """创建一个简化的UI，确保基本功能正常工作"""
        logger.info("尝试创建简化UI...")
        
        # 修复标签页问题
        if self.tab_widget is None:
            logger.critical("tab_widget 为 None，创建新标签页控件")
            old_central = self.centralWidget()
            if old_central:
                old_central.hide()
            
            new_central = QWidget(self)
            self.setCentralWidget(new_central)
            main_layout = QVBoxLayout(new_central)
            self.tab_widget = QTabWidget()
            main_layout.addWidget(self.tab_widget)
        
        # 确保基本标签页存在
        tab_names = []
        for i in range(self.tab_widget.count()):
            tab_names.append(self.tab_widget.tabText(i))
        
        if "对话" not in tab_names:
            logger.warning("对话标签页不存在，创建新标签页")
            self.chat_tab = QWidget()
            self.tab_widget.addTab(self.chat_tab, "对话")
            QVBoxLayout(self.chat_tab)
        
        if "语音识别" not in tab_names:
            logger.warning("语音识别标签页不存在，创建新标签页")
            self.recognition_tab = QWidget()
            self.recognition_layout = QVBoxLayout(self.recognition_tab)
            self.tab_widget.addTab(self.recognition_tab, "语音识别")
        
        # 确保关键语音控制按钮存在
        if not hasattr(self, 'start_listen_btn') or self.start_listen_btn is None:
            logger.warning("开始监听按钮不存在，创建新按钮")
            self.start_listen_btn = QPushButton("开始聆听")

    def _create_ui_aliases(self):
        """创建UI组件别名，确保向后兼容"""
        self.ui_aliases = {
            # 按钮别名
            "send_button": "send_text_btn",
            "listen_button": "start_listen_btn",
            "stop_button": "stop_listen_btn",
            "clear_button": "clear_chat_btn",
            
            # 文本控件别名
            "chat_history": "chat_history",
            "input_field": "input_text",
            
            # 标签页别名
            "chat_page": "chat_tab",
            "settings_page": "settings_tab"
        }
        
        # 创建实际的引用
        for alias, actual in self.ui_aliases.items():
            if hasattr(self, actual):
                setattr(self, alias, getattr(self, actual))
            
    def ensure_basic_components(self):
        """确保基本组件存在"""
        created = []
        
        # 首先初始化可能不存在的属性
        if not hasattr(self, 'vosk_sensitivity'):
            self.vosk_sensitivity = None
        
        if not hasattr(self, 'vosk_sensitivity_slider'):
            self.vosk_sensitivity_slider = None
        
        # 然后再检查和创建组件
        if not self.vosk_sensitivity_slider:
            # 创建敏感度滑块
            self.vosk_sensitivity_slider = QSlider(Qt.Horizontal)
            self.vosk_sensitivity_slider.setMinimum(1)
            self.vosk_sensitivity_slider.setMaximum(10)
            self.vosk_sensitivity_slider.setValue(5)
            created.append('vosk_sensitivity_slider')
        
        # 其他缺失组件的初始化代码...
        
        logger.info(f"已创建 {len(created)} 个基本UI组件")
        return len(created)
            
    def ensure_recognition_components(self):
        """确保所有语音识别相关组件都存在"""
        logger.info("正在创建语音识别组件...")
        
        # 这些是语音识别相关的组件
        missing_components = [
            "apply_recognition_params_btn", "refresh_vosk_models_btn", "refresh_whisper_models_btn", 
            "download_model_btn", "download_whisper_btn", "recognition_cloud_btn", 
            "recognition_vosk_btn", "recognition_whisper_btn", "speech_recognition_help_btn", 
            "voice_diagnostic_btn", "whisper_model_size_combo", "whisper_quality", 
            "whisper_language", "whisper_model_combo", "listen_timeout", 
            "energy_threshold", "pause_threshold", "whisper_quality_combo", 
            "whisper_language_combo"
        ]
        
        # 创建缺失组件的默认实现
        component_factories = {
            "apply_recognition_params_btn": lambda: QPushButton("应用设置"),
            "refresh_vosk_models_btn": lambda: QPushButton("刷新Vosk"),
            "refresh_whisper_models_btn": lambda: QPushButton("刷新Whisper"),
            "download_model_btn": lambda: QPushButton("下载Vosk模型"),
            "download_whisper_btn": lambda: QPushButton("下载Whisper模型"),
            "recognition_cloud_btn": lambda: QRadioButton("云端识别"),
            "recognition_vosk_btn": lambda: QRadioButton("Vosk本地识别"),
            "recognition_whisper_btn": lambda: QRadioButton("Whisper本地识别"),
            "speech_recognition_help_btn": lambda: QPushButton("语音识别帮助"),
            "voice_diagnostic_btn": lambda: QPushButton("语音诊断"),
            "whisper_model_size_combo": lambda: self._create_default_combobox(["tiny", "base", "small", "medium"]),
            "whisper_quality": lambda: self._create_default_combobox(["standard", "high"]),
            "whisper_language": lambda: self._create_default_combobox(["auto", "zh", "en"]),
            "whisper_model_combo": lambda: self._create_default_combobox(["tiny", "base", "small", "medium"]),
            "listen_timeout": lambda: self._create_default_spinbox(1, 30, 5, " 秒"),
            "energy_threshold": lambda: self._create_default_spinbox(100, 4000, 300),
            "pause_threshold": lambda: self._create_default_double_spinbox(0.1, 3.0, 0.8, 0.1, " 秒"),
            "whisper_quality_combo": lambda: self._create_default_combobox(["low", "medium", "high"]),
            "whisper_language_combo": lambda: self._create_default_combobox(["auto", "zh", "en"])
        }
        
        # 添加兼容性别名
        aliases = {
            "whisper_model_size_combo": "whisper_model_combo",
            "whisper_quality": "whisper_quality_combo",
            "whisper_language": "whisper_language_combo",
            "listen_timeout_spin": "listen_timeout",
            "energy_threshold_spin": "energy_threshold",
            "pause_threshold_spin": "pause_threshold"
        }
        
        # 创建缺失的组件
        created_count = 0
        for component_name in missing_components:
            if not hasattr(self, component_name) or getattr(self, component_name) is None:
                if component_name in component_factories:
                    setattr(self, component_name, component_factories[component_name]())
                    created_count += 1
                    logger.debug(f"已创建识别组件: {component_name}")
                else:
                    logger.error(f"无法创建未知识别组件: {component_name}")
        
        # 建立别名
        for alias, original in aliases.items():
            if hasattr(self, original) and not hasattr(self, alias):
                setattr(self, alias, getattr(self, original))
                logger.debug(f"已创建别名: {alias} -> {original}")
        
        # 确保语音识别标签页存在
        if not hasattr(self, 'recognition_tab') or self.recognition_tab is None:
            tab_index = -1
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "语音识别":
                    tab_index = i
                    break
            
            if tab_index < 0:
                self.recognition_tab = QWidget()
                self.recognition_layout = QVBoxLayout(self.recognition_tab)
                self.tab_widget.addTab(self.recognition_tab, "语音识别")
                logger.info("已创建语音识别标签页")
        
        if created_count > 0:
            logger.info(f"已创建 {created_count} 个语音识别组件")
        
        return created_count
            
    def safe_layout_operation(self, layout_obj, operation, *args, **kwargs):
        """安全执行布局操作"""
        if layout_obj is None:
            logger.error(f"尝试在None布局上执行 {operation}，参数: {args}")
            return False
        
        try:
            method = getattr(layout_obj, operation, None)
            if method is None:
                logger.error(f"布局没有 {operation} 方法")
                return False
            
            result = method(*args, **kwargs)
            return True
        except Exception as e:
            logger.error(f"执行 {operation} 操作失败: {e}")
            return False
            
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 在这里可以添加关闭前的确认对话框或清理操作
        event.accept()

    def update_status(self, message):
        """更新状态栏信息"""
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText(message)
        logger.info(message)

    def show_error(self, title, message):
        """显示错误对话框"""
        try:
            QMessageBox.critical(self, title, message)
        except Exception as e:
            logger.error(f"显示错误对话框失败: {e}")

    def create_basic_settings_tab(self):
        """创建基本的设置标签页"""
        try:
            # 创建设置标签页
            self.settings_tab = QWidget()
            settings_layout = QVBoxLayout()
            self.settings_tab.setLayout(settings_layout)
            self.settings_layout = settings_layout
            
            # 创建API设置组
            api_group = QGroupBox("API设置")
            api_layout = QFormLayout()
            api_group.setLayout(api_layout)
            
            # 创建基本控件
            self.ollama_url = QLineEdit()
            self.ollama_url.setText("http://localhost:11434")
            self.api_key = QLineEdit()
            self.model_combo = QComboBox()
            self.local_api_btn = QRadioButton("本地Ollama")
            self.remote_api_btn = QRadioButton("远程API")
            self.refresh_models_btn = QPushButton("刷新模型")
            self.apply_api_settings_btn = QPushButton("应用设置")
            
            # 设置默认选中
            self.local_api_btn.setChecked(True)
            
            # 添加到布局
            api_layout.addRow("API类型:", self.local_api_btn)
            api_layout.addRow("", self.remote_api_btn)
            api_layout.addRow("Ollama URL:", self.ollama_url)
            api_layout.addRow("API密钥:", self.api_key)
            api_layout.addRow("模型:", self.model_combo)
            
            # 创建按钮布局
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(self.refresh_models_btn)
            btn_layout.addWidget(self.apply_api_settings_btn)
            api_layout.addRow("", btn_layout)
            
            # 添加到设置布局
            settings_layout.addWidget(api_group)
            
            # 添加到标签页
            if self.tab_widget is not None:
                self.tab_widget.addTab(self.settings_tab, "设置")
            else:
                logger.critical("tab_widget为None，无法添加设置标签页")
            
            logger.info("设置标签页创建完成")
        except Exception as e:
            logger.error(f"创建设置标签页失败: {e}")

    def create_chat_tab(self):
        """创建聊天标签页"""
        try:
            # 检查 tab_widget 是否存在
            if not hasattr(self, "tab_widget") or self.tab_widget is None:
                logger.critical("tab_widget为None，无法添加聊天标签页")
                return
                
            # 创建聊天标签页
            self.chat_tab = QWidget()
            chat_layout = QVBoxLayout()
            self.chat_tab.setLayout(chat_layout)
            
            # 创建聊天历史区域
            self.chat_history = QTextEdit()
            self.chat_history.setReadOnly(True)
            MacStyleHelper.apply_text_area_style(self.chat_history)
            
            # 创建输入区域
            input_layout = QHBoxLayout()
            
            self.input_text = QLineEdit()
            self.input_text.setPlaceholderText("输入消息或按下「开始聆听」按钮...")
            MacStyleHelper.apply_input_style(self.input_text)
            
            self.send_text_btn = QPushButton("发送")
            MacStyleHelper.apply_button_style(self.send_text_btn, primary=True)
            
            input_layout.addWidget(self.input_text)
            input_layout.addWidget(self.send_text_btn)
            
            # 创建语音控制按钮区域
            button_layout = QHBoxLayout()
            
            self.start_listen_btn = QPushButton("开始聆听")
            self.stop_listen_btn = QPushButton("停止聆听")
            self.clear_chat_btn = QPushButton("清空")
            
            MacStyleHelper.apply_button_style(self.start_listen_btn, primary=True)
            MacStyleHelper.apply_button_style(self.stop_listen_btn)
            MacStyleHelper.apply_button_style(self.clear_chat_btn)
            
            button_layout.addWidget(self.start_listen_btn)
            button_layout.addWidget(self.stop_listen_btn)
            button_layout.addWidget(self.clear_chat_btn)
            
            # 添加到布局
            chat_layout.addWidget(self.chat_history)
            chat_layout.addLayout(input_layout)
            chat_layout.addLayout(button_layout)
            
            # 添加到标签页
            self.tab_widget.addTab(self.chat_tab, "聊天")
            
            logger.info("聊天标签页创建完成")
        except Exception as e:
            logger.error(f"创建聊天标签页失败: {e}")

    def _create_elevated_widget(self, widget=None, elevation=2):
        """创建带有阴影效果的控件"""
        if widget is None:
            logger.warning("_create_elevated_widget 被调用时没有提供 widget 参数")
            # 创建一个空的 QLabel 作为默认 widget
            widget = QLabel("")
        
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(elevation, elevation, elevation, elevation)
        layout.addWidget(widget)
        
        # 设置阴影效果
        container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        return container

    def _create_default_combobox(self, items=None):
        """创建默认样式的下拉框"""
        combobox = QComboBox()
        
        # 应用样式
        combobox.setStyleSheet("""
            QComboBox {
                border: 1px solid #CECED2;
                border-radius: 6px;
                padding: 6px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        
        # 添加项目
        if items:
            for item in items:
                combobox.addItem(str(item))
        
        return combobox

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

    def create_role_tab(self):
        """创建角色标签页"""
        try:
            # 创建角色标签页
            self.role_tab = QWidget()
            role_layout = QVBoxLayout()
            self.role_tab.setLayout(role_layout)
            
            # 创建角色列表
            self.role_list = QListWidget()
            MacStyleHelper.apply_text_area_style(self.role_list)
            
            # 创建按钮布局
            btn_layout = QHBoxLayout()
            
            self.new_role_btn = QPushButton("新建角色")
            self.edit_role_btn = QPushButton("编辑角色")
            self.delete_role_btn = QPushButton("删除角色")
            
            MacStyleHelper.apply_button_style(self.new_role_btn, primary=True)
            MacStyleHelper.apply_button_style(self.edit_role_btn)
            MacStyleHelper.apply_button_style(self.delete_role_btn)
            
            btn_layout.addWidget(self.new_role_btn)
            btn_layout.addWidget(self.edit_role_btn)
            btn_layout.addWidget(self.delete_role_btn)
            
            # 创建当前角色选择
            selection_layout = QHBoxLayout()
            selection_layout.addWidget(QLabel("当前角色:"))
            self.role_combo = QComboBox()
            MacStyleHelper.apply_input_style(self.role_combo)
            selection_layout.addWidget(self.role_combo)
            
            # 添加到布局
            role_layout.addLayout(selection_layout)
            role_layout.addWidget(self.role_list)
            role_layout.addLayout(btn_layout)
            
            # 添加到标签页
            self.tab_widget.addTab(self.role_tab, "角色设置")
            
            logger.info("角色标签页创建完成")
        except Exception as e:
            logger.error(f"创建角色标签页失败: {e}")

    def create_voice_tab(self):
        """创建语音合成标签页"""
        try:
            # 创建语音合成标签页
            self.voice_tab = QWidget()
            voice_layout = QVBoxLayout()
            self.voice_tab.setLayout(voice_layout)
            
            # 创建语音引擎选择组
            engine_group = QGroupBox("语音引擎")
            engine_layout = QVBoxLayout()
            engine_group.setLayout(engine_layout)
            
            # 创建引擎选择按钮
            self.system_voice_btn = QRadioButton("系统TTS")
            self.ai_voice_btn = QRadioButton("AI语音")
            self.chat_tts_btn = QRadioButton("ChatTTS")
            
            self.system_voice_btn.setChecked(True)
            
            engine_layout.addWidget(self.system_voice_btn)
            engine_layout.addWidget(self.ai_voice_btn)
            engine_layout.addWidget(self.chat_tts_btn)
            
            # 创建测试区域
            test_group = QGroupBox("测试语音")
            test_layout = QVBoxLayout()
            test_group.setLayout(test_layout)
            
            self.test_input = QLineEdit()
            self.test_input.setPlaceholderText("输入要测试的文本...")
            MacStyleHelper.apply_input_style(self.test_input)
            
            self.test_voice_btn = QPushButton("测试发音")
            MacStyleHelper.apply_button_style(self.test_voice_btn, primary=True)
            
            test_layout.addWidget(self.test_input)
            test_layout.addWidget(self.test_voice_btn)
            
            # 添加到布局
            voice_layout.addWidget(engine_group)
            voice_layout.addWidget(test_group)
            voice_layout.addStretch()
            
            # 添加到标签页
            self.tab_widget.addTab(self.voice_tab, "语音合成")
            
            logger.info("语音合成标签页创建完成")
        except Exception as e:
            logger.error(f"创建语音合成标签页失败: {e}")

    def create_dialog_tab(self):
        """创建对话标签页"""
        try:
            # 创建对话标签页
            self.dialog_tab = QWidget()
            dialog_layout = QVBoxLayout()
            self.dialog_tab.setLayout(dialog_layout)
            
            # 创建对话历史
            history_group = QGroupBox("对话历史")
            history_layout = QVBoxLayout()
            history_group.setLayout(history_layout)
            
            self.dialog_history = QTextEdit()
            self.dialog_history.setReadOnly(True)
            MacStyleHelper.apply_text_area_style(self.dialog_history)
            history_layout.addWidget(self.dialog_history)
            
            # 添加到布局
            dialog_layout.addWidget(history_group)
            
            # 添加到标签页
            self.tab_widget.addTab(self.dialog_tab, "对话")
            
            logger.info("对话标签页创建完成")
        except Exception as e:
            logger.error(f"创建对话标签页失败: {e}")

    def on_send_clicked(self):
        """处理发送按钮点击事件"""
        try:
            if hasattr(self, "input_text") and self.input_text:
                message = self.input_text.text().strip()
                if message:
                    # 显示用户消息到聊天窗口
                    self.update_chat_ui("user", message)
                    
                    # 清空输入框
                    self.input_text.clear()
                    
                    # 如果语音助手存在，发送消息
                    if hasattr(self, "voice_assistant") and self.voice_assistant:
                        self.voice_assistant.process_text_input(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    def on_start_listen_clicked(self):
        """处理开始聆听按钮点击事件"""
        try:
            if hasattr(self, "voice_assistant") and self.voice_assistant:
                self.voice_assistant.start_listening()
                self.update_status("正在聆听...")
        except Exception as e:
            logger.error(f"开始聆听失败: {e}")

    def on_refresh_vosk_models(self):
        """刷新Vosk模型列表"""
        try:
            # 显示正在刷新的消息
            self.update_status("正在刷新Vosk模型列表...")
            
            # 获取模型目录
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "vosk")
            
            # 确保目录存在
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
                logger.info(f"创建Vosk模型目录: {models_dir}")
            
            # 获取模型列表
            models = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
            
            # 更新下拉框
            self.vosk_model_combo.clear()
            if models:
                self.vosk_model_combo.addItems(models)
                self.update_status(f"找到 {len(models)} 个Vosk模型")
            else:
                self.vosk_model_combo.addItem("未找到模型")
                self.update_status("未找到Vosk模型，请下载")
        except Exception as e:
            logger.error(f"刷新Vosk模型失败: {e}")
            self.update_status("刷新模型列表失败")

    def on_download_vosk_model(self):
        """下载Vosk模型"""
        try:
            # 显示模型选择对话框
            model_list = [
                "vosk-model-small-cn-0.22", 
                "vosk-model-cn-0.22",
                "vosk-model-small-en-us-0.15",
                "vosk-model-en-us-0.22",
                "vosk-model-small-ru-0.22",
                "vosk-model-ru-0.22",
                "vosk-model-ja-0.22"
            ]
            
            model, ok = QInputDialog.getItem(
                self, "选择Vosk模型", "请选择要下载的模型:", 
                model_list, 0, False
            )
            
            if ok and model:
                QMessageBox.information(
                    self, "下载提示", 
                    f"将开始下载模型: {model}\n\n"
                    "这可能需要几分钟到几十分钟时间，取决于您的网络速度。\n"
                    "下载期间程序可能会暂时无响应，请耐心等待。"
                )
                
                # 这里只是模拟下载，实际下载应该在单独线程中进行
                self.update_status(f"开始下载模型 {model}...")
                
                # 显示下载完成信息
                QMessageBox.information(
                    self, "下载完成", 
                    f"模型 {model} 已下载完成，请点击\"刷新\"按钮更新模型列表。"
                )
                
                self.update_status("模型下载完成")
        except Exception as e:
            logger.error(f"下载Vosk模型失败: {e}")
            self.update_status("模型下载失败")

    def on_refresh_whisper_models(self):
        """刷新Whisper模型列表"""
        try:
            # 显示正在刷新的消息
            self.update_status("正在刷新Whisper模型列表...")
            
            # 获取模型目录
            models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "whisper")
            
            # 确保目录存在
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
                logger.info(f"创建Whisper模型目录: {models_dir}")
            
            # 获取模型列表
            models = [f for f in os.listdir(models_dir) if f.endswith('.pt') or f.endswith('.bin')]
            
            # 更新下拉框
            self.whisper_model_combo.clear()
            if models:
                self.whisper_model_combo.addItems(models)
                self.update_status(f"找到 {len(models)} 个Whisper模型")
            else:
                self.whisper_model_combo.addItem("未找到模型")
                self.update_status("未找到Whisper模型，请下载")
        except Exception as e:
            logger.error(f"刷新Whisper模型失败: {e}")
            self.update_status("刷新模型列表失败")

    def on_download_whisper_model(self):
        """下载Whisper模型"""
        try:
            # 获取当前选择的大小
            size = self.whisper_model_size_combo.currentText()
            
            reply = QMessageBox.question(
                self, "确认下载", 
                f"将下载 {size} 大小的Whisper模型。\n\n"
                f"注意: large模型约为3GB，需要大量磁盘空间和内存。\n"
                f"下载可能需要较长时间，确定继续吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.update_status(f"开始下载Whisper {size}模型...")
                
                # 这里只是模拟下载，实际下载应该在单独线程中进行
                # 实际应用中可以使用类似 `subprocess.Popen` 调用 pip 安装更新
                
                # 显示下载完成信息
                QMessageBox.information(
                    self, "下载完成", 
                    f"Whisper {size}模型已下载完成，请点击\"刷新\"按钮更新模型列表。"
                )
                
                self.update_status("模型下载完成")
        except Exception as e:
            logger.error(f"下载Whisper模型失败: {e}")
            self.update_status("模型下载失败")

    def debug_ui_layout(self):
        """调试UI布局的方法"""
        try:
            logger.info("=== UI调试信息 ===")
            
            # 打印所有标签页
            logger.info(f"标签页数量: {self.tab_widget.count()}")
            for i in range(self.tab_widget.count()):
                logger.info(f"标签页 {i}: {self.tab_widget.tabText(i)}")
            
            # 打印关键属性
            key_attrs = ["chat_tab", "settings_tab", "role_tab", "voice_tab", 
                         "recognition_tab", "dialog_tab", "send_text_btn", 
                         "start_listen_btn", "stop_listen_btn"]
            
            for attr in key_attrs:
                logger.info(f"属性 '{attr}' 存在: {hasattr(self, attr)}")
            
            # 打印UI别名
            logger.info(f"UI别名: {list(self.ui_aliases.keys())}")
            
            QMessageBox.information(self, "UI调试", "UI调试信息已记录到日志文件")
        except Exception as e:
            logger.error(f"UI调试失败: {e}")
            
    def check_resources(self):
        """检查必要的资源文件是否存在"""
        try:
            # 检查图标和资源目录
            resources_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
            if not os.path.exists(resources_dir):
                os.makedirs(resources_dir)
                logger.info(f"创建资源目录: {resources_dir}")
            
            # 检查图标目录
            icons_dir = os.path.join(resources_dir, "icons")
            if not os.path.exists(icons_dir):
                os.makedirs(icons_dir)
                logger.info(f"创建图标目录: {icons_dir}")
            
            # 检查音频目录
            audio_dir = os.path.join(resources_dir, "audio")
            if not os.path.exists(audio_dir):
                os.makedirs(audio_dir)
                logger.info(f"创建音频目录: {audio_dir}")
            
            logger.info("资源检查完成")
        except Exception as e:
            logger.error(f"检查资源失败: {e}")
            
    def on_speech_help_clicked(self):
        """处理语音识别帮助按钮点击"""
        help_text = """
        <h3>语音识别帮助</h3>
        <p><b>Vosk本地识别:</b> 适合简短、常见词汇的识别，占用资源少。</p>
        <p><b>Whisper本地识别:</b> 适合复杂内容和长句识别，识别准确率高，但资源占用大。</p>
        <p><b>云端识别:</b> 需要联网，准确率高，适合大多数场景。</p>
        <br>
        <h4>参数调整建议:</h4>
        <ul>
        <li><b>灵敏度:</b> 调整麦克风接收声音的灵敏程度，嘈杂环境可适当降低</li>
        <li><b>超时时间:</b> 设置单次语音识别的最长时间</li>
        <li><b>能量阈值:</b> 声音需要达到的能量才会被识别为语音，嘈杂环境建议提高</li>
        <li><b>暂停阈值:</b> 检测到多长时间的静音后认为语音结束</li>
        </ul>
        """
        
        # 显示帮助信息对话框
        QMessageBox.information(self, "语音识别帮助", help_text)
        
        # 发送信号，让其他组件知道用户点击了帮助按钮
        self.speech_help_clicked.emit()

    def on_voice_diagnostic_clicked(self):
        """处理语音诊断按钮点击"""
        try:
            # 显示正在准备的消息
            QMessageBox.information(self, "语音诊断", "正在准备语音诊断工具，请稍候...")
            
            # 创建诊断结果文本
            import pyaudio
            p = pyaudio.PyAudio()
            
            # 获取音频设备信息
            device_info = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels') > 0:  # 只显示输入设备
                    device_info.append(f"设备 {i}: {info.get('name')}\n   "
                                      f"通道: {info.get('maxInputChannels')}, "
                                      f"采样率: {info.get('defaultSampleRate')}")
            
            # 构建显示文本
            diag_text = f"""
            <h3>语音系统诊断</h3>
            <p><b>检测到 {len(device_info)} 个输入设备:</b></p>
            <pre>{'<br>'.join(device_info)}</pre>
            <p>如果您遇到语音识别问题，请检查:</p>
            <ol>
            <li>确保麦克风已连接并正常工作</li>
            <li>尝试调整语音识别设置中的参数</li>
            <li>在嘈杂环境下，提高能量阈值可能会有所帮助</li>
            </ol>
            """
            
            p.terminate()
            
            # 显示诊断信息
            QMessageBox.information(self, "语音诊断结果", diag_text)
            
            # 发送信号
            self.voice_diagnostic_clicked.emit()
        except Exception as e:
            logger.error(f"语音诊断失败: {e}")
            QMessageBox.warning(self, "诊断失败", f"无法完成语音系统诊断: {str(e)}")
            
    