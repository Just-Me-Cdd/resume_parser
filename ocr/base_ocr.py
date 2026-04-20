"""
OCR 基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np


@dataclass
class OCRResult:
    text: str
    bbox: List[float]
    confidence: float
    angle: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {"text": self.text, "bbox": self.bbox, "confidence": self.confidence, "angle": self.angle}


class BaseOCR(ABC):
    """OCR 引擎抽象基类"""
    
    @abstractmethod
    def recognize(self, img: np.ndarray) -> List[OCRResult]:
        """执行 OCR 识别"""
        pass
    
    @abstractmethod
    def recognize_batch(self, images: List[np.ndarray]) -> List[List[OCRResult]]:
        """批量执行 OCR 识别"""
        pass
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """支持的语言列表"""
        pass
    
    @abstractmethod
    def set_language(self, lang: str):
        """设置识别语言"""
        pass
    
    def extract_tables(self, img: np.ndarray) -> List[List[str]]:
        """提取表格内容（预留接口）"""
        return []
