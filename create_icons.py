#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PIL import Image, ImageDraw, ImageFont

# 确保图标目录存在
icons_dir = "ui/icons"
os.makedirs(icons_dir, exist_ok=True)

# 定义要创建的图标及其颜色
icons = {
    "mic.png": "#4CAF50",        # 绿色
    "stop.png": "#F44336",       # 红色
    "send.png": "#2196F3",       # 蓝色
    "test.png": "#FFC107",       # 琥珀色
    "cloud.png": "#03A9F4",      # 浅蓝色
    "vosk.png": "#9C27B0",       # 紫色
    "whisper.png": "#673AB7",    # 深紫色
    "apply.png": "#4CAF50",      # 绿色
    "refresh.png": "#00BCD4",    # 青色
    "add.png": "#4CAF50",        # 绿色
    "edit.png": "#FF9800",       # 橙色
    "delete.png": "#F44336",     # 红色
    "clear.png": "#607D8B",      # 蓝灰色
    "settings.png": "#607D8B",   # 蓝灰色
    "start.png": "#4CAF50"       # 绿色
}

def create_basic_icon(filename, color, size=48):
    """创建一个简单的彩色图标"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 画一个圆形图标
    padding = 4
    draw.ellipse([padding, padding, size-padding, size-padding], fill=color)
    
    # 根据文件名添加简单的标识
    if "mic" in filename:
        # 画一个麦克风
        draw.rectangle([size//3, size//3, 2*size//3, 3*size//4], fill="white")
    elif "stop" in filename:
        # 画一个停止图标
        draw.rectangle([size//3, size//3, 2*size//3, 2*size//3], fill="white")
    elif "send" in filename:
        # 画一个箭头
        points = [(size//3, size//3), (2*size//3, size//2), (size//3, 2*size//3)]
        draw.polygon(points, fill="white")
    
    # 保存图标
    path = os.path.join(icons_dir, filename)
    img.save(path)
    print(f"创建图标: {path}")

# 创建所有图标
for icon_name, color in icons.items():
    create_basic_icon(icon_name, color)

print("所有图标已创建完成！") 