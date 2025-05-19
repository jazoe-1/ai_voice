import sys
import logging
from typing import Tuple, Optional, Callable
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QApplication
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
from OpenGL.GL import *

logger = logging.getLogger(__name__)


class PetWindow(QWidget):
    """透明窗口，显示桌面宠物"""
    
    # 定义信号
    mouse_pressed = pyqtSignal(int, int, int)  # x, y, button
    mouse_moved = pyqtSignal(int, int)
    mouse_released = pyqtSignal(int, int, int)
    mouse_double_clicked = pyqtSignal(int, int, int)
    
    def __init__(self, width: int = 300, height: int = 400):
        super().__init__()
        
        logger.info(f"创建窗口，大小: {width}x{height}")
        
        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 始终置顶
            Qt.Tool  # 工具窗口，不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景
        self.setMouseTracking(True)  # 跟踪鼠标移动
        
        # 基本属性
        self.resize(width, height)
        self.dragging = False
        self.drag_position = None
        self.opacity = 1.0
        
        logger.info("窗口属性已设置")
        
        # 创建OpenGL窗口
        self.init_gl_widget()
        
        # 确保窗口可见性
        self.setWindowOpacity(1.0)  # 设置初始不透明度为完全不透明
        
    def init_gl_widget(self):
        """初始化OpenGL窗口"""
        logger.info("初始化OpenGL窗口")
        # 创建OpenGL格式
        fmt = QGLFormat()
        fmt.setAlpha(True)
        fmt.setSampleBuffers(True)
        logger.info("已设置OpenGL格式")
        
        # 创建OpenGL小部件
        self.gl_widget = QGLWidget(fmt, self)
        self.gl_widget.setGeometry(0, 0, self.width(), self.height())
        
    def setup_renderer(self, renderer):
        """设置渲染器
        
        Args:
            renderer: 用于渲染模型的渲染器实例
        """
        logger.info("设置渲染器")
        self.renderer = renderer
        logger.info("正在初始化OpenGL上下文")
        self.gl_widget.makeCurrent()
        logger.info("正在初始化渲染器")
        self.renderer.initialize()
        
    def resizeEvent(self, event):
        """窗口大小改变时调整GL窗口大小"""
        super().resizeEvent(event)
        if hasattr(self, 'gl_widget'):
            self.gl_widget.setGeometry(0, 0, self.width(), self.height())
            
    def paintEvent(self, event):
        """绘制事件，保持窗口透明"""
        painter = QPainter(self)
        painter.setOpacity(0)  # 透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.mouse_pressed.emit(event.x(), event.y(), event.button())
            
        elif event.button() == Qt.RightButton:
            # 右键菜单
            self.show_context_menu(event.globalPos())
            self.mouse_pressed.emit(event.x(), event.y(), event.button())
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        self.mouse_moved.emit(event.x(), event.y())
        
        if self.dragging and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            
        self.mouse_released.emit(event.x(), event.y(), event.button())
        
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        self.mouse_double_clicked.emit(event.x(), event.y(), event.button())
        
    def show_context_menu(self, position: QPoint):
        """显示右键菜单
        
        Args:
            position: 菜单显示位置
        """
        menu = QMenu()
        
        # 添加菜单项
        settings_action = menu.addAction("设置")
        hide_action = menu.addAction("隐藏")
        exit_action = menu.addAction("退出")
        
        # 执行菜单并获取结果
        action = menu.exec_(position)
        
        # 处理菜单选择
        if action == settings_action:
            self.on_settings()
        elif action == hide_action:
            self.hide()
        elif action == exit_action:
            self.on_exit()
            
    def set_size(self, width: int, height: int):
        """设置窗口大小
        
        Args:
            width: 窗口宽度
            height: 窗口高度
        """
        self.resize(width, height)
        
    def set_opacity(self, opacity: float):
        """设置窗口不透明度
        
        Args:
            opacity: 不透明度 (0.0-1.0)
        """
        self.opacity = max(0.1, min(1.0, opacity))
        self.setWindowOpacity(self.opacity)
        
    def reset_position(self):
        """重置窗口位置到屏幕右下角"""
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry()
        x = screen_rect.width() - self.width() - 50
        y = screen_rect.height() - self.height() - 50
        self.move(x, y)
        
    def on_settings(self):
        """设置菜单项点击回调"""
        # 这个方法将被外部逻辑重写
        logger.debug("Settings menu clicked")
        
    def on_exit(self):
        """退出菜单项点击回调"""
        # 这个方法将被外部逻辑重写
        logger.debug("Exit menu clicked")
        
    def isValid(self):
        """检查窗口是否可用于渲染"""
        return self.isVisible() and not self.isMinimized()

    def isExposed(self):
        """检查窗口是否暴露给显示系统"""
        return self.isVisible() and hasattr(self, "windowHandle") and self.windowHandle().isExposed()

    def show(self):
        """显示窗口并确保它在前台"""
        # 调用基类方法
        super().show()
        
        # 强制窗口显示在前台
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.activateWindow()
        self.raise_()
        
        # 记录窗口显示状态
        logging.info(f"窗口显示: 可见={self.isVisible()}, 活动={self.isActiveWindow()}, 前台={self.isTopLevel()}")
        
        # 设置一个定时器再次确保窗口可见
        QTimer.singleShot(500, self._ensure_visibility) 

    def _ensure_visibility(self):
        """确保窗口可见的辅助方法"""
        if not self.isVisible():
            logging.warning("窗口不可见，尝试强制显示")
            self.show()
            self.activateWindow()
            self.raise_()
        
        # 检查窗口是否有效
        if not self.is_exposed():
            logging.warning("窗口未暴露给显示系统，尝试重新创建")
            # 尝试重新初始化OpenGL部件
            if hasattr(self, 'gl_widget') and self.gl_widget:
                # 先记住渲染器
                renderer = None
                if hasattr(self.gl_widget, 'renderer'):
                    renderer = self.gl_widget.renderer
                
                # 重新创建OpenGL部件
                self.gl_widget.hide()
                self.gl_widget.deleteLater()
                self.gl_widget = None
                
                # 创建新的OpenGL部件
                self.setup_opengl_widget()
                
                # 恢复渲染器
                if renderer:
                    self.setup_renderer(renderer)
                
                # 重新显示
                self.show()
                self.activateWindow()
                self.raise_() 