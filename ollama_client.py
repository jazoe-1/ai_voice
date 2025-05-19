#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import time
from urllib.parse import urljoin
from logger import logger

class OllamaClient:
    def __init__(self, base_url, api_key=None, model=None, is_local=None):
        """初始化OllamaClient"""
        # 使用属性设置器确保正确设置URL和is_local属性
        self._base_url = None
        self._is_local = None
        self.set_base_url(base_url)  # 使用方法正确设置
        self.api_key = api_key
        self.model = model or "llama2"
        
        # 如果显式传入is_local，则使用传入值，否则自动检测
        if is_local is not None:
            self._is_local = is_local
        
        logger.info(f"OllamaClient初始化: URL={self.base_url}, is_local={self.is_local}")
        
        # 检测 API 版本
        self.api_endpoint = "generate"  # 默认值
        if self.check_connection():
            self.detect_api_version()
    
    @property
    def base_url(self):
        """获取API基础URL"""
        return self._base_url
    
    @base_url.setter
    def base_url(self, url):
        """设置API基础URL"""
        self.set_base_url(url)
    
    def set_base_url(self, url):
        """设置API基础URL并自动判断模式"""
        if not url:
            url = "http://localhost:11434"
        
        self._base_url = url.rstrip('/')
        
        # 自动判断是否为本地模式
        if 'localhost' in url or '127.0.0.1' in url:
            self._is_local = True
        elif 'openrouter.ai' in url:
            self._is_local = False
    
    @property
    def is_local(self):
        """获取是否为本地模式"""
        return self._is_local
    
    @is_local.setter
    def is_local(self, value):
        """设置是否为本地模式"""
        self._is_local = bool(value)
        
        # 如果切换模式，确保URL是合理的
        if self._is_local and ('openrouter.ai' in self._base_url):
            self._base_url = "http://localhost:11434"
            logger.info("切换到本地模式，重置URL为localhost")
        elif not self._is_local and ('localhost' in self._base_url or '127.0.0.1' in self._base_url):
            self._base_url = "https://openrouter.ai/api/v1"
            logger.info("切换到远程模式，重置URL为OpenRouter")
    
    def list_models(self):
        """获取可用模型列表"""
        try:
            logger.info(f"正在获取模型列表: mode={self.is_local}, URL={self.base_url}")
            
            # 如果URL和模式不匹配，强制修复
            is_local_url = 'localhost' in self.base_url or '127.0.0.1' in self.base_url
            if self.is_local != is_local_url:
                logger.warning(f"发现模式和URL不匹配，修复中: is_local={self.is_local}, URL={self.base_url}")
                if self.is_local:
                    self.base_url = "http://localhost:11434"
                else:
                    self.base_url = "https://openrouter.ai/api/v1"
            
            logger.info("获取可用模型列表")
            if self.is_local:
                # 本地Ollama API
                logger.info(f"从本地Ollama获取模型列表: {self.base_url}")
                
                # 首先尝试新的API端点 (适用于Ollama较新版本)
                try:
                    url = urljoin(self.base_url, '/api/tags')
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    logger.debug(f"Ollama返回数据: {data}")
                    
                    # 解析不同格式的API响应
                    if 'models' in data:
                        # 新版API格式
                        models = [model['name'] for model in data.get('models', [])]
                        logger.info(f"使用新API格式解析到 {len(models)} 个模型")
                    elif isinstance(data, list):
                        # 可能是旧版API，直接返回模型列表
                        models = [model.get('name', '') for model in data if 'name' in model]
                        logger.info(f"使用旧API格式解析到 {len(models)} 个模型")
                    else:
                        # 未知格式，尝试查找已知字段
                        models = []
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if isinstance(value, list) and value and isinstance(value[0], dict) and 'name' in value[0]:
                                    models = [item['name'] for item in value]
                                    logger.info(f"尝试解析未知格式，找到 {len(models)} 个模型")
                                    break
                    
                    if not models:
                        # 如果未解析到模型，尝试备用API端点
                        raise Exception("未从主API端点解析到模型")
                    
                    logger.info(f"本地Ollama模型: {models}")
                    return models
                    
                except Exception as e:
                    # 如果主API端点失败，尝试备用API端点
                    logger.warning(f"主API端点失败: {e}，尝试备用端点")
                    try:
                        url = urljoin(self.base_url, '/api/models')
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        
                        data = response.json()
                        if 'models' in data:
                            models = [model['name'] for model in data.get('models', [])]
                        else:
                            models = []
                        
                        logger.info(f"从备用API获取到 {len(models)} 个模型")
                        return models
                    except Exception as backup_e:
                        # 如果两个端点都失败，显示详细错误
                        logger.error(f"所有API端点都失败: {backup_e}")
                        raise Exception(f"无法获取本地Ollama模型列表，请确保Ollama服务正在运行: {backup_e}")
                
            else:
                # OpenRouter API - 修复编码问题
                url = "https://openrouter.ai/api/v1/models"
                
                # 确保所有请求头值都是ASCII编码兼容的
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost',
                    'X-Title': 'AI Voice Assistant'  # 使用英文名称避免编码问题
                }
                
                logger.info(f"请求OpenRouter模型列表: {url}")
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # 解析响应
                data = response.json()
                
                if 'data' in data and isinstance(data['data'], list):
                    models = [model['id'] for model in data['data']]
                    logger.info(f"找到 {len(models)} 个OpenRouter模型")
                    return models
                else:
                    logger.warning(f"OpenRouter响应格式异常: {data}")
                    return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取模型列表失败: {e}")
            raise Exception(f"获取模型列表失败: {e}")
        except UnicodeEncodeError as e:
            # 特别处理编码错误
            logger.error(f"编码错误: {e}")
            logger.error("可能是请求头中包含了非ASCII字符")
            # 尝试使用安全的ASCII请求头重试
            try:
                safe_headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost',
                    'X-Title': 'AI-Assistant'
                }
                response = requests.get(url, headers=safe_headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                if 'data' in data and isinstance(data['data'], list):
                    models = [model['id'] for model in data['data']]
                    logger.info(f"使用安全请求头成功获取 {len(models)} 个模型")
                    return models
            except Exception as retry_e:
                logger.error(f"重试失败: {retry_e}")
            raise Exception("API请求编码错误，请确保所有设置使用英文字符")
    
    def check_service(self):
        """检查服务是否可用"""
        try:
            logger.info(f"检查服务可用性: {self.base_url}")
            if self.is_local:
                # 恢复原来能正常工作的 API 调用方式
                try:
                    # 尝试获取模型列表，用于检查服务是否可用
                    url = urljoin(self.base_url, '/api/tags')
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        logger.info("Ollama服务连接正常")
                        return True
                    else:
                        logger.warning(f"Ollama服务响应异常: {response.status_code}")
                        return False
                except Exception as e:
                    logger.error(f"检查Ollama服务失败: {e}")
                    return False
            else:
                # OpenRouter API
                url = "https://openrouter.ai/api/v1/models"
                
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    logger.info("OpenRouter服务连接正常")
                    return True
                else:
                    logger.warning(f"OpenRouter服务响应异常: {response.status_code}")
                    return False
                
        except Exception as e:
            logger.error(f"检查服务可用性失败: {e}")
            return False

    def get_response(self, prompt, system_prompt=None):
        """获取AI响应"""
        if not prompt:
            return ""
        
        try:
            logger.info(f"发送请求到AI模型: {self.model}")
            
            if self.is_local:
                # 尝试使用完整的Ollama API
                url = urljoin(self.base_url, '/api/chat/completions')
                
                # 准备请求体 - 使用完整的OpenAI格式
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                }
                
                logger.info(f"发送请求到本地Ollama: {url}")
                logger.info(f"请求负载: {json.dumps(payload)}")
                
                # 发送请求
                response = requests.post(url, json=payload, timeout=120)
                response.raise_for_status()
                
                # 处理响应
                response_data = response.json()
                
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    return response_data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"响应格式不正确: {response_data}")
                    return ""
                
            else:
                # OpenRouter API
                url = "https://openrouter.ai/api/v1/chat/completions"
                
                # 修复请求头
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'http://localhost',
                    'X-Title': 'AI Voice Assistant'
                }
                
                # 构建消息
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                messages.append({"role": "user", "content": prompt})
                
                # 修复请求体，确保符合OpenRouter要求
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                
                logger.info(f"发送请求到OpenRouter: {url}")
                logger.info(f"请求模型: {self.model}")
                logger.debug(f"请求负载: {json.dumps(payload)}")
                
                # 发送请求
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                # 检查错误并尝试获取详细错误信息
                if response.status_code != 200:
                    error_detail = "未知错误"
                    try:
                        error_json = response.json()
                        if 'error' in error_json:
                            error_detail = f"{error_json['error'].get('message', '未提供错误详情')}"
                        logger.error(f"OpenRouter错误详情: {error_detail}")
                    except:
                        pass
                    raise Exception(f"OpenRouter错误: {response.status_code} - {error_detail}")
                
                # 解析响应
                data = response.json()
                
                # 验证响应格式
                if 'choices' in data and len(data['choices']) > 0:
                    if 'message' in data['choices'][0]:
                        ai_response = data['choices'][0]['message']['content']
                        logger.info(f"获取到AI响应: {len(ai_response)} 个字符")
                        return ai_response
                
                logger.error(f"响应格式不正确: {data}")
                return "OpenRouter返回了不正确的格式。请检查日志获取详情。"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取AI响应失败: {e}")
            raise Exception(f"获取AI响应失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"解析响应失败: {e}")
            raise Exception(f"解析响应失败: {e}")
        except KeyError as e:
            logger.error(f"响应格式错误: {e}")
            raise Exception(f"响应格式错误: {e}")
        except Exception as e:
            logger.error(f"获取AI响应时发生未知错误: {e}")
            raise Exception(f"获取AI响应时发生未知错误: {e}")

    def generate(self, message, system_prompt=None):
        """生成回复"""
        try:
            # 获取当前角色的系统提示词
            if system_prompt is None:
                system_prompt = "你是一个有帮助的AI助手。"
            
            # 尝试新版 API：先尝试 /api/chat
            try:
                url = f"{self.base_url}/api/chat"
                data = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "stream": False
                }
                
                logger.info(f"尝试使用 /api/chat 端点: {url}")
                response = requests.post(url, json=data, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('message', {}).get('content', '')
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"使用 /api/chat 端点失败: {e}, 尝试使用 /api/generate 端点")

            # 如果 /api/chat 失败，尝试旧版 API：/api/generate
            url = f"{self.base_url}/api/generate"
            data = {
                "model": self.model,
                "prompt": message,
                "system": system_prompt,
                "stream": False
            }
            
            logger.info(f"尝试使用 /api/generate 端点: {url}")
            response = requests.post(url, json=data, timeout=60)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            return result.get('response', '')
        
        except Exception as e:
            logger.error(f"Ollama生成回复失败: {e}")
            raise Exception(f"AI生成回复失败: {str(e)}")

    def detect_api_version(self):
        """检测 Ollama API 版本，确定使用哪个端点"""
        try:
            # 先尝试获取版本信息
            url = f"{self.base_url}/api/version"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                version_info = response.json()
                version = version_info.get('version', '')
                logger.info(f"Ollama 服务器版本: {version}")
                
                # 分析版本号确定使用哪个 API
                # 通常 0.x.x 版本使用 /api/generate
                # 1.x.x 及以上版本使用 /api/chat
                if version.startswith("0."):
                    self.api_endpoint = "generate"
                else:
                    self.api_endpoint = "chat"
                    
                return self.api_endpoint
                
            # 如果无法获取版本，则通过尝试不同端点来判断
            chat_url = f"{self.base_url}/api/chat"
            generate_url = f"{self.base_url}/api/generate"
            
            # 尝试 chat API
            try:
                chat_response = requests.post(chat_url, json={"model": self.model}, timeout=2)
                if chat_response.status_code != 404:  # 即使返回错误，只要不是404就说明端点存在
                    self.api_endpoint = "chat"
                    return "chat"
            except:
                pass
            
            # 尝试 generate API
            try:
                generate_response = requests.post(generate_url, json={"model": self.model}, timeout=2)
                if generate_response.status_code != 404:
                    self.api_endpoint = "generate"
                    return "generate"
            except:
                pass
            
            # 默认使用 generate
            self.api_endpoint = "generate"
            return "generate"
            
        except Exception as e:
            logger.error(f"检测 Ollama API 版本失败: {e}")
            self.api_endpoint = "generate"  # 默认使用旧版API
            return "generate"

    def check_connection(self):
        """检查与Ollama服务器的连接"""
        try:
            # 尝试连接到Ollama服务
            url = f"{self.base_url}/api/tags"
            logger.info(f"检查Ollama连接: {url}")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info("Ollama连接成功")
                return True
            else:
                logger.warning(f"Ollama连接失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.warning(f"无法连接到Ollama服务: {self.base_url}")
            return False
        except Exception as e:
            logger.error(f"检查Ollama连接时发生错误: {e}")
            return False