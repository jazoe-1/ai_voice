import os
import sys
import importlib.util
import subprocess

def check_package(package_name):
    """检查包是否已安装"""
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        print(f"未安装: {package_name}")
        return False
    print(f"已安装: {package_name}")
    return True

# 检查必要的包
requirements = [
    "PyQt5", "numpy", "Pillow", "PyOpenGL", "PyOpenGL_accelerate"
]

missing = []
for package in requirements:
    if not check_package(package):
        missing.append(package)

# 安装缺失的包
if missing:
    print("\n需要安装以下包:")
    for package in missing:
        print(f" - {package}")
    
    # 询问是否自动安装
    answer = input("\n是否自动安装这些包? (y/n): ")
    if answer.lower() == 'y':
        for package in missing:
            print(f"正在安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("所有包已安装完成!")
else:
    print("\n所有必要的包都已安装!")

# 检查资源文件
print("\n检查资源文件...")
if os.path.exists("setup.py"):
    print("运行资源检查...")
    subprocess.call([sys.executable, "setup.py"])
else:
    print("找不到setup.py，跳过资源检查")

print("\n依赖检查完成，您现在可以运行主程序了!") 