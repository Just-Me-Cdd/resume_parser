"""
自动识别解析器
"""

from pathlib import Path
from typing import Union, List, Optional

from parser.base import BaseParser
from parser.image_parser import ImageParser
from parser.pdf_parser import PDFParser
from parser.docx_parser import DOCXParser, DOCParser
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


class AutoDetectParser:
    """自动识别文件类型并路由到对应解析器"""
    PARSER_MAP = {".jpg": ImageParser, ".jpeg": ImageParser, ".png": ImageParser, ".bmp": ImageParser, ".webp": ImageParser, ".tiff": ImageParser, ".tif": ImageParser, ".pdf": PDFParser, ".docx": DOCXParser, ".doc": DOCParser}
    
    def __init__(self, default_lang: str = "ch", default_mode: str = "text", **parser_kwargs):
        self.default_lang = default_lang
        self.default_mode = default_mode
        self.parser_kwargs = parser_kwargs
        self._parsers: dict = {}
    
    def _get_parser(self, file_path: Union[str, Path]) -> BaseParser:
        path = Path(file_path)
        ext = path.suffix.lower()
        parser_class = self.PARSER_MAP.get(ext)
        if parser_class is None:
            raise ValueError(f"不支持的文件类型: {ext}")
        
        cache_key = f"{ext}_{self.default_lang}_{self.default_mode}"
        if cache_key not in self._parsers:
            if parser_class == ImageParser:
                self._parsers[cache_key] = parser_class(lang=self.default_lang, **self.parser_kwargs)
            elif parser_class == PDFParser:
                self._parsers[cache_key] = parser_class(mode=self.default_mode, lang=self.default_lang, **self.parser_kwargs)
            elif parser_class in (DOCXParser, DOCParser):
                self._parsers[cache_key] = parser_class()
            else:
                self._parsers[cache_key] = parser_class()
        
        return self._parsers[cache_key]
    
    def parse(self, file_path: Union[str, Path]) -> Resume:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not path.is_file():
            raise ValueError(f"不是有效的文件: {file_path}")
        
        ext = path.suffix.lower()
        logger.info(f"检测到文件类型: {ext} ({path.name})")
        parser = self._get_parser(path)
        resume = parser.parse(path)
        return resume
    
    def parse_batch(self, file_paths: List[Union[str, Path]]) -> List[Resume]:
        results = []
        for file_path in file_paths:
            try:
                resume = self.parse(file_path)
                results.append(resume)
            except Exception as e:
                logger.error(f"解析失败 {file_path}: {e}")
                results.append(Resume(file_name=str(file_path), file_type="error", metadata={"error": str(e)}))
        return results
    
    @staticmethod
    def get_supported_extensions() -> List[str]:
        return list(AutoDetectParser.PARSER_MAP.keys())
    
    @staticmethod
    def is_supported(file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in AutoDetectParser.PARSER_MAP
