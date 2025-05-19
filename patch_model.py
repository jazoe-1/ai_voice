import os
import json
import shutil
import logging
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_model_texture_paths():
    """修复模型文件中的纹理路径"""
    try:
        model_path = "./Unitychan/runtime/unitychan.model3.json"
        logging.info(f"正在处理模型文件: {model_path}")
        
        if not os.path.exists(model_path):
            logging.error(f"模型文件不存在: {model_path}")
            return False
        else:
            logging.info(f"模型文件存在: {model_path}")
            
        # 读取模型文件
        with open(model_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
            logging.info(f"成功读取模型文件")
            
        # 备份原始文件
        backup_path = model_path + ".backup"
        shutil.copy2(model_path, backup_path)
        logging.info(f"已创建备份: {backup_path}")
            
        # 检查和修复纹理路径
        textures = model_data.get("FileReferences", {}).get("Textures", [])
        logging.info(f"模型中定义的纹理: {textures}")
        
        if not textures:
            logging.error("未找到纹理路径数据")
            return False
            
        # 检查unitychan.2048目录是否存在
        texture_dir = os.path.join(os.path.dirname(model_path), "unitychan.2048")
        if os.path.exists(texture_dir):
            logging.info(f"目录已存在: {texture_dir}")
            texture_files = os.listdir(texture_dir)
            logging.info(f"{texture_dir}中的文件: {texture_files}")
        else:
            logging.info(f"创建目录: {texture_dir}")
            os.makedirs(texture_dir, exist_ok=True)
            
        # 检查现有纹理文件
        textures_dir = os.path.join(os.path.dirname(model_path), "textures")
        if os.path.exists(textures_dir):
            logging.info(f"找到纹理目录: {textures_dir}")
            texture_files = os.listdir(textures_dir)
            logging.info(f"{textures_dir}中的文件: {texture_files}")
            
            copied_files = 0
            for file in texture_files:
                if file.endswith(".png"):
                    # 复制纹理文件到unitychan.2048目录
                    src_path = os.path.join(textures_dir, file)
                    dst_path = os.path.join(texture_dir, file)
                    if not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
                        logging.info(f"复制纹理: {src_path} -> {dst_path}")
                        copied_files += 1
            
            logging.info(f"复制了{copied_files}个纹理文件")
            return True
        else:
            logging.warning(f"纹理目录不存在: {textures_dir}")
            
            # 如果textures目录不存在，修改模型文件以使用正确路径
            logging.info("准备修改模型文件中的纹理路径")
            old_textures = model_data["FileReferences"]["Textures"]
            new_textures = []
            
            for texture in old_textures:
                # 替换unitychan.2048为textures
                if "unitychan.2048" in texture:
                    new_texture = texture.replace("unitychan.2048", "textures")
                    new_textures.append(new_texture)
                    logging.info(f"修改纹理路径: {texture} -> {new_texture}")
                else:
                    new_textures.append(texture)
                    
            model_data["FileReferences"]["Textures"] = new_textures
            
            # 保存修改后的模型文件
            with open(model_path, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, indent=4)
                
            logging.info(f"已更新模型文件: {model_path}")
            
        return True
    except Exception as e:
        logging.error(f"修复纹理路径失败: {e}")
        logging.error(traceback.format_exc())
        return False
        
def check_and_fix_model():
    """检查并修复模型文件和目录结构"""
    logging.info("开始检查模型文件...")
    
    # 修复纹理路径
    if fix_model_texture_paths():
        logging.info("模型纹理路径修复完成")
    else:
        logging.warning("模型纹理路径修复失败")
        
    # 检查model3.json是否存在，如果不存在则创建一个复制
    model_dir = "./Unitychan/runtime"
    if os.path.exists(os.path.join(model_dir, "unitychan.model3.json")) and not os.path.exists(os.path.join(model_dir, "model3.json")):
        try:
            # 对于Windows，创建一个复制
            shutil.copy2(
                os.path.join(model_dir, "unitychan.model3.json"),
                os.path.join(model_dir, "model3.json")
            )
            logging.info("创建了model3.json的复制")
        except Exception as e:
            logging.error(f"创建model3.json失败: {e}")
            logging.error(traceback.format_exc())
    else:
        if os.path.exists(os.path.join(model_dir, "model3.json")):
            logging.info("model3.json已存在")
        else:
            logging.warning(f"无法创建model3.json，unitychan.model3.json不存在")
            
    logging.info("模型检查和修复完成")
    
if __name__ == "__main__":
    check_and_fix_model() 