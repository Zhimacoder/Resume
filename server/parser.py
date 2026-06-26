"""
文档解析模块
支持PDF、DOCX、DOC、TXT、RTF格式简历解析
"""

import io
from typing import Optional
from pathlib import Path

# PDF解析
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# DOCX解析
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# DOC解析
try:
    import antiword
    HAS_ANTIWORD = True
except ImportError:
    HAS_ANTIWORD = False

# RTF解析
try:
    from striprtf.striprtf import rtf_to_text
    HAS_STRIPRTF = True
except ImportError:
    HAS_STRIPRTF = False


def parse_pdf(file_content: bytes) -> str:
    """解析PDF文件"""
    if not HAS_PYPDF2:
        return "[PDF解析需要安装PyPDF2库]"

    try:
        with io.BytesIO(file_content) as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        return f"[PDF解析失败: {str(e)}]"


def parse_docx(file_content: bytes) -> str:
    """解析DOCX文件"""
    if not HAS_DOCX:
        return "[DOCX解析需要安装python-docx库]"

    try:
        with io.BytesIO(file_content) as f:
            doc = docx.Document(f)
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            return text.strip()
    except Exception as e:
        return f"[DOCX解析失败: {str(e)}]"


def parse_doc(file_content: bytes) -> str:
    """解析DOC文件"""
    if not HAS_ANTIWORD:
        return "[DOC解析需要安装antiword库或使用OCR识别]"

    try:
        with io.BytesIO(file_content) as f:
            text = antiword.text_from_doc(f.read())
            return text.strip() if text else ""
    except Exception as e:
        return f"[DOC解析失败: {str(e)}]"


def parse_txt(file_content: bytes) -> str:
    """解析TXT纯文本文件，自动检测编码"""
    encodings = ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]
    for enc in encodings:
        try:
            return file_content.decode(enc).strip()
        except (UnicodeDecodeError, LookupError):
            continue
    return "[TXT解析失败: 无法识别文件编码]"


def parse_rtf(file_content: bytes) -> str:
    """解析RTF富文本文件"""
    if not HAS_STRIPRTF:
        # 降级方案：直接提取可读字符
        try:
            raw = file_content.decode("latin-1", errors="ignore")
            # 去除RTF控制字和花括号，保留可读文本
            import re
            text = re.sub(r'\\[a-z]+\d*\s?', ' ', raw)
            text = re.sub(r'[{}\\]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text if text else "[RTF解析失败: 请安装striprtf库]"
        except Exception as e:
            return f"[RTF解析失败: {str(e)}]"

    try:
        raw = file_content.decode("latin-1", errors="ignore")
        text = rtf_to_text(raw)
        return text.strip()
    except Exception as e:
        return f"[RTF解析失败: {str(e)}]"


def parse_document(file_content: bytes, filename: str) -> str:
    """统一解析接口"""
    ext = Path(filename).suffix.lower()

    if ext == '.pdf':
        return parse_pdf(file_content)
    elif ext == '.docx':
        return parse_docx(file_content)
    elif ext == '.doc':
        # 尝试先作为docx解析，失败则尝试doc
        result = parse_docx(file_content)
        if "[解析失败" in result or "[需要" in result:
            return parse_doc(file_content)
        return result
    elif ext == '.txt':
        return parse_txt(file_content)
    elif ext == '.rtf':
        return parse_rtf(file_content)
    else:
        return f"[不支持的文件格式: {ext}]"


# 便捷函数
__all__ = ['parse_document', 'parse_pdf', 'parse_docx', 'parse_doc', 'parse_txt', 'parse_rtf']
