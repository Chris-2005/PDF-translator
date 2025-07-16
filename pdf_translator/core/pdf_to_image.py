import os
from pathlib import Path
from pdf2image import convert_from_path


class PDFToImageConverter:
    def __init__(self, config):
        self.config = config

    def convert(self):
        """将PDF转换为图片"""
        print("\n" + "=" * 50)
        print("步骤1: 将PDF转换为图片")
        print("=" * 50)

        pdf_path = self.config['input']['pdf_path']
        output_folder = self.config['output']['image_dir']

        Path(output_folder).mkdir(parents=True, exist_ok=True)

        images = convert_from_path(pdf_path, dpi=self.config['processing']['dpi'])

        for i, image in enumerate(images):
            image_path = f"{output_folder}/page_{i + 1}.jpg"
            image.save(image_path, 'JPEG')
            print(f"保存: {image_path}")

        return len(images)