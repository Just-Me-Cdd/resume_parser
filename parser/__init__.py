"""
简历解析工具 - 解析器模块
"""

from parser.base import BaseParser
from parser.image_parser import ImageParser
from parser.pdf_parser import PDFParser
from parser.docx_parser import DOCXParser
from parser.auto_detect import AutoDetectParser

__all__ = ["BaseParser", "ImageParser", "PDFParser", "DOCXParser", "AutoDetectParser"]
