from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont

class MacStyleHelper:
    """苹果风格样式助手"""
    
    # 苹果风格颜色
    COLORS = {
        "primary": "#007AFF",      # 蓝色主色调
        "secondary": "#54C7FC",    # 浅蓝色次要色调
        "success": "#34C759",      # 绿色成功色调
        "warning": "#FF9500",      # 橙色警告色调
        "error": "#FF3B30",        # 红色错误色调
        "background": "#F5F5F7",   # 背景色
        "surface": "#FFFFFF",      # 表面色
        "text": "#1D1D1F",         # 文本颜色
        "text_secondary": "#86868B" # 次要文本颜色
    }
    
    # 字体大小
    FONTS = {
        "title": 20,        # 标题
        "subtitle": 16,     # 副标题
        "body": 14,         # 正文
        "caption": 12,      # 说明文字
        "button": 14        # 按钮文字
    }
    
    @staticmethod
    def apply_mac_style(app):
        """应用全局苹果风格样式"""
        app.setStyle("Fusion")  # 使用Fusion风格作为基础
        
        # 创建苹果风格的样式表
        style_sheet = """
        QMainWindow, QDialog {
            background-color: """ + MacStyleHelper.COLORS["background"] + """;
        }
        
        QWidget {
            font-family: 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
            color: """ + MacStyleHelper.COLORS["text"] + """;
        }
        """
        app.setStyleSheet(style_sheet)

    @staticmethod
    def create_mac_card(title=None):
        """创建苹果风格的卡片"""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: """ + MacStyleHelper.COLORS["surface"] + """;
                border-radius: 10px;
                padding: 15px;
                border: 1px solid #EAEAEA;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                font-size: """ + str(MacStyleHelper.FONTS["subtitle"]) + """px;
                font-weight: bold;
                color: """ + MacStyleHelper.COLORS["text"] + """;
                margin-bottom: 10px;
            """)
            layout.addWidget(title_label)
        
        return card, layout

    @staticmethod
    def apply_text_area_style(text_edit):
        """应用文本区域样式"""
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: """ + MacStyleHelper.COLORS["surface"] + """;
                border: 1px solid #CECED2;
                border-radius: 6px;
                padding: 8px;
                color: """ + MacStyleHelper.COLORS["text"] + """;
            }
        """)

    @staticmethod
    def apply_input_style(line_edit):
        """应用输入框样式"""
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: """ + MacStyleHelper.COLORS["surface"] + """;
                border: 1px solid #CECED2;
                border-radius: 6px;
                padding: 8px;
                color: """ + MacStyleHelper.COLORS["text"] + """;
            }
            QLineEdit:focus {
                border: 1px solid """ + MacStyleHelper.COLORS["primary"] + """;
            }
        """)

    @staticmethod
    def apply_button_style(button, primary=False):
        """应用按钮样式"""
        if primary:
            button.setStyleSheet("""
                QPushButton {
                    background-color: """ + MacStyleHelper.COLORS["primary"] + """;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2E8BFF;
                }
                QPushButton:pressed {
                    background-color: #0062CC;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F7;
                    color: """ + MacStyleHelper.COLORS["text"] + """;
                    border: 1px solid #CECED2;
                    border-radius: 6px;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #EAEAEA;
                }
                QPushButton:pressed {
                    background-color: #D6D6D6;
                }
            """)

    @staticmethod
    def apply_window_style(window):
        """应用窗口样式"""
        window.setStyleSheet("""
            QMainWindow {
                background-color: """ + MacStyleHelper.COLORS["background"] + """;
            }
        """)

    @staticmethod
    def apply_title_style(label):
        """应用标题样式"""
        font = label.font()
        font.setPointSize(18)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("""
            QLabel {
                color: """ + MacStyleHelper.COLORS["text"] + """;
                margin: 10px;
            }
        """)

    @staticmethod
    def apply_tab_style(tab_widget):
        """应用标签页样式"""
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CECED2;
                border-radius: 6px;
                background-color: """ + MacStyleHelper.COLORS["surface"] + """;
            }
            QTabBar::tab {
                background-color: """ + MacStyleHelper.COLORS["background"] + """;
                border: 1px solid #CECED2;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: """ + MacStyleHelper.COLORS["surface"] + """;
                border-bottom: none;
            }
        """)

    @staticmethod
    def apply_status_style(label):
        """应用状态栏样式"""
        label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #ced4da;
            }
        """) 