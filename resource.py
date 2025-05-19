import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理器，负责加载和管理模型和动作资源"""
    
    def __init__(self, base_path: str = "./"):
        self.base_path = base_path
        
    def scan_models(self, models_dir: Optional[str] = None) -> List[str]:
        """扫描可用的Live2D模型
        
        Args:
            models_dir: 模型目录，如果为None则使用base_path
            
        Returns:
            模型名称列表
        """
        models = []
        search_dir = models_dir or self.base_path
        
        try:
            # 查找包含model3.json的目录
            for root, dirs, files in os.walk(search_dir):
                if "model3.json" in files:
                    # 提取相对路径作为模型名
                    rel_path = os.path.relpath(root, search_dir)
                    if rel_path == ".":
                        # 如果model3.json直接在搜索目录下
                        models.append(os.path.basename(search_dir))
                    else:
                        models.append(rel_path)
                        
            return models
            
        except Exception as e:
            logger.error(f"Error scanning models: {e}")
            return []
            
    def scan_motions(self, motion_dir: str) -> Dict[str, List[str]]:
        """扫描可用的动作文件
        
        Args:
            motion_dir: 动作文件目录
            
        Returns:
            分组动作文件字典，键为组名，值为动作文件列表
        """
        motions = {}
        
        try:
            if not os.path.exists(motion_dir):
                logger.warning(f"Motion directory not found: {motion_dir}")
                return motions
                
            # 扫描所有.motion3.json文件
            for file in os.listdir(motion_dir):
                if file.endswith(".motion3.json"):
                    # 尝试提取组名
                    parts = file.split("_")
                    if len(parts) > 1:
                        group = parts[0]
                    else:
                        group = "default"
                        
                    if group not in motions:
                        motions[group] = []
                        
                    motions[group].append(file)
                    
            return motions
            
        except Exception as e:
            logger.error(f"Error scanning motions: {e}")
            return {}
            
    def get_model_path(self, model_name: str) -> str:
        """获取模型路径
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型路径
        """
        return os.path.join(self.base_path, model_name)
        
    def get_motion_path(self, model_name: str, motion_file: str) -> str:
        """获取动作文件路径
        
        Args:
            model_name: 模型名称
            motion_file: 动作文件名
            
        Returns:
            动作文件路径
        """
        model_path = self.get_model_path(model_name)
        return os.path.join(model_path, "motion", motion_file) 