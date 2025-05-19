#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import threading
import time
import numpy as np
import speech_recognition as sr
import pygame
import simpleaudio as sa
from logger import logger
from chat_tts_client import ChatTTSClient
import uuid
from utils import handle_errors

class AudioProcessor:
    
    def __init__(self, voice_rate=180, voice_volume=0.9, language="zh-CN", 
             recognition_mode="cloud", listen_timeout=5, energy_threshold=300, 
             pause_threshold=0.8, use_ai_voice=True, ai_voice=None, system_voice=None,
             chat_tts_path=None):
        """
        初始化音频处理器
    
        Args:
            voice_rate: 语音速率
            voice_volume: 语音音量
            language: 语言代码
            recognition_mode: 语音识别模式 ("cloud", "vosk", "whisper")
            listen_timeout: 语音识别超时时间
            energy_threshold: 能量阈值
            pause_threshold: 停顿阈值
            use_ai_voice: 是否使用AI语音
            ai_voice: AI语音名称
            system_voice: 系统语音名称
            chat_tts_path: ChatTTS安装路径
        """
        self.voice_rate = voice_rate
        self.voice_volume = voice_volume
        self.language = language
        self.recognition_mode = recognition_mode
    
        # 语音识别设置
        self.recognizer = sr.Recognizer()
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self.listen_timeout = listen_timeout
        self.is_listening = False
        
        # 语音合成设置
        self.use_ai_voice = use_ai_voice
        self.ai_voice = ai_voice if ai_voice else "zh-CN-XiaoxiaoNeural"
        self.system_voice = system_voice
        
        # 本地语音识别组件
        self.vosk_model = None
        self.whisper_model = None
        
        # 初始化语音合成引擎
        self.engine = None
        try:
            self._init_tts_engine()
        except Exception as e:
            logger.error(f"初始化TTS引擎失败: {e}")
        
        # 初始化pygame混音器(用于播放音频)
        try:
            self._init_mixer()
        except Exception as e:
            logger.error(f"初始化混音器失败: {e}")

        # 添加ChatTTS支持
        self.chat_tts_client = None
        self.chat_tts_path = chat_tts_path
        self.voice_type = "ai" if use_ai_voice else "system"  # 增加区分voice_type

        # 如果选择ChatTTS，初始化客户端
        if self.voice_type == "chat_tts":
            self.init_chat_tts()

        # 检查麦克风可用性
        self.microphone_available = self._check_microphone_available()
        if not self.microphone_available:
            logger.warning("未检测到可用麦克风，语音识别功能将不可用")

        # 添加互斥锁
        self.tts_lock = threading.Lock()

    def _check_microphone_available(self):
        """检查是否有可用的麦克风"""
        try:
            mics = sr.Microphone.list_microphone_names()
            return len(mics) > 0
        except Exception as e:
            logger.error(f"检查麦克风失败: {e}")
            return False

    @handle_errors
    def init_local_recognition(self):
        """初始化本地语音识别引擎"""
        if self.recognition_mode == "vosk":
            self._init_vosk_model()
        elif self.recognition_mode == "whisper":
            self._init_whisper_model()

    def _init_vosk_model(self):
        """初始化Vosk模型"""
        try:
            import vosk
            model_path = os.path.join(os.path.expanduser("~"), ".ai_voice_assistant", "vosk_model")
            if not os.path.exists(model_path):
                logger.warning("Vosk模型不存在，请下载模型文件")
                return
            
            self.vosk_model = vosk.Model(model_path)
            logger.info("Vosk模型加载成功")
        except ImportError:
            logger.error("未安装Vosk库，无法使用本地语音识别")
        except Exception as e:
            logger.error(f"初始化Vosk失败: {e}")

    def _init_whisper_model(self):
        """初始化Whisper模型"""
        try:
            import whisper
            model_size = "base"
            self.whisper_model = whisper.load_model(model_size)
            logger.info(f"Whisper {model_size}模型加载成功")
        except ImportError:
            logger.error("未安装OpenAI Whisper库，无法使用本地语音识别")
        except Exception as e:
            logger.error(f"初始化Whisper失败: {e}")

    def set_recognition_mode(self, mode):
       """设置语音识别模式"""
       if mode in ["cloud", "vosk", "whisper"]:
           old_mode = self.recognition_mode
           self.recognition_mode = mode
        
        # 如果切换到本地模式，确保模型已初始化
           if mode != "cloud" and mode != old_mode:
               self.init_local_recognition()
        
           logger.info(f"语音识别模式已切换: {mode}")
           return True
       return False
    

    @handle_errors
    def recognize_speech(self, callback=None):
        """执行语音识别"""
        if not self._check_recognition_prerequisites():
            return None

        try:
            with sr.Microphone() as source:
                audio = self._capture_audio(source)
                if not audio or not self.is_listening:
                    return None
                
                text = self._process_audio(audio)
                
                if text:
                    logger.info(f"识别结果: {text}")
                    if callback:
                        callback({"success": True, "text": text})
                    return text
                else:
                    logger.info("没有识别到任何内容")
                    if callback:
                        callback({"success": False, "error": "未识别到语音内容"})
                    return None
                
        except Exception as e:
            error_msg = f"语音识别错误: {e}"
            logger.error(error_msg)
            if callback:
                callback({"success": False, "error": error_msg})
            return None

    def _check_recognition_prerequisites(self):
        """检查语音识别前提条件"""
        if not self.microphone_available:
            logger.warning("麦克风不可用，无法进行语音识别")
            return False
        
        if self.recognition_mode in ["vosk", "whisper"]:
            if not self._ensure_model_initialized():
                return False
        
        return True

    def _capture_audio(self, source):
        """捕获音频输入"""
        try:
            logger.info("调整环境噪音...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            
            self.play_beep()
            
            logger.info(f"开始聆听，等待时间 {self.listen_timeout} 秒...")
            self.is_listening = True
            
            return self.recognizer.listen(
                source, 
                timeout=self.listen_timeout,
                phrase_time_limit=10
            )
        except Exception as e:
            logger.error(f"捕获音频失败: {e}")
            return None

    def _process_audio(self, audio):
        """处理音频并返回识别结果"""
        try:
            if self.recognition_mode == "cloud":
                return self._recognize_with_cloud(audio)
            elif self.recognition_mode == "vosk":
                return self._recognize_with_vosk(audio)
            elif self.recognition_mode == "whisper":
                return self._recognize_with_whisper(audio)
            else:
                logger.error(f"未知的识别模式: {self.recognition_mode}")
                return None
        except Exception as e:
            logger.error(f"音频处理失败: {e}")
            return None

    def _recognize_with_cloud(self, audio):
        """使用云服务进行语音识别"""
        try:
            return self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            logger.warning("云服务无法识别语音内容")
            return None
        except sr.RequestError as e:
            logger.error(f"无法连接到语音识别服务: {e}")
            return None
        
    def _recognize_with_vosk(self, audio):
        """使用Vosk进行本地语音识别"""
        if not self.vosk_model:
            logger.error("Vosk模型未初始化")
            return None
    
        try:
           import vosk
           import json
        
        # 获取音频数据
           wav_data = audio.get_wav_data()
        
        # 创建Vosk识别器
           rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
        
        # 送入音频数据
           rec.AcceptWaveform(wav_data)
           result = json.loads(rec.FinalResult())
        
        # 提取识别文本
           return result.get("text", "")
        except Exception as e:
           logger.error(f"Vosk识别失败: {e}")
           return None
        
    def _recognize_with_whisper(self, audio):
        """使用OpenAI Whisper进行本地语音识别"""
        if not self.whisper_model:
           logger.error("Whisper模型未初始化")
           return None
    
        try:
           import tempfile
           import os
        
        # 保存音频到临时文件
           with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
               temp_filename = temp_audio.name
               temp_audio.write(audio.get_wav_data())
        
        # 使用whisper进行识别
           result = self.whisper_model.transcribe(temp_filename)
        
        # 删除临时文件
           os.unlink(temp_filename)
        
           return result["text"]
        except Exception as e:
           logger.error(f"Whisper识别失败: {e}")
           return None

    def set_voice(self, voice_id):
        """设置语音"""
        if not voice_id:
            return False
        
        try:
            if self.use_ai_voice:
                self.ai_voice = voice_id
                logger.info(f"已设置AI语音: {voice_id}")
                return True
            elif self.engine:
                # 检查voice_id是否是完整的语音信息
                if isinstance(voice_id, dict):
                    voice_id = voice_id.get('id', voice_id)
                self.system_voice = voice_id
                self.engine.setProperty('voice', voice_id)
                logger.info(f"已设置系统语音: {voice_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"设置语音失败: {e}")
            return False
    
    def get_available_ai_voices(self):
        """获取可用的AI语音列表"""
        try:
            return [
                {
                    'id': 'zh-CN-XiaoxiaoNeural',
                    'name': '晓晓',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-YunxiNeural',
                    'name': '云希',
                    'gender': '男',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-YunyangNeural',
                    'name': '云扬',
                    'gender': '男',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-XiaohanNeural',
                    'name': '晓涵',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-XiaomoNeural',
                    'name': '晓墨',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-XiaoxuanNeural',
                    'name': '晓萱',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                                {
                    'id': 'zh-CN-XiaorouNeural',
                    'name': '晓柔',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-XiaoruiNeural',
                    'name': '晓睿',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'en-US-JennyNeural',
                    'name': 'Jenny',
                    'gender': '女',
                    'languages': ['英语'],
                    'type': 'ai'
                },
                {
                    'id': 'en-US-GuyNeural',
                    'name': 'Guy',
                    'gender': '男',
                    'languages': ['英语'],
                    'type': 'ai'
                }
            ]
        except Exception as e:
            logger.error(f"获取AI语音列表失败: {e}")
            return []
    
    def get_dynamic_ai_voices(self):
        """动态获取AI语音列表"""
        try:
            # 先返回静态列表，避免频繁网络请求
            return self.get_available_ai_voices()
            
            # 真正动态获取的代码可以在此添加
            # import edge_tts
            # voices = await edge_tts.list_voices()
            # return [{'id': v.get('ShortName'), 'name': v.get('FriendlyName'), ...}]
        except Exception as e:
            logger.error(f"动态获取AI语音列表失败: {e}")
            return self.get_available_ai_voices()  # 回退到静态列表
    
    @handle_errors
    def get_available_voices(self):
        """获取当前可用的语音列表"""
        voices = []
        
        # 获取AI语音列表或系统语音列表
        if self.use_ai_voice:
            return self.get_dynamic_ai_voices()
        else:
            # 获取系统语音
            if self.engine:
                system_voices = self.engine.getProperty('voices')
                for voice in system_voices:
                    # 判断语言
                    language = []
                    if 'zh' in voice.id.lower() or 'chinese' in voice.name.lower():
                        language = ['中文']
                    elif 'en' in voice.id.lower() or 'english' in voice.name.lower():
                        language = ['英语']
                    else:
                        language = ['其他']
                    
                    # 判断性别
                    gender = '未知'
                    if 'female' in voice.name.lower() or '女' in voice.name:
                        gender = '女'
                    elif 'male' in voice.name.lower() or '男' in voice.name:
                        gender = '男'
                    
                    voices.append({
                        'id': voice.id,
                        'name': voice.name.split('Voice')[0].strip(),
                        'gender': gender,
                        'languages': language,
                        'type': 'system'
                    })
                
                if not voices:
                    logger.warning("未找到系统语音，将使用AI语音")
                    self.use_ai_voice = True
                    return self.get_dynamic_ai_voices()
                
                return voices
            else:
                # 系统语音引擎初始化失败，使用AI语音
                logger.warning("系统语音引擎不可用，将使用AI语音")
                self.use_ai_voice = True
                return self.get_dynamic_ai_voices()
    
    def process_text(self, text):
        """处理文本以改善语音效果"""
        if not text:
            return text
        
        # 替换常见缩写和符号，使其更适合语音播报
        replacements = {
            '&': '和',
            '@': '在',
            'AI': 'A I',
            'URL': 'U R L',
            'HTTP': 'H T T P',
            'HTTPS': 'H T T P S',
            'API': 'A P I',
            '...': '，',
            '\n': '，',  # 换行符替换为停顿
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # 处理重复标点符号
        import re
        text = re.sub(r'([,.!?;:，。！？；：])\1+', r'\1', text)
        
        # 添加适当的停顿
        text = re.sub(r'([,.!?;:，。！？；：])', r'\1 ', text)
        
        return text
    
    @handle_errors
    def text_to_speech(self, text, play_audio=True):
        """统一的文本转语音接口"""
        if not text:
            return False
        
        with self.tts_lock:
            try:
                # 根据voice_type选择合适的TTS方法
                if self.voice_type == "chat_tts":
                    return self._synthesize_chat_tts(text, play_audio)
                elif self.voice_type == "ai":
                    return self._synthesize_azure(text, play_audio)
                elif self.voice_type == "system":
                    return self._synthesize_system(text, play_audio)
                else:
                    logger.error(f"未知的语音类型: {self.voice_type}")
                    return False
            except Exception as e:
                logger.error(f"语音合成失败: {e}")
                return False
    
    def init_chat_tts(self):
        """初始化ChatTTS客户端"""
        if self.chat_tts_client is None:
            try:
                self.chat_tts_client = ChatTTSClient(self.chat_tts_path)
                # 异步初始化以避免阻塞UI
                threading.Thread(target=self.chat_tts_client.initialize, 
                                daemon=True).start()
            except Exception as e:
                logger.error(f"初始化ChatTTS客户端失败: {e}")
                
    def get_voice_list(self):
        """获取可用的语音列表"""
        if self.voice_type == "chat_tts":
            if self.chat_tts_client is None:
                self.init_chat_tts()
            return self.chat_tts_client.get_voices() if self.chat_tts_client else ["ChatTTS默认语音"]
        elif self.voice_type == "ai" or self.use_ai_voice:
            return self.get_online_voices()
        else:
            return self.get_system_voices()
            
    def set_chat_tts_path(self, path):
        """设置ChatTTS路径"""
        self.chat_tts_path = path
        if self.chat_tts_client:
            self.chat_tts_client.set_path(path)
        else:
            self.init_chat_tts()
    
    def set_listen_timeout(self, timeout):
        """设置语音识别超时时间"""
        if timeout > 0:
            self.listen_timeout = timeout
            return True
        return False
    
    def set_energy_threshold(self, threshold):
        """设置语音识别能量阈值"""
        if threshold > 0:
            self.energy_threshold = threshold
            return True
        return False
    
    def set_pause_threshold(self, threshold):
        """设置语音识别停顿阈值"""
        if threshold > 0:
            self.pause_threshold = threshold
            return True
        return False
    
    @handle_errors
    def stop_listening(self):
        """停止语音识别"""
        self.is_listening = False
        # 如果使用pygame播放，确保停止播放
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        return True
    
    def play_beep(self):
        """播放提示音"""
        try:
            # 生成简单的提示音
            sample_rate = 44100
            duration = 0.2
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # 生成一个简单的提示音（440Hz正弦波）
            beep_tone = np.sin(2 * np.pi * 440 * t) * 0.3
            
            # 将numpy数组转换为音频格式
            audio = np.int16(beep_tone * 32767)
            
            # 使用simpleaudio播放
            wave_obj = sa.WaveObject(audio, 1, 2, sample_rate)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            
            return True
        except Exception as e:
            logger.error(f"播放提示音失败: {e}")
            return False
        
    def download_vosk_model(self, model_id):
        """下载Vosk模型"""
        try:
            import os
            import requests
            import zipfile
            import tempfile
            import shutil
            
            # 创建模型目录
            models_dir = os.path.join(os.path.expanduser("~"), ".cache", "vosk")
            os.makedirs(models_dir, exist_ok=True)
            
            # 下载地址
            download_url = f"https://alphacephei.com/vosk/models/{model_id}.zip"
            
            # 使用临时文件下载
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
                # 下载模型
                logger.info(f"开始从 {download_url} 下载模型")
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                # 获取总大小以显示进度
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # 写入临时文件
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        # 每10%更新一次进度
                        if total_size > 0 and downloaded % (total_size // 10) < 8192:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"下载进度: {percent:.1f}%")
            
            # 解压模型
            target_dir = os.path.join(models_dir, model_id.split('-')[-1])
            os.makedirs(target_dir, exist_ok=True)
            
            logger.info(f"解压模型到 {target_dir}")
            with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                zip_ref.extractall(models_dir)
            
            # 删除临时文件
            os.unlink(temp_file.name)
            
            logger.info(f"Vosk模型 {model_id} Is下载完成")
            return True
            
        except Exception as e:
            logger.error(f"下载Vosk模型失败: {e}")
            return False

    def check_and_download_whisper(self, model_size="base"):
        """检查并下载Whisper模型"""
        try:
            import whisper
        
        # 检查模型是否已下载
            models_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
            model_path = os.path.join(models_dir, f"{model_size}.pt")
        
            if os.path.exists(model_path):
               logger.info(f"Whisper {model_size}模型已存在")
               return True
            
        # 下载模型
            logger.info(f"开始下载Whisper {model_size}模型")
            self.whisper_model = whisper.load_model(model_size)
            logger.info(f"Whisper {model_size}模型下载完成")
            return True
        
        except Exception as e:
            logger.error(f"下载Whisper模型失败: {e}")
            return False
        
    def set_whisper_options(self, options):
        """设置Whisper模型参数"""
        try:
            self.whisper_options = options
            # 如果已经初始化了模型，可以考虑重新加载
            if self.recognition_mode == "whisper" and self.whisper_model:
                logger.info("应用Whisper新参数")
            return True
        except Exception as e:
            logger.error(f"设置Whisper参数失败: {e}")
            return False

    def set_vosk_options(self, options):
        """设置Vosk参数"""
        try:
            self.vosk_options = options
            # 如果需要重新初始化Vosk模型可以在这里添加代码
            return True
        except Exception as e:
            logger.error(f"设置Vosk参数失败: {e}")
            return False

    def get_online_voices(self):
        """
        获取在线AI语音列表
        
        Returns:
            list: 可用的在线语音列表
        """
        try:
            # 获取Azure TTS语音列表
            voices = [
                "zh-CN-XiaoxiaoNeural",  # 晓晓，女声
                "zh-CN-YunxiNeural",     # 云希，男声
                "zh-CN-YunjianNeural",   # 云健，男声
                "zh-CN-XiaoyiNeural",    # 晓依，女声
                "zh-CN-YunyangNeural",   # 云扬，男声
                "zh-CN-XiaohanNeural",   # 晓涵，女声
                "zh-CN-XiaomoNeural",    # 晓墨，女声
                "zh-CN-XiaoxuanNeural",  # 晓璇，女声
                "zh-CN-YunfengNeural",   # 云枫，男声
                "zh-CN-XiaoruiNeural",   # 晓睿，女声
                "en-US-JennyNeural",     # 英语-珍妮，女声
                "en-US-GuyNeural",       # 英语-盖伊，男声
                "ja-JP-NanamiNeural",    # 日语-七海，女声
                "ko-KR-SunHiNeural",     # 韩语-善熙，女声
            ]
            logger.info(f"获取到 {len(voices)} 个在线语音")
            return voices
        except Exception as e:
            logger.error(f"获取在线语音列表失败: {e}")
            return []

    def get_system_voices(self):
        """
        获取系统语音列表
        
        Returns:
            list: 系统语音列表
        """
        try:
            if not self.engine:
                self._init_tts_engine()
            
            if not self.engine:
                logger.error("语音引擎未初始化，无法获取系统语音")
                return []
            
            voices = []
            for voice in self.engine.getProperty('voices'):
                voices.append(voice.id)
            
            logger.info(f"获取到 {len(voices)} 个系统语音")
            return voices
        except Exception as e:
            logger.error(f"获取系统语音列表失败: {e}")
            return []
        
    @handle_errors
    def get_all_voices(self):
        """获取所有可用语音列表，包括AI语音、系统语音和ChatTTS语音"""
        all_voices = {
            "ai": self._get_ai_voices(),
            "system": self._get_system_voices(),
            "chat_tts": self._get_chat_tts_voices()
        }
        
        total_voices = sum(len(voices) for voices in all_voices.values())
        logger.info(f"获取到总计 {total_voices} 个语音")
        return all_voices

    def _get_ai_voices(self):
        """获取AI语音列表"""
        try:
            voices = [
                {
                    'id': 'zh-CN-XiaoxiaoNeural',
                    'name': '晓晓',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-YunxiNeural',
                    'name': '云希',
                    'gender': '男',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-YunyangNeural',
                    'name': '云扬',
                    'gender': '男',
                    'languages': ['中文'],
                    'type': 'ai'
                },
                {
                    'id': 'zh-CN-XiaohanNeural',
                    'name': '晓涵',
                    'gender': '女',
                    'languages': ['中文'],
                    'type': 'ai'
                }
            ]
            logger.info(f"获取到 {len(voices)} 个AI语音")
            return voices
        except Exception as e:
            logger.error(f"获取AI语音列表失败: {e}")
            return []

    def _get_system_voices(self):
        """获取系统语音列表"""
        try:
            if not self.engine:
                self._init_tts_engine()
            
            if not self.engine:
                return []
            
            voices = []
            for voice in self.engine.getProperty('voices'):
                language = []
                if 'zh' in voice.id.lower() or 'chinese' in voice.name.lower():
                    language = ['中文']
                elif 'en' in voice.id.lower() or 'english' in voice.name.lower():
                    language = ['英语']
                else:
                    language = ['其他']
                
                gender = '未知'
                if 'female' in voice.name.lower() or '女' in voice.name:
                    gender = '女'
                elif 'male' in voice.name.lower() or '男' in voice.name:
                    gender = '男'
                
                voices.append({
                    'id': voice.id,
                    'name': voice.name.split('Voice')[0].strip(),
                    'gender': gender,
                    'languages': language,
                    'type': 'system'
                })
            
            logger.info(f"获取到 {len(voices)} 个系统语音")
            return voices
        except Exception as e:
            logger.error(f"获取系统语音列表失败: {e}")
            return []

    def _get_chat_tts_voices(self):
        """获取ChatTTS语音列表"""
        try:
            if self.chat_tts_client and hasattr(self.chat_tts_client, 'get_voices'):
                raw_voices = self.chat_tts_client.get_voices()
                voices = []
                for voice in raw_voices:
                    if isinstance(voice, dict):
                        voices.append(voice)
                    else:
                        voices.append({
                            'id': str(voice),
                            'name': str(voice),
                            'gender': '未知',
                            'languages': ['未知'],
                            'type': 'chat_tts'
                        })
                logger.info(f"获取到 {len(voices)} 个ChatTTS语音")
                return voices
            return []
        except Exception as e:
            logger.error(f"获取ChatTTS语音列表失败: {e}")
            return []

    def get_models_directory(self, model_type):
        """获取模型目录路径
        
        Args:
            model_type: 模型类型 ("vosk" 或 "whisper")
        
        Returns:
            str: 模型目录的完整路径
        """
        try:
            base_dir = os.path.join(os.path.expanduser("~"), ".cache")
            if model_type == "vosk":
                return os.path.join(base_dir, "vosk")
            elif model_type == "whisper":
                return os.path.join(base_dir, "whisper")
            else:
                logger.error(f"不支持的模型类型: {model_type}")
                return None
        except Exception as e:
            logger.error(f"获取模型目录失败: {e}")
            return None

    def get_available_models(self, model_type):
        """获取可用的语音识别模型列表
        
        Args:
            model_type: 模型类型 ("vosk" 或 "whisper")
        
        Returns:
            list: 可用模型列表
        """
        try:
            models_dir = self.get_models_directory(model_type)
            if not models_dir or not os.path.exists(models_dir):
                return []
            
            models = []
            if model_type == "vosk":
                # 获取已下载的模型
                downloaded = [d for d in os.listdir(models_dir) 
                            if os.path.isdir(os.path.join(models_dir, d))]
                models.extend([f"{m} [已下载]" for m in downloaded])
                
                # 添加可下载的标准模型
                available = [
                    "vosk-model-small-cn-0.22",
                    "vosk-model-cn-0.22",
                    "vosk-model-small-en-us-0.15",
                    "vosk-model-en-us-0.22",
                    "vosk-model-small-fr-0.22",
                    "vosk-model-fr-0.22",
                    "vosk-model-small-de-0.15",
                    "vosk-model-de-0.21",
                    "vosk-model-small-ru-0.22",
                    "vosk-model-ru-0.22",
                    "vosk-model-ja-0.22"
                ]
                
                for model in available:
                    if not any(model in m for m in models):
                        models.append(f"{model} [可下载]")
                    
            elif model_type == "whisper":
                # 获取所有.pt或.bin文件
                models = [f for f in os.listdir(models_dir) 
                         if f.endswith(('.pt', '.bin'))]
                
                # 添加标准大小选项
                standard_sizes = ["tiny", "base", "small", "medium", "large"]
                for size in standard_sizes:
                    if not any(size in m for m in models):
                        models.append(f"{size} [可下载]")
            
            logger.info(f"找到 {len(models)} 个 {model_type} 模型")
            return models
            
        except Exception as e:
            logger.error(f"获取{model_type}模型列表失败: {e}")
            return []

    @handle_errors
    def download_model(self, model_type, model_name=None):
        """下载语音识别模型"""
        if model_type == "vosk":
            return self._download_vosk_model(model_name)
        elif model_type == "whisper":
            return self._download_whisper_model(model_name or "base")
        else:
            logger.error(f"不支持的模型类型: {model_type}")
            return False

    def _download_vosk_model(self, model_id):
        """下载Vosk模型"""
        try:
            import requests
            import zipfile
            
            models_dir = os.path.join(os.path.expanduser("~"), ".cache", "vosk")
            os.makedirs(models_dir, exist_ok=True)
            
            download_url = f"https://alphacephei.com/vosk/models/{model_id}.zip"
            
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
                logger.info(f"开始从 {download_url} 下载模型")
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and downloaded % (total_size // 10) < 8192:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"下载进度: {percent:.1f}%")
            
            target_dir = os.path.join(models_dir, model_id.split('-')[-1])
            os.makedirs(target_dir, exist_ok=True)
            
            logger.info(f"解压模型到 {target_dir}")
            with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                zip_ref.extractall(models_dir)
            
            os.unlink(temp_file.name)
            logger.info(f"Vosk模型 {model_id} 下载完成")
            return True
            
        except Exception as e:
            logger.error(f"下载Vosk模型失败: {e}")
            return False

    def _download_whisper_model(self, model_size):
        """下载Whisper模型"""
        try:
            import whisper
            
            models_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
            model_path = os.path.join(models_dir, f"{model_size}.pt")
            
            if os.path.exists(model_path):
                logger.info(f"Whisper {model_size}模型已存在")
                return True
            
            logger.info(f"开始下载Whisper {model_size}模型")
            self.whisper_model = whisper.load_model(model_size)
            logger.info(f"Whisper {model_size}模型下载完成")
            return True
        
        except Exception as e:
            logger.error(f"下载Whisper模型失败: {e}")
            return False

    def get_available_vosk_models(self):
        """获取可用的Vosk模型列表（保持向后兼容）"""
        return self.get_available_models("vosk")

    def get_available_whisper_models(self):
        """获取可用的Whisper模型列表（保持向后兼容）"""
        return self.get_available_models("whisper")

    @handle_errors
    def start_listening(self, callback=None):
        """开始语音识别"""
        if not self.microphone_available:
            logger.warning("麦克风不可用，无法进行语音识别")
            return False
            
        self.is_listening = True
        
        # 在新线程中启动识别
        def recognition_thread():
            try:
                while self.is_listening:
                    result = self.recognize_speech(callback)
                    if not result or not self.is_listening:
                        break
            except Exception as e:
                logger.error(f"语音识别线程错误: {e}")
                if callback:
                    callback({"success": False, "error": str(e)})
        
        thread = threading.Thread(target=recognition_thread)
        thread.daemon = True
        thread.start()
        return True

    @handle_errors
    def apply_settings(self, settings_type, settings):
        """应用配置设置
        
        Args:
            settings_type: 设置类型 ("recognition", "voice", "api")
            settings: 设置字典
        """
        try:
            logger.info(f"应用{settings_type}设置: {settings}")
            
            if settings_type == "voice":
                # 先设置语音类型
                if "voice_type" in settings:
                    if not self.set_voice_type(settings["voice_type"]):
                        raise Exception(f"设置语音类型失败: {settings['voice_type']}")
                
                # 设置语音属性
                rate = settings.get("rate", 180)
                volume = settings.get("volume", 0.9)
                if not self.set_properties(rate, volume):
                    raise Exception("设置语音属性失败")
                
                # 设置语音
                voice_id = settings.get("voice_id")
                if voice_id and not self.set_voice(voice_id):
                    raise Exception(f"设置语音失败: {voice_id}")
                
                # 如果是ChatTTS，设置路径
                if settings.get("voice_type") == "chat_tts" and "chat_tts_path" in settings:
                    if not self.set_chat_tts_path(settings["chat_tts_path"]):
                        raise Exception("设置ChatTTS路径失败")
                
                logger.info("语音设置应用成功")
                return True
                
            elif settings_type == "recognition":
                # 设置识别模式
                if "mode" in settings:
                    if not self.set_recognition_mode(settings["mode"]):
                        raise Exception(f"设置识别模式失败: {settings['mode']}")
                
                # 设置超时时间
                if "timeout" in settings:
                    if not self.set_listen_timeout(settings["timeout"]):
                        raise Exception("设置超时时间失败")
                
                # 设置能量阈值
                if "energy_threshold" in settings:
                    if not self.set_energy_threshold(settings["energy_threshold"]):
                        raise Exception("设置能量阈值失败")
                
                # 设置暂停阈值
                if "pause_threshold" in settings:
                    if not self.set_pause_threshold(settings["pause_threshold"]):
                        raise Exception("设置暂停阈值失败")
                
                logger.info("语音识别设置应用成功")
                return True
                
            elif settings_type == "api":
                if settings.get("type") == "whisper":
                    return self.set_whisper_options(settings)
                elif settings.get("type") == "vosk":
                    return self.set_vosk_options(settings)
                
            logger.error(f"不支持的设置类型: {settings_type}")
            return False
            
        except Exception as e:
            logger.error(f"应用设置失败: {e}")
            return False

    def set_voice_type(self, voice_type):
        """设置语音类型
        
        Args:
            voice_type: 语音类型 ("system", "ai", "chat_tts")
        
        Returns:
            bool: 是否设置成功
        """
        try:
            logger.info(f"设置语音类型: {voice_type}")
            if voice_type not in ["system", "ai", "chat_tts"]:
                logger.error(f"不支持的语音类型: {voice_type}")
                return False
            
            self.voice_type = voice_type
            self.use_ai_voice = (voice_type == "ai")
            
            # 根据类型初始化相应组件
            if voice_type == "chat_tts" and not self.chat_tts_client:
                self.init_chat_tts()
            elif voice_type == "system" and not self.engine:
                self._init_tts_engine()
            
            logger.info(f"语音类型已切换为: {voice_type}")
            return True
        except Exception as e:
            logger.error(f"设置语音类型失败: {e}")
            return False

    def _synthesize_azure(self, text, play_audio=True):
        """使用Azure TTS服务合成语音"""
        try:
            temp_filename = f"tts_{uuid.uuid4().hex}.mp3"
            temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
            processed_text = self.process_text(text)
            
            import edge_tts
            import asyncio
            
            async def synthesize_speech():
                try:
                    communicate = edge_tts.Communicate(processed_text, self.ai_voice)
                    await communicate.save(temp_file_path)
                    logger.info(f"AI语音已合成到: {temp_file_path}")
                    return True
                except Exception as e:
                    logger.error(f"Edge-TTS语音合成失败: {e}")
                    return False
            
            success = asyncio.run(synthesize_speech())
            
            if not success or not os.path.exists(temp_file_path):
                raise Exception("语音合成失败")
            
            if play_audio:
                self._play_audio(temp_file_path)
                threading.Timer(2.0, lambda: os.remove(temp_file_path) if os.path.exists(temp_file_path) else None).start()
            
            return True
        except Exception as e:
            logger.error(f"Azure语音合成失败: {e}")
            return False

    def _synthesize_system(self, text, play_audio=True):
        """使用系统TTS引擎合成语音"""
        try:
            processed_text = self.process_text(text)
            
            if not self.engine:
                self._init_tts_engine()
            
            if not self.engine:
                return False
            
            if self.system_voice:
                self.engine.setProperty('voice', self.system_voice)
            self.engine.setProperty('rate', self.voice_rate)
            self.engine.setProperty('volume', self.voice_volume)
            
            if play_audio:
                self.engine.say(processed_text)
                self.engine.runAndWait()
            
            return True
        except Exception as e:
            logger.error(f"系统语音合成失败: {e}")
            return False

    def _synthesize_chat_tts(self, text, play_audio=True):
        """使用ChatTTS合成语音"""
        try:
            processed_text = self.process_text(text)
            
            if self.chat_tts_client is None:
                self.init_chat_tts()
            
            retry_count = 0
            while (self.chat_tts_client and not self.chat_tts_client.is_initialized 
                   and retry_count < 3):
                logger.info("等待ChatTTS初始化完成...")
                time.sleep(1)
                retry_count += 1
            
            if self.chat_tts_client and self.chat_tts_client.is_initialized:
                return self.chat_tts_client.text_to_speech(processed_text, play_audio)
            else:
                logger.warning("ChatTTS未初始化或初始化失败，无法合成语音")
                return False
        except Exception as e:
            logger.error(f"ChatTTS语音合成失败: {e}")
            return False

    def _play_audio(self, audio_file):
        """播放音频文件"""
        try:
            # 确保pygame已初始化
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # 停止当前正在播放的音频
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                time.sleep(0.1)  # 短暂延迟确保资源释放
            
            # 加载并播放音频
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # 播放完成，释放资源
            pygame.mixer.music.unload()
            return True
        
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            return False

    def _ensure_model_initialized(self):
        """确保模型已初始化"""
        try:
            if self.recognition_mode == "vosk" and not self.vosk_model:
                logger.info("正在初始化Vosk模型...")
                self.init_local_recognition()
                if not self.vosk_model:
                    logger.error("Vosk模型初始化失败")
                    return False
            elif self.recognition_mode == "whisper" and not self.whisper_model:
                logger.info("正在初始化Whisper模型...")
                self.init_local_recognition()
                if not self.whisper_model:
                    logger.error("Whisper模型初始化失败")
                    return False
            return True
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            return False

    def _init_tts_engine(self):
        """初始化文本转语音引擎"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            if self.engine:
                self.engine.setProperty('rate', self.voice_rate)
                self.engine.setProperty('volume', self.voice_volume)
                
                # 获取可用的系统语音列表
                voices = self.engine.getProperty('voices')
                if voices:
                    # 尝试找到中文语音
                    for voice in voices:
                        if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                            self.system_voice = voice.id
                            break
                    
                    # 如果没有中文语音，使用第一个可用语音
                    if not self.system_voice and voices:
                        self.system_voice = voices[0].id
                    
                    if self.system_voice:
                        self.engine.setProperty('voice', self.system_voice)
                
                logger.info(f"文本转语音引擎初始化成功，使用系统语音: {self.system_voice}")
        except ImportError:
            logger.warning("未安装pyttsx3，系统语音功能将不可用")
            self.engine = None
        except Exception as e:
            logger.error(f"初始化TTS引擎失败: {e}")
            self.engine = None

    def _init_mixer(self):
        """初始化音频混音器"""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            logger.info("音频混音器初始化成功")
        except Exception as e:
            logger.error(f"初始化音频混音器失败: {e}")

    def set_properties(self, voice_rate=None, voice_volume=None):
        """设置语音属性"""
        try:
            modified = False
            
            if voice_rate is not None and voice_rate > 0:
                self.voice_rate = voice_rate
                if self.engine:
                    self.engine.setProperty('rate', voice_rate)
                modified = True
                logger.info(f"设置语音速率: {voice_rate}")
            
            if voice_volume is not None and 0 <= voice_volume <= 1:
                self.voice_volume = voice_volume
                if self.engine:
                    self.engine.setProperty('volume', voice_volume)
                modified = True
                logger.info(f"设置语音音量: {voice_volume}")
            
            return modified
        except Exception as e:
            logger.error(f"设置语音属性失败: {e}")
            return False