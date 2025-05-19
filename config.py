import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        # 默认配置
        self.default_config = {
            "enabled": True,
            "model_path": "./Unitychan/runtime/unitychan.model3.json",  # 指向完整模型文件
            "window_width": 400,
            "window_height": 600,
            "opacity": 0.9,
            "quality": "high",
            "interaction_frequency": 60,  # 单位：秒
            "mouse_follow": True,
            "fixed_position": False,
            "position_x": -1,  # -1表示屏幕右下角
            "position_y": -1,
            "motions": {
                "idle": "idle_01.motion3.json",
                "idle2": "idle_02.motion3.json",
                "talk": "m_01.motion3.json",
                "expression": "m_02.motion3.json"
            }
        }
        
        self.config = self.default_config.copy()
        self.config_path = config_path or os.path.join(
            os.path.expanduser("~"), ".desktop_pet_config.json")
        
        # 加载配置
        self.load_config()
        
    def load_config(self) -> bool:
        """从文件加载配置
        
        Returns:
            是否成功加载
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                # 更新配置，保留默认值
                for key, value in loaded_config.items():
                    if key in self.config:
                        self.config[key] = value
                        
                logger.info(f"Configuration loaded from {self.config_path}")
                return True
            else:
                logger.info("No configuration file found, using defaults")
                return False
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
            
    def save_config(self) -> bool:
        """保存配置到文件
        
        Returns:
            是否成功保存
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
                
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
            
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值（如果配置项不存在）
            
        Returns:
            配置项值
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
        """
        if key in self.config or key in self.default_config:
            self.config[key] = value
        else:
            logger.warning(f"Adding new configuration item: {key}")
            self.config[key] = value
            
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置
        
        Returns:
            所有配置的副本
        """
        return self.config.copy()
        
    def reset(self) -> None:
        """重置为默认配置"""
        self.config = self.default_config.copy()
        
    def get_motion_path(self, motion_type: str) -> Optional[str]:
        """获取动作文件路径
        
        Args:
            motion_type: 动作类型
            
        Returns:
            动作文件路径，如果不存在则返回None
        """
        motions = self.config.get("motions", {})
        motion_file = motions.get(motion_type)
        
        if not motion_file:
            return None
            
        model_path = self.config.get("model_path", "")
        motion_dir = os.path.join(model_path, "motion")
        
        return os.path.join(motion_dir, motion_file) 