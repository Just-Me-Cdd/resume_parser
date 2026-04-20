"""
PaddleOCR 引擎实现
"""

from typing import List, Dict, Optional
import cv2
import numpy as np
from paddleocr import PaddleOCR

from ocr.base_ocr import BaseOCR, OCRResult
from config import OCR_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)


class PaddleOCREngine(BaseOCR):
    """PaddleOCR 封装引擎（推荐使用）"""
    
    def __init__(self, use_angle_cls: bool = True, lang: str = "ch", use_gpu: bool = False, det_db_thresh: float = 0.3, det_db_box_thresh: float = 0.5, show_log: bool = False):
        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self.use_gpu = use_gpu
        self.det_db_thresh = det_db_thresh
        self.det_db_box_thresh = det_db_box_thresh
        self.show_log = show_log
        self._ocr: Optional[PaddleOCR] = None
    
    @property
    def ocr(self) -> PaddleOCR:
        """延迟初始化 OCR 引擎"""
        if self._ocr is None:
            logger.info("初始化 PaddleOCR 引擎...")
            self._ocr = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, use_gpu=self.use_gpu, det_db_thresh=self.det_db_thresh, det_db_box_thresh=self.det_db_box_thresh, show_log=self.show_log)
            logger.info(f"PaddleOCR 引擎初始化完成 (lang={self.lang}, gpu={self.use_gpu})")
        return self._ocr
    
    def recognize(self, img: np.ndarray) -> List[OCRResult]:
        """执行 OCR 识别"""
        logger.info("开始 OCR 识别...")
        
        try:
            results = self.ocr.ocr(img, cls=True)
            ocr_results = []
            
            if results and results[0]:
                for line in results[0]:
                    bbox = line[0]
                    text_info = line[1]
                    
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    x1, y1 = min(x_coords), min(y_coords)
                    x2, y2 = max(x_coords), max(y_coords)
                    
                    ocr_results.append(OCRResult(text=text_info[0], bbox=[float(x1), float(y1), float(x2), float(y2)], confidence=float(text_info[1]), angle=line[2] if len(line) > 2 else "正度"))
                
                logger.info(f"OCR 识别完成，检测到 {len(ocr_results)} 个文本区域")
            else:
                logger.warning("未检测到文本")
            
            return ocr_results
            
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return []
    
    def recognize_batch(self, images: List[np.ndarray]) -> List[List[OCRResult]]:
        """批量执行 OCR 识别"""
        results = []
        for img in images:
            results.append(self.recognize(img))
        return results
    
    @property
    def supported_languages(self) -> List[str]:
        """支持的语言列表"""
        return ["ch", "en", "japan", "korean", "chinese_cht", "fr", "de", "ru", "ar"]
    
    def set_language(self, lang: str):
        """设置识别语言"""
        if lang not in self.supported_languages:
            logger.warning(f"语言 {lang} 可能不受支持，支持的语言: {self.supported_languages}")
        self.lang = lang
        self._ocr = None
        logger.info(f"语言已切换为: {lang}")
    
    def recognize_with_layout(self, img: np.ndarray) -> Dict:
        """带布局分析的 OCR 识别"""
        from preprocessor.layout_analyzer import LayoutAnalyzer
        
        text_blocks = self.recognize(img)
        analyzer = LayoutAnalyzer()
        ocr_dicts = [{"text": r.text, "bbox": r.bbox, "confidence": r.confidence} for r in text_blocks]
        layout_info = analyzer.analyze(img, ocr_dicts)
        
        return {"text_blocks": text_blocks, "layout": layout_info}
    
    def extract_tables(self, img: np.ndarray) -> List[List[str]]:
        """提取表格内容"""
        try:
            result = self.ocr.ocr(img, cls=True, table=True)
            if not result or not result[0]:
                return []
            
            tables = []
            for line in result[0]:
                if len(line) >= 2 and isinstance(line[1], tuple):
                    table_html = line[1][0]
                    logger.info(f"检测到表格: {table_html[:100]}...")
                    tables.append([table_html])
            
            return tables
            
        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            return []
    
    def recognize_and_merge_lines(self, img: np.ndarray, y_threshold: int = 10) -> List[OCRResult]:
        """OCR 识别并合并相邻行"""
        results = self.recognize(img)
        if not results:
            return []
        
        sorted_results = sorted(results, key=lambda r: r.bbox[1])
        merged = []
        current_group = [sorted_results[0]]
        
        for result in sorted_results[1:]:
            prev_y = current_group[-1].bbox[1]
            curr_y = result.bbox[1]
            
            if abs(curr_y - prev_y) <= y_threshold:
                current_group.append(result)
            else:
                merged.append(self._merge_results(current_group))
                current_group = [result]
        
        if current_group:
            merged.append(self._merge_results(current_group))
        
        return merged
    
    def _merge_results(self, results: List[OCRResult]) -> OCRResult:
        """合并同一段落的多个 OCR 结果"""
        sorted_by_x = sorted(results, key=lambda r: r.bbox[0])
        merged_text = " ".join(r.text for r in sorted_by_x)
        
        min_x = min(r.bbox[0] for r in results)
        min_y = min(r.bbox[1] for r in results)
        max_x = max(r.bbox[2] for r in results)
        max_y = max(r.bbox[3] for r in results)
        
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        return OCRResult(text=merged_text, bbox=[min_x, min_y, max_x, max_y], confidence=avg_confidence)
