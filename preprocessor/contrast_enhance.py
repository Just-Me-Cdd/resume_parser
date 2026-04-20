"""
对比度增强处理器
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class ContrastEnhancer:
    """对比度增强处理器"""
    
    def __init__(self, clahe_clip_limit: float = 2.0, clahe_grid_size: Tuple[int, int] = (8, 8)):
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
    
    def clahe(self, img: np.ndarray) -> np.ndarray:
        """CLAHE 对比度增强"""
        clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=self.clahe_grid_size)
        enhanced = clahe.apply(img)
        logger.debug(f"CLAHE 增强完成: clip_limit={self.clahe_clip_limit}")
        return enhanced
    
    def histogram_equalization(self, img: np.ndarray) -> np.ndarray:
        """直方图均衡化"""
        equalized = cv2.equalizeHist(img)
        logger.debug("直方图均衡化完成")
        return equalized
    
    def gamma_correction(self, img: np.ndarray, gamma: float = 1.0) -> np.ndarray:
        """Gamma 校正"""
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        if len(img.shape) == 3:
            corrected = cv2.LUT(img, table)
        else:
            corrected = cv2.LUT(img, table)
        logger.debug(f"Gamma 校正完成: gamma={gamma}")
        return corrected
    
    def adaptive_threshold(self, img: np.ndarray, block_size: int = 11, c: int = 2) -> np.ndarray:
        """自适应阈值二值化"""
        if block_size % 2 == 0:
            block_size += 1
        binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c)
        logger.debug(f"自适应阈值完成: block_size={block_size}, c={c}")
        return binary
    
    def otsu_threshold(self, img: np.ndarray) -> np.ndarray:
        """Otsu 大津法阈值分割"""
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        logger.debug("Otsu 阈值分割完成")
        return binary
    
    def stretch_histogram(self, img: np.ndarray) -> np.ndarray:
        """直方图拉伸"""
        min_val = img.min()
        max_val = img.max()
        if max_val > min_val:
            stretched = ((img - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:
            stretched = img
        logger.debug(f"直方图拉伸完成: range=[{min_val}, {max_val}] -> [0, 255]")
        return stretched
    
    def process(self, img: np.ndarray, method: str = "clahe") -> np.ndarray:
        """统一对比度增强接口"""
        methods = {"clahe": self.clahe, "histogram": self.histogram_equalization, "gamma": self.gamma_correction, "stretch": self.stretch_histogram}
        processor = methods.get(method, self.clahe)
        return processor(img)
