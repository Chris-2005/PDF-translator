import os
from pathlib import Path
from PIL import Image
import re


class ImageToPDFConverter:
    def __init__(self, config):
        self.config = config

    def natural_sort_key(self, s):
        """
        自然排序键函数，用于按数字顺序排序文件名
        例如：page_1.jpg, page_2.jpg,..., page_10.jpg
        """
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', str(s))]

    def convert(self):
        """将翻译后的图片按数字顺序合并为PDF"""
        print("\n" + "=" * 50)
        print("步骤4: 将翻译后的图片合并为PDF")
        print("=" * 50)

        input_dir = self.config['output']['translated_image_dir']
        output_dir = self.config['output']['pdf_dir']

        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 获取原始PDF文件名(不含扩展名)
        pdf_name = Path(self.config['input']['pdf_path']).stem
        output_pdf = os.path.join(output_dir, f"{pdf_name}_translated.pdf")

        # 收集所有图片文件并按自然顺序排序
        image_list = []
        for f in os.listdir(input_dir):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                image_list.append(os.path.join(input_dir, f))

        if not image_list:
            print("错误: 没有找到翻译后的图片")
            return None

        # 按数字顺序排序图片文件
        image_list.sort(key=self.natural_sort_key)

        print("按以下顺序合并图片:")
        for img_path in image_list:
            print(f"- {os.path.basename(img_path)}")

        try:
            # 打开所有图片并转换为RGB模式
            images = []
            for img_path in image_list:
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)

            # 保存为PDF，第一张图片使用save，后续图片使用append
            if images:
                images[0].save(
                    output_pdf,
                    save_all=True,
                    append_images=images[1:],
                    quality=100
                )
                print(f"\nPDF已保存至: {output_pdf}")
                return output_pdf

        except Exception as e:
            print(f"合并PDF时出错: {e}")
            return None