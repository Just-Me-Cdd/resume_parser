"""
图片去噪处理器
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class DenoiseProcessor:
    """图片去噪处理器"""
    
    def __init__(self, h: int = 10, template_window: int = 7, search_window: int = 21):
        self.h = h
        self.template_window = template_window
        self.search_window = search_window
    
    def fast_nl_means(self, img: np.ndarray) -> np.ndarray:
        """非局部均值去噪"""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img.copy()
        
        denoised = cv2.fastNlMeansDenoising(gray, h=self.h, templateWindowSize=self.template_window, searchWindowSize=self.search_window)
        logger.debug(f"非局部均值去噪完成: h={self.h}")
        return denoised
    
    def gaussian_blur(self, img: np.ndarray, kernel_size: Tuple[int, int] = (3, 3)) -> np.ndarray:
        """高斯模糊去噪"""
        k = kernel_size[0]
        if k % 2 == 0:
            k += 1
            kernel_size = (k, k)
        blurred = cv2.GaussianBlur(img, kernel_size, 0)
        logger.debug(f"高斯模糊去噪完成: kernel={kernel_size}")
        return blurred
    
    def bilateral_filter(self, img: np.ndarray, d: int = 9, sigma_color: int = 75, sigma_space: int = 75) -> np.ndarray:
        """双边滤波去噪"""
        filtered = cv2.bilateralFilter(img, d, sigma_color, sigma_space)
        logger.debug(f"双边滤波去噪完成: d={d}, sigma_color={sigma_color}")
        return filtered
    
    def median_blur(self, img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """中值滤波去噪"""
        if kernel_size % 2 == 0:
            kernel_size += 1
        filtered = cv2.medianBlur(img, kernel_size)
        logger.debug(f"中值滤波去噪完成: kernel_size={kernel_size}")
        return filtered
    
    def combined(self, img: np.ndarray) -> np.ndarray:
        """组合去噪"""
        blurred = cv2.GaussianBlur(img, (3, 3), 0)
        denoised = cv2.fastNlMeansDenoising(blurred, h=self.h)
        logger.debug("组合去噪完成")
        return denoised
    
    def process(self, img: np.ndarray, method: str = "nlmeans") -> np.ndarray:
        """统一去噪接口"""
        methods = {"nlmeans": self.fast_nl_means, "gaussian": self.gaussian_blur, "bilateral": self.bilateral_filter, "median": self.median_blur, "combined": self.combined}
        processor = methods.get(method, self.fast_nl_means)
        return processor(img)
