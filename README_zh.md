# PDF Translator README

## 中文版

### PDF 文档翻译工具
[![Python 版本](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![许可证](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

这是一个强大的PDF文档翻译工具，支持扫描件和非扫描件PDF的翻译处理。扫描件PDF通过OCR识别后翻译，非扫描件PDF直接处理文本内容进行翻译。

#### 功能特点

1. **双模式处理**：
   - 扫描件模式：OCR识别 → 文本翻译 → 生成翻译后PDF
   - 非扫描件模式：直接提取文本 → 翻译 → 重新排版生成PDF

2. **多语言支持**：
   - 支持中文、英文、日文、韩文、俄文、西班牙文、法文、德文等

3. **智能字体选择**：
   - 自动根据目标语言选择最佳字体
   - 支持CJK字符集(中文、日文、韩文)

4. **API集成**：
   - 使用DeepSeek API进行高质量翻译

#### 安装与使用

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **配置**：
   - 修改`config.yaml`文件，设置输入PDF路径和输出目录
   - 添加DeepSeek API密钥

3. **运行**：
   ```bash
   python main.py
   ```

4. **选择模式**：
   - 根据PDF类型选择扫描件或非扫描件处理模式

#### 配置说明

编辑`config.yaml`文件进行配置：

```yaml
input:
  pdf_path: "输入PDF路径"
  is_scanned: false  # 是否为扫描件

output:
  pdf_dir: "PDF输出目录"
  image_dir: "临时图片目录"
  json_dir: "OCR结果目录"
  translated_image_dir: "翻译后图片目录"

api:
  deepseek_key: "DeepSeek API密钥"
  deepseek_url: "https://api.deepseek.com/v1/chat/completions"
```

#### 注意事项

1. 扫描件PDF需要较高的图像质量才能获得好的OCR效果
2. 非扫描件PDF处理速度更快，效果更好
3. 确保系统已安装必要的字体
