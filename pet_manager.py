import os
import time
import logging
import threading
import json
from typing import Dict, Any, Optional, Callable
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from .core.parameter import ParameterManager
from .core.window import PetWindow
from .core.renderer import Renderer
from .core.model_parser import ModelParser
from .core.motion_parser import MotionManager
from .core.physics import PhysicsSystem
from .utils.config import ConfigManager
from .utils.resource import ResourceManager

logger = logging.getLogger(__name__)


class InteractionManager(QObject):
    """交互管理器，处理桌面宠物与用户的互动"""
    
    # 定义信号
    play_motion = pyqtSignal(str)  # 播放动作
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.last_interaction_time = time.time()
        self.next_interaction_delay = self.get_random_delay()
        self.dragging = False
        self.timer = None
        
    def start(self):
        """启动互动系统"""
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.check_auto_interaction)
            self.timer.start(1000)  # 每秒检查一次
            
    def stop(self):
        """停止互动系统"""
        if self.timer:
            self.timer.stop()
            self.timer = None
            
    def check_auto_interaction(self):
        """检查是否应该自动互动"""
        if self.dragging:
            return  # 拖动中不自动互动
            
        current_time = time.time()
        if current_time - self.last_interaction_time > self.next_interaction_delay:
            self.perform_random_interaction()
            self.last_interaction_time = current_time
            self.next_interaction_delay = self.get_random_delay()
            
    def perform_random_interaction(self):
        """执行随机互动"""
        # 随机选择动作类型
        import random
        interaction_types = [
            "idle", "idle2", "talk", "expression"
        ]
        
        # 按权重随机选择
        weights = [0.4, 0.3, 0.15, 0.15]  # 各类型的权重
        selected_type = random.choices(interaction_types, weights=weights, k=1)[0]
        
        # 触发动作播放
        logger.debug(f"Auto interaction: {selected_type}")
        self.play_motion.emit(selected_type)
        
    def get_random_delay(self) -> float:
        """获取随机互动延迟
        
        Returns:
            延迟时间(秒)
        """
        import random
        base_delay = self.config_manager.get("interaction_frequency", 60)
        # 在基础延迟的基础上随机增减30%
        variation = base_delay * 0.3
        return random.uniform(base_delay - variation, base_delay + variation)
        
    def mouse_pressed(self, x: int, y: int, button: int):
        """处理鼠标按下事件"""
        if button == 1:  # 左键
            self.dragging = True
            # 播放触摸动作
            self.play_motion.emit("expression")
            
    def mouse_released(self, x: int, y: int, button: int):
        """处理鼠标释放事件"""
        if button == 1:  # 左键
            self.dragging = False
            # 恢复待机动作
            self.play_motion.emit("idle")
            
    def mouse_moved(self, x: int, y: int):
        """处理鼠标移动事件"""
        # 如果启用了视线跟随，可以在这里实现
        pass


class PetManager(QObject):
    """桌面宠物管理器 - 整个系统的核心控制器"""
    
    # 定义信号
    settings_updated = pyqtSignal(dict)  # 设置更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化资源管理器
        self.resource_manager = ResourceManager()
        
        # 初始化参数管理器
        self.parameter_manager = ParameterManager()
        
        # 初始化渲染器
        self.renderer = Renderer(self.parameter_manager)
        
        # 初始化模型解析器
        self.model_parser = ModelParser()
        
        # 初始化物理系统
        self.physics_system = PhysicsSystem(self.parameter_manager)
        
        # 初始化动作管理器
        self.motion_manager = MotionManager(self.parameter_manager)
        
        # 初始化交互管理器
        self.interaction_manager = InteractionManager(self.config_manager)
        self.interaction_manager.play_motion.connect(self.play_motion)
        
        # 窗口和渲染相关
        self.window = None
        self.render_timer = None
        self.update_timer = None
        self.stop_flag = False
        self.last_update_time = time.time()
        
        # 事件回调
        self.on_settings_callback = None
        self.on_exit_callback = None
        
    def setup_window_events(self):
        """设置窗口事件处理"""
        if not self.window:
            return
            
        # 设置窗口菜单回调
        self.window.on_settings = self.show_settings
        self.window.on_exit = self.exit
        
        # 连接鼠标事件
        self.window.mouse_pressed.connect(self.interaction_manager.mouse_pressed)
        self.window.mouse_released.connect(self.interaction_manager.mouse_released)
        self.window.mouse_moved.connect(self.interaction_manager.mouse_moved)
        
    def start(self):
        """启动桌面宠物"""
        if not self.config_manager.get("enabled", True):
            logger.info("Desktop pet is disabled in settings")
            return
            
        if self.window:
            logger.warning("Desktop pet is already running")
            self.window.show()  # 确保窗口可见
            self.window.raise_()  # 将窗口提升到前面
            return
            
        try:
            # 创建窗口
            width = self.config_manager.get("window_width", 400)
            height = self.config_manager.get("window_height", 600)
            self.window = PetWindow(width, height)
            
            # 设置窗口事件
            self.setup_window_events()
            
            # 设置渲染器
            self.window.setup_renderer(self.renderer)
            
            # 获取模型路径
            model_path = self.config_manager.get("model_path", "")
            
            # 如果配置中没有模型路径，尝试默认路径
            if not model_path or not os.path.exists(model_path):
                possible_paths = [
                    "./Unitychan/runtime/unitychan.model3.json",
                    os.path.join(os.getcwd(), "models/Unitychan/runtime/unitychan.model3.json"),
                    os.path.join(os.getcwd(), "Unitychan/runtime/unitychan.model3.json")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        model_path = path
                        self.config_manager.set("model_path", model_path)
                        logger.info(f"找到模型: {model_path}")
                        break
            
            # 加载模型
            if not model_path or not os.path.exists(model_path):
                # 模型不存在，显示错误
                logger.error(f"找不到模型文件: {model_path}")
                self.show_model_error(model_path)
                self.window.close()
                self.window = None
                return
            
            # 显式加载模型，传递模型路径参数
            if not self.load_model(model_path):
                # 模型加载失败，清理资源
                self.window.close()
                self.window = None
                return
            
            # 设置窗口不透明度
            opacity = self.config_manager.get("opacity", 0.9)
            self.window.set_opacity(opacity)
            
            # 显示窗口并确保它可见
            self.window.show()
            self.window.raise_()
            
            # 设置窗口位置
            fixed_position = self.config_manager.get("fixed_position", False)
            if not fixed_position:
                self.window.reset_position()
            else:
                x = self.config_manager.get("position_x", 0)
                y = self.config_manager.get("position_y", 0)
                self.window.move(x, y)
            
            # 延迟启动渲染
            QTimer.singleShot(300, self._start_rendering)  # 增加延迟时间
            
            # 启动交互系统
            self.interaction_manager.start()
            
            logger.info("Desktop pet started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start desktop pet: {e}")
            import traceback
            logger.error(traceback.format_exc())
            if self.window:
                self.window.close()
                self.window = None
                
    def _start_rendering(self):
        """延迟启动渲染和更新定时器"""
        if not self.window or self.stop_flag:
            return
        
        # 确保先停止已有的定时器
        if hasattr(self, 'render_timer') and self.render_timer:
            self.render_timer.stop()
            self.render_timer = None
            
        if hasattr(self, 'update_timer') and self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        
        self.stop_flag = False
        
        # 使用QTimer替代线程，采用单一定时器模式
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self._process_frame)
        self.render_timer.start(16)  # 约60FPS
        
        logging.info("渲染和更新定时器已启动")
        
    def _process_frame(self):
        """处理单一帧的渲染和更新"""
        if self.stop_flag:
            return
            
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        
        # 更新逻辑 - 限制更新频率
        if delta_time >= 0.033:  # 约30FPS的更新频率
            # 更新动作和物理
            self.motion_manager.update(delta_time)
            self.physics_system.update(delta_time)
            self.last_update_time = current_time
        
        # 渲染
        self.render_frame()
        
    def stop(self):
        """停止桌面宠物"""
        if self.window is None:
            return
            
        # 设置停止标志
        self.stop_flag = True
        
        # 停止定时器
        if hasattr(self, 'render_timer') and self.render_timer:
            self.render_timer.stop()
            self.render_timer = None
        
        if hasattr(self, 'update_timer') and self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        
        # 停止交互系统
        self.interaction_manager.stop()
        
        # 保存当前位置
        if self.window:
            pos = self.window.pos()
            self.config_manager.set("position_x", pos.x())
            self.config_manager.set("position_y", pos.y())
            self.config_manager.save_config()
            
            # 清理OpenGL资源
            try:
                if hasattr(self.window, 'gl_widget') and self.window.gl_widget:
                    self.window.gl_widget.makeCurrent()
                    if hasattr(self.renderer, 'cleanup'):
                        self.renderer.cleanup()
                    self.window.gl_widget.doneCurrent()
            except Exception as e:
                logger.error(f"Error cleaning up OpenGL resources: {e}")
            
            # 关闭窗口
            self.window.close()
            self.window = None
            
        logger.info("Desktop pet stopped")
        
    def load_model(self, model_path):
        """加载模型"""
        try:
            if not os.path.exists(model_path):
                logging.error(f"模型文件不存在: {model_path}")
                return False
                
            with open(model_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
                
            # 添加模型目录路径用于纹理加载
            model_dir = os.path.dirname(os.path.abspath(model_path))
            model_data["__model_dir__"] = model_dir
            
            # 检查并预处理所有纹理路径
            if "Parts" in model_data:
                for part in model_data["Parts"]:
                    if "TexturePath" in part:
                        texture_path = part["TexturePath"]
                        if texture_path and not os.path.isabs(texture_path):
                            # 构建相对于模型文件的绝对路径
                            abs_texture_path = os.path.join(model_dir, texture_path)
                            if os.path.exists(abs_texture_path):
                                part["TexturePath"] = abs_texture_path
                                logging.debug(f"更新纹理路径: {abs_texture_path}")
            
            logging.info(f"已设置模型目录: {model_dir}")
                
            if self.is_valid_model(model_data):
                if hasattr(self, 'renderer') and self.renderer:
                    # 确保渲染器已初始化
                    if not hasattr(self.renderer, 'initialized') or not self.renderer.initialized:
                        logging.warning("渲染器未初始化，尝试初始化...")
                        self.renderer.initialize()
                        
                    self.renderer.load_model(model_data)
                    logging.info(f"模型加载成功: {model_path}")
                    return True
                else:
                    logging.error("渲染器未初始化，无法加载模型")
            else:
                logging.error(f"无效的模型文件: {model_path}")
        except Exception as e:
            logging.error(f"加载模型失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
        return False
        
    def is_valid_model(self, model_data):
        """检查模型数据是否有效
        
        Args:
            model_data: JSON格式的模型数据
            
        Returns:
            布尔值，指示模型是否有效
        """
        # 基本有效性检查
        if not isinstance(model_data, dict):
            logging.error("模型数据必须是字典类型")
            return False
            
        # 检查Parts部分
        if "Parts" not in model_data:
            logging.error("模型数据缺少Parts部分")
            return False
            
        parts = model_data.get("Parts", [])
        if not isinstance(parts, list) or len(parts) == 0:
            logging.error(f"模型数据的Parts部分无效或为空: {parts}")
            return False
            
        # 验证每个部件是否有有效的ID
        for part in parts:
            if not isinstance(part, dict):
                logging.error("部件必须是字典类型")
                return False
                
            if "Id" not in part:
                logging.error("部件缺少Id字段")
                return False
                
        # 如果通过了所有检查，则模型有效
        return True
        
    def setup_physics(self, physics_data):
        """设置物理系统
        
        Args:
            physics_data: 物理定义数据
        """
        # 简化实现：添加头发物理效果
        hair_group = self.physics_system.create_group("hair", "PARAM_HAIR_FRONT")
        
        # 添加质点（头发从上到下）
        hair_group.add_point(0.0, 0.0, fixed=True)  # 头顶固定点
        hair_group.add_point(0.0, -5.0)             # 中段
        hair_group.add_point(0.0, -10.0)            # 发梢
        
        # 添加弹簧（连接质点）
        hair_group.add_spring(0, 1, stiffness=0.8)
        hair_group.add_spring(1, 2, stiffness=0.7)
        
    def load_motions(self, motion_dir):
        """加载动作文件
        
        Args:
            motion_dir: 动作文件目录
        """
        if not os.path.exists(motion_dir):
            logger.error(f"Motion directory not found: {motion_dir}")
            return
        
        # 加载默认动作
        motions = self.config_manager.get("motions", {})
        
        # 尝试加载idle动作
        idle_path = os.path.join(motion_dir, motions.get("idle", "idle_01.motion3.json"))
        idle2_path = os.path.join(motion_dir, motions.get("idle2", "idle_02.motion3.json"))
        talk_path = os.path.join(motion_dir, motions.get("talk", "m_01.motion3.json"))
        expression_path = os.path.join(motion_dir, motions.get("expression", "m_02.motion3.json"))
        
        # 加载动作，如果文件存在
        loaded = False
        for path, name in [(idle_path, "idle_01"), (idle2_path, "idle_02"), 
                          (talk_path, "m_01"), (expression_path, "m_02")]:
            if os.path.exists(path):
                logger.debug(f"Loading motion: {path}")
                self.motion_manager.load_motion(path)
                loaded = True
            else:
                logger.warning(f"Motion file not found: {path}")
        
        # 如果找不到指定的动作文件，尝试加载任何可用的动作
        if not loaded:
            logger.warning("No specific motions found, trying to load any available motions")
            for filename in os.listdir(motion_dir):
                if filename.endswith(".motion3.json"):
                    path = os.path.join(motion_dir, filename)
                    logger.debug(f"Loading alternative motion: {path}")
                    self.motion_manager.load_motion(path)
                    loaded = True
                    
                    # 更新动作映射
                    name = os.path.splitext(filename)[0]
                    if "idle" in name.lower():
                        motions["idle"] = filename
                        self.config_manager.set("motions", motions)
                    elif "talk" in name.lower() or "mouth" in name.lower():
                        motions["talk"] = filename
                        self.config_manager.set("motions", motions)
                
        # 播放默认动作，找一个可用的
        try:
            if self.motion_manager.has_motion("idle_01"):
                self.motion_manager.play_motion("idle_01")
            elif self.motion_manager.has_motion("idle_02"):
                self.motion_manager.play_motion("idle_02")
            elif self.motion_manager.get_loaded_motions():  # 获取任何已加载的动作
                first_motion = list(self.motion_manager.get_loaded_motions())[0]
                self.motion_manager.play_motion(first_motion)
        except Exception as e:
            logger.error(f"Error playing initial motion: {e}")
        
    def render_frame(self):
        """渲染单帧"""
        if not self.window or self.stop_flag:
            return
        
        # 更严格地检查窗口是否准备好
        if not self.window.isVisible() or not hasattr(self.window, 'gl_widget') or not self.window.gl_widget.isValid():
            # 窗口未准备好，跳过渲染
            return
        
        try:
            # 使用窗口的OpenGL上下文
            self.window.gl_widget.makeCurrent()
            
            # 检查渲染器是否初始化
            if not hasattr(self.renderer, 'initialized') or not self.renderer.initialized:
                logging.warning("渲染器未初始化，跳过渲染")
                self.window.gl_widget.doneCurrent()
                return
                
            # 尝试渲染
            try:
                self.renderer.render()
            except Exception as e:
                logging.error(f"渲染错误: {e}")
                import traceback
                logging.error(traceback.format_exc())
            
            # 交换缓冲区
            self.window.gl_widget.swapBuffers()
            
            # 释放上下文
            self.window.gl_widget.doneCurrent()
        except Exception as e:
            logging.error(f"渲染框架错误: {e}")
            # 尝试恢复
            try:
                if hasattr(self.window, 'gl_widget'):
                    self.window.gl_widget.doneCurrent()
            except:
                pass
        
    def update_settings(self, settings):
        """更新设置
        
        Args:
            settings: 新的设置值
        """
        # 处理特殊设置
        if "test_motion" in settings:
            self.play_motion(settings["test_motion"])
            return
            
        # 更新配置
        for key, value in settings.items():
            self.config_manager.set(key, value)
            
        # 保存配置
        self.config_manager.save_config()
        
        # 应用更改
        self.apply_settings()
        
        # 触发设置更新事件
        self.settings_updated.emit(self.config_manager.get_all())
        
    def apply_settings(self):
        """应用当前设置"""
        if not self.window:
            # 如果窗口不存在但设置为启用，则启动
            if self.config_manager.get("enabled", True):
                self.start()
            return
            
        # 如果设置为禁用，则停止
        if not self.config_manager.get("enabled", True):
            self.stop()
            return
            
        # 更新窗口大小
        width = self.config_manager.get("window_width", 400)
        height = self.config_manager.get("window_height", 600)
        self.window.set_size(width, height)
        
        # 更新不透明度
        opacity = self.config_manager.get("opacity", 0.9)
        self.window.set_opacity(opacity)
        
        # 更新渲染质量
        quality = self.config_manager.get("quality", "high")
        self.renderer.set_quality(quality)
        
        # 更新位置
        if self.config_manager.get("position_x", -1) == -1:
            self.window.reset_position()
            
    def play_motion(self, motion_type):
        """播放指定类型的动作
        
        Args:
            motion_type: 动作类型
        """
        motions = self.config_manager.get("motions", {})
        motion_file = motions.get(motion_type, "")
        
        if not motion_file:
            logger.warning(f"Motion type not defined: {motion_type}")
            return
            
        logger.debug(f"Playing motion: {motion_type} ({motion_file})")
        
        # 提取文件名（不含后缀）
        motion_name = os.path.splitext(os.path.basename(motion_file))[0]
        
        # 播放动作
        self.motion_manager.play_motion(motion_name)
            
    def show_settings(self):
        """显示设置对话框"""
        if self.on_settings_callback:
            self.on_settings_callback()
            
    def exit(self):
        """退出应用程序"""
        self.stop()
        if self.on_exit_callback:
            self.on_exit_callback()
            
    def scan_available_models(self):
        """扫描可用的模型
        
        Returns:
            模型列表
        """
        models_dir = os.path.dirname(self.config_manager.get("model_path", "./"))
        return self.resource_manager.scan_models(models_dir)
        
    def register_settings_callback(self, callback: Callable):
        """注册设置菜单回调
        
        Args:
            callback: 回调函数
        """
        self.on_settings_callback = callback
        
    def register_exit_callback(self, callback: Callable):
        """注册退出菜单回调
        
        Args:
            callback: 回调函数
        """
        self.on_exit_callback = callback
        
    def handle_voice_assistant_event(self, event_type: str, data: Any = None):
        """处理语音助手事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        # 根据事件类型播放相应动作
        if event_type == "listening":
            self.play_motion("talk")
        elif event_type == "thinking":
            self.play_motion("idle2")
        elif event_type == "speaking":
            self.play_motion("talk")
        elif event_type == "idle":
            self.play_motion("idle")
        
    def ensure_model_directory(self):
        """确保模型目录存在，必要时创建"""
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
            logger.info(f"创建模型目录: {model_dir}")
            
        # 可以在这里添加自动下载模型的代码
        
    def show_model_error(self, model_path):
        """显示模型错误信息"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("模型加载错误")
        msg.setText(f"找不到模型文件: {model_path}")
        msg.setInformativeText("请检查模型路径设置，或确保模型文件存在。")
        
        # 添加详细的搜索路径信息
        search_paths = "\n".join([
            f"- {path}" for path in [
                "./Unitychan/runtime/unitychan.model3.json",
                os.path.join(os.getcwd(), "models/Unitychan/runtime/unitychan.model3.json"),
                os.path.join(os.getcwd(), "Unitychan/runtime/unitychan.model3.json")
            ]
        ])
        msg.setDetailedText(f"应用程序尝试加载的模型路径是: {model_path}\n"
                             f"尝试过的其他路径:\n{search_paths}\n\n"
                             f"您可以下载Unitychan模型并放置在以上任一位置。")
        msg.exec_()
        
    def debug_model_status(self):
        """显示模型状态信息"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not hasattr(self, 'model_parser') or not hasattr(self, 'renderer'):
            QMessageBox.information(None, "模型状态", "模型组件未初始化")
            return
        
        model_path = self.config_manager.get("model_path", "未设置")
        model_exists = "是" if os.path.exists(model_path) else "否"
        
        renderer_initialized = "是" if hasattr(self.renderer, 'initialized') and self.renderer.initialized else "否"
        window_visible = "是" if self.window and self.window.isVisible() else "否"
        
        motions = self.motion_manager.get_loaded_motions() if hasattr(self, 'motion_manager') else []
        
        info_text = (
            f"模型路径: {model_path}\n"
            f"模型文件存在: {model_exists}\n"
            f"渲染器初始化: {renderer_initialized}\n"
            f"窗口可见: {window_visible}\n"
            f"已加载动作数量: {len(motions)}\n"
        )
        
        QMessageBox.information(None, "模型状态", info_text) 