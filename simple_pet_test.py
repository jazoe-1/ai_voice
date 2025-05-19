import sys
import os
import time
import logging
import traceback
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer, Qt
from PIL import Image
import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
from typing import Optional
import ctypes
import math
import json

# 创建QApplication实例
app = QApplication.instance() or QApplication(sys.argv)

# Define transform matrix function
def create_transform_matrix(tx=0, ty=0, rotation=0, sx=1, sy=1):
    """创建变换矩阵"""
    # 创建单位矩阵
    matrix = np.identity(4, dtype=np.float32)
    
    # 缩放
    matrix[0, 0] = sx
    matrix[1, 1] = sy
    
    # 旋转 (围绕Z轴)
    if rotation != 0:
        cos_r = math.cos(rotation)
        sin_r = math.sin(rotation)
        rot_matrix = np.identity(4, dtype=np.float32)
        rot_matrix[0, 0] = cos_r
        rot_matrix[0, 1] = -sin_r
        rot_matrix[1, 0] = sin_r
        rot_matrix[1, 1] = cos_r
        matrix = np.matmul(matrix, rot_matrix)
    
    # 平移
    matrix[0, 3] = tx
    matrix[1, 3] = ty
    
    return matrix

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pet_debug.log", encoding="utf-8")
    ]
)

def check_file_exists(filepath):
    """检查文件是否存在并记录"""
    exists = os.path.exists(filepath)
    logging.info(f"文件检查: {filepath} 存在: {exists}")
    return exists

def check_imports():
    """检查关键导入是否可用"""
    try:
        logging.info("=== 检查关键模块导入 ===")
        
        # 检查OpenGL
        try:
            import OpenGL
            logging.info(f"OpenGL版本: {OpenGL.__version__}")
            
            from OpenGL.GL import glGetString, GL_VENDOR, GL_RENDERER, GL_VERSION
            logging.info("OpenGL.GL模块可用")
        except Exception as e:
            logging.error(f"OpenGL导入失败: {e}")
        
        # 检查PIL
        try:
            from PIL import Image
            logging.info(f"PIL可用")
        except Exception as e:
            logging.error(f"PIL导入失败: {e}")
        
        # 检查核心模块
        try:
            from desktop_pet.core.parameter import ParameterManager
            logging.info("ParameterManager模块可用")
        except Exception as e:
            logging.error(f"ParameterManager模块导入失败: {e}")
            
        try:
            from desktop_pet.core.window import PetWindow
            logging.info("PetWindow模块可用")
        except Exception as e:
            logging.error(f"PetWindow模块导入失败: {e}")
            
        try:
            from desktop_pet.core.renderer import Renderer
            logging.info("Renderer模块可用")
        except Exception as e:
            logging.error(f"Renderer模块导入失败: {e}")
            
        try:
            from desktop_pet.pet_manager import PetManager
            logging.info("PetManager模块可用")
        except Exception as e:
            logging.error(f"PetManager模块导入失败: {e}")
            logging.error(traceback.format_exc())
    except Exception as e:
        logging.error(f"检查导入失败: {e}")
        logging.error(traceback.format_exc())

def check_opengl_context():
    """检查OpenGL上下文"""
    try:
        from PyQt5.QtOpenGL import QGLWidget
        from OpenGL.GL import glGetString, GL_VENDOR, GL_RENDERER, GL_VERSION
        
        # 创建临时窗口以提供OpenGL上下文
        temp_widget = QGLWidget()
        temp_widget.show()  # 必须显示才能创建有效上下文
        app.processEvents()  # 处理事件以确保显示
        temp_widget.makeCurrent()
        
        vendor = glGetString(GL_VENDOR)
        if vendor:
            vendor = vendor.decode('utf-8')
        
        renderer = glGetString(GL_RENDERER)
        if renderer:
            renderer = renderer.decode('utf-8')
        
        version = glGetString(GL_VERSION)
        if version:
            version = version.decode('utf-8')
        
        logging.info(f"OpenGL供应商: {vendor}")
        logging.info(f"OpenGL渲染器: {renderer}")
        logging.info(f"OpenGL版本: {version}")
        
        temp_widget.doneCurrent()
        temp_widget.hide()
    except Exception as e:
        logging.error(f"OpenGL上下文检查失败: {e}")
        logging.error(traceback.format_exc())

def check_paths():
    """检查关键路径"""
    logging.info("=== 检查关键路径 ===")
    desktop_pet_dir = os.path.join(os.getcwd(), "desktop_pet")
    check_file_exists(desktop_pet_dir)
    
    core_dir = os.path.join(desktop_pet_dir, "core")
    check_file_exists(core_dir)
    
    renderer_path = os.path.join(core_dir, "renderer.py")
    check_file_exists(renderer_path)
    
    window_path = os.path.join(core_dir, "window.py")
    check_file_exists(window_path)
    
    model_dirs = [
        os.path.join(os.getcwd(), "Unitychan"),
        os.path.join(os.getcwd(), "models", "Unitychan"),
    ]
    
    for dir_path in model_dirs:
        if check_file_exists(dir_path):
            runtime_dir = os.path.join(dir_path, "runtime")
            if check_file_exists(runtime_dir):
                model_path = os.path.join(runtime_dir, "unitychan.model3.json")
                check_file_exists(model_path)

def create_config_file():
    """创建桌面宠物配置文件"""
    try:
        config_path = os.path.expanduser("~/.desktop_pet_config.json")
        
        # 基本配置
        config = {
            "enabled": True,
            "window_width": 400,
            "window_height": 600,
            "opacity": 0.9,
            "quality": "medium",
            "model_path": "./Unitychan/runtime/unitychan.model3.json",
            "debug_mode": True,
            "render_delay": 50,
            "update_delay": 100
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
        logging.info(f"创建配置文件: {config_path}")
    except Exception as e:
        logging.error(f"创建配置文件失败: {e}")

def initialize_pet_manager():
    """初始化并测试PetManager"""
    try:
        logging.info("=== 开始初始化PetManager ===")
        
        # 创建配置文件
        create_config_file()
        
        # 导入PetManager
        from desktop_pet.pet_manager import PetManager
        
        # 创建PetManager实例
        logging.info("创建PetManager实例...")
        pet_manager = PetManager()
        
        # 添加各种回调以显示更多信息
        def on_settings():
            logging.info("设置菜单点击")
        
        def on_exit():
            logging.info("退出菜单点击")
            
        pet_manager.register_settings_callback(on_settings)
        pet_manager.register_exit_callback(on_exit)
        
        # 启动桌面宠物
        logging.info("启动桌面宠物...")
        pet_manager.start()
        
        # 创建一个简单的主窗口
        main_window = QMainWindow()
        main_window.setWindowTitle("桌面宠物测试")
        main_window.setGeometry(100, 100, 300, 200)
        
        central_widget = QWidget()
        main_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        stop_btn = QPushButton("停止宠物")
        stop_btn.clicked.connect(pet_manager.stop)
        layout.addWidget(stop_btn)
        
        debug_btn = QPushButton("调试状态")
        debug_btn.clicked.connect(pet_manager.debug_model_status)
        layout.addWidget(debug_btn)
        
        main_window.show()
        
        # 设置应用程序退出清理
        app.aboutToQuit.connect(pet_manager.stop)
        
        # 延迟检查状态
        def check_pet_status():
            logging.info("=== 桌面宠物状态检查 ===")
            if hasattr(pet_manager, 'window') and pet_manager.window:
                logging.info(f"窗口对象: {pet_manager.window}")
                logging.info(f"窗口可见性: {pet_manager.window.isVisible()}")
                
                if hasattr(pet_manager.window, 'gl_widget'):
                    logging.info(f"GL部件存在: 是")
                    logging.info(f"GL部件有效: {pet_manager.window.gl_widget.isValid()}")
                else:
                    logging.info("GL部件存在: 否")
            else:
                logging.info("窗口未创建")
                
            if hasattr(pet_manager, 'renderer'):
                logging.info(f"渲染器存在: 是")
                logging.info(f"渲染器初始化: {getattr(pet_manager.renderer, 'initialized', False)}")
            else:
                logging.info("渲染器未创建")
        
        QTimer.singleShot(1000, check_pet_status)
        
        # 运行应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        logging.error(f"PetManager初始化失败: {e}")
        logging.error(traceback.format_exc())

def main():
    """主函数"""
    logging.info("开始桌面宠物测试")
    
    # 检查关键模块导入
    check_imports()
    
    # 检查OpenGL上下文
    check_opengl_context()
    
    # 检查关键路径
    check_paths()
    
    # 初始化PetManager
    initialize_pet_manager()

def render(self):
    """优化的渲染循环"""
    if not self.initialized or not self.parts:
        return
        
    # 清除缓冲区
    glClear(GL_COLOR_BUFFER_BIT)
    
    # 使用着色器程序
    glUseProgram(self.shader_program)
    
    # 按深度排序部件
    sorted_parts = sorted(self.parts.values(), key=lambda p: p.get("depth", 0))
    
    # 预计算常用uniform位置
    texture_loc = glGetUniformLocation(self.shader_program, "textureSampler")
    alpha_loc = glGetUniformLocation(self.shader_program, "alpha")
    transform_loc = glGetUniformLocation(self.shader_program, "transform")
    
    # 绑定VAO
    glBindVertexArray(self.vao)
    
    # 渲染每个部件
    for part in sorted_parts:
        if not part.get("visible", True):
            continue
            
        # 计算alpha值
        alpha = part.get("opacity", 1.0)
        for deformer in part.get("deformers", []):
            if deformer.get("type") == "opacity":
                param_value = self.parameter_manager.get_parameter(
                    deformer.get("parameter", ""), 0.0)
                alpha *= (1.0 + param_value * deformer.get("scale", 0.0))
        alpha = max(0.0, min(1.0, alpha))
        
        # 设置uniforms
        glUniform1f(alpha_loc, alpha)
        
        # 创建并设置变换矩阵
        transform = create_transform_matrix(0.0, 0.0, 0.0, 1.0, 1.0)
        glUniformMatrix4fv(transform_loc, 1, GL_FALSE, transform)
        
        # 绑定纹理
        if "texture" in part:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, part["texture"].id)
            glUniform1i(texture_loc, 0)
        
        # 绘制
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
    
    # 清理状态
    glBindVertexArray(0)
    glUseProgram(0)

def initialize(self):
    """优化的OpenGL初始化"""
    try:
        # 初始化OpenGL
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        
        # 创建和编译着色器
        self.shader_program = self._compile_shaders()
        
        # 创建VAO和VBO
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)
        
        # 设置顶点属性
        glBindVertexArray(self.vao)
        
        # 位置属性
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        # 纹理坐标属性
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 20, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        
        # 解绑
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        
        self.initialized = True
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize OpenGL: {e}")
        self.cleanup()
        return False

def cleanup(self):
    """优化的资源清理"""
    try:
        if hasattr(self, 'shader_program') and self.shader_program:
            glDeleteProgram(self.shader_program)
            self.shader_program = None
            
        if hasattr(self, 'vao') and self.vao:
            glDeleteVertexArrays(1, [self.vao])
            self.vao = None
            
        if hasattr(self, 'vbo') and self.vbo:
            glDeleteBuffers(1, [self.vbo])
            self.vbo = None
            
        if hasattr(self, 'ebo') and self.ebo:
            glDeleteBuffers(1, [self.ebo])
            self.ebo = None
            
        # 清理纹理缓存
        if hasattr(self, 'texture_manager'):
            self.texture_manager.clear_cache()
            
        # 清理部件数据
        if hasattr(self, 'parts'):
            self.parts.clear()
            
        self.initialized = False
        
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

def edit_pet_window():
    from desktop_pet.core.window import PetWindow
    
    # 在PetWindow类的show方法中添加以下内容
    def show(self):
        super().show()
        # 强制窗口显示在最前面并设置为活动窗口
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.activateWindow()  # 确保窗口获得焦点
        self.raise_()  # 将窗口提升到顶层
        # 记录窗口显示状态
        logging.info(f"窗口显示状态: isVisible={self.isVisible()}, isActiveWindow={self.isActiveWindow()}")

def force_window_visibility(pet_manager):
    """强制窗口显示在最前面"""
    if pet_manager and hasattr(pet_manager, 'window') and pet_manager.window:
        pet_manager.window.setWindowState(Qt.WindowActive)
        pet_manager.window.show()
        pet_manager.window.activateWindow()
        pet_manager.window.raise_()
        logging.info("已强制窗口显示")

if __name__ == "__main__":
    """主程序入口点"""
    logging.info("=== 开始初始化 ===")
    
    # 必要的QApplication实例
    app = QApplication.instance() or QApplication(sys.argv)
    
    # 创建临时OpenGL上下文以确保系统支持OpenGL
    from PyQt5.QtOpenGL import QGLWidget
    temp_gl = QGLWidget()
    temp_gl.makeCurrent()
    logging.info("已创建临时OpenGL上下文")
    
    # 检查模型文件是否存在
    model_path = "./Unitychan/runtime/unitychan.model3.json"
    if not os.path.exists(model_path):
        logging.error(f"模型文件不存在: {model_path}")
        # 尝试其他可能的路径
        alt_paths = [
            os.path.join(os.getcwd(), "models/Unitychan/runtime/unitychan.model3.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "Unitychan/runtime/unitychan.model3.json")
        ]
        for path in alt_paths:
            if os.path.exists(path):
                model_path = path
                logging.info(f"使用替代模型路径: {model_path}")
                break
        else:
            logging.error("无法找到模型文件，程序将退出")
            sys.exit(1)
    
    # 创建配置文件确保其存在
    create_config_file()
    
    # 简化初始化流程
    from desktop_pet.pet_manager import PetManager
    pet_manager = PetManager()
    
    # 释放临时上下文
    temp_gl.doneCurrent()
    temp_gl = None
    
    # 启动桌面宠物，会自动搜索和加载模型
    pet_manager.start()
    
    # 强制窗口可见
    QTimer.singleShot(1000, lambda: force_window_visibility(pet_manager))
    
    # 添加一个定期检查窗口状态的定时器
    def check_window_status():
        if pet_manager.window:
            visible = pet_manager.window.isVisible()
            logging.info(f"窗口可见状态: {visible}")
            if not visible:
                force_window_visibility(pet_manager)
    
    status_timer = QTimer()
    status_timer.timeout.connect(check_window_status)
    status_timer.start(3000)  # 每3秒检查一次
    
    # 运行应用程序
    logging.info("开始事件循环")
    sys.exit(app.exec_()) 