import numpy as np
from typing import List, Tuple, Dict, Optional


class BezierCalculator:
    """计算和缓存贝塞尔曲线"""
    
    def __init__(self):
        self.curve_cache = {}
        self.precision = 200  # 预计算采样点数量
        
    def calculate_point(self, p0: float, p1: float, p2: float, p3: float, t: float) -> float:
        """计算三次贝塞尔曲线上某一点的值
        
        Args:
            p0, p1, p2, p3: 控制点值
            t: 参数值 (0.0 ~ 1.0)
            
        Returns:
            该点的值
        """
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        t2 = t * t
        t3 = t2 * t
        
        return mt3 * p0 + 3 * mt2 * t * p1 + 3 * mt * t2 * p2 + t3 * p3
    
    def create_curve_cache(self, curve_id: str, p0: float, p1: float, p2: float, p3: float) -> None:
        """创建并缓存贝塞尔曲线的采样点
        
        Args:
            curve_id: 曲线唯一标识
            p0, p1, p2, p3: 控制点值
        """
        cache_data = []
        for i in range(self.precision + 1):
            t = i / self.precision
            value = self.calculate_point(p0, p1, p2, p3, t)
            cache_data.append((t, value))
        
        self.curve_cache[curve_id] = cache_data
    
    def evaluate_cached(self, curve_id: str, t: float) -> float:
        """从缓存中快速查找曲线值
        
        Args:
            curve_id: 曲线唯一标识
            t: 参数值 (0.0 ~ 1.0)
            
        Returns:
            该点的值，如果曲线不存在则返回0
        """
        if curve_id not in self.curve_cache:
            return 0.0
            
        cached_curve = self.curve_cache[curve_id]
        
        # 边界情况
        if t <= cached_curve[0][0]:
            return cached_curve[0][1]
        if t >= cached_curve[-1][0]:
            return cached_curve[-1][1]
        
        # 二分查找
        left = 0
        right = len(cached_curve) - 1
        
        while left <= right:
            mid = (left + right) // 2
            if cached_curve[mid][0] < t:
                left = mid + 1
            elif cached_curve[mid][0] > t:
                right = mid - 1
            else:
                return cached_curve[mid][1]  # 精确匹配
        
        # 线性插值
        low_index = right
        high_index = left
        
        t1 = cached_curve[low_index][0]
        v1 = cached_curve[low_index][1]
        t2 = cached_curve[high_index][0]
        v2 = cached_curve[high_index][1]
        
        # 计算插值
        fraction = (t - t1) / (t2 - t1) if t2 != t1 else 0
        return v1 + fraction * (v2 - v1)


class SegmentEvaluator:
    """评估 Live2D 动作中的曲线段"""
    
    def __init__(self):
        self.bezier_calculator = BezierCalculator()
        
    def evaluate_segment(self, 
                         segment_type: int, 
                         time: float, 
                         segment_data: List[float], 
                         segment_id: str = None) -> Optional[float]:
        """评估不同类型的段
        
        Args:
            segment_type: 段类型 (0=线性, 1=贝塞尔)
            time: 当前时间
            segment_data: 段数据
            segment_id: 可选的段ID用于缓存
            
        Returns:
            计算的值，如果时间超出段范围则返回None
        """
        if segment_type == 0:  # 线性段
            # 检查时间是否在段内
            if len(segment_data) >= 2 and time <= segment_data[0]:
                return segment_data[1]
                
        elif segment_type == 1:  # 贝塞尔段
            # 贝塞尔段有6个值: [t1, v1, t2, v2, t3, v3]
            if len(segment_data) >= 6:
                start_time = segment_data[0]
                end_time = segment_data[4]
                
                # 检查时间是否在段范围内
                if time >= start_time and time <= end_time:
                    # 标准化时间参数
                    t = (time - start_time) / (end_time - start_time) if end_time > start_time else 0.0
                    
                    # 使用缓存或直接计算
                    if segment_id:
                        # 如果该段没有缓存，创建缓存
                        if segment_id not in self.bezier_calculator.curve_cache:
                            p0 = segment_data[1]  # 起始值
                            p1 = segment_data[3]  # 第一控制点值
                            p2 = segment_data[5]  # 第二控制点值
                            p3 = segment_data[1]  # 结束值 (通常会在下一段的开始提供)
                            
                            # 创建缓存
                            self.bezier_calculator.create_curve_cache(segment_id, p0, p1, p2, p3)
                        
                        # 从缓存获取值
                        return self.bezier_calculator.evaluate_cached(segment_id, t)
                    else:
                        # 直接计算贝塞尔值
                        p0 = segment_data[1]
                        p1 = segment_data[3]
                        p2 = segment_data[5]
                        p3 = segment_data[1]  # 假设结束值等于起始值，实际应从下一段获取
                        
                        return self.bezier_calculator.calculate_point(p0, p1, p2, p3, t)
        
        # 时间不在段范围内或段类型不支持
        return None 