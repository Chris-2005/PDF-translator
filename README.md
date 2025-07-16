---
# PDF Translator README

## English Version
[English](./README.md) | [简体中文](./README_zh.md)
### PDF Document Translator
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A powerful PDF document translation tool that supports both scanned and non-scanned PDFs. Scanned PDFs are processed through OCR before translation, while non-scanned PDFs are translated directly.

#### Key Features

1. **Dual Processing Modes**:
   - Scanned mode: OCR → Translation → Generate translated PDF
   - Non-scanned mode: Direct text extraction → Translation → Re-layout

2. **Multilingual Support**:
   - Supports Chinese, English, Japanese, Korean, Russian, Spanish, French, German, etc.

3. **Smart Font Selection**:
   - Automatically selects optimal fonts based on target language
   - Supports CJK character sets (Chinese, Japanese, Korean)

4. **API Integration**:
   - Uses DeepSeek API for high-quality translation

#### Installation & Usage

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Modify `config.yaml` to set input PDF path and output directories
   - Add your DeepSeek API key

3. **Run**:
   ```bash
   python main.py
   ```

4. **Select Mode**:
   - Choose between scanned or non-scanned processing based on your PDF type

#### Configuration

Edit `config.yaml`:

```yaml
input:
  pdf_path: "input_pdf_path"
  is_scanned: false  # Whether the PDF is scanned

output:
  pdf_dir: "output_pdf_directory"
  image_dir: "temp_image_directory"
  json_dir: "ocr_results_directory"
  translated_image_dir: "translated_images_directory"

api:
  deepseek_key: "your_deepseek_api_key"
  deepseek_url: "https://api.deepseek.com/v1/chat/completions"
```

#### Notes

1. Scanned PDFs require good image quality for optimal OCR results
2. Non-scanned PDFs process faster with better results
3. Ensure necessary fonts are installed on your system

---
