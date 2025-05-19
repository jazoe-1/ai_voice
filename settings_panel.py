import os
import logging
from typing import Callable, List, Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QGroupBox, QCheckBox, QComboBox, QSlider, QLabel, 
                            QPushButton, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class PetSettingsPanel(QWidget):
    """桌面宠物设置面板"""
    
    # 定义信号
    settings_changed = pyqtSignal(dict)  # 当设置改变时发射
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self.available_models = []
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 添加启用选项
        self.enable_checkbox = QCheckBox("启用桌面宠物")
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        main_layout.addWidget(self.enable_checkbox)
        
        # 设置选项卡
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 基本设置选项卡
        basic_tab = QWidget()
        tabs.addTab(basic_tab, "基本设置")
        basic_layout = QVBoxLayout(basic_tab)
        
        # 模型设置
        model_group = QGroupBox("模型设置")
        basic_layout.addWidget(model_group)
        model_layout = QGridLayout(model_group)
        
        model_layout.addWidget(QLabel("选择模型:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_layout.addWidget(self.model_combo, 0, 1)
        
        # 窗口设置
        window_group = QGroupBox("窗口设置")
        basic_layout.addWidget(window_group)
        window_layout = QGridLayout(window_group)
        
        # 窗口大小
        window_layout.addWidget(QLabel("窗口大小:"), 0, 0)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(50, 500)
        self.size_slider.valueChanged.connect(self.on_size_changed)
        window_layout.addWidget(self.size_slider, 0, 1)
        self.size_label = QLabel("200")
        window_layout.addWidget(self.size_label, 0, 2)
        
        # 不透明度
        window_layout.addWidget(QLabel("不透明度:"), 1, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        window_layout.addWidget(self.opacity_slider, 1, 1)
        self.opacity_label = QLabel("90%")
        window_layout.addWidget(self.opacity_label, 1, 2)
        
        # 渲染质量
        window_layout.addWidget(QLabel("渲染质量:"), 2, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高", "中", "低"])
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        window_layout.addWidget(self.quality_combo, 2, 1)
        
        # 添加位置设置
        position_group = QGroupBox("位置设置")
        basic_layout.addWidget(position_group)
        position_layout = QHBoxLayout(position_group)
        
        self.reset_position_button = QPushButton("重置位置")
        self.reset_position_button.clicked.connect(self.on_reset_position)
        position_layout.addWidget(self.reset_position_button)
        
        self.fixed_position_checkbox = QCheckBox("固定位置")
        self.fixed_position_checkbox.toggled.connect(self.on_fixed_position_toggled)
        position_layout.addWidget(self.fixed_position_checkbox)
        
        # 行为选项卡
        behavior_tab = QWidget()
        tabs.addTab(behavior_tab, "行为设置")
        behavior_layout = QVBoxLayout(behavior_tab)
        
        # 互动设置
        interaction_group = QGroupBox("互动设置")
        behavior_layout.addWidget(interaction_group)
        interaction_layout = QGridLayout(interaction_group)
        
        # 互动频率
        interaction_layout.addWidget(QLabel("互动频率:"), 0, 0)
        self.frequency_slider = QSlider(Qt.Horizontal)
        self.frequency_slider.setRange(10, 300)
        self.frequency_slider.valueChanged.connect(self.on_frequency_changed)
        interaction_layout.addWidget(self.frequency_slider, 0, 1)
        self.frequency_label = QLabel("60秒")
        interaction_layout.addWidget(self.frequency_label, 0, 2)
        
        # 鼠标跟随
        self.mouse_follow_checkbox = QCheckBox("视线跟随鼠标")
        self.mouse_follow_checkbox.toggled.connect(self.on_mouse_follow_toggled)
        interaction_layout.addWidget(self.mouse_follow_checkbox, 1, 0, 1, 3)
        
        # 互动动作测试
        test_group = QGroupBox("动作测试")
        behavior_layout.addWidget(test_group)
        test_layout = QHBoxLayout(test_group)
        
        # 添加几个测试按钮
        self.idle1_button = QPushButton("待机1")
        self.idle1_button.clicked.connect(lambda: self.on_test_motion("idle"))
        test_layout.addWidget(self.idle1_button)
        
        self.idle2_button = QPushButton("待机2")
        self.idle2_button.clicked.connect(lambda: self.on_test_motion("idle2"))
        test_layout.addWidget(self.idle2_button)
        
        self.talk_button = QPushButton("说话")
        self.talk_button.clicked.connect(lambda: self.on_test_motion("talk"))
        test_layout.addWidget(self.talk_button)
        
        self.expression_button = QPushButton("表情")
        self.expression_button.clicked.connect(lambda: self.on_test_motion("expression"))
        test_layout.addWidget(self.expression_button)
        
        # 关于选项卡
        about_tab = QWidget()
        tabs.addTab(about_tab, "关于")
        about_layout = QVBoxLayout(about_tab)
        
        about_label = QLabel(
            "Live2D桌面宠物\n\n"
            "一个基于Python的Live2D桌面宠物实现\n"
            "使用PyQt5和OpenGL进行渲染\n\n"
            "基于unitychan模型展示\n"
            "© Unity Technologies Japan/UCL"
        )
        about_label.setAlignment(Qt.AlignCenter)
        about_layout.addWidget(about_label)
        
        # 空白空间
        main_layout.addStretch()
        
    def update_model_list(self, models: List[str]):
        """更新模型列表
        
        Args:
            models: 模型名称列表
        """
        self.available_models = models
        self.model_combo.clear()
        for model in models:
            self.model_combo.addItem(model)
            
    def update_settings(self, settings: Dict[str, Any]):
        """更新设置控件状态
        
        Args:
            settings: 设置字典
        """
        self.settings = settings
        
        # 更新控件状态
        self.enable_checkbox.setChecked(settings.get("enabled", True))
        
        # 模型选择
        model_path = settings.get("model_path", "")
        model_name = os.path.basename(model_path) if model_path else ""
        model_index = self.model_combo.findText(model_name)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
            
        # 窗口大小
        size = settings.get("window_width", 200)
        self.size_slider.setValue(size)
        self.size_label.setText(str(size))
        
        # 不透明度
        opacity = int(settings.get("opacity", 0.9) * 100)
        self.opacity_slider.setValue(opacity)
        self.opacity_label.setText(f"{opacity}%")
        
        # 渲染质量
        quality = settings.get("quality", "high")
        quality_index = {"high": 0, "medium": 1, "low": 2}.get(quality, 0)
        self.quality_combo.setCurrentIndex(quality_index)
        
        # 互动频率
        frequency = settings.get("interaction_frequency", 60)
        self.frequency_slider.setValue(frequency)
        self.frequency_label.setText(f"{frequency}秒")
        
        # 鼠标跟随
        self.mouse_follow_checkbox.setChecked(settings.get("mouse_follow", True))
        
        # 固定位置
        self.fixed_position_checkbox.setChecked(settings.get("fixed_position", False))
        
    def get_current_settings(self) -> Dict[str, Any]:
        """获取当前设置
        
        Returns:
            设置字典
        """
        return self.settings.copy()
        
    # 事件处理方法
    def on_enable_toggled(self, checked: bool):
        """启用/禁用桌面宠物"""
        self.settings["enabled"] = checked
        self.settings_changed.emit(self.settings)
        
    def on_model_changed(self, index: int):
        """选择不同的模型"""
        if index >= 0 and index < len(self.available_models):
            model_name = self.available_models[index]
            self.settings["model_path"] = model_name
            self.settings_changed.emit(self.settings)
            
    def on_size_changed(self, value: int):
        """调整窗口大小"""
        self.settings["window_width"] = value
        self.settings["window_height"] = int(value * 1.5)  # 保持宽高比
        self.size_label.setText(str(value))
        self.settings_changed.emit(self.settings)
        
    def on_opacity_changed(self, value: int):
        """调整不透明度"""
        opacity = value / 100.0
        self.settings["opacity"] = opacity
        self.opacity_label.setText(f"{value}%")
        self.settings_changed.emit(self.settings)
        
    def on_quality_changed(self, index: int):
        """调整渲染质量"""
        quality_map = {0: "high", 1: "medium", 2: "low"}
        self.settings["quality"] = quality_map.get(index, "high")
        self.settings_changed.emit(self.settings)
        
    def on_frequency_changed(self, value: int):
        """调整互动频率"""
        self.settings["interaction_frequency"] = value
        self.frequency_label.setText(f"{value}秒")
        self.settings_changed.emit(self.settings)
        
    def on_mouse_follow_toggled(self, checked: bool):
        """启用/禁用鼠标跟随"""
        self.settings["mouse_follow"] = checked
        self.settings_changed.emit(self.settings)
        
    def on_reset_position(self):
        """重置位置按钮点击处理"""
        # 发送重置位置信号
        self.settings["position_x"] = -1
        self.settings["position_y"] = -1
        self.settings_changed.emit(self.settings)
        
    def on_fixed_position_toggled(self, checked: bool):
        """启用/禁用固定位置"""
        self.settings["fixed_position"] = checked
        self.settings_changed.emit(self.settings)
        
    def on_test_motion(self, motion_type: str):
        """测试动作按钮点击处理"""
        # 这个信号将被外部处理逻辑捕获，播放对应动作
        self.settings_changed.emit({"test_motion": motion_type}) 