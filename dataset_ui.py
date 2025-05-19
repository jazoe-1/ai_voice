#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
from PyQt5.QtWidgets import QAction, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QTabWidget
from PyQt5.QtCore import Qt
import json
from logger import logger


class DatasetStatsDialog(QDialog):
    """数据集统计对话框"""
    
    def __init__(self, parent, stats):
        super().__init__(parent)
        self.stats = stats
        self.setWindowTitle("数据集统计")
        self.setMinimumSize(500, 400)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 总览选项卡
        overview_tab = QLabel()
        overview_tab.setTextFormat(Qt.RichText)
        overview_tab.setText(self._create_overview_html())
        tab_widget.addTab(overview_tab, "总览")
        
        # 数据集详情选项卡
        datasets_tab = QTextEdit()
        datasets_tab.setReadOnly(True)
        datasets_tab.setText(self._create_datasets_text())
        tab_widget.addTab(datasets_tab, "数据集详情")
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def _create_overview_html(self):
        """创建概览HTML"""
        return f"""
        <h2>数据集收集统计</h2>
        <p>
        <b>总数据集数量:</b> {self.stats['total_datasets']}<br>
        <b>总条目数量:</b> {self.stats['total_entries']}<br>
        <b>平均每个数据集条目:</b> {self.stats['total_entries'] / max(1, self.stats['total_datasets']):.1f}
        </p>
        """
    
    def _create_datasets_text(self):
        """创建数据集详情文本"""
        text = "数据集详细信息:\n\n"
        
        for dataset in self.stats['datasets']:
            text += f"数据集 #{dataset['id']}:\n"
            text += f"  条目数量: {dataset['entries']}\n"
            text += f"  创建时间: {dataset['created_at']}\n"
            text += f"  最后更新: {dataset['updated_at']}\n\n"
        
        return text


def add_dataset_menu(main_window, collector):
    """向主窗口添加数据集管理菜单"""
    # 检查菜单是否存在
    menu_bar = main_window.menuBar()
    
    # 寻找工具菜单，如果不存在则创建
    tools_menu = None
    for action in menu_bar.actions():
        if action.text() == "工具":
            tools_menu = action.menu()
            break
    
    if not tools_menu:
        tools_menu = menu_bar.addMenu("工具")
    
    # 添加数据集管理子菜单
    dataset_menu = tools_menu.addMenu("数据集管理")
    
    # 添加菜单项 - 显示统计
    stats_action = QAction("查看数据集统计", main_window)
    stats_action.triggered.connect(lambda: show_dataset_stats(main_window, collector))
    dataset_menu.addAction(stats_action)
    
    # 添加菜单项 - 切换数据收集
    toggle_action = QAction("暂停数据收集", main_window)
    toggle_action.triggered.connect(lambda: toggle_collection(toggle_action, collector))
    dataset_menu.addAction(toggle_action)
    
    # 添加菜单项 - 打开数据文件夹
    folder_action = QAction("打开数据集文件夹", main_window)
    folder_action.triggered.connect(lambda: open_dataset_folder(collector))
    dataset_menu.addAction(folder_action)


def show_dataset_stats(main_window, collector):
    """显示数据集统计对话框"""
    try:
        stats = collector.dataset_manager.get_dataset_stats()
        dialog = DatasetStatsDialog(main_window, stats)
        dialog.exec_()
    except Exception as e:
        logger.error(f"Error showing dataset stats: {e}")


def toggle_collection(action, collector):
    """切换数据收集状态"""
    active = collector.toggle_active()
    action.setText("继续数据收集" if not active else "暂停数据收集")


def open_dataset_folder(collector):
    """打开数据集文件夹"""
    path = os.path.abspath(collector.config['dataset_path'])
    
    try:
        if os.path.exists(path):
            # 在不同平台打开文件夹
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS, Linux
                if 'darwin' in os.sys.platform:  # macOS
                    subprocess.call(['open', path])
                else:  # Linux
                    subprocess.call(['xdg-open', path])
        else:
            os.makedirs(path, exist_ok=True)
            open_dataset_folder(collector)
    except Exception as e:
        logger.error(f"Error opening dataset folder: {e}") 