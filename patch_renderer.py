import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def patch_renderer_shaders():
    """修补渲染器使用更简单的着色器"""
    # 渲染器文件路径
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
        
    # 读取原始文件
    with open(renderer_path, 'r', encoding='utf-8') as f:
        renderer_code = f.read()
        
    # 创建备份
    backup_path = renderer_path + ".backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(renderer_code)
    logging.info(f"创建了渲染器备份: {backup_path}")
    
    # 查找着色器编译函数
    shader_func_pattern = r'def compile_shaders\(self\):(.*?)def'
    shader_match = re.search(shader_func_pattern, renderer_code, re.DOTALL)
    
    if not shader_match:
        logging.error("找不到着色器编译函数")
        return False
        
    # 简化的着色器代码
    simplified_shader_func = '''def compile_shaders(self):
        """编译顶点和片元着色器"""
        # 简化的顶点着色器
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 inTexCoord;
        
        out vec2 texCoord;
        
        uniform mat4 transform;
        
        void main()
        {
            gl_Position = vec4(position.x, position.y, 0.0, 1.0);
            texCoord = inTexCoord;
        }
        """

        # 简化的片元着色器
        fragment_shader_source = """
        #version 330 core
        in vec2 texCoord;
        
        out vec4 FragColor;
        
        uniform sampler2D textureSampler;
        
        void main()
        {
            FragColor = texture(textureSampler, texCoord);
        }
        """

        # 编译着色器
        try:
            vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
            self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)
            
            # 获取uniform位置
            self.transform_loc = glGetUniformLocation(self.shader_program, "transform")
            self.texture_loc = glGetUniformLocation(self.shader_program, "textureSampler")
            
            logging.info("着色器编译成功")
        except Exception as e:
            logging.error(f"Error compiling shaders: {e}")
            raise

    def'''
    
    # 替换着色器函数
    updated_code = re.sub(shader_func_pattern, simplified_shader_func, renderer_code, flags=re.DOTALL)
    
    # 将window属性强制设置为visible
    window_visible_pattern = r'(def isValid.*?return )(.*?)(\s+and not)'
    if re.search(window_visible_pattern, updated_code, re.DOTALL):
        updated_code = re.sub(window_visible_pattern, r'\1True\3', updated_code, flags=re.DOTALL)
        logging.info("修改了窗口可见性检查")
        
    # 修改渲染函数以显示调试信息
    render_pattern = r'def render\(self\):(.*?)# 清除缓冲区'
    render_debug = '''def render(self):
        """渲染当前模型"""
        if not self.initialized:
            logging.warning("渲染器未初始化")
            return
            
        if not self.parts:
            logging.warning("没有模型部件可渲染")
            return
            
        # 清除缓冲区'''
        
    updated_code = re.sub(render_pattern, render_debug, updated_code, flags=re.DOTALL)
    
    # 保存修改后的代码
    with open(renderer_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)
        
    logging.info(f"已更新渲染器文件: {renderer_path}")
    return True

def add_logging_to_window():
    """为窗口类添加更多日志输出"""
    window_path = "./desktop_pet/core/window.py"
    
    if not os.path.exists(window_path):
        logging.error(f"找不到窗口文件: {window_path}")
        return False
        
    # 读取原始文件
    with open(window_path, 'r', encoding='utf-8') as f:
        window_code = f.read()
        
    # 创建备份
    backup_path = window_path + ".backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(window_code)
    logging.info(f"创建了窗口类备份: {backup_path}")
    
    # 修改窗口初始化方法
    init_pattern = r'def __init__\(self, width: int = 300, height: int = 400\):(.*?)# 确保窗口可见性'
    init_with_logging = '''def __init__(self, width: int = 300, height: int = 400):
        super().__init__()
        
        logger.info(f"创建窗口，大小: {width}x{height}")
        
        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 始终置顶
            Qt.Tool  # 工具窗口，不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.setMouseTracking(True)  # 跟踪鼠标移动
        
        # 基本属性
        self.resize(width, height)
        self.dragging = False
        self.drag_position = None
        self.opacity = 1.0
        
        logger.info("窗口属性已设置")
        
        # 创建OpenGL窗口
        self.init_gl_widget()
        
        # 确保窗口可见性'''
    
    updated_code = re.sub(init_pattern, init_with_logging, window_code, flags=re.DOTALL)
    
    # 修改GL初始化方法
    gl_init_pattern = r'def init_gl_widget\(self\):(.*?)# 创建OpenGL小部件'
    gl_init_with_logging = '''def init_gl_widget(self):
        """初始化OpenGL窗口"""
        logger.info("初始化OpenGL窗口")
        # 创建OpenGL格式
        fmt = QGLFormat()
        fmt.setAlpha(True)
        fmt.setSampleBuffers(True)
        logger.info("已设置OpenGL格式")
        
        # 创建OpenGL小部件'''
    
    updated_code = re.sub(gl_init_pattern, gl_init_with_logging, updated_code, flags=re.DOTALL)
    
    # 修改渲染器设置方法
    setup_pattern = r'def setup_renderer\(self, renderer\):(.*?)self\.renderer\.initialize\(\)'
    setup_with_logging = '''def setup_renderer(self, renderer):
        """设置渲染器
        
        Args:
            renderer: 用于渲染模型的渲染器实例
        """
        logger.info("设置渲染器")
        self.renderer = renderer
        logger.info("正在初始化OpenGL上下文")
        self.gl_widget.makeCurrent()
        logger.info("正在初始化渲染器")
        self.renderer.initialize()'''
    
    updated_code = re.sub(setup_pattern, setup_with_logging, updated_code, flags=re.DOTALL)
    
    # 保存修改后的代码
    with open(window_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)
        
    logging.info(f"已更新窗口文件: {window_path}")
    return True

if __name__ == "__main__":
    logging.info("开始修补渲染器和窗口类...")
    
    if patch_renderer_shaders():
        logging.info("渲染器修补完成")
    else:
        logging.error("渲染器修补失败")
        
    if add_logging_to_window():
        logging.info("窗口类修补完成")
    else:
        logging.error("窗口类修补失败")
        
    logging.info("修补完成，请重新运行桌面宠物") 