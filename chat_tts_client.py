#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import requests
import torch
import numpy as np
import sounddevice as sd
from logger import logger

class ChatTTSClient:
    """ChatTTS客户端封装类"""
    
    def __init__(self, chat_tts_path=None):
        """
        初始化ChatTTS客户端
        
        Args:
            chat_tts_path: ChatTTS安装路径，如果为None则使用默认路径
        """
        self.chat_tts_path = chat_tts_path or r"D:\AI\DUDULab_ChatTTS_Ench_WIN_v3.0"
        self.process = None
        self.is_initialized = False
        self.sample_rate = 24000  # ChatTTS默认采样率
        self.server_url = "http://127.0.0.1:7866"  # ChatTTS服务器地址
        
        logger.info(f"初始化ChatTTS客户端, 路径: {self.chat_tts_path}")
    
    def initialize(self):
        """初始化ChatTTS模型"""
        if self.is_initialized:
            return True
        
        try:
            # 启动ChatTTS启动器
            launcher_path = os.path.join(self.chat_tts_path, "启动器.exe")
            if not os.path.exists(launcher_path):
                logger.error(f"找不到ChatTTS启动器: {launcher_path}")
                return False
                
            logger.info(f"启动ChatTTS: {launcher_path}")
            # 使用子进程启动ChatTTS
            self.process = subprocess.Popen(
                launcher_path, 
                cwd=self.chat_tts_path,
                creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏窗口
            )
            
            # 等待服务器启动
            logger.info("等待ChatTTS服务器启动...")
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # 尝试连接服务器
                    response = requests.get(f"{self.server_url}/ping", timeout=2)
                    if response.status_code == 200:
                        logger.info("ChatTTS服务器已启动")
                        self.is_initialized = True
                        return True
                except:
                    pass
                
                time.sleep(2)  # 等待2秒后重试
            
            logger.error(f"ChatTTS服务器启动超时")
            return False
            
        except Exception as e:
            logger.error(f"初始化ChatTTS失败: {e}")
            return False
    
    def text_to_speech(self, text, play_audio=True):
        """
        将文本转换为语音并可选择直接播放
        
        Args:
            text: 要转换的文本
            play_audio: 是否直接播放音频
            
        Returns:
            音频数据(如果不直接播放)
        """
        if not self.is_initialized and not self.initialize():
            logger.error("ChatTTS未初始化，无法合成语音")
            return None
        
        try:
            logger.info(f"ChatTTS生成语音: {text[:30]}...")
            
            # 通过API请求生成语音
            response = requests.post(
                f"{self.server_url}/tts", 
                json={"text": text, "format": "wav"},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"ChatTTS API请求失败: {response.status_code}")
                return None
                
            # 获取音频数据
            audio_data = np.frombuffer(response.content, dtype=np.float32)
            
            # 如果需要播放
            if play_audio:
                self._play_audio(audio_data)
                return None
            else:
                return audio_data
                
        except Exception as e:
            logger.error(f"ChatTTS生成语音失败: {e}")
            return None
    
    def _play_audio(self, audio_data):
        """播放音频数据"""
        try:
            # 确保数据是float32类型，值范围在-1到1之间
            if isinstance(audio_data, torch.Tensor):
                audio_np = audio_data.cpu().numpy()
            else:
                audio_np = np.array(audio_data)
                
            if audio_np.dtype != np.float32:
                audio_np = audio_np.astype(np.float32)
            
            if np.max(np.abs(audio_np)) > 1.0:
                audio_np = audio_np / np.max(np.abs(audio_np))
            
            # 播放音频
            sd.play(audio_np, self.sample_rate)
            sd.wait()  # 等待音频播放完成
            logger.info("ChatTTS音频播放完成")
            
        except Exception as e:
            logger.error(f"播放ChatTTS音频失败: {e}")
    
    def get_voices(self):
        """
        获取可用的语音列表（目前ChatTTS只有一个语音）
        
        Returns:
            语音名称列表
        """
        return ["ChatTTS默认语音"]
    
    def set_path(self, path):
        """设置ChatTTS路径"""
        self.chat_tts_path = path
        self.is_initialized = False  # 重置初始化状态
        logger.info(f"已设置ChatTTS路径: {path}")
    
    def __del__(self):
        """析构函数，确保进程被终止"""
        if self.process:
            try:
                self.process.terminate()
                logger.info("已终止ChatTTS进程")
            except:
                pass 