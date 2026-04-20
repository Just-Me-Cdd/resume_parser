"""
图片预处理流水线
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from config import PREPROCESS_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)


class ImagePreprocessor:
    """简历图片预处理流水线"""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or PREPROCESS_CONFIG
    
    def process(self, img: np.ndarray) -> np.ndarray:
        """完整预处理流程"""
        gray = self._to_gray(img)
        denoised = self._denoise(gray)
        deskewed = self._deskew(denoised)
        enhanced = self._enhance_contrast(deskewed)
        binary = self._binarize(enhanced)
        return binary
    
    def enhance_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """专为 OCR 优化的预处理"""
        gray = self._to_gray(img)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, h=5)
        return denoised
    
    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        return img
    
    def _denoise(self, img: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(img, (3, 3), 0)
        denoised = cv2.fastNlMeansDenoising(blurred, h=self.config["denoise_h"])
        return denoised
    
    def _deskew(self, img: np.ndarray) -> np.ndarray:
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None or len(lines) == 0:
            return img
        
        angles = []
        for line in lines[:20]:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            if -45 < angle < 45:
                angles.append(angle)
        
        if not angles:
            return img
        
        median_angle = np.median(angles)
        
        if abs(median_angle) < self.config["deskew_angle_threshold"]:
            return img
        
        h, w = img.shape
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        logger.debug(f"图片纠偏: 角度={median_angle:.2f}°")
        return rotated
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=self.config["clahe_clip_limit"], tileGridSize=self.config["clahe_grid_size"])
        return clahe.apply(img)
    
    def _binarize(self, img: np.ndarray) -> np.ndarray:
        binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, self.config["binary_block_size"], self.config["binary_c"])
        return binary
    
    def remove_border(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape
        
        left_border = 0
        for x in range(w // 10):
            col = img[:, x]
            if np.mean(col) < 10:
                left_border = x
            else:
                break
        
        right_border = w
        for x in range(w - 1, w - w // 10, -1):
            col = img[:, x]
            if np.mean(col) < 10:
                right_border = x
            else:
                break
        
        top_border = 0
        for y in range(h // 10):
            row = img[y, :]
            if np.mean(row) < 10:
                top_border = y
            else:
                break
        
        bottom_border = h
        for y in range(h - 1, h - h // 10, -1):
            row = img[y, :]
            if np.mean(row) < 10:
                bottom_border = y
            else:
                break
        
        return img[top_border:bottom_border, left_border:right_border]
    
    def resize_if_needed(self, img: np.ndarray, max_size: int = 4096) -> np.ndarray:
        h, w = img.shape[:2]
        
        if max(h, w) <= max_size:
            return img
        
        scale = max_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug(f"图片缩放: ({w}x{h}) -> ({new_w}x{new_h})")
        return resized
