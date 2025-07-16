import os
import shutil
from pathlib import Path


class FileUtils:
    @staticmethod
    def cleanup_temp_files(config):
        """清理临时文件目录"""
        temp_dirs = [
            config['output']['image_dir'],
            config['output']['json_dir'],
            config['output']['translated_image_dir']
        ]

        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"已清理: {temp_dir}")
            except Exception as e:
                print(f"清理失败 {temp_dir}: {e}")