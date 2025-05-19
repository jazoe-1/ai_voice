import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ModelParser:
    """解析Live2D模型文件"""
    
    def __init__(self):
        self.model_cache = {}
        
    def parse_model_file(self, model_path: str) -> Optional[Dict]:
        """解析model3.json文件
        
        Args:
            model_path: model3.json文件的路径或其所在目录
            
        Returns:
            解析后的模型数据，如果解析失败则返回None
        """
        # 检查缓存
        if model_path in self.model_cache:
            return self.model_cache[model_path]
            
        try:
            # 确保路径是model3.json文件或其所在目录
            if model_path.endswith('.model3.json'):
                model_file = model_path
                model_dir = os.path.dirname(model_path)
            elif os.path.isdir(model_path):
                model_file = os.path.join(model_path, 'model3.json')
                model_dir = model_path
            else:
                model_dir = os.path.dirname(model_path)
                model_file = os.path.join(model_dir, 'model3.json')
                
            # 如果找不到model3.json，尝试找unitychan.model3.json
            if not os.path.exists(model_file):
                model_file = os.path.join(model_dir, 'unitychan.model3.json')
            
            if not os.path.exists(model_file):
                logger.error(f"Model file not found: {model_file}")
                return None
                
            # 解析JSON
            with open(model_file, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
                
            # 处理模型数据
            processed_model = self.process_model_data(model_data, model_dir)
            
            # 缓存结果
            self.model_cache[model_path] = processed_model
            return processed_model
            
        except Exception as e:
            logger.error(f"Error parsing model file {model_path}: {e}")
            return None
            
    def process_model_data(self, model_data: Dict, model_path: str) -> Dict:
        """处理模型数据
        
        Args:
            model_data: 解析的JSON数据
            model_path: 模型文件所在路径
            
        Returns:
            处理后的模型数据
        """
        # 创建处理后的模型数据结构
        processed_model = {
            "Version": model_data.get("Version", 3),
            "FileReferences": {},
            "Groups": [],
            "Parameters": [],
            "Parts": []
        }
        
        # 处理文件引用
        file_refs = model_data.get("FileReferences", {})
        processed_model["FileReferences"] = self.process_file_references(file_refs, model_path)
        
        # 处理参数
        params = model_data.get("Parameters", {})
        if "Parameters" in params:  # Cubism 4格式
            processed_model["Parameters"] = params.get("Parameters", [])
        else:  # 直接包含参数列表
            processed_model["Parameters"] = params
            
        # 处理部件
        if "Parts" in model_data:
            processed_model["Parts"] = self.process_parts(model_data["Parts"], model_path)
            
        return processed_model
        
    def process_file_references(self, file_refs: Dict, model_path: str) -> Dict:
        """处理文件引用
        
        Args:
            file_refs: 文件引用数据
            model_path: 模型文件所在路径
            
        Returns:
            处理后的文件引用
        """
        processed_refs = {}
        
        # 处理Moc文件路径
        if "Moc" in file_refs:
            processed_refs["Moc"] = os.path.join(model_path, file_refs["Moc"])
            
        # 处理纹理路径
        if "Textures" in file_refs:
            processed_refs["Textures"] = []
            for texture in file_refs["Textures"]:
                processed_refs["Textures"].append(os.path.join(model_path, texture))
                
        # 处理物理文件路径
        if "Physics" in file_refs:
            processed_refs["Physics"] = os.path.join(model_path, file_refs["Physics"])
            
        # 处理动作文件路径
        if "Motions" in file_refs:
            processed_refs["Motions"] = {}
            for motion_group, motions in file_refs["Motions"].items():
                processed_refs["Motions"][motion_group] = []
                for motion in motions:
                    if isinstance(motion, dict) and "File" in motion:
                        processed_motion = motion.copy()
                        processed_motion["File"] = os.path.join(model_path, motion["File"])
                        processed_refs["Motions"][motion_group].append(processed_motion)
                    elif isinstance(motion, str):
                        processed_refs["Motions"][motion_group].append(os.path.join(model_path, motion))
                        
        return processed_refs
        
    def process_parts(self, parts: List[Dict], model_path: str) -> List[Dict]:
        """处理模型部件
        
        Args:
            parts: 部件数据列表
            model_path: 模型文件所在路径
            
        Returns:
            处理后的部件列表
        """
        processed_parts = []
        
        for part in parts:
            processed_part = part.copy()
            
            # 处理纹理路径
            if "TexturePath" in part:
                processed_part["TexturePath"] = os.path.join(model_path, part["TexturePath"])
                
            # 添加到列表
            processed_parts.append(processed_part)
            
        return processed_parts
        
    def load_physics(self, physics_path: str) -> Optional[Dict]:
        """加载物理文件
        
        Args:
            physics_path: 物理文件路径
            
        Returns:
            物理数据，如果加载失败则返回None
        """
        if not os.path.exists(physics_path):
            logger.warning(f"Physics file not found: {physics_path}")
            return None
            
        try:
            with open(physics_path, 'r', encoding='utf-8') as f:
                physics_data = json.load(f)
                
            return physics_data
            
        except Exception as e:
            logger.error(f"Error loading physics file {physics_path}: {e}")
            return None 