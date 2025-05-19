import os
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_texture_class():
    """查找Texture类的定义"""
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
    
    with open(renderer_path, 'r', encoding='utf-8') as f:
        renderer_code = f.read()
    
    # 找到Texture类定义
    texture_class_match = re.search(r'class Texture\(.*?\):(.*?)class', renderer_code, re.DOTALL)
    if texture_class_match:
        texture_class = texture_class_match.group(0)
        texture_class = texture_class[:-5]  # 移除末尾"class"
        logging.info(f"找到Texture类定义:\n{texture_class}")
        return texture_class
    else:
        logging.error("找不到Texture类定义")
        return None

def find_from_texture_import():
    """查找'from .texture import Texture'语句"""
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return None
    
    with open(renderer_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if "from .texture import Texture" in line:
            logging.info(f"找到引用行: 第{i+1}行 '{line.strip()}'")
            return i, line
    
    logging.info("没有找到'from .texture import Texture'语句")
    return None

def create_texture_module():
    """创建texture.py模块文件"""
    texture_dir = "./desktop_pet/core"
    texture_path = os.path.join(texture_dir, "texture.py")
    
    # 获取Texture类定义
    texture_class = find_texture_class()
    if not texture_class:
        return False
    
    # 创建新的texture.py文件
    texture_module_content = f"""# texture.py
# 从renderer.py中提取的Texture类
import logging
from OpenGL.GL import *

logger = logging.getLogger(__name__)

{texture_class}
"""
    
    # 写入文件
    with open(texture_path, 'w', encoding='utf-8') as f:
        f.write(texture_module_content)
    
    logging.info(f"创建了texture.py模块: {texture_path}")
    return True

def patch_simple_debug_mesh():
    """修复create_simple_debug_mesh方法中的Texture导入"""
    renderer_path = "./desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
    
    with open(renderer_path, 'r', encoding='utf-8') as f:
        renderer_code = f.read()
    
    # 查找简单网格方法中的错误导入并替换
    if "from .texture import Texture" in renderer_code:
        # 检查创建简单网格方法
        debug_mesh_method = re.search(r'def create_simple_debug_mesh\(self\):(.*?)return True', renderer_code, re.DOTALL)
        if debug_mesh_method:
            # 替换方法定义末尾的部分
            old_code = debug_mesh_method.group(1)
            new_code = old_code.replace("from .texture import Texture", "# 直接使用内部定义的Texture类")
            
            # 替换self.parts中的赋值代码
            new_code = new_code.replace(
                "self.parts['debug_quad']['texture'] = Texture(texture_id, texture_size, texture_size)",
                "# 创建纹理对象\n        self.parts['debug_quad']['texture'] = self.texture_manager.textures.get('debug') or Texture(texture_id, texture_size, texture_size)\n        # 存入纹理管理器\n        self.texture_manager.textures['debug'] = self.parts['debug_quad']['texture']"
            )
            
            # 替换整个方法
            updated_code = renderer_code.replace(old_code, new_code)
            
            with open(renderer_path, 'w', encoding='utf-8') as f:
                f.write(updated_code)
                
            logging.info("已修复create_simple_debug_mesh方法中的纹理导入")
            return True
    
    logging.info("未找到需要修复的纹理导入语句")
    return False

if __name__ == "__main__":
    logging.info("开始修复纹理类导入问题...")
    
    # 先查找是否存在从外部导入Texture的代码
    import_info = find_from_texture_import()
    
    if import_info:
        # 创建texture.py模块
        if create_texture_module():
            logging.info("成功创建texture.py模块")
        else:
            logging.error("创建texture.py模块失败")
    else:
        # 修复simple_debug_mesh中的纹理导入
        if patch_simple_debug_mesh():
            logging.info("已修复纹理导入问题")
        else:
            logging.warning("纹理导入问题修复失败或不需要修复")
    
    logging.info("修复完成") 