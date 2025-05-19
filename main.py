#!/usr/bin/env python3
import os
import sys
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建必要的导入钩子，以确保代码能在各种情况下运行
try:
    from PyQt5.QtWidgets import QTextEdit, QLineEdit
except ImportError:
    logging.warning("无法导入一些PyQt5组件，UI可能受限")

# 导入统一窗口类
from unified_main_window import UnifiedMainWindow


def ensure_resources():
    """确保资源文件存在"""
    # 检查图标目录
    icons_dir = os.path.join(os.path.dirname(__file__), "ui", "icons")
    
    # 确保目录存在
    os.makedirs(icons_dir, exist_ok=True)
    
    if not os.path.exists(icons_dir) or len([f for f in os.listdir(icons_dir) if f.endswith('.png')]) < 5:
        try:
            logging.info("正在生成应用图标...")
            # 使用try导入防止导入失败
            try:
                import create_icons
            except ImportError:
                # 如果模块不在路径中，使用exec执行脚本
                with open('create_icons.py') as f:
                    exec(f.read())
            logging.info("图标生成完成")
        except Exception as e:
            logging.error(f"生成图标失败: {e}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("语音助手与桌面宠物")
    
    # 应用Mac风格
    try:
        from ui.mac_style_helper import MacStyleHelper
        MacStyleHelper.apply_mac_style(app)
    except Exception as e:
        logging.error(f"应用Mac风格失败: {e}")
    
    # 检查依赖
    try:
        check_dependencies()
    except Exception as e:
        logging.error(f"检查依赖失败: {e}")
    
    # 在main函数开始前调用
    ensure_resources()
    
    # 创建主窗口
    main_window = UnifiedMainWindow()
    
    # 创建语音助手
    try:
        from voice_assistant import VoiceAssistantCore
        # 使用VoiceAssistantCore而不是完整的VoiceAssistant
        voice_assistant = VoiceAssistantCore(main_window, connect_ui=True)
        main_window.voice_assistant = voice_assistant
        
        # 增加这一行 - 延迟加载UI数据
        QTimer.singleShot(1000, lambda: hasattr(voice_assistant, "load_ui_data") and voice_assistant.load_ui_data())
        
        # 连接基本事件
        if hasattr(main_window, 'speech_recognition_help_btn'):
            # 确保window类自己的方法被优先使用
            main_window.speech_recognition_help_btn.clicked.connect(main_window.on_speech_help_clicked)

        if hasattr(main_window, 'voice_diagnostic_btn'):
            main_window.voice_diagnostic_btn.clicked.connect(main_window.on_voice_diagnostic_clicked)

        # 检查方法是否存在后再连接
        if hasattr(voice_assistant, 'test_voice') and hasattr(main_window, 'test_voice_btn'):
            main_window.test_voice_btn.clicked.connect(voice_assistant.test_voice)

        if hasattr(voice_assistant, 'apply_recognition_settings') and hasattr(main_window, 'apply_recognition_params_btn'):
            main_window.apply_recognition_params_btn.clicked.connect(voice_assistant.apply_recognition_settings)

        if hasattr(voice_assistant, 'apply_voice_settings') and hasattr(main_window, 'apply_voice_settings_btn'):
            main_window.apply_voice_settings_btn.clicked.connect(voice_assistant.apply_voice_settings)
        
        # 连接桌面宠物控制按钮事件
        if hasattr(voice_assistant, 'pet_integration') and voice_assistant.pet_integration:
            pet_manager = voice_assistant.pet_integration.pet_manager
            
            # 确保按钮存在且未连接
            if hasattr(main_window, 'start_pet_btn') and not is_signal_connected(main_window.start_pet_btn.clicked, lambda: pet_manager.start()):
                main_window.start_pet_btn.clicked.connect(lambda: pet_manager.start())
            
            if hasattr(main_window, 'stop_pet_btn') and not is_signal_connected(main_window.stop_pet_btn.clicked, lambda: pet_manager.stop()):
                main_window.stop_pet_btn.clicked.connect(lambda: pet_manager.stop())
            
            # 添加调试按钮事件
            if hasattr(main_window, 'debug_pet_btn') and not is_signal_connected(main_window.debug_pet_btn.clicked, pet_manager.debug_model_status):
                main_window.debug_pet_btn.clicked.connect(pet_manager.debug_model_status)
            
            # 桌面宠物的模型下载 - 使用宠物专用按钮
            if hasattr(main_window, 'pet_download_model_btn'):
                download_func = lambda: __import__("desktop_pet.utils.model_downloader").utils.model_downloader.ModelDownloader.download_sample_model(main_window)
                if not is_signal_connected(main_window.pet_download_model_btn.clicked, download_func):
                    main_window.pet_download_model_btn.clicked.connect(download_func)

        # 添加额外的按钮连接 - API设置相关
        if hasattr(main_window, 'refresh_models_btn') and hasattr(voice_assistant, 'update_model_list'):
            if not is_signal_connected(main_window.refresh_models_btn.clicked, voice_assistant.update_model_list):
                main_window.refresh_models_btn.clicked.connect(voice_assistant.update_model_list)

        if hasattr(main_window, 'apply_api_settings_btn') and hasattr(voice_assistant, 'apply_api_settings'):
            if not is_signal_connected(main_window.apply_api_settings_btn.clicked, voice_assistant.apply_api_settings):
                main_window.apply_api_settings_btn.clicked.connect(voice_assistant.apply_api_settings)

        # 注意：语音识别页面按钮连接已在unified_main_window.py中直接实现
        # 不再需要以下连接，因为它们会导致冲突和覆盖
        # if hasattr(main_window, 'refresh_vosk_models_btn'):
        #     main_window.refresh_vosk_models_btn.clicked.connect(voice_assistant.load_ui_data)
        # 
        # if hasattr(main_window, 'download_model_btn'):
        #     main_window.download_model_btn.clicked.connect(lambda: main_window.on_download_vosk_model())
    except Exception as e:
        logging.error(f"初始化语音助手失败: {e}")
        QMessageBox.critical(main_window, "初始化错误", f"无法初始化语音助手: {str(e)}")
    
    # 在main函数中创建主窗口后添加
    try:
        # 集成数据集UI
        from dataset_ui import add_dataset_menu
        from data_collector import DataCollector
        
        # 创建数据收集器
        collector = DataCollector(config_path="config/dataset_config.json")
        # 添加数据集管理菜单
        add_dataset_menu(main_window, collector)
        
        # Enhanced UI for data collection (optional)
        try:
            from data_collector_ui import initialize_data_collector_ui
            initialize_data_collector_ui(main_window)
            logging.info("数据收集UI增强已初始化")
        except ImportError:
            pass
    except ImportError as e:
        logging.warning(f"数据收集组件导入失败: {e}")
    except Exception as e:
        logging.error(f"初始化数据收集功能失败: {e}")
    
    # 显示窗口
    main_window.show()
    
    # 运行应用程序
    exit_code = app.exec_()
    
    # 退出前清理资源
    if hasattr(main_window, 'voice_assistant') and hasattr(main_window.voice_assistant, 'pet_integration'):
        main_window.voice_assistant.pet_integration.cleanup()
    
    sys.exit(exit_code)


def check_dependencies():
    """检查必要的依赖"""
    missing = []
    
    # 检查PyOpenGL
    try:
        import OpenGL
        import OpenGL.GL
    except ImportError:
        missing.append("PyOpenGL")
    
    # 检查numpy
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    # 检查Pillow
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")
    
    # 如果有缺失的依赖，提示安装
    if missing:
        error_msg = f"缺少必要的依赖: {', '.join(missing)}\n请运行 'pip install {' '.join(missing)}' 安装它们"
        logging.error(error_msg)
        # 不抛出异常，让程序继续尝试运行
        return False
        
    return True


def is_signal_connected(signal, slot):
    """检查信号是否已连接到指定的槽函数"""
    try:
        # 尝试断开连接，如果成功返回True，说明之前已连接
        signal.disconnect(slot)
        # 如果成功断开，重新连接
        signal.connect(slot)
        return True
    except (TypeError, RuntimeError):
        # 如果断开失败，则说明之前未连接
        signal.connect(slot)  # 连接信号
        return False
    except Exception as e:
        logging.warning(f"检查信号连接失败: {e}")
        return False


if __name__ == "__main__":
    main()