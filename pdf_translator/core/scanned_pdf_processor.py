from .base_processor import BasePDFProcessor
from .pdf_to_image import PDFToImageConverter
from .image_ocr import ImageOCRProcessor
from .image_translator import ImageTranslator
from .image_to_pdf import ImageToPDFConverter
from utils.file_utils import FileUtils


class ScannedPDFProcessor(BasePDFProcessor):
    def run(self):
        """处理扫描件PDF的完整流程"""
        try:
            print("\n" + "=" * 50)
            print("开始处理扫描件PDF (OCR流程)")
            print("=" * 50)

            # 1. PDF转图片
            print("步骤1: PDF转图片...")
            PDFToImageConverter(self.config).convert()

            # 2. 运行OCR
            print("\n步骤2: 运行OCR...")
            ImageOCRProcessor(self.config).process()

            # 3. 翻译图片内容
            print("\n步骤3: 翻译内容...")
            ImageTranslator(self.config).translate_images()

            # 4. 合并为PDF
            print("\n步骤4: 生成最终PDF...")
            final_pdf = ImageToPDFConverter(self.config).convert()

            # 5. 清理临时文件
            if not self.config['processing']['keep_temp_files']:
                print("\n清理临时文件...")
                FileUtils.cleanup_temp_files(self.config)

            return final_pdf
        except Exception as e:
            print(f"\n扫描件处理失败: {e}")
            return None