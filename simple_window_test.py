import sys
import os
import logging
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtOpenGL import QGLWidget
from OpenGL.GL import *
from OpenGL.GL import shaders
from PIL import Image

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_window_test')

class SimpleGLWidget(QGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 600)
        self.texture_id = None
        self.shader_program = None
        self.vao = None
        self.vbo = None
        self.ebo = None
        self.logger = logging.getLogger('simple_window_test')
        
    def initializeGL(self):
        """初始化OpenGL"""
        self.logger.info("初始化OpenGL")
        
        # 设置清除颜色（RGBA，全透明）
        glClearColor(0.0, 0.0, 0.0, 0.0)
        
        # 启用混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # 编译着色器
        self.create_shaders()
        
        # 创建顶点缓冲区
        self.create_buffers()
        
        # 创建测试纹理
        self.create_test_texture()
        
        self.logger.info("OpenGL初始化成功")
        
    def create_shaders(self):
        """创建并编译着色器"""
        # 顶点着色器代码
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 texCoord;
        
        out vec2 fragTexCoord;
        
        void main()
        {
            gl_Position = vec4(position, 1.0);
            fragTexCoord = texCoord;
        }
        """
        
        # 片元着色器代码
        fragment_shader_source = """
        #version 330 core
        in vec2 fragTexCoord;
        
        out vec4 fragColor;
        
        uniform sampler2D texture1;
        
        void main()
        {
            fragColor = texture(texture1, fragTexCoord);
        }
        """
        
        # 编译着色器
        vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
        fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
        
        # 创建程序和链接
        self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)
        
        self.logger.info("着色器编译成功")
        
    def create_buffers(self):
        """创建顶点缓冲区"""
        # 顶点数据（位置和纹理坐标）
        vertices = np.array([
            # 位置(x,y,z)      # 纹理坐标(u,v)
            -0.8, -0.8, 0.0,    0.0, 1.0,  # 左下
             0.8, -0.8, 0.0,    1.0, 1.0,  # 右下
             0.8,  0.8, 0.0,    1.0, 0.0,  # 右上
            -0.8,  0.8, 0.0,    0.0, 0.0   # 左上
        ], dtype=np.float32)
        
        # 索引数据
        indices = np.array([
            0, 1, 2,  # 第一个三角形
            2, 3, 0   # 第二个三角形
        ], dtype=np.uint32)
        
        # 创建顶点数组对象
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        # 创建并绑定顶点缓冲对象
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        # 创建并绑定索引缓冲对象
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        # 设置顶点属性指针
        # 位置属性
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, None)
        glEnableVertexAttribArray(0)
        
        # 纹理坐标属性
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        
        # 解绑顶点数组对象
        glBindVertexArray(0)
        
        self.logger.info("顶点缓冲区创建成功")
        
    def create_test_texture(self):
        """创建测试纹理"""
        # 尝试加载Unitychan模型的纹理
        model_texture_path = "./Unitychan/runtime/textures/texture_00.png"
        if os.path.exists(model_texture_path):
            try:
                image = Image.open(model_texture_path).convert("RGBA")
                # 创建OpenGL纹理
                self.texture_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, self.texture_id)
                
                # 设置纹理参数
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                
                # 加载纹理数据
                img_data = np.array(image.getdata(), np.uint8).reshape(image.height, image.width, 4)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
                
                self.logger.info(f"模型纹理加载成功: {model_texture_path}")
                return
            except Exception as e:
                self.logger.error(f"模型纹理加载失败: {e}")
        
        # 如果模型纹理加载失败，创建一个测试纹理
        # 创建测试纹理(棋盘格)
        texture_size = 64
        texture_data = np.zeros((texture_size, texture_size, 4), dtype=np.uint8)
        
        # 填充棋盘格纹理
        for y in range(texture_size):
            for x in range(texture_size):
                if (x // 8 + y // 8) % 2 == 0:
                    texture_data[y, x] = [255, 0, 0, 255]  # 红色
                else:
                    texture_data[y, x] = [255, 255, 255, 255]  # 白色
        
        # 创建OpenGL纹理
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # 加载纹理数据
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA, texture_size, texture_size, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, texture_data
        )
        
        self.logger.info("测试纹理创建成功")
        
    def paintGL(self):
        """绘制OpenGL场景"""
        # 清除颜色缓冲
        glClear(GL_COLOR_BUFFER_BIT)
        
        # 使用着色器程序
        glUseProgram(self.shader_program)
        
        # 绑定纹理
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # 绑定VAO并绘制
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        
        # 解绑VAO和纹理
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        
    def resizeGL(self, width, height):
        """处理窗口大小变化"""
        glViewport(0, 0, width, height)
        
    def cleanup(self):
        """清理OpenGL资源"""
        if self.shader_program:
            glDeleteProgram(self.shader_program)
            
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
            
        if self.vbo:
            glDeleteBuffers(1, [self.vbo])
            
        if self.ebo:
            glDeleteBuffers(1, [self.ebo])
            
        if self.texture_id:
            glDeleteTextures(1, [self.texture_id])
            
        self.logger.info("OpenGL资源已清理")

class SimpleTransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题
        self.setWindowTitle("简单透明窗口测试")
        
        # 设置窗口标志（无边框、始终保持在最前）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 设置窗口透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建OpenGL部件
        self.gl_widget = SimpleGLWidget(self)
        self.setCentralWidget(self.gl_widget)
        
        # 调整窗口大小以适应OpenGL部件
        self.resize(self.gl_widget.size())
        
        # 定时器用于更新动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gl_widget.update)
        self.timer.start(16)  # 约60fps
        
        logger.info("透明窗口创建成功")
        
    def showEvent(self, event):
        """显示窗口时的事件处理"""
        super().showEvent(event)
        logger.info("透明窗口已显示")
        
    def closeEvent(self, event):
        """关闭窗口时的事件处理"""
        self.gl_widget.cleanup()
        logger.info("透明窗口已关闭")
        super().closeEvent(event)
        
    def mousePressEvent(self, event):
        """鼠标按下事件，用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于拖动窗口"""
        if event.buttons() & Qt.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
            event.accept()

class ControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("透明窗口测试控制面板")
        self.setGeometry(100, 100, 300, 200)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建按钮
        self.create_window_btn = QPushButton("创建透明窗口")
        self.create_window_btn.clicked.connect(self.create_transparent_window)
        layout.addWidget(self.create_window_btn)
        
        # 窗口引用
        self.transparent_window = None
        
        logger.info("控制面板创建成功")
        
    def create_transparent_window(self):
        """创建透明窗口"""
        if not self.transparent_window:
            self.transparent_window = SimpleTransparentWindow()
            self.transparent_window.show()
        else:
            self.transparent_window.close()
            self.transparent_window = None
            QTimer.singleShot(500, self.create_transparent_window)

def main():
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建控制面板
    control_panel = ControlPanel()
    control_panel.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 