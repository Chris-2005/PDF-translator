from pathlib import Path
import yaml
from core.scanned_pdf_processor import ScannedPDFProcessor
from core.non_scanned_pdf_processor import NonScannedPDFProcessor


class PDFTranslator:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 让用户选择处理模式
        self._select_processing_mode()

        self.processor = self._select_processor()
        Path(self.config['output']['pdf_dir']).mkdir(parents=True, exist_ok=True)

    def _select_processing_mode(self):
        """让用户选择处理模式"""
        print("\n" + "=" * 50)
        print("请选择PDF处理模式:")
        print("1. 扫描件翻译 (OCR流程)")
        print("2. 非扫描件翻译 (直接文本处理)")
        print("=" * 50)

        while True:
            choice = input("请输入数字选择模式 (默认1): ").strip()
            if not choice:
                choice = "1"

            if choice == "1":
                self.config['input']['is_scanned'] = True
                print("\n已选择: 扫描件翻译模式")
                break
            elif choice == "2":
                self.config['input']['is_scanned'] = False
                print("\n已选择: 非扫描件翻译模式")
                break
            else:
                print("无效输入，请重新选择")

    def _select_processor(self):
        """根据配置选择PDF处理器"""
        if self.config['input']['is_scanned']:
            return ScannedPDFProcessor(self.config)
        else:
            return NonScannedPDFProcessor(self.config)

    def _detect_if_scanned(self, pdf_path):
        """检测PDF是否为扫描件"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text_length = 0
            for page in doc:
                text = page.get_text()
                if text and len(text.strip()) > 50:  # 如果有超过50个字符的可读文本
                    return False
                text_length += len(text or "")

            # 如果总文本很少，则认为是扫描件
            return text_length < 100
        except Exception as e:
            print(f"PDF检测失败，默认使用OCR流程: {e}")
            return True

    def run(self):
        """统一运行接口"""
        try:
            result = self.processor.run()
            if result:
                print("\n" + "=" * 50)
                print(f"翻译完成: {result}")
                print("=" * 50)
                return result
            else:
                raise Exception("处理器返回空结果")
        except Exception as e:
            print("\n" + "!" * 50)
            print(f"处理失败: {e}")
            print("!" * 50)
            return None


if __name__ == "__main__":
    translator = PDFTranslator()
    translator.run()