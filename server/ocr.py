"""
OCR识别模块
支持本地OCR（PyTesseract）识别图片简历
"""

import io
from typing import Optional

# PIL用于图像处理
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# PyTesseract用于OCR
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def ocr_image(file_content: bytes) -> str:
    """OCR识别图片中的文字"""
    if not HAS_PIL:
        return "[图像处理需要安装Pillow库]"

    if not HAS_TESSERACT:
        return "[OCR识别需要安装pytesseract库，并配置Tesseract]"

    try:
        with io.BytesIO(file_content) as f:
            image = Image.open(f)

            # 转换为RGB模式（处理RGBA等模式）
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # OCR识别
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text.strip()
    except Exception as e:
        return f"[OCR识别失败: {str(e)}]"


def is_image_file(filename: str) -> bool:
    """判断是否为图片文件"""
    ext = filename.lower().split('.')[-1]
    return ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp']


def process_image(file_content: bytes, filename: str) -> str:
    """处理图片简历的统一接口"""
    if not is_image_file(filename):
        return "[不是图片文件]"

    return ocr_image(file_content)


__all__ = ['ocr_image', 'is_image_file', 'process_image']