import logging
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from .pet_manager import PetManager
from .ui.settings_panel import PetSettingsPanel

logger = logging.getLogger(__name__)

class PetAssistantIntegration(QObject):
    """将桌面宠物与语音助手系统集成"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # 创建宠物管理器
        self.pet_manager = PetManager()
        
        # 创建设置面板
        self.setup_settings_panel()
        
        # 连接语音助手事件
        self.connect_assistant_events()
        
        # 启动宠物（如果配置允许）
        current_settings = self.pet_manager.config_manager.get_all()
        if current_settings.get("enabled", True):
            self.pet_manager.start()
            
    def setup_settings_panel(self):
        """设置桌面宠物设置面板"""
        # 创建设置面板
        self.settings_panel = PetSettingsPanel()
        self.settings_panel.settings_changed.connect(self.pet_manager.update_settings)
        
        # 将设置面板添加到主窗口，支持不同窗口类
        try:
            # 尝试使用tab_widget（统一接口）
            if hasattr(self.main_window, 'tab_widget') and self.main_window.tab_widget:
                self.main_window.tab_widget.addTab(self.settings_panel, "桌面宠物")
                logger.info("桌面宠物设置面板已添加到标签页")
            else:
                # 备用方案：查找任何可能的标签控件
                for attr_name in dir(self.main_window):
                    if "tab" in attr_name.lower() and hasattr(getattr(self.main_window, attr_name), "addTab"):
                        tab_widget = getattr(self.main_window, attr_name)
                        tab_widget.addTab(self.settings_panel, "桌面宠物")
                        logger.info(f"桌面宠物设置面板已添加到 {attr_name}")
                        break
                else:
                    logger.warning("无法找到合适的标签控件，设置面板未添加")
                
            # 扫描可用模型并更新设置面板
            available_models = self.pet_manager.scan_available_models()
            self.settings_panel.update_model_list(available_models)
            
            # 加载当前设置到面板
            current_settings = self.pet_manager.config_manager.get_all()
            self.settings_panel.update_settings(current_settings)
        except Exception as e:
            logger.error(f"添加设置面板失败: {e}")
            
    def connect_assistant_events(self):
        """连接语音助手事件到桌面宠物"""
        try:
            # 首先尝试标准信号
            if hasattr(self.main_window, 'update_status_signal'):
                self.main_window.update_status_signal.connect(self.on_assistant_status_update)
            # 如果没有标准信号，尝试状态标签
            elif hasattr(self.main_window, 'status_label'):
                # 使用定时器监控状态变化
                self.status_timer = QTimer()
                self.status_timer.timeout.connect(self._check_status_label)
                self.status_timer.start(500)  # 每500毫秒检查一次
                self.last_status = ""
            
            # 注册宠物的设置和退出回调
            self.pet_manager.register_settings_callback(self.show_pet_settings)
            self.pet_manager.register_exit_callback(self.on_pet_exit)
            
            logger.info("桌面宠物已连接到语音助手事件")
        except Exception as e:
            logger.error(f"连接语音助手事件失败: {e}")
            
    def on_assistant_status_update(self, status: str):
        """处理语音助手状态更新
        
        Args:
            status: 状态消息
        """
        # 根据状态消息判断助手状态
        if "正在听取" in status or "录音中" in status:
            self.pet_manager.handle_voice_assistant_event("listening")
        elif "思考中" in status or "处理中" in status:
            self.pet_manager.handle_voice_assistant_event("thinking")
        elif "回答" in status or "播放" in status:
            self.pet_manager.handle_voice_assistant_event("speaking")
        elif "就绪" in status or "准备" in status:
            self.pet_manager.handle_voice_assistant_event("idle")
            
    def show_pet_settings(self):
        """显示宠物设置面板"""
        if self.main_window:
            # 显示主窗口
            self.main_window.show()
            self.main_window.raise_()
            
            # 切换到宠物设置标签
            try:
                if hasattr(self.main_window, 'tab_widget'):
                    for i in range(self.main_window.tab_widget.count()):
                        if self.main_window.tab_widget.tabText(i) == "桌面宠物":
                            self.main_window.tab_widget.setCurrentIndex(i)
                            break
            except Exception as e:
                logger.error(f"切换到桌面宠物设置标签失败: {e}")
                
    def on_pet_exit(self):
        """处理宠物退出请求"""
        # 显示确认对话框
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.main_window,
            "退出确认",
            "您确定要退出整个应用程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 退出整个应用程序
            self.main_window.close()
            
    def cleanup(self):
        """清理资源，在应用退出前调用"""
        # 停止桌面宠物
        if self.pet_manager:
            self.pet_manager.stop()

    def _check_status_label(self):
        """检查状态标签的变化"""
        if hasattr(self.main_window, 'status_label'):
            current_status = self.main_window.status_label.text()
            if current_status != self.last_status:
                self.on_assistant_status_update(current_status)
                self.last_status = current_status 