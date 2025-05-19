# logger.py
import logging
import os
import sys
import time
from datetime import datetime

class Logger:
    def __init__(self, log_level=logging.INFO):
        # 创建记录器
        self.logger = logging.getLogger('VoiceAssistant')
        self.logger.setLevel(log_level)
        
        # 避免重复处理程序
        if not self.logger.handlers:
            # 创建日志目录
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建文件处理程序
            log_file = os.path.join(log_dir, f'voice_assistant_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            
            # 创建控制台处理程序
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            
            # 创建格式化程序
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理程序到记录器
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)

# 创建全局日志记录器
logger = Logger()