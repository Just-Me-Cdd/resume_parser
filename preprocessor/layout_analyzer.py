"""
布局分析器
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextRegion:
    bbox: Tuple[int, int, int, int]
    text: str = ""
    confidence: float = 0.0
    region_type: str = "text"
    align: str = "left"


class LayoutAnalyzer:
    """简历布局分析器"""
    
    def __init__(self):
        self.min_region_width = 50
        self.min_region_height = 10
    
    def analyze(self, img: np.ndarray, ocr_results: Optional[List[Dict]] = None) -> Dict:
        """分析图片布局"""
        h, w = img.shape[:2]
        
        if ocr_results is None:
            logger.warning("未提供 OCR 结果，布局分析可能不准确")
            regions = []
        else:
            regions = self._classify_regions(ocr_results, w)
        
        has_photo = self._detect_photo(regions, w, h)
        columns, layout_type = self._detect_columns(regions, w)
        
        return {
            "regions": regions,
            "has_photo": has_photo,
            "columns": columns,
            "layout_type": layout_type,
            "image_size": (w, h)
        }
    
    def _classify_regions(self, ocr_results: List[Dict], img_width: int) -> List[TextRegion]:
        """根据 OCR 结果分类文本区域"""
        regions = []
        
        for result in ocr_results:
            bbox = result["bbox"]
            x1, y1, x2, y2 = [int(v) for v in bbox]
            
            region_w = x2 - x1
            region_h = y2 - y1
            if region_w < self.min_region_width or region_h < self.min_region_height:
                continue
            
            align = self._detect_align(x1, x2, img_width)
            region_type = self._classify_region(x1, y1, region_w, region_h, img_width)
            
            region = TextRegion(bbox=(x1, y1, x2, y2), text=result.get("text", ""), confidence=result.get("confidence", 0.0), region_type=region_type, align=align)
            regions.append(region)
        
        return regions
    
    def _detect_align(self, x1: int, x2: int, img_width: int) -> str:
        """检测文本对齐方式"""
        left_ratio = x1 / img_width
        right_ratio = (img_width - x2) / img_width
        
        if left_ratio < 0.15:
            return "left"
        elif right_ratio < 0.15:
            return "right"
        elif abs(left_ratio - right_ratio) < 0.1:
            return "center"
        else:
            return "left"
    
    def _classify_region(self, x: int, y: int, w: int, h: int, img_width: int) -> str:
        """分类区域类型"""
        aspect_ratio = w / h if h > 0 else 0
        
        if aspect_ratio > 4 and h < 30:
            return "title"
        if h > 100 and aspect_ratio < 0.5:
            return "table"
        
        x_ratio = x / img_width
        if x_ratio > 0.7 and 0.8 < aspect_ratio < 1.3 and h < 150:
            return "photo"
        
        return "text"
    
    def _detect_photo(self, regions: List[TextRegion], img_width: int, img_height: int) -> bool:
        """检测是否有证件照"""
        for region in regions:
            if region.region_type == "photo":
                return True
        
        right_regions = [r for r in regions if r.bbox[0] > img_width * 0.7]
        if len(right_regions) == 0:
            return True
        
        return False
    
    def _detect_columns(self, regions: List[TextRegion], img_width: int) -> Tuple[int, str]:
        """检测栏数"""
        if not regions:
            return 1, "single"
        
        left_regions = [r for r in regions if r.bbox[0] < img_width * 0.4]
        right_regions = [r for r in regions if r.bbox[0] > img_width * 0.6]
        
        if len(left_regions) > 2 and len(right_regions) > 2:
            return 2, "double"
        
        return 1, "single"
    
    def split_columns(self, img: np.ndarray, regions: List[TextRegion]) -> Tuple[np.ndarray, np.ndarray]:
        """将双栏布局的图片分割为左右两栏"""
        h, w = img.shape[:2]
        
        if len(regions) == 0:
            mid = w // 2
            return img[:, :mid], img[:, mid:]
        
        mid_x = w // 2
        mid_regions = [r for r in regions if r.bbox[0] < mid_x < r.bbox[2]]
        
        if mid_regions:
            left_max_x = max(r.bbox[2] for r in regions if r.bbox[2] < mid_x)
            right_min_x = min(r.bbox[0] for r in regions if r.bbox[0] > mid_x)
            mid_x = (left_max_x + right_min_x) // 2
        
        return img[:, :mid_x], img[:, mid_x:]
    
    def detect_lines(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """检测水平分割线"""
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=50, minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return []
        
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y2 - y1) < 20:
                horizontal_lines.append((x1, y1, x2, y2))
        
        return horizontal_lines
