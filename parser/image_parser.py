"""
图片简历解析器
"""

from pathlib import Path
from typing import Union, Optional, List, Dict
from PIL import Image
import numpy as np

from parser.base import BaseParser
from preprocessor.image_preprocessor import ImagePreprocessor
from preprocessor.layout_analyzer import LayoutAnalyzer
from ocr.paddle_ocr import PaddleOCREngine
from extractor.section_matcher import SectionMatcher
from models.resume import Resume
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageParser(BaseParser):
    """图片简历解析器"""
    SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"]
    
    def __init__(self, use_preprocessing: bool = True, lang: str = "ch", use_gpu: bool = False, enable_layout_analysis: bool = False):
        self.use_preprocessing = use_preprocessing
        self.enable_layout_analysis = enable_layout_analysis
        self.preprocessor = ImagePreprocessor()
        self.ocr = PaddleOCREngine(lang=lang, use_gpu=use_gpu)
        self.matcher = SectionMatcher()
        self.layout_analyzer = LayoutAnalyzer()
    
    def parse(self, file_path: Union[str, Path]) -> Resume:
        path = self.validate_file(file_path)
        logger.info(f"开始解析图片简历: {path.name}")
        
        img = self._load_image(path)
        processed = self._preprocess(img)
        ocr_results = self._ocr_recognize(processed)
        
        layout_info = None
        if self.enable_layout_analysis:
            layout_info = self._analyze_layout(img, ocr_results)
        
        sections = self._match_sections(ocr_results)
        raw_text = "\n".join([r["text"] for r in ocr_results])
        
        resume = Resume(sections=sections, raw_text=raw_text, file_name=path.name, file_type="image", metadata={"layout": layout_info} if layout_info else {})
        
        logger.info(f"解析完成，共提取 {len(sections)} 个章节")
        return resume
    
    def _load_image(self, file_path: Path) -> np.ndarray:
        img = Image.open(file_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return np.array(img)
    
    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        if not self.use_preprocessing:
            import cv2
            return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        return self.preprocessor.enhance_for_ocr(img)
    
    def _ocr_recognize(self, img: np.ndarray) -> List[Dict]:
        logger.info("开始 OCR 识别...")
        try:
            ocr_results = self.ocr.recognize(img)
            return [{"text": r.text, "bbox": r.bbox, "confidence": r.confidence, "angle": r.angle} for r in ocr_results]
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return []
    
    def _analyze_layout(self, img: np.ndarray, ocr_results: List[Dict]) -> Dict:
        logger.info("开始布局分析...")
        try:
            layout = self.layout_analyzer.analyze(img, ocr_results)
            logger.info(f"布局分析完成: columns={layout['columns']}, has_photo={layout['has_photo']}, layout_type={layout['layout_type']}")
            return layout
        except Exception as e:
            logger.error(f"布局分析失败: {e}")
            return {}
    
    def _match_sections(self, ocr_results: List[Dict]) -> List:
        logger.info("开始标题-内容配对...")
        sections = self.matcher.match(ocr_results)
        logger.info(f"配对完成，共识别 {len(sections)} 个章节")
        return sections
    
    @classmethod
    def can_parse(cls, file_path: Union[str, Path]) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS


class ImageParserWithTable(ImageParser):
    """支持表格识别的图片解析器"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def parse_with_tables(self, file_path: Union[str, Path]) -> tuple:
        resume = self.parse(file_path)
        tables = self._extract_tables(file_path)
        return resume, tables
    
    def _extract_tables(self, file_path: Union[str, Path]) -> List[List[str]]:
        logger.info("开始表格提取...")
        try:
            img = self._load_image(Path(file_path))
            tables = self.ocr.extract_tables(img)
            logger.info(f"提取到 {len(tables)} 个表格")
            return tables
        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            return []
