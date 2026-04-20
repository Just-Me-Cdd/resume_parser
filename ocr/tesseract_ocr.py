"""
Tesseract OCR 引擎实现（备选）
"""

from typing import List, Dict, Optional
import cv2
import numpy as np
import pytesseract

from ocr.base_ocr import BaseOCR, OCRResult
from utils.logger import get_logger

logger = get_logger(__name__)


class TesseractOCREngine(BaseOCR):
    """Tesseract OCR 封装引擎（备选，轻量级）"""
    
    def __init__(self, lang: str = "chi_sim+eng", config: str = "--oem 3 --psm 6", timeout: int = 30):
        self.lang = lang
        self.config = config
        self.timeout = timeout
    
    def recognize(self, img: np.ndarray) -> List[OCRResult]:
        """执行 OCR 识别"""
        logger.info("开始 Tesseract OCR 识别...")
        
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            
            data = pytesseract.image_to_data(gray, lang=self.lang, config=self.config, timeout=self.timeout, output_type=pytesseract.Output.DICT)
            
            ocr_results = []
            n = len(data["text"])
            
            for i in range(n):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                
                if text and conf > 30:
                    x = data["left"][i]
                    y = data["top"][i]
                    w = data["width"][i]
                    h = data["height"][i]
                    
                    ocr_results.append(OCRResult(text=text, bbox=[float(x), float(y), float(x + w), float(y + h)], confidence=conf / 100.0))
            
            logger.info(f"Tesseract OCR 识别完成，检测到 {len(ocr_results)} 个文本区域")
            return ocr_results
            
        except Exception as e:
            logger.error(f"Tesseract OCR 识别失败: {e}")
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
        return ["eng", "chi_sim", "chi_tra", "jpn", "kor", "fra", "deu", "spa", "por", "ita", "rus", "ara", "hin", "ben", "tam", "tel"]
    
    def set_language(self, lang: str):
        """设置识别语言"""
        if "+" in lang:
            langs = lang.split("+")
            for l in langs:
                if l not in self.supported_languages:
                    logger.warning(f"语言 {l} 可能不受支持")
        elif lang not in self.supported_languages:
            logger.warning(f"语言 {lang} 可能不受支持")
        self.lang = lang
        logger.info(f"语言已切换为: {lang}")
    
    def extract_tables(self, img: np.ndarray) -> List[List[str]]:
        """提取表格内容"""
        try:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            
            config = self.config + " -c tessedit/create_tsv=1"
            data = pytesseract.image_to_data(gray, lang=self.lang, config=config)
            logger.warning("Tesseract 表格提取功能待完善")
            return []
            
        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            return []
    
    @staticmethod
    def check_installation() -> bool:
        """检查 Tesseract 是否正确安装"""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_available_languages() -> List[str]:
        """获取系统中可用的语言包"""
        try:
            return pytesseract.get_languages()
        except Exception:
            return []
