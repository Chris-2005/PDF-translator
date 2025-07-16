import os
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict
import fitz  # PyMuPDF
from pdf2zh.doclayout import ModelInstance, OnnxModel
from langdetect import detect, LangDetectException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 支持的语言选项
SUPPORTED_LANGUAGES = {
    "1": {"code": "zh", "name": "简体中文", "font": "SourceHanSerifCN-Regular.ttf"},
    "2": {"code": "en", "name": "English", "font": "Arial.ttf"},
    "3": {"code": "ja", "name": "日本語", "font": "MS-Mincho.ttf"},
    "4": {"code": "ko", "name": "한국어", "font": "NanumGothic.ttf"},
    "5": {"code": "ru", "name": "Русский", "font": "TimesNewRoman.ttf"},
    "6": {"code": "es", "name": "Español", "font": "Arial.ttf"},
    "7": {"code": "fr", "name": "Français", "font": "Arial.ttf"},
    "8": {"code": "de", "name": "Deutsch", "font": "Arial.ttf"}
}

# 语言代码到名称的映射
CODE_TO_NAME = {
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "ru": "Русский",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch"
}


class DocumentLayoutModel:
    """简化版文档布局模型"""

    def predict(self, image, imgsz=1024):
        class DummyResult:
            def __init__(self):
                self.boxes = [DummyBox()]
                self.names = ["text", "formula"]

        class DummyBox:
            def __init__(self):
                self.xyxy = [0, 0, image.shape[1], image.shape[0]]
                self.conf = 0.9
                self.cls = 0

        return [DummyResult()]


class NonScannedPDFProcessor:
    def __init__(self, config):
        self.config = config
        self._init_model()
        self.input_pdf = self.config['input']['pdf_path']
        self.output_dir = self.config['output']['pdf_dir']
        self.api_key = self.config['api']['deepseek_key']
        self.api_url = self.config['api']['deepseek_url']

    def _init_model(self):
        """初始化文档布局模型"""
        try:
            ModelInstance.value = OnnxModel.load_available()
            logger.info("Document layout model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {str(e)}")
            ModelInstance.value = DocumentLayoutModel()

    def _get_font_path(self, lang_code: str) -> str:
        """获取适合目标语言的字体"""
        font_dir = self.config['non_scanned']['font_dir']
        for lang in SUPPORTED_LANGUAGES.values():
            if lang["code"] == lang_code:
                font_path = Path(font_dir) / lang["font"]
                if font_path.exists():
                    return str(font_path)
        return str(Path(font_dir) / "Arial.ttf")

    def detect_language(self, text_sample: str) -> str:
        """检测文本的语言"""
        try:
            return detect(text_sample)
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return "en"  # 默认英语

    def extract_sample_text(self, pdf_path: str) -> str:
        """从PDF中提取样本文本用于语言检测"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
                if len(text) > 500:  # 500字符足够检测语言
                    break
            return text[:500]
        except Exception as e:
            logger.error(f"Failed to extract sample text: {str(e)}")
            return ""

    def _translate_with_deepseek(self, text: str, src_lang: str, target_lang: str) -> str:
        """使用DeepSeek API翻译文本"""
        try:
            if src_lang == target_lang:
                return text

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            prompt = (
                f"Translate the following text from {src_lang} to {target_lang}.\n"
                f"Preserve all special formatting and symbols.\n"
                f"Only return the translated text.\n"
                f"Text: {text}"
            )

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return f"[TRANSLATION ERROR] {text}"

    def select_source_language(self, detected_lang: str) -> Dict:
        """让用户选择源语言"""
        print(f"\n检测到输入PDF可能语言：{CODE_TO_NAME.get(detected_lang, detected_lang)}")
        choice = input("是否使用此语言作为源语言？（Y/n）：").strip().lower()

        if choice == 'y' or choice == '':
            # 查找对应的语言选项
            for num, lang in SUPPORTED_LANGUAGES.items():
                if lang["code"] == detected_lang:
                    print(f"\n已选择: {lang['name']}")
                    return lang
            # 如果不在支持的语言中，默认使用英语
            print(f"\n检测到的语言不在支持列表中，默认使用英语")
            return SUPPORTED_LANGUAGES["2"]

        print("\n请选择源语言:")
        for num, lang in SUPPORTED_LANGUAGES.items():
            print(f"{num}. {lang['name']} ({lang['code']})")

        while True:
            choice = input("请输入数字选择语言：").strip()
            if choice in SUPPORTED_LANGUAGES:
                selected = SUPPORTED_LANGUAGES[choice]
                print(f"\n已选择: {selected['name']}")
                return selected
            print("无效输入，请重新选择")

    def select_target_language(self) -> Dict:
        """让用户选择目标语言"""
        print("\n请选择目标语言:")
        for num, lang in SUPPORTED_LANGUAGES.items():
            print(f"{num}. {lang['name']} ({lang['code']})")

        while True:
            choice = input("请输入数字选择语言（默认1-英语）：").strip()
            if choice == "":
                choice = "1"  # 默认英语
            if choice in SUPPORTED_LANGUAGES:
                selected = SUPPORTED_LANGUAGES[choice]
                print(f"\n已选择: {selected['name']}")
                return selected
            print("无效输入，请重新选择")

    def run(self, target_lang_code: str = None) -> str:
        """翻译PDF文件"""
        try:
            # 提取样本文本并检测语言
            sample_text = self.extract_sample_text(self.input_pdf)
            detected_lang = self.detect_language(sample_text)

            # 让用户选择源语言
            source_lang = self.select_source_language(detected_lang)
            src_lang_code = source_lang["code"]

            # 让用户选择目标语言或使用传入的参数
            if target_lang_code is None:
                target_lang = self.select_target_language()
            else:
                # 从支持的语言中查找
                target_lang = next(
                    (lang for lang in SUPPORTED_LANGUAGES.values()
                     if lang["code"] == target_lang_code),
                    None
                )
                if target_lang is None:
                    raise ValueError(f"不支持的目标语言代码: {target_lang_code}")

            lang_code = target_lang["code"]
            font_path = self._get_font_path(lang_code)

            # 确保输出目录存在
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

            logger.info(f"源语言: {src_lang_code}, 目标语言: {lang_code}")

            # 设置翻译参数
            params = {
                "files": [self.input_pdf],
                "output": self.output_dir,
                "lang_in": src_lang_code,
                "lang_out": lang_code,
                "service": "deepseek",
                "thread": self.config['non_scanned']['thread_count'],
                "model": ModelInstance.value,
                "envs": {"DEEPSEEK_API_KEY": self.api_key},
                "skip_subset_fonts": True
            }

            # 执行翻译
            logger.info(f"开始翻译到 {target_lang['name']}...")
            from pdf2zh.high_level import translate
            result = translate(**params)

            if result:
                output_path = Path(self.output_dir) / f"{Path(self.input_pdf).stem}_{lang_code}.pdf"
                logger.info(f"翻译完成: {output_path}")
                return str(output_path)

            logger.error("翻译失败 - 无输出文件生成")
            return None

        except Exception as e:
            logger.error(f"翻译失败: {str(e)}", exc_info=True)
            return None