#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import time
import uuid
import json
import platform
import requests
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QDialog, QListWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog

from audio_processor import AudioProcessor
from ollama_client import OllamaClient
from role_manager import RoleManager
from ui.role_dialog import RoleEditDialog
from config import load_config, save_config
from logger import logger
from chat_tts_client import ChatTTSClient
from utils import handle_errors, safe_connect

# 添加对UnifiedMainWindow的检测和兼容性支持
def is_compatible_window(window):
    """检查窗口是否兼容"""
    required_attrs = ['start_listen_btn', 'stop_listen_btn', 'send_text_btn', 'input_text', 'tab_widget']
    for attr in required_attrs:
        if not hasattr(window, attr):
            logger.warning(f"主窗口缺少必要属性: {attr}")
            return False
    return True

class VoiceAssistantCore(QObject):
    """与UI解耦的语音助手核心类
    
    推荐使用此类作为主要实现，而非完整的VoiceAssistant类。
    这个类已被设计为与UI解耦，更容易测试和维护。
    """
    
    # 定义信号
    speech_recognized_signal = pyqtSignal(str)
    response_received_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)
    
    def __init__(self, main_window, connect_ui=False):
        super().__init__()
        self.main_window = main_window
        
        # 添加状态跟踪属性
        self.is_listening = False
        self.is_processing = False
        self.ollama_available = False  # 添加Ollama可用性标志
        
        # 加载配置
        self.config = load_config()
        
        # 只初始化核心组件，不触及UI
        self.init_core_components()
        
        # 如果要求，连接UI
        if connect_ui:
            QTimer.singleShot(100, self.connect_to_ui)
    
    def init_core_components(self):
        """只初始化核心组件，避免访问UI"""
        try:
            # 初始化音频处理器
            self.audio_processor = AudioProcessor(
                language=self.config.get("language", "zh"),
                recognition_mode=self.config.get("recognition_mode", "vosk"),
                voice_rate=self.config.get("voice_rate", 180),
                voice_volume=self.config.get("voice_volume", 0.9),
                use_ai_voice=self.config.get("use_ai_voice", True)
            )
            
            # 添加功能检查
            self._check_audio_processor_capabilities()
            
            # 初始化Ollama客户端
            self.ollama_client = OllamaClient(
                base_url=self.config.get("ollama_url", "http://localhost:11434"),
                api_key=self.config.get("api_key", ""),
                model=self.config.get("model", "llama2"),
                is_local=self.config.get("is_local", True)
            )
            
            # 初始化角色管理器
            self.role_manager = RoleManager()
            
            # 初始化完成标志
            self.is_initialized = True
            
            logger.info("核心组件初始化完成")
        except Exception as e:
            self.is_initialized = False
            logger.error(f"核心组件初始化失败: {e}")
            raise

    def check_initialization(self):
        """检查核心组件是否已初始化"""
        if not hasattr(self, 'is_initialized') or not self.is_initialized:
            self.init_core_components()
        return self.is_initialized

    def _check_audio_processor_capabilities(self):
        """检查音频处理器的功能"""
        # 检查语音识别方法
        has_recognition = (hasattr(self.audio_processor, 'start_listening') or 
                          hasattr(self.audio_processor, 'start_recognition') or
                          hasattr(self.audio_processor, 'listen'))
        
        if not has_recognition:
            logger.warning("AudioProcessor没有可用的语音识别方法")
        
        # 检查语音合成功能
        has_synthesis = hasattr(self.audio_processor, 'speak') or hasattr(self.audio_processor, 'synthesize')
        
        if not has_synthesis:
            logger.warning("AudioProcessor没有可用的语音合成方法")
    
    @handle_errors
    def connect_to_ui(self):
        """在UI完全加载后连接信号"""
        try:
            # 首先检查窗口兼容性
            if not is_compatible_window(self.main_window):
                logger.error("主窗口不兼容，无法连接UI")
                return
            
            # 连接基本按钮信号
            if hasattr(self.main_window, "start_listen_btn"):
                safe_connect(self.main_window.start_listen_btn.clicked, 
                           self.start_listening, "start_listen_btn")
            
            if hasattr(self.main_window, "stop_listen_btn"):
                safe_connect(self.main_window.stop_listen_btn.clicked, 
                           self.stop_listening, "stop_listen_btn")
            
            if hasattr(self.main_window, "send_text_btn"):
                safe_connect(self.main_window.send_text_btn.clicked, 
                           self.send_message, "send_text_btn")
            
            # 连接语音类型切换信号
            if hasattr(self.main_window, "system_voice_btn"):
                safe_connect(self.main_window.system_voice_btn.toggled,
                    lambda checked: self.on_voice_type_changed("system") if checked else None,
                    "system_voice_btn")
            
            if hasattr(self.main_window, "ai_voice_btn"):
                safe_connect(self.main_window.ai_voice_btn.toggled,
                    lambda checked: self.on_voice_type_changed("ai") if checked else None,
                    "ai_voice_btn")
            
            if hasattr(self.main_window, "chat_tts_btn"):
                safe_connect(self.main_window.chat_tts_btn.toggled,
                    lambda checked: self.on_voice_type_changed("chat_tts") if checked else None,
                    "chat_tts_btn")
            
            # 连接我们自己的信号到UI更新方法
            self.speech_recognized_signal.connect(lambda text: self.main_window.update_chat("user", text))
            self.response_received_signal.connect(lambda text: self.main_window.update_chat("assistant", text))
            self.status_signal.connect(self.main_window.update_status)
            self.error_signal.connect(self.main_window.show_error)
            
            logger.info("UI信号连接成功")
        except Exception as e:
            logger.error(f"连接UI信号失败: {e}")
            raise

    # 添加这个辅助方法用于检查信号是否已连接
    def _is_signal_connected(self, signal, slot):
        """检查信号是否已连接到指定的槽函数"""
        try:
            # 在PyQt5中，没有直接的API检查信号连接，但可以使用以下方法:
            # 尝试断开连接，如果成功返回True，说明之前已连接
            return signal.disconnect(slot)
        except TypeError:
            # 如果断开失败，则说明之前未连接
            return False
        except Exception:
            # 其他错误情况也视为未连接
            return False

    @handle_errors
    def start_listening(self):
        """开始监听"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.status_signal.emit("正在聆听...")
        
        # 使用音频处理器的start_listening方法
        if hasattr(self.audio_processor, 'start_listening'):
            success = self.audio_processor.start_listening(
                callback=self.on_speech_recognized
            )
            if not success:
                self.is_listening = False
                self.status_signal.emit("启动语音识别失败")
                return False
            return True
        else:
            logger.error("AudioProcessor没有start_listening方法")
            self.error_signal.emit("功能不可用", "语音识别功能不可用")
            self.is_listening = False
            self.status_signal.emit("就绪")
            return False

    @handle_errors
    def stop_listening(self):
        """停止监听"""
        try:
            if not self.is_listening:
                return True
            
            self.is_listening = False
            
            # 使用音频处理器的stop_listening方法
            if hasattr(self.audio_processor, 'stop_listening'):
                success = self.audio_processor.stop_listening()
                if not success:
                    logger.warning("停止语音识别可能不完全")
            
            self.status_signal.emit("就绪")
            return True
        except Exception as e:
            self.error_signal.emit("停止语音识别错误", str(e))
            return False
            
    @handle_errors
    def send_message(self, message):
        """发送文本消息"""
        try:
            text = ""
            if hasattr(self.main_window, "input_text") and self.main_window.input_text:
                text = self.main_window.input_text.text().strip()
                self.main_window.input_text.clear()
                
            if not text:
                return
                
            # 将用户消息添加到聊天历史
            self.speech_recognized_signal.emit(text)
            
            # 处理消息
            self.process_user_message(text)
        except Exception as e:
            self.error_signal.emit("发送消息错误", str(e))
            
    @handle_errors
    def process_user_message(self, message):
        """处理用户消息"""
        if self.is_processing:
            self.error_signal.emit("处理中", "已有消息正在处理，请稍后...")
            return
            
        self.is_processing = True
        self.status_signal.emit("思考中...")
        
        # 获取当前角色和模型信息
        try:
            # 获取当前角色的系统提示词
            system_prompt = "你是一个有帮助的AI助手。"
            if hasattr(self, "current_role") and self.current_role:
                system_prompt = self.current_role.get("system_prompt", system_prompt)
            
            # 记录当前使用的模型
            current_model = self.config.get("model", "未知")
            logger.info(f"使用模型 '{current_model}' 和角色系统提示词处理消息")
            
            # 使用线程处理请求，避免阻塞UI
            thread = threading.Thread(
                target=self._process_message_thread, 
                args=(message, system_prompt)
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            logger.error(f"准备处理消息失败: {e}")
            self.error_signal.emit("处理错误", f"准备处理消息时出错: {str(e)}")
            self.is_processing = False
            self.status_signal.emit("就绪")

    def _process_message_thread(self, message, system_prompt):
        """在线程中处理消息"""
        try:
            # 验证Ollama客户端是否已正确配置
            if not hasattr(self, "ollama_client") or not self.ollama_client:
                raise Exception("AI引擎未初始化")
            
            # 确保模型设置正确
            model = self.config.get("model", "llama2")
            if self.ollama_client.model != model:
                logger.warning(f"模型不匹配，更新客户端模型从 '{self.ollama_client.model}' 到 '{model}'")
                self.ollama_client.model = model
            
            # 发送到模型并获取响应
            response = self.ollama_client.generate(message, system_prompt)
            
            # 发出响应信号
            self.response_received_signal.emit(response)
            
            # 朗读响应（如果已启用）
            # 这里需要实现TTS功能
            
            self.status_signal.emit("就绪")
        except Exception as e:
            logger.error(f"AI响应错误: {e}")
            self.error_signal.emit("AI响应错误", str(e))
        finally:
            self.is_processing = False

    def on_speech_recognized(self, text):
        """收到语音识别结果"""
        if not text or text.isspace():
            return
        
        # 发出信号
        self.speech_recognized_signal.emit(text)
        
        # 处理消息
        self.process_user_message(text)

    def test_voice(self):
        """测试语音合成功能"""
        try:
            # 获取测试文本
            test_text = ""
            if self.has_ui_component("test_input"):
                test_text = self.main_window.test_input.text().strip()
            
            if not test_text:
                test_text = "这是一个语音合成测试，听起来怎么样？"
            
            # 获取TTS设置
            tts_type = "system"
            if self.has_ui_component("ai_voice_btn") and self.main_window.ai_voice_btn.isChecked():
                tts_type = "ai"
            elif self.has_ui_component("chat_tts_btn") and self.main_window.chat_tts_btn.isChecked():
                tts_type = "chat_tts"
            
            # 获取语速和音量
            speed = 1.0
            volume = 1.0
            if self.has_ui_component("voice_speed_spin"):
                speed = self.main_window.voice_speed_spin.value() / 180.0
            if self.has_ui_component("voice_volume_spin"):
                volume = self.main_window.voice_volume_spin.value()
            
            # 获取选择的语音
            voice = None
            if self.has_ui_component("voice_combo") and self.main_window.voice_combo.currentText():
                voice = self.main_window.voice_combo.currentText()
            
            # 直接使用speak_text函数，不再尝试使用audio_processor.speak
            from audio_processor import speak_text
            speak_text(
                text=test_text, 
                speed=speed, 
                volume=volume, 
                voice=voice,  # 传递选择的语音
                tts_type=tts_type
            )
            
            self.status_signal.emit(f"测试语音播放中: {test_text[:20]}...")
        except Exception as e:
            logger.error(f"测试语音失败: {e}")
            self.error_signal.emit("测试失败", f"无法播放测试语音: {str(e)}")

    @handle_errors
    def apply_voice_settings(self):
        """应用语音合成设置"""
        try:
            # 获取当前语音类型
            voice_type = "system"
            if self.has_ui_component("ai_voice_btn") and self.main_window.ai_voice_btn.isChecked():
                voice_type = "ai"
            elif self.has_ui_component("chat_tts_btn") and self.main_window.chat_tts_btn.isChecked():
                voice_type = "chat_tts"
            
            logger.info(f"正在应用语音设置，类型: {voice_type}")
            
            settings = {
                "voice_type": voice_type,
                "rate": self.get_voice_rate(),
                "volume": self.get_voice_volume(),
                "voice_id": self.get_selected_voice()
            }
            
            # 如果是ChatTTS，添加路径设置
            if voice_type == "chat_tts" and self.has_ui_component("chat_tts_path"):
                chat_tts_path = self.main_window.chat_tts_path.text().strip()
                if chat_tts_path:
                    settings["chat_tts_path"] = chat_tts_path
            
            logger.info(f"语音设置: {settings}")
            success = self.audio_processor.apply_settings("voice", settings)
            if success:
                self.status_signal.emit("语音设置已更新")
                logger.info("语音设置应用成功")
            else:
                raise Exception("应用语音设置失败")
            return success
        except Exception as e:
            logger.error(f"应用语音设置失败: {e}")
            self.error_signal.emit("设置错误", str(e))
            return False

    @handle_errors
    def apply_recognition_settings(self):
        """应用语音识别设置"""
        try:
            settings = {
                "mode": self.get_recognition_mode(),
                "timeout": self.get_listen_timeout(),
                "energy_threshold": self.get_energy_threshold(),
                "pause_threshold": self.get_pause_threshold()
            }
            
            success = self.audio_processor.apply_settings("recognition", settings)
            if success:
                self.status_signal.emit("语音识别设置已更新")
            return success
        except Exception as e:
            logger.error(f"应用语音识别设置失败: {e}")
            self.error_signal.emit("设置错误", str(e))
            return False

    def load_ui_data(self):
        """加载UI数据"""
        try:
            # 加载角色列表
            if self.has_ui_component("role_combo") and hasattr(self, 'role_manager'):
                roles = self.role_manager.get_all_roles()
                role_names = [role.get("name", "未命名角色") for role in roles]
                # 使用信号或方法更新UI，避免直接访问
                if hasattr(self.main_window, 'update_role_list'):
                    self.main_window.update_role_list(role_names)
                else:
                    # 退回到直接访问方式
                    self.main_window.role_combo.clear()
                    for role_name in role_names:
                        self.main_window.role_combo.addItem(role_name)
                    
            # 加载模型列表
            if self.has_ui_component("model_combo"):
                self.update_model_list()
                
            # 加载语音列表
            if self.has_ui_component("voice_combo"):
                try:
                    voices = self.get_available_voices()
                    # 使用信号或方法更新UI
                    if hasattr(self.main_window, 'update_voice_list'):
                        self.main_window.update_voice_list(voices)
                    else:
                        # 退回到直接访问方式
                        self.main_window.voice_combo.clear()
                        for voice in voices:
                            self.main_window.voice_combo.addItem(voice)
                except Exception as e:
                    logger.error(f"获取可用语音失败: {e}")
                    self.error_signal.emit("语音加载失败", f"无法获取可用语音: {str(e)}")
                    
            # 加载语音识别模型
            if self.has_ui_component("vosk_model_combo"):
                try:
                    models = self.get_vosk_models()
                    # 使用信号或方法更新UI
                    if hasattr(self.main_window, 'update_local_models'):
                        self.main_window.update_local_models("vosk", models)
                    else:
                        # 退回到直接访问方式
                        self.main_window.vosk_model_combo.clear()
                        for model in models:
                            self.main_window.vosk_model_combo.addItem(model)
                    
                    # 确保有模型选择
                    if self.main_window.vosk_model_combo.count() == 0:
                        self.main_window.vosk_model_combo.addItem("未找到模型，请下载")
                except Exception as e:
                    logger.error(f"获取Vosk模型失败: {e}")
                    self.error_signal.emit("模型加载失败", f"无法获取Vosk模型: {str(e)}")
                    
            # 应用现有配置
            self.apply_config_to_ui()
            
            logger.info("UI数据加载完成")
        except Exception as e:
            logger.error(f"加载UI数据失败: {e}")
            self.error_signal.emit("数据加载失败", f"无法加载界面数据: {str(e)}")

    def apply_config_to_ui(self):
        """应用配置到UI"""
        try:
            # 应用API设置
            if self.has_ui_component("local_api_btn") and self.has_ui_component("remote_api_btn"):
                is_local = self.config.get("is_local", True)
                if is_local:
                    self.main_window.local_api_btn.setChecked(True)
                else:
                    self.main_window.remote_api_btn.setChecked(True)
                    
            if self.has_ui_component("ollama_url"):
                self.main_window.ollama_url.setText(self.config.get("ollama_url", "http://localhost:11434"))
                
            if self.has_ui_component("api_key"):
                self.main_window.api_key.setText(self.config.get("api_key", ""))
                
            # 应用语音设置
            tts_type = self.config.get("tts_type", "system")
            if self.has_ui_component("system_voice_btn") and tts_type == "system":
                self.main_window.system_voice_btn.setChecked(True)
            elif self.has_ui_component("ai_voice_btn") and tts_type == "ai":
                self.main_window.ai_voice_btn.setChecked(True)
            elif self.has_ui_component("chat_tts_btn") and tts_type == "chat_tts":
                self.main_window.chat_tts_btn.setChecked(True)
                
            if self.has_ui_component("voice_speed_spin"):
                speed = self.config.get("tts_speed", 1.0)
                self.main_window.voice_speed_spin.setValue(int(speed * 180))
                
            if self.has_ui_component("voice_volume_spin"):
                volume = self.config.get("tts_volume", 0.8)
                self.main_window.voice_volume_spin.setValue(volume)
                
            if self.has_ui_component("chat_tts_path"):
                self.main_window.chat_tts_path.setText(self.config.get("chat_tts_path", ""))
                
            # 应用语音识别设置
            recognition_mode = self.config.get("recognition_mode", "vosk")
            if self.has_ui_component("recognition_vosk_btn") and recognition_mode == "vosk":
                self.main_window.recognition_vosk_btn.setChecked(True)
            elif self.has_ui_component("recognition_cloud_btn") and recognition_mode == "cloud":
                self.main_window.recognition_cloud_btn.setChecked(True)
            elif self.has_ui_component("recognition_whisper_btn") and recognition_mode == "whisper":
                self.main_window.recognition_whisper_btn.setChecked(True)
                
            if self.has_ui_component("listen_timeout"):
                self.main_window.listen_timeout.setValue(self.config.get("listen_timeout", 5))
                
            if self.has_ui_component("energy_threshold"):
                self.main_window.energy_threshold.setValue(self.config.get("energy_threshold", 300))
                
            if self.has_ui_component("pause_threshold"):
                self.main_window.pause_threshold.setValue(self.config.get("pause_threshold", 0.8))
                
        except Exception as e:
            logger.error(f"应用配置到UI失败: {e}")

    def update_model_list(self):
        """更新模型列表"""
        try:
            if not self.has_ui_component("model_combo"):
                logger.warning("模型下拉框不可用")
                return
            
            # 获取当前选择的模型
            current_model = ""
            if self.main_window.model_combo.currentText():
                current_model = self.main_window.model_combo.currentText()
            
            # 清空下拉框
            self.main_window.model_combo.clear()
            
            # 获取可用模型
            try:
                # 检查是否可以连接到Ollama
                self.check_ollama_connection()
                
                if not self.ollama_available:
                    self.main_window.model_combo.addItem("无法连接到Ollama")
                    return
                
                # 获取模型列表
                models = self.ollama_client.list_models()
                
                if not models:
                    self.main_window.model_combo.addItem("未找到可用模型")
                    return
                
                # 将模型添加到下拉框
                for model in models:
                    self.main_window.model_combo.addItem(model)
                
                # 恢复之前选择的模型
                if current_model:
                    index = self.main_window.model_combo.findText(current_model)
                    if index >= 0:
                        self.main_window.model_combo.setCurrentIndex(index)
                    
                # 如果没有选择任何模型，默认选择第一个
                if self.main_window.model_combo.currentIndex() < 0 and self.main_window.model_combo.count() > 0:
                    self.main_window.model_combo.setCurrentIndex(0)
                
                self.status_signal.emit(f"已获取 {len(models)} 个可用模型")
                
            except Exception as e:
                logger.error(f"获取模型列表失败: {e}")
                self.main_window.model_combo.addItem("获取模型失败")
            
        except Exception as e:
            logger.error(f"更新模型列表失败: {e}")
            self.error_signal.emit("更新失败", f"无法更新模型列表: {str(e)}")
        
    def check_ollama_connection(self):
        """检查Ollama连接"""
        try:
            if not hasattr(self, 'ollama_client'):
                if not self.check_initialization():
                    raise Exception("核心组件未初始化")
            
            # 获取Ollama服务器信息
            url = self.config.get("ollama_url", "http://localhost:11434")
            response = self.ollama_client.check_connection()
            if response:
                self.ollama_available = True
                logger.info(f"Ollama连接正常: {url}")
                return True
            else:
                self.ollama_available = False
                logger.warning(f"无法连接到Ollama: {url}")
                return False
        except Exception as e:
            self.ollama_available = False
            logger.error(f"检查Ollama连接失败: {e}")
            return False
        
    def has_ui_component(self, component_name):
        """检查UI组件是否存在
        
        Args:
            component_name: 组件名称
            
        Returns:
            组件是否存在
        """
        # 先检查主窗口是否有此属性
        if hasattr(self.main_window, component_name) and getattr(self.main_window, component_name) is not None:
            return True
        
        # 再检查ui_aliases字典
        if hasattr(self.main_window, "ui_aliases") and component_name in self.main_window.ui_aliases:
            return self.main_window.ui_aliases[component_name] is not None
        
        return False

    @handle_errors
    def apply_api_settings(self):
        """应用API设置"""
        try:
            settings = {
                "type": self.get_recognition_mode(),
                "options": self.get_api_options()
            }
            return self.audio_processor.apply_settings("api", settings)
        except Exception as e:
            logger.error(f"应用API设置失败: {e}")
            self.error_signal.emit("设置错误", str(e))
            return False

    def get_available_voices(self):
        """获取可用的语音列表"""
        try:
            if hasattr(self, 'audio_processor') and self.audio_processor:
                voices = self.audio_processor.get_all_voices()
                if voices:
                    # 根据当前语音类型返回相应的语音列表
                    voice_type = "system"
                    if self.has_ui_component("ai_voice_btn") and self.main_window.ai_voice_btn.isChecked():
                        voice_type = "ai"
                    elif self.has_ui_component("chat_tts_btn") and self.main_window.chat_tts_btn.isChecked():
                        voice_type = "chat_tts"
                    
                    return voices.get(voice_type, [])
                
            return ["系统默认语音"]
        except Exception as e:
            logger.error(f"获取可用语音失败: {e}")
            return ["获取语音失败"]

    def get_vosk_models(self):
        """获取可用的Vosk模型列表"""
        try:
            if hasattr(self, 'audio_processor') and self.audio_processor:
                return self.audio_processor.get_available_models("vosk")
            return ["未找到模型，请下载"]
        except Exception as e:
            logger.error(f"获取Vosk模型失败: {e}")
            return ["获取模型列表失败"]

    def on_voice_type_changed(self, voice_type):
        """当语音类型变化时调用"""
        try:
            logger.info(f"正在切换语音类型到: {voice_type}")
            
            if not hasattr(self, 'audio_processor'):
                if not self.check_initialization():
                    raise Exception("核心组件未初始化")
            
            # 更新音频处理器的语音类型
            if not self.audio_processor.set_voice_type(voice_type):
                raise Exception("设置语音类型失败")
            
            # 更新UI状态
            if self.has_ui_component("voice_combo"):
                self.main_window.voice_combo.clear()
                voices = self.audio_processor.get_all_voices().get(voice_type, [])
                
                # 将字典类型的语音信息转换为字符串
                voice_items = []
                for voice in voices:
                    if isinstance(voice, dict):
                        # 构建显示文本
                        display_text = voice.get('name', '')
                        if voice.get('gender'):
                            display_text += f" ({voice['gender']})"
                        if voice.get('languages'):
                            display_text += f" - {', '.join(voice['languages'])}"
                        voice_items.append(display_text)
                    else:
                        voice_items.append(str(voice))
                
                if voice_items:
                    self.main_window.voice_combo.addItems(voice_items)
                    self.main_window.voice_combo.setCurrentIndex(0)
                    logger.info(f"已加载 {len(voice_items)} 个{voice_type}语音")
                else:
                    logger.warning(f"未找到可用的{voice_type}语音")
            
            # 保存当前选择的语音类型到配置
            self.config["voice_type"] = voice_type
            save_config(self.config)
            
            # 更新状态
            self.status_signal.emit(f"已切换到{voice_type}语音")
            logger.info(f"已切换到语音类型: {voice_type}")
            
        except Exception as e:
            logger.error(f"切换语音类型失败: {e}")
            self.error_signal.emit("切换失败", f"无法切换到{voice_type}语音: {str(e)}")

    def update_voice_list(self):
        """更新语音列表"""
        try:
            if not self.has_ui_component("voice_combo"):
                return
            
            # 获取当前语音类型
            tts_type = "system"
            if self.has_ui_component("ai_voice_btn") and self.main_window.ai_voice_btn.isChecked():
                tts_type = "ai"
            elif self.has_ui_component("chat_tts_btn") and self.main_window.chat_tts_btn.isChecked():
                tts_type = "chat_tts"
            
            # 保存当前选中的语音
            current_voice = self.main_window.voice_combo.currentText()
            
            # 清空并重新加载语音列表
            self.main_window.voice_combo.clear()
            
            # 获取当前类型的可用语音
            voices = self.get_available_voices()
            if voices:
                self.main_window.voice_combo.addItems(voices)
                
                # 尝试恢复之前选择的语音
                if current_voice:
                    index = self.main_window.voice_combo.findText(current_voice)
                    if index >= 0:
                        self.main_window.voice_combo.setCurrentIndex(index)
                    
            self.status_signal.emit(f"已获取{len(voices)}个语音")
        except Exception as e:
            logger.error(f"更新语音列表失败: {e}")

    def download_vosk_model(self, model_name=None):
        """下载指定的Vosk模型
        
        此方法现在是一个代理方法，它首先检查模型名称，然后将下载请求转交给主窗口的
        download_vosk_model_directly方法处理，避免维护两套下载逻辑。
        
        Args:
            model_name: 要下载的模型名称，如"vosk-model-small-cn-0.22"
        
        Returns:
            bool: 下载是否成功启动
        """
        try:
            if not model_name:
                # 获取当前选择的模型
                if self.has_ui_component("vosk_model_combo"):
                    # 从UI中获取的值可能包含[已下载]标记，需要清理
                    current_text = self.main_window.vosk_model_combo.currentText()
                    if "[已下载]" in current_text:
                        model_name = current_text.split(" [已下载]")[0]
                    elif "[可下载]" in current_text:
                        model_name = current_text.split(" [可下载]")[0]
                    else:
                        model_name = current_text
                else:
                    model_name = "vosk-model-small-cn-0.22"  # 默认中文小模型
            
            # 检查main_window是否有download_vosk_model_directly方法
            if hasattr(self.main_window, 'download_vosk_model_directly'):
                # 使用主窗口的方法处理下载
                return self.main_window.download_vosk_model_directly(model_name)
            else:
                # 如果主窗口没有下载方法，显示错误
                self.status_signal.emit(f"下载功能不可用")
                self.error_signal.emit("功能不可用", "Vosk模型下载功能未实现")
                return False
        except Exception as e:
            logger.error(f"启动模型下载失败: {e}")
            self.error_signal.emit("下载失败", f"无法启动下载: {str(e)}")
            return False

    @handle_errors
    def download_whisper_model(self, model_size):
        """下载 Whisper 模型"""
        return self.audio_processor.check_and_download_whisper(model_size)

    @handle_errors
    def refresh_models(self, model_type):
        """刷新模型列表"""
        if model_type == "vosk":
            return self.audio_processor.get_available_vosk_models()
        elif model_type == "whisper":
            return self.audio_processor.get_available_whisper_models()
        return []

    # Helper methods for getting UI values
    def get_recognition_mode(self):
        """获取当前选择的识别模式"""
        if self.has_ui_component("recognition_cloud_btn") and self.main_window.recognition_cloud_btn.isChecked():
            return "cloud"
        elif self.has_ui_component("recognition_whisper_btn") and self.main_window.recognition_whisper_btn.isChecked():
            return "whisper"
        return "vosk"

    def get_listen_timeout(self):
        """获取监听超时时间"""
        if self.has_ui_component("listen_timeout"):
            return self.main_window.listen_timeout.value()
        return 5

    def get_energy_threshold(self):
        """获取能量阈值"""
        if self.has_ui_component("energy_threshold"):
            return self.main_window.energy_threshold.value()
        return 300

    def get_pause_threshold(self):
        """获取暂停阈值"""
        if self.has_ui_component("pause_threshold"):
            return self.main_window.pause_threshold.value()
        return 0.8

    def get_voice_rate(self):
        """获取语音速率"""
        if self.has_ui_component("voice_speed_spin"):
            return self.main_window.voice_speed_spin.value()
        return 180

    def get_voice_volume(self):
        """获取语音音量"""
        if self.has_ui_component("voice_volume_spin"):
            return self.main_window.voice_volume_spin.value() / 100.0
        return 0.9

    def get_selected_voice(self):
        """获取选择的语音"""
        if self.has_ui_component("voice_combo"):
            display_text = self.main_window.voice_combo.currentText()
            
            # 从显示文本中提取语音ID
            voices = self.audio_processor.get_all_voices().get(self.config.get("voice_type", "system"), [])
            for voice in voices:
                if isinstance(voice, dict):
                    # 构建显示文本进行比较
                    voice_text = voice.get('name', '')
                    if voice.get('gender'):
                        voice_text += f" ({voice['gender']})"
                    if voice.get('languages'):
                        voice_text += f" - {', '.join(voice['languages'])}"
                    
                    if voice_text == display_text:
                        return voice.get('id')  # 返回语音ID
            
            # 如果没有找到匹配的语音ID，返回显示文本
            return display_text
        return None

    def get_api_options(self):
        """获取API选项"""
        options = {}
        if self.get_recognition_mode() == "whisper":
            if self.has_ui_component("whisper_model_size_combo"):
                options["model_size"] = self.main_window.whisper_model_size_combo.currentText()
            if self.has_ui_component("whisper_quality_combo"):
                options["quality"] = self.main_window.whisper_quality_combo.currentText()
            if self.has_ui_component("whisper_language_combo"):
                options["language"] = self.main_window.whisper_language_combo.currentText()
        return options