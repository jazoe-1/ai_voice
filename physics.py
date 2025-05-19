import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from .parameter import ParameterManager

logger = logging.getLogger(__name__)


class PhysicsPoint:
    """物理系统中的质点"""
    
    def __init__(self, x: float, y: float, mass: float = 1.0, fixed: bool = False):
        self.position = np.array([x, y], dtype=np.float32)
        self.prev_position = np.array([x, y], dtype=np.float32)
        self.velocity = np.array([0.0, 0.0], dtype=np.float32)
        self.mass = mass
        self.fixed = fixed


class PhysicsSpring:
    """连接两个质点的弹簧"""
    
    def __init__(self, point1_idx: int, point2_idx: int, 
                length: Optional[float] = None, stiffness: float = 1.0):
        self.point1_idx = point1_idx
        self.point2_idx = point2_idx
        self.rest_length = length  # 如果为None，将在初始化时基于点的距离设置
        self.stiffness = stiffness
        

class PhysicsGroup:
    """物理效果组，包含一组相关的质点和弹簧"""
    
    def __init__(self, group_id: str, influence_parameter: str, input_parameter: str = "PARAM_ANGLE_X"):
        self.id = group_id
        self.influence_parameter = influence_parameter
        self.input_parameter = input_parameter
        self.points: List[PhysicsPoint] = []
        self.springs: List[PhysicsSpring] = []
        
    def add_point(self, x: float, y: float, mass: float = 1.0, fixed: bool = False) -> int:
        """添加质点
        
        Args:
            x, y: 质点位置
            mass: 质量
            fixed: 是否固定
            
        Returns:
            质点索引
        """
        point = PhysicsPoint(x, y, mass, fixed)
        self.points.append(point)
        return len(self.points) - 1
        
    def add_spring(self, point1_idx: int, point2_idx: int, 
                  length: Optional[float] = None, stiffness: float = 1.0) -> None:
        """添加弹簧
        
        Args:
            point1_idx, point2_idx: 连接的两个质点索引
            length: 弹簧静止长度
            stiffness: 弹簧刚度
        """
        # 如果未指定长度，计算两点之间的距离
        if length is None and point1_idx < len(self.points) and point2_idx < len(self.points):
            p1 = self.points[point1_idx].position
            p2 = self.points[point2_idx].position
            length = np.linalg.norm(p2 - p1)
            
        spring = PhysicsSpring(point1_idx, point2_idx, length, stiffness)
        self.springs.append(spring)


class PhysicsSystem:
    """Live2D模型的物理系统，处理头发、衣服等物理效果"""
    
    def __init__(self, parameter_manager: ParameterManager):
        self.parameter_manager = parameter_manager
        self.groups: List[PhysicsGroup] = []
        self.gravity = np.array([0.0, -9.8], dtype=np.float32)
        self.air_resistance = 0.01
        self.last_update_time = 0.0
        
    def create_group(self, group_id: str, influence_parameter: str, 
                    input_parameter: str = "PARAM_ANGLE_X") -> PhysicsGroup:
        """创建物理组
        
        Args:
            group_id: 组ID
            influence_parameter: 影响的参数
            input_parameter: 输入参数
            
        Returns:
            创建的物理组
        """
        group = PhysicsGroup(group_id, influence_parameter, input_parameter)
        self.groups.append(group)
        return group
        
    def update(self, delta_time: float) -> None:
        """更新物理系统
        
        Args:
            delta_time: 时间增量(秒)
        """
        # 限制时间步长，保证稳定性
        delta_time = min(delta_time, 0.033)  # 最大30FPS的物理更新
        
        # 更新每个物理组
        for group in self.groups:
            # 获取输入参数的值
            input_value = self.parameter_manager.get_parameter(group.input_parameter, 0.0)
            
            # 施加外力
            self.apply_external_forces(group, input_value, delta_time)
            
            # 更新质点位置
            self.update_points(group, delta_time)
            
            # 解算约束
            self.solve_constraints(group)
            
            # 计算结果并更新参数
            result_value = self.calculate_result(group)
            self.parameter_manager.set_parameter(group.influence_parameter, result_value)
            
    def apply_external_forces(self, group: PhysicsGroup, input_value: float, delta_time: float) -> None:
        """施加外力到物理组
        
        Args:
            group: 物理组
            input_value: 输入参数值
            delta_time: 时间增量
        """
        for point in group.points:
            if point.fixed:
                continue
                
            # 应用重力
            gravity_force = self.gravity * point.mass * delta_time
            
            # 应用基于输入参数的力
            input_force = np.array([input_value * 0.1, 0.0], dtype=np.float32) * delta_time
            
            # 应用力
            point.velocity += gravity_force + input_force
            
            # 应用空气阻力
            point.velocity *= (1.0 - self.air_resistance)
            
    def update_points(self, group: PhysicsGroup, delta_time: float) -> None:
        """更新质点位置
        
        Args:
            group: 物理组
            delta_time: 时间增量
        """
        for point in group.points:
            if point.fixed:
                continue
                
            # 保存当前位置
            current_pos = point.position.copy()
            
            # 使用Verlet积分更新位置
            new_pos = 2 * point.position - point.prev_position + point.velocity * delta_time
            
            # 更新位置
            point.prev_position = current_pos
            point.position = new_pos
            
            # 更新速度
            point.velocity = (new_pos - current_pos) / delta_time
            
    def solve_constraints(self, group: PhysicsGroup) -> None:
        """解算约束
        
        Args:
            group: 物理组
        """
        # 多次迭代提高稳定性
        for _ in range(3):
            # 处理弹簧约束
            for spring in group.springs:
                if spring.point1_idx >= len(group.points) or spring.point2_idx >= len(group.points):
                    continue
                    
                point1 = group.points[spring.point1_idx]
                point2 = group.points[spring.point2_idx]
                
                # 计算当前长度
                delta = point2.position - point1.position
                current_length = np.linalg.norm(delta)
                
                if current_length < 0.0001:
                    continue  # 避免除以零
                    
                # 计算需要调整的长度
                diff_ratio = (spring.rest_length - current_length) / current_length
                correction = delta * diff_ratio * 0.5 * spring.stiffness
                
                # 调整两端质点位置
                if not point1.fixed:
                    point1.position -= correction
                    
                if not point2.fixed:
                    point2.position += correction
                    
    def calculate_result(self, group: PhysicsGroup) -> float:
        """计算物理组的结果值
        
        Args:
            group: 物理组
            
        Returns:
            参数值
        """
        # 如果没有质点，返回0
        if not group.points:
            return 0.0
            
        # 简单实现：使用末端质点的水平位置变化作为结果
        # 在实际应用中，应该根据物理组的具体目的来计算结果
        end_point = group.points[-1]
        start_point = group.points[0]
        
        # 计算水平偏移
        horizontal_offset = end_point.position[0] - start_point.position[0]
        
        # 映射到适当的范围
        return horizontal_offset * 5.0  # 简单的映射系数 