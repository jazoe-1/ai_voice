import os
import sys
import logging
import shutil

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_texture_module():
    """确保texture.py模块存在"""
    texture_path = "desktop_pet/core/texture.py"
    
    # 如果已经存在，备份它
    if os.path.exists(texture_path):
        backup_path = texture_path + ".backup"
        shutil.copy2(texture_path, backup_path)
        logging.info(f"已备份原有texture.py: {backup_path}")
    
    # 创建texture.py
    texture_module_content = """# texture.py
# Texture class extracted from renderer.py
import logging
from OpenGL.GL import *

logger = logging.getLogger(__name__)

class Texture:
    \"\"\"OpenGL纹理\"\"\"

    def __init__(self, texture_id: int, width: int, height: int):
        self.id = texture_id
        self.width = width
        self.height = height
"""
    
    # 写入文件
    with open(texture_path, 'w', encoding='utf-8') as f:
        f.write(texture_module_content)
    
    logging.info(f"创建texture.py模块: {texture_path}")
    return True

def fix_renderer():
    """修复renderer.py文件中的导入错误"""
    renderer_path = "desktop_pet/core/renderer.py"
    
    if not os.path.exists(renderer_path):
        logging.error(f"找不到渲染器文件: {renderer_path}")
        return False
    
    # 备份原始文件
    backup_path = renderer_path + ".backup"
    shutil.copy2(renderer_path, backup_path)
    logging.info(f"已备份原有renderer.py: {backup_path}")
    
    # 读取文件内容
    with open(renderer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换导入语句
    if "from .texture import Texture" in content:
        content = content.replace("from .texture import Texture", "# 使用当前模块中的Texture类")
        
        # 写回文件
        with open(renderer_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info("修复了renderer.py中的导入")
        return True
    else:
        logging.info("renderer.py不需要修复")
        return True

def run_pet_test():
    """运行桌面宠物测试程序"""
    try:
        logging.info("运行test_pet.py...")
        
        # 直接导入并运行test_pet.py
        from test_pet import main as test_pet_main
        test_pet_main()
    except Exception as e:
        logging.error(f"运行test_pet.py失败: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    logging.info("开始修复并运行桌面宠物...")
    
    # 确保texture.py模块存在
    if ensure_texture_module():
        # 修复renderer.py
        if fix_renderer():
            # 运行测试
            run_pet_test()
    
    logging.info("完成") 