import os
import json

def check_model_files():
    """检查Unitychan模型文件是否存在"""
    model_dir = "Unitychan/runtime"
    model_file = os.path.join(model_dir, "unitychan.model3.json")
    
    if not os.path.exists(model_dir):
        print(f"警告: 模型目录不存在: {model_dir}")
        print("将尝试创建目录...")
        os.makedirs(model_dir, exist_ok=True)
        print(f"创建目录: {model_dir}")
        return False
        
    if not os.path.exists(model_file):
        print(f"警告: 模型文件不存在: {model_file}")
        print("您需要提供正确的Unitychan模型文件，或者配置使用其他Live2D模型")
        return False
        
    print(f"模型文件检查通过: {model_file}")
    return True
    
def check_motion_files():
    """检查动作文件是否存在"""
    motion_dir = "Unitychan/runtime/motion"
    
    if not os.path.exists(motion_dir):
        print(f"警告: 动作目录不存在: {motion_dir}")
        print("将尝试创建目录...")
        os.makedirs(motion_dir, exist_ok=True)
        print(f"创建目录: {motion_dir}")
        return False
        
    motion_files = [f for f in os.listdir(motion_dir) if f.endswith(".motion3.json")]
    
    if not motion_files:
        print(f"警告: 动作目录中没有.motion3.json文件: {motion_dir}")
        print("您可能需要添加动作文件以使宠物有动画效果")
        return False
        
    print(f"找到 {len(motion_files)} 个动作文件: {', '.join(motion_files[:5])}...")
    return True
    
def check_texture_files():
    """检查纹理文件是否存在"""
    texture_dir = "Unitychan/runtime/textures"
    
    if not os.path.exists(texture_dir):
        print(f"警告: 纹理目录不存在: {texture_dir}")
        return False
        
    texture_files = [f for f in os.listdir(texture_dir) if f.endswith((".png", ".jpg"))]
    
    if not texture_files:
        print(f"警告: 纹理目录中没有图像文件: {texture_dir}")
        return False
        
    print(f"找到 {len(texture_files)} 个纹理文件: {', '.join(texture_files[:5])}...")
    return True
    
def main():
    print("检查Live2D桌面宠物所需文件...")
    
    model_ok = check_model_files()
    motion_ok = check_motion_files()
    texture_ok = check_texture_files()
    
    if model_ok and motion_ok and texture_ok:
        print("所有必需的文件都已找到，可以运行桌面宠物程序了!")
    else:
        print("\n警告：一些必要的文件似乎缺失。")
        print("如果您已有完整的Unitychan或其他Live2D模型，请将其放置在正确位置。")
        print("或者，您可以修改配置文件指向其他Live2D模型。")

if __name__ == "__main__":
    main() 