import numpy as np
from typing import Tuple


def create_transform_matrix(tx: float = 0.0, ty: float = 0.0, 
                           rotation: float = 0.0, 
                           sx: float = 1.0, sy: float = 1.0) -> np.ndarray:
    """创建2D变换矩阵（平移、旋转、缩放）
    
    Args:
        tx, ty: 平移量
        rotation: 旋转角度（弧度）
        sx, sy: 缩放因子
        
    Returns:
        4x4变换矩阵
    """
    # 创建单位矩阵
    matrix = np.identity(4, dtype=np.float32)
    
    # 计算旋转值
    cos_r = np.cos(rotation)
    sin_r = np.sin(rotation)
    
    # 应用缩放
    matrix[0, 0] = sx
    matrix[1, 1] = sy
    
    # 应用旋转
    rot_matrix = np.identity(4, dtype=np.float32)
    rot_matrix[0, 0] = cos_r
    rot_matrix[0, 1] = -sin_r
    rot_matrix[1, 0] = sin_r
    rot_matrix[1, 1] = cos_r
    
    matrix = np.matmul(matrix, rot_matrix)
    
    # 应用平移
    matrix[0, 3] = tx
    matrix[1, 3] = ty
    
    return matrix


def calculate_distance(dx: float, dy: float) -> float:
    """计算两点之间的距离
    
    Args:
        dx, dy: 两点x和y坐标的差值
        
    Returns:
        距离
    """
    return np.sqrt(dx * dx + dy * dy)


def lerp(a: float, b: float, t: float) -> float:
    """线性插值
    
    Args:
        a: 起始值
        b: 结束值
        t: 插值因子 (0.0 ~ 1.0)
        
    Returns:
        插值结果
    """
    return a + t * (b - a)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """限制值在指定范围内
    
    Args:
        value: 要限制的值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        限制后的值
    """
    return max(min_value, min(max_value, value))


def map_range(value: float, 
             source_min: float, source_max: float, 
             target_min: float, target_max: float) -> float:
    """将值从一个范围映射到另一个范围
    
    Args:
        value: 要映射的值
        source_min, source_max: 源范围
        target_min, target_max: 目标范围
        
    Returns:
        映射后的值
    """
    # 防止除以零
    if source_max == source_min:
        return target_min
        
    # 计算映射
    source_range = source_max - source_min
    target_range = target_max - target_min
    normalized = (value - source_min) / source_range
    
    return target_min + normalized * target_range 