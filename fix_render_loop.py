import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_pet_manager_render_loop():
    """修复PetManager中的渲染循环问题"""
    # PetManager文件路径
    pet_manager_path = "./desktop_pet/pet_manager.py"
    
    if not os.path.exists(pet_manager_path):
        logging.error(f"找不到PetManager文件: {pet_manager_path}")
        return False
        
    # 读取原始文件
    with open(pet_manager_path, 'r', encoding='utf-8') as f:
        pet_manager_code = f.read()
        
    # 创建备份
    backup_path = pet_manager_path + ".backup"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(pet_manager_code)
    logging.info(f"创建了PetManager备份: {backup_path}")
    
    # 修复渲染帧方法
    render_frame_pattern = r'def render_frame\(self\):(.*?)def update_frame'
    render_frame_match = re.search(render_frame_pattern, pet_manager_code, re.DOTALL)
    
    if not render_frame_match:
        logging.error("找不到render_frame方法")
        return False
    
    # 替换为更健壮的渲染帧方法
    safe_render_frame = """def render_frame(self):
        \"\"\"渲染单帧\"\"\"
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
        
    def update_frame"""
    
    # 替换渲染帧方法
    updated_code = re.sub(render_frame_pattern, safe_render_frame, pet_manager_code, flags=re.DOTALL)
    
    # 修复_start_rendering方法以使用更长的延迟
    start_rendering_pattern = r'def _start_rendering\(self\):(.*?)def stop'
    start_rendering_match = re.search(start_rendering_pattern, updated_code, re.DOTALL)
    
    if start_rendering_match:
        start_rendering_content = start_rendering_match.group(1)
        
        # 增加延迟时间并降低刷新率
        fixed_start_rendering = start_rendering_content.replace('self.render_timer.start(16)', 'self.render_timer.start(33)')
        fixed_start_rendering = fixed_start_rendering.replace('self.update_timer.start(33)', 'self.update_timer.start(50)')
        fixed_start_rendering = fixed_start_rendering.replace('QTimer.singleShot(300', 'QTimer.singleShot(1000')
        
        fixed_start_rendering_method = f"def _start_rendering(self):{fixed_start_rendering}def stop"
        updated_code = re.sub(start_rendering_pattern, fixed_start_rendering_method, updated_code, flags=re.DOTALL)
        
        logging.info("已修改渲染循环的定时器设置")
    
    # 修复load_model方法以在失败时提供更好的错误处理
    load_model_pattern = r'def load_model\(self\):(.*?)return True'
    load_model_match = re.search(load_model_pattern, updated_code, re.DOTALL)
    
    if load_model_match:
        load_model_content = load_model_match.group(1)
        
        # 检查是否已有错误检查
        if "Failed to parse model" in load_model_content:
            # 添加更详细的错误消息
            improved_error_check = load_model_content.replace(
                'logger.error(f"Failed to parse model: {model_path}")',
                'logger.error(f"无法解析模型: {model_path}，请检查模型文件是否正确")\n            import traceback\n            logger.error(traceback.format_exc())'
            )
            
            improved_load_model = f"def load_model(self):{improved_error_check}        return True"
            updated_code = re.sub(load_model_pattern, improved_load_model, updated_code, flags=re.DOTALL)
            
            logging.info("已改进模型加载错误处理")
    
    # 保存修改后的代码
    with open(pet_manager_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)
    
    logging.info(f"已修复PetManager文件: {pet_manager_path}")
    return True

def create_simple_mesh_for_debugging():
    """为调试目的创建一个简单的网格渲染器"""
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
    
    with open(renderer_path, 'r', encoding='utf-8') as f:
        renderer_code = f.read()
    
    # 添加简单网格创建方法
    simple_mesh_method = """
    def create_simple_debug_mesh(self):
        \"\"\"创建简单的调试用网格\"\"\"
        import numpy as np
        import ctypes
        
        # 简单的四边形顶点数据
        vertices = np.array([
            # 位置             # 纹理坐标
            -0.5, -0.5, 0.0,  0.0, 1.0,  # 左下
             0.5, -0.5, 0.0,  1.0, 1.0,  # 右下
             0.5,  0.5, 0.0,  1.0, 0.0,  # 右上
            -0.5,  0.5, 0.0,  0.0, 0.0   # 左上
        ], dtype=np.float32)
        
        # 索引数据
        indices = np.array([
            0, 1, 2,  # 第一个三角形
            2, 3, 0   # 第二个三角形
        ], dtype=np.uint32)
        
        # 创建一个测试部件
        if not hasattr(self, 'parts'):
            self.parts = {}
            
        self.parts['debug_quad'] = {
            'mesh': {
                'vertices': vertices,
                'indices': indices,
                'index_count': len(indices)
            },
            'visible': True,
            'opacity': 1.0,
            'depth': 0,
            'deformers': []
        }
        
        # 尝试加载一个简单的测试纹理
        from PIL import Image
        import numpy as np
        
        # 创建一个简单的测试纹理
        texture_size = 64
        texture_data = np.zeros((texture_size, texture_size, 4), dtype=np.uint8)
        
        # 填充纹理数据 - 创建一个简单的棋盘格
        for y in range(texture_size):
            for x in range(texture_size):
                if (x // 8 + y // 8) % 2 == 0:
                    texture_data[y, x] = [255, 0, 0, 255]  # 红色
                else:
                    texture_data[y, x] = [255, 255, 255, 255]  # 白色
        
        # 创建PIL图像
        image = Image.fromarray(texture_data)
        
        # 使用OpenGL创建纹理
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        
        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # 加载纹理数据
        from OpenGL.GL import GL_RGBA, GL_UNSIGNED_BYTE
        img_data = np.array(image)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA, texture_size, texture_size, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, img_data
        )
        
        # 将纹理存储到部件中
        from .texture import Texture
        self.parts['debug_quad']['texture'] = Texture(texture_id, texture_size, texture_size)
        
        logging.info("已创建调试网格和纹理")
        return True
    """
    
    # 在cleanup方法之前插入
    cleanup_pattern = r'def cleanup\(self\):'
    updated_code = re.sub(cleanup_pattern, simple_mesh_method + "\n    def cleanup(self):", renderer_code, flags=re.DOTALL)
    
    # 修改initialize方法以创建测试网格
    initialize_pattern = r'(# 初始化标志\s+self\.initialized = True)'
    updated_code = re.sub(initialize_pattern, r'\1\n            # 创建测试网格\n            self.create_simple_debug_mesh()', updated_code, flags=re.DOTALL)
    
    # 保存修改后的代码
    with open(renderer_path, 'w', encoding='utf-8') as f:
        f.write(updated_code)
    
    logging.info(f"已添加简单调试网格渲染功能: {renderer_path}")
    return True

def add_debug_flags():
    """添加调试标志到桌面宠物配置"""
    config_path = os.path.expanduser("~/.desktop_pet_config.json")
    
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 添加调试标志
            config["debug_mode"] = True
            config["render_delay"] = 50  # 毫秒
            config["update_delay"] = 100  # 毫秒
            
            # 保存更新后的配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
                
            logging.info(f"已添加调试标志到配置文件")
            return True
        except Exception as e:
            logging.error(f"修改配置文件失败: {e}")
    
    return False

if __name__ == "__main__":
    logging.info("开始修复渲染循环问题...")
    
    if fix_pet_manager_render_loop():
        logging.info("渲染循环问题修复完成")
    else:
        logging.error("渲染循环问题修复失败")
    
    if create_simple_mesh_for_debugging():
        logging.info("已添加调试网格渲染功能")
    
    if add_debug_flags():
        logging.info("已添加调试配置")
    
    logging.info("修复完成，请重新运行测试") 