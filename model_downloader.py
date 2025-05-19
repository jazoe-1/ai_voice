import os
import zipfile
import shutil
import logging
import tempfile
import urllib.request
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)

class ModelDownloader:
    """模型下载器，用于下载Live2D模型资源"""
    
    # 示例模型URL
    SAMPLE_MODEL_URL = "https://example.com/live2d/unitychan.zip"  # 替换为实际URL
    
    @staticmethod
    def download_sample_model(parent_widget=None):
        """下载示例模型
        
        Args:
            parent_widget: 父窗口，用于显示进度对话框
            
        Returns:
            bool: 下载是否成功
        """
        try:
            # 创建进度对话框
            progress = QProgressDialog("下载中...", "取消", 0, 100, parent_widget)
            progress.setWindowTitle("下载示例模型")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 下载ZIP文件
                zip_path = os.path.join(temp_dir, "model.zip")
                
                def update_progress(block_num, block_size, total_size):
                    """更新下载进度"""
                    if progress.wasCanceled():
                        raise Exception("用户取消下载")
                    
                    downloaded = block_num * block_size
                    if total_size > 0:
                        percent = min(100, int(downloaded * 100 / total_size))
                        progress.setValue(percent)
                
                # 执行下载
                try:
                    urllib.request.urlretrieve(
                        ModelDownloader.SAMPLE_MODEL_URL,
                        zip_path,
                        reporthook=update_progress
                    )
                except Exception as e:
                    logger.error(f"下载失败: {e}")
                    progress.close()
                    QMessageBox.warning(parent_widget, "下载失败", f"无法下载模型: {str(e)}")
                    return False
                
                progress.setValue(100)
                progress.setLabelText("解压中...")
                
                # 创建模型目录
                models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))), "models")
                os.makedirs(models_dir, exist_ok=True)
                
                # 解压文件
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(models_dir)
                    
                    logger.info(f"模型已下载并解压到: {models_dir}")
                    progress.close()
                    
                    QMessageBox.information(
                        parent_widget, 
                        "下载完成", 
                        f"示例模型已下载并解压到:\n{models_dir}\n\n请重新启动桌面宠物。"
                    )
                    return True
                    
                except Exception as e:
                    logger.error(f"解压失败: {e}")
                    progress.close()
                    QMessageBox.warning(parent_widget, "解压失败", f"无法解压模型文件: {str(e)}")
                    return False
                
        except Exception as e:
            logger.error(f"下载模型过程中发生错误: {e}")
            QMessageBox.warning(parent_widget, "错误", f"下载模型过程中发生错误: {str(e)}")
            return False 