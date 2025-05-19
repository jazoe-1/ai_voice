import sys
import os
import logging
import traceback
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtCore import QTimer

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建一个日志处理器，将日志输出到UI
class QTextEditLogger(logging.Handler):
    def __init__(self, textEdit):
        super().__init__()
        self.textEdit = textEdit
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
    def emit(self, record):
        msg = self.format(record)
        self.textEdit.append(msg)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌面宠物测试")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 添加日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)
        
        # 设置日志处理器
        log_handler = QTextEditLogger(self.log_display)
        logging.getLogger().addHandler(log_handler)
        
        # 添加按钮
        self.start_btn = QPushButton("启动宠物")
        self.start_btn.clicked.connect(self.start_pet)
        layout.addWidget(self.start_btn)
        
        self.check_env_btn = QPushButton("检查环境")
        self.check_env_btn.clicked.connect(self.check_environment)
        layout.addWidget(self.check_env_btn)
        
        self.check_model_btn = QPushButton("检查模型文件")
        self.check_model_btn.clicked.connect(self.check_model_files)
        layout.addWidget(self.check_model_btn)
        
        self.stop_btn = QPushButton("停止宠物")
        self.stop_btn.clicked.connect(self.stop_pet)
        layout.addWidget(self.stop_btn)
        
        self.debug_btn = QPushButton("调试宠物状态")
        self.debug_btn.clicked.connect(self.debug_pet)
        layout.addWidget(self.debug_btn)
        
        # 宠物管理器
        self.pet_manager = None
        
        logging.info("测试窗口初始化完成")
        
    def check_environment(self):
        """检查运行环境"""
        try:
            logging.info("=== 检查OpenGL环境 ===")
            from OpenGL.GL import glGetString, GL_VENDOR, GL_RENDERER, GL_VERSION
            
            # 需要一个有效的OpenGL上下文来获取这些信息
            # 这里创建一个临时的OpenGL widget
            from PyQt5.QtOpenGL import QGLWidget
            temp_gl = QGLWidget()
            temp_gl.makeCurrent()
            
            try:
                vendor = glGetString(GL_VENDOR).decode('utf-8')
                renderer = glGetString(GL_RENDERER).decode('utf-8')
                version = glGetString(GL_VERSION).decode('utf-8')
                
                logging.info(f"OpenGL 供应商: {vendor}")
                logging.info(f"OpenGL 渲染器: {renderer}")
                logging.info(f"OpenGL 版本: {version}")
            except Exception as e:
                logging.error(f"无法获取OpenGL信息: {e}")
                
            temp_gl.doneCurrent()
            
            # 检查PyQt版本
            from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            logging.info(f"Qt版本: {QT_VERSION_STR}")
            logging.info(f"PyQt版本: {PYQT_VERSION_STR}")
            
            # 检查其他核心模块
            logging.info("=== 检查核心模块 ===")
            try:
                from desktop_pet.core.renderer import Renderer
                logging.info("Renderer模块可用")
            except Exception as e:
                logging.error(f"Renderer模块导入失败: {e}")
                
            try:
                from desktop_pet.core.model_parser import ModelParser
                logging.info("ModelParser模块可用")
            except Exception as e:
                logging.error(f"ModelParser模块导入失败: {e}")
                
            try:
                from desktop_pet.core.window import PetWindow
                logging.info("PetWindow模块可用")
            except Exception as e:
                logging.error(f"PetWindow模块导入失败: {e}")
        except Exception as e:
            logging.error(f"环境检查失败: {e}")
            logging.error(traceback.format_exc())
            
    def check_model_files(self):
        """检查模型文件"""
        try:
            # 检查默认模型路径
            model_path = "./Unitychan/runtime/unitychan.model3.json"
            if os.path.exists(model_path):
                logging.info(f"模型文件存在: {model_path}")
                # 检查模型文件结构
                try:
                    import json
                    with open(model_path, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                    
                    logging.info(f"模型版本: {model_data.get('Version')}")
                    
                    # 检查纹理文件
                    textures = model_data.get("FileReferences", {}).get("Textures", [])
                    logging.info(f"纹理数量: {len(textures)}")
                    
                    for i, texture in enumerate(textures):
                        texture_path = os.path.join(os.path.dirname(model_path), texture)
                        if os.path.exists(texture_path):
                            logging.info(f"纹理{i+1}存在: {texture}")
                        else:
                            logging.error(f"纹理{i+1}不存在: {texture}")
                            
                    # 检查动作文件
                    motion_dir = os.path.join(os.path.dirname(model_path), "motion")
                    if os.path.exists(motion_dir):
                        motion_files = [f for f in os.listdir(motion_dir) if f.endswith(".motion3.json")]
                        logging.info(f"动作文件数量: {len(motion_files)}")
                    else:
                        logging.error(f"动作目录不存在: {motion_dir}")
                except Exception as e:
                    logging.error(f"模型文件解析失败: {e}")
            else:
                logging.error(f"模型文件不存在: {model_path}")
                
            # 检查其他可能的位置
            alt_paths = [
                "./models",
                "../models",
                "Unitychan"
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    logging.info(f"目录存在: {path}")
                    if os.path.isdir(path):
                        files = os.listdir(path)
                        logging.info(f"{path}中的文件: {', '.join(files) if files else '空目录'}")
                else:
                    logging.info(f"目录不存在: {path}")
        except Exception as e:
            logging.error(f"检查模型文件失败: {e}")
            logging.error(traceback.format_exc())
        
    def start_pet(self):
        """启动桌面宠物"""
        try:
            logging.info("=== 开始启动桌面宠物 ===")
            
            # 分步骤导入并初始化
            try:
                logging.info("导入PetManager...")
                from desktop_pet.pet_manager import PetManager
                
                if not self.pet_manager:
                    logging.info("创建PetManager实例...")
                    self.pet_manager = PetManager()
                    
                # 检查配置
                config = self.pet_manager.config_manager.get_all()
                logging.info(f"配置中的模型路径: {config.get('model_path')}")
                
                # 启动宠物
                logging.info("调用start()方法...")
                self.pet_manager.start()
                logging.info("桌面宠物启动完成")
                
                # 延迟检查窗口状态
                QTimer.singleShot(1000, self.check_window_status)
            except Exception as e:
                logging.error(f"桌面宠物启动失败: {e}")
                logging.error(traceback.format_exc())
        except Exception as e:
            logging.error(f"启动宠物过程中发生未捕获异常: {e}")
            logging.error(traceback.format_exc())
            
    def check_window_status(self):
        """检查窗口状态"""
        try:
            if not self.pet_manager or not hasattr(self.pet_manager, 'window'):
                logging.error("宠物窗口未创建")
                return
                
            window = self.pet_manager.window
            if window is None:
                logging.error("宠物窗口为None")
                return
                
            logging.info(f"窗口可见性: {window.isVisible()}")
            logging.info(f"窗口位置: ({window.x()}, {window.y()})")
            logging.info(f"窗口大小: {window.width()}x{window.height()}")
            
            if hasattr(window, 'gl_widget'):
                logging.info("OpenGL窗口已创建")
                logging.info(f"GL窗口有效: {window.gl_widget.isValid()}")
            else:
                logging.error("OpenGL窗口未创建")
                
            # 检查渲染器状态
            if hasattr(self.pet_manager, 'renderer'):
                logging.info(f"渲染器初始化: {self.pet_manager.renderer.initialized}")
            else:
                logging.error("渲染器未创建")
        except Exception as e:
            logging.error(f"检查窗口状态失败: {e}")
            logging.error(traceback.format_exc())
            
    def stop_pet(self):
        """停止桌面宠物"""
        try:
            if self.pet_manager:
                logging.info("正在停止桌面宠物...")
                self.pet_manager.stop()
                logging.info("桌面宠物已停止")
            else:
                logging.warning("桌面宠物管理器未初始化，无需停止")
        except Exception as e:
            logging.error(f"停止宠物失败: {e}")
            logging.error(traceback.format_exc())
            
    def debug_pet(self):
        """调试桌面宠物状态"""
        try:
            if self.pet_manager:
                logging.info("调试桌面宠物状态...")
                self.pet_manager.debug_model_status()
            else:
                logging.error("宠物管理器未初始化")
        except Exception as e:
            logging.error(f"调试宠物状态失败: {e}")
            logging.error(traceback.format_exc())
            
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            logging.info("正在关闭测试窗口...")
            self.stop_pet()
        except Exception as e:
            logging.error(f"关闭事件处理失败: {e}")
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 