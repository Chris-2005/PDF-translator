from pathlib import Path
from paddleocr import PaddleOCR
import time
from datetime import datetime


class ImageOCRProcessor:
    def __init__(self, config):
        self.config = config

    def process(self):
        """运行OCR处理"""
        print("\n" + "=" * 50)
        print("步骤2: 运行OCR处理")
        print("=" * 50)

        input_dir = Path(self.config['output']['image_dir'])
        output_dir = Path(self.config['output']['json_dir'])

        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize PaddleOCR instance with similar config to the example
        pipeline = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )

        # 获取所有图片文件并按数字顺序排序
        image_files = []
        for img_path in input_dir.glob('*'):
            if img_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}:
                image_files.append(img_path)

        # 按页码数字排序
        image_files.sort(key=lambda x: int(x.stem.split('_')[-1]))

        for img_path in image_files:
            start_time = time.time()
            print(f"\n处理: {img_path.name}")

            try:
                output = pipeline.predict(input=str(img_path))
            except Exception as e:
                print(f"处理失败: {str(e)}")
                continue

            img_output_dir = output_dir / img_path.stem
            img_output_dir.mkdir(exist_ok=True)

            for res in output:
                # PP-OCRv5 has slightly different output handling
                res.print()  # Print results to console
                res.save_to_img(save_path=str(img_output_dir))
                res.save_to_json(save_path=str(img_output_dir))

            print(f"处理完成: {img_path.name} (耗时: {time.time() - start_time:.2f}秒)")