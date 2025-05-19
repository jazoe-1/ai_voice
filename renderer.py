import os
import json
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from OpenGL.GL import *
from OpenGL.GL import shaders
from PyQt5.QtGui import QImage
from .parameter import ParameterManager
from ..utils.math_utils import create_transform_matrix

logger = logging.getLogger(__name__)


class Texture:
    """OpenGL纹理"""

    def __init__(self, texture_id: int, width: int, height: int):
        self.id = texture_id
        self.width = width
        self.height = height


class TextureManager:
    """纹理管理器"""

    def __init__(self):
        self.textures = {}  # 纹理缓存
        self.quality = "high"  # 纹理质量: high, medium, low
        self.max_textures = 50  # 最大纹理缓存数量
        self.texture_usage = {}  # 纹理使用计数

    def set_quality(self, quality: str):
        """设置纹理质量"""
        if quality in ["high", "medium", "low"] and quality != self.quality:
            self.quality = quality
            self.clear_cache()

    def clear_cache(self):
        """清除纹理缓存"""
        for texture_id in self.textures.values():
            if hasattr(texture_id, 'id'):
                try:
                    glDeleteTextures(1, [texture_id.id])
                except Exception as e:
                    logger.error(f"删除纹理失败: {e}")
        self.textures.clear()
        self.texture_usage.clear()

    def load_texture(self, path: str, force_reload: bool = False) -> Optional[Texture]:
        """加载纹理 (优化版)

        Args:
            path: 纹理文件路径
            force_reload: 是否强制重新加载

        Returns:
            Texture对象或None（如果加载失败）
        """
        # 检查路径有效性
        if not path or not os.path.exists(path):
            logger.error(f"纹理路径无效: {path}")
            return None

        cache_key = f"{path}_{self.quality}"

        # 检查缓存
        if not force_reload and cache_key in self.textures:
            # 更新使用计数
            self.texture_usage[cache_key] = self.texture_usage.get(cache_key, 0) + 1
            return self.textures[cache_key]

        # 检查缓存大小，如果超过限制则清理最少使用的纹理
        if len(self.textures) >= self.max_textures:
            self._clean_least_used_textures()

        # 根据质量设置缩放因子
        scale = 1.0
        if self.quality == "medium":
            scale = 0.75
        elif self.quality == "low":
            scale = 0.5

        try:
            # 使用PIL加载图像
            with Image.open(path) as image:
                # 转换为RGBA模式
                image = image.convert("RGBA")
                
                # 根据缩放因子调整大小
                if scale < 1.0:
                    new_width = max(1, int(image.width * scale))
                    new_height = max(1, int(image.height * scale))
                    image = image.resize((new_width, new_height), Image.LANCZOS)
                
                # 获取像素数据
                img_data = np.array(image, dtype=np.uint8)

            # 创建OpenGL纹理
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)

            # 设置纹理参数
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

            # 上传纹理数据
            width, height = img_data.shape[1], img_data.shape[0]
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height,
                        0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

            # 创建Texture对象
            texture = Texture(texture_id, width, height)

            # 缓存并返回
            self.textures[cache_key] = texture
            self.texture_usage[cache_key] = 1
            return texture

        except Exception as e:
            logger.error(f"Error loading texture {path}: {e}")
            return None

    def _clean_least_used_textures(self):
        """清理最少使用的纹理"""
        if not self.textures:
            return
            
        # 按使用次数排序
        sorted_textures = sorted(self.texture_usage.items(), key=lambda x: x[1])
        
        # 删除最少使用的10%纹理
        textures_to_delete = sorted_textures[:max(1, len(sorted_textures) // 10)]
        
        for key, _ in textures_to_delete:
            if key in self.textures:
                texture = self.textures[key]
                if hasattr(texture, 'id'):
                    try:
                        glDeleteTextures(1, [texture.id])
                    except Exception as e:
                        logger.error(f"删除纹理失败: {e}")
                del self.textures[key]
                del self.texture_usage[key]
                logger.debug(f"清理未使用纹理: {key}")


class Renderer:
    """OpenGL渲染器"""

    def __init__(self, parameter_manager: ParameterManager):
        self.parameter_manager = parameter_manager
        self.texture_manager = TextureManager()
        self.parts = {}  # 存储模型部件
        self.initialized = False
        self.shader_program = None
        self.vao = None
        self.vbo = None
        self.ebo = None

    def initialize(self):
        """初始化OpenGL渲染器"""
        try:
            # 设置OpenGL版本和配置
            glClearColor(0.0, 0.0, 0.0, 0.0)  # 透明背景
            
            # 启用混合
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 创建着色器程序
            self.compile_shaders()
            
            # 创建顶点缓冲区
            self.create_buffers()
            
            # 初始化标志
            self.initialized = True
            # 创建测试网格
            self.create_simple_debug_mesh()
            logger.info("OpenGL渲染器初始化成功")
            
        except Exception as e:
            logger.error(f"OpenGL渲染器初始化失败: {e}")
            self.initialized = False
            # 显示更详细的错误信息
            self.show_opengl_error(str(e))

    def show_opengl_error(self, error_message):
        """显示OpenGL错误信息"""
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("OpenGL渲染错误")
        msg.setText("OpenGL渲染器初始化失败")
        msg.setInformativeText(f"错误信息: {error_message}")
        
        # 获取OpenGL版本信息
        try:
            vendor = glGetString(GL_VENDOR).decode('utf-8')
            renderer = glGetString(GL_RENDERER).decode('utf-8')
            version = glGetString(GL_VERSION).decode('utf-8')
            
            detailed_text = f"OpenGL详细信息:\n" \
                            f"供应商: {vendor}\n" \
                            f"渲染器: {renderer}\n" \
                            f"版本: {version}\n\n" \
                            f"请确保您的系统支持OpenGL 3.3或更高版本，并安装了最新的显卡驱动程序。"
            
            msg.setDetailedText(detailed_text)
        except:
            msg.setDetailedText("无法获取OpenGL信息。请确保您的系统支持OpenGL 3.3或更高版本。")
        
        msg.exec_()

    def compile_shaders(self):
        """编译顶点和片元着色器"""
        # 简化的顶点着色器
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 inTexCoord;
        
        out vec2 texCoord;
        
        uniform mat4 transform;
        
        void main()
        {
            gl_Position = vec4(position.x, position.y, 0.0, 1.0);
            texCoord = inTexCoord;
        }
        """

        # 简化的片元着色器
        fragment_shader_source = """
        #version 330 core
        in vec2 texCoord;
        
        out vec4 FragColor;
        
        uniform sampler2D textureSampler;
        uniform float alpha;
        
        void main()
        {
            FragColor = texture(textureSampler, texCoord);
            FragColor.a *= alpha;
        }
        """

        # 编译着色器
        try:
            vertex_shader = shaders.compileShader(vertex_shader_source, GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(fragment_shader_source, GL_FRAGMENT_SHADER)
            self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)
            
            # 获取uniform位置
            self.transform_loc = glGetUniformLocation(self.shader_program, "transform")
            self.texture_loc = glGetUniformLocation(self.shader_program, "textureSampler")
            self.alpha_loc = glGetUniformLocation(self.shader_program, "alpha")
            
            logging.info("着色器编译成功")
        except Exception as e:
            logging.error(f"Error compiling shaders: {e}")
            raise

    def create_buffers(self):
        """创建顶点缓冲对象"""
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)
        
        # 绑定VAO
        glBindVertexArray(self.vao)
        
        # 创建并绑定VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        
        # 创建并绑定EBO
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        
        # 设置顶点属性指针
        # 位置属性
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        # 纹理坐标属性
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        
        # 解绑VAO
        glBindVertexArray(0)

    def load_model(self, model_data: Dict):
        """加载模型数据
        
        Args:
            model_data: 解析后的模型数据
        """
        self.parts = {}
        
        # 加载所有部件
        parts_data = model_data.get("Parts", [])
        logger.info(f"Loading model with {len(parts_data)} parts")
        
        for part_data in parts_data:
            part_id = part_data.get("Id", "")
            if not part_id:
                continue
                
            # 创建部件对象
            part = {
                "id": part_id,
                "name": part_data.get("Name", ""),
                "opacity": 1.0,
                "visible": True,
                "texture_path": part_data.get("TexturePath", ""),
                "mesh": self.create_mesh_for_part(part_data),
                "deformers": part_data.get("Deformers", []),
                "depth": part_data.get("Depth", 0)
            }
            
            # 加载纹理
            if part["texture_path"]:
                texture_path = part["texture_path"]
                logger.info(f"Loading texture for part {part_id}: {texture_path}")
                
                # 检查路径是否存在
                if not os.path.exists(texture_path):
                    # 尝试相对于模型文件的路径
                    model_dir = model_data.get("__model_dir__", "")
                    if model_dir:
                        alt_path = os.path.join(model_dir, texture_path)
                        if os.path.exists(alt_path):
                            texture_path = alt_path
                            logger.info(f"Using alternative path: {texture_path}")
                
                texture = self.texture_manager.load_texture(texture_path)
                if texture:
                    part["texture"] = texture
                else:
                    logger.error(f"Failed to load texture for part {part_id}: {texture_path}")
            
            self.parts[part_id] = part
        
        logger.info(f"Model loaded with {len(self.parts)} valid parts")

    def create_mesh_for_part(self, part_data: Dict) -> Dict:
        """为部件创建网格数据
        
        Args:
            part_data: 部件数据
            
        Returns:
            网格数据字典
        """
        # 这里简化处理，为每个部件创建一个矩形网格
        # 实际应用中应该从模型文件中读取顶点数据
        
        # 默认的矩形顶点（包含位置和纹理坐标）
        vertices = np.array([
            # 位置(x,y,z)      # 纹理坐标(u,v)
            -0.5, -0.5, 0.0,    0.0, 1.0,
             0.5, -0.5, 0.0,    1.0, 1.0,
             0.5,  0.5, 0.0,    1.0, 0.0,
            -0.5,  0.5, 0.0,    0.0, 0.0
        ], dtype=np.float32)
        
        # 索引
        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)
        
        return {
            "vertices": vertices,
            "indices": indices,
            "vertex_count": 4,
            "index_count": 6
        }

    def render(self):
        """渲染当前模型"""
        if not self.initialized:
            logging.warning("渲染器未初始化")
            return
            
        if not self.parts:
            logging.warning("没有模型部件可渲染")
            return
            
        # 清除缓冲区
        glClear(GL_COLOR_BUFFER_BIT)
        
        # 使用着色器程序
        glUseProgram(self.shader_program)
        
        # 激活纹理单元并绑定VAO
        glActiveTexture(GL_TEXTURE0)
        glUniform1i(self.texture_loc, 0)
        glBindVertexArray(self.vao)
        
        # 按深度排序部件 - 只有在部件改变时才排序
        if not hasattr(self, '_sorted_parts') or len(self._sorted_parts) != len(self.parts):
            self._sorted_parts = sorted(self.parts.values(), key=lambda p: p.get("depth", 0))
        
        # 渲染每个部件
        for part in self._sorted_parts:
            if not part.get("visible", True):
                continue
                
            # 获取部件参数
            alpha = part.get("opacity", 1.0)
            
            # 应用参数影响 (性能优化：只在有deformers时计算)
            deformers = part.get("deformers", [])
            if deformers:
                for deformer in deformers:
                    param_name = deformer.get("parameter", "")
                    if param_name and deformer.get("type", "") == "opacity":
                        param_value = self.parameter_manager.get_parameter(param_name, 0.0)
                        alpha *= (1.0 + param_value * deformer.get("scale", 0.0))
            
            # 限制alpha值在有效范围内
            alpha = max(0.0, min(1.0, alpha))
            
            # 设置alpha uniform
            glUniform1f(self.alpha_loc, alpha)
            
            # 获取变换矩阵 (性能优化：使用缓存的矩阵)
            if not hasattr(self, '_transform_matrix'):
                self._transform_matrix = create_transform_matrix(0.0, 0.0, 0.0, 1.0, 1.0)
            
            # 设置变换矩阵uniform
            glUniformMatrix4fv(self.transform_loc, 1, GL_FALSE, self._transform_matrix)
            
            # 绑定纹理 (如果存在)
            if "texture" in part:
                glBindTexture(GL_TEXTURE_2D, part["texture"].id)
                
                # 获取网格数据
                mesh = part.get("mesh", {})
                if mesh:
                    # 缓存顶点和索引数据 (性能优化)
                    if not hasattr(mesh, '_cached'):
                        vertices = mesh.get("vertices")
                        indices = mesh.get("indices")
                        
                        if vertices is not None and indices is not None:
                            # 更新顶点缓冲 - 只在第一次或更改时
                            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
                            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
                            
                            # 更新索引缓冲 - 只在第一次或更改时
                            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
                            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
                            
                            # 标记为已缓存
                            mesh['_cached'] = True
                    
                    # 绘制
                    glDrawElements(GL_TRIANGLES, mesh.get("index_count", 0), GL_UNSIGNED_INT, None)
        
        # 解绑VAO
        glBindVertexArray(0)
        glUseProgram(0)

    def set_quality(self, quality: str):
        """设置渲染质量
        
        Args:
            quality: 质量级别 ("high", "medium", "low")
        """
        self.texture_manager.set_quality(quality)

    
    def create_simple_debug_mesh(self):
        """创建简单的调试用网格"""
        import ctypes
        
        # 简单的四边形顶点数据 - 使用更小的数据类型
        vertices = np.array([
            # 位置             # 纹理坐标
            -0.5, -0.5, 0.0,  0.0, 1.0,  # 左下
             0.5, -0.5, 0.0,  1.0, 1.0,  # 右下
             0.5,  0.5, 0.0,  1.0, 0.0,  # 右上
            -0.5,  0.5, 0.0,  0.0, 0.0   # 左上
        ], dtype=np.float32)
        
        # 索引数据
        indices = np.array([
            0, 1, 2,  # 第一个三角形
            2, 3, 0   # 第二个三角形
        ], dtype=np.uint32)
        
        # 创建一个测试部件
        if not hasattr(self, 'parts'):
            self.parts = {}
            
        self.parts['debug_quad'] = {
            'mesh': {
                'vertices': vertices,
                'indices': indices,
                'index_count': len(indices)
            },
            'visible': True,
            'opacity': 1.0,
            'depth': 0,
            'deformers': []
        }
        
        # 改用更小的测试纹理
        texture_size = 32  # 减小纹理尺寸
        
        # 使用预定义的纹理数据创建纹理
        texture_data = np.zeros((texture_size, texture_size, 4), dtype=np.uint8)
        
        # 使用简单的棋盘格图案 - 更高效的循环
        for i in range(texture_size * texture_size):
            x = i % texture_size
            y = i // texture_size
            if ((x // 4) + (y // 4)) % 2 == 0:  # 增大棋盘格
                texture_data[y, x] = [255, 0, 0, 255]  # 红色
            else:
                texture_data[y, x] = [255, 255, 255, 255]  # 白色
        
        # 创建纹理ID并配置
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        
        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # 加载纹理数据
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA, texture_size, texture_size, 0,
            GL_RGBA, GL_UNSIGNED_BYTE, texture_data
        )
        
        # 创建并存储纹理对象
        texture_obj = Texture(texture_id, texture_size, texture_size)
        self.parts['debug_quad']['texture'] = texture_obj
        self.texture_manager.textures['debug'] = texture_obj
        
        logging.info("已创建调试网格和纹理")
        return True
    
    def cleanup(self):
        """清理资源"""
        if self.shader_program:
            glDeleteProgram(self.shader_program)
            
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
            
        if self.vbo:
            glDeleteBuffers(1, [self.vbo])
            
        if self.ebo:
            glDeleteBuffers(1, [self.ebo])
            
        self.texture_manager.clear_cache()
        self.initialized = False 

    def render_model(self, model_path, pos_x, pos_y, scale=1.0, alpha=1.0):
        """渲染模型到指定位置"""
        if not self.initialized:
            logging.warning("Renderer not initialized, cannot render model")
            return

        try:
            # 加载纹理
            texture = self.texture_manager.load_texture(model_path)
            if not texture:
                logging.error(f"Failed to load texture for model: {model_path}")
                return
                
            # 使用着色器程序
            glUseProgram(self.shader_program)
                
            # 设置纹理
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, texture.id)
            glUniform1i(self.texture_loc, 0)
                
            # 设置透明度
            glUniform1f(self.alpha_loc, alpha)
            
            # 计算变换矩阵
            transform = create_transform_matrix(
                tx=pos_x, ty=pos_y,
                rotation=0.0,
                sx=scale, sy=scale
            )
            
            # 设置变换矩阵uniform
            glUniformMatrix4fv(self.transform_loc, 1, GL_FALSE, transform)
                
            # 绑定VAO和绘制
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
                
            # 解绑纹理
            glBindTexture(GL_TEXTURE_2D, 0)
                
        except Exception as e:
            logging.error(f"Error rendering model {model_path}: {e}") 