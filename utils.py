#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
from logger import logger

def handle_errors(func):
    """统一的错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {e}")
            # 如果是UI类的方法，显示错误对话框
            if hasattr(args[0], 'error_signal'):
                args[0].error_signal.emit("操作失败", str(e))
            return None
    return wrapper

def safe_connect(signal, slot, description=""):
    """安全地连接信号和槽，避免重复连接"""
    try:
        # 尝试断开连接，如果成功则说明之前已连接
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            # 未连接，无需操作
            pass
        
        # 连接信号
        signal.connect(slot)
        return True
    except Exception as e:
        logger.error(f"连接信号失败({description}): {e}")
        return False 