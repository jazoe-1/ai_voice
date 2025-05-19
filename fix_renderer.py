import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_renderer_initialization():
    """修复渲染器初始化问题"""
    # 渲染器文件路径
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
        
    # 读取原始文件
    with open(renderer_path, 'r', encoding='utf-8') as f:
        renderer_code = f.read()
        
    # 创建备份
    backup_path = renderer_path + ".backup2"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(renderer_code)
    logging.info(f"创建了渲染器备份: {backup_path}")
    
    # 检查initialize方法
    initialize_pattern = r'def initialize\(self\):(.*?)(# 初始化标志)'
    initialize_match = re.search(initialize_pattern, renderer_code, re.DOTALL)
    
    if not initialize_match:
        logging.error("找不到initialize方法")
        return False
    
    # 获取initialize方法内容
    initialize_content = initialize_match.group(1)
    
    # 检查是否有create_shader_program调用
    if 'create_shader_program' in initialize_content:
        # 替换为compile_shaders
        fixed_initialize = initialize_content.replace('create_shader_program', 'compile_shaders')
        fixed_initialize = initialize_content.replace('self.create_shader_program()', 'self.compile_shaders()')
        
        # 更新整个初始化方法
        fixed_initialize_method = f"def initialize(self):{fixed_initialize}    # 初始化标志"
        updated_code = re.sub(initialize_pattern, fixed_initialize_method, renderer_code, flags=re.DOTALL)
        
        logging.info("已修复initialize方法中的函数调用")
    else:
        # 如果没有找到create_shader_program调用，则添加一个简化的initialize方法
        simple_initialize = """def initialize(self):
        \"\"\"初始化OpenGL渲染器\"\"\"
        try:
            # 设置OpenGL版本和配置
            glClearColor(0.0, 0.0, 0.0, 0.0)  # 透明背景
            
            # 启用混合
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 创建着色器程序
            self.compile_shaders()
            
            # 创建顶点缓冲区
            self.create_buffers()
            
            # 初始化标志"""
        
        updated_code = re.sub(initialize_pattern, simple_initialize, renderer_code, flags=re.DOTALL)
        logging.info("已添加简化的initialize方法")
    
    # 检查是否需要添加create_buffers方法
    if 'def create_buffers' not in renderer_code:
        # 添加简化的create_buffers方法
        create_buffers_method = """
    def create_buffers(self):
        \"\"\"创建顶点缓冲对象\"\"\"
        try:
            self.vao = glGenVertexArrays(1)
            self.vbo = glGenBuffers(1)
            self.ebo = glGenBuffers(1)
            
            # 绑定VAO
            glBindVertexArray(self.vao)
            
            # 创建并绑定VBO
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            
            # 创建并绑定EBO
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            
            # 设置顶点属性指针
            # 位置属性
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)
            
            # 纹理坐标属性
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
            glEnableVertexAttribArray(1)
            
            # 解绑VAO
            glBindVertexArray(0)
            logging.info("顶点缓冲区创建成功")
        except Exception as e:
            logging.error(f"创建顶点缓冲区失败: {e}")
"""
        # 在cleanup方法前插入create_buffers方法
        cleanup_pattern = r'def cleanup\(self\):'
        updated_code = re.sub(cleanup_pattern, create_buffers_method + "\n    def cleanup(self):", updated_code)
        logging.info("已添加create_buffers方法")
    
    # 修复render方法中的日志导入
    if 'logging.warning' in updated_code and 'import logging' not in updated_code.split('\n')[:10]:
        # 在文件开头添加logging导入
        updated_code = "import logging\n" + updated_code
        logging.info("已添加logging导入")
    
    # 保存修改后的代码
    with open(renderer_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)
    
    logging.info(f"已修复渲染器文件: {renderer_path}")
    return True

def fix_texture_path_in_config():
    """修复配置文件中的模型路径"""
    config_path = os.path.expanduser("~/.desktop_pet_config.json")
    
    if not os.path.exists(config_path):
        logging.warning(f"找不到配置文件: {config_path}")
        return False
    
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查当前模型路径
        current_path = config.get("model_path", "")
        logging.info(f"当前配置中的模型路径: {current_path}")
        
        # 如果路径不是完整的路径，修复它
        if current_path == "runtime":
            # 修改为全路径
            config["model_path"] = "./Unitychan/runtime/unitychan.model3.json"
            
            # 保存更新后的配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
                
            logging.info(f"已更新配置文件中的模型路径: {config['model_path']}")
            return True
    except Exception as e:
        logging.error(f"修复配置文件失败: {e}")
    
    return False

if __name__ == "__main__":
    logging.info("开始修复渲染器初始化问题...")
    
    if fix_renderer_initialization():
        logging.info("渲染器初始化问题修复完成")
    else:
        logging.error("渲染器初始化问题修复失败")
    
    if fix_texture_path_in_config():
        logging.info("配置文件中的路径已修复")
    
    logging.info("修复完成，请重新运行测试") 