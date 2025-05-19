from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ParameterManager:
    """参数管理器 - 管理Live2D模型的所有参数"""
    
    def __init__(self):
        self.parameters = {}  # 存储所有参数值
        self.parameter_definitions = {}  # 存储参数定义（最小值、最大值等）
        
    def register_parameter(self, param_id: str, default_value: float = 0.0, 
                           min_value: float = -100.0, max_value: float = 100.0) -> None:
        """注册新参数
        
        Args:
            param_id: 参数ID
            default_value: 默认值
            min_value: 最小值
            max_value: 最大值
        """
        self.parameter_definitions[param_id] = {
            "default": default_value,
            "min": min_value,
            "max": max_value
        }
        self.parameters[param_id] = default_value
        
    def set_parameter(self, param_id: str, value: float) -> None:
        """设置参数值
        
        Args:
            param_id: 参数ID
            value: 新的参数值
        """
        # 如果参数未注册，自动注册
        if param_id not in self.parameter_definitions:
            logger.debug(f"Auto-registering parameter: {param_id}")
            self.register_parameter(param_id)
            
        # 获取参数限制
        definition = self.parameter_definitions.get(param_id, {"min": -100.0, "max": 100.0})
        
        # 限制值在有效范围内
        clamped_value = max(definition["min"], min(definition["max"], value))
        
        # 设置参数
        self.parameters[param_id] = clamped_value
        
    def get_parameter(self, param_id: str, default: float = 0.0) -> float:
        """获取参数值
        
        Args:
            param_id: 参数ID
            default: 如果参数不存在，使用的默认值
            
        Returns:
            参数的当前值
        """
        return self.parameters.get(param_id, default)
        
    def update_parameters(self, param_dict: Dict[str, float]) -> None:
        """批量更新多个参数
        
        Args:
            param_dict: 键为参数ID，值为参数值的字典
        """
        for param_id, value in param_dict.items():
            self.set_parameter(param_id, value)
            
    def reset_parameters(self) -> None:
        """将所有参数重置为默认值"""
        for param_id, definition in self.parameter_definitions.items():
            self.parameters[param_id] = definition["default"]
            
    def get_all_parameters(self) -> Dict[str, float]:
        """获取所有参数的当前值
        
        Returns:
            包含所有当前参数值的字典
        """
        return self.parameters.copy()
        
    def load_parameter_definitions(self, definitions: List[Dict[str, Any]]) -> None:
        """从模型定义中加载参数定义
        
        Args:
            definitions: 包含参数定义的列表
        """
        for param_def in definitions:
            param_id = param_def.get("Id", "")
            if param_id:
                self.register_parameter(
                    param_id,
                    default_value=param_def.get("Default", 0.0),
                    min_value=param_def.get("Min", -100.0),
                    max_value=param_def.get("Max", 100.0)
                ) 