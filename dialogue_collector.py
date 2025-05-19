#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import datetime
from logger import logger

class DialogueEvaluator:
    """对话评估器 - 评估对话的训练价值"""
    
    def __init__(self, criteria):
        self.criteria = criteria
        self.keyword_weights = criteria.get('keyword_weights', {})
        self.topic_weights = criteria.get('topic_weights', {})
        self.min_dialogue_length = criteria.get('min_dialogue_length', 10)
    
    def evaluate(self, dialogue_data):
        """评估对话价值并返回分数和标签"""
        score = 0.0
        tags = []
        
        user_input = dialogue_data['user_input']
        assistant_response = dialogue_data['assistant_response']
        
        # 1. 长度评估 - 更长的、有实质内容的对话通常更有价值
        input_length = len(user_input.split())
        response_length = len(assistant_response.split())
        if input_length >= self.min_dialogue_length:
            score += 0.2
            tags.append('substantial_query')
        if response_length >= self.min_dialogue_length * 2:
            score += 0.3
            tags.append('detailed_response')
        
        # 2. 关键词评估 - 检查是否包含高价值关键词
        for keyword, weight in self.keyword_weights.items():
            if keyword.lower() in user_input.lower() or keyword.lower() in assistant_response.lower():
                score += weight
                tags.append(f'keyword:{keyword}')
        
        # 3. 主题评估 - 根据预设主题评分
        detected_topics = self._detect_topics(user_input, assistant_response)
        for topic in detected_topics:
            if topic in self.topic_weights:
                score += self.topic_weights[topic]
                tags.append(f'topic:{topic}')
        
        # 4. 问答质量评估 - 特定模式的问答更有价值
        if '?' in user_input and len(assistant_response) > len(user_input) * 1.5:
            score += 0.25
            tags.append('informative_qa')
        
        # 5. 个性化指令评估 - 用户的个性化指令特别有价值
        if self._contains_personalization_indicators(user_input):
            score += 0.4
            tags.append('personalization')
        
        # 规范化分数到0-1之间
        score = min(max(score, 0.0), 1.0)
        
        return score, tags
    
    def _detect_topics(self, user_input, assistant_response):
        """检测对话中的主题"""
        combined_text = user_input + " " + assistant_response
        detected_topics = []
        
        # 简化的主题检测
        for topic in self.topic_weights.keys():
            if topic.lower() in combined_text.lower():
                detected_topics.append(topic)
        
        return detected_topics
    
    def _contains_personalization_indicators(self, text):
        """检测文本是否包含个性化指示符"""
        personalization_indicators = [
            "记住我", "我喜欢", "我的偏好", "我希望你", "根据我的", 
            "按照我的习惯", "我通常", "我常常", "我的方式", "自定义"
        ]
        
        for indicator in personalization_indicators:
            if indicator in text:
                return True
        return False


class DatasetManager:
    """数据集管理器 - 管理对话数据的存储和组织"""
    
    def __init__(self, base_path, max_entries=5000):
        self.base_path = base_path
        self.max_entries_per_dataset = max_entries
        self.current_dataset_id = 1
        self.current_entries = 0
        
        # 确保数据目录存在
        self._ensure_data_directory()
        
        # 加载或创建第一个数据集
        self._initialize_current_dataset()
    
    def add_entry(self, dialogue_data):
        """添加一条对话数据到当前数据集"""
        # 检查当前数据集是否已满
        if self.current_entries >= self.max_entries_per_dataset:
            self._create_new_dataset()
        
        # 添加到当前数据集
        filename = self._get_current_dataset_path()
        
        try:
            # 读取现有数据
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 添加新条目
            data['entries'].append(dialogue_data)
            data['metadata']['updated_at'] = self._get_current_timestamp()
            data['metadata']['entry_count'] = len(data['entries'])
            
            # 写回文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.current_entries = len(data['entries'])
            
        except Exception as e:
            logger.error(f"Error adding entry to dataset: {e}")
    
    def get_current_size(self):
        """获取当前数据集大小"""
        return self.current_entries
    
    def get_dataset_stats(self):
        """获取所有数据集的统计信息"""
        stats = {
            'total_datasets': self.current_dataset_id,
            'total_entries': 0,
            'datasets': []
        }
        
        for i in range(1, self.current_dataset_id + 1):
            path = self._get_dataset_path(i)
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    dataset_stat = {
                        'id': i,
                        'entries': len(data['entries']),
                        'created_at': data['metadata']['created_at'],
                        'updated_at': data['metadata']['updated_at']
                    }
                    
                    stats['datasets'].append(dataset_stat)
                    stats['total_entries'] += dataset_stat['entries']
                
            except Exception as e:
                logger.error(f"Error reading dataset {i}: {e}")
        
        return stats
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.base_path, exist_ok=True)
    
    def _initialize_current_dataset(self):
        """初始化当前数据集，如果不存在则创建"""
        # 寻找最高的数据集ID
        import glob
        dataset_files = glob.glob(os.path.join(self.base_path, "dataset_*.json"))
        if dataset_files:
            # 从文件名提取数字，找出最大值
            ids = [int(os.path.basename(f).split('_')[-1].split('.')[0]) for f in dataset_files]
            self.current_dataset_id = max(ids)
            
            # 读取当前条目数
            path = self._get_current_dataset_path()
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.current_entries = len(data['entries'])
            except:
                self._create_new_dataset()
        else:
            self._create_new_dataset()
    
    def _create_new_dataset(self):
        """创建新的数据集"""
        self.current_dataset_id += 1
        self.current_entries = 0
        
        # 创建新的数据集文件
        filename = self._get_current_dataset_path()
        
        data = {
            'metadata': {
                'id': self.current_dataset_id,
                'created_at': self._get_current_timestamp(),
                'updated_at': self._get_current_timestamp(),
                'entry_count': 0
            },
            'entries': []
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_current_dataset_path(self):
        """获取当前数据集的文件路径"""
        return self._get_dataset_path(self.current_dataset_id)
    
    def _get_dataset_path(self, dataset_id):
        """获取指定ID的数据集文件路径"""
        return os.path.join(self.base_path, f"dataset_{dataset_id}.json")
    
    def _get_current_timestamp(self):
        """获取当前时间戳"""
        return datetime.datetime.now().isoformat()


class UIFeedbackManager:
    """UI反馈管理器 - 负责向用户提供可视化反馈"""
    
    def __init__(self):
        self.main_window = None
        self.status_label = None
        self.stats_label = None
        self.is_initialized = False
    
    def initialize(self, main_window):
        """初始化UI组件"""
        from PyQt5.QtWidgets import QLabel, QStatusBar
        from PyQt5.QtCore import Qt
        
        self.main_window = main_window
        
        # 创建一个状态栏，如果不存在
        if not hasattr(main_window, 'statusBar') or main_window.statusBar() is None:
            status_bar = QStatusBar()
            main_window.setStatusBar(status_bar)
        
        # 创建状态标签
        self.status_label = QLabel("数据收集就绪")
        self.status_label.setStyleSheet("margin-right: 10px;")
        main_window.statusBar().addWidget(self.status_label)
        
        # 创建统计标签
        self.stats_label = QLabel("总对话: 0 | 已保存: 0 | 当前数据集: 0/1")
        self.stats_label.setStyleSheet("margin-right: 10px;")
        main_window.statusBar().addWidget(self.stats_label)
        
        self.is_initialized = True
    
    def show_collection_success(self, value_score, tags):
        """显示成功收集的反馈"""
        if not self.is_initialized:
            return
            
        # 如果价值分数很高，显示明显的成功提示
        if value_score > 0.8:
            self._show_notification(f"已保存高价值对话 (评分: {value_score:.2f})", "success")
        else:
            # 否则只是更新状态指示器
            self._update_status_indicator("已收集新对话", "success")
    
    def update_collection_stats(self, stats):
        """更新统计信息显示"""
        if not self.is_initialized or not self.stats_label:
            return
            
        self.stats_label.setText(
            f"总对话: {stats['total_collected']} | "
            f"已保存: {stats['high_value_collected']} | "
            f"当前数据集: {stats['current_dataset_size']}/{stats['datasets_created']}"
        )
    
    def _update_status_indicator(self, text, status):
        """更新状态指示器"""
        if not self.is_initialized or not self.status_label:
            return
            
        self.status_label.setText(text)
        
        # 根据状态设置样式
        if status == "success":
            self.status_label.setStyleSheet("color: green; margin-right: 10px;")
        elif status == "error":
            self.status_label.setStyleSheet("color: red; margin-right: 10px;")
        else:
            self.status_label.setStyleSheet("margin-right: 10px;")
        
        # 2秒后恢复默认状态
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.status_label.setText("数据收集就绪"))
        QTimer.singleShot(2000, lambda: self.status_label.setStyleSheet("margin-right: 10px;"))
    
    def _show_notification(self, text, notification_type="info"):
        """显示通知"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.is_initialized or not self.main_window:
            return
            
        # 简化版只在状态栏显示
        self._update_status_indicator(text, notification_type)
        
        # 对于重要通知，可以考虑弹出消息框
        if notification_type == "success" and "高价值" in text:
            # 仅在主线程中执行，避免Qt警告
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._show_toast(text))
    
    def _show_toast(self, text):
        """显示一个临时消息"""
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
        
        if not self.main_window:
            return
            
        # 创建一个悬浮标签
        toast = QLabel(text, self.main_window)
        toast.setStyleSheet("""
            background-color: rgba(50, 150, 50, 180); 
            color: white; 
            padding: 10px; 
            border-radius: 5px;
            font-size: 14px;
        """)
        toast.setAlignment(Qt.AlignCenter)
        toast.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        toast.setAttribute(Qt.WA_TranslucentBackground)
        toast.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # 计算位置 - 窗口底部居中
        toast.adjustSize()
        main_rect = self.main_window.geometry()
        toast_point = QPoint(
            main_rect.x() + (main_rect.width() - toast.width()) // 2,
            main_rect.y() + main_rect.height() - toast.height() - 50
        )
        toast.move(toast_point)
        
        # 显示并设置自动消失
        toast.show()
        QTimer.singleShot(3000, toast.deleteLater)


class DialogueDataCollector:
    """对话数据收集器 - 负责捕获、评估和存储对话数据"""
    
    def __init__(self, config):
        self.config = config
        self.dataset_manager = DatasetManager(config['dataset_path'])
        self.evaluator = DialogueEvaluator(config['evaluation_criteria'])
        self.ui_feedback = UIFeedbackManager()
        self.active = True
        
        self.stats = {
            'total_collected': 0,
            'high_value_collected': 0,
            'current_dataset_size': 0,
            'datasets_created': 1
        }
    
    def initialize(self, voice_assistant):
        """连接到语音助手以捕获对话"""
        # 确保语音助手有对话回调机制
        if not hasattr(voice_assistant, 'register_dialogue_callback'):
            # 添加回调支持
            voice_assistant.dialogue_callbacks = []
            
            def register_dialogue_callback(callback):
                voice_assistant.dialogue_callbacks.append(callback)
            
            voice_assistant.register_dialogue_callback = register_dialogue_callback
            
            # 修补原始处理方法来调用回调
            original_process = getattr(voice_assistant, 'process_response', None)
            if original_process:
                def patched_process(user_input, response):
                    result = original_process(user_input, response)
                    # 调用所有回调
                    for callback in voice_assistant.dialogue_callbacks:
                        try:
                            callback(user_input, response)
                        except Exception as e:
                            logger.error(f"Error in dialogue callback: {e}")
                    return result
                
                voice_assistant.process_response = patched_process
        
        # 注册回调
        voice_assistant.register_dialogue_callback(self.process_dialogue)
        self.voice_assistant = voice_assistant
    
    def process_dialogue(self, user_input, assistant_response, dialogue_context=None):
        """处理一组新的对话，评估并决定是否存储"""
        if not self.active:
            return False
            
        # 组装对话数据
        dialogue_data = {
            'user_input': user_input,
            'assistant_response': assistant_response,
            'timestamp': datetime.datetime.now().isoformat(),
            'context': dialogue_context or {}
        }
        
        # 评估对话价值
        value_score, value_tags = self.evaluator.evaluate(dialogue_data)
        
        # 更新统计
        self.stats['total_collected'] += 1
        
        # 决定是否保存
        if value_score >= self.config['value_threshold']:
            # 为对话添加评估信息
            dialogue_data['value_score'] = value_score
            dialogue_data['value_tags'] = value_tags
            
            # 存储到数据集
            self.dataset_manager.add_entry(dialogue_data)
            
            # 更新统计
            self.stats['high_value_collected'] += 1
            self.stats['current_dataset_size'] = self.dataset_manager.get_current_size()
            
            # 更新UI反馈
            self.ui_feedback.show_collection_success(value_score, value_tags)
        
        # 无论是否保存，都更新收集状态显示
        self.ui_feedback.update_collection_stats(self.stats)
        
        return value_score >= self.config['value_threshold']
    
    def toggle_active(self):
        """切换数据收集活动状态"""
        self.active = not self.active
        return self.active


# 默认配置
DEFAULT_CONFIG = {
    'dataset_path': './data/training_datasets',
    'value_threshold': 0.6,
    'evaluation_criteria': {
        'keyword_weights': {
            '例子': 0.3,
            '解释': 0.2,
            '如何': 0.2,
            '区别': 0.2,
            '详细': 0.2,
            '自定义': 0.4,
            '个性化': 0.4,
            '偏好': 0.3
        },
        'topic_weights': {
            '编程': 0.3,
            '学习': 0.2,
            '日常任务': 0.2,
            '工作': 0.2,
            '娱乐': 0.1,
            '自定义设置': 0.4
        },
        'min_dialogue_length': 15
    }
}


def create_collector(voice_assistant, main_window, config=None):
    """创建并初始化对话收集器"""
    collector_config = config or DEFAULT_CONFIG
    
    # 创建数据收集器
    collector = DialogueDataCollector(collector_config)
    
    # 初始化并连接到语音助手
    collector.initialize(voice_assistant)
    
    # 初始化UI反馈
    collector.ui_feedback.initialize(main_window)
    
    return collector 