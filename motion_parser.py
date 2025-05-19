import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from .bezier import SegmentEvaluator
from .parameter import ParameterManager

logger = logging.getLogger(__name__)


class Motion:
    """表示一个Live2D动作"""
    
    def __init__(self, motion_id: str):
        self.id = motion_id
        self.duration = 0.0
        self.fps = 30.0
        self.loop = True
        self.fade_in_time = 1.0
        self.fade_out_time = 1.0
        self.curves = []  # 参数曲线列表
        
    @classmethod
    def from_dict(cls, motion_id: str, data: Dict) -> 'Motion':
        """从字典创建Motion对象
        
        Args:
            motion_id: 动作ID
            data: 动作数据字典
            
        Returns:
            Motion对象
        """
        motion = cls(motion_id)
        
        # 设置基本属性
        meta = data.get("Meta", {})
        motion.duration = meta.get("Duration", 0.0)
        motion.fps = meta.get("Fps", 30.0)
        motion.loop = meta.get("Loop", True)
        motion.fade_in_time = meta.get("FadeInTime", 1.0)
        motion.fade_out_time = meta.get("FadeOutTime", 1.0)
        
        # 复制曲线
        motion.curves = data.get("Curves", [])
        
        return motion


class MotionParser:
    """解析Live2D的motion3.json文件"""
    
    def __init__(self):
        self.motion_cache = {}  # 缓存已解析的动作
        self.segment_evaluator = SegmentEvaluator()
        
    def parse_motion_file(self, motion_path: str) -> Optional[Motion]:
        """解析动作文件
        
        Args:
            motion_path: motion3.json文件的路径
            
        Returns:
            Motion对象，如果解析失败则返回None
        """
        # 检查缓存
        if motion_path in self.motion_cache:
            return self.motion_cache[motion_path]
            
        try:
            with open(motion_path, 'r', encoding='utf-8') as f:
                motion_data = json.load(f)
                
            # 创建Motion对象
            motion_id = os.path.splitext(os.path.basename(motion_path))[0]
            motion = Motion.from_dict(motion_id, motion_data)
            
            # 解析元数据
            meta = motion_data.get("Meta", {})
            motion.duration = meta.get("Duration", 0.0)
            motion.fps = meta.get("Fps", 30.0)
            motion.loop = meta.get("Loop", True)
            motion.fade_in_time = meta.get("FadeInTime", 1.0)
            motion.fade_out_time = meta.get("FadeOutTime", 1.0)
            
            # 解析曲线
            curves = motion_data.get("Curves", [])
            for curve_data in curves:
                # 提取曲线信息
                curve = {
                    "Target": curve_data.get("Target", ""),
                    "Id": curve_data.get("Id", ""),
                    "Segments": curve_data.get("Segments", [])
                }
                motion.curves.append(curve)
                
            # 缓存并返回
            self.motion_cache[motion_path] = motion
            return motion
            
        except Exception as e:
            logger.error(f"Error parsing motion file {motion_path}: {e}")
            return None
            
    def evaluate_curve(self, curve: Dict[str, Any], time: float) -> float:
        """评估给定时间点的曲线值
        
        Args:
            curve: 曲线数据
            time: 时间点
            
        Returns:
            曲线在给定时间点的值
        """
        segments = curve.get("Segments", [])
        if not segments:
            return 0.0
            
        # Live2D的段格式：[类型, 时间, 值, ...]
        i = 0
        value = None
        
        while i < len(segments):
            segment_type = segments[i]
            i += 1
            
            if segment_type == 0:  # 线性段
                if i + 1 < len(segments):
                    segment_data = segments[i:i+2]
                    i += 2
                    
                    # 生成段ID用于缓存
                    segment_id = f"{curve['Id']}_{i-3}"
                    segment_value = self.segment_evaluator.evaluate_segment(
                        segment_type, time, segment_data, segment_id)
                    
                    if segment_value is not None:
                        value = segment_value
                        
            elif segment_type == 1:  # 贝塞尔段
                if i + 5 < len(segments):
                    segment_data = segments[i:i+6]
                    i += 6
                    
                    # 生成段ID用于缓存
                    segment_id = f"{curve['Id']}_{i-7}"
                    segment_value = self.segment_evaluator.evaluate_segment(
                        segment_type, time, segment_data, segment_id)
                    
                    if segment_value is not None:
                        value = segment_value
            else:
                # 跳过未知段类型
                i += 1
                
        return value if value is not None else 0.0
        

class MotionManager:
    """管理动作的播放、混合和过渡"""
    
    def __init__(self, parameter_manager: ParameterManager):
        self.parameter_manager = parameter_manager
        self.motion_parser = MotionParser()
        self.current_motion = None
        self.fade_in_motion = None
        self.fade_out_motion = None
        self.current_time = 0.0
        self.last_update_time = 0.0
        self.motions = {}  # 存储已加载的动作
        
    def load_motion(self, motion_path: str) -> Optional[str]:
        """加载动作文件
        
        Args:
            motion_path: 动作文件路径
            
        Returns:
            加载的动作ID，如果加载失败则返回None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(motion_path):
                logger.error(f"Motion file not found: {motion_path}")
                return None
            
            # 解析文件
            motion = self.motion_parser.parse_motion_file(motion_path)
            if not motion:
                logger.error(f"Failed to parse motion file: {motion_path}")
                return None
            
            # 获取ID并存储动作
            motion_id = os.path.splitext(os.path.basename(motion_path))[0]
            self.motions[motion_id] = motion
            
            logger.debug(f"Motion loaded: {motion_id}, type: {type(motion)}")
            
            return motion_id
            
        except Exception as e:
            logger.error(f"Error loading motion file {motion_path}: {e}")
            return None
        
    def play_motion(self, motion_name: str, loop: Optional[bool] = None, fade_in_time: Optional[float] = None) -> bool:
        """播放指定动作
        
        Args:
            motion_name: 动作名称
            loop: 是否循环播放，如果为None则使用动作定义
            fade_in_time: 淡入时间，如果为None则使用动作定义
            
        Returns:
            是否成功开始播放
        """
        if motion_name not in self.motions:
            logger.warning(f"Motion not found: {motion_name}")
            return False
        
        # 获取动作
        motion = self.motions[motion_name]
        
        # 设置动作参数
        loop = loop if loop is not None else motion.loop
        fade_in_time = fade_in_time if fade_in_time is not None else motion.fade_in_time
        
        logger.debug(f"Playing motion: {motion_name}, loop={loop}, fade_in={fade_in_time}")
        
        # 如果有当前动作，将其设为淡出
        if self.current_motion:
            # 获取当前动作的淡出时间
            current_motion = self.motions[self.current_motion["name"]]
            fade_out_time = current_motion.fade_out_time
            
            # 保存为淡出动作
            self.fade_out_motion = {
                "motion": current_motion,  # ⚠️这里存储的是字典而非Motion对象
                "start_time": self.current_time - self.current_motion["time"],
                "fade_out_time": fade_out_time
            }
        
        # 设置为当前动作
        self.current_motion = {
            "name": motion_name,
            "time": 0.0,
            "loop": loop,
            "fade_in_time": fade_in_time
        }
        
        return True
        
    def update(self, delta_time: float) -> None:
        """更新动作状态
        
        Args:
            delta_time: 时间增量
        """
        if not self.current_motion:
            return
        
        # 更新当前时间
        self.current_time += delta_time
        
        # 更新当前动作时间
        self.current_motion["time"] += delta_time
        
        # 获取当前动作对象
        motion_name = self.current_motion["name"]
        if motion_name not in self.motions:
            # 动作不存在，清空当前动作
            self.current_motion = None
            return
        
        motion_obj = self.motions[motion_name]
        
        # 获取动作持续时间
        duration = motion_obj.get("Meta", {}).get("Duration", 3.0)
        
        # 处理循环
        if self.current_motion["loop"] and self.current_motion["time"] > duration:
            self.current_motion["time"] = self.current_motion["time"] % duration
        
        # 计算淡入权重
        fade_in_weight = 1.0
        if self.current_motion["fade_in_time"] > 0:
            fade_in_progress = min(self.current_motion["time"] / self.current_motion["fade_in_time"], 1.0)
            fade_in_weight = fade_in_progress
        
        # 计算淡出权重
        fade_out_weight = 0.0
        if self.fade_out_motion:
            fade_out_time = self.current_time - self.fade_out_motion["start_time"]
            
            # 处理循环
            fade_out_duration = self.fade_out_motion["motion"].get("Meta", {}).get("Duration", 3.0)
            if fade_out_time > fade_out_duration:
                fade_out_time = fade_out_time % fade_out_duration
            
            # 计算淡出权重
            fade_out_progress = min(fade_out_time / self.fade_out_motion["fade_out_time"], 1.0)
            fade_out_weight = 1.0 - fade_out_progress
            
            # 如果淡出完成，清除淡出动作
            if fade_out_progress >= 1.0:
                self.fade_out_motion = None
        
        # 计算当前动作时间
        motion_time = self.current_motion["time"]
        
        # 暂存所有参数及其权重
        parameters = {}
        
        # 应用当前动作
        if fade_in_weight > 0:
            # 遍历所有参数曲线
            for curve in motion_obj.get("Curves", []):
                if curve["Target"] == "Parameter":
                    param_id = curve["Id"]
                    value = self.motion_parser.evaluate_curve(curve, motion_time)
                    
                    # 应用淡入权重
                    weight = fade_in_weight
                    
                    # 添加到参数字典
                    parameters[param_id] = {"value": value * weight, "weight": weight}
        
        # 计算并应用最终参数值
        final_parameters = {}
        for param_id, data in parameters.items():
            if data["weight"] > 0:
                final_parameters[param_id] = data["value"] / data["weight"]
                
        # 更新参数
        self.parameter_manager.update_parameters(final_parameters)

        # 淡出动作
        if self.fade_out_motion and fade_out_weight > 0:
            fade_out_motion_obj = self.fade_out_motion["motion"]
            fade_out_time = self.current_time - self.fade_out_motion["start_time"]
            
            # 处理循环
            fade_out_duration = fade_out_motion_obj.get("Meta", {}).get("Duration", 3.0)
            if fade_out_time > fade_out_duration:
                fade_out_time = fade_out_time % fade_out_duration
            
            # 计算淡出动作的参数值
            for curve in fade_out_motion_obj.get("Curves", []):
                if curve["Target"] == "Parameter":
                    param_id = curve["Id"]
                    value = self.motion_parser.evaluate_curve(curve, fade_out_time)
                    
                    # 应用淡出权重
                    weight = fade_out_weight
                    
                    # 添加到参数字典
                    if param_id in parameters:
                        parameters[param_id] = {
                            "value": parameters[param_id]["value"] + value * weight,
                            "weight": parameters[param_id]["weight"] + weight
                        }
                    else:
                        parameters[param_id] = {"value": value * weight, "weight": weight}

    def has_motion(self, motion_name: str) -> bool:
        """检查是否有指定的动作
        
        Args:
            motion_name: 动作名称
            
        Returns:
            是否有该动作
        """
        return motion_name in self.motions

    def get_loaded_motions(self) -> List[str]:
        """获取所有已加载的动作名称
        
        Returns:
            动作名称列表
        """
        return list(self.motions.keys()) 