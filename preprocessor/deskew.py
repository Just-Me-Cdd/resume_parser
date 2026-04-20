"""
图片纠偏处理器
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DeskewProcessor:
    """图片倾斜校正处理器"""
    
    def __init__(self, angle_threshold: float = 0.5):
        self.angle_threshold = angle_threshold
    
    def detect_angle(self, img: np.ndarray) -> float:
        """检测图片倾斜角度"""
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        angles = []
        for line in lines[:50]:
            rho, theta = line[0]
            if abs(np.sin(theta)) < 0.1:
                continue
            angle = (theta * 180 / np.pi) - 90
            if -45 <= angle <= 45:
                angles.append(angle)
        
        if not angles:
            return 0.0
        
        median_angle = np.median(angles)
        logger.debug(f"检测到倾斜角度: {median_angle:.2f}°")
        return median_angle
    
    def correct(self, img: np.ndarray, angle: Optional[float] = None) -> np.ndarray:
        """校正图片倾斜"""
        if angle is None:
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            angle = self.detect_angle(gray)
        
        if abs(angle) < self.angle_threshold:
            logger.debug(f"倾斜角度 {angle:.2f}° 小于阈值，不纠偏")
            return img
        
        if len(img.shape) == 3:
            h, w = img.shape[:2]
        else:
            h, w = img.shape
        
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        logger.info(f"图片纠偏完成: 角度={angle:.2f}°")
        return rotated
    
    def process(self, img: np.ndarray) -> np.ndarray:
        """完整纠偏流程"""
        return self.correct(img)
