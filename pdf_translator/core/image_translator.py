import os
import json
import requests
from PIL import Image, ImageDraw, ImageFont
import platform
import subprocess
import re
import time
import hashlib
from tqdm import tqdm
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # 确保结果可重复


def detect_pdf_language(pdf_path):
    """从PDF中提取文本并识别占比最多的语言"""
    try:
        import fitz  # PyMuPDF
        from collections import defaultdict

        # 支持的语言及其Unicode范围 (与non_scanned_pdf_processor.py保持一致)
        LANGUAGE_RANGES = {
            'zh': [('\u4e00', '\u9fff')],  # 中文
            'ja': [('\u3040', '\u30ff'), ('\u31f0', '\u31ff')],  # 日文
            'ko': [('\uac00', '\ud7a3')],  # 韩文
            'ru': [('\u0400', '\u04ff')],  # 俄文
            'en': [],  # 英文(无特定范围)
            'es': [],  # 西班牙文
            'fr': [],  # 法文
            'de': []  # 德文
        }

        # 从PDF中提取样本文本 (使用fitz而非pdfplumber)
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > 500:  # 500字符足够检测语言
                break
        text = text[:500]

        if not text:
            return None  # 不设置默认语言

        # 统计各语言字符数
        lang_counts = defaultdict(int)
        total_chars = 0

        for char in text:
            total_chars += 1
            char_matched = False

            # 检查特定Unicode范围的文字
            for lang, ranges in LANGUAGE_RANGES.items():
                if not ranges:  # 拉丁语系
                    continue

                for (start, end) in ranges:
                    if start <= char <= end:
                        lang_counts[lang] += 1
                        char_matched = True
                        break
                if char_matched:
                    break

            # 未匹配特定范围的字符归类为拉丁语系
            if not char_matched and char.isalpha():
                try:
                    lang = detect(char)
                    if lang in LANGUAGE_RANGES:
                        lang_counts[lang] += 1
                except:
                    pass

        # 如果没有检测到任何特定语言字符，使用langdetect检测全文
        if not lang_counts and len(text) > 10:
            try:
                lang = detect(text[:1000])
                if lang in LANGUAGE_RANGES:
                    return lang
            except:
                pass

            return None

        # 返回占比最高的语言
        if lang_counts:
            return max(lang_counts.items(), key=lambda x: x[1])[0]

        return None

    except Exception as e:
        print(f"语言检测失败: {e}")
        return None

class ImageTranslator:
    LANGUAGE_MAP = {
        "en": ("English", "latin"),
        "zh": ("简体中文", "cjk"),
        "ko": ("한국어", "korean"),
        "ru": ("Русский", "cyrillic"),
        "ja": ("日本語", "japanese"),
        "es": ("Español", "latin"),
        "fr": ("Français", "latin"),
        "de": ("Deutsch", "latin")
    }

    def __init__(self, config):
        self.config = config
        self.api_key = config['api']['deepseek_key']
        self.source_lang = self.detect_source_language()  # 新增自动检测
        self.target_lang = self.select_target_language()  # 修改为交互式选择
        self.api_url = config['api']['deepseek_url']
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.font_cache = {}
        self.setup_fonts()
        self.max_retries = config['api'].get('max_retries', 3)  # 从配置获取或默认3次
        self.retry_delay = config['api'].get('retry_delay', 5)  # 从配置获取或默认5秒

    def detect_source_language(self):
        """自动检测源PDF语言，处理未识别情况"""
        pdf_path = self.config['input']['pdf_path']

        # 提取样本文本
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
                if len(text) > 500:
                    break
            text_sample = text[:500]
        except Exception as e:
            print(f"提取PDF文本失败: {e}")
            text_sample = ""

        # 检测语言
        try:
            from langdetect import detect, LangDetectException
            DetectorFactory.seed = 0
            lang_code = detect(text_sample) if text_sample else None
        except LangDetectException:
            lang_code = None

        if lang_code is None:
            print("\n无法自动确定文档语言，请手动选择:")
        else:
            lang_name = self.LANGUAGE_MAP.get(lang_code, ('未知', ''))[0]
            print(f"\n检测到输入PDF可能语言: {lang_name}")
            confirm = input("是否使用此语言作为源语言? (Y/n): ").strip().lower()
            if confirm != 'n':
                return lang_code

        # 手动选择语言
        print("\n请选择源语言:")
        for i, (code, (name, _)) in enumerate(self.LANGUAGE_MAP.items(), 1):
            print(f"{i}. {name} ({code})")

        while True:
            try:
                choice = input("请输入数字选择语言: ").strip()
                if choice:
                    lang_map = {str(i): code for i, (code, _) in enumerate(self.LANGUAGE_MAP.items(), 1)}
                    return lang_map[choice]
            except:
                print("无效输入，请重新选择")

    def _translate_with_deepseek(self, text: str, src_lang: str, target_lang: str) -> str:
        """使用DeepSeek API翻译文本"""
        try:
            if src_lang == target_lang:
                return text

            target_language_name = self.LANGUAGE_MAP.get(target_lang, ("未知语言", ""))[0]
            source_language_name = self.LANGUAGE_MAP.get(src_lang, ("未知语言", ""))[0]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            prompt = (
                f"你是一名专业的翻译官，能够将{source_language_name}准确翻译成{target_language_name}。\n"
                f"严格只输出翻译后的内容，不要添加任何解释、注解或额外信息。\n"
                f"保持专业术语准确，保留换行和格式。\n"
                f"请将以下{source_language_name}内容翻译成{target_language_name}：\n{text}"
            )

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名专业的翻译官，能够准确翻译各种语言内容。严格只输出翻译后的内容，不要添加任何解释、注解或额外信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"翻译失败: {str(e)}")
            return f"[TRANSLATION ERROR] {text}"

    def select_target_language(self):
        """交互式选择目标语言"""
        print("\n请选择目标语言:")
        for i, (code, (name, _)) in enumerate(self.LANGUAGE_MAP.items(), 1):
            print(f"{i}. {name} ({code})")

        while True:
            try:
                choice = input("请输入数字选择语言 (默认1-英语): ").strip()
                if not choice:
                    return "en"

                lang_map = {str(i): code for i, (code, _) in enumerate(self.LANGUAGE_MAP.items(), 1)}
                target_lang = lang_map.get(choice, "en")
                print(f"\n已选择: {self.LANGUAGE_MAP.get(target_lang, ('英语', ''))[0]}")
                return target_lang
            except Exception as e:
                print(f"无效输入: {e}")


    def setup_fonts(self):
        """初始化多语言字体支持"""
        self.font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.local/share/fonts"),
            os.path.expanduser("~/.fonts"),
            "/mnt/c/Windows/Fonts"
        ]

    def find_font(self, font_name):
        """在系统中查找字体文件"""
        for font_dir in self.font_dirs:
            if not os.path.exists(font_dir):
                continue

            for root, _, files in os.walk(font_dir):
                for filename in files:
                    if filename.lower() == font_name.lower():
                        return os.path.join(root, filename)

        try:
            result = subprocess.run(["fc-match", "-f", "%{file}", font_name],
                                    capture_output=True,
                                    text=True,
                                    check=True)
            if result.returncode == 0 and os.path.exists(result.stdout.strip()):
                return result.stdout.strip()
        except:
            pass

        return None

    def get_best_font(self, text, is_bold=False):
        """根据文本内容选择最合适的字体"""
        script = self.detect_script(text)

        if script == "cjk":
            font_name = "NotoSansCJK-Regular.ttc" if not is_bold else "NotoSansCJK-Bold.ttc"
        elif script == "korean":
            font_name = "NanumGothic.ttf" if not is_bold else "NanumGothicBold.ttf"
        elif script == "japanese":
            font_name = "NotoSansJP-Regular.otf" if not is_bold else "NotoSansJP-Bold.otf"
        elif script == "cyrillic":
            font_name = "NotoSans-Regular.ttf" if not is_bold else "NotoSans-Bold.ttf"
        else:
            font_name = "Arial.ttf" if not is_bold else "Arial Bold.ttf"

        font_key = f"{font_name}_{is_bold}"
        if font_key in self.font_cache:
            return self.font_cache[font_key]

        font_path = self.find_font(font_name)
        if font_path:
            self.font_cache[font_key] = font_path
            return font_path

        fallback = self.find_font("Arial.ttf") or self.find_font("DejaVuSans.ttf")
        if fallback:
            self.font_cache[font_key] = fallback
            return fallback

        raise ValueError(f"找不到合适的字体: {font_name}")

    def detect_script(self, text):
        """检测文本的主要文字系统"""
        if not text:
            return "latin"

        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return "cjk"
            elif '\uac00' <= char <= '\ud7a3':
                return "korean"
            elif '\u3040' <= char <= '\u30ff':
                return "japanese"
            elif '\u0400' <= char <= '\u04ff':
                return "cyrillic"

        return "latin"

    def translate_text(self, text):
        """使用 DeepSeek Chat API 进行翻译"""
        if self.source_lang == self.target_lang:
            return text  # 相同语言不翻译

        target_language_name = self.LANGUAGE_MAP.get(self.target_lang, ("英语", ""))[0]
        source_language_name = self.LANGUAGE_MAP.get(self.source_lang, ("自动检测", ""))[0]

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": f"你是一名专业的翻译官，能够将{source_language_name}准确翻译成{target_language_name}。"
                               "严格只输出翻译后的内容，不要添加任何解释、注解或额外信息。"
                               "保持专业术语准确，保留换行和格式。"
                },
                {
                    "role": "user",
                    "content": f"请将以下{source_language_name}内容翻译成{target_language_name}：\n{text}"
                }
            ],
            "temperature": 0.1,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.config['api'].get('timeout', 30)
                )
                response.raise_for_status()
                translated_text = response.json()["choices"][0]["message"]["content"]
                return translated_text.strip()

            except requests.exceptions.RequestException as e:
                print(f"翻译尝试 {attempt + 1}/{self.max_retries} 失败: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print("达到最大重试次数，保留原文")
                    return text
            except Exception as e:
                print(f"翻译过程中发生意外错误: {str(e)}")
                return text

    def load_json_file(self, json_file):
        """安全加载JSON文件"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        except Exception as e:
            print(f"加载JSON文件失败: {e}")
            return []

    def process_blocks(self, json_file):
        """处理JSON文件中的区块 - 修改为读取所有文本框的坐标和文本信息"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"加载JSON文件失败: {e}")
            return self.get_default_blocks()

        boxes = []

        # 检查并处理文本框信息
        if "rec_texts" in data and "rec_boxes" in data and len(data["rec_texts"]) == len(data["rec_boxes"]):
            for text, box_coords in zip(data["rec_texts"], data["rec_boxes"]):
                if text.strip() and len(box_coords) == 4:
                    translated = self.translate_text(text.strip())
                    text_lines = [line.strip() for line in translated.split('\n') if line.strip()]

                    boxes.append({
                        "coords": box_coords,
                        "text": text_lines,
                        "is_bold": False,
                        "left_margin": 30
                    })

        # 如果没有找到文本框信息，尝试使用dt_polys作为备选
        elif "dt_polys" in data and len(data["dt_polys"]) > 0:
            for poly in data["dt_polys"]:
                if len(poly) >= 4:
                    # 计算文本框的边界坐标
                    x_coords = [p[0] for p in poly]
                    y_coords = [p[1] for p in poly]
                    box_coords = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

                    # 添加一个默认文本（因为没有识别到的文本内容）
                    boxes.append({
                        "coords": box_coords,
                        "text": ["[待翻译文本]"],
                        "is_bold": False,
                        "left_margin": 30
                    })

        return boxes if boxes else self.get_default_blocks()

    def get_default_blocks(self):
        """获取默认处理块配置"""
        return [{
            "coords": [100, 100, 500, 200],
            "text": ["默认标题"],
            "is_bold": True,
            "left_margin": 50
        }]

    def wrap_text(self, text, font, max_width):
        """将文本按单词分割为多行"""
        if self.detect_script(text) in ["cjk", "korean", "japanese"]:
            # CJK文本按字符换行
            lines = []
            current_line = []
            current_width = 0
            for char in text:
                char_width = font.getbbox(char)[2] - font.getbbox(char)[0]
                if current_line and current_width + char_width > max_width:
                    lines.append(''.join(current_line))
                    current_line = [char]
                    current_width = char_width
                else:
                    current_line.append(char)
                    current_width += char_width
            if current_line:
                lines.append(''.join(current_line))
            return lines
        else:
            # 非CJK文本按单词换行
            words = text.split(' ')
            lines = []
            current_line = []
            current_width = 0
            space_width = font.getbbox(' ')[2]
            for word in words:
                word_width = font.getbbox(word)[2] - font.getbbox(word)[0]
                if current_line and current_width + word_width > max_width:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_width = word_width
                else:
                    current_line.append(word)
                    current_width += word_width + space_width
            if current_line:
                lines.append(' '.join(current_line))
            return lines

    def get_optimal_font(self, draw, text_lines, font_path, box_width, box_height):
        """计算最佳字体大小"""
        max_font_size = 150
        min_font_size = 8
        full_text = '\n'.join(text_lines)
        paragraphs = full_text.split('\n')

        for font_size in range(max_font_size, min_font_size - 1, -1):
            try:
                font = ImageFont.truetype(font_path, font_size)
                total_height = 0
                is_fit = True
                for para in paragraphs:
                    wrapped_lines = self.wrap_text(para, font, box_width * 0.95)
                    for line in wrapped_lines:
                        line_width = font.getbbox(line)[2] - font.getbbox(line)[0]
                        line_height = font.getbbox(line)[3] - font.getbbox(line)[1]
                        total_height += line_height
                        if line_width > box_width * 0.95:
                            is_fit = False
                            break
                    total_height += 5
                    if not is_fit or total_height > box_height * 0.95:
                        is_fit = False
                        break
                if is_fit:
                    return font_size
            except:
                continue
        return min_font_size

    def clear_area(self, draw, coords):
        """更精确的清除区域方法"""
        # 计算实际文本区域(可根据字体大小调整)
        text_width = coords[2] - coords[0]
        text_height = coords[3] - coords[1]
        effective_coords = [
            coords[0] + text_width * 0,  # 左边界内缩0%
            coords[1] + text_height * 0.15,  # 上边界内缩15%
            coords[2] - text_width * 0,  # 右边界内缩0%
            coords[3] - text_height * 0  # 下边界内缩0%
        ]
        draw.rectangle(effective_coords, fill='white', outline='white')

    def add_text(self, draw, coords, text_lines, is_bold=False, left_margin=30, right_margin=0):
        """在指定区域添加文本（严格左对齐）"""
        try:
            full_text = '\n'.join(text_lines)
            font_path = self.get_best_font(full_text, is_bold)
            if not font_path:
                print("警告: 找不到合适的字体")
                return

            box_width = coords[2] - coords[0] - left_margin - right_margin
            box_height = coords[3] - coords[1]
            font_size = self.get_optimal_font(draw, text_lines, font_path, box_width, box_height)
            font = ImageFont.truetype(font_path, font_size)

            paragraphs = full_text.split('\n')
            wrapped_lines_all = []
            for para in paragraphs:
                wrapped_lines = self.wrap_text(para, font, box_width)
                wrapped_lines_all.extend(wrapped_lines)

            # 计算起始位置（严格左对齐）
            x_pos = coords[0] + left_margin  # 固定左边距
            y_pos = coords[1]  # 从文本框顶部开始

            for line in wrapped_lines_all:
                # 绘制文本阴影（可选）
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    draw.text((x_pos + dx, y_pos + dy), line, font=font, fill='white')

                # 绘制文本（严格左对齐）
                draw.text((x_pos, y_pos), line, font=font, fill='black')

                # 移动到下一行（使用字体实际高度）
                y_pos += font.getbbox(line)[3] - font.getbbox(line)[1] + 2  # 2像素行间距
        except Exception as e:
            print(f"文本添加错误: {e}")

    def process_single_image(self, json_file, image_directory, output_directory):
        """处理单张图片（带完善错误处理）"""
        try:
            # 从JSON文件名推断图片文件名
            json_basename = os.path.basename(json_file)
            image_filename = json_basename.replace('_res.json',
                                                   '.jpg') if '_res.json' in json_basename else json_basename.replace(
                '.json', '.jpg')

            # 查找对应的图片文件
            image_path = None
            for root, _, files in os.walk(image_directory):
                if image_filename in files:
                    image_path = os.path.join(root, image_filename)
                    break

            if not image_path:
                print(f"警告: 找不到图片文件 {image_filename}")
                return False

            # 准备输出路径
            lang_suffix = f"_{self.target_lang}" if self.target_lang != "en" else ""
            output_filename = f"translated{lang_suffix}_{os.path.basename(image_filename)}"
            output_path = os.path.join(output_directory, output_filename)

            print(f"\n处理文件: {json_file}")
            print(f"使用图片: {image_path}")
            print(f"输出到: {output_path}")

            # 处理图片
            img = Image.open(image_path).convert('RGB')
            draw = ImageDraw.Draw(img)
            boxes = self.process_blocks(json_file)

            for box in boxes:
                coords = box["coords"]
                self.clear_area(draw, coords)
                if box.get("text"):
                    self.add_text(
                        draw=draw,
                        coords=coords,
                        text_lines=box["text"],
                        is_bold=box.get("is_bold", False),
                        left_margin=box.get("left_margin", 30)
                    )

            os.makedirs(output_directory, exist_ok=True)
            img.save(output_path, quality=100)
            return True
        except Exception as e:
            print(f"处理文件 {json_file} 失败: {e}")
            return False

    def batch_process_images(self, json_directory, image_directory, output_directory):
        """批量处理目录中的所有JSON文件（按数字顺序）"""
        os.makedirs(output_directory, exist_ok=True)

        # 获取所有JSON文件
        json_files = []
        for root, _, files in os.walk(json_directory):
            for file in files:
                if file.lower().endswith('.json'):
                    json_files.append(os.path.join(root, file))

        # 按数字顺序排序（关键修改点）
        json_files.sort(key=lambda x: int(re.search(r'page_(\d+)', x).group(1)))

        if not json_files:
            print(f"在目录 {json_directory} 中没有找到JSON文件")
            return

        processed_count = 0
        failed_count = 0

        for json_file in tqdm(json_files, desc="处理进度"):
            try:
                if self.process_single_image(json_file, image_directory, output_directory):
                    processed_count += 1
                else:
                    failed_count += 1
                    time.sleep(10)
            except Exception as e:
                print(f"处理文件 {json_file} 时发生严重错误: {e}")
                failed_count += 1

        print(f"\n处理完成! 成功处理 {processed_count} 个文件, 失败 {failed_count} 个")

    def translate_images(self):
        """翻译图片内容"""
        print("\n" + "=" * 50)
        print("步骤3: 翻译图片内容")
        print("=" * 50)

        json_directory = self.config['output']['json_dir']
        image_directory = self.config['output']['image_dir']
        output_directory = self.config['output']['translated_image_dir']

        self.batch_process_images(json_directory, image_directory, output_directory)